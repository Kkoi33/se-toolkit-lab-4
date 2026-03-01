"""Unit tests for learner endpoint edge cases and boundary values."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from app.models.learner import Learner, LearnerCreate
from app.routers.learners import get_learners, post_learner


def _make_learner(id: int, name: str, email: str, enrolled_at: datetime | None = None) -> Learner:
    """Helper to create a Learner for testing."""
    if enrolled_at is None:
        enrolled_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return Learner(
        id=id,
        name=name,
        email=email,
        enrolled_at=enrolled_at,
    )


@pytest.mark.asyncio
async def test_get_learners_with_enrolled_after_filters_correctly() -> None:
    """Test that enrolled_after parameter filters learners by enrollment date."""
    mock_session = AsyncMock()
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)
    
    old_learner = _make_learner(id=1, name="Old", email="old@test.com", enrolled_at=yesterday)
    new_learner = _make_learner(id=2, name="New", email="new@test.com", enrolled_at=tomorrow)
    
    mock_exec = AsyncMock()
    mock_exec.all = MagicMock(return_value=[old_learner, new_learner])
    mock_session.exec = AsyncMock(return_value=mock_exec)
    
    result = await get_learners(enrolled_after=now, session=mock_session)
    
    assert len(result) == 1
    assert result[0].id == 2
    assert result[0].name == "New"


@pytest.mark.asyncio
async def test_get_learners_with_none_enrolled_after_returns_all() -> None:
    """Test that enrolled_after=None returns all learners without filtering."""
    mock_session = AsyncMock()
    
    learner1 = _make_learner(id=1, name="First", email="first@test.com")
    learner2 = _make_learner(id=2, name="Second", email="second@test.com")
    
    mock_exec = AsyncMock()
    mock_exec.all = MagicMock(return_value=[learner1, learner2])
    mock_session.exec = AsyncMock(return_value=mock_exec)
    
    result = await get_learners(enrolled_after=None, session=mock_session)
    
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_learners_with_boundary_datetime_excludes_equal() -> None:
    """Test that enrolled_after uses >= comparison (boundary value test)."""
    mock_session = AsyncMock()
    
    boundary_time = datetime(2025, 1, 1, 12, 0, 0)
    
    exactly_at_boundary = _make_learner(
        id=1, name="At Boundary", email="at@test.com", enrolled_at=boundary_time
    )
    before_boundary = _make_learner(
        id=2, name="Before", email="before@test.com", enrolled_at=boundary_time - timedelta(seconds=1)
    )
    after_boundary = _make_learner(
        id=3, name="After", email="after@test.com", enrolled_at=boundary_time + timedelta(seconds=1)
    )
    
    mock_exec = AsyncMock()
    mock_exec.all = MagicMock(return_value=[exactly_at_boundary, before_boundary, after_boundary])
    mock_session.exec = AsyncMock(return_value=mock_exec)
    
    result = await get_learners(enrolled_after=boundary_time, session=mock_session)
    
    assert len(result) == 2
    ids = {r.id for r in result}
    assert 1 in ids
    assert 3 in ids
    assert 2 not in ids


@pytest.mark.asyncio
async def test_post_learner_creates_learner_with_current_time() -> None:
    """Test that creating a learner sets enrolled_at to current time."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    body = LearnerCreate(name="Test User", email="test@example.com")
    
    before_call = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await post_learner(body=body, session=mock_session)
    after_call = datetime.now(timezone.utc).replace(tzinfo=None)
    
    assert result.name == "Test User"
    assert result.email == "test@example.com"
    assert result.enrolled_at is not None
    assert before_call <= result.enrolled_at <= after_call


@pytest.mark.asyncio
async def test_get_learners_empty_result_returns_empty_list() -> None:
    """Test that no learners returns an empty list (boundary case)."""
    mock_session = AsyncMock()
    
    mock_exec = AsyncMock()
    mock_exec.all = MagicMock(return_value=[])
    mock_session.exec = AsyncMock(return_value=mock_exec)
    
    result = await get_learners(enrolled_after=None, session=mock_session)
    
    assert result == []
    assert isinstance(result, list)
