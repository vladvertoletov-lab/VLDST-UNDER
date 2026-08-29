import hashlib,hmac,urllib.parse,json,time
from fastapi import Header,HTTPException
from .config import settings
def validate(init_data):
    if not init_data: raise HTTPException(401,"Откройте приложение через Telegram")
    q=dict(urllib.parse.parse_qsl(init_data,keep_blank_values=True)); received=q.pop("hash",None)
    if not received: raise HTTPException(401,"Invalid Telegram data")
    check="\n".join(f"{k}={q[k]}" for k in sorted(q))
    secret=hmac.new(b"WebAppData",settings.BOT_TOKEN.encode(),hashlib.sha256).digest()
    good=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(good,received): raise HTTPException(401,"Invalid Telegram signature")
    if "auth_date" in q and time.time()-int(q["auth_date"])>86400: raise HTTPException(401,"Expired Telegram data")
    return json.loads(q["user"])
async def telegram_user(x_telegram_init_data: str|None=Header(default=None)):
    return validate(x_telegram_init_data)
