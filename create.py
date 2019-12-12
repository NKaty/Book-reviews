import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable
if not os.getenv('DATABASE_URL'):
    raise RuntimeError('DATABASE_URL is not set')

engine = create_engine(os.getenv('DATABASE_URL'))
db = scoped_session(sessionmaker(bind=engine))


def main():
    db.execute('CREATE TABLE books (isbn VARCHAR PRIMARY KEY,\
                                    title VARCHAR NOT NULL,\
                                    author VARCHAR NOT NULL,\
                                    year SMALLINT NOT NULL)')
    print('The table "books" is created.')
    db.execute('CREATE TABLE users (id SERIAL PRIMARY KEY,\
                                    username VARCHAR UNIQUE NOT NULL,\
                                    password VARCHAR NOT NULL)')
    print('The table "users" is created.')
    db.commit()


if __name__ == '__main__':
    main()
