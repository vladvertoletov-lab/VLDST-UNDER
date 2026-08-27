import hashlib, hmac, json, time

def test_telegram_hash_shape():
    bot = "token"
    secret = hmac.new(b"WebAppData", bot.encode(), hashlib.sha256).digest()
    data = f"auth_date={int(time.time())}\nuser={json.dumps({'id': 1})}"
    digest = hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()
    assert len(digest) == 64
