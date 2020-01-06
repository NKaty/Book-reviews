import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL = os.getenv('DATABASE_URL')
    GOODREADS_KEY = os.getenv('GOODREADS_KEY')
    # Configure session to use filesystem
    SESSION_PERMANENT = False
    SESSION_TYPE = 'filesystem'
