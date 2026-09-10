# backend/services/db.py
from __future__ import annotations
import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncIterator

_pool: asyncpg.Pool | None = None


async def init_pool(dsn: str) -> None:
    global _pool
    # asyncpg uses postgresql:// not postgresql+asyncpg://
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def transaction() -> AsyncIterator[asyncpg.Connection]:
    assert _pool is not None, "DB pool not initialized — call init_pool() first"
    async with _pool.acquire() as conn:
        async with conn.transaction():
            yield conn
