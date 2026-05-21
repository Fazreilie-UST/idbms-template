"""Generic repository base.

Provides a small, opinionated CRUD mixin so domain repositories can avoid
boilerplate. Domain repos may add their own query methods on top.

Existing stock repositories (`app/repositories/stock/*.py`) predate this
base; they remain free-standing. New repos should subclass `BaseRepository`.
"""

from __future__ import annotations

from typing import Generic, Iterable, Sequence, Type, TypeVar

from sqlalchemy.orm import Session

from app.db.base import Base


ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Minimal generic CRUD repository.

    Subclasses set ``model`` to a SQLAlchemy model class. All methods take
    a session so the caller controls the unit-of-work boundary; repositories
    intentionally do NOT commit.
    """

    model: Type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- read ---------------------------------------------------------------

    def get(self, id_: int) -> ModelT | None:
        return self.db.get(self.model, id_)

    def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[ModelT]:
        return (
            self.db.query(self.model)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        return self.db.query(self.model).count()

    # --- write --------------------------------------------------------------

    def add(self, instance: ModelT) -> ModelT:
        self.db.add(instance)
        self.db.flush()
        return instance

    def add_all(self, instances: Iterable[ModelT]) -> None:
        self.db.add_all(list(instances))
        self.db.flush()

    def delete(self, instance: ModelT) -> None:
        self.db.delete(instance)
        self.db.flush()
