"""Model calls billed to the operator's ChatGPT plan through Sign in with ChatGPT.

Ported from Condere's plan route (owner-approved there on 2026-10-30) without its ledger.
OpenAI documents plan usage for open-source and locally hosted apps
(https://developers.openai.com/siwc/token-sharing-open-source). BackIntel registers itself
dynamically for one ChatGPT account, bound to a persistent host ID. Credentials live in a
private local directory (`BACKINTEL_CHATGPT_HOME`, default ~/.local/share/backintel/chatgpt),
never in the repository, Doppler, logs or traces. Inference uses the public Responses API
with `store: false` and `stream: true`; usage stops at the plan's limits.
"""

from __future__ import annotations

import base64
import contextlib
import fcntl
import hashlib
import http.server
import json
import os
import secrets
import threading
import time
import uuid
import webbrowser
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
import jwt
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import _construct_lc_result_from_responses_api
from openai import APIError, APIStatusError, OpenAI
from pydantic import PrivateAttr

ISSUER = "https://auth.openai.com"
DISCOVERY_URL = ISSUER + "/.well-known/openid-configuration"
AUTHORIZE_URL = ISSUER + "/oauth/authorize"
TOKEN_URL = ISSUER + "/oauth/token"
RESOURCE = "https://api.openai.com/v1"
PLAN_SCOPE = "subscription.sharing"
SCOPES = "openid profile email offline_access " + PLAN_SCOPE
USAGE_URL = "https://chatgpt.com/settings/connected-apps"
AGENT_NAME = "BackIntel"
CALLBACK_PORT = 1456
CALLBACK_PATH = "/auth/callback"
DEFAULT_HOME = Path(
    os.environ.get("BACKINTEL_CHATGPT_HOME") or Path.home() / ".local/share/backintel/chatgpt"
)
REFRESH_MARGIN_SECONDS = 300
UNSUPPORTED_FIELDS = {
    "background",
    "conversation",
    "max_output_tokens",
    "max_tool_calls",
    "metadata",
    "moderation",
    "multi_agent",
    "previous_response_id",
    "prompt",
    "prompt_cache_retention",
    "safety_identifier",
    "temperature",
    "top_logprobs",
    "top_p",
    "truncation",
    "user",
}
UNUSABLE_REFRESH = {
    "invalid_grant",
    "invalid_refresh_token",
    "token_expired",
    "refresh_token_expired",
    "refresh_token_invalidated",
    "refresh_token_reused",
}
TRANSIENT = {
    "admission_unavailable",
    "transport_error",
    "server_is_overloaded",
    "server_error",
    "subscription_sharing_usage_unavailable",
    "subscription_sharing_user_unavailable",
}
BACKOFF_SECONDS = (5, 20, 60)
STREAM_IDLE_SECONDS = 120
STREAM_TOTAL_SECONDS = 300


class SignInRequired(RuntimeError):
    """No usable ChatGPT credentials; run `backintel chatgpt login`."""


class PlanUsageStopped(RuntimeError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"ChatGPT plan request stopped ({code}): {detail}")


