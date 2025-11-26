from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def hash_password(raw_password):
    """هش کردن رمز عبور"""
    return bcrypt.generate_password_hash(raw_password).decode('utf-8')

def check_password(hashed_password, raw_password):
    """بررسی تطابق رمز عبور"""
    try:
        return bcrypt.check_password_hash(hashed_password, raw_password)
    except Exception:
        return False