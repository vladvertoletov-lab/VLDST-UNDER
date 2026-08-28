import hashlib, hmac, json, time, jwt
from urllib.parse import parse_qsl
from .config import settings

def verify_telegram_init_data(init_data: str, max_age=86400):
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received = pairs.pop("hash", None)
    if not received:
        raise ValueError("Missing Telegram hash")
    auth_date = int(pairs.get("auth_date","0"))
    if not auth_date or time.time() - auth_date > max_age:
        raise ValueError("Expired Telegram initData")
    data_check = "\n".join(f"{k}={v}" for k,v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise ValueError("Invalid Telegram signature")
    user = json.loads(pairs["user"])
    user["_start_param"] = pairs.get("start_param") or pairs.get("startapp")
    return user

def make_token(user_id: int, session_version: int = 1):
    return jwt.encode({"sub": str(user_id), "sv": int(session_version), "exp": int(time.time())+86400}, settings.secret_key, algorithm="HS256")

def read_token(token: str):
    data = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    return {"uid": int(data["sub"]), "sv": int(data.get("sv", 1))}