def _write_private(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    tmp.replace(path)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _error_code(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"http_{response.status_code}"
    if isinstance(body.get("error"), dict):
        return body["error"].get("code") or f"http_{response.status_code}"
    return body.get("error") or f"http_{response.status_code}"


class PlanCredentials:
    """One ChatGPT account registration and this host's identity, stored privately."""

    def __init__(self, home: Path = DEFAULT_HOME):
        self.home = Path(home)
        self._lock = threading.Lock()

    @property
    def record_path(self) -> Path:
        return self.home / "credentials.json"

    def host_id(self) -> str:
        path = self.home / "host.json"
        if path.exists():
            return json.loads(path.read_text())["ext_agent_host_id"]
        value = "urn:uuid:" + str(uuid.uuid4())
        _write_private(path, {"ext_agent_host_id": value})
        return value

    def load(self) -> dict | None:
        return json.loads(self.record_path.read_text()) if self.record_path.exists() else None

    def save(self, record: dict) -> None:
        _write_private(self.record_path, record)

    @contextlib.contextmanager
    def _serialized(self):
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._lock, (self.home / "refresh.lock").open("w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def status(self) -> dict:
        record = self.load()
        if not record or not record.get("refresh_token"):
            return {"signed_in": False, "home": str(self.home)}
        return {
            "signed_in": True,
            "email": record.get("email"),
            "client_id": record["client_id"],
            "plan_usage": PLAN_SCOPE in record.get("scopes", []),
            "access_expires_at": record["expires_at"],
            "manage_usage": USAGE_URL,
            "home": str(self.home),
        }

    def access_token(self, now: Callable[[], float] = time.time) -> str:
        with self._serialized():
            record = self.load()
            if not record or not record.get("refresh_token"):
                raise SignInRequired("Sign in with ChatGPT first: backintel chatgpt login")
            if PLAN_SCOPE not in record.get("scopes", []):
                raise SignInRequired("ChatGPT plan usage was not granted; sign in again.")
            if record["expires_at"] - now() > REFRESH_MARGIN_SECONDS:
                return record["access_token"]
            return self._refresh(record, now)["access_token"]

    def _refresh(self, record: dict, now: Callable[[], float]) -> dict:
        with httpx.Client(timeout=30, trust_env=False) as client:
            response = client.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": record["client_id"],
                    "refresh_token": record["refresh_token"],
                    "resource": RESOURCE,
                },
            )
        if response.status_code != 200:
            code = _error_code(response)
            if code == "invalid_client":
                raise SignInRequired("The ChatGPT client registration is invalid; sign in again.")
            if code in UNUSABLE_REFRESH:
                self.save({**record, "access_token": None, "refresh_token": None})
                raise SignInRequired(f"ChatGPT refresh was rejected ({code}); sign in again.")
            raise PlanUsageStopped(
                "admission_unavailable", f"token refresh HTTP {response.status_code} ({code})"
            )
        renewed = response.json()
        updated = record | {
            "access_token": renewed["access_token"],
            "refresh_token": renewed.get("refresh_token", record["refresh_token"]),
            "expires_at": now() + int(renewed.get("expires_in", 3600)),
            "scopes": renewed.get("scope", " ".join(record["scopes"])).split(),
            "saved_at": datetime.now(UTC).isoformat(),
        }
        self.save(updated)
        return updated

    def sign_out(self) -> bool:
        with self._serialized():
            record = self.load()
            if not record or not record.get("refresh_token"):
                return True
            revoked = False
            with (
                contextlib.suppress(httpx.HTTPError),
                httpx.Client(timeout=30, trust_env=False) as client,
            ):
                endpoint = client.get(DISCOVERY_URL).json()["revocation_endpoint"]
                revoked = (
                    client.post(
                        endpoint,
                        data={
                            "token": record["refresh_token"],
                            "token_type_hint": "refresh_token",
                            "client_id": record["client_id"],
                        },
                    ).status_code
                    == 200
                )
            self.save({**record, "access_token": None, "refresh_token": None})
            return revoked


def authorization_request(credentials: PlanCredentials, redirect_uri: str) -> tuple[str, dict]:
    record = credentials.load()
    attempt = {
        "state": _b64url(secrets.token_bytes(32)),
        "nonce": _b64url(secrets.token_bytes(32)),
        "verifier": _b64url(secrets.token_bytes(48)),
        "redirect_uri": redirect_uri,
        "client_id": record["client_id"] if record else "dynamic_agent_client",
    }
    params = {
        "client_id": attempt["client_id"],
        "ext_agent_host_id": credentials.host_id(),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "resource": RESOURCE,
        "state": attempt["state"],
        "nonce": attempt["nonce"],
        "code_challenge_method": "S256",
        "code_challenge": _b64url(hashlib.sha256(attempt["verifier"].encode()).digest()),
    }
    if record is None:
        params["agent_name_hint"] = AGENT_NAME
    else:
        if record.get("id_token"):
            params["id_token_hint"] = record["id_token"]
        if record.get("email"):
            params["login_hint"] = record["email"]
    return AUTHORIZE_URL + "?" + urlencode(params), attempt


def complete_sign_in(credentials: PlanCredentials, attempt: dict, callback: dict[str, str]) -> dict:
    if callback.get("state") != attempt["state"]:
        raise SignInRequired("The sign-in callback state did not match; start again.")
    if callback.get("error"):
        raise SignInRequired(
            "ChatGPT plan usage was not enabled."
            if callback["error"] == "access_denied"
            else f"Sign-in failed: {callback['error']}."
        )
    existing = credentials.load()
    client_id = attempt["client_id"]
    if client_id == "dynamic_agent_client":
        client_id = callback.get("client_id") or ""
        if not client_id or client_id == "dynamic_agent_client":
            raise SignInRequired("Registration did not return an issued client ID.")
    with httpx.Client(timeout=30, trust_env=False) as client:
        response = client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": callback["code"],
                "code_verifier": attempt["verifier"],
                "redirect_uri": attempt["redirect_uri"],
                "resource": RESOURCE,
            },
        )
        if response.status_code != 200:
            raise SignInRequired(f"Code exchange failed ({_error_code(response)}); start again.")
        tokens = response.json()
        jwks = jwt.PyJWKClient(client.get(DISCOVERY_URL).json()["jwks_uri"])
    claims = jwt.decode(
        tokens["id_token"],
        jwks.get_signing_key_from_jwt(tokens["id_token"]).key,
        algorithms=["RS256", "ES256"],
        audience=client_id,
        issuer=ISSUER,
    )
    if claims.get("nonce") != attempt["nonce"]:
        raise SignInRequired("The ID token nonce did not match this sign-in.")
    if existing and existing.get("subject") not in {None, claims["sub"]}:
        raise SignInRequired("A different ChatGPT account signed in; registration not replaced.")
    scopes = tokens.get("scope", callback.get("scope", "")).split()
    record = {
        "issuer": ISSUER,
        "subject": claims["sub"],
        "email": claims.get("email"),
        "client_id": client_id,
        "ext_agent_host_id": credentials.host_id(),
        "id_token": tokens["id_token"],
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type", "Bearer"),
        "expires_at": time.time() + int(tokens.get("expires_in", 3600)),
        "scopes": scopes,
        "saved_at": datetime.now(UTC).isoformat(),
    }
    credentials.save(record)
    if PLAN_SCOPE not in scopes:
        raise SignInRequired("Signed in, but ChatGPT plan usage was not granted. Sign in again and allow it.")
    return record


