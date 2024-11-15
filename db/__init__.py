import logging
import sqlite3

from dataclasses import dataclass
from datetime import datetime, timedelta

# constants
DATABASE_PATH = "juliebot.db"
MONTH_IN_SECONDS = 30 * 24 * 60 * 60
TWELVE_HOURS_IN_SECONDS = 60 * 60 * 12

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
                self.init_checkin_db()

                # checkin module vars
                self.current_broadcast = -1
            
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
        
    # checkin
    def init_checkin_db(self) -> None:
        statements = [
            '''CREATE TABLE IF NOT EXISTS checkin_users (id INTEGER PRIMARY KEY, twitch_id INTEGER NOT NULL UNIQUE, last_seen INTEGER, last_seen_broadcast INTEGER, watch_streak INTEGER)''',
            '''CREATE TABLE IF NOT EXISTS broadcasts (id INTEGER PRIMARY KEY, date INTEGER NOT NULL)'''
        ]
        for statement in statements:
            self.run_sql_commit(statement)

    def add_broadcast_to_db(self) -> bool:
        now = int(datetime.now().strftime('%s'))
        last_broadcast = self.get_last_broadcast_from_db()
        logging.info(f'checking for last broadcast: {last_broadcast}')

        if last_broadcast is None or now - last_broadcast[1] >= TWELVE_HOURS_IN_SECONDS:
            logging.info(f'recorded new broadcast: {now}')
            self.run_sql_commit('''INSERT INTO broadcasts(date) VALUES(?)''', (int(datetime.now().strftime('%s')), ))
            return True
        else:
            logging.info(f'last broadcast within 12 hours {last_broadcast}; skipping broadcast checkin for {now}')
            return False

    def get_last_broadcast_from_db(self) -> tuple | None:
        results = self.run_sql_query('''SELECT * FROM broadcasts ORDER BY date DESC''', vals=tuple(), limit_one=False, expect_one=False)

        if results is None or len(results) == 0:
            return None
        
        if results[0][0] == self.current_broadcast:
            return None
        else:
            if len(results) > 1:
                return results[1]
            else:
                return None

    def add_checkinuser_to_db(self, twitch_id: int) -> None:
        self.run_sql_commit('''INSERT INTO checkin_users(twitch_id, last_seen, last_seen_broadcast, watch_streak) VALUES(?, ?, ?, ?)''', (twitch_id, int(datetime.now().strftime('%s')), -1, 1))

    def get_checkinuser_from_db(self, twitch_id: int) -> tuple:
        res = self.run_sql_query('''SELECT * FROM checkin_users WHERE twitch_id=?''', (twitch_id, ))
        if res is None:
            logging.error(f'Failed to fetch twitch_id={twitch_id} from the checkin_users db.')
            return None
        
        return res
    
    def record_checkinuser(self, twitch_id: int) -> int:
        user = self.get_checkinuser_from_db(twitch_id)
        if user is None:
            self.add_checkinuser_to_db(twitch_id)
            user = self.get_checkinuser_from_db(twitch_id)

        last_broadcast = self.get_last_broadcast_from_db()
        was_here_last_broadcast = False

        if last_broadcast is None:
            was_here_last_broadcast = False
        else:
            was_here_last_broadcast = user[3] == last_broadcast[0]
        
        watch_streak = int(user[4])

        now_timestamp = datetime.now()
        if now_timestamp - datetime.fromtimestamp(int(user[2])) < timedelta(seconds=TWELVE_HOURS_IN_SECONDS):
            return watch_streak
        
        if was_here_last_broadcast:
            watch_streak += 1
        else:
            watch_streak = 1
        
        self.run_sql_commit('''UPDATE checkin_users SET last_seen=?, last_seen_broadcast=?, watch_streak=? WHERE id=?''', (now_timestamp, last_broadcast[0], watch_streak, user[0]))
        return watch_streak
        
    # mood
    def init_mood_db(self) -> None:
        statements = [
            '''CREATE TABLE IF NOT EXISTS mood_users (id INTEGER PRIMARY KEY, twitch_id INTEGER NOT NULL UNIQUE, last_mood INTEGER)''',
            '''CREATE TABLE IF NOT EXISTS mood_record (user_id INTEGER NOT NULL, timestamp INTEGER NOT NULL, mood INTEGER NOT NULL, FOREIGN KEY (user_id) REFERENCES mood_users (id) )'''
        ]
        for sql in statements:
            self.run_sql_commit(sql)

    def add_mooduser_to_db(self, twitch_id: int) -> None:
        self.run_sql_commit('''INSERT INTO mood_users(twitch_id) VALUES (?)''', (twitch_id, ))
    
    def get_mooduser_from_db(self, twitch_id: int) -> tuple | None:
        return self.run_sql_query('''SELECT * FROM mood_users WHERE twitch_id=?''', (twitch_id, ))
    
    def record_mooduser(self, twitch_id: int, mood: int) -> None:
        user = self.get_mooduser_from_db(twitch_id)
        if user is None:
            self.add_mooduser_to_db(twitch_id)
            user = self.get_mooduser_from_db(twitch_id)

        self.run_sql_commit('''INSERT INTO mood_record(user_id, timestamp, mood) VALUES(?, ?, ?)''', (user[0], int(datetime.now().strftime('%s')), mood))
        self.run_sql_commit('''UPDATE mood_users SET last_mood=? WHERE twitch_id=?''', (mood, twitch_id))

    def get_average_mood(self, twitch_id: int) -> int:
        user = self.get_mooduser_from_db(twitch_id)
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
        user = self.get_mooduser_from_db(twitch_id)
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
