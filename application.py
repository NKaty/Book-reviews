import os

from flask import Flask, session, redirect, request, render_template
from flask_session import Session
from functools import wraps
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
        return render_template('signup.html', error_message='All fields of the form must be filled in!')

    if len(username) < 2:
        return render_template('signup.html', error_message='Username must be at least 2 characters long!')

    if len(password) < 6:
        return render_template('signup.html', error_message='Password must be at least 6 characters long!')

    if password != conf_password:
        return render_template('signup.html', error_message='Passwords must match!')

    is_username_taken = db.execute('SELECT id FROM users WHERE username = :username', {'username': username}).fetchone()

    if is_username_taken:
        return render_template('signup.html',
                               error_message='That username is already taken. Please, choose another username!')

    db.execute('INSERT INTO users (username, password) VALUES (:username, :password)',
               {'username': username, 'password': generate_password_hash(password)})
    db.commit()

    user = db.execute('SELECT * FROM users WHERE username = :username', {'username': username}).fetchone()

    if user is None:
        return render_template('signup.html', error_message='An error occurred during registration. Please try again!')

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
        return render_template('login.html', error_message='All fields of the form must be filled in!')

    user = db.execute('SELECT * FROM users WHERE username = :username', {'username': username}).fetchone()

    if user is None or not check_password_hash(user.password, password):
        return render_template('login.html', error_message='Invalid password or username!')

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
        return render_template('search.html', error_message='Nothing has been found on your request!')

    return render_template("books.html", books=books)
