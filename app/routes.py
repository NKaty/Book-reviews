import math

from flask import session, redirect, request, render_template, url_for, flash, jsonify, abort
import requests
from werkzeug.security import check_password_hash, generate_password_hash

from app.application import app, db
from app.utils.pagination import get_pagination
from app.utils.login_required_helpers import login_required
from app.utils.login_user import login_user
from app.utils.check_signup_form import check_signup_form


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('user_id'):
        return redirect(url_for('search_form'))

    if request.method == 'GET':
        return render_template('signup.html')

    username = request.form.get('username')
    password = request.form.get('password')
    conf_password = request.form.get('conf-password')

    if len(error_messages := check_signup_form(username, password, conf_password)):
        flash(' '.join(error_messages), 'danger')
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

    next_url = login_user(session, user)

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

    next_url = login_user(session, user)

    flash('You were logged in.', 'success')
    return redirect(next_url or url_for('search_form'))


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You were logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/search-form', methods=['GET'])
def search_form():
    return render_template("search.html")


@app.route('/search/', defaults={'page': 1}, methods=['GET'])
@app.route('/search/<int:page>', methods=['GET'])
def search(page):
    per_page = 20
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


@app.route('/book/<string:isbn>', defaults={'page': 1}, methods=['GET'])
@app.route('/book/<string:isbn>/<int:page>', methods=['GET'])
@login_required
def book(isbn, page):
    per_page = 10
    offset = ((page - 1) * per_page)
    neighbours_number = 1

    book_data = db.execute("SELECT isbn, title, author, year, \
                                reviews.rating, reviews.comment, \
                                TO_CHAR(reviews.created_on, 'DD/MM/YYYY HH24:MI:SS') as created_on, \
                                users.username \
                                FROM books \
                                LEFT JOIN reviews ON reviews.book_isbn = books.isbn \
                                LEFT JOIN users ON users.id = reviews.user_id \
                                WHERE books.isbn = :isbn \
                                ORDER by created_on DESC OFFSET :offset LIMIT :per_page",
                           {'isbn': isbn,
                            'offset': offset,
                            'per_page': per_page
                            }).fetchall()

    if len(book_data):
        book_reviews = db.execute("SELECT COUNT(reviews.id) as ratings_count, \
                                        ROUND(AVG(reviews.rating), 2) as average_rating \
                                        FROM books \
                                        LEFT JOIN reviews ON reviews.book_isbn = books.isbn \
                                        WHERE books.isbn = :isbn",
                                  {'isbn': isbn}).fetchone()

        for i in range(len(book_data)):
            book_data[i] = dict(book_data[i])
            if book_data[i]['created_on'] is not None:
                book_data[i]['created_on'] = book_data[i]['created_on'].split(' ')

        rating_data = {'books': dict(book_reviews)}
        rating_data['books']['average_rating'] = rating_data['books']['average_rating'] or 0

        # request to Goodreads API
        try:
            rating_data['goodreads'] = requests.get('https://www.goodreads.com/book/review_counts.json', params={
                'key': app.config['GOODREADS_KEY'],
                'isbns': isbn
            }).json()['books'][0]
        except Exception:
            flash('Unfortunately we cannot get information from goodreads.com.', 'warning')
            rating_data['goodreads'] = None

        # request to Google API
        try:
            book_id = requests.get('https://www.googleapis.com/books/v1/volumes', params={
                'q': f'isbn:{isbn}'
            }).json()['items'][0]['id']
            google_data = requests.get(f'https://www.googleapis.com/books/v1/volumes/{book_id}').json()
        except Exception:
            flash('Unfortunately we cannot get information from Google Books API.', 'warning')
            rating_data['google'] = None
            desc_data = None
        else:
            rating_data['google'] = {
                'average_rating': google_data['volumeInfo']['averageRating'],
                'ratings_count': google_data['volumeInfo']['ratingsCount']
            }
            desc_data = {
                'image': google_data['volumeInfo']['imageLinks']['thumbnail'],
                'description': google_data['volumeInfo']['description']
            }

    else:
        return abort(404)

    pages = int(math.ceil(book_reviews['ratings_count'] / per_page))

    pagination = {'pages': pages,
                  'items': get_pagination(page, pages, neighbours_number),
                  'page': page,
                  'neighbours_number': neighbours_number}

    return render_template('book.html', book_data=book_data, rating_data=rating_data, desc_data=desc_data,
                           pagination=pagination)


@app.route('/book/<string:isbn>', methods=['POST'])
@login_required
def create_review(isbn):
    rating = request.form.get('rating')
    comment = request.form.get('comment')

    if rating is None:
        flash('You must provide your rating for the book!', 'danger')
        return redirect(url_for('book', isbn=isbn))

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


@app.route("/api/<string:isbn>", methods=['GET'])
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
        book_data['average_score'] = round(float(book_data['average_score'] or 0), 2)
        return jsonify(book_data)
    else:
        return jsonify({'error': 'Invalid book ISBN'}), 404
