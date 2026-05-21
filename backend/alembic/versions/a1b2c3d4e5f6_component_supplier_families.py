"""component_supplier_families

Revision ID: a1b2c3d4e5f6
Revises: 22ac283387b8
Create Date: 2026-05-19 12:00:00.000000

Adds a three-way junction table that records which families a given
(component, supplier) pair supplies for. The existing ``component_suppliers``
many-to-many table is preserved; the new table merely refines each pair with
a family list.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "22ac283387b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "component_supplier_families",
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["component_id", "supplier_id"],
            ["component_suppliers.component_id", "component_suppliers.supplier_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["family_id"], ["families.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("component_id", "supplier_id", "family_id"),
    )
    op.create_index(
        "ix_csf_family", "component_supplier_families", ["family_id"], unique=False
    )
    op.create_index(
        "ix_csf_component_supplier",
        "component_supplier_families",
        ["component_id", "supplier_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_csf_component_supplier", table_name="component_supplier_families")
    op.drop_index("ix_csf_family", table_name="component_supplier_families")
    op.drop_table("component_supplier_families")
