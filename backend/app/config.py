import os
from dotenv import load_dotenv
load_dotenv()
ENV = os.getenv('APP_ENV', 'development')
SECRET = os.getenv('APP_SECRET', 'development-only-change-this-secret')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./escape.db')
PUBLIC_URL = os.getenv('PUBLIC_URL', 'http://localhost:8000').rstrip('/')
OTP_MODE = os.getenv('OTP_MODE', 'console')
# Edit these three values before running the owner dashboard.
OWNER_EMAIL = os.getenv('OWNER_EMAIL', 'sjagadish89772@gmail.com').strip().lower()
OWNER_PHONE = os.getenv('OWNER_PHONE', '+919148858149').strip()
OWNER_PASSWORD = os.getenv('OWNER_PASSWORD', 'Jaggu_@_123')
OWNER_USER_ID = os.getenv('OWNER_USER_ID', 'sjaggu89772').strip()
if ENV == 'production':
    if len(SECRET) < 32 or SECRET.startswith('development'):
        raise RuntimeError('Set a random APP_SECRET of at least 32 characters')
    if OWNER_PASSWORD == 'CHANGE_THIS_OWNER_PASSWORD' or len(OWNER_PASSWORD) < 8:
        raise RuntimeError('Set a real OWNER_PASSWORD in backend/app/config.py')
    if not all(os.getenv(key) for key in ('OWNER_EMAIL','OWNER_PHONE','OWNER_PASSWORD','OWNER_USER_ID')):
        raise RuntimeError('Set OWNER_EMAIL, OWNER_PHONE, OWNER_PASSWORD and OWNER_USER_ID in hosting secrets')
    if OTP_MODE != 'live' or not DATABASE_URL.startswith('postgresql') or not PUBLIC_URL.startswith('https://'):
        raise RuntimeError('Production requires live OTP, PostgreSQL and an HTTPS PUBLIC_URL')
