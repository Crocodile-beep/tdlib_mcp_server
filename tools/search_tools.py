from tdlib_client import TDLibClient


def _format_message(msg: dict, chat_title: str = "") -> dict:
    content = msg.get("content", {})
    text = ""
    if content.get("@type") == "messageText":
        text = content.get("text", {}).get("text", "")
    return {
        "id": msg.get("id"),
        "chat_id": msg.get("chat_id"),
        "chat_title": chat_title,
        "date": msg.get("date"),
        "content": {"type": "text", "text": text},
    }


async def search_in_chat(
    client: TDLibClient,
    chat_id: int,
    query: str,
    limit: int = 50,
) -> dict:
    response = await client.send_request({
        "@type": "searchChatMessages",
        "chat_id": chat_id,
        "query": query,
        "limit": limit,
        "offset": 0,
        "from_message_id": 0,
        "filter": {"@type": "searchMessagesFilterEmpty"},
    })
    messages = response.get("messages", [])
    return {
        "count": len(messages),
        "messages": [_format_message(m) for m in messages],
    }


async def search_global(
    client: TDLibClient,
    query: str,
    limit: int = 50,
) -> dict:
    response = await client.send_request({
        "@type": "searchMessages",
        "query": query,
        "limit": limit,
        "offset": 0,
        "offset_message_id": 0,
        "offset_chat_id": 0,
        "filter": {"@type": "searchMessagesFilterEmpty"},
    })
    messages = response.get("messages", [])
    return {
        "count": len(messages),
        "messages": [
            _format_message(m, chat_title=m.get("chat_title", ""))
            for m in messages
        ],
    }
