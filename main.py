from __future__ import annotations

import asyncio

import discord

from discord_cli import (
    DiscordProvisioner,
    collect_session_configuration,
    display_summary,
)
from discord_cli.errors import ConfigurationError, DiscordCliError
from discord_cli.progress import ProgressPrinter
from discord_cli.webhook import WebhookNotifier


async def _async_main() -> None:
    progress = ProgressPrinter()

    try:
        config = collect_session_configuration()
    except ConfigurationError as exc:
        progress.error(str(exc))
        return

    progress.step("Starting Discord provisioning workflow...")

    webhook_notifier = WebhookNotifier(config.webhook, progress) if config.webhook else None
    provisioner = DiscordProvisioner(config, progress=progress, webhook=webhook_notifier)

    try:
        results = await provisioner.execute()
    except DiscordCliError as exc:
        progress.error(str(exc))
    except discord.LoginFailure:
        progress.error("Failed to authenticate with Discord. Please verify your token.")
    except Exception as exc:  # noqa: BLE001
        progress.error(f"An unexpected error occurred: {exc}")
    else:
        display_summary(results, progress=progress)
    finally:
        if webhook_notifier:
            await webhook_notifier.close()


def main() -> None:
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")


if __name__ == "__main__":
    main()
