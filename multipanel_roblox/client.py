import asyncio
import json
from typing import Any, Optional
import httpx

from multipanel_roblox.models import UniverseInfo, DatastoreEntry


class RobloxCloudError(Exception):
    def __init__(self, status_code: int, message: str, raw_body: str = ""):
        super().__init__(f"Roblox API error {status_code}: {message}")
        self.status_code = status_code
        self.raw_body = raw_body


class RobloxClient:
    """Async wrapper over Roblox Open Cloud endpoints with retry on throttle."""

    BASE_URL = "https://apis.roblox.com"

    def __init__(self, api_key: str, timeout: float = 12.0):
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "x-api-key": self.api_key,
                "User-Agent": "multipanel-roblox/0.2",
            },
            timeout=timeout,
        )

    async def close(self):
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        # Roblox sometimes drops connections under burst traffic or 429s without headers
        for attempt in range(5):
            try:
                resp = await self._client.request(method, path, **kwargs)
                if resp.status_code == 429 or resp.status_code == 503:
                    raw_retry = resp.headers.get("retry-after")
                    # Open Cloud often omits retry-after completely
                    delay = float(raw_retry) if raw_retry else (0.8 * (2**attempt))
                    await asyncio.sleep(min(delay, 10.0))
                    continue
                if resp.status_code >= 400:
                    raise RobloxCloudError(resp.status_code, resp.text, resp.text)
                return resp
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError):
                if attempt == 4:
                    raise
                await asyncio.sleep(0.4 * (2**attempt))
        raise RobloxCloudError(500, "Exhausted retries")

    async def get_universe(self, universe_id: int) -> UniverseInfo:
        url = f"/universes/v1/universes/{universe_id}"
        r = await self._request("GET", url)
        data = r.json()
        return UniverseInfo(
            universe_id=universe_id,
            name=data.get("name", f"Universe {universe_id}"),
            description=data.get("description", ""),
            is_active=data.get("isActive", True),
        )

    async def list_datastores(
        self, universe_id: int, prefix: str = "", limit: int = 50, cursor: str = ""
    ) -> tuple[list[str], str]:
        params: dict[str, Any] = {
            "maxPageSize": min(limit, 50),
        }
        if prefix:
            params["prefix"] = prefix
        if cursor:
            params["cursor"] = cursor
        url = f"/datastores/v1/universes/{universe_id}/standard-datastores"
        r = await self._request("GET", url, params=params)
        data = r.json()
        stores = [ds["name"] for ds in data.get("datastores", [])]
        next_cursor = data.get("nextPageCursor", "")
        return stores, next_cursor

    async def list_keys(
        self, universe_id: int, datastore: str, scope: str = "global", prefix: str = "", limit: int = 50, cursor: str = ""
    ) -> tuple[list[str], str]:
        params: dict[str, Any] = {
            "datastoreName": datastore,
            "scope": scope,
            "maxPageSize": min(limit, 100),
        }
        if prefix:
            params["prefix"] = prefix
        if cursor:
            params["cursor"] = cursor
        url = f"/datastores/v1/universes/{universe_id}/standard-datastores/datastore/entries"
        r = await self._request("GET", url, params=params)
        data = r.json()
        keys = [item["key"] for item in data.get("keys", [])]
        return keys, data.get("nextPageCursor", "")

    async def get_entry(
        self, universe_id: int, datastore: str, key: str, scope: str = "global"
    ) -> Optional[DatastoreEntry]:
        url = f"/datastores/v1/universes/{universe_id}/standard-datastores/datastore/entries/entry"
        params = {
            "datastoreName": datastore,
            "entryKey": key,
            "scope": scope,
        }
        try:
            r = await self._request("GET", url, params=params)
        except RobloxCloudError as err:
            if err.status_code == 404:
                return None
            raise

        val = r.text
        # print(f"DEBUG get_entry status={r.status_code} raw={val[:40]}")
        try:
            parsed = json.loads(val)
        except json.JSONDecodeError:
            parsed = val

        version_id = r.headers.get("roblox-entry-version", "")
        created_time = r.headers.get("roblox-entry-created-time", "")
        return DatastoreEntry(key=key, value=parsed, version_id=version_id, updated_at=created_time)

    async def set_entry(
        self, universe_id: int, datastore: str, key: str, value_obj: Any, scope: str = "global"
    ) -> str:
        url = f"/datastores/v1/universes/{universe_id}/standard-datastores/datastore/entries/entry"
        params = {
            "datastoreName": datastore,
            "entryKey": key,
            "scope": scope,
        }
        payload = json.dumps(value_obj)
        headers = {
            "content-type": "application/json",
        }
        # FIXME: compute md5 checksum when roblox standard datastores enforce content-md5 header
        r = await self._request("POST", url, params=params, content=payload, headers=headers)
        return r.headers.get("roblox-entry-version", "")

    async def publish_message(self, universe_id: int, topic: str, message_data: str) -> bool:
        url = f"/messaging-service/v1/universes/{universe_id}/topics/{topic}"
        payload = {"message": message_data}
        resp = await self._request("POST", url, json=payload)
        return resp.status_code == 200
