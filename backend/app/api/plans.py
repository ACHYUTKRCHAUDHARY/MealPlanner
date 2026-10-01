from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.security import current_user
from app.db.session import session
from app.db.models import User, MealPlan, MealPlanItem, GroceryList, GroceryItem
from app.schemas import PlanRequest, PlanResponse, SavePlan, CheckedRequest, Quantity
from app.core.errors import DomainError
from app.services.planner import MealPlanner
from app.rag.retriever import catalog, retrieve
from app.ai.gemini import Gemini

router = APIRouter(prefix='/api/v1/plans', tags=['Plans'])


def owned(db, plan_id, user, lock=False):
    query = select(MealPlan).where(MealPlan.id == plan_id, MealPlan.user_id == user.id)
    if lock:
        query = query.with_for_update()
    plan = db.scalar(query)
    if not plan:
        raise DomainError('plan_not_found','Plan not found.',404)
    return plan


def store_result(db, plan, result):
    result.id, result.saved = plan.id, plan.saved
    plan.result = result.model_dump(mode='json')
    # Flush deletions before inserting rows with the same slot uniqueness keys.
    plan.items.clear()
    if plan.grocery:
        plan.grocery.items.clear()
    else:
        plan.grocery = GroceryList()
    db.flush()
    for meal in result.meals:
        plan.items.append(MealPlanItem(id=meal.id, recipe_id=meal.recipe_id, day=meal.day, meal_type=meal.meal_type, servings=plan.preferences['people']))
    plan.grocery.items = [GroceryItem(name=q.name, quantity=q.quantity, unit=q.unit) for q in result.grocery_items]
    db.commit()
    return result


@router.post('/generate', response_model=PlanResponse)
def generate(body: PlanRequest, user: User = Depends(current_user), db: Session = Depends(session)):
    if not {'pantry', 'pantry_quantities'} & body.model_fields_set:
        body.pantry_quantities = [Quantity(name=i.name, quantity=i.quantity, unit=i.unit) for i in user.pantry]
        body.pantry = [i.name for i in user.pantry]
    recipes = catalog(db)
    scores, mode = retrieve(db,body,recipes)
    result = MealPlanner(recipes).create(body,scores)
    result.retrieval_mode = mode
    if mode != 'pgvector':
        result.warnings.append('Semantic retrieval is inactive; hard-filtered deterministic selection was used.')
    result = Gemini().explain(result,body,recipes)
    plan = MealPlan(user_id=user.id, preferences=body.model_dump(mode='json'), result={}, saved=False)
    db.add(plan)
    db.flush()
    return store_result(db,plan,result)


@router.post('', response_model=PlanResponse)
def save(body: SavePlan, user: User = Depends(current_user), db: Session = Depends(session)):
    plan = owned(db,body.plan_id,user,True)
    result = PlanResponse.model_validate(plan.result)
    result.saved = plan.saved = True
    plan.result = result.model_dump(mode='json')
    db.commit()
    return result


@router.get('')
def history(user: User = Depends(current_user), db: Session = Depends(session), limit: int = Query(20,ge=1,le=100), offset: int = Query(0,ge=0)):
    plans = db.scalars(select(MealPlan).where(MealPlan.user_id==user.id,MealPlan.saved.is_(True)).order_by(MealPlan.created_at.desc()).limit(limit).offset(offset)).all()
    return [{'id':p.id,'created_at':p.created_at,'estimated_total':p.result['estimated_total'],'meal_count':len(p.result['meals'])} for p in plans]


@router.get('/{plan_id}', response_model=PlanResponse)
def get_plan(plan_id: str, user: User = Depends(current_user), db: Session = Depends(session)):
    return owned(db,plan_id,user).result


@router.delete('/{plan_id}', status_code=204)
def delete_plan(plan_id: str, user: User = Depends(current_user), db: Session = Depends(session)):
    db.delete(owned(db,plan_id,user,True))
    db.commit()


@router.post('/{plan_id}/items/{item_id}/swap', response_model=PlanResponse)
def swap(plan_id: str,item_id: str,user: User = Depends(current_user),db: Session = Depends(session)):
    plan = owned(db,plan_id,user,True)
    result = MealPlanner(catalog(db)).swap(PlanRequest.model_validate(plan.preferences),PlanResponse.model_validate(plan.result),item_id)
    return store_result(db,plan,result)


@router.get('/{plan_id}/groceries')
def groceries(plan_id: str,user: User = Depends(current_user),db: Session = Depends(session)):
    plan = owned(db,plan_id,user)
    return [{'id':i.id,'name':i.name,'quantity':i.quantity,'unit':i.unit,'checked':i.checked} for i in plan.grocery.items]


@router.patch('/{plan_id}/groceries/{item_id}')
def check_grocery(plan_id: str,item_id: str,body: CheckedRequest,user: User = Depends(current_user),db: Session = Depends(session)):
    plan = owned(db,plan_id,user,True)
    item = next((i for i in plan.grocery.items if i.id==item_id),None)
    if not item:
        raise DomainError('grocery_not_found','Grocery item not found.',404)
    item.checked = body.checked
    db.commit()
    return {'id':item.id,'checked':item.checked}
