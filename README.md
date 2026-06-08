# tdlib-mcp-server

**Open-source MCP server** that connects AI agents to Telegram via the official TDLib (Telegram Database Library).

Unlike other Telegram MCP servers (GramJS, Telethon), this uses the **official C++ library** via Python `ctypes`. Your account is treated as an official client (like Telegram Desktop) — no unofficial client flags.

## Features

| Tool | Description |
|------|-------------|
| `get_me` | Get current authorized user profile |
| `list_dialogs` | List chats with basic info |
| `resolve_username` | Convert @username to chat info |
| `get_chat_info` | Get detailed chat/channel/group info |
| `list_messages` | Get messages from a chat (newest first) |
| `get_message` | Get a single message by ID |
| `search_in_chat` | Search messages in a specific chat |
| `search_global` | Search messages across all chats |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Crocodile-beep/tdlib_mcp_server.git
cd tdlib_mcp_server

# 2. Create venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure API credentials
cp .env.example .env
# Edit .env with your api_id, api_hash from https://my.telegram.org/apps

# 4. First-time auth
python test_auth.py
# Enter the code sent to Telegram

# 5. Run MCP server
python main.py
```

### MCP Client Configuration

Add to your `opencode.jsonc`:

```json
{
  "mcp": {
    "tdlib": {
      "type": "local",
      "command": ["./venv/bin/python", "-u", "./main.py"],
      "enabled": true
    }
  }
}
```

For other MCP clients (Claude Desktop, etc.), point them to `python /path/to/tdlib-mcp-server/main.py`.

## Architecture

```
┌──────────────┐    queue.Queue     ┌──────────────────┐
│  asyncio     │ ──────────────────>│  TDLib Thread    │
│  MCP Server  │                    │  libtdjson.so    │
│  (main.py)   │ <──────────────────│  (tdlib_client)  │
│              │   asyncio.Future   │                  │
└──────────────┘                    └──────────────────┘
```

- **Python 3.14** — MCP stdio transport via `mcp` SDK
- **TDLib 1.8.57** — compiled `libtdjson.so` in `lib/`
- **ctypes** — direct C function calls, no bindings
- **SQLite** — session data stored in `data/tdlib/` (managed by TDLib)

## Roadmap

- `list_messages_date_range` — filter messages by date
- Error handling — FLOOD_WAIT retry, reconnection
- More tools as needed

## License

MIT — fully open source, use it freely.
