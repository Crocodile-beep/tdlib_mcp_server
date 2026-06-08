#!/usr/bin/env python3
import ctypes, json, os, sys
from dotenv import load_dotenv
load_dotenv()

API_ID = int(os.getenv("TDLIB_API_ID", "0"))
API_HASH = os.getenv("TDLIB_API_HASH", "")
PHONE = os.getenv("TDLIB_PHONE_NUMBER", "")
PROXY_HOST = os.getenv("TDLIB_PROXY_HOST", "")
PROXY_PORT = int(os.getenv("TDLIB_PROXY_PORT", "0"))
if not API_ID or not API_HASH:
    print("❌ Нет ключей в .env"); sys.exit(1)

lib = ctypes.CDLL("lib/libtdjson.so")
lib.td_set_log_verbosity_level(2)  # показываем warnings

lib.td_json_client_create.restype = ctypes.c_void_p
lib.td_json_client_send.restype = None
lib.td_json_client_send.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.td_json_client_receive.restype = ctypes.c_char_p
lib.td_json_client_receive.argtypes = [ctypes.c_void_p, ctypes.c_double]
lib.td_json_client_destroy.restype = None
lib.td_json_client_destroy.argtypes = [ctypes.c_void_p]

client = lib.td_json_client_create()
print("✅ Клиент создан")

def send(obj):
    lib.td_json_client_send(client, json.dumps(obj).encode())

def wait_auth(target_states: set, timeout=30):
    """Читает обновления пока не увидит одно из target_states"""
    import time
    start = time.time()
    while time.time() - start < timeout:
        raw = lib.td_json_client_receive(client, 1.0)
        if raw:
            u = json.loads(raw)
            t = u.get("@type")
            if t == "updateAuthorizationState":
                s = u["authorization_state"]["@type"]
                print(f"  🔐 {s}")
                if s in target_states:
                    return s
            elif t == "updateConnectionState":
                s = u["state"]["@type"]
                print(f"  🌐 connection: {s}")
            elif t == "error":
                print(f"  ❌ {u['code']}: {u['message']}")
                return None
    print("  ⏰ timeout")
    return None

# 1. Ждем authorizationStateWaitTdlibParameters
state = wait_auth({"authorizationStateWaitTdlibParameters"})
if state is None: exit(1)

# 2. Отправляем параметры (flat format для 1.8.6+)
BASE = os.path.abspath(".")
send({
    "@type": "setTdlibParameters",
    "use_test_dc": False,
    "api_id": API_ID,
    "api_hash": API_HASH,
    "system_language_code": "en",
    "device_model": "Desktop",
    "system_version": "Linux",
    "application_version": "1.0.0",
    "database_directory": os.path.join(BASE, "data", "tdlib"),
    "files_directory": os.path.join(BASE, "data", "tdlib", "files"),
    "use_file_database": True,
    "use_chat_info_database": True,
    "use_message_database": True,
    "use_secret_chats": False,
    "enable_storage_optimizer": True,
    "ignore_file_names": False,
})

# 3. Настраиваем прокси (до подключения к Telegram)
if PROXY_HOST and PROXY_PORT:
    send({
        "@type": "addProxy",
        "server": PROXY_HOST,
        "port": PROXY_PORT,
        "enable": True,
        "type": {"@type": "proxyTypeHttp", "username": "", "password": "", "http_only": False},
    })
    print(f"🌐 Прокси {PROXY_HOST}:{PROXY_PORT} (HTTP) настроен")

# 4. Ждем запрос номера
state = wait_auth({"authorizationStateWaitPhoneNumber"}, timeout=60)
if state is None: exit(1)

# 4. Отправляем номер
if not PHONE:
    PHONE = input("📞 Номер телефона: ")
send({"@type": "setAuthenticationPhoneNumber", "phone_number": PHONE})
print(f"📞 Отправлен номер {PHONE}")

# 5. Ждем код
state = wait_auth({"authorizationStateWaitCode", "authorizationStateReady",
                    "authorizationStateWaitPassword"}, timeout=120)
if state == "authorizationStateReady":
    print("\n✅ УЖЕ АВТОРИЗОВАН!")
elif state == "authorizationStateWaitCode":
    code = input("🔑 Код из Telegram: ")
    send({"@type": "checkAuthenticationCode", "code": code.strip()})
    state = wait_auth({"authorizationStateReady", "authorizationStateWaitPassword"}, timeout=30)
    if state == "authorizationStateReady":
        print("\n✅ АВТОРИЗАЦИЯ УСПЕШНА!")
    elif state == "authorizationStateWaitPassword":
        pwd = input("🔒 Пароль 2FA: ")
        send({"@type": "checkAuthenticationPassword", "password": pwd})
        state = wait_auth({"authorizationStateReady"}, timeout=30)
        if state == "authorizationStateReady":
            print("\n✅ АВТОРИЗАЦИЯ УСПЕШНА!")
elif state == "authorizationStateWaitPassword":
    pwd = input("🔒 Пароль 2FA: ")
    send({"@type": "checkAuthenticationPassword", "password": pwd})
    state = wait_auth({"authorizationStateReady"}, timeout=30)
    if state == "authorizationStateReady":
        print("\n✅ АВТОРИЗАЦИЯ УСПЕШНА!")

# 6. getMe
if state == "authorizationStateReady":
    send({"@type": "getMe"})
    import time
    for _ in range(20):
        raw = lib.td_json_client_receive(client, 1.0)
        if raw:
            u = json.loads(raw)
            if u.get("@type") != "updateAuthorizationState":
                print(f"\n👤 Профиль:\n{json.dumps(u, ensure_ascii=False, indent=2)}")
                break

lib.td_json_client_destroy(client)
