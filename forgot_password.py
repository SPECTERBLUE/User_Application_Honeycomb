from itsdangerous import URLSafeTimedSerializer

SECRET_KEY = "9iO2kT2q6j3KsPpR0QdE4sA9YH9wS3pM0o2FvH7lU1w="
serializer = URLSafeTimedSerializer(SECRET_KEY)

def generate_reset_token(email: str):
    return serializer.dumps(email, salt="password-reset")

def verify_reset_token(token: str, expiration=3600):
    try:
        email = serializer.loads(token, salt="password-reset", max_age=expiration)
        return email
    except Exception:
        return None
