from __future__ import annotations

import asyncio
import re
from typing import Awaitable, Callable, Iterable, List, Optional, TypeVar

import discord

from .config import InvitationConfig, ServerRequest
from .errors import ConfigurationError, RateLimitError

T = TypeVar("T")


SERVER_NAME_REGEX = re.compile(r"[^\w\s-]")


def sanitize_server_name(name: str) -> str:
    cleaned = SERVER_NAME_REGEX.sub("", name).strip()
    if not cleaned:
        raise ConfigurationError("Server name cannot be empty after sanitisation.")
    return cleaned[:95]


def build_server_requests(raw_names: Iterable[str]) -> List[ServerRequest]:
    servers: List[ServerRequest] = []
    for raw_name in raw_names:
        cleaned = sanitize_server_name(raw_name)
        servers.append(ServerRequest(name=cleaned))
    if not servers:
        raise ConfigurationError("At least one server name must be provided.")
    return servers


def parse_target_user(identifier: str) -> InvitationConfig:
    identifier = identifier.strip()
    if not identifier:
        raise ConfigurationError("Target user identifier cannot be empty.")

    if re.fullmatch(r"\d{5,}", identifier):
        return InvitationConfig(raw_identifier=identifier, user_id=int(identifier))

    if "#" in identifier:
        username, _, discriminator = identifier.partition("#")
        if not username or not discriminator or not re.fullmatch(r"\d{4}", discriminator):
            raise ConfigurationError(
                "Discord username must be in the format username#1234 with a 4-digit discriminator."
            )
        return InvitationConfig(
            raw_identifier=identifier,
            username=username,
            discriminator=discriminator,
        )

    raise ConfigurationError(
        "Target user must be a numeric user ID or in the format username#1234."
    )


async def with_rate_limit_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    retries: int = 5,
    base_delay: float = 2.0,
    backoff_factor: float = 2.0,
) -> T:
    delay = base_delay
    for attempt in range(retries):
        try:
            return await operation()
        except discord.HTTPException as exc:
            if exc.status == 429 and attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= backoff_factor
                continue
            raise
    raise RateLimitError("Exceeded maximum retries due to rate limits.")
