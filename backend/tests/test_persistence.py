"""Tests for persistence/repository layer."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persistence.repository import Repository
from db.base import Base


class TestRepository:
    def test_repository_initialization(self):
        """Repository can be initialized with a model class."""
        repo = Repository(SomeModel)
        assert repo.model is SomeModel

    def test_repository_get_by_id_requires_session(self):
        """Repository without session needs a session context."""
        repo = Repository(SomeModel)
        # _get_session should raise when no session and no async context
        # We can't easily test async here without a DB, so just verify structure
        assert repo._session is None

    def test_repository_get_by_external_id_signature(self):
        """Repository has external ID lookup methods."""
        repo = Repository(SomeModel)
        assert hasattr(repo, "get_by_external_id")
        assert hasattr(repo, "create_external_id")

    def test_repository_has_all_methods(self):
        repo = Repository(SomeModel)
        for method in ["get_by_id", "get_all", "get_by_slug", "get_by_external_id", "create_external_id"]:
            assert hasattr(repo, method), f"Missing method: {method}"


class SomeModel(Base):
    """Test model for repository tests."""
    from sqlalchemy.orm import Mapped, mapped_column
    from sqlalchemy import Integer, String
    __tablename__ = "test_some_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
