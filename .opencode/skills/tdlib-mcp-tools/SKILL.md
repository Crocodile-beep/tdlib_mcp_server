---
name: tdlib-mcp-tools
description: "Справочник по 8 MVP MCP-инструментам tdlib-mcp-server: названия, схемы, когда использовать, примеры композиции."
---

# MCP Tools — Справочник

Текущий MVP: 8 инструментов в 4 категориях.

## 1. Profile

### `get_me`
Профиль авторизованного аккаунта.

```json
{
  "input": {},
  "output": {
    "id": 123456789,
    "first_name": "Адиль",
    "username": "adil",
    "phone_number": "+7...",
    "is_premium": false
  }
}
```

**Когда:** первая проверка после запуска — залогинен ли, кто я.

## 2. Dialogs

### `list_dialogs`
Список чатов.

```json
{
  "input": {
    "limit": 20,              // default 20
    "folder": 0,              // опционально, ID папки
    "only_unread": false      // default false
  },
  "output": {
    "total_count": 42,
    "chats": [{"id": 123, "title": "...", "type": "private", "unread_count": 3}]
  }
}
```

**Когда:** "покажи мои чаты", "что непрочитанного?", "найди чат X".

## 3. Messages

### `list_messages`
История сообщений из чата.

```json
{
  "input": {
    "chat_id": 123456789,    // required
    "limit": 50,              // default 50
    "from_message_id": 0      // 0 = с самых новых
  }
}
```

**Когда:** "покажи последние 20 сообщений в чате X", "что писали вчера?".

### `get_message`
Одно сообщение по ID.

```json
{
  "input": {
    "chat_id": 123456789,    // required
    "message_id": 12345       // required
  }
}
```

**Когда:** точная выборка, когда знаешь конкретный message_id.

### `send_message`
Отправить текстовое сообщение. ⚠️ Мутация!

```json
{
  "input": {
    "chat_id": 123456789,    // required
    "text": "Привет!",        // required, max 4096
    "reply_to_message_id": 0  // опционально
  }
}
```

**Когда:** "отправь сообщение в чат X", "ответь на сообщение Y".

## 4. Search

### `search_in_chat`
Поиск в одном чате.

```json
{
  "input": {
    "chat_id": 123456789,    // required
    "query": "дирижер",       // required
    "limit": 50
  }
}
```

**Когда:** "найди в чате X упоминания Y".

### `search_global`
Поиск по всем чатам. Может быть медленным.

```json
{
  "input": {
    "query": "важная инфа",   // required
    "limit": 100
  }
}
```

**Когда:** "найди где я писал про X", "где упоминалось Y?".

### `resolve_username`
`@username` → chat_id.

```json
{
  "input": {
    "username": "durov"       // required, БЕЗ @
  },
  "output": {"chat_id": 123456789, "type": "user"}
}
```

**Когда:** цепочка: сначала resolve, потом send_message/list_messages.

## Типичные сценарии (композиция)

### "Найди последние 5 сообщений от @durov"
```text
1. resolve_username("durov")     → chat_id: 1234567890
2. list_messages(chat_id, 5)     → массив сообщений
3. Агент форматирует ответ
```

### "Сколько у меня непрочитанных?"
```text
1. list_dialogs(only_unread=true)
2. Сумма unread_count → ответ
```

### "Отправь привет в @channelname"
```text
1. resolve_username("channelname") → chat_id
2. send_message(chat_id, "привет")
3. Результат: статус отправки
```

### "Покажи все упоминания 'AI PM' за последний месяц"
```text
1. list_dialogs(limit=100)        → все чаты
2. Для каждого чата: search_in_chat(query="AI PM", limit=20)
3. Агент агрегирует результаты
```

## Чего пока НЕТ (Phase 2+)

| Хочу | Будет в |
|------|---------|
| `get_user_info` (bio, common chats) | Phase 2 |
| `mark_as_read` | Phase 2 |
| `download_media` | Phase 2 |
| `get_chat_members` | Phase 2 |
| `send_file` | Phase 2 |
| `list_folders` | Phase 2 |
| `edit_message` | Phase 3 |
| `delete_message` | Phase 3 |
| Reactions, polls, stories | Phase 3 |

## Загрузка скилла
Когда добавляешь новый tool, проверяешь существующие, или проектируешь сценарий использования.
