"""Aiutanti comuni ai test degli handler: gli agent sono sempre finti, così i
test verificano la macchina a stati e non la qualità del testo."""
from __future__ import annotations


def fake_stream(text: str):
    async def stream(*a, **kw):
        yield text
    return stream


async def collect(gen) -> list:
    return [e async for e in gen]


def types_of(events) -> list[str]:
    return [type(e).__name__ for e in events]
