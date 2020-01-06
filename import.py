import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from config import Config

engine = create_engine(Config.DATABASE_URL)
db = scoped_session(sessionmaker(bind=engine))


def main():
    with open('books.csv') as file:
        reader = csv.reader(file)
        next(reader)
        for isbn, title, author, year in reader:
            db.execute('INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)',
                       {'isbn': isbn, 'title': title, 'author': author, 'year': year})

    db.commit()
    print('All books are added to the database.')


if __name__ == '__main__':
    main()
