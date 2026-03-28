"""initial_schema

Revision ID: e785a96f7622
Revises: 
Create Date: 2026-03-28 19:32:12.803442

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e785a96f7622'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('ratings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ratings_user_id'), ['user_id'], unique=False)
        batch_op.create_unique_constraint('uq_skill_user', ['skill_id', 'user_id'])
        batch_op.create_foreign_key('fk_ratings_user_id', 'users', ['user_id'], ['id'])

    with op.batch_alter_table('skills', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_skills_client_id'), ['client_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_skills_content_hash'), ['content_hash'], unique=False)
        batch_op.create_index(batch_op.f('ix_skills_skill_slug'), ['skill_slug'], unique=False)
        batch_op.create_index(batch_op.f('ix_skills_user_id'), ['user_id'], unique=False)
        batch_op.create_foreign_key('fk_skills_parent_id', 'skills', ['parent_id'], ['id'])
        batch_op.create_foreign_key('fk_skills_user_id', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('skills', schema=None) as batch_op:
        batch_op.drop_constraint('fk_skills_user_id', type_='foreignkey')
        batch_op.drop_constraint('fk_skills_parent_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_skills_user_id'))
        batch_op.drop_index(batch_op.f('ix_skills_skill_slug'))
        batch_op.drop_index(batch_op.f('ix_skills_content_hash'))
        batch_op.drop_index(batch_op.f('ix_skills_client_id'))

    with op.batch_alter_table('ratings', schema=None) as batch_op:
        batch_op.drop_constraint('fk_ratings_user_id', type_='foreignkey')
        batch_op.drop_constraint('uq_skill_user', type_='unique')
        batch_op.drop_index(batch_op.f('ix_ratings_user_id'))
