import pytest
from unittest.mock import patch, MagicMock, call
import httpx
from multipanel_roblox.client import OpenCloudClient, RobloxAPIError, RateLimitError


@pytest.fixture
def client():
    return OpenCloudClient(api_key="test-key-123", max_retries=2)


def test_headers_contain_api_key(client):
    headers = client._build_headers()
    assert headers["x-api-key"] == "test-key-123"
    assert "application/json" in headers["accept"]


@patch("httpx.Client.send")
def test_get_universe_success(mock_send, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": 12345, "name": "Dev Place", "description": "test"}
    mock_send.return_value = mock_resp

    data = client.get_universe(12345)
    assert data["id"] == 12345
    assert data["name"] == "Dev Place"


@patch("httpx.Client.send")
def test_client_raises_roblox_api_error_on_403(mock_send, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = '{"error": "UnauthorizedAccess"}'
    mock_send.return_value = mock_resp

    with pytest.raises(RobloxAPIError) as exc_info:
        client.get_universe(12345)
    assert exc_info.value.status_code == 403
    assert "UnauthorizedAccess" in str(exc_info.value)


@patch("time.sleep", return_value=None)
@patch("httpx.Client.send")
def test_retry_on_429_eventual_success(mock_send, mock_sleep, client):
    rate_limit_resp = MagicMock()
    rate_limit_resp.status_code = 429
    rate_limit_resp.headers = {"retry-after": "1"}
    rate_limit_resp.text = "Rate limit exceeded"

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {"dataStores": [{"name": "PlayerData"}]}

    mock_send.side_effect = [rate_limit_resp, ok_resp]

    res = client.list_datastores(universe_id=12345)
    assert len(res["dataStores"]) == 1
    assert mock_send.call_count == 2
    mock_sleep.assert_called_once_with(1.0)


@patch("time.sleep", return_value=None)
@patch("httpx.Client.send")
def test_retry_exhaustion_raises_ratelimit(mock_send, mock_sleep, client):
    rate_limit_resp = MagicMock()
    rate_limit_resp.status_code = 429
    rate_limit_resp.headers = {}
    rate_limit_resp.text = "Too many requests"

    mock_send.return_value = rate_limit_resp

    with pytest.raises(RateLimitError):
        client.list_datastores(universe_id=12345)
    # initial request + 2 retries
    assert mock_send.call_count == 3
