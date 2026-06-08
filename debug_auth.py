import ctypes, json, os, time
from dotenv import load_dotenv
load_dotenv()

lib = ctypes.CDLL("lib/libtdjson.so")

# Настройка ctypes
lib.td_json_client_create.restype = ctypes.c_void_p
lib.td_json_client_create.argtypes = []
lib.td_json_client_send.restype = None
lib.td_json_client_send.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.td_json_client_receive.restype = ctypes.c_char_p
lib.td_json_client_receive.argtypes = [ctypes.c_void_p, ctypes.c_double]
lib.td_json_client_destroy.restype = None
lib.td_json_client_destroy.argtypes = [ctypes.c_void_p]

client = lib.td_json_client_create()
print("✅ Клиент создан:", hex(client))

# Дренаж начальных событий
print("--- Дренаж ---")
for _ in range(20):
    r = lib.td_json_client_receive(client, 0.5)
    if r:
        print("  ", r.decode())

# Параметры (flat format for 1.8.6+)
BASE = os.path.abspath(".")
print("\n--- Отправляю setTdlibParameters ---")
lib.td_json_client_send(client, json.dumps({
    "@type": "setTdlibParameters",
    "use_test_dc": False,
    "api_id": int(os.getenv("TDLIB_API_ID")),
    "api_hash": os.getenv("TDLIB_API_HASH"),
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
}).encode())

print("--- Жду ответ на setTdlibParameters (60s) ---")
found_phone = False
for _ in range(60):
    r = lib.td_json_client_receive(client, 1.0)
    if r:
        u = json.loads(r)
        t = u.get("@type")
        if t == "updateAuthorizationState":
            s = u["authorization_state"]["@type"]
            print("  AUTH:", s)
            if s == "authorizationStateWaitPhoneNumber":
                found_phone = True
                break
        elif t == "error":
            print("  ERROR:", u["code"], u["message"])
        elif t == "updateOption":
            pass  # игнорируем
        else:
            print("  OTHER:", t)

if not found_phone:
    print("❌ Не дождались authorizationStateWaitPhoneNumber")
    lib.td_json_client_destroy(client)
    exit(1)

# Отправляем номер
print("\n--- Отправляю номер телефона ---")
lib.td_json_client_send(client, json.dumps({
    "@type": "setAuthenticationPhoneNumber",
    "phone_number": os.getenv("TDLIB_PHONE_NUMBER", ""),
}).encode())

print("--- Жду ответ (120s) ---")
for i in range(120):
    r = lib.td_json_client_receive(client, 1.0)
    if r:
        u = json.loads(r)
        print(f"  [{i}] {json.dumps(u, ensure_ascii=False)}")
        t = u.get("@type")
        if t == "updateAuthorizationState":
            s = u["authorization_state"]["@type"]
            if s in ("authorizationStateWaitCode", "authorizationStateReady", "authorizationStateWaitPassword"):
                print(f"\n🎯 ДОЖДАЛИСЬ: {s}")
                break
    else:
        if i % 10 == 0 and i > 0:
            print(f"  [{i}] ... тишина ...")

lib.td_json_client_destroy(client)
print("\n🏁 Готово")
