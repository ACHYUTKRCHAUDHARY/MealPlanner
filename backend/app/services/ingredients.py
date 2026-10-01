import re
from collections import defaultdict
from app.schemas import Quantity

ALIASES = {'atta': 'whole wheat atta', 'wheat flour': 'whole wheat atta', 'chana': 'chickpeas',
           'chickpea': 'chickpeas', 'onions': 'onion', 'tomatoes': 'tomato', 'yogurt': 'curd',
           'yoghurt': 'curd', 'soy': 'soya', 'groundnut': 'peanut', 'groundnuts': 'peanut'}
UNITS = {'kg': ('g', 1000), 'g': ('g', 1), 'l': ('ml', 1000), 'ml': ('ml', 1),
         'piece': ('count', 1), 'count': ('count', 1), 'bunch': ('bunch', 1), 'bulb': ('bulb', 1)}
ALLERGEN_WORDS = {
    'dairy': ['milk', 'paneer', 'curd', 'yogurt', 'yoghurt', 'butter', 'ghee', 'cheese', 'cream'],
    'peanuts': ['peanut', 'groundnut'],
    'tree nuts': ['almond', 'cashew', 'walnut', 'pistachio', 'hazelnut', 'pecan', 'nut'],
    'gluten': ['wheat', 'atta', 'semolina', 'rava', 'suji', 'barley', 'bread', 'oats'],
    'soy': ['soy', 'soya', 'tofu'], 'egg': ['egg', 'mayonnaise']}


def normalize(name: str) -> str:
    value = ' '.join(name.casefold().split())
    return ALIASES.get(value, value)


def canonical(quantity: float, unit: str) -> tuple[float, str]:
    target, factor = UNITS[unit.lower()]
    return quantity * factor, target


def display(quantity: float, unit: str) -> str:
    return f'{quantity:.2f}'.rstrip('0').rstrip('.') + ' ' + unit


def detected_allergens(ingredients: list[dict]) -> set[str]:
    text = ' '.join(i['name'].lower() for i in ingredients)
    return {a for a, words in ALLERGEN_WORDS.items() if any(word in text for word in words)}


def aggregate(recipes: list[dict], people: int, pantry: list[Quantity]) -> list[Quantity]:
    totals = defaultdict(float)
    for recipe in recipes:
        for ingredient in recipe['ingredients']:
            quantity, unit = canonical(ingredient['quantity'] * people / recipe['servings'], ingredient['unit'])
            totals[(normalize(ingredient['name']), unit)] += quantity
    for item in pantry:
        if item.quantity is not None:
            quantity, unit = canonical(item.quantity, item.unit)
            key = (normalize(item.name), unit)
            totals[key] = max(0, totals.get(key, 0) - quantity)
    return [Quantity(name=name, quantity=round(q, 3), unit=unit)
            for (name, unit), q in sorted(totals.items()) if q > 0.0001]
