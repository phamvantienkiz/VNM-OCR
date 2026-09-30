"""Unit tests for memory_utils."""

from app.utils.memory_utils import force_garbage_collection_and_trim


def test_force_garbage_collection_and_trim():
    """Verify force_garbage_collection_and_trim executes without error across platforms."""
    # Should run smoothly and not raise exceptions
    force_garbage_collection_and_trim()
