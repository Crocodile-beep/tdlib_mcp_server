---
title: "MVP Functional Spec v1"
project: "tdlib-mcp-server"
target: "Integration with Dirizher channel workflow"
status: "draft"
version: "1.0"
created: "2026-06-06"
author: "Адиль"
---

# MVP Functional Spec v1 — TDLib MCP Server

## 1. Overview

### Purpose
Первая интеграция MCP-сервера с проектом **Dirizher** — Telegram-каналом «Дирижер Нейросетей».  
Сервер даёт AI-агентам (OpenCode, Claude Code, Cursor) **доступ к контенту Telegram** для:

- **Research** — поиск референсов, трендов, фактов по всем чатам
- **Context Gathering** — извлечение последних сообщений из ключевых источников
- **Fact-Checking** — проверка утверждений через поиск в истории
- **Content Analysis** — чтение каналов конкурентов, тематических групп

### Key Requirement
**Только чтение.** Публикация (`send_message`) НЕ входит в первый скоуп.  
Это conscious decision: сначала поиск и чтение, потом (возможно) публикация.

### Target Workflow in Dirizher

```
Idea → Research → Draft → Quality Check → Publish
         ↑
    TDLib MCP — поиск, контекст, фактчекинг
```

---

## 2. Functional Coverage

Первый скоуп покрывает **4 группы действий**:

| Группа | Что даёт | Инструменты |
|--------|----------|-------------|
| **A. Identity & Discovery** | Навигация: кто я, какие чаты есть, как найти канал по @username | `get_me`, `list_dialogs`, `resolve_username` |
| **B. Content Reading** | Чтение сообщений из чата: последние или конкретные по ID | `list_messages`, `get_message`, `get_chat_info` |
| **C. Search** | Поиск по тексту: глобальный по всем чатам или в одном чате | `search_global`, `search_in_chat` |
| **D. Date Range Queries** | Чтение и поиск с фильтром по датам | `list_messages_date_range`, `search_date_range` |

---

## 3. Tool Specifications

### Group A — Identity & Discovery

---

#### `get_me`

Получить профиль авторизованного аккаунта.

```json
{
  "name": "get_me",
  "description": "Получить информацию о текущем авторизованном Telegram-аккаунте. Используется для проверки статуса авторизации и идентификации аккаунта.",
  "inputSchema": {
    "type": "object",
    "properties": {}
  },
  "output": {
    "id": 123456789,
    "first_name": "Адиль",
    "last_name": null,
    "username": "adil",
    "phone_number": "+71111111111",
    "is_premium": false,
    "type": "user"
  }
}
```

**Use for Dirizher:** Убедиться что сервер подключён к правильному аккаунту.

---

#### `resolve_username`

Преобразовать `@username` в объект пользователя/канала/группы с `chat_id`.

```json
{
  "name": "resolve_username",
  "description": "Преобразовать @username в chat_id и тип сущности. Используется для цепочки вызовов: resolve → затем другие инструменты.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "username": {
        "type": "string",
        "description": "Username БЕЗ символа @. Пример: 'durov', 'ai_news'"
      }
    },
    "required": ["username"]
  },
  "output": {
    "id": 123456789,
    "title": "Pavel Durov",
    "type": "user | channel | supergroup | basicgroup"
  }
}
```

**Use for Dirizher:** Преобразовать `@ai_news` в `chat_id` для поиска/чтения.

---

#### `list_dialogs`

Получить список диалогов (чатов) с базовой информацией.

```json
{
  "name": "list_dialogs",
  "description": "Получить список всех диалогов (личных чатов, групп, каналов). Возвращает ID, название, тип и количество непрочитанных сообщений. Опциональные фильтры: только непрочитанные, только каналы, папка.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "limit": {
        "type": "integer",
        "default": 50,
        "description": "Количество чатов для загрузки (max 200)"
      },
      "filter": {
        "type": "string",
        "enum": ["all", "unread", "channels", "groups", "private"],
        "default": "all",
        "description": "Фильтр по типу чата"
      }
    }
  },
  "output": {
    "total_count": 42,
    "chats": [
      {
        "id": -1001234567890,
        "title": "Дирижер Нейросетей",
        "type": "channel",
        "unread_count": 0,
        "username": "dirizher_ai",
        "last_message_date": 1717689600,
        "last_message_preview": "Сегодняшний пост..."
      }
    ]
  }
}
```

