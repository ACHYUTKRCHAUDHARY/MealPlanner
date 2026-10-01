"""Add email_verified to users and account_tokens table"""
from alembic import op
import sqlalchemy as sa

revision = 'a2e4f6b8d0c1'
down_revision = '68640028cfbd'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.create_table('account_tokens',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('purpose', sa.String(length=20), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used', sa.Boolean(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_account_tokens_user_id'), 'account_tokens', ['user_id'], unique=False)
    op.create_index('ix_account_tokens_user_purpose', 'account_tokens', ['user_id', 'purpose'], unique=False)


def downgrade():
    op.drop_index('ix_account_tokens_user_purpose', table_name='account_tokens')
    op.drop_index(op.f('ix_account_tokens_user_id'), table_name='account_tokens')
    op.drop_table('account_tokens')
    op.drop_column('users', 'email_verified')
