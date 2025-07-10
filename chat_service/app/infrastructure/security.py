import datetime
import secrets
from typing import Optional

import jwt  # Import PyJWT
from jwt import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext


class SecurityService:
    def __init__(self, config):
        self.config = config
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    def create_access_token(
        self, data: dict, expires_delta: Optional[datetime.timedelta] = None
    ):
        to_encode = data.copy()
        to_encode.update({"nonce": secrets.token_hex(8)})  # Add a random nonce
        if expires_delta:
            expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
        else:
            expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                minutes=15
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, self.config.SECRET_KEY, algorithm=self.config.ALGORITHM
        )
        return encoded_jwt, expire

    def create_refresh_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            days=self.config.REFRESH_TOKEN_EXPIRE_DAYS
        )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, self.config.REFRESH_SECRET_KEY, algorithm=self.config.ALGORITHM
        )
        return encoded_jwt, expire

    def decode_access_token(self, token: str):
        try:
            payload = jwt.decode(
                token, self.config.SECRET_KEY, algorithms=[self.config.ALGORITHM]
            )
            username: str = payload.get("sub")
            if username is None:
                return None
            return username
        except (ExpiredSignatureError, InvalidTokenError):
            return None

    def decode_refresh_token(self, token: str):
        try:
            payload = jwt.decode(
                token,
                self.config.REFRESH_SECRET_KEY,
                algorithms=[self.config.ALGORITHM],
            )
            username: str = payload.get("sub")
            if username is None:
                return None
            return username
        except (ExpiredSignatureError, InvalidTokenError):
            return None
