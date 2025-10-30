from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import discord

from .config import ServerRequest, SessionConfig
from .errors import DiscordOperationError
from .invitations import InvitationManager
from .progress import ProgressPrinter
from .utils import with_rate_limit_retry
from .webhook import ProvisioningNotification, WebhookNotifier


@dataclass(slots=True)
class ServerProvisionResult:
    name: str
    guild_id: int
    invite_url: str


class _ProvisioningClient(discord.Client):
    def __init__(
        self,
        config: SessionConfig,
        progress: ProgressPrinter,
        webhook: Optional[WebhookNotifier],
        *,
        intents: Optional[discord.Intents] = None,
    ) -> None:
        intents = intents or discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self._config = config
        self._progress = progress
        self._webhook = webhook
        self._results: List[ServerProvisionResult] = []
        self._invitation_manager: Optional[InvitationManager] = None
        if config.invitation:
            self._invitation_manager = InvitationManager(self, config.invitation, progress)
        self._exception: Optional[BaseException] = None

    @property
    def results(self) -> List[ServerProvisionResult]:
        return self._results

    @property
    def exception(self) -> Optional[BaseException]:
        return self._exception

    async def setup_hook(self) -> None:
        self.loop.create_task(self._execute_provisioning())

    async def on_ready(self) -> None:
        self._progress.success(f"Authenticated as {self.user}.")

    async def close(self) -> None:
        await super().close()

    async def _execute_provisioning(self) -> None:
        try:
            self._progress.step("Connecting to Discord...")
            await self.wait_until_ready()
            if self._invitation_manager:
                self._progress.step("Sending friend request to target user...")
                await self._invitation_manager.send_friend_request()

            for server in self._config.servers:
                result = await self._provision_server(server)
                self._results.append(result)
                if self._webhook:
                    notification = ProvisioningNotification(
                        server_name=result.name,
                        invite_url=result.invite_url,
                        message=f"Server '{result.name}' has been provisioned successfully.",
                    )
                    await self._webhook.notify(notification)

            self._progress.success("All requested servers have been created.")
        except Exception as exc:  # noqa: BLE001
            self._exception = exc
            self._progress.error(f"Provisioning failed: {exc}")
        finally:
            await self.close()

    async def _provision_server(self, request: ServerRequest) -> ServerProvisionResult:
        self._progress.divider()
        self._progress.step(f"Creating server '{request.name}'...")

        async def _create_guild() -> discord.Guild:
            guild_payload = await self.http.create_guild(request.name)
            guild_id = int(guild_payload["id"])
            return await self.fetch_guild(guild_id)

        try:
            guild = await with_rate_limit_retry(_create_guild)
        except discord.Forbidden as exc:
            raise DiscordOperationError("Discord denied the guild creation request.") from exc
        except discord.HTTPException as exc:
            raise DiscordOperationError(
                f"Discord API responded with status {exc.status} while creating the server."
            ) from exc

        self._progress.success(f"Server '{guild.name}' created successfully.")

        text_channel = guild.system_channel
        if text_channel is None:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).create_instant_invite:
                    text_channel = channel
                    break

        if text_channel is None:
            self._progress.step("Creating default text channel for invites...")
            text_channel = await with_rate_limit_retry(lambda: guild.create_text_channel("general"))

        self._progress.step("Generating invite link...")
        invite = await with_rate_limit_retry(
            lambda: text_channel.create_invite(max_age=86400, max_uses=0, unique=True)
        )
        self._progress.success(f"Invite link ready for '{guild.name}'.")

        if self._invitation_manager:
            if self._invitation_manager.should_grant_admin:
                self._progress.step("Preparing administrator role...")
                admin_role = await with_rate_limit_retry(
                    lambda: guild.create_role(
                        name="AutoAdmin",
                        permissions=discord.Permissions(administrator=True),
                    )
                )
                self._invitation_manager.register_admin_role(guild, admin_role)

            await self._invitation_manager.create_invite_and_dm(guild, invite)

            if self._invitation_manager.should_grant_admin:
                await self._invitation_manager.monitor_member_join(guild)

        return ServerProvisionResult(
            name=guild.name,
            guild_id=guild.id,
            invite_url=invite.url,
        )


class DiscordProvisioner:
    """Public facade for executing the provisioning workflow."""

    def __init__(
        self,
        config: SessionConfig,
        progress: Optional[ProgressPrinter] = None,
        webhook: Optional[WebhookNotifier] = None,
    ) -> None:
        self._config = config
        self._progress = progress or ProgressPrinter()
        self._webhook = webhook
        self._client = _ProvisioningClient(config, self._progress, webhook)

    async def execute(self) -> List[ServerProvisionResult]:
        try:
            await self._client.start(self._config.token, reconnect=False)
        finally:
            if self._webhook:
                await self._webhook.close()
        if self._client.exception:
            raise self._client.exception
        return self._client.results
