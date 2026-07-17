from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Optional, List
from multipanel_roblox.client import RobloxClient


@dataclass
class LogEntry:
    timestamp: str
    message: str
    log_type: str
    server_id: Optional[str] = None
    count: int = 1

    def format_terminal(self, show_server: bool = False) -> str:
        colors = {
            "error": "\033[31m",  # red
            "warn": "\033[33m",   # yellow
            "info": "\033[37m",   # white
            "debug": "\033[90m",  # gray
        }
        reset = "\033[0m"
        col = colors.get(self.log_type, "\033[37m")

        server_tag = f"[{self.server_id[:8]}] " if show_server and self.server_id else ""
        count_tag = f" (x{self.count})" if self.count > 1 else ""
        return f"\033[90m{self.timestamp}\033[0m {server_tag}{col}{self.message}{count_tag}{reset}"


class LogStreamer:
    def __init__(self, client: RobloxClient, universe_id: int, place_id: int):
        self.client = client
        self.universe_id = universe_id
        self.place_id = place_id
        self._seen_hashes = set()

    def _hash_entry(self, entry: LogEntry) -> int:
        return hash((entry.timestamp, entry.message, entry.server_id))

    def parse_raw_message(self, raw: str) -> LogEntry:
        log_type = "info"
        cleaned = raw.strip()

        # regex catches standard Roblox stack frames: 'Script "ServerScriptService.Handler", Line 42'
        if re.search(r"(Script '[^']+', Line \d+|ServerScriptService|Players\.[^:]+:)", cleaned):
            log_type = "error"
        elif "[Error]" in cleaned or "error:" in cleaned.lower():
            log_type = "error"
        elif "[Warning]" in cleaned or "[Warn]" in cleaned:
            log_type = "warn"
        elif cleaned.startswith("DEBUG:"):
            log_type = "debug"

        return LogEntry(
            timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            message=cleaned,
            log_type=log_type,
        )

    async def poll_recent(self) -> List[LogEntry]:
        records = await self.client.get_universe_errors(self.universe_id, self.place_id)
        new_entries = []

        for rec in records:
            # Cloud error logs group repeated errors with a count field
            entry = LogEntry(
                timestamp=rec.get("timestamp", "")[-8:] if "timestamp" in rec else datetime.now(timezone.utc).strftime("%H:%M:%S"),
                message=rec.get("message", "").strip(),
                log_type="error" if rec.get("level", "").lower() == "error" else "warn",
                server_id=rec.get("serverJobId"),
                count=rec.get("count", 1),
            )
            h = self._hash_entry(entry)
            if h not in self._seen_hashes:
                self._seen_hashes.add(h)
                new_entries.append(entry)

        if len(self._seen_hashes) > 5000:
            self._seen_hashes = set(list(self._seen_hashes)[-2000:])

        return new_entries
