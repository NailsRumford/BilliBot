from sqlalchemy import create_engine, Column, Integer, String, PickleType, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json


Base = declarative_base()

class UserProfile(Base):
    __tablename__ = 'user_profile'

    id = Column(Integer, primary_key=True)
    game_settings_created = Column(Boolean)
    game_started = Column(Boolean)
    user = Column(String)
    character = Column(String)
    history = Column(JSON)

    def __init__(self,game_settings_created=False ,game_started=False, user=None, character=None, history=None):
        self.game_settings_created = game_settings_created
        self.game_started = game_started
        self.user = user
        self.character = character
        self.history = history if history is not None else []
        
    def replace_history(self, new_history):
        self.history = new_history


    def delete(self, session):
        session.delete(self)
        session.commit()
