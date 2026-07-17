from datetime import datetime, timezone
import time


def human_bytes(size: int | float) -> str:
    if size <= 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024.0:
            return f"{size:3.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024.0
    return f"{size:.1f} PB"


def time_ago(ts: float | int | str | datetime) -> str:
    if isinstance(ts, str):
        # Roblox datastore metadata returns RFC3339/ISO strings like '2023-11-04T18:22:01.123Z'
        clean_ts = ts.replace("Z", "+00:00")
        ts = datetime.fromisoformat(clean_ts)

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        diff = time.time() - ts.timestamp()
    else:
        diff = time.time() - float(ts)

    if diff < 0:
        return "just now"
    if diff < 60:
        return f"{int(diff)}s ago"
    if diff < 3600:
        return f"{int(diff // 60)}m ago"
    if diff < 86400:
        return f"{int(diff // 3600)}h ago"
    return f"{int(diff // 86400)}d ago"


def truncate_str(s: str, max_len: int = 32) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."
