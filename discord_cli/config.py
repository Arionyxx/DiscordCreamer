from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(slots=True)
class ServerRequest:
    """Represents a single server creation request."""

    name: str


@dataclass(slots=True)
class WebhookConfig:
    """Configuration for optional webhook notifications."""

    enabled: bool
    url: Optional[str] = None
    username: Optional[str] = None


@dataclass(slots=True)
class InvitationConfig:
    """Configuration for inviting a target user."""

    raw_identifier: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    discriminator: Optional[str] = None
    grant_admin: bool = True


@dataclass(slots=True)
class SessionConfig:
    """Aggregate configuration for a provisioning session."""

    token: str
    servers: List[ServerRequest] = field(default_factory=list)
    invitation: Optional[InvitationConfig] = None
    webhook: Optional[WebhookConfig] = None
