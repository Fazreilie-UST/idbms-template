"""add is_imported flag to build_plans and build_plan_revisions

Adds an ``is_imported`` boolean indicator that distinguishes records that
originated from an Excel build-plan import (legacy / manual files) from
records authored directly in the web app (e.g. manual revisions).

Backfill rules:
    * ``build_plan_revisions.is_imported = TRUE``   when ``import_file_id`` IS NOT NULL.
    * ``build_plans.is_imported       = TRUE``   when ``first_seen_file_id`` IS NOT NULL
      OR any of the plan's revisions has ``import_file_id`` IS NOT NULL.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "build_plans",
        sa.Column(
            "is_imported",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "build_plan_revisions",
        sa.Column(
            "is_imported",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Backfill: every revision that was produced by an import file is imported.
    op.execute(
        """
        UPDATE build_plan_revisions
           SET is_imported = TRUE
         WHERE import_file_id IS NOT NULL
        """
    )

    # Backfill: a build plan is imported if it was first seen via an import
    # file or any of its revisions came from an import file.
    op.execute(
        """
        UPDATE build_plans bp
           SET is_imported = TRUE
         WHERE bp.first_seen_file_id IS NOT NULL
            OR EXISTS (
                SELECT 1 FROM build_plan_revisions r
                 WHERE r.build_plan_id = bp.id
                   AND r.import_file_id IS NOT NULL
            )
        """
    )

    op.create_index(
        "ix_build_plans_is_imported",
        "build_plans",
        ["is_imported"],
    )


def downgrade() -> None:
    op.drop_index("ix_build_plans_is_imported", table_name="build_plans")
    op.drop_column("build_plan_revisions", "is_imported")
    op.drop_column("build_plans", "is_imported")
