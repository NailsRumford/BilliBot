from sqlalchemy import create_engine, Column, Integer, String, PickleType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .models import Base, UserProfile

engine = create_engine('sqlite:///user_history.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


def save_user_profile(user_history):
    session.add(user_history)
    session.commit()

def load_user_profile(user):
    user_profile = session.query(UserProfile).filter(UserProfile.user == user).first()
    if user_profile is not None:
        return user_profile
    else:
        return None
