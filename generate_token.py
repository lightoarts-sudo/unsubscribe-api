import hmac
import hashlib
import csv
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-render")
BASE_URL = os.environ.get("BASE_URL", "https://your-app.onrender.com")

def make_token(email: str) -> str:
    return hmac.new(
        SECRET_KEY.encode(),
        email.lower().encode(),
        hashlib.sha256
    ).hexdigest()[:32]

def generate_unsubscribe_url(email: str) -> str:
    token = make_token(email)
    return f"{BASE_URL}/unsubscribe?email={email}&token={token}"

# 範例:批次產生
if __name__ == "__main__":
    emails = [
        "test1@example.com",
        "test2@example.com",
    ]
    for email in emails:
        url = generate_unsubscribe_url(email)
        print(f"{email} => {url}")
