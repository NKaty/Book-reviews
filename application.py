import os

from flask import Flask, session, redirect, request, render_template, url_for, flash
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


@app.route('/search', methods=['GET'])
@login_required
def search():
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
        books = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                            (UPPER(isbn) LIKE :isbn AND \
                            UPPER(title) LIKE :title AND \
                            UPPER(author) LIKE :author) ORDER BY title LIMIT 10",
                           {'isbn': query['isbn'],
                            'title': query['title'],
                            'author': query['author']
                            }).fetchall()
    else:
        books = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                            (UPPER(isbn) LIKE :isbn AND \
                            UPPER(title) LIKE :title AND \
                            UPPER(author) LIKE :author AND \
                            year = :year) ORDER BY title LIMIT 10",
                           {'isbn': query['isbn'],
                            'title': query['title'],
                            'author': query['author'],
                            'year': query['year']
                            }).fetchall()

    if not len(books):
        flash('Nothing has been found on your request!')
        return render_template('search.html')

    return render_template("books.html", books=books)


@app.route('/book/<isbn>', methods=['GET', 'POST'])
@login_required
def book(isbn):
    if request.method == 'GET':
        book_data = db.execute("SELECT isbn, title, author, year, \
                                reviews.rating, reviews.comment, \
                                TO_CHAR(reviews.created_on, 'DD/MM/YYYY HH24:MI:SS') as created_on, \
                                users.username \
                                FROM books \
                                INNER JOIN reviews ON reviews.book_isbn = books.isbn \
                                INNER JOIN users ON users.id = reviews.user_id \
                                WHERE books.isbn = :isbn \
                                ORDER by created_on DESC",
                               {"isbn": isbn}).fetchall()

        # request to Goodreads API
        print(book_data)
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
