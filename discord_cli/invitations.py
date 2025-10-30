from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import discord
from discord.http import Route

from .config import InvitationConfig
from .errors import DiscordOperationError
from .progress import ProgressPrinter
from .utils import with_rate_limit_retry


@dataclass(slots=True)
class FriendRequestResult:
    user_id: int
    username: Optional[str]
    discriminator: Optional[str]


class InvitationManager:
    """Handles friend requests, direct messages, and permission grants."""

    def __init__(
        self,
        client: discord.Client,
        invitation: InvitationConfig,
        progress: ProgressPrinter,
    ) -> None:
        self._client = client
        self._invitation = invitation
        self._progress = progress
        self._admin_roles: dict[int, discord.Role] = {}
        self._grant_admin = invitation.grant_admin

    @property
    def target_user_id(self) -> Optional[int]:
        return self._invitation.user_id

    @property
    def should_grant_admin(self) -> bool:
        return self._grant_admin

    async def send_friend_request(self) -> FriendRequestResult:
        if self._invitation.user_id is not None:
            route = Route(
                "PUT",
                "/users/@me/relationships/{user_id}",
                user_id=self._invitation.user_id,
            )
            payload = {"type": 1}
        else:
            if not self._invitation.username or not self._invitation.discriminator:
                raise DiscordOperationError(
                    "Username and discriminator are required to send a friend request."
                )
            route = Route("POST", "/users/@me/relationships")
            payload = {
                "username": self._invitation.username,
                "discriminator": self._invitation.discriminator,
            }

        async def _operation() -> FriendRequestResult:
            data = await self._client.http.request(route, json=payload)

            if data:
                user_data = data.get("user", data)
                try:
                    user_id = int(user_data["id"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise DiscordOperationError(
                        "Unexpected response while sending friend request"
                    ) from exc
                username = user_data.get("username", self._invitation.username)
                discriminator = user_data.get(
                    "discriminator", self._invitation.discriminator
                )
            else:
                if self._invitation.user_id is None:
                    raise DiscordOperationError(
                        "Unable to resolve user information after sending the friend request."
                    )
                fetched_user = await with_rate_limit_retry(
                    lambda: self._client.fetch_user(int(self._invitation.user_id))
                )
                user_id = fetched_user.id
                username = fetched_user.name
                discriminator = fetched_user.discriminator

            self._invitation.user_id = user_id
            self._invitation.username = username
            self._invitation.discriminator = discriminator
            display_target = (
                f"{username}#{discriminator}" if discriminator else username or str(user_id)
            )
            self._progress.success(f"Friend request sent to {display_target}")
            return FriendRequestResult(
                user_id=user_id,
                username=username,
                discriminator=discriminator,
            )

        try:
            return await with_rate_limit_retry(_operation)
        except discord.HTTPException as exc:
            raise DiscordOperationError(
                f"Failed to send friend request (status {exc.status})."
            ) from exc

    async def create_invite_and_dm(self, guild: discord.Guild, invite: discord.Invite) -> None:
        if not self._invitation.user_id:
            raise DiscordOperationError("Target user ID is required before sending an invite.")

        user_id = int(self._invitation.user_id)
        try:
            user_obj = await with_rate_limit_retry(lambda: self._client.fetch_user(user_id))
        except discord.HTTPException as exc:
            raise DiscordOperationError(
                f"Failed to fetch target user for DM (status {exc.status})."
            ) from exc

        message = (
            f"Hello {user_obj.name}!\n"
            f"You have been invited to join **{guild.name}**.\n"
            f"Use this invite link to join: {invite.url}"
        )
        try:
            dm_channel = await with_rate_limit_retry(user_obj.create_dm)
            await with_rate_limit_retry(lambda: dm_channel.send(message))
        except discord.HTTPException as exc:
            raise DiscordOperationError(
                f"Failed to send invite via DM (status {exc.status})."
            ) from exc
        self._progress.success(f"Invite link sent via DM to {user_obj}.")

    def register_admin_role(self, guild: discord.Guild, role: discord.Role) -> None:
        if self._grant_admin:
            self._admin_roles[guild.id] = role
            self._progress.success(
                f"Administrator role '{role.name}' prepared for {guild.name}."
            )

    async def monitor_member_join(
        self, guild: discord.Guild, timeout: float = 600.0
    ) -> Optional[discord.Member]:
        if not self._grant_admin or not self._invitation.user_id:
            return None

        existing_member = guild.get_member(self._invitation.user_id)
        if existing_member is not None:
            await self._grant_admin_to_member(existing_member)
            return existing_member

        identifier = self._invitation.username or str(self._invitation.user_id)
        self._progress.step(
            f"Waiting for {identifier} to join {guild.name} to grant administrator permissions..."
        )
        try:
            member = await self._client.wait_for(
                "member_join",
                timeout=timeout,
                check=lambda m: m.guild.id == guild.id and m.id == self._invitation.user_id,
            )
        except asyncio.TimeoutError:
            self._progress.warning(
                f"User {self._invitation.raw_identifier} did not join {guild.name} before timeout."
            )
            return None

        await self._grant_admin_to_member(member)
        return member

    async def _grant_admin_to_member(self, member: discord.Member) -> None:
        if not self._grant_admin:
            return
        role = self._admin_roles.get(member.guild.id)
        if role is None:
            return
        try:
            await with_rate_limit_retry(lambda: member.add_roles(role))
        except discord.HTTPException as exc:
            raise DiscordOperationError(
                f"Failed to grant administrator permissions (status {exc.status})."
            ) from exc
        self._progress.success(f"Granted administrator permissions to {member.display_name}.")
