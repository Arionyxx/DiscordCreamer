# Discord Server Management CLI Bot

> ⚠️ **Warning:** Automating user accounts on Discord using tokens violates Discord's Terms of Service. This project is provided for educational purposes only. Proceed at your own risk.

## Overview

This command-line utility provisions Discord servers using a user token. It guides you through entering a token, defining server names, inviting a target user, and optionally notifying a webhook when provisioning completes.

## Features

- Interactive CLI with safety warnings and guided prompts
- Batch creation of Discord servers
- Automatic friend requests, direct messages with invite links, and optional admin role assignment for the invited user
- Optional webhook notifications summarizing provisioning results
- Rate-limit aware API interactions and comprehensive error handling

## Getting Started

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the CLI:

   ```bash
   python main.py
   ```

Follow the interactive prompts to provide your user token, server names, invitation details, and webhook configuration.

## Security Notes

- Tokens are never written to disk and are only stored in memory for the duration of the session.
- Avoid sharing your token. Automating user accounts may result in Discord account termination.

## Project Structure

```
.
├── discord_cli
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── discord_client.py
│   ├── errors.py
│   ├── invitations.py
│   ├── progress.py
│   ├── utils.py
│   └── webhook.py
├── main.py
├── requirements.txt
└── README.md
```

Each module focuses on a single concern—CLI interactions, configuration, Discord API operations, invitation workflows, and webhook integration.
