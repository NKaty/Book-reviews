import os

from flask import Flask, session, redirect, request, render_template
from flask_session import Session
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
    return 'Project 1: TODO'


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    session.clear()

    if request.method == 'GET':
        return render_template('signup.html')

    username = request.form.get('username')
    password = request.form.get('password')
    conf_password = request.form.get('conf_password')

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
               {'username': username, password: generate_password_hash(password)})
    db.commit()

    user = db.execute('SELECT * FROM users WHERE username = :username', {'username': username}).fetchone()

    if user is None:
        return render_template('signup.html', error_message='An error occurred during registration. Please try again!')

    session['user_id'] = user.id
    session['username'] = user.username

    redirect('/search')


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

    redirect('/search')


@app.route('/logout')
def logout():
    session.clear()
    redirect('/')
