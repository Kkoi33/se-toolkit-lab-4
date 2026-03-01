"""Unit tests for item endpoint edge cases and boundary values."""

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.item import ItemRecord, ItemCreate, ItemUpdate
from app.routers.items import get_item, post_item, put_item


def _make_item_record(id: int, title: str = "Test Item", description: str = "", parent_id: int | None = None) -> ItemRecord:
    """Helper to create an ItemRecord for testing."""
    return ItemRecord(
        id=id,
        type="step",
        parent_id=parent_id,
        title=title,
        description=description,
        attributes={},
    )


@pytest.mark.asyncio
async def test_get_item_returns_404_for_nonexistent_id() -> None:
    """Test that requesting a non-existent item returns 404."""
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)
    
    with pytest.raises(HTTPException) as exc_info:
        await get_item(item_id=999, session=mock_session)
    
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Item not found"


@pytest.mark.asyncio
async def test_post_item_raises_422_for_invalid_parent_id() -> None:
    """Test that creating an item with non-existent parent_id raises 422."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock(side_effect=IntegrityError(
        statement="INSERT INTO item ...",
        params={},
        orig=Exception("foreign key violation")
    ))
    
    body = ItemCreate(type="step", parent_id=999, title="Child Item", description="")
    
    with pytest.raises(HTTPException) as exc_info:
        await post_item(body=body, session=mock_session)
    
    assert exc_info.value.status_code == 422
    assert "parent_id" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_put_item_returns_404_for_nonexistent_id() -> None:
    """Test that updating a non-existent item returns 404."""
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)
    
    body = ItemUpdate(title="Updated Title", description="Updated description")
    
    with pytest.raises(HTTPException) as exc_info:
        await put_item(item_id=999, body=body, session=mock_session)
    
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Item not found"


@pytest.mark.asyncio
async def test_get_item_returns_existing_item() -> None:
    """Test that requesting an existing item returns it successfully."""
    mock_session = AsyncMock()
    expected_item = _make_item_record(id=1, title="Existing Item")
    mock_session.get = AsyncMock(return_value=expected_item)
    
    result = await get_item(item_id=1, session=mock_session)
    
    assert result.id == 1
    assert result.title == "Existing Item"


@pytest.mark.asyncio
async def test_put_item_updates_existing_item() -> None:
    """Test that updating an existing item succeeds and returns updated data."""
    mock_session = AsyncMock()
    existing_item = _make_item_record(id=1, title="Old Title", description="Old desc")
    mock_session.get = AsyncMock(return_value=existing_item)
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    body = ItemUpdate(title="New Title", description="New description")
    
    result = await put_item(item_id=1, body=body, session=mock_session)
    
    assert result.title == "New Title"
    assert result.description == "New description"
    assert existing_item.title == "New Title"
    assert existing_item.description == "New description"
