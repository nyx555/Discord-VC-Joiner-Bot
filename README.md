# Arox Token VC Joiner Bot

A Discord bot that allows you to join multiple accounts to a voice channel simultaneously using slash commands.

## Features

- Slash command interface for easy use
- Join multiple Discord accounts to a voice channel
- Real-time connection status logging
- Detailed error reporting
- Token management through commands
- Log viewing through Discord
- Administrator-only commands for security

## Prerequisites

- Python 3.7 or higher
- Required Python packages:
  - discord.py
  - websockets
  - asyncio

## Installation

1. Clone or download this repository
2. Install the required packages:
```bash
pip install discord.py websockets
```
3. Create a Discord bot application at [Discord Developer Portal](https://discord.com/developers/applications)
4. Copy your bot token
5. Replace `YOUR_BOT_TOKEN_HERE` in `bot.py` with your actual bot token
6. Invite the bot to your server with the following permissions:
   - Send Messages
   - Read Message History
   - Connect to Voice Channels
   - Use Slash Commands

## Commands

- `/join <server_id> <amount>` - Join a voice channel with specified number of tokens
- `/restock <file>` - Load tokens from a .txt file
- `/clear` - Clear all loaded tokens
- `/logs` - View the latest logs
- `/help` - Show help information

## Usage

1. Start the bot:
```bash
python bot.py
```

2. In Discord:
   - Use `/restock` to upload your tokens.txt file
   - Use `/join` to join a voice channel with your tokens
   - Use `/logs` to view connection status
   - Use `/clear` to remove all loaded tokens

## Logging

The bot generates detailed logs in two ways:
- Console output
- Log file (`token_joiner.log`) containing:
  - Timestamps
  - Connection status
  - Error messages
  - Token connection attempts
  - Voice channel join status

## Security Notes

- All commands require administrator permissions
- Tokens are partially masked in logs (only first 10 characters shown)
- Never share your tokens or log files
- Keep your bot token secure

## Error Handling

The bot includes comprehensive error handling for:
- Connection failures
- Invalid tokens
- Network issues
- Gateway disconnections
- Permission checks
- File validation

## Support

For support, join our Discord server: discord.gg/r1ch

## License

This tool is provided for educational purposes only. Use responsibly and in accordance with Discord's Terms of Service. 