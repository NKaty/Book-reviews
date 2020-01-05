from app.utils.login_required_helpers import is_safe_url


def login_user(session, user):
    session['user_id'] = user.id
    session['username'] = user.username
    next_url = session.get('next_url')
    session['next_url'] = None

    if not is_safe_url(next_url):
        next_url = None

    return next_url
