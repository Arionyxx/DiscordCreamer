from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import aiohttp

from .config import WebhookConfig
from .errors import DiscordOperationError
from .progress import ProgressPrinter


@dataclass(slots=True)
class ProvisioningNotification:
    server_name: str
    invite_url: str
    message: str


class WebhookNotifier:
    """Handles optional webhook notifications once provisioning completes."""

    def __init__(self, config: WebhookConfig, progress: ProgressPrinter) -> None:
        self._config = config
        self._progress = progress
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def notify(self, payload: ProvisioningNotification) -> None:
        if not self._config.enabled or not self._config.url:
            return

        session = await self._ensure_session()
        data = {
            "content": payload.message,
            "embeds": [
                {
                    "title": "Discord Server Provisioned",
                    "description": f"Server **{payload.server_name}** is ready.",
                    "fields": [
                        {"name": "Invite Link", "value": payload.invite_url},
                    ],
                }
            ],
        }
        if self._config.username:
            data["username"] = self._config.username

        try:
            async with session.post(self._config.url, json=data) as response:
                if response.status >= 400:
                    body = await response.text()
                    raise DiscordOperationError(
                        f"Webhook responded with status {response.status}: {body}"
                    )
        except asyncio.TimeoutError as exc:
            raise DiscordOperationError("Webhook request timed out") from exc

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
