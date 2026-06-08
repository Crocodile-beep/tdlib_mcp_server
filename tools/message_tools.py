from tdlib_client import TDLibClient


def _format_message(msg: dict) -> dict:
    content = msg.get("content", {})
    text = ""
    if content.get("@type") == "messageText":
        text = content.get("text", {}).get("text", "")
    return {
        "id": msg.get("id"),
        "date": msg.get("date"),
        "sender_id": msg.get("sender_id", {}).get("user_id") or msg.get("sender_id", {}).get("chat_id"),
        "content": {"type": "text", "text": text},
        "is_outgoing": msg.get("is_outgoing", False),
        "reply_to_message_id": None,
        "views": msg.get("views", 0),
    }


async def list_messages(
    client: TDLibClient,
    chat_id: int,
    limit: int = 50,
    from_message_id: int = 0,
) -> dict:
    response = await client.send_request({
        "@type": "getChatHistory",
        "chat_id": chat_id,
        "from_message_id": from_message_id,
        "offset": 0,
        "limit": limit,
        "only_local": False,
    })
    messages = response.get("messages", [])
    return {
        "count": len(messages),
        "messages": [_format_message(m) for m in messages],
    }


async def get_message(client: TDLibClient, chat_id: int, message_id: int) -> dict:
    response = await client.send_request({
        "@type": "getMessage",
        "chat_id": chat_id,
        "message_id": message_id,
    })
    return _format_message(response)
