"""Timezone-aware scheduling engine with standard 5-field cron parsing and DST handling."""

from __future__ import annotations

import calendar
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger("datalens.automation.scheduler")


def _resolve_tz(tz_str: str) -> Any:
    """Resolve an IANA timezone string, falling back safely to UTC."""
    if not tz_str or tz_str.upper() in ("UTC", "GMT", "ETC/UTC"):
        return UTC
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz_str)
    except Exception:
        logger.warning(f"Unrecognized timezone '{tz_str}', falling back to UTC")
        return UTC


def _parse_field(field_str: str, min_val: int, max_val: int) -> set[int]:
    """Parse a single cron field with support for *, commas, ranges, and step values."""
    field_str = field_str.strip()
    values: set[int] = set()

    parts = field_str.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue

        if "/" in part:
            subparts = part.split("/")
            if len(subparts) != 2:
                continue
            range_part, step_str = subparts
            try:
                step = int(step_str)
            except ValueError:
                continue
            if step <= 0:
                continue

            if range_part == "*" or range_part == "":
                start, end = min_val, max_val
            elif "-" in range_part:
                r_start, r_end = range_part.split("-")
                start, end = int(r_start), int(r_end)
            else:
                start, end = int(range_part), max_val

            for val in range(start, end + 1, step):
                if min_val <= val <= max_val:
                    values.add(val)

        elif "-" in part:
            subparts = part.split("-")
            if len(subparts) == 2:
                try:
                    start, end = int(subparts[0]), int(subparts[1])
                    for val in range(start, end + 1):
                        if min_val <= val <= max_val:
                            values.add(val)
                except ValueError:
                    continue

        elif part == "*":
            return set(range(min_val, max_val + 1))

        else:
            try:
                val = int(part)
                if min_val <= val <= max_val:
                    values.add(val)
            except ValueError:
                continue

    return values if values else set(range(min_val, max_val + 1))


class AutomationScheduler:
    """Calculates next execution timestamps with timezone and DST awareness."""

    @classmethod
    def parse_cron(cls, expression: str, base_time: datetime, tz: Any) -> datetime:
        """Parse standard 5-field cron: minute hour day_of_month month day_of_week."""
        tokens = expression.strip().split()
        if len(tokens) != 5:
            # Fallback daily
            return (base_time + timedelta(days=1)).astimezone(UTC)

        minutes = _parse_field(tokens[0], 0, 59)
        hours = _parse_field(tokens[1], 0, 23)
        doms = _parse_field(tokens[2], 1, 31)
        months = _parse_field(tokens[3], 1, 12)
        dows = _parse_field(tokens[4], 0, 6)  # 0=Sunday or 0=Monday depending on convention; here 0=Sunday, 6=Saturday

        # Candidate search starting 1 minute after base_time up to 5 years
        current = (base_time + timedelta(minutes=1)).replace(second=0, microsecond=0)
        # Search minute by minute for the next match up to 100,000 minutes (~70 days)
        # To optimize, step by days if hour/dom does not match
        limit_minutes = 100000
        checked = 0

        while checked < limit_minutes:
            if current.month not in months:
                # Advance to start of next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1, day=1, hour=0, minute=0)
                else:
                    current = current.replace(month=current.month + 1, day=1, hour=0, minute=0)
                checked += 1440
                continue

            # Day of month & day of week check
            cron_dow = (current.weekday() + 1) % 7  # 0=Sunday..6=Saturday
            dom_match = current.day in doms
            dow_match = cron_dow in dows

            if not (dom_match and dow_match):
                # Advance 1 day
                current = (current + timedelta(days=1)).replace(hour=0, minute=0)
                checked += 1440
                continue

            if current.hour not in hours:
                # Advance 1 hour
                current = (current + timedelta(hours=1)).replace(minute=0)
                checked += 60
                continue

            if current.minute in minutes:
                return current.astimezone(UTC)

            current += timedelta(minutes=1)
            checked += 1

        # Fallback 24h
        return (base_time + timedelta(days=1)).astimezone(UTC)

    @classmethod
    def calculate_next_run(
        cls,
        frequency: str,
        timezone_str: str = "UTC",
        hour: int = 0,
        minute: int = 0,
        day_of_week: int | None = None,
        day_of_month: int | None = None,
        cron_expression: str | None = None,
        base_time: datetime | None = None,
    ) -> datetime | None:
        """Calculate next scheduled execution in UTC preserving timezone context."""
        tz = _resolve_tz(timezone_str)
        now_utc = base_time or datetime.now(UTC)
        now_local = now_utc.astimezone(tz)

        freq = frequency.lower().strip()

        if freq == "one_time":
            candidate = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now_local:
                return None  # One-time schedule in past has no next run
            return candidate.astimezone(UTC)

        elif freq == "hourly":
            candidate = (now_local + timedelta(hours=1)).replace(minute=minute, second=0, microsecond=0)
            return candidate.astimezone(UTC)

        elif freq == "daily":
            candidate = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now_local:
                candidate += timedelta(days=1)
            return candidate.astimezone(UTC)

        elif freq == "weekly":
            target_dow = day_of_week if day_of_week is not None else 0  # 0=Monday
            candidate = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = (target_dow - now_local.weekday()) % 7
            if days_ahead == 0 and candidate <= now_local:
                days_ahead = 7
            candidate += timedelta(days=days_ahead)
            return candidate.astimezone(UTC)

        elif freq == "monthly":
            target_dom = day_of_month if day_of_month is not None else 1
            year = now_local.year
            month = now_local.month

            max_days = calendar.monthrange(year, month)[1]
            clamped_day = min(target_dom, max_days)
            candidate = now_local.replace(year=year, month=month, day=clamped_day, hour=hour, minute=minute, second=0, microsecond=0)

            if candidate <= now_local:
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1
                max_days = calendar.monthrange(year, month)[1]
                clamped_day = min(target_dom, max_days)
                candidate = now_local.replace(year=year, month=month, day=clamped_day, hour=hour, minute=minute, second=0, microsecond=0)

            return candidate.astimezone(UTC)

        elif freq == "cron" and cron_expression:
            return cls.parse_cron(cron_expression, now_local, tz)

        # Default fallback: +24h
        return (now_utc + timedelta(days=1))
