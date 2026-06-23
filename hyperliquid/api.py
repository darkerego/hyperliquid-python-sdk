import json
import logging
from json import JSONDecodeError

import aiohttp

from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError
from hyperliquid.utils.types import Any, Optional


class API:
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None, session=None):
        self.base_url = base_url or MAINNET_API_URL
        self.session: Optional[aiohttp.ClientSession] = session
        self._owns_session = session is None
        self._logger = logging.getLogger(__name__)
        self.timeout = timeout

        if self.session is not None:
            self.session.headers.update({"Content-Type": "application/json"})

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout) if self.timeout is not None else None
            self.session = aiohttp.ClientSession(timeout=timeout, headers={"Content-Type": "application/json"})
            self._owns_session = True
        return self.session

    async def aclose(self) -> None:
        if self.session is not None and not self.session.closed and self._owns_session:
            await self.session.close()

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def post(self, url_path: str, payload: Any = None) -> Any:
        payload = payload or {}
        url = self.base_url + url_path
        session = await self._ensure_session()

        async with session.post(url, json=payload) as response:
            await self._handle_exception(response)
            try:
                return await response.json()
            except (ValueError, aiohttp.ContentTypeError):
                return {"error": f"Could not parse JSON: {await response.text()}"}

    async def _handle_exception(self, response: aiohttp.ClientResponse) -> None:
        status_code = response.status
        if status_code < 400:
            return

        text = await response.text()
        if 400 <= status_code < 500:
            try:
                err = json.loads(text)
            except JSONDecodeError as exc:
                raise ClientError(status_code, None, text, None, response.headers) from exc
            if err is None:
                raise ClientError(status_code, None, text, None, response.headers)
            error_data = err.get("data")
            raise ClientError(status_code, err["code"], err["msg"], response.headers, error_data)

        raise ServerError(status_code, text)
