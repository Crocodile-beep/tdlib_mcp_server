---
name: tdlib-mcp-conventions
description: "Правила кода для tdlib-mcp-server: naming, JSON Schema, async/await, error handling, logging, type hints."
---

# Coding Conventions — tdlib-mcp-server

## Именование

### MCP-инструменты
- **snake_case**: `list_dialogs`, `send_message`, `search_global`
- Глагол + существительное: `get_*`, `list_*`, `search_*`, `send_*`, `mark_*`
- НЕ используем префикс `td_` (он внутри библиотеки)
- НЕ используем camelCase (это не Python-style)

### Python код
- `snake_case` для функций и переменных: `def get_chat_info()`, `chat_id`
- `PascalCase` для классов: `TDLibClient`, `AuthHandler`
- `UPPER_SNAKE_CASE` для констант: `MAX_LIMIT = 100`
- Приватные методы с `_`: `_setup_ctypes()`

### Файлы
- `snake_case.py` для модулей
- `kebab-case` для директорий skills/ (стандарт OpenCode)

## JSON Schema для инструментов

```python
{
    "name": "list_dialogs",
    "description": "Получить список диалогов. Возвращает ID чатов и базовую инфо.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 20,
                "description": "Сколько чатов вернуть (1-100)"
            },
            "only_unread": {
                "type": "boolean",
                "default": False,
                "description": "Только непрочитанные"
            }
        }
        # "required": [] — если нет обязательных полей
    }
}
```

**Правила:**
- Обязательные поля — в `required: [...]`
- Дефолты — в `default:`, не в описании
- `description` — одно предложение, понятное агенту
- Enum'ы — `"enum": ["text", "photo", "video"]`

## Async/Await

- ВСЕ обработчики в `main.py` — `async def`
- Внутри tools/* можно `def` (sync), TDLib вызовы быстрые
- Если tool делает несколько TDLib-вызовов — `async` + `await asyncio.sleep()` между ними

## Type Hints

```python
from typing import Optional, List, Dict, Any

async def list_messages(
    client: TDLibClient,
    chat_id: int,
    limit: int = 50,
    from_message_id: int = 0
) -> List[Dict[str, Any]]:
    """Получить сообщения из чата."""
    ...
```

**Правила:**
- Всегда указываем типы параметров и возврата
- `Optional[T]` для nullable, не `T | None` (Python 3.14 совместимо, но PEP 604)
- `Dict[str, Any]` для JSON-объектов
- `List[T]` для списков

## Error Handling

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        # логика
        result = await some_tool(...)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
    except TDLibError as e:
        # TDLib-специфичная ошибка
        logger.error(f"TDLib error in {name}: {e}")
        return [TextContent(type="text", text=f"TDLib error: {e}")]
    except Exception as e:
        # Непредвиденная ошибка
        logger.exception(f"Unexpected error in {name}")
        return [TextContent(type="text", text=f"Internal error: {e}")]
```

**Правила:**
- Ловим конкретные исключения, не голый `except`
- Логируем с контекстом (имя tool, аргументы)
- Возвращаем `TextContent` с понятным сообщением, НЕ бросаем исключение в MCP

## Логирование

```python
import logging

logger = logging.getLogger('tdlib-mcp')

# В коде:
logger.info(f"Loading TDLib from {lib_path}")
logger.debug(f"Sending request: {request}")
logger.warning(f"FLOOD_WAIT: sleeping {seconds}s")
logger.error(f"Failed to authenticate: {e}")
```

**Уровни:**
- `DEBUG` — детали каждого TDLib-вызова
- `INFO` — запуск сервера, авторизация, важные события
- `WARNING` — `FLOOD_WAIT`, повторные попытки
- `ERROR` — невозможность выполнить запрос

## Docstrings

```python
def send_message(client: TDLibClient, chat_id: int, text: str) -> dict:
    """
    Send a text message to a chat.

    Args:
        client: TDLib client instance.
        chat_id: Target chat ID.
        text: Message text (max 4096 chars).

    Returns:
        TDLib message object on success.

    Raises:
        TDLibError: If FLOOD_WAIT or other Telegram error.
    """
```

**Правила:**
- Google-style docstrings
- На английском (код — на английском)
- Описываем Args, Returns, Raises
- Одна строка summary в начале

## Выходной формат

- **JSON**, не plain text
- `json.dumps(result, ensure_ascii=False, indent=2)` для читаемости
- Минимум полей — только то, что агенту реально нужно
- Даты — Unix timestamp (агенты сами форматируют)

## Архитектурное правило зависимостей

- `tools/*` зависят **только** от `tdlib_client.py`
- `tools/*` **НЕ зависят** друг от друга
- `main.py` — единственная точка интеграции (связывает всё вместе)
- `tdlib_client.py` — единственный доступ к `libtdjson.so`

## Загрузка скилла
Когда пишешь новый код, новый tool, или рефакторишь существующий.
