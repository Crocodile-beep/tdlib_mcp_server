from tdlib_client import TDLibClient


async def get_me(client: TDLibClient) -> dict:
    response = await client.send_request({"@type": "getMe"})
    return {
        "id": response.get("id"),
        "first_name": response.get("first_name"),
        "last_name": response.get("last_name"),
        "username": response.get("username"),
        "phone_number": response.get("phone_number"),
        "is_premium": response.get("is_premium", False),
        "type": "user",
    }


async def resolve_username(client: TDLibClient, username: str) -> dict:
    response = await client.send_request({
        "@type": "searchPublicChat",
        "username": username,
    })
    chat_type = list(response.get("type", {}).keys())[0] if response.get("type") else "unknown"
    return {
        "id": response.get("id"),
        "title": response.get("title", ""),
        "type": chat_type,
        "username": response.get("username", ""),
    }


async def get_chat_info(client: TDLibClient, chat_id: int) -> dict:
    response = await client.send_request({
        "@type": "getChat",
        "chat_id": chat_id,
    })
    chat_type = list(response.get("type", {}).keys())[0] if response.get("type") else "unknown"
    return {
        "id": response.get("id"),
        "title": response.get("title", ""),
        "type": chat_type,
        "username": response.get("username", ""),
        "description": response.get("description", ""),
        "permissions": response.get("permissions"),
        "photo": response.get("photo"),
    }


async def list_dialogs(client: TDLibClient, limit: int = 50) -> dict:
    response = await client.send_request({
        "@type": "getChats",
        "chat_list": {"@type": "chatListMain"},
        "limit": limit,
    })
    chat_ids = response.get("chat_ids", [])

    chats = []
    for chat_id in chat_ids[:limit]:
        try:
            chat = await get_chat_info(client, chat_id)
            chats.append(chat)
        except Exception:
            chats.append({"id": chat_id, "title": "<error>", "type": "unknown"})

    return {"total_count": len(chats), "chats": chats}
