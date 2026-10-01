from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.auth.security import current_user
from app.db.models import User, UserPreference, PantryItem
from app.db.session import session
from app.schemas import PlanRequest, PantryRequest
from app.services.ingredients import normalize

router = APIRouter(prefix='/api/v1/users/me', tags=['Preferences and pantry'])


@router.get('/preferences')
def preferences(user: User = Depends(current_user)):
    return user.preferences.data if user.preferences else None


@router.put('/preferences', response_model=PlanRequest)
def put_preferences(body: PlanRequest,user: User = Depends(current_user),db: Session = Depends(session)):
    if not user.preferences:
        user.preferences = UserPreference(data={})
    user.preferences.data = body.model_dump(mode='json')
    db.commit()
    return body


@router.get('/pantry')
def pantry(user: User = Depends(current_user)):
    return {'items':[{'name':i.name,'quantity':i.quantity,'unit':i.unit} for i in user.pantry]}


@router.put('/pantry')
def put_pantry(body: PantryRequest,user: User = Depends(current_user),db: Session = Depends(session)):
    # Normalize aliases before checking duplicates too.
    from app.core.errors import DomainError
    names = [normalize(i.name) for i in body.items]
    if len(set(names)) != len(names):
        raise DomainError('invalid_pantry','Use one quantity per ingredient, including aliases.')
    user.pantry.clear()
    db.flush()
    user.pantry = [PantryItem(name=normalize(i.name),quantity=i.quantity,unit=i.unit) for i in body.items]
    db.commit()
    return pantry(user)
