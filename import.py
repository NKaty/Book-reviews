import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable
if not os.getenv('DATABASE_URL'):
    raise RuntimeError('DATABASE_URL is not set')

engine = create_engine(os.getenv('DATABASE_URL'))
db = scoped_session(sessionmaker(bind=engine))


def main():
    with open('books.csv') as file:
        reader = csv.reader(file)
        next(reader)
        for isbn, title, author, year in reader:
            db.execute('INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)',
                       {'isbn': isbn, 'title': title, 'author': author, 'year': year})

    print('All books are added to the database.')
    db.commit()


if __name__ == '__main__':
    main()
