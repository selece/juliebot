import logging
import sqlite3

from datetime import datetime

# constants
DATABASE_PATH = "juliebot.db"
MONTH_IN_SECONDS = 30*24*60*60

logger = logging.getLogger(__name__)

class DB:
    __instance = None

    def __init__(self) -> None:
        if DB.__instance is not None:
            raise RuntimeError('cannot re-instantiate DB class')
        else:
            DB.__instance = self
            self.conn = None
            try:
                self.conn = sqlite3.connect(DATABASE_PATH)
                self.init_puns_db()
                self.init_mood_db()
            
            except sqlite3.Error as e:
                logging.error(f'failed to instantiate db: {e} - bot functionality will be limited')
                return None
            
    
    @staticmethod
    def instance():
        if DB.__instance is None:
            DB()

        return DB.__instance
    
    def cleanup(self) -> None:
        self.conn.close()

    def run_sql_commit(self, sql_statement: str, vals: tuple|None=None) -> None:
        try:
            cursor = self.conn.cursor()
            
            if vals is None:
                cursor.execute(sql_statement)
            else:
                cursor.execute(sql_statement, vals)

            self.conn.commit()
            logger.info(f'sql OK: {sql_statement} {vals}')
            
        except sqlite3.Error as e:
            logger.error(f'failed to execute sql statement \'{sql_statement}\' with vals {vals}: {e}')
        
    def run_sql_query(self, sql_statement: str, vals: tuple, limit_one: bool=True, expect_one: bool=True) -> list[tuple]|tuple:
        cursor = self.conn.cursor()
        cursor.execute(sql_statement, vals)
        rows = cursor.fetchall()

        if expect_one:
            if len(rows) > 1:
                logger.error(f'duplicate entries in db found, only expected one for query: {sql_statement} {vals}')
                return None
            
        if len(rows) == 0:
            logger.info(f'no entries found in db for query: {sql_statement} {vals}')
            return None
        
        if limit_one:
            return rows[0]
        else:
            return rows
        
    # mood
    def init_mood_db(self):
        statements = [
            '''CREATE TABLE IF NOT EXISTS mood_users (id INTEGER PRIMARY KEY, twitch_id INTEGER NOT NULL UNIQUE, last_mood INTEGER)''',
            '''CREATE TABLE IF NOT EXISTS mood_record (user_id INTEGER NOT NULL, timestamp INTEGER NOT NULL, mood INTEGER NOT NULL, FOREIGN KEY (user_id) REFERENCES mood_users (id) )'''
        ]
        for sql in statements:
            self.run_sql_commit(sql)

    def add_user_to_db(self, twitch_id: int) -> None:
        self.run_sql_commit('''INSERT INTO mood_users(twitch_id) VALUES (?)''', (twitch_id, ))
    
    def get_user_from_db(self, twitch_id: int) -> tuple:
        return self.run_sql_query('''SELECT * from mood_users WHERE twitch_id=?''', (twitch_id, ))
    
    def record_user_mood(self, twitch_id: int, mood: int) -> None:
        user = self.get_user_from_db(twitch_id)
        if user is None:
            self.add_user_to_db(twitch_id)
            user = self.get_user_from_db(twitch_id)

        self.run_sql_commit('''INSERT INTO mood_record(user_id, timestamp, mood) VALUES(?, ?, ?)''', (user[0], int(datetime.now().strftime('%s')), mood))
        self.run_sql_commit('''UPDATE mood_users SET last_mood=? WHERE twitch_id=?''', (mood, twitch_id))

    def get_average_mood(self, twitch_id: int) -> int:
        user = self.get_user_from_db(twitch_id)
        if user is None:
            return 0
        
        timestamp_now = int(datetime.now().strftime('%s'))
        results = self.run_sql_query('''SELECT * FROM mood_record WHERE user_id=? AND (? - timestamp < ?)''', (user[0], timestamp_now, MONTH_IN_SECONDS), limit_one=False, expect_one=False)

        if results is None or len(results) == 0:
            logger.warn(f'no moods found for user {twitch_id}, returning 0')
            return 0

        average_mood = 0
        for res in results:
            average_mood += res[2]
        average_mood = average_mood / len(results)

        return average_mood
    
    def get_last_mood(self, twitch_id: int) -> int:
        user = self.get_user_from_db(twitch_id)
        if user is None:
            return 0
        
        if user[2] is None:
            return 0
        
        return user[2]
                    
    # puns
    def init_puns_db(self) -> None:
        self.run_sql_commit('''CREATE TABLE IF NOT EXISTS puns (id INTEGER PRIMARY KEY, api_id INTEGER NOT NULL UNIQUE, rating REAL NOT NULL, ban INT NOT NULL)''')

    def add_pun_to_db(self, api_id) -> None:
        self.run_sql_commit('''INSERT INTO puns(api_id, rating, ban) VALUES(?, ?, ?)''', (api_id, 0, 0))
    
    def get_pun_from_db(self, api_id: int) -> tuple|None:
        return self.run_sql_query('''SELECT * FROM puns WHERE api_id=?''', (api_id, ))

    def update_pun_rating(self, api_id: int, rating: float) -> None:
        self.run_sql_commit('''UPDATE puns SET rating=? WHERE api_id=?''', (rating, api_id))
    
    def check_if_pun_exists(self, api_id: int) -> bool:
        results = self.run_sql_query('''SELECT * FROM puns WHERE api_id=?''', (api_id, ), limit_one=False, expect_one=False)
        if results is None:
            return False
        return len(results) == 1
    
    def ban_pun(self, api_id: int) -> None:
        self.run_sql_commit('''UPDATE puns SET ban=1 WHERE api_id=?''', (api_id, ))
