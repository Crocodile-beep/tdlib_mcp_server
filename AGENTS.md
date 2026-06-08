# Project Context: tdlib-mcp-server

## 1. Core Idea
Open-source MCP (Model Context Protocol) server that connects AI agents to Telegram via the official **TDLib** (Telegram Database Library).

Unlike other Telegram MCP servers (e.g., `beautyfree/mcp-telegram` using GramJS or `chigwell/telegram-mcp` using Telethon), this project uses the **official C++ library** via Python `ctypes`.

**Key Benefit:**
*   **Official Client Status:** Using TDLib means the user's account is treated as an official client (like Telegram Desktop), avoiding the "unofficial client" flag and associated monitoring/bans.
*   **Security:** Full MTProto encryption and official data consistency.

## 2. Architecture
*   **Language:** Python 3.14
*   **MCP Transport:** stdio (via `mcp` SDK)
*   **Telegram Backend:** TDLib v1.8.57 (C++)
*   **Bridge:** `ctypes` (Python calls C functions in `libtdjson.so`)
*   **Data Storage:** SQLite (managed by TDLib in `data/tdlib/`)

## 3. Project Structure
*   `main.py`: MCP server entry point.
*   `tdlib_client.py`: Wrapper for `libtdjson.so`.
*   `tools/`: Business logic for MCP tools.
*   `lib/`: `libtdjson.so` binary.
*   `.env`: API credentials.

## 4. Current Status
*   **Phase:** MVP — 8 tools implemented and working
*   **Goal:** v1.0 stable release with all 9 tools per `docs-specs/mvp-v1-functional-scope.md`
*   **Missing for v1.0:** `list_messages_date_range`, error handling (FLOOD_WAIT retry, reconnection)

## 5. Infrastructure (Что уже есть)

| Компонент | Статус | Подробности |
|-----------|--------|-------------|
| `lib/libtdjson.so` (TDLib v1.8.57) | ✅ Готов | Скомпилирован, лежит в `lib/` |
| `.env` (api_id, api_hash, phone) | ✅ Готов | `chmod 600`, в `.gitignore` |
| `.gitignore` | ✅ Готов | Игнорит `.env`, `data/tdlib/`, `venv/`, `__pycache__/` |
| Авторизация через TDLib | ✅ Протестирована | Полный цикл: params → phone → code → getMe работает |
| Прокси (WSL → Windows) | ✅ Настроен | WSL → Windows → Happy Proxy. Настраивается через `TDLIB_PROXY_HOST` / `TDLIB_PROXY_PORT` в `.env` |
| Spec (`docs-specs/mvp-v1-functional-scope.md`) | ✅ Есть | 9 инструментов в 4 группах |
| Skills (`.opencode/skills/`) | ✅ Есть | api-reference, architecture, conventions, tools, workflows |
| Python venv | ✅ Есть | `venv/` с dotenv, mcp, httpx, pydantic |
| `test_auth.py` | ✅ Есть | Рабочий тест авторизации с прокси |

## 6. Что НУЖНО сделать (Critial Path)

| Компонент | Статус | Описание |
|-----------|--------|----------|
| **`tdlib_client.py`** | ✅ | Класс-обёртка с отдельным TDLib потоком, queue + asyncio.Future, @extra корреляция, auth + proxy |
| **`main.py`** (MCP Entry) | ✅ | MCP stdio transport (mcp SDK v1.27.2). Инициализация TDLibClient, регистрация 8 tools, маршрутизация вызовов |
| **`tools/__init__.py`** | ✅ | Пакет tools |
| **`tools/chat_tools.py`** | ✅ | `get_me`, `list_dialogs`, `resolve_username`, `get_chat_info` |
| **`tools/message_tools.py`** | ✅ | `list_messages`, `get_message` |
| **`tools/search_tools.py`** | ✅ | `search_in_chat`, `search_global` |
| **`list_messages_date_range`** | ❌ | 9-й инструмент — фильтр по дате (не реализован) |
| **Error handling** | ❌ | FLOOD_WAIT retry, reconnection, graceful shutdown |
| **Async wrapper** | ✅ | TDLib sync thread → asyncio.Future bridge через run_in_executor + Event |

## 7. Архитектурные решения (зафиксированы)

1. **Sync → Async bridge**: `asyncio.run_in_executor()` для каждого TDLib вызова (MVP). Потоковый вариант — в Phase 2.
2. **Прокси**: Настраивается через переменные `TDLIB_PROXY_HOST` / `TDLIB_PROXY_PORT` в `.env`.
3. **Сессия**: TDLib сам сохраняет auth state в `data/tdlib/`. Повторная авторизация не нужна.
4. **Формат `setTdlibParameters`**: Flat (без вложенного `parameters`), требуется для TDLib 1.8.6+.

## 8. Constraints
*   **No Telethon/Pyrogram:** Must use official TDLib via ctypes.
*   **No Spam:** Strict anti-spam rules to protect the account.
*   **No Ghost Mode:** Messages must be marked as read.
*   **Dependency Rule:** `tools/*` depend on `tdlib_client.py`, NOT on each other. `main.py` is the only integration point.