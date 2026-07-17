from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ServerHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    DEAD = "dead"


@dataclass
class PlaceInfo:
    place_id: int
    name: str
    universe_id: int
    description: str = ""
    is_root: bool = False


@dataclass
class UniverseInfo:
    universe_id: int
    name: str
    root_place_id: int
    is_archived: bool = False
    places: List[PlaceInfo] = field(default_factory=list)
    # legacy field kept around for old dashboard table formatter
    active_player_count: int = 0


@dataclass
class ServerMetric:
    server_id: str
    place_id: int
    universe_id: int
    player_count: int
    max_players: int
    ping_ms: float
    uptime_seconds: float
    fps: float = 60.0
    region: str = "unknown"
    health: ServerHealth = ServerHealth.HEALTHY


@dataclass
class LogMessage:
    timestamp: datetime
    server_id: str
    place_id: int
    level: str
    message: str
    raw_json: Optional[Dict[str, Any]] = None


@dataclass
class DataStoreRecord:
    key: str
    value: Any
    scope: str = "global"
    datastore_name: str = ""
    version: Optional[str] = None
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    user_ids: List[int] = field(default_factory=list)


@dataclass
class DataStorePage:
    items: List[DataStoreRecord]
    next_page_cursor: Optional[str] = None
