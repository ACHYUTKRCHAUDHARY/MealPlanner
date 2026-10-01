from datetime import datetime, timezone, timedelta
import hashlib
import secrets
from fastapi import APIRouter, Depends
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth.security import current_user, passwords, dummy_hash, token
from app.core.config import settings
from app.core.errors import DomainError
from app.db.models import User, AccountToken
from app.db.session import session
from app.schemas import Credentials, EmailOnly

router = APIRouter(prefix='/api/v1/auth', tags=['Authentication'])


def public(user):
    return {'id': user.id, 'email': user.email, 'email_verified': user.email_verified}


def _create_account_token(db: Session, user_id: str, purpose: str, expire_minutes: int = 30) -> str:
    """Create a single-use, expiring token. Returns the raw token; only its hash is stored."""
    # Clean up expired/used tokens for this user and purpose.
    db.execute(delete(AccountToken).where(
        AccountToken.user_id == user_id, AccountToken.purpose == purpose,
        (AccountToken.used.is_(True)) | (AccountToken.expires_at < datetime.now(timezone.utc))))
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    db.add(AccountToken(user_id=user_id, token_hash=token_hash, purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)))
    db.commit()
    return raw


def _verify_account_token(db: Session, raw_token: str, purpose: str) -> AccountToken | None:
    """Validate and consume a single-use token. Returns the token row or None."""
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    row = db.scalar(select(AccountToken).where(
        AccountToken.token_hash == token_hash, AccountToken.purpose == purpose,
        AccountToken.used.is_(False), AccountToken.expires_at > datetime.now(timezone.utc)))
    if row:
        row.used = True
        db.commit()
    return row


@router.post('/register', status_code=201)
def register(body: Credentials, db: Session = Depends(session)):
    user = User(email=body.email, password_hash=passwords.hash(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError('registration_failed', 'Unable to register this email. Try signing in.', 409)
    return {'access_token': token(user), 'token_type': 'bearer', 'user': public(user)}


@router.post('/login')
def login(body: Credentials, db: Session = Depends(session)):
    user = db.scalar(select(User).where(User.email == body.email))
    valid = passwords.verify(body.password, user.password_hash if user else dummy_hash)
    if not user or not valid:
        raise DomainError('invalid_credentials', 'Email or password is incorrect.', 401)
    return {'access_token': token(user), 'token_type': 'bearer', 'user': public(user)}


@router.get('/me')
def me(user: User = Depends(current_user)):
    return public(user)


@router.post('/logout', status_code=204)
def logout(user: User = Depends(current_user), db: Session = Depends(session)):
    db.execute(update(User).where(User.id == user.id).values(token_version=User.token_version + 1))
    db.commit()


@router.post('/request-password-reset')
def request_password_reset(body: EmailOnly, db: Session = Depends(session)):
    """Generate a password reset token. The token is returned directly because no email
    provider is configured. In production, this would send an email instead. The password
    field in the request body is ignored; only the email is used for lookup."""
    user = db.scalar(select(User).where(User.email == body.email))
    if not user:
        # Do not reveal whether the email exists — return a generic success message.
        return {'message': 'If an account with that email exists, a reset token has been created.'}
    raw = _create_account_token(db, user.id, 'password_reset', expire_minutes=30)
    # In a real deployment, send `raw` via email. Never log it.
    return {'message': 'If an account with that email exists, a reset token has been created.',
            '_dev_token': raw if settings().environment != 'production' else None}


@router.post('/reset-password')
def reset_password(body: dict, db: Session = Depends(session)):
    """Reset password using a single-use token. Body: {token, new_password}."""
    raw_token = body.get('token', '')
    new_password = body.get('new_password', '')
    if not raw_token or not new_password or len(new_password) < 12 or len(new_password) > 128:
        raise DomainError('validation_error', 'Provide a valid token and a password between 12 and 128 characters.')
    account_token = _verify_account_token(db, raw_token, 'password_reset')
    if not account_token:
        raise DomainError('invalid_token', 'This reset link has expired or was already used. Request a new one.', 400)
    user = db.get(User, account_token.user_id)
    if not user:
        raise DomainError('invalid_token', 'Account not found.', 400)
    user.password_hash = passwords.hash(new_password)
    user.token_version += 1  # Revoke all existing sessions.
    db.commit()
    return {'message': 'Password has been reset. Please sign in with your new password.'}


@router.post('/send-verification')
def send_verification(user: User = Depends(current_user), db: Session = Depends(session)):
    """Create an email verification token. In production, this would be emailed."""
    if user.email_verified:
        return {'message': 'Email is already verified.'}
    raw = _create_account_token(db, user.id, 'email_verify', expire_minutes=60)
    return {'message': 'Verification token created.',
            '_dev_token': raw if settings().environment != 'production' else None}


@router.post('/verify-email')
def verify_email(body: dict, db: Session = Depends(session)):
    """Verify email using a single-use token. Body: {token}."""
    raw_token = body.get('token', '')
    if not raw_token:
        raise DomainError('validation_error', 'Provide a verification token.')
    account_token = _verify_account_token(db, raw_token, 'email_verify')
    if not account_token:
        raise DomainError('invalid_token', 'This verification link has expired or was already used.', 400)
    user = db.get(User, account_token.user_id)
    if not user:
        raise DomainError('invalid_token', 'Account not found.', 400)
    user.email_verified = True
    db.commit()
    return {'message': 'Email verified successfully.'}


@router.delete('/account', status_code=204)
def delete_account(user: User = Depends(current_user), db: Session = Depends(session)):
    """Permanently delete the authenticated user's account and all owned data.
    Cascading foreign keys handle plans, preferences, pantry and tokens."""
    db.delete(user)
    db.commit()

