import logging
from datetime import datetime
from sqlalchemy import create_engine, select, select_from, update, insert, DateTime
from sqlalchemy.orm import sessionmaker

from .models import Base, Viewer

# constants
DATABASE_PATH = "juliebot.db"

logger = logging.getLogger(__name__)

class DB:
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super(DB, cls).__new__(cls)
            cls.__instance.__initialized = False
        return cls.__instance

    def __self__(self):
        if self.__initialized:
            return
        
        self.__initialized = True
        self.engine = create_engine(f'sqlite://{DATABASE_PATH}')
        self.session = sessionmaker(self.engine, autoflush=True)
        Base.metadata.create_all(self.engine)

    def get_viewer(self, id):
        with self.session() as sess:
            query = (
                select_from(Viewer)
                    .where(Viewer.id == id)
            )
            result = sess.execute(query).one()

        return result
