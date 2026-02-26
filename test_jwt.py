import os
from datetime import datetime, timedelta
import jwt

SECRET_KEY = "super-secret-default-key-1234"
ALGORITHM = "HS256"
access_token_expires = timedelta(hours=24)
expire = datetime.utcnow() + access_token_expires

to_encode = {
    "sub": "1",
    "username": "admin",
    "role": "admin",
    "api_key": "some-api-key",
    "exp": expire,
}
encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
print(encoded_jwt)
