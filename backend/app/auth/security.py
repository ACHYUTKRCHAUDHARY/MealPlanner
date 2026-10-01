from datetime import datetime, timezone, timedelta
from uuid import uuid4
import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.errors import DomainError
from app.db.session import session
from app.db.models import User

passwords = PasswordHash.recommended()
dummy_hash = passwords.hash('timing-equalization-password-only')
bearer = HTTPBearer(auto_error=False)


def token(user: User) -> str:
    config = settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': user.id, 'ver': user.token_version, 'iat': now,
        'exp': now + timedelta(minutes=config.access_token_expire_minutes), 'jti': str(uuid4()),
        'iss': 'plateful', 'aud': 'plateful-web'}, config.jwt_secret, algorithm=config.jwt_algorithm)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(session)) -> User:
    if not credentials:
        raise DomainError('unauthorized', 'Please sign in.', 401)
    try:
        config = settings()
        claims = jwt.decode(credentials.credentials, config.jwt_secret, algorithms=[config.jwt_algorithm],
            audience='plateful-web', issuer='plateful', options={'require':['exp','iat','sub','ver','jti','iss','aud']})
        user = db.get(User, claims['sub'])
        if not user or claims['ver'] != user.token_version:
            raise ValueError('Revoked')
        return user
    except (jwt.PyJWTError, ValueError, TypeError):
        raise DomainError('unauthorized', 'Your session expired. Please sign in again.', 401)
