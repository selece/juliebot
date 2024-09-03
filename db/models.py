from sqlalchemy import (
    Integer,
    Boolean,
    Column,
    VARCHAR,
    Date,
    ForeignKey,
    Enum
)

from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Viewer:
    def __init__(self, id, last_seen, view_streak):
        self.id = id
        self.last_seen = last_seen
        self.view_streak = view_streak

