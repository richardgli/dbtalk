import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

class Base(DeclarativeBase):
    pass

engine = create_engine(os.getenv("DATABASE_URL"))
test_engine = create_engine(os.getenv("DEV_DATABASE_URL"))