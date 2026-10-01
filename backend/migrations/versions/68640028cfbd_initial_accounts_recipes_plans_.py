"""Initial accounts recipes plans groceries and rate limits"""
from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy

revision = '68640028cfbd'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('rate_buckets',
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('window', sa.Integer(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('key', 'window')
    )
    op.create_table('recipes',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=768).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('embedding_model', sa.String(length=100), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('users',
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('token_version', sa.Integer(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('meal_plans',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('saved', sa.Boolean(), nullable=False),
    sa.Column('preferences', sa.JSON(), nullable=False),
    sa.Column('result', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_meal_plans_saved'), 'meal_plans', ['saved'], unique=False)
    op.create_index(op.f('ix_meal_plans_user_id'), 'meal_plans', ['user_id'], unique=False)
    op.create_table('pantry_items',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('quantity', sa.Float(), nullable=True),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('quantity IS NULL OR quantity >= 0'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'name', 'unit')
    )
    op.create_index(op.f('ix_pantry_items_user_id'), 'pantry_items', ['user_id'], unique=False)
    op.create_table('recipe_ingredients',
    sa.Column('recipe_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('quantity', sa.Float(), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('unit_cost', sa.Float(), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('quantity > 0'),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recipe_ingredients_name'), 'recipe_ingredients', ['name'], unique=False)
    op.create_index(op.f('ix_recipe_ingredients_recipe_id'), 'recipe_ingredients', ['recipe_id'], unique=False)
    op.create_table('user_preferences',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('grocery_lists',
    sa.Column('plan_id', sa.String(length=36), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['plan_id'], ['meal_plans.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('plan_id')
    )
    op.create_table('meal_plan_items',
    sa.Column('plan_id', sa.String(length=36), nullable=False),
    sa.Column('recipe_id', sa.String(length=36), nullable=False),
    sa.Column('day', sa.String(length=12), nullable=False),
    sa.Column('meal_type', sa.String(length=12), nullable=False),
    sa.Column('servings', sa.Integer(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['plan_id'], ['meal_plans.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('plan_id', 'day', 'meal_type')
    )
    op.create_index(op.f('ix_meal_plan_items_plan_id'), 'meal_plan_items', ['plan_id'], unique=False)
    op.create_index(op.f('ix_meal_plan_items_recipe_id'), 'meal_plan_items', ['recipe_id'], unique=False)
    op.create_table('grocery_items',
    sa.Column('grocery_list_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('quantity', sa.Float(), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('checked', sa.Boolean(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('quantity >= 0'),
    sa.ForeignKeyConstraint(['grocery_list_id'], ['grocery_lists.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('grocery_list_id', 'name', 'unit')
    )
    op.create_index(op.f('ix_grocery_items_grocery_list_id'), 'grocery_items', ['grocery_list_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_grocery_items_grocery_list_id'), table_name='grocery_items')
    op.drop_table('grocery_items')
    op.drop_index(op.f('ix_meal_plan_items_recipe_id'), table_name='meal_plan_items')
    op.drop_index(op.f('ix_meal_plan_items_plan_id'), table_name='meal_plan_items')
    op.drop_table('meal_plan_items')
    op.drop_table('grocery_lists')
    op.drop_table('user_preferences')
    op.drop_index(op.f('ix_recipe_ingredients_recipe_id'), table_name='recipe_ingredients')
    op.drop_index(op.f('ix_recipe_ingredients_name'), table_name='recipe_ingredients')
    op.drop_table('recipe_ingredients')
    op.drop_index(op.f('ix_pantry_items_user_id'), table_name='pantry_items')
    op.drop_table('pantry_items')
    op.drop_index(op.f('ix_meal_plans_user_id'), table_name='meal_plans')
    op.drop_index(op.f('ix_meal_plans_saved'), table_name='meal_plans')
    op.drop_table('meal_plans')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('recipes')
    op.drop_table('rate_buckets')
    # ### end Alembic commands ###
