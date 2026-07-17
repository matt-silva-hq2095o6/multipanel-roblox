import json
from pathlib import Path
import pytest
from multipanel_roblox.config import load_config, Config, resolve_universe_target


def test_load_config_default_when_missing(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    cfg = load_config(path=None)
    assert isinstance(cfg, Config)
    assert cfg.universes == {}
    assert cfg.default_poll_interval == 3.0


def test_load_config_from_file(tmp_path):
    cfg_file = tmp_path / "config.json"
    raw = {
        "api_key": "rbx-test-key-123",
        "universes": {
            "staging": {"universe_id": 987654321, "place_id": 123456},
            "prod": {"universe_id": 111222333, "place_id": 444555}
        },
        "poll_interval": 5.0
    }
    cfg_file.write_text(json.dumps(raw), encoding="utf-8")

    cfg = load_config(path=cfg_file)
    assert cfg.api_key == "rbx-test-key-123"
    assert len(cfg.universes) == 2
    assert cfg.universes["staging"].universe_id == 987654321
    assert cfg.universes["prod"].place_id == 444555
    assert cfg.default_poll_interval == 5.0


def test_env_override_api_key(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"api_key": "old-key"}), encoding="utf-8")
    monkeypatch.setenv("ROBLOX_API_KEY", "override-key-999")

    cfg = load_config(path=cfg_file)
    assert cfg.api_key == "override-key-999"


def test_resolve_universe_target_by_alias():
    cfg = Config(
        api_key="key",
        universes={
            "qa": {"universe_id": 5001, "place_id": 6001},
            "live": {"universe_id": 7001, "place_id": 8001}
        }
    )
    u_id, p_id = resolve_universe_target(cfg, "qa")
    assert u_id == 5001
    assert p_id == 6001


def test_resolve_universe_target_raw_id():
    cfg = Config(api_key="key", universes={})
    # Passing a numeric string directly when it is not in the alias map
    u_id, p_id = resolve_universe_target(cfg, "998877")
    assert u_id == 998877
    assert p_id is None
