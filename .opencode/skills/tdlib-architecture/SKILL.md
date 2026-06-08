---
name: tdlib-architecture
description: "Архитектура tdlib-mcp-server: слои системы, поток данных, как Python общается с libtdjson.so через ctypes, ключевые решения."
---

# TDLib MCP — Архитектура

## Слои системы (снизу вверх)

```
┌─────────────────────────────────────────────────────────────┐
│  OpenCode / Claude Code / Cursor (MCP client)               │
└──────────────────────────┬──────────────────────────────────┘
                           │ MCP protocol (stdio, JSON-RPC)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  main.py — FastAPI + MCP stdio transport                    │
│  • Регистрация инструментов (list_tools)                    │
│  • Обработка вызовов (call_tool)                            │
│  • Маршрутизация к tools/*                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ async Python calls
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  tools/chat_tools.py, message_tools.py, search_tools.py     │
│  • Бизнес-логика каждого MCP-инструмента                    │
│  • Валидация входных параметров                             │
│  • Преобразование Python dict ↔ TDLib JSON                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ sync method calls
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  tdlib_client.py — обёртка над libtdjson.so                 │
│  • ctypes.CDLL загрузка библиотеки                          │
│  • send/receive JSON-объектов                               │
│  • Управление жизненным циклом клиента                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ C function calls через ctypes
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  libtdjson.so (TDLib v1.8.57, 24MB)                         │
│  • Сетевая логика (MTProto)                                 │
│  • Шифрование                                               │
│  • SQLite кэш сообщений                                     │
│  • Обработка обновлений                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ MTProto
                           ▼
                    Telegram Servers
```

## Поток данных (один вызов)

1. AI-агент вызывает MCP-инструмент через stdio
2. `main.py` парсит JSON-RPC запрос, находит обработчик
3. `main.py` вызывает `await tools.chat_tools.list_dialogs(client, limit=20)`
4. Tool отправляет `{"@type": "getChats", "limit": 20}` в TDLib
5. `tdlib_client.py` сериализует в JSON, вызывает `td_json_client_send()`
6. `libtdjson.so` отправляет MTProto-запрос на серверы Telegram
7. Ответ приходит в `td_json_client_receive()` как JSON-строка
8. Tool парсит JSON, возвращает результат в `main.py`
9. `main.py` упаковывает в JSON-RPC ответ, отправляет агенту

## Ключевые архитектурные решения

### Почему отдельный tdlib_client.py
- Инкапсулирует ctypes-детали в одном месте
- Легко тестировать (можно mock C-функции)
- Изолирует TDLib-специфику от бизнес-логики tools/

### Почему FastAPI + MCP, а не чистый MCP SDK
- FastAPI даёт async/await из коробки
- Потенциально можно подключить HTTP-клиентов в будущем
- MCP транспорт всё равно stdio (через `stdio_server()`)

### Почему snake_case для tool names
- Стандарт Python-экосистемы
- Агенты (Claude, GPT) одинаково хорошо читают любой case
- Совместимо с PEP 8

## Мост Python ↔ C (ctypes)

```python
# Загрузка библиотеки
lib = ctypes.CDLL('/path/to/libtdjson.so')

# Сигнатуры функций (обязательно для ctypes)
lib.td_json_client_create.restype = ctypes.c_void_p
lib.td_json_client_create.argtypes = []

lib.td_json_client_send.restype = None
lib.td_json_client_send.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

lib.td_json_client_receive.restype = ctypes.c_char_p
lib.td_json_client_receive.argtypes = [ctypes.c_void_p, ctypes.c_double]

# Вызов
handle = lib.td_json_client_create()
request = json.dumps({"@type": "getMe"}).encode('utf-8')
lib.td_json_client_send(handle, request)
response_json = lib.td_json_client_receive(handle, 1.0)
```

## Загрузка скилла
Когда обсуждаем: архитектуру, слои, мост Python↔C, ctypes, принятые решения.