def sign_in(
    credentials: PlanCredentials,
    *,
    announce: Callable[[str], None] = print,
    open_browser: Callable[[str], object] = webbrowser.open,
    timeout: float = 600,
) -> dict:
    """Run the loopback browser flow on 127.0.0.1 and save validated credentials."""
    received: dict[str, str] = {}
    done = threading.Event()

    class Callback(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urlsplit(self.path)
            if parsed.path != CALLBACK_PATH:
                self.send_error(404)
                return
            received.update({k: v[0] for k, v in parse_qs(parsed.query).items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"BackIntel received the ChatGPT sign-in. You can close this tab.")
            done.set()

        def log_message(self, *args):
            return

    port = CALLBACK_PORT if credentials.load() is None else 0
    server = http.server.HTTPServer(("127.0.0.1", port), Callback)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        redirect = f"http://127.0.0.1:{server.server_address[1]}{CALLBACK_PATH}"
        url, attempt = authorization_request(credentials, redirect)
        announce("Continue with ChatGPT in your normal browser to authorize BackIntel.")
        if "id_token_hint" not in url:
            announce("Open this link on this computer:\n" + url)
        open_browser(url)
        if not done.wait(timeout):
            raise SignInRequired("Timed out waiting for ChatGPT authorization.")
    finally:
        server.shutdown()
        server.server_close()
    return complete_sign_in(credentials, attempt, received)


class PlanChatOpenAI(ChatOpenAI):
    """Responses API calls billed to the signed-in ChatGPT plan."""

    _credentials: PlanCredentials = PrivateAttr()

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        payload = {k: v for k, v in payload.items() if k not in UNSUPPORTED_FIELDS}
        payload |= {"store": False, "stream": True}
        if payload.get("tool_choice") not in (None, "auto"):
            payload["tool_choice"] = "auto"
        functions = [t for t in payload.pop("tools", []) if t.get("type") == "function"]
        if functions:
            payload["tools"] = [
                {
                    "type": "namespace",
                    "name": "backintel",
                    "description": "BackIntel data-analysis tools.",
                    "tools": functions,
                }
            ]
        items = []
        for item in payload["input"]:
            if item.get("type", "message") == "message" and item.get("role") == "system":
                item = item | {"role": "developer"}
            items.append(item)
        payload["input"] = items
        return payload

    def _stream_once(self, payload: dict):
        client = OpenAI(
            api_key=self._credentials.access_token(),
            base_url=RESOURCE,
            max_retries=0,
            timeout=httpx.Timeout(STREAM_TOTAL_SECONDS, read=STREAM_IDLE_SECONDS, connect=15),
        )
        deadline = time.monotonic() + STREAM_TOTAL_SECONDS
        try:
            with client.responses.create(**payload) as stream:
                items = {}
                for event in stream:
                    if time.monotonic() > deadline:
                        return None, ("transport_error", f"stream exceeded {STREAM_TOTAL_SECONDS}s")
                    if event.type == "response.output_item.done":
                        items[event.output_index] = event.item
                    if event.type == "response.completed":
                        response = event.response
                        if not response.output and items:
                            response = response.model_copy(
                                update={"output": [items[i] for i in sorted(items)]}
                            )
                        return response, None
                    if event.type in {"response.failed", "response.incomplete"}:
                        error = getattr(event.response, "error", None)
                        details = getattr(event.response, "incomplete_details", None)
                        code = getattr(error, "code", None) or getattr(details, "reason", None) or event.type
                        return None, (code, event.type)
            return None, ("transport_error", "stream ended without completion")
        except APIStatusError as error:
            body = error.body if isinstance(error.body, dict) else {}
            nested = body.get("error") if isinstance(body.get("error"), dict) else body
            code = (nested or {}).get("code") or (
                "admission_unavailable" if error.status_code == 503 else f"http_{error.status_code}"
            )
            return None, (code, str((nested or {}).get("message") or ""))
        except APIError as error:
            return None, ("transport_error", f"{type(error).__name__}: {str(error)[:300]}")
        finally:
            client.close()

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        for delay in (*BACKOFF_SECONDS, None):
            response, failure = self._stream_once(payload)
            if response is not None:
                result = _construct_lc_result_from_responses_api(response, output_version="responses/v1")
                usage = response.usage.model_dump(exclude_none=True) if response.usage else {}
                result.llm_output = {
                    "token_usage": usage,
                    "model_name": self.model_name,
                    "billing": "chatgpt_plan",
                }
                return result
            code, detail = failure
            if (code in TRANSIENT or code.startswith("http_5")) and delay is not None:
                time.sleep(delay)
                continue
            raise PlanUsageStopped(code, detail)
        raise AssertionError("unreachable")

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        import asyncio

        return await asyncio.to_thread(self._generate, messages, stop, None, **kwargs)


def plan_model(
    model: str, credentials: PlanCredentials | None = None, *, reasoning_effort: str = "medium"
) -> PlanChatOpenAI:
    credentials = credentials or PlanCredentials()
    if credentials.load() is None:
        raise SignInRequired("Run `backintel chatgpt login` before using the chatgpt-plan provider.")
    chat = PlanChatOpenAI(
        model=model,
        api_key="chatgpt-plan-token-supplied-per-request",
        base_url=RESOURCE,
        max_retries=0,
        timeout=300,
        disable_streaming=True,
        use_responses_api=True,
        store=False,
        include=["reasoning.encrypted_content"],
        reasoning={"effort": reasoning_effort},
        profile={"max_input_tokens": 200_000, "tool_calling": True, "structured_output": True},
    )
    chat._credentials = credentials
    return chat


__all__ = [
    "AIMessage",
    "ChatGeneration",
    "PlanChatOpenAI",
    "PlanCredentials",
    "PlanUsageStopped",
    "SignInRequired",
    "plan_model",
    "sign_in",
]
