import json
from copy import deepcopy
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.schemas import PlanRequest, Quantity
from app.services.planner import MealPlanner, eligible, plan_cost
from app.services.ingredients import aggregate
from app.core.errors import DomainError

RECIPES=json.loads((Path(__file__).parents[1] / 'app/data/recipes.json').read_text())


def request(**kwargs):
    values=dict(days=['Monday','Tuesday'],budget=1500,people=2,goals=['protein'],diet='vegan',appliances=['stove','pressure-cooker'])
    return PlanRequest(**(values|kwargs))


@pytest.mark.parametrize('diet',['vegetarian','vegan','eggetarian'])
def test_diet(diet):
    plan=MealPlanner(RECIPES).create(request(diet=diet))
    assert len(plan.meals)==2
    for meal in plan.meals:
        recipe=next(r for r in RECIPES if r['id']==meal.recipe_id)
        assert ('vegetarian' if diet=='eggetarian' else diet) in recipe['diet']


@pytest.mark.parametrize('allergy,ingredient',[('dairy','Milk'),('peanuts','Groundnut'),('tree nuts','Cashew'),('gluten','Atta'),('soy','Tofu'),('egg','Egg')])
def test_allergy_inference(allergy,ingredient):
    recipe=deepcopy(RECIPES[0]);recipe['ingredients'].append({'name':ingredient,'quantity':1,'unit':'count'})
    assert not eligible(recipe,request(allergies=[allergy]))


def test_no_unsafe_fallback():
    with pytest.raises(DomainError,match='No recipes'):
        MealPlanner([RECIPES[1]]).create(request())


def test_all_appliances_required():
    assert not eligible(RECIPES[2],request(appliances=['stove']))
    assert eligible(RECIPES[2],request())


def test_exclusions_and_unreviewed():
    assert not eligible(RECIPES[2],request(exclusions=['onion']))
    recipe=deepcopy(RECIPES[0]);recipe['allergen_reviewed']=False
    assert not eligible(recipe,request(allergies=['egg']))


def test_pantry_preference():
    plan=MealPlanner(RECIPES).create(request(days=['Monday'],pantry=['soya granules','whole wheat wraps']))
    assert plan.meals[0].name=='Soya Keema Wrap'


def test_budget_feasible_and_infeasible():
    plan=MealPlanner(RECIPES).create(request(budget=170))
    assert plan.estimated_total<=170
    with pytest.raises(DomainError) as error:
        MealPlanner(RECIPES).create(request(budget=169))
    assert error.value.code=='budget_infeasible'


def test_aggregate_duplicates_scale_and_units():
    recipes=[{'servings':2,'ingredients':[{'name':'rice','quantity':300,'unit':'g'},{'name':'rice','quantity':.4,'unit':'kg'},{'name':'rice','quantity':2,'unit':'count'}]}]
    quantities=aggregate(recipes,4,[Quantity(name='rice',quantity=.5,unit='kg')])
    assert {(q.name,q.unit):q.quantity for q in quantities}=={('rice','g'):900,('rice','count'):4}


def test_unknown_pantry_does_not_subtract():
    quantities=aggregate([RECIPES[2]],2,[Quantity(name='rice')])
    assert next(q.quantity for q in quantities if q.name=='rice')==400


def test_pantry_priced_budget():
    recipe={'servings':1,'cost':100,'ingredients':[{'name':'rice','quantity':100,'unit':'g','unit_cost':1}]}
    assert plan_cost([recipe],request(people=1,pantry_quantities=[Quantity(name='rice',quantity=50,unit='g')]))==50


def test_multiple_types_and_totals():
    plan=MealPlanner(RECIPES).create(request(meal_types=['breakfast','dinner']))
    assert len(plan.meals)==4
    assert plan.nutrition_totals['weekly']['calories']==sum(m.calories*2 for m in plan.meals)
    assert plan.nutrition_totals['weekly']['fat'] is None


def test_swap():
    planner=MealPlanner(RECIPES);body=request();plan=planner.create(body)
    old=plan.meals[0].recipe_id
    swapped=planner.swap(body,plan,plan.meals[0].id)
    assert swapped.meals[0].recipe_id!=old
    assert swapped.estimated_total<=body.budget
    assert swapped.groceries!=plan.groceries


def test_empty_and_invalid():
    with pytest.raises(DomainError):MealPlanner([]).create(request())
    for kwargs in ({'days':[]},{'days':['Monday','Monday']},{'people':0},{'budget':-1},{'allergies':['unknown']},{'meal_types':[]}):
        with pytest.raises(ValidationError):request(**kwargs)
