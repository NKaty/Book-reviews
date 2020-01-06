from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from config import Config

engine = create_engine(Config.DATABASE_URL)
db = scoped_session(sessionmaker(bind=engine))


def main():
    db.execute('CREATE TABLE books (isbn VARCHAR PRIMARY KEY, \
                                    title VARCHAR NOT NULL, \
                                    author VARCHAR NOT NULL, \
                                    year SMALLINT NOT NULL)')
    print('The table "books" is created.')

    db.execute('CREATE TABLE users (id SERIAL PRIMARY KEY, \
                                    username VARCHAR UNIQUE NOT NULL, \
                                    password VARCHAR NOT NULL)')
    print('The table "users" is created.')

    db.execute('CREATE TABLE reviews (id SERIAL PRIMARY KEY, \
                                        book_isbn VARCHAR REFERENCES books NOT NULL, \
                                        user_id INTEGER REFERENCES users NOT NULL, \
                                        rating SMALLINT NOT NULL CHECK (rating <= 5 AND rating >= 1), \
                                        comment VARCHAR, \
                                        created_on TIMESTAMP NOT NULL DEFAULT NOW(), \
                                        CONSTRAINT review_user_book_unique UNIQUE (book_isbn, user_id))')
    print('The table "reviews" is created.')

    db.commit()


if __name__ == '__main__':
    main()
