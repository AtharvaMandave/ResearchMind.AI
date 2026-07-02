"""
pytest configuration for the ResearchMind AI backend tests.
Sets asyncio_mode = auto so @pytest.mark.asyncio is not required on every test.
"""
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
