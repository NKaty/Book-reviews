import math
import os

from flask import Flask, session, redirect, request, render_template, url_for, flash, jsonify
from flask_session import Session
from functools import wraps
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, template_folder='templates')

# Check for environment variable
if not os.getenv('DATABASE_URL'):
    raise RuntimeError('DATABASE_URL is not set')

# Configure session to use filesystem
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Set up database
engine = create_engine(os.getenv('DATABASE_URL'))
db = scoped_session(sessionmaker(bind=engine))


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    session.clear()

    if request.method == 'GET':
        return render_template('signup.html')

    username = request.form.get('username')
    password = request.form.get('password')
    conf_password = request.form.get('conf-password')

    if not username or not password or not conf_password:
        flash('All fields of the form must be filled in!')
        return render_template('signup.html')

    if len(username) < 2:
        flash('Username must be at least 2 characters long!')
        return render_template('signup.html')

    if len(password) < 6:
        flash('Password must be at least 6 characters long!')
        return render_template('signup.html')

    if password != conf_password:
        flash('Passwords must match!')
        return render_template('signup.html')

    user = db.execute('INSERT INTO users (username, password) \
                        VALUES (:username, :password) \
                        ON CONFLICT ON CONSTRAINT users_username_key \
                        DO NOTHING \
                        RETURNING id, username',
                      {'username': username, 'password': generate_password_hash(password)}).fetchone()
    db.commit()

    if user is None:
        flash('That username is already taken. Please, choose another username!')
        return render_template('signup.html')

    session['user_id'] = user.id
    session['username'] = user.username

    return redirect('/search-form')


@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()

    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('All fields of the form must be filled in!')
        return render_template('login.html')

    user = db.execute('SELECT * FROM users WHERE username = :username', {'username': username}).fetchone()

    if user is None or not check_password_hash(user.password, password):
        flash('Invalid password or username!')
        return render_template('login.html')

    session['user_id'] = user.id
    session['username'] = user.username

    return redirect('/search-form')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated_function


@app.route('/search-form', methods=['GET'])
@login_required
def search_form():
    return render_template("search.html")


@app.route('/search/<int:page>', methods=['GET'])
@login_required
def search(page):
    per_page = 10
    page = int(page)
    offset = ((page - 1) * per_page)

    query = {
        'isbn': f'%{request.args.get("isbn").upper()}%',
        'title': f'%{request.args.get("title").upper()}%',
        'author': f'%{request.args.get("author").upper()}%',
        'year': request.args.get('year')
    }

    try:
        query['year'] = int(query['year'])
    except ValueError:
        query['year'] = None

    if session.get('query')['year'] is None:
        total = db.execute('SELECT COUNT(*) FROM books WHERE \
                            (UPPER(isbn) LIKE :isbn AND \
                            UPPER(title) LIKE :title AND \
                            UPPER(author) LIKE :author)',
                           {'isbn': query['isbn'],
                            'title': query['title'],
                            'author': query['author']
                            }).fetchone()

        if not total:
            flash('Nothing has been found on your request!')
            return render_template('search.html')

        books = db.execute('SELECT isbn, title, author, year FROM books WHERE \
                            (UPPER(isbn) LIKE :isbn AND \
                            UPPER(title) LIKE :title AND \
                            UPPER(author) LIKE :author) \
                            ORDER BY title OFFSET :offset LIMIT :per_page',
                           {'isbn': query['isbn'],
                            'title': query['title'],
                            'author': query['author'],
                            'offset': offset,
                            'per_page': per_page
                            }).fetchall()
        print(total)
    else:
        total = db.execute('SELECT COUNT(*) FROM books WHERE \
                            (UPPER(isbn) LIKE :isbn AND \
                            UPPER(title) LIKE :title AND \
                            UPPER(author) LIKE :author) \
                            year = :year)',
                           {'isbn': query['isbn'],
                            'title': query['title'],
                            'author': query['author']
                            }).fetchone()

        if not total:
            flash('Nothing has been found on your request!')
            return render_template('search.html')

        books = db.execute('SELECT isbn, title, author, year FROM books WHERE \
                            (UPPER(isbn) LIKE :isbn AND \
                            UPPER(title) LIKE :title AND \
                            UPPER(author) LIKE :author AND \
                            year = :year) \
                            ORDER BY title OFFSET :offset LIMIT :per_page',
                           {'isbn': query['isbn'],
                            'title': query['title'],
                            'author': query['author'],
                            'year': query['year'],
                            'offset': offset,
                            'per_page': per_page
                            }).fetchall()

    # 404
    if not len(books):
        flash('Nothing has been found on your request!')
        return render_template('search.html')

    pages = int(math.ceil(total[0] / float(per_page)))
    pagination = {'pages': pages,
                  'previous': page - 1 if page > 1 else None,
                  'next': page + 1 if page < pages else None,
                  'page': page}

    return render_template('books.html', books=books, pagination=pagination, query_params=dict(request.args))


@app.route('/book/<isbn>', methods=['GET', 'POST'])
@login_required
def book(isbn):
    if request.method == 'GET':
        book_data = db.execute("SELECT isbn, title, author, year, \
                                reviews.rating, reviews.comment, \
                                TO_CHAR(reviews.created_on, 'DD/MM/YYYY HH24:MI:SS') as created_on, \
                                users.username \
                                FROM books \
                                LEFT JOIN reviews ON reviews.book_isbn = books.isbn \
                                LEFT JOIN users ON users.id = reviews.user_id \
                                WHERE books.isbn = :isbn \
                                ORDER by created_on DESC",
                               {'isbn': isbn}).fetchall()

        # request to Goodreads API
        if len(book_data):
            try:
                rating_data = requests.get('https://www.goodreads.com/book/review_counts.json', params={
                    'key': os.getenv('GOODREADS_KEY'),
                    'isbns': isbn
                }).json()['books'][0]
            except Exception:
                flash('Unfortunately we cannot get information from goodreads.com.')
                rating_data = None

        else:
            flash(f'There is no book with isbn {isbn}. Please, try again.')
            return redirect(url_for('search_form'))

        return render_template('book.html', book_data=book_data, rating_data=rating_data)

    # POST request
    rating = request.form.get('rating')
    comment = request.form.get('comment')

    review_id = db.execute('INSERT INTO reviews (book_isbn, user_id, rating, comment) \
                            VALUES (:book_isbn, :user_id, :rating, :comment) \
                            ON CONFLICT ON CONSTRAINT review_user_book_unique \
                            DO NOTHING \
                            RETURNING id',
                           {'book_isbn': isbn,
                            'user_id': session.get('user_id'),
                            'rating': rating,
                            'comment': comment}).fetchone()
    db.commit()

    if review_id is None:
        flash('You already submitted a review for this book.')

    return redirect(url_for('book', isbn=isbn))


@app.route("/api/<isbn>", methods=['GET'])
def api_book(isbn):
    book_data = db.execute('SELECT isbn, title, author, year, \
                            COUNT(reviews.id) as review_count, \
                            AVG(reviews.rating) as average_score \
                            FROM books \
                            LEFT JOIN reviews ON reviews.book_isbn = books.isbn \
                            WHERE books.isbn = :isbn \
                            GROUP BY isbn',
                           {'isbn': isbn}).fetchone()

    if book_data:
        book_data = dict(book_data)
        book_data['average_score'] = round(float(book_data['average_score'] or 0), 1)
        return jsonify(book_data)
    else:
        return jsonify({'error': 'Invalid book ISBN'}), 404
