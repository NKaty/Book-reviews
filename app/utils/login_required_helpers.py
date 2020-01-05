from functools import wraps
from urllib.parse import urlsplit

from flask import session, redirect, request, url_for, flash


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            flash('You need to login first.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def is_safe_url(url):
    if url is None or url.strip() == '':
        return False
    url_next = urlsplit(url)
    url_base = urlsplit(request.host_url)
    if (url_next.netloc or url_next.scheme) and \
            url_next.netloc != url_base.netloc:
        return False
    return True
