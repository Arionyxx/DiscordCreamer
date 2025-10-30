from __future__ import annotations

import getpass
from typing import Iterable, List, Optional

from .config import InvitationConfig, SessionConfig, WebhookConfig
from .errors import ConfigurationError
from .progress import ProgressPrinter
from .utils import build_server_requests, parse_target_user

WARNING_BANNER = "=" * 72


def display_intro(progress: Optional[ProgressPrinter] = None) -> None:
    warning = (
        "This tool automates actions on a Discord user account using your token.\n"
        "Using user tokens with automation is against Discord's Terms of Service.\n"
        "Proceed at your own risk. Never share your token and keep it secure."
    )
    banner = f"{WARNING_BANNER}\n⚠️  IMPORTANT WARNING\n{warning}\n{WARNING_BANNER}"
    if progress:
        progress.warning(warning)
    else:
        print(banner)


def _prompt_yes_no(prompt: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        answer = input(prompt + suffix).strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter 'y' or 'n'.")


def _prompt_server_names() -> List[str]:
    while True:
        raw = input(
            "Enter the server name(s) you want to create (comma-separated for multiple): "
        ).strip()
        names = [name.strip() for name in raw.split(",") if name.strip()]
        if names:
            return names
        print("You must provide at least one server name.")


def _prompt_token() -> str:
    print("Your user token will not be displayed and is only used in memory for this session.")
    return getpass.getpass("Enter your Discord user token: ").strip()


def _prompt_webhook_configuration() -> Optional[WebhookConfig]:
    if not _prompt_yes_no("Would you like to send webhook notifications when provisioning completes?", False):
        return None
    url = input("Enter the webhook URL: ").strip()
    if not url:
        print("Webhook URL cannot be empty. Webhook notifications will be disabled.")
        return None
    username = input("Optional: Enter a custom webhook username (leave blank to skip): ").strip()
    return WebhookConfig(enabled=True, url=url, username=username or None)


def _prompt_invitation_configuration() -> Optional[InvitationConfig]:
    print(
        "Provide the target user's Discord ID or username (username#1234) to send a friend request."
    )
    print("Leave blank to skip inviting a user.")
    while True:
        identifier = input("Target user: ").strip()
        if not identifier:
            return None
        try:
            invitation = parse_target_user(identifier)
            break
        except ConfigurationError as exc:
            print(f"Error: {exc}")
            continue
    invitation.grant_admin = _prompt_yes_no(
        "Grant administrator permissions to the invited user automatically?", True
    )
    return invitation


def collect_session_configuration() -> SessionConfig:
    """Interactively gather configuration from the user via CLI prompts."""
    display_intro()
    token = _prompt_token()
    while not token:
        print("Token cannot be empty. Please try again.")
        token = _prompt_token()

    while True:
        server_names = _prompt_server_names()
        try:
            servers = build_server_requests(server_names)
            break
        except ConfigurationError as exc:
            print(f"Error: {exc}")

    invitation = _prompt_invitation_configuration()
    webhook = _prompt_webhook_configuration()

    return SessionConfig(token=token, servers=servers, invitation=invitation, webhook=webhook)


def display_summary(results: Iterable, progress: Optional[ProgressPrinter] = None) -> None:
    """Print a high-level summary of provisioned servers and invite links."""
    lines = ["", "Summary:"]
    for result in results:
        lines.append(f" • {result.name} — Invite: {result.invite_url}")
    message = "\n".join(lines)
    if progress:
        progress.divider()
        progress.info(message)
    else:
        print(message)
