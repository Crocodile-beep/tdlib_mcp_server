import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability

from tdlib_client import TDLibClient, TDLibError

from tools import chat_tools

BASE_DIR = Path(__file__).parent.resolve()
os.chdir(BASE_DIR)
load_dotenv(BASE_DIR / ".env")
logger = logging.getLogger("tdlib-mcp")

server = Server("tdlib-mcp")

client: TDLibClient | None = None


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_me",
            description="Get current authorized user profile",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_dialogs",
            description="Get list of chats with basic info",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Number of chats (max 200)",
                    },
                },
            },
        ),
        Tool(
            name="resolve_username",
            description="Convert @username to chat info",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username without @",
                    },
                },
                "required": ["username"],
            },
        ),
        Tool(
            name="get_chat_info",
            description="Get detailed info about a chat/channel/group",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "integer",
                        "description": "Chat ID",
                    },
                },
                "required": ["chat_id"],
            },
        ),
        Tool(
            name="list_messages",
            description="Get messages from a chat (newest first)",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "integer",
                        "description": "Chat ID",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Number of messages (max 100)",
                    },
                    "from_message_id": {
                        "type": "integer",
                        "default": 0,
                        "description": "Start from this message ID (0 = newest)",
                    },
                },
                "required": ["chat_id"],
            },
        ),
        Tool(
            name="get_message",
            description="Get a single message by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "integer",
                        "description": "Chat ID",
                    },
                    "message_id": {
                        "type": "integer",
                        "description": "Message ID",
                    },
                },
                "required": ["chat_id", "message_id"],
            },
        ),
        Tool(
            name="search_in_chat",
            description="Search messages in a specific chat",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "integer",
                        "description": "Chat ID",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Max results (max 100)",
                    },
                },
                "required": ["chat_id", "query"],
            },
        ),
        Tool(
            name="search_global",
            description="Search messages across all chats",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Max results (max 100)",
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    global client
    try:
        if name == "get_me":
            result = await chat_tools.get_me(client)
        elif name == "list_dialogs":
            result = await chat_tools.list_dialogs(
                client, limit=arguments.get("limit", 50)
            )
        elif name == "resolve_username":
            result = await chat_tools.resolve_username(
                client, username=arguments["username"]
            )
        elif name == "get_chat_info":
            result = await chat_tools.get_chat_info(
                client, chat_id=arguments["chat_id"]
            )
        elif name == "list_messages":
            from tools import message_tools
            result = await message_tools.list_messages(
                client,
                chat_id=arguments["chat_id"],
                limit=arguments.get("limit", 50),
                from_message_id=arguments.get("from_message_id", 0),
            )
        elif name == "get_message":
            from tools import message_tools
            result = await message_tools.get_message(
                client,
                chat_id=arguments["chat_id"],
                message_id=arguments["message_id"],
            )
        elif name == "search_in_chat":
            from tools import search_tools
            result = await search_tools.search_in_chat(
                client,
                chat_id=arguments["chat_id"],
                query=arguments["query"],
                limit=arguments.get("limit", 50),
            )
        elif name == "search_global":
            from tools import search_tools
            result = await search_tools.search_global(
                client,
                query=arguments["query"],
                limit=arguments.get("limit", 50),
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2),
        )]
    except TDLibError as e:
        return [TextContent(type="text", text=f"TDLib error: {e}")]
    except Exception as e:
        logger.exception(f"Error in {name}")
        return [TextContent(type="text", text=f"Error: {e}")]


async def main():
    global client

    api_id = int(os.getenv("TDLIB_API_ID", "0"))
    api_hash = os.getenv("TDLIB_API_HASH", "")
    phone = os.getenv("TDLIB_PHONE_NUMBER", "")
    proxy_host = os.getenv("TDLIB_PROXY_HOST", "")
    proxy_port = int(os.getenv("TDLIB_PROXY_PORT", "0"))

    if not api_id or not api_hash:
        logger.error("TDLIB_API_ID and TDLIB_API_HASH must be set in .env")
        return

    client = TDLibClient(
        lib_path=str(BASE_DIR / "lib/libtdjson.so"),
        api_id=api_id,
        api_hash=api_hash,
        phone=phone,
        proxy_host=proxy_host,
        proxy_port=proxy_port,
    )

    await client.start()
    logger.info("TDLib client ready")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="tdlib-mcp",
                server_version="0.1.0",
                capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=True)),
            ),
        )

    client.stop()


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(main())
