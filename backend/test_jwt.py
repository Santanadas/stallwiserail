import jwt
from datetime import datetime, timezone, timedelta

def test():
    payload = {
        "sub": "user_123",
        "exp": datetime.now(timezone.utc) + timedelta(days=180)
    }
    tok = jwt.encode(payload, "secret", algorithm="HS256")
    decoded = jwt.decode(tok, "secret", algorithms=["HS256"])
    print(decoded)

test()