**Use for Dirizher:** «Покажи все каналы, которые у меня есть», «Какие чаты у меня в списке?»

---

### Group B — Content Reading

---

#### `get_chat_info`

Получить расширенную информацию о чате/канале/группе.

```json
{
  "name": "get_chat_info",
  "description": "Получить детальную информацию о чате, канале или группе: название, описание, количество участников, username, дата создания.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "chat_id": {
        "type": "integer",
        "description": "ID чата (можно получить через list_dialogs или resolve_username)"
      }
    },
    "required": ["chat_id"]
  },
  "output": {
    "id": -1001234567890,
    "title": "Дирижер Нейросетей",
    "type": "channel",
    "description": "Голос за практический AI без хайпа",
    "username": "dirizher_ai",
    "member_count": 53,
    "is_verified": false,
    "is_scam": false,
    "is_fake": false,
    "photo": null
  }
}
```

**Use for Dirizher:** «Расскажи про канал @dirizher_ai», «Сколько подписчиков у @ai_news?»

---

#### `list_messages`

Получить сообщения из чата (от новых к старым).

```json
{
  "name": "list_messages",
  "description": "Получить последние сообщения из чата. Сообщения возвращаются от новых к старым. Для пагинации используйте параметр from_message_id.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "chat_id": {
        "type": "integer",
        "description": "ID чата (обязательно)"
      },
      "limit": {
        "type": "integer",
        "default": 50,
        "description": "Количество сообщений (max 100)"
      },
      "from_message_id": {
        "type": "integer",
        "default": 0,
        "description": "ID сообщения, начиная с которого загружать. 0 = с самых новых"
      }
    },
    "required": ["chat_id"]
  },
  "output": {
    "count": 50,
    "messages": [
      {
        "id": 12345,
        "date": 1717689600,
        "sender_id": 123456789,
        "sender_name": "Адиль",
        "content": {
          "type": "text",
          "text": "Текст сообщения"
        },
        "is_outgoing": false,
        "reply_to_message_id": null,
        "views": 53
      }
    ]
  }
}
```

**Use for Dirizher:** «Покажи последние 20 постов из @ai_news», «Что сегодня писали в чате?»

---

#### `get_message`

Получить одно конкретное сообщение по ID.

```json
{
  "name": "get_message",
  "description": "Получить одно сообщение по его chat_id и message_id. Используется для точечного извлечения сообщения, когда известен его ID.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "chat_id": {
        "type": "integer",
        "description": "ID чата"
      },
      "message_id": {
        "type": "integer",
        "description": "ID сообщения"
      }
    },
    "required": ["chat_id", "message_id"]
  },
  "output": {
    "id": 12345,
    "date": 1717689600,
    "sender_id": 123456789,
    "sender_name": "Адиль",
    "content": {
      "type": "text",
      "text": "Полный текст сообщения"
    },
    "views": 53,
    "forward_from": null,
    "reply_to_message_id": 12344
  }
}
```

**Use for Dirizher:** «Найди сообщение 12345 из @ai_news и покажи его», цитирование в посте.

---

### Group C — Search

---

#### `search_in_chat`

Поиск сообщений в одном конкретном чате.

