---
name: tdlib-api-reference
description: "Справочник по TDLib JSON API: ctypes-сигнатуры, формат запросов/ответов, жизненный цикл авторизации, rate limits, обработка ошибок."
---

# TDLib API Reference

## C-функции (ctypes)

```python
import ctypes

lib = ctypes.CDLL('/path/to/libtdjson.so')

# Создать клиент
lib.td_json_client_create.restype = ctypes.c_void_p
lib.td_json_client_create.argtypes = []
client = lib.td_json_client_create()  # → handle (int)

# Отправить запрос (async)
lib.td_json_client_send.restype = None
lib.td_json_client_send.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.td_json_client_send(client, json.dumps({"@type": "getMe"}).encode())

# Получить ответ (с таймаутом в секундах)
lib.td_json_client_receive.restype = ctypes.c_char_p
lib.td_json_client_receive.argtypes = [ctypes.c_void_p, ctypes.c_double]
response = lib.td_json_client_receive(client, 1.0)  # → bytes или None

# Уничтожить клиент
lib.td_json_client_destroy.restype = None
lib.td_json_client_destroy.argtypes = [ctypes.c_void_p]
lib.td_json_client_destroy(client)
```

## Логирование TDLib

```python
lib.td_set_log_verbosity_level.argtypes = [ctypes.c_int]
lib.td_set_log_verbosity_level(2)  # 0=fatal, 1=error, 2=warning, 3=info, 4=debug

lib.td_set_log_file_path.argtypes = [ctypes.c_char_p]
lib.td_set_log_file_path(b"/var/log/tdlib.log")

lib.td_set_log_max_file_size.argtypes = [ctypes.c_int64]
lib.td_set_log_max_file_size(100 * 1024 * 1024)  # 100MB
```

## Формат запросов и ответов

### Запрос
```json
{
  "@type": "getMe",
  "@extra": "optional_correlation_id"
}
```

### Ответ (успех)
```json
{
  "@type": "user",
  "id": 123456789,
  "first_name": "Адиль",
  "@extra": "optional_correlation_id"
}
```

### Ответ (ошибка)
```json
{
  "@type": "error",
  "code": 400,
  "message": "Chat not found",
  "@extra": "optional_correlation_id"
}
```

**Ключевые моменты:**
- Поле `@type` — обязательно для всех объектов
- `@extra` — опционально, для корреляции запрос↔ответ (не используем пока)
- Обновления приходят без явного запроса (push)

## Жизненный цикл авторизации

```
setTdlibParameters (api_id, api_hash, database_directory, ...)
    ↓
updateAuthorizationState { @type: "authorizationStateWaitTdlibParameters" }
    ↓ (TDLib обработал параметры)
updateAuthorizationState { @type: "authorizationStateWaitPhoneNumber" }
    ↓
setAuthenticationPhoneNumber { phone_number: "+7..." }
    ↓
updateAuthorizationState { @type: "authorizationStateWaitCode" }
    ↓
checkAuthenticationCode { code: "12345" }
    ↓ (если есть 2FA)
updateAuthorizationState { @type: "authorizationStateWaitPassword" }
    ↓
checkAuthenticationPassword { password: "secret" }
    ↓
updateAuthorizationState { @type: "authorizationStateReady" }
```

**Сессия сохраняется** в `database_directory` — повторная авторизация не нужна.

## Rate Limits

| Действие | Лимит | Обработка |
|----------|-------|-----------|
| Запросы к API | ~30/сек | Батчинг, кэширование |
| Отправка сообщений | ~20/мин в один чат | Очередь |
| `FLOOD_WAIT_X` | Сервер говорит "жди X секунд" | `time.sleep(X)`, retry |

```python
# Обработка FLOOD_WAIT
result = client.receive(1.0)
if result and result.get("@type") == "error":
    if "FLOOD_WAIT" in result.get("message", ""):
        wait = int(result["message"].split("_")[-1])
        logger.warning(f"FLOOD_WAIT: sleeping {wait}s")
        time.sleep(wait)
        # повторить запрос
```

## Типичные методы (для MVP)

| Метод | Что делает |
|-------|------------|
| `getMe` | Профиль текущего пользователя |
| `getChats(limit)` | Список чатов (только ID) |
| `getChat(chat_id)` | Инфо об одном чате |
| `getChatHistory(chat_id, from_message_id, limit)` | История сообщений |
| `getMessage(chat_id, message_id)` | Одно сообщение |
| `searchChatMessages(chat_id, query, limit)` | Поиск в чате |
| `searchMessages(query, limit)` | Глобальный поиск |
| `sendMessage(chat_id, input_message_content)` | Отправить сообщение |
| `resolveUsername(username)` | @username → chat_id |

## Хранение сессии

```
data/tdlib/
├── msg_db/         # SQLite база сообщений
├── file_db/        # Скачанные файлы
└── ...             # Метаданные сессии (зашифрованы)
```

**Важно:** папку `data/tdlib/` НЕ коммитить в git (содержит сессию).

## Загрузка скилла
Когда работаем с TDLib напрямую: пишем новый tool, дебажим вызов, разбираемся с авторизацией или rate limits.
