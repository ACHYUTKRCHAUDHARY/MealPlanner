from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth.security import current_user, passwords, dummy_hash, token
from app.core.errors import DomainError
from app.db.models import User
from app.db.session import session
from app.schemas import Credentials

router = APIRouter(prefix='/api/v1/auth', tags=['Authentication'])


def public(user):
    return {'id':user.id, 'email':user.email}


@router.post('/register', status_code=201)
def register(body: Credentials, db: Session = Depends(session)):
    user = User(email=body.email, password_hash=passwords.hash(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError('registration_failed', 'Unable to register this email. Try signing in.', 409)
    return {'access_token':token(user), 'token_type':'bearer', 'user':public(user)}


@router.post('/login')
def login(body: Credentials, db: Session = Depends(session)):
    user = db.scalar(select(User).where(User.email == body.email))
    valid = passwords.verify(body.password, user.password_hash if user else dummy_hash)
    if not user or not valid:
        raise DomainError('invalid_credentials', 'Email or password is incorrect.', 401)
    return {'access_token':token(user), 'token_type':'bearer', 'user':public(user)}


@router.get('/me')
def me(user: User = Depends(current_user)):
    return public(user)


@router.post('/logout', status_code=204)
def logout(user: User = Depends(current_user), db: Session = Depends(session)):
    db.execute(update(User).where(User.id == user.id).values(token_version=User.token_version + 1))
    db.commit()