```json
{
  "name": "search_in_chat",
  "description": "Поиск сообщений по текстовому запросу в одном чате. Поддерживает фильтры по типу контента, отправителю и дате.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "chat_id": {
        "type": "integer",
        "description": "ID чата для поиска (обязательно)"
      },
      "query": {
        "type": "string",
        "description": "Поисковый запрос (обязательно). Пример: 'agentic ai', 'дирижер'"
      },
      "limit": {
        "type": "integer",
        "default": 50,
        "description": "Максимум результатов (max 100)"
      },
      "from_date": {
        "type": "integer",
        "description": "Unix timestamp начала периода (опционально)"
      },
      "to_date": {
        "type": "integer",
        "description": "Unix timestamp конца периода (опционально)"
      }
    },
    "required": ["chat_id", "query"]
  },
  "output": {
    "count": 10,
    "messages": [
      {
        "id": 12345,
        "date": 1717689600,
        "content": {
          "type": "text",
          "text": "...найденный текст..."
        },
        "message_link": "https://t.me/username/12345"
      }
    ]
  }
}
```

**Use for Dirizher:** «Найди в @ai_news всё про 'GPT-5' за последний месяц», фактчекинг.

---

#### `search_global`

Поиск сообщений по всем доступным чатам.

```json
{
  "name": "search_global",
  "description": "Глобальный поиск сообщений по всем чатам аккаунта. Поддерживает фильтры по типу чата, дате и лимиту. Внимание: может быть медленным на больших аккаунтах.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Поисковый запрос (обязательно)"
      },
      "limit": {
        "type": "integer",
        "default": 50,
        "description": "Максимум результатов (max 100)"
      },
      "from_date": {
        "type": "integer",
        "description": "Unix timestamp начала периода (опционально)"
      },
      "to_date": {
        "type": "integer",
        "description": "Unix timestamp конца периода (опционально)"
      },
      "chat_type": {
        "type": "string",
        "enum": ["all", "channels", "groups", "private"],
        "default": "all",
        "description": "Тип чата для фильтрации"
      }
    },
    "required": ["query"]
  },
  "output": {
    "count": 15,
    "messages": [
      {
        "id": 12345,
        "chat_id": -1001234567890,
        "chat_title": "Название чата",
        "chat_type": "channel",
        "date": 1717689600,
        "content": {
          "type": "text",
          "text": "...найденный текст..."
        },
        "message_link": "https://t.me/username/12345"
      }
    ]
  }
}
```

**Use for Dirizher:** «Найди всё что писали про 'OpenCode' в моих чатах», «Где упоминался 'Semantic Kernel'?»

---

### Group D — Date Range Queries

---

#### `list_messages_date_range`

Получить сообщения из чата за определённый период времени.

```json
{
  "name": "list_messages_date_range",
  "description": "Получить сообщения из чата за указанный период времени. Используется для аналитики: 'что писали на прошлой неделе', дайджесты, обзоры.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "chat_id": {
        "type": "integer",
        "description": "ID чата (обязательно)"
      },
      "from_date": {
        "type": "integer",
        "description": "Unix timestamp начала периода (обязательно)"
      },
      "to_date": {
        "type": "integer",
        "description": "Unix timestamp конца периода (обязательно)"
      },
      "limit": {
        "type": "integer",
        "default": 100,
        "description": "Максимум сообщений (max 200)"
      }
    },
    "required": ["chat_id", "from_date", "to_date"]
  },
  "output": {
    "count": 15,
    "period": {
      "from": "2026-05-01",
      "to": "2026-05-07"
    },
    "messages": [
      {
        "id": 12345,
        "date": 1717689600,
        "content": {
          "type": "text",
          "text": "..."
        }
      }
    ]
  }
}
```

**Use for Dirizher:** «Покажи все посты @ai_news за прошлую неделю», «Что я писал в своём канале в мае?»

---

#### `search_date_range` (composite — объединяет поиск с date range)

Поиск с датами — это поведенческая фича, не отдельный tool.  
Реализуется через `search_in_chat` + параметры `from_date`/`to_date`.  
Отдельный `search_date_range` не нужен — агент просто передаёт даты в `search_in_chat` или `search_global`.

**Пример запроса агента:**
```
1. resolve_username("ai_news") → chat_id: -1001234567890
2. search_in_chat(chat_id: -1001234567890, query: "GPT-5", from_date: 1750000000, to_date: 1755000000)
```

