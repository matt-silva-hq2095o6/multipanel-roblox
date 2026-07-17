import json
import base64
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
from multipanel_roblox.client import RobloxClient


@dataclass
class DatastoreEntry:
    key: str
    scope: str
    datastore_name: str
    value: Any
    version_id: Optional[str] = None
    created_time: Optional[str] = None
    md5: Optional[str] = None
    user_ids: Optional[List[int]] = None
    attributes: Optional[Dict[str, Any]] = None


class DatastoreManager:
    """High-level helper for Roblox Open Cloud Standard & Ordered DataStores."""

    def __init__(self, client: RobloxClient, universe_id: int):
        self.client = client
        self.universe_id = universe_id

    async def list_datastores(self, prefix: str = "", limit: int = 50) -> List[str]:
        data = await self.client.list_datastores(self.universe_id, prefix=prefix, max_page_size=limit)
        return [ds.get("name", "") for ds in data.get("datastores", [])]

    async def list_keys(
        self, 
        datastore_name: str, 
        scope: str = "global", 
        prefix: str = "",
        page_token: Optional[str] = None,
        limit: int = 50,
    ) -> Tuple[List[str], Optional[str]]:
        data = await self.client.list_datastore_keys(
            universe_id=self.universe_id,
            datastore_name=datastore_name,
            scope=scope,
            prefix=prefix,
            cursor=page_token,
            limit=limit,
        )
        keys = [k.get("key", "") for k in data.get("keys", [])]
        next_token = data.get("nextPageCursor")
        return keys, next_token

    async def get_entry(self, datastore_name: str, key: str, scope: str = "global") -> DatastoreEntry:
        raw_body, headers = await self.client.get_datastore_entry(
            universe_id=self.universe_id,
            datastore_name=datastore_name,
            key=key,
            scope=scope,
        )

        # datastores can store raw numbers, booleans, strings, or stringified json dicts
        parsed_val: Any = raw_body
        if isinstance(raw_body, str):
            try:
                parsed_val = json.loads(raw_body)
            except json.JSONDecodeError:
                parsed_val = raw_body

        # roblox returns attributes as JSON-encoded string inside a header
        raw_attrs = headers.get("roblox-entry-attributes")
        attrs = None
        if raw_attrs:
            try:
                attrs = json.loads(raw_attrs)
            except json.JSONDecodeError:
                attrs = {}

        raw_user_ids = headers.get("roblox-entry-userids")
        user_ids = None
        if raw_user_ids:
            try:
                user_ids = json.loads(raw_user_ids)
            except json.JSONDecodeError:
                pass

        # compute md5 for local checksum verify if needed
        encoded_content = raw_body.encode("utf-8") if isinstance(raw_body, str) else str(raw_body).encode("utf-8")
        checksum = hashlib.md5(encoded_content).hexdigest()

        return DatastoreEntry(
            key=key,
            scope=scope,
            datastore_name=datastore_name,
            value=parsed_val,
            version_id=headers.get("roblox-entry-version-id"),
            created_time=headers.get("roblox-entry-created-time"),
            md5=checksum,
            user_ids=user_ids,
            attributes=attrs,
        )

    async def set_entry(
        self, 
        datastore_name: str, 
        key: str, 
        value: Union[dict, list, str, int, float, bool],
        scope: str = "global",
        match_version: Optional[str] = None,
        user_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        # TODO: support setting custom EntryAttributes once client exposes header pass-through
        if isinstance(value, (dict, list)):
            payload = json.dumps(value, separators=(',', ':'))
        else:
            payload = str(value)

        res = await self.client.set_datastore_entry(
            universe_id=self.universe_id,
            datastore_name=datastore_name,
            key=key,
            data=payload,
            scope=scope,
            match_version=match_version,
            user_ids=user_ids,
        )
        return res

    async def delete_entry(self, datastore_name: str, key: str, scope: str = "global") -> bool:
        return await self.client.delete_datastore_entry(
            universe_id=self.universe_id,
            datastore_name=datastore_name,
            key=key,
            scope=scope,
        )
