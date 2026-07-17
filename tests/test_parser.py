import pytest
from multipanel_roblox.logs import parse_log_entry, strip_roblox_prefixes
from multipanel_roblox.datastore import decode_datastore_value


def test_parse_standard_log_line():
    raw = "2023-10-27T14:20:00.123Z [Server] Player joined: BuilderMan (123456)"
    entry = parse_log_entry(raw)
    assert entry.timestamp == "2023-10-27T14:20:00.123Z"
    assert entry.level == "INFO"
    assert "BuilderMan" in entry.message


def test_parse_error_log_line():
    raw = "2023-10-27T14:20:05.000Z [Server] [ERROR] Script 'PlayerHandler':42: attempt to index nil"
    entry = parse_log_entry(raw)
    assert entry.level == "ERROR"
    assert "attempt to index nil" in entry.message


def test_strip_prefixes():
    line = "[Output] [Server] Game initialized"
    clean = strip_roblox_prefixes(line)
    assert clean == "Game initialized"


def test_decode_datastore_json_dict():
    raw = '{"Coins": 500, "Inventory": ["sword", "shield"]}'
    val, is_json = decode_datastore_value(raw)
    assert is_json is True
    assert val["Coins"] == 500
    assert "sword" in val["Inventory"]


def test_decode_datastore_primitive():
    raw = "12345"
    val, is_json = decode_datastore_value(raw)
    assert val == 12345
    assert is_json is True


def test_decode_double_encoded_json():
    # Lua HttpService:JSONEncode called twice by older game code
    double_encoded = '"{\\\"xp\\\": 100, \\\"level\\\": 2}"'
    val, is_json = decode_datastore_value(double_encoded)
    assert is_json is True
    # Should unwrap inner payload cleanly
    assert isinstance(val, dict)
    assert val.get("xp") == 100
    assert val.get("level") == 2


# TODO: add test for cursor-based datastore pagination once ordered ds v2 lands
