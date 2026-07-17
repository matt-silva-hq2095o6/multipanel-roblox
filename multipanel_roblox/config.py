import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


@dataclass
class UniverseConfig:
    universe_id: int
    alias: str
    api_key: Optional[str] = None
    default_place_id: Optional[int] = None
    places: List[int] = field(default_factory=list)


@dataclass
class AppConfig:
    """Runtime configuration aggregated from local file, user config, and env."""
    api_key: str
    refresh_interval: float = 3.0
    universes: Dict[str, UniverseConfig] = field(default_factory=dict)
    log_level: str = "info"
    auto_reconnect: bool = True
    max_log_buffer: int = 500


def find_config_file() -> Optional[Path]:
    # check cwd first so team repos can commit a shared dev config
    local = Path.cwd() / "multipanel.toml"
    if local.is_file():
        return local

    local_alt = Path.cwd() / ".multipanel.toml"
    if local_alt.is_file():
        return local_alt

    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    user_cfg = base / "multipanel-roblox" / "config.toml"
    if user_cfg.is_file():
        return user_cfg

    return None


def load_config(path: Optional[Path] = None) -> AppConfig:
    config_path = path or find_config_file()
    raw_data: Dict[str, Any] = {}

    if config_path and config_path.is_file():
        with open(config_path, "rb") as f:
            raw_data = tomllib.load(f)

    # print(f"DEBUG: loaded raw config from {config_path}")
    global_key = os.environ.get("ROBLOX_OPEN_CLOUD_KEY") or raw_data.get("api_key", "")
    raw_interval = os.environ.get("MULTIPANEL_REFRESH_RATE", raw_data.get("refresh_interval", 3.0))
    try:
        interval = float(raw_interval)
    except (ValueError, TypeError):
        interval = 3.0

    parsed_universes: Dict[str, UniverseConfig] = {}
    raw_universes = raw_data.get("universes", [])
    
    # Allow either a list of tables or a dictionary keyed by alias
    if isinstance(raw_universes, list):
        for item in raw_universes:
            alias = str(item.get("alias") or item.get("universe_id"))
            parsed_universes[alias] = UniverseConfig(
                universe_id=int(item["universe_id"]),
                alias=alias,
                api_key=item.get("api_key"),
                default_place_id=item.get("default_place_id"),
                places=item.get("places", []),
            )
    elif isinstance(raw_universes, dict):
        for alias, udata in raw_universes.items():
            uid = int(udata.get("universe_id", udata.get("id", 0)))
            if uid == 0:
                continue
            parsed_universes[alias] = UniverseConfig(
                universe_id=uid,
                alias=alias,
                api_key=udata.get("api_key"),
                default_place_id=udata.get("default_place_id"),
                places=udata.get("places", []),
            )

    # FIXME: allow setting per-universe endpoints when on enterprise proxy
    return AppConfig(
        api_key=global_key,
        refresh_interval=interval,
        universes=parsed_universes,
        log_level=raw_data.get("log_level", "info"),
        auto_reconnect=raw_data.get("auto_reconnect", True),
        max_log_buffer=int(raw_data.get("max_log_buffer", 500)),
    )
