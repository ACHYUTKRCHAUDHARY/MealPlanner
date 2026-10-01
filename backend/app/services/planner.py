from collections import Counter
from uuid import uuid4
from app.core.errors import DomainError
from app.schemas import Meal, PlanRequest, PlanResponse
from app.services.ingredients import aggregate, detected_allergens, normalize, display


def eligible(recipe: dict, request: PlanRequest) -> bool:
    diet = request.diet.value
    allowed_diets = {'vegetarian', 'eggetarian'} if diet == 'eggetarian' else {diet}
    if diet != 'none' and not allowed_diets.intersection(recipe['diet']):
        return False
    if not any(set(option) <= set(request.appliances) for option in recipe['appliance_options']):
        return False
    if request.allergies and not recipe.get('allergen_reviewed', False):
        return False
    allergens = set(recipe.get('allergens', [])) | detected_allergens(recipe['ingredients'])
    if allergens & set(request.allergies):
        return False
    ingredients = [normalize(i['name']) for i in recipe['ingredients']]
    if any(normalize(x) in ingredient for x in request.exclusions for ingredient in ingredients):
        return False
    return True


def recipe_cost(recipe: dict, people: int) -> float:
    return round(recipe['cost'] * people / recipe['servings'], 2)


def plan_cost(recipes: list[dict], request: PlanRequest) -> float:
    # If ingredient prices are complete, use remaining purchases after pantry subtraction.
    # Never fabricate discounts from a pantry name or an unpriced ingredient.
    prices = {}
    for recipe in recipes:
        for i in recipe['ingredients']:
            if i.get('unit_cost') is None:
                return round(sum(recipe_cost(r, request.people) for r in recipes), 2)
            from app.services.ingredients import canonical
            factor, unit = canonical(1, i['unit'])
            key = (normalize(i['name']), unit)
            prices[key] = max(prices.get(key, 0), i['unit_cost'] / factor)
    return round(sum(q.quantity * prices[(q.name, q.unit)] for q in aggregate(recipes, request.people, request.pantry_quantities)), 2)


