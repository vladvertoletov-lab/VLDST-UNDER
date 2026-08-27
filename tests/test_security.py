import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.config import settings
from app.security import verify_telegram_init_data


def telegram_hash(bot_token: str, data_check: str) -> str:
    # Telegram Mini Apps: secret_key = HMAC-SHA256(key=WebAppData, msg=bot_token)
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()


def test_telegram_hash_shape():
    digest = telegram_hash("token", 'auth_date=1700000000\nuser={"id":1}')
    assert len(digest) == 64


def test_telegram_init_data_verification(monkeypatch):
    bot_token = "123456:TEST_TOKEN"
    monkeypatch.setattr(settings, "bot_token", bot_token)
    payload = {
        "auth_date": str(int(time.time())),
        "query_id": "AAEAAAE",
        "user": json.dumps({"id": 123, "first_name": "VLDST", "username": "tester"}, separators=(",", ":")),
        "start_param": "ref_ABC123",
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    init_data = urlencode({**payload, "hash": telegram_hash(bot_token, data_check)})

    user = verify_telegram_init_data(init_data)
    assert user["id"] == 123
    assert user["username"] == "tester"
    assert user["_start_param"] == "ref_ABC123"


def test_telegram_init_data_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr(settings, "bot_token", "123456:TEST_TOKEN")
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": 123}, separators=(",", ":")),
        "hash": "0" * 64,
    }
    with pytest.raises(ValueError, match="Invalid Telegram signature"):
        verify_telegram_init_data(urlencode(payload))
