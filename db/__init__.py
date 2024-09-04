import logging
import sqlite3

from datetime import datetime

# constants
DATABASE_PATH = "juliebot.db"

logger = logging.getLogger(__name__)

class DB:
    __instance = None

    def __init__(self):
        if DB.__instance is not None:
            raise RuntimeError('cannot re-instantiate DB class')
        else:
            DB.__instance = self
            self.conn = None
            try:
                self.conn = sqlite3.connect(DATABASE_PATH)
                self.init_puns_db()
            
            except sqlite3.Error as e:
                logging.error(f'failed to instantiate db: {e} - bot functionality will be limited')
                return None
            
    
    @staticmethod
    def instance():
        if DB.__instance is None:
            DB()

        return DB.__instance
    
    def cleanup(self):
        self.conn.close()

    def run_sql_commit(self, sql_statement, vals=None):
        try:
            cursor = self.conn.cursor()
            
            if vals is None:
                cursor.execute(sql_statement)
            else:
                cursor.execute(sql_statement, vals)

            self.conn.commit()
            logger.info(f'sql OK: {sql_statement} {vals}')
            return cursor.lastrowid
            
        except sqlite3.Error as e:
            logger.error(f'failed to execute sql statement \'{sql_statement}\' with vals {vals}: {e}')
            return -1

    
    def init_puns_db(self):
        sql = '''CREATE TABLE IF NOT EXISTS puns (id INTEGER PRIMARY KEY, api_id INTEGER NOT NULL UNIQUE, rating REAL NOT NULL, ban INT NOT NULL)'''
        self.run_sql_commit(sql)

    def add_pun_to_db(self, api_id):
        sql = '''INSERT INTO puns(api_id, rating, ban) VALUES(?, ?, ?)'''
        return self.run_sql_commit(sql, (api_id, 0, 0))
    
    def get_pun_from_db(self, api_id: int):
        sql = '''SELECT * FROM puns WHERE api_id=?'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (api_id))
        rows = cursor.fetchall()

        if len(rows) > 1:
            logger.error(f'duplicate entry in db for api_id: {api_id}')
            return None
        
        if len(rows) == 0:
            logger.info(f'no pun with api_id {api_id} found in db')
            return None
        
        return rows[0]

    def update_pun_rating(self, api_id: int, rating: float):
        sql = '''UPDATE puns SET rating=? WHERE api_id=?'''
        return self.run_sql_commit(sql, (api_id, rating))
    
    def check_if_pun_exists(self, api_id: int):
        sql = '''SELECT * FROM puns WHERE api_id=?'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (api_id, ))
        rows = cursor.fetchall()

        if len(rows) > 1:
            logger.error(f'duplicate entry in db for api_id: {api_id}')
            return True
        
        return len(rows) == 1
