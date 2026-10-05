from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import AstroCalculation, BirthData


_ENGINE_DIR = Path(__file__).resolve().parent / "engine"


def _load_donor_engine():
    engine_path = str(_ENGINE_DIR)
    if engine_path not in sys.path:
        sys.path.insert(0, engine_path)

    # Donor modules intentionally keep their original flat imports so that the
    # current QUANTAREON Astrofractal can be reused with minimal changes.
    from af_machine import Machine  # type: ignore
    from af_natal_scenario import render_natal  # type: ignore

    return Machine, render_natal


def _calculate_sync(data: BirthData) -> AstroCalculation:
    Machine, render_natal = _load_donor_engine()

    local = datetime(
        data.year,
        data.month,
        data.day,
        data.hour,
        data.minute,
    )
    try:
        birth_utc = local.replace(
            tzinfo=ZoneInfo(data.timezone)
        ).astimezone(timezone.utc)
    except Exception:
        birth_utc = local.replace(tzinfo=timezone.utc)

    machine = Machine(
        "TELEPAT Client",
        data.year,
        data.month,
        data.day,
        data.hour,
        data.minute,
        data.latitude,
        data.longitude,
        data.timezone,
        birth_utc,
        ss=0,
    )
    raw_text = render_natal(machine)

    return AstroCalculation(
        raw_text=raw_text,
        metadata={
            "timezone": data.timezone,
            "birth_utc": birth_utc.isoformat(),
            "latitude": data.latitude,
            "longitude": data.longitude,
        },
    )


async def calculate_natal(data: BirthData) -> AstroCalculation:
    """Run the deterministic donor engine outside the asyncio event loop."""
    return await asyncio.to_thread(_calculate_sync, data)
