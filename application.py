import math
import os

from flask import Flask, session, redirect, request, render_template, url_for, flash, jsonify, abort
from flask_session import Session
from functools import wraps
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from urllib.parse import urlsplit
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


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


@app.route('/')
def index():
    return render_template("index.html")


def is_safe_url(url):
    if url is None or url.strip() == '':
        return False
    url_next = urlsplit(url)
    url_base = urlsplit(request.host_url)
    if (url_next.netloc or url_next.scheme) and \
            url_next.netloc != url_base.netloc:
        return False
    return True


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('user_id'):
        return redirect(url_for('search_form'))

    if request.method == 'GET':
        return render_template('signup.html')

    username = request.form.get('username')
    password = request.form.get('password')
    conf_password = request.form.get('conf-password')

    if not username or not password or not conf_password:
        flash('All fields of the form must be filled in!', 'danger')
        return render_template('signup.html')

    if len(username) < 2:
        flash('Username must be at least 2 characters long!', 'danger')
        return render_template('signup.html')

    if len(password) < 6:
        flash('Password must be at least 6 characters long!', 'danger')
        return render_template('signup.html')

    if password != conf_password:
        flash('Passwords must match!', 'danger')
        return render_template('signup.html')

    user = db.execute('INSERT INTO users (username, password) \
                        VALUES (:username, :password) \
                        ON CONFLICT ON CONSTRAINT users_username_key \
                        DO NOTHING \
                        RETURNING id, username',
                      {'username': username, 'password': generate_password_hash(password)}).fetchone()
    db.commit()

    if user is None:
        flash('That username is already taken. Please, choose another username!', 'danger')
        return render_template('signup.html')

    session['user_id'] = user.id
    session['username'] = user.username
    next_url = session.get('next_url')
    session['next_url'] = None

    if not is_safe_url(next_url):
        next_url = None

    flash('Congratulations, you are now a registered user!', 'success')
    return redirect(next_url or url_for('search_form'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('search_form'))

    if request.method == 'GET':
        session['next_url'] = request.args.get('next')
        return render_template('login.html')

    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('All fields of the form must be filled in!', 'danger')
        return render_template('login.html')

    user = db.execute('SELECT * FROM users WHERE username = :username', {'username': username}).fetchone()

    if user is None or not check_password_hash(user.password, password):
        flash('Invalid password or username!', 'danger')
        return render_template('login.html')

    session['user_id'] = user.id
    session['username'] = user.username
    next_url = session.get('next_url')
    session['next_url'] = None

    if not is_safe_url(next_url):
        next_url = None

    flash('You were logged in.', 'success')
    return redirect(next_url or url_for('search_form'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            flash('You need to login first.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You were logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/search-form', methods=['GET'])
def search_form():
    return render_template("search.html")


def get_pagination(page, total, neighbours_number):
    arrow_block_len = neighbours_number * 2 + 3
    pagination_len = arrow_block_len + 2
    if pagination_len >= total:
        return list(range(1, total + 1))

    start_page = max(2, page - neighbours_number)
    end_page = min(total - 1, page + neighbours_number)
    pages = list(range(start_page, end_page + 1))
    to_fill = arrow_block_len - len(pages) - 1

    if start_page > 2 and total - end_page > 1:
        pages = ['&laquo;'] + pages + ['&raquo;']
    elif start_page > 2:
        pages = ['&laquo;'] + list(range(start_page - to_fill, start_page)) + pages
    else:
        pages = pages + list(range(end_page + 1, end_page + to_fill + 1)) + ['&raquo;']

    return [1] + pages + [total]


@app.route('/search/', defaults={'page': 1}, methods=['GET'])
@app.route('/search/<int:page>', methods=['GET'])
def search(page):
    per_page = 10
    offset = ((page - 1) * per_page)
    neighbours_number = 1

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

    if query['year'] is None:
        total = db.execute('SELECT COUNT(*) FROM books WHERE \
                            (UPPER(isbn) LIKE :isbn AND \
                            UPPER(title) LIKE :title AND \
                            UPPER(author) LIKE :author)',
                           {'isbn': query['isbn'],
                            'title': query['title'],
                            'author': query['author']
                            }).fetchone()[0]

        if not total:
            flash('Nothing has been found on your request!', 'warning')
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

    else:
        total = db.execute('SELECT COUNT(*) FROM books WHERE \
                            (UPPER(isbn) LIKE :isbn AND \
                            UPPER(title) LIKE :title AND \
                            UPPER(author) LIKE :author AND \
                            year = :year)',
                           {'isbn': query['isbn'],
                            'title': query['title'],
                            'author': query['author'],
                            'year': query['year']
                            }).fetchone()[0]

        if not total:
            flash('Nothing has been found on your request!', 'warning')
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

    if not len(books):
        return abort(404)

    pages = int(math.ceil(total / per_page))

    pagination = {'pages': pages,
                  'items': get_pagination(page, pages, neighbours_number),
                  'page': page,
                  'neighbours_number': neighbours_number}

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
                flash('Unfortunately we cannot get information from goodreads.com.', 'warning')
                rating_data = None

        else:
            return abort(404)

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
        flash('You have already submitted a review for this book.', 'danger')

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
