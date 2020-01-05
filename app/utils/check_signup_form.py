def check_signup_form(username, password, conf_password):
    messages = []

    if not username or not password or not conf_password:
        messages.append('All fields of the form must be filled in!')

    if len(username) < 2:
        messages.append('Username must be at least 2 characters long!')

    if len(password) < 6:
        messages.append('Password must be at least 6 characters long!')

    if password != conf_password:
        messages.append('Passwords must match!')

    return messages