class MealPlanner:
    def __init__(self, recipes: list[dict]):
        self.recipes = recipes

    def create(self, request: PlanRequest, semantic_scores: dict | None = None) -> PlanResponse:
        candidates = [r for r in self.recipes if eligible(r, request)]
        slots = [(day, kind) for day in request.days for kind in request.meal_types]
        options = [[r for r in candidates if kind in r['meal_types']] for _, kind in slots]
        if any(not group for group in options):
            raise DomainError('no_matching_meal', 'No recipes match every selected meal type, diet, allergy and appliance requirement. Change a non-safety preference or import more reviewed recipes.')
        # Keep a feasible baseline from the entire safe catalog, not only vector top-k.
        chosen = [min(group, key=lambda r: recipe_cost(r, request.people)) for group in options]
        minimum = plan_cost(chosen, request)
        if minimum > request.budget:
            # With ingredient-level pantry discounts the objective is non-additive; avoid
            # claiming global infeasibility from a greedy baseline.
            complete_prices = all(i.get('unit_cost') is not None for r in candidates for i in r['ingredients'])
            if complete_prices:
                chosen = self._feasible_search(options, request)
            else:
                raise DomainError('budget_infeasible', f'The lowest estimated cost is ₹{minimum:.2f}; requested budget is ₹{request.budget:.2f}. Reduce servings or meal slots, or increase the budget.')
        used = Counter(r['id'] for r in chosen)
        pantry = {normalize(x) for x in request.pantry} | {normalize(q.name) for q in request.pantry_quantities}
        scores = semantic_scores or {}
        for index, group in enumerate(options):
            used[chosen[index]['id']] -= 1
            def score(r):
                return (3 * len(set(r['goals']) & set(request.goals))
                        + 2 * len({normalize(i['name']) for i in r['ingredients']} & pantry)
                        + scores.get(r['id'], 0) - 4 * used[r['id']]
                        + (1 if r.get('cuisine', '').casefold() == request.cuisine.casefold() else 0))
            for recipe in sorted(group, key=lambda r: (-score(r), recipe_cost(r, request.people))):
                trial = chosen.copy()
                trial[index] = recipe
                if plan_cost(trial, request) <= request.budget:
                    chosen = trial
                    break
            used[chosen[index]['id']] += 1
        return self.response(request, slots, chosen)

    def _feasible_search(self, options, request):
        # Bounded exact search for non-additive pantry pricing. Do not silently report
        # infeasibility if the search limit is reached.
        from itertools import product
        for index, combination in enumerate(product(*options)):
            if index >= 100000:
                raise DomainError('budget_search_limit', 'Could not establish a feasible plan within the search limit. Reduce days or meal types, or increase budget.')
            if plan_cost(list(combination), request) <= request.budget:
                return list(combination)
        raise DomainError('budget_infeasible', 'No combination in the safe catalog meets this budget.')

    def response(self, request, slots, chosen, item_ids=None) -> PlanResponse:
        meals = []
        totals = {}
        for index, ((day, kind), recipe) in enumerate(zip(slots, chosen)):
            ingredients = aggregate([recipe], request.people, [])
            meals.append(Meal(id=item_ids[index] if item_ids else str(uuid4()), recipe_id=recipe['id'], day=day,
                meal_type=kind, name=recipe['name'], time_minutes=recipe['time_minutes'],
                estimated_cost=recipe_cost(recipe, request.people), calories=recipe.get('calories'),
                protein_grams=recipe.get('protein_grams'), ingredients={q.name: display(q.quantity,q.unit) for q in ingredients},
                instructions=recipe.get('instructions', [])))
            daily = totals.setdefault(day, {'calories': 0, 'protein_grams': 0, 'carbohydrates': 0, 'fat': 0, 'fiber': 0})
            for key in daily:
                value = recipe.get(key)
                daily[key] = None if daily[key] is None or value is None else round(daily[key] + value * request.people, 2)
        weekly = {key: None if any(d[key] is None for d in totals.values()) else sum(d[key] for d in totals.values()) for key in next(iter(totals.values()))}
        groceries = aggregate(chosen, request.people, request.pantry_quantities)
        cost = plan_cost(chosen, request)
        warnings = ['Nutrition and cost are stored estimates, not independently verified. Totals cover selected meals only; daily/weekly totals include all people.',
                    'Check packaged ingredient labels and preparation cross-contact for allergies.']
        if any(i.get('unit_cost') is None for r in chosen for i in r['ingredients']):
            warnings.append('Ingredient prices are unavailable: budget uses conservative whole-recipe estimates without pantry discounts.')
        return PlanResponse(meals=meals, groceries={q.name + (' (' + q.unit + ')' if sum(x.name == q.name for x in groceries)>1 else ''): display(q.quantity,q.unit) for q in groceries}, grocery_items=groceries,
            estimated_total=cost, budget_remaining=round(request.budget-cost,2), nutrition_totals={'daily':totals,'weekly':weekly},
            explanation='Selected from stored recipes using your diet, allergies, appliances, pantry, goals and budget.', warnings=warnings)

    def swap(self, request: PlanRequest, result: PlanResponse, item_id: str) -> PlanResponse:
        index = next((i for i,m in enumerate(result.meals) if m.id == item_id), None)
        if index is None:
            raise DomainError('item_not_found', 'Meal item not found.', 404)
        by_id = {r['id']: r for r in self.recipes}
        if any(m.recipe_id not in by_id for m in result.meals):
            raise DomainError('recipe_not_found', 'A recipe was removed; generate a new plan.', 409)
        chosen = [by_id[m.recipe_id] for m in result.meals]
        if any(not eligible(r, request) for r in chosen):
            raise DomainError('recipe_changed', 'Recipe constraints changed; generate a new plan.', 409)
        current = chosen[index]
        group = [r for r in self.recipes if r['id'] != current['id'] and eligible(r,request) and result.meals[index].meal_type in r['meal_types']]
        group.sort(key=lambda r: (abs((r.get('protein_grams') or 0)-(current.get('protein_grams') or 0)), recipe_cost(r,request.people)))
        for recipe in group:
            chosen[index] = recipe
            if plan_cost(chosen,request) <= request.budget:
                updated = self.response(request,[(m.day,m.meal_type) for m in result.meals],chosen,[m.id for m in result.meals])
                updated.id, updated.saved = result.id, result.saved
                return updated
        raise DomainError('no_swap_available', 'No different recipe meets this meal type, hard constraints and budget.', 409)
