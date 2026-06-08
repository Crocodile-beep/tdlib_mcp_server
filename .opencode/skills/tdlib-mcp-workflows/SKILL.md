---
name: tdlib-mcp-workflows
description: "Типовые задачи разработки tdlib-mcp-server: добавить новый MCP tool, дебажить TDLib вызов, оптимизировать, подготовить release."
---

# Workflows — Типовые задачи

## 1. Добавить новый MCP-инструмент

**Пример:** добавляем `mark_as_read`.

### Шаг 1: Определить спецификацию
```python
# В голове или в обсуждении с пользователем:
# - Название: mark_as_read
# - Что делает: отметить сообщения прочитанными до message_id
# - Вход: chat_id (int, required), message_id (int, required)
# - Выход: ok / error
```

### Шаг 2: Реализовать в tools/
```python
# tools/message_tools.py (или chat_tools.py, если про чат)

async def mark_as_read(
    client: TDLibClient,
    chat_id: int,
    message_id: int
) -> bool:
    """
    Mark all messages in chat up to message_id as read.

    Args:
        client: TDLib client instance.
        chat_id: Target chat ID.
        message_id: Last read message ID.

    Returns:
        True on success.
    """
    client.send({
        "@type": "viewMessages",
        "chat_id": chat_id,
        "message_ids": [message_id],
        "force_read": False
    })

    # Ждём ответ
    for _ in range(5):
        response = client.receive(timeout=2.0)
        if response and response.get("@type") == "ok":
            return True
        if response and response.get("@type") == "error":
            logger.error(f"viewMessages error: {response}")
            return False
    return False
```

### Шаг 3: Зарегистрировать в main.py
```python
# В list_tools():
Tool(
    name="mark_as_read",
    description="Отметить сообщения в чате прочитанными до указанного message_id.",
    inputSchema={
        "type": "object",
        "properties": {
            "chat_id": {"type": "integer", "description": "ID чата"},
            "message_id": {"type": "integer", "description": "Последний прочитанный message_id"}
        },
        "required": ["chat_id", "message_id"]
    }
)

# В call_tool():
elif name == "mark_as_read":
    chat_id = arguments["chat_id"]
    message_id = arguments["message_id"]
    result = await message_tools.mark_as_read(client, chat_id, message_id)
    return [TextContent(type="text", text=json.dumps({"ok": result}))]
```

### Шаг 4: Обновить документацию
- Добавить в скилл `tdlib-mcp-tools` (таблица)
- Обновить README.md (список инструментов)
- Добавить пример в скилл `tdlib-mcp-tools` (секция "Типичные сценарии")

### Шаг 5: Тестировать
```bash
# Перезапустить сервер
cd /home/msi/tdlib-mcp-server
source venv/bin/activate
python3 main.py

# В OpenCode вызвать tool:
# "Отметь сообщения в чате 1234567890 до message_id 12345 как прочитанные"
```

## 2. Дебажить TDLib вызов

**Симптом:** tool возвращает ошибку или пустой результат.

### Шаг 1: Включить verbose логирование
```python
# В tdlib_client.py:
lib.td_set_log_verbosity_level(4)  # DEBUG
lib.td_set_log_file_path(b"/tmp/tdlib.log")
```

### Шаг 2: Посмотреть сырой JSON
```python
# В tools/*.py, перед client.send():
logger.debug(f"Sending: {json.dumps(request)}")
response = client.receive(timeout=5.0)
logger.debug(f"Response: {response}")
```

### Шаг 3: Проверить ответ вручную
```bash
# Из Python REPL:
import ctypes, json
lib = ctypes.CDLL('/home/msi/tdlib-mcp-server/lib/libtdjson.so')
client = lib.td_json_client_create()

# Отправить запрос
lib.td_json_client_send(client, json.dumps({"@type": "getMe"}).encode())

# Читать ответы в цикле
while True:
    r = lib.td_json_client_receive(client, 2.0)
    if not r: break
    print(json.loads(r))
```

### Шаг 4: Проверить TDLib API docs
- [td_api.tl](https://github.com/tdlib/td/blob/master/td/generate/scheme/td_api.tl) — все методы
- Или скилл `tdlib-api-reference`

## 3. Оптимизировать

### Проблема: list_dialogs возвращает только ID чатов
**Решение:** используй `getChats` (возвращает ID), потом `getChat` для каждого. Или слушай `updateNewChat` для кэша.

### Проблема: каждый вызов — round-trip к TDLib
**Решение:** кэшируй маппинг `chat_id → title` в `tdlib_client.py`.

### Проблема: rate limits при глобальном поиске
**Решение:** `search_global` с `limit=50` достаточно для большинства случаев. Не вызывай чаще 1 раза в 5 секунд.

## 4. Подготовить release

### Чеклист
- [ ] Все инструменты из MVP реализованы и протестированы
- [ ] README.md обновлён (установка, использование, список tools)
- [ ] `.env.example` есть в репо, `.env` в `.gitignore`
- [ ] `requirements.txt` актуален
- [ ] License файл (MIT) добавлен
- [ ] Примеры использования в README
- [ ] Тесты (хотя бы smoke test)
- [ ] GitHub Actions для CI (линтер + pytest)
- [ ] Опубликовать в npm/pip? (опционально)

### Структура README
1. Что это и зачем
2. Почему TDLib, а не альтернативы
3. Установка
4. Конфигурация (API_ID, API_HASH)
5. Список инструментов
6. Примеры использования
7. Contributing
8. License

## 5. Онбординг нового контрибьютора

1. README → понять что это
2. Скилл `tdlib-architecture` → понять слои
3. Скилл `tdlib-structure` → понять файлы
4. Скилл `tdlib-mcp-conventions` → понять conventions
5. Скилл `tdlib-mcp-tools` → понять что уже есть
6. Скилл `tdlib-api-reference` → понять TDLib
7. Скилл `tdlib-mcp-workflows` (этот) → как делать типовые задачи

## Загрузка скилла
Когда добавляешь новый tool, дебажишь, оптимизируешь или готовишь release.
