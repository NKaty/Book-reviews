import requests

from app.application import app


def make_request_to_goodreads_api(isbn):
    try:
        goodreads_data = requests.get('https://www.goodreads.com/book/review_counts.json', params={
            'key': app.config['GOODREADS_KEY'],
            'isbns': isbn
        }).json()['books'][0]
    except Exception:
        goodreads_data = None
    else:
        if goodreads_data.get('average_rating') and goodreads_data.get('work_ratings_count'):
            goodreads_data = {
                'average_rating': goodreads_data['average_rating'],
                'ratings_count': goodreads_data['work_ratings_count']
            }
        else:
            goodreads_data = None

    return goodreads_data


def make_request_to_google_books_api(isbn):
    try:
        google_data = requests.get('https://www.googleapis.com/books/v1/volumes', params={
            'q': f'isbn:{isbn}'
        }).json()['items'][0]
    except Exception:
        rating_data = None
        desc_data = {
            'image': None,
            'description': None
        }
    else:
        if google_data['volumeInfo'].get('averageRating') and google_data['volumeInfo'].get('ratingsCount'):
            rating_data = {
                'average_rating': google_data['volumeInfo']['averageRating'],
                'ratings_count': google_data['volumeInfo']['ratingsCount']
            }
        else:
            rating_data = None

        desc_data = {}
        if google_data['volumeInfo'].get('imageLinks') and google_data['volumeInfo']['imageLinks'].get('thumbnail'):
            desc_data['image'] = google_data['volumeInfo']['imageLinks']['thumbnail']
        else:
            desc_data['image'] = None

        desc_data['description'] = google_data['volumeInfo'].get('description', None)

    return rating_data, desc_data
