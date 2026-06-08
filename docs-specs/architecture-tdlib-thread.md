# Архитектура: TDLib Thread + Async MCP Bridge

## Проблема

TDLib (`td_json_client_receive`) — синхронный C-вызов, блокирующий поток. 
MCP сервер работает на asyncio. Напрямую их соединить нельзя.

## Решение: Отдельный поток + очередь + asyncio.Future

```
┌─────────────────────────────────────────────────────────┐
│                   TDLib Thread (фон)                     │
│                                                          │
│  while running:                                          │
│    # 1. Берем запрос от MCP                              │
│    request = requests_queue.get()                        │
│    # 2. Отправляем в TDLib                               │
│    td_json_client_send(client, request)                  │
│                                                          │
│    # 3. Ждем ответ (или таймаут)                         │
│    while True:                                           │
│      response = td_json_client_receive(client, 1.0)      │
│      if not response: break  # таймаут, идем за новым    │
│                                                          │
│      if response.@extra in pending:                      │
│        # Это ответ на наш запрос — возвращаем            │
│        future = pending.pop(response.@extra)             │
│        loop.call_soon_threadsafe(future.set_result)      │
│        break                                             │
│      else:                                               │
│        # Фоновое событие — пропускаем, ждем дальше       │
│        continue                                          │
└───────────────┬──────────────────────────▲──────────────┘
                │                          │
    queue.Queue  │                          │ loop.call_soon_threadsafe
    (thread-safe)│                          │ future.set_result
                ▼                          │
┌─────────────────────────────────────────────────────────┐
│              MCP Server (async, anyio)                   │
│                                                          │
│  async def call_tool(name, arguments):                    │
│    req_id = str(uuid4())                                  │
│    future = loop.create_future()                          │
│    pending[req_id] = future                               │
│    requests_queue.put({..., @extra: req_id})              │
│    result = await asyncio.wait_for(future, timeout=30)    │
│    return result                                          │
└─────────────────────────────────────────────────────────┘
```

## Компоненты

### 1. `requests_queue: queue.Queue`
- thread-safe очередь из стандартной библиотеки
- MCP кладёт запрос, TDLib Thread забирает
- Один запрос за раз (sequential processing)

### 2. `pending: dict[str, asyncio.Future]`
- Словарь `@extra → Future`
- TDLib Thread находит Future по `@extra` и заполняет через `loop.call_soon_threadsafe()`
- MCP сторона await'ит Future с таймаутом

### 3. `@extra` (корреляция)
- Уникальный UUID для каждого запроса
- MCP указывает `@extra` при отправке
- TDLib возвращает его в ответе
- Поток сверяет: если `@extra` есть в `pending` — это наш ответ

### 4. Фоновые события
- Всё что приходит без `@extra` из `pending` — пропускаем
- Не теряются (TDLib хранит в БД), просто не обрабатываем сейчас
- Примеры: `updateNewMessage`, `updateChatPosition`, `updateFile`

## Порядок старта

```
1. MCP Server стартует (async)
2. Создаётся TDLib Thread
3. Поток проходит авторизацию:
   setTdlibParameters → addProxy → getMe (для проверки Ready)
4. После authorizationStateReady:
   MCP регистрирует tools и начинает слушать stdio
5. Каждый call_tool → запрос в очередь → Future → ответ
```

## Почему это правильно для open source

- Чистое разделение: TDLib в одном потоке, MCP в async
- Никаких блокировок event loop
- Возможность позже добавить обработку фоновых событий
- Легко тестировать (можно мокать TDLib Thread через ту же очередь)
- Единый источник правды: все запросы проходят через один `send`