---

## 4. Implementation Plan

### Sprint 1 — Foundation (3 инструмента)

| # | Инструмент | Сложность | Зависит от |
|---|------------|-----------|------------|
| 1 | `get_me` | ★☆☆ | `tdlib_client.py`, `auth.py` |
| 2 | `list_dialogs` | ★★☆ | `tdlib_client.py` |
| 3 | `resolve_username` | ★☆☆ | `tdlib_client.py` |

### Sprint 2 — Reading (3 инструмента)

| # | Инструмент | Сложность | Зависит от |
|---|------------|-----------|------------|
| 4 | `get_chat_info` | ★☆☆ | `tdlib_client.py` |
| 5 | `list_messages` | ★★☆ | `tdlib_client.py` |
| 6 | `get_message` | ★☆☆ | `tdlib_client.py` |

### Sprint 3 — Search (2 инструмента)

| # | Инструмент | Сложность | Зависит от |
|---|------------|-----------|------------|
| 7 | `search_in_chat` | ★★☆ | `tdlib_client.py` |
| 8 | `search_global` | ★★★ | `tdlib_client.py` (большой объём данных) |

### Sprint 4 — Date Range (1 инструмент)

| # | Инструмент | Сложность | Зависит от |
|---|------------|-----------|------------|
| 9 | `list_messages_date_range` | ★★☆ | `list_messages` |

---

## 5. TDLib API Mapping

Каждому MCP-инструменту соответствует TDLib метод:

| MCP Tool | TDLib Request | Примечание |
|----------|---------------|------------|
| `get_me` | `getMe` | ✅ Async |
| `list_dialogs` | `getChats(limit)` | ✅ Возвращает только ID, нужен `getChat` для каждого |
| `resolve_username` | `searchPublicChat(username)` | ✅ |
| `get_chat_info` | `getChat(chat_id)` | ✅ |
| `list_messages` | `getChatHistory(chat_id, from_message_id, limit)` | ✅ |
| `get_message` | `getMessage(chat_id, message_id)` | ✅ |
| `search_in_chat` | `searchChatMessages(chat_id, query, limit)` | ✅ |
| `search_global` | `searchMessages(query, limit)` | ✅ Возвращает глобальные результаты |
| `list_messages_date_range` | `getChatHistory` + фильтр по `date` client-side | ⚠️ Фильтр на клиенте |

---

## 6. Integration with Dirizher OpenCode

### AGENTS.md reference
Для использования в проекте Dirizher, обновить `idea/dirizher/.opencode/AGENTS.md` —  
добавить ссылку на MCP-сервер в карту файлов.

### .opencode.jsonc
MCP-сервер уже глобально прописан в `~/.config/opencode/opencode.jsonc`.  
Агенты Dirizher могут использовать инструменты как:

```
/agent architect
«Найди в @ai_news всё про Agentic AI за последнюю неделю»
→ TDLib MCP: resolve_username + search_in_chat
```

### Typical Agent Prompts for Dirizher

```text
"Найди в моих чатах все упоминания 'Semantic Kernel' за последний месяц"
→ search_global(query: "Semantic Kernel", from_date: ..., to_date: ...)

"Покажи последние 10 постов из канала @ai_news"
→ resolve_username("ai_news") + list_messages(chat_id: ..., limit: 10)

"Достань сообщение 54321 из канала @dirizher_ai"
→ resolve_username("dirizher_ai") + get_message(chat_id: ..., message_id: 54321)
```

---

## 7. Open Questions

1. **Date range в search_global** — TDLib поддерживает `searchMessages` с фильтром по дате? Или фильтр нужно делать на клиенте?
2. **Пагинация** — как агент запрашивает следующую страницу? Через `from_message_id` или offset?
3. **Кэширование** — одни и те же `list_dialogs` вызывает каждый раз round-trip к Telegram?

Эти вопросы решим в процессе имплементации.

---

## 8. Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-06 | 1.0 | Initial spec |
