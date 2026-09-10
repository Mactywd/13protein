"""Manual retention purge — inspect before you enable the daily job.

    python -m scripts.purge_expired                  # dry run: counts only
    python -m scripts.purge_expired --apply          # actually deletes
    python -m scripts.purge_expired --content-days 540 --session-days 900

Dry run is the default on purpose: the deletion is final and does not reach the
backups. I termini sono stati approvati dal titolare il 17.8.2026 (L5) e sono
pubblicati nella §9 dell'informativa; il job giornaliero è attivo. Questo
comando serve a guardare l'effetto di un termine più corto prima di applicarlo.
Prints row counts, never content — see retention.py.
"""
from __future__ import annotations

import argparse
import asyncio

import retention
import services.db as db
from config import settings


async def _run(content_days: int, session_days: int, apply: bool) -> None:
    await db.init_pool(settings.database_url)
    try:
        async with db.transaction() as conn:
            counts = await retention.purge_expired(
                conn,
                content_days=content_days,
                session_days=session_days,
                dry_run=not apply,
            )
    finally:
        await db.close_pool()

    mode = "ELIMINATE" if apply else "da eliminare (dry run)"
    print(f"Righe {mode}:")
    print(f"  transcript                      {counts['transcripts']}")
    print(f"  sessioni con narrativa ripulita {counts['states_scrubbed']}")
    print(f"  sessioni rimosse (cascade)      {counts['sessions']}")
    if not apply:
        print("\nNessuna riga toccata. Rilancia con --apply per eseguire.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--content-days", type=int, default=settings.retention_content_days)
    p.add_argument("--session-days", type=int, default=settings.retention_session_days)
    p.add_argument("--apply", action="store_true", help="esegue la cancellazione")
    args = p.parse_args()
    asyncio.run(_run(args.content_days, args.session_days, args.apply))


if __name__ == "__main__":
    main()
