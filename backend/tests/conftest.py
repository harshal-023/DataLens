import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def async_client():
    """Provides an asynchronous HTTP test client for FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def is_postgres_reachable() -> bool:
    """Synchronous check if PostgreSQL server is listening."""
    import socket
    try:
        s = socket.create_connection(("localhost", 5432), timeout=1)
        s.close()
        return True
    except (OSError, ConnectionRefusedError):
        return False


POSTGRES_AVAILABLE = is_postgres_reachable()
