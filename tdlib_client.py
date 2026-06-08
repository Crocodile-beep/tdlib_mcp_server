import asyncio
import ctypes
import json
import logging
import os
import queue
import threading
import time
import uuid

logger = logging.getLogger("tdlib-mcp")


class TDLibError(Exception):
    pass


class TDLibClient:
    def __init__(
        self,
        lib_path: str,
        api_id: int,
        api_hash: str,
        phone: str = "",
        database_dir: str = "data/tdlib",
        proxy_host: str = "",
        proxy_port: int = 0,
    ):
        self._api_id = api_id
        self._api_hash = api_hash
        self._phone = phone
        self._database_dir = os.path.abspath(database_dir)
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port

        self._lib = ctypes.CDLL(lib_path)
        self._setup_ctypes()

        self._client: int | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._request_queue: queue.Queue = queue.Queue()
        self._pending: dict[str, asyncio.Future] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()

    def _setup_ctypes(self):
        self._lib.td_set_log_verbosity_level(1)
        for f, restype, argtypes in [
            ("td_json_client_create", ctypes.c_void_p, []),
            ("td_json_client_send", None, [ctypes.c_void_p, ctypes.c_char_p]),
            ("td_json_client_receive", ctypes.c_char_p, [ctypes.c_void_p, ctypes.c_double]),
            ("td_json_client_destroy", None, [ctypes.c_void_p]),
        ]:
            fn = getattr(self._lib, f)
            fn.restype = restype
            fn.argtypes = argtypes

    def _send(self, request: dict):
        payload = json.dumps(request).encode("utf-8")
        self._lib.td_json_client_send(self._client, payload)

    def _receive(self, timeout: float = 1.0) -> dict | None:
        raw = self._lib.td_json_client_receive(self._client, timeout)
        return json.loads(raw) if raw else None

    def _drain(self, timeout: float = 0.1):
        while self._receive(timeout) is not None:
            pass

    def _wait_for_auth_state(self, target: set, timeout: float = 30) -> str | None:
        start = time.time()
        while time.time() - start < timeout:
            upd = self._receive(1.0)
            if not upd:
                continue
            t = upd.get("@type")
            if t == "updateAuthorizationState":
                state = upd["authorization_state"]["@type"]
                if state in target:
                    return state
            elif t == "error":
                raise TDLibError(f"{upd['code']}: {upd['message']}")
        return None

    def _auth_flow(self):
        self._wait_for_auth_state({"authorizationStateWaitTdlibParameters"})

        self._send({
            "@type": "setTdlibParameters",
            "use_test_dc": False,
            "api_id": self._api_id,
            "api_hash": self._api_hash,
            "system_language_code": "en",
            "device_model": "tdlib-mcp-server",
            "system_version": "1.0",
            "application_version": "1.0.0",
            "database_directory": self._database_dir,
            "files_directory": os.path.join(self._database_dir, "files"),
            "use_file_database": True,
            "use_chat_info_database": True,
            "use_message_database": True,
            "use_secret_chats": False,
            "enable_storage_optimizer": True,
            "ignore_file_names": False,
        })

        if self._proxy_host and self._proxy_port:
            self._send({
                "@type": "addProxy",
                "server": self._proxy_host,
                "port": self._proxy_port,
                "enable": True,
                "type": {
                    "@type": "proxyTypeHttp",
                    "username": "",
                    "password": "",
                    "http_only": False,
                },
            })

        state = self._wait_for_auth_state(
            {"authorizationStateWaitPhoneNumber", "authorizationStateReady"},
            timeout=60,
        )
        if state is None:
            raise TDLibError("Timeout waiting for phone prompt")

        if state == "authorizationStateWaitPhoneNumber":
            if not self._phone:
                raise TDLibError("Phone required but not set")
            self._send({"@type": "setAuthenticationPhoneNumber", "phone_number": self._phone})
            state = self._wait_for_auth_state(
                {"authorizationStateWaitCode", "authorizationStateReady"},
                timeout=120,
            )
            if state == "authorizationStateWaitCode":
                raise TDLibError(
                    "Auth code required. Run test_auth.py first, then restart."
                )

        if state != "authorizationStateReady":
            raise TDLibError(f"Unexpected state: {state}")

    def _resolve_pending(self, extra: str, response: dict):
        future = self._pending.pop(extra, None)
        if future and not future.done():
            self._loop.call_soon_threadsafe(future.set_result, response)

    def _tdlib_thread(self):
        self._error = None
        try:
            self._client = self._lib.td_json_client_create()
            logger.info("TDLib client created")

            self._auth_flow()
            logger.info("Authorization ready")

            self._drain(0.5)

            self._ready.set()

            while self._running:
                try:
                    request = self._request_queue.get(timeout=1.0)
                except queue.Empty:
                    self._drain(0.1)
                    continue

                if "@extra" not in request:
                    continue
                req_id = request["@extra"]
                timeout = request.pop("_timeout", 30.0)
                logger.debug(f"Sending request @extra={req_id[:8]} type={request.get('@type')}")
                self._send(request)

                start = time.time()
                while time.time() - start < timeout:
                    response = self._receive(1.0)
                    if not response:
                        continue
                    resp_type = response.get("@type")
                    resp_extra = response.get("@extra", "")
                    if resp_extra and resp_extra in self._pending:
                        logger.debug(f"Got response @extra={resp_extra[:8]} type={resp_type}")
                        self._resolve_pending(resp_extra, response)
                        break
        except Exception as e:
            logger.exception("TDLib thread crashed")
            self._error = e
        finally:
            self._ready.set()
            if self._client:
                self._lib.td_json_client_destroy(self._client)
                self._client = None

    async def start(self):
        self._loop = asyncio.get_event_loop()
        self._running = True
        self._thread = threading.Thread(target=self._tdlib_thread, daemon=True)
        self._thread.start()

        await asyncio.get_event_loop().run_in_executor(None, self._ready.wait, 180)
        if not self._ready.is_set():
            raise TDLibError("Timeout starting TDLib client")
        if self._error:
            raise TDLibError(f"Startup failed: {self._error}")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    async def send_request(self, request: dict, timeout: float = 30.0) -> dict:
        req_id = str(uuid.uuid4())
        request["@extra"] = req_id

        future = self._loop.create_future()
        self._pending[req_id] = future
        self._request_queue.put(request)

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            if response.get("@type") == "error":
                raise TDLibError(f"{response['code']}: {response['message']}")
            return response
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise TDLibError("Request timeout")
