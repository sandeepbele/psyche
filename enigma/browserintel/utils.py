import random

def check_compromised_email(email):
    if "compromised" in email:
        return True
    return False

def check_compromised_password(password_hash):
    if "compromised" in password_hash:
        return True
    return False