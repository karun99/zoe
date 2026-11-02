"""Layer 3 backends - pluggable inference engines for the frozen base model.

The rig does not care *where* text comes from, only that the base model stays
frozen while the LoRA adapter keeps evolving (FR-3.1 .. FR-3.6). This module
supplies interchangeable engines behind one tiny interface:

============  ===========================================================
name          transport
============  ===========================================================
``ollama``    HTTP ``/api/chat`` on a local Ollama daemon (default on Termux)
``llama-server``  HTTP ``/v1/chat/completions`` from llama.cpp's ``llama-server``
``llamacpp``  in-process ``llama-cpp-python`` (desktop / server)
``llama-cli`` subprocess ``llama-cli`` (no compiler needed, good on Android)
``mock``      deterministic, dependency-free fallback (never leaves the device)
============  ===========================================================

Design notes
------------
* **Standard library only.** HTTP uses ``urllib``; nothing new to compile on
  Termux, where wheels for native extensions are scarce.
* **No numpy here.** ``zoe doctor`` and backend probing stay fast and can run
  before the scientific stack is installed.
* **Failures are typed.** ``BackendUnavailable`` means "not installed / not
  running"; ``BackendError`` means "it answered, but badly". The rig turns the
  first into an honest mock fallback instead of a crash.
* **Nothing is inferred about the network.** A backend only reports
  ``available()`` when it can actually serve a request.
"""

from __future__ import annotations

import http.client
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

__all__ = [
    "BackendError",
    "BackendUnavailable",
    "BackendReply",
    "LLMBackend",
    "OllamaBackend",
    "LlamaServerBackend",
    "LlamaCppBackend",
    "LlamaCliBackend",
    "MockBackend",
    "build_backend",
    "resolve_backend",
    "available_backends",
    "BACKENDS",
]


class BackendError(RuntimeError):
    """The backend answered, but the answer was unusable."""


class BackendUnavailable(BackendError):
    """The backend is not installed, not configured, or not running."""


@dataclass
class BackendReply:
    """One completion, normalised across engines."""

    text: str
    tokens: int
    backend: str
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)


def _word_count(text: str) -> int:
    return len(text.split())


class LLMBackend:
    """Minimal interface every engine implements."""

    name = "base"
    label = "Base backend"

    def available(self) -> bool:  # pragma: no cover - overridden
        return False

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "label": self.label, "available": self.available()}

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 128,
        temperature: float = 0.7,
        stop: Optional[Sequence[str]] = None,
    ) -> BackendReply:  # pragma: no cover - overridden
        raise NotImplementedError


# --------------------------------------------------------------------------- http


class _HTTPBackend(LLMBackend):
    """Shared JSON-over-HTTP plumbing for Ollama and llama-server."""

    def __init__(self, base_url: str, timeout: float = 120.0,
                 probe_timeout: float = 1.5) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.probe_timeout = float(probe_timeout)

    # -- transport ---------------------------------------------------------
    def _request(self, path: str, payload: Optional[Dict[str, Any]] = None,
                 timeout: Optional[float] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        method = "GET"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
            method = "POST"
        request = urllib.request.Request(url, data=data, headers=headers,
                                         method=method)
        try:
            with urllib.request.urlopen(
                request, timeout=timeout or self.timeout
            ) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise BackendError(
                f"{self.name}: HTTP {exc.code} from {url}: {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BackendUnavailable(
                f"{self.name}: cannot reach {url} ({exc})"
            ) from exc
        except http.client.HTTPException as exc:
            raise BackendUnavailable(
                f"{self.name}: connection to {url} broke ({exc})"
            ) from exc
        try:
            return json.loads(body) if body.strip() else {}
        except json.JSONDecodeError as exc:
            raise BackendError(
                f"{self.name}: malformed JSON from {url}: {body[:200]}"
            ) from exc

    def _probe(self, path: str) -> bool:
        try:
            self._request(path, timeout=self.probe_timeout)
            return True
        except Exception:  # any failure means 'not usable right now'
            return False


class OllamaBackend(_HTTPBackend):
    """Local Ollama daemon (``ollama serve``), the Termux default."""

    name = "ollama"
    label = "Ollama (local HTTP)"

    def __init__(self, host: str = "http://127.0.0.1:11434",
                 model: str = "qwen2.5:0.5b", timeout: float = 120.0,
                 probe_timeout: float = 1.5, keep_alive: str = "5m") -> None:
        super().__init__(host, timeout, probe_timeout)
        self.model = model
        self.keep_alive = keep_alive

    def list_models(self) -> List[str]:
        data = self._request("/api/tags", timeout=self.probe_timeout)
        return [str(m.get("name", "")) for m in data.get("models", []) if m.get("name")]

    def available(self) -> bool:
        return self._probe("/api/tags")

    def describe(self) -> Dict[str, Any]:
        info = super().describe()
        info.update({"host": self.base_url, "model": self.model})
        try:
            info["models"] = self.list_models()
            info["model_present"] = any(
                m == self.model or m.split(":")[0] == self.model.split(":")[0]
                for m in info["models"]
            )
        except BackendError as exc:
            info["error"] = str(exc)
            info["models"] = []
            info["model_present"] = False
        return info

    def complete(self, prompt: str, *, max_tokens: int = 128,
                 temperature: float = 0.7,
                 stop: Optional[Sequence[str]] = None) -> BackendReply:
        options: Dict[str, Any] = {
            "temperature": float(temperature),
            "num_predict": int(max_tokens),
        }
        if stop:
            options["stop"] = list(stop)
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": options,
        }
        data = self._request("/api/chat", payload)
        message = data.get("message") or {}
        text = str(message.get("content", "")).strip()
        if not text:
            raise BackendError(f"{self.name}: empty completion from {self.model}")
        return BackendReply(
            text=text,
            tokens=int(data.get("eval_count") or _word_count(text)),
            backend=self.name,
            raw={"model": data.get("model"),
                 "done_reason": data.get("done_reason")},
        )


class LlamaServerBackend(_HTTPBackend):
    """llama.cpp ``llama-server`` (OpenAI-compatible endpoint)."""

    name = "llama-server"
    label = "llama.cpp server (OpenAI-compatible)"

    def __init__(self, url: str = "http://127.0.0.1:8080",
                 model: str = "zoe", timeout: float = 120.0,
                 probe_timeout: float = 1.5) -> None:
        super().__init__(url, timeout, probe_timeout)
        self.model = model

    def available(self) -> bool:
        return self._probe("/health") or self._probe("/v1/models")

    def describe(self) -> Dict[str, Any]:
        info = super().describe()
        info.update({"url": self.base_url, "model": self.model})
        return info

    def complete(self, prompt: str, *, max_tokens: int = 128,
                 temperature: float = 0.7,
                 stop: Optional[Sequence[str]] = None) -> BackendReply:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
            "stream": False,
        }
        if stop:
            payload["stop"] = list(stop)
        data = self._request("/v1/chat/completions", payload)
        choices = data.get("choices") or []
        text = ""
        if choices:
            text = str((choices[0].get("message") or {}).get("content", "")).strip()
        if not text:
            raise BackendError(f"{self.name}: empty completion from {self.base_url}")
        usage = data.get("usage") or {}
        return BackendReply(
            text=text,
            tokens=int(usage.get("completion_tokens") or _word_count(text)),
            backend=self.name,
            raw={"model": data.get("model")},
        )


# ----------------------------------------------------------------------- local


class LlamaCppBackend(LLMBackend):
    """In-process ``llama-cpp-python`` binding (desktop, or Termux with clang)."""

    name = "llamacpp"
    label = "llama.cpp (in-process python binding)"

    def __init__(self, model_path: str, context: int = 2048,
                 timeout: float = 120.0, threads: Optional[int] = None) -> None:
        self.model_path = model_path
        self.context = int(context)
        self.timeout = float(timeout)
        self.threads = threads
        self._model = None

    @staticmethod
    def _has_module() -> bool:
        return importlib.util.find_spec("llama_cpp") is not None

    def available(self) -> bool:
        return bool(self.model_path) and os.path.isfile(self.model_path) \
            and self._has_module()

    def describe(self) -> Dict[str, Any]:
        info = super().describe()
        info.update({
            "model_path": self.model_path,
            "module_installed": self._has_module(),
            "model_exists": bool(self.model_path) and os.path.isfile(self.model_path),
        })
        return info

    def _llama(self):
        if self._model is not None:
            return self._model
        if not self._has_module():
            raise BackendUnavailable(
                "llamacpp: llama-cpp-python is not installed "
                "(pip install llama-cpp-python, or use the ollama backend)"
            )
        if not self.model_path or not os.path.isfile(self.model_path):
            raise BackendUnavailable(
                f"llamacpp: GGUF not found at {self.model_path!r} "
                "(set ZOE_GGUF_PATH)"
            )
        from llama_cpp import Llama  # type: ignore

        self._model = Llama(
            model_path=self.model_path,
            n_ctx=self.context,
            n_threads=self.threads,
            verbose=False,
        )
        return self._model

    def complete(self, prompt: str, *, max_tokens: int = 128,
                 temperature: float = 0.7,
                 stop: Optional[Sequence[str]] = None) -> BackendReply:
        model = self._llama()
        try:
            out = model(
                prompt,
                max_tokens=int(max_tokens),
                temperature=float(temperature),
                stop=list(stop) if stop else [],
            )
        except Exception as exc:  # pragma: no cover - native failure
            raise BackendError(f"{self.name}: generation failed ({exc})") from exc
        text = str((out.get("choices") or [{}])[0].get("text", "")).strip()
        if not text:
            raise BackendError(f"{self.name}: empty completion")
        return BackendReply(text=text, tokens=_word_count(text),
                            backend=self.name, raw={"model": self.model_path})


class LlamaCliBackend(LLMBackend):
    """Subprocess wrapper around the ``llama-cli`` binary.

    This is the Termux-friendly llama.cpp path: ``pkg install llama-cpp`` gives
    you a working binary without compiling a Python extension.
    """

    name = "llama-cli"
    label = "llama.cpp CLI (subprocess)"

    def __init__(self, model_path: str, binary: str = "llama-cli",
                 context: int = 2048, timeout: float = 120.0,
                 extra_args: str = "") -> None:
        self.model_path = model_path
        self.binary = binary
        self.context = int(context)
        self.timeout = float(timeout)
        self.extra_args = extra_args

    def _exe(self) -> Optional[str]:
        return shutil.which(self.binary)

    def available(self) -> bool:
        return bool(self.model_path) and os.path.isfile(self.model_path) \
            and self._exe() is not None

    def describe(self) -> Dict[str, Any]:
        info = super().describe()
        info.update({
            "model_path": self.model_path,
            "binary": self.binary,
            "binary_path": self._exe(),
            "model_exists": bool(self.model_path) and os.path.isfile(self.model_path),
        })
        return info

    def complete(self, prompt: str, *, max_tokens: int = 128,
                 temperature: float = 0.7,
                 stop: Optional[Sequence[str]] = None) -> BackendReply:
        exe = self._exe()
        if exe is None:
            raise BackendUnavailable(
                f"{self.name}: {self.binary!r} not on PATH "
                "(Termux: pkg install llama-cpp)"
            )
        if not self.model_path or not os.path.isfile(self.model_path):
            raise BackendUnavailable(
                f"{self.name}: GGUF not found at {self.model_path!r} "
                "(set ZOE_GGUF_PATH)"
            )
        cmd = [
            exe, "-m", self.model_path, "-p", prompt,
            "-n", str(int(max_tokens)),
            "--temp", f"{float(temperature):.2f}",
            "-c", str(self.context),
            "--no-display-prompt",
        ]
        if stop:
            # llama-cli accepts one reverse-prompt at a time; the first is the
            # meaningful one (we use it to cap the 4-line body).
            cmd.extend(["-r", str(stop[0])])
        if self.extra_args:
            cmd.extend(shlex.split(self.extra_args))
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BackendError(
                f"{self.name}: timed out after {self.timeout:.0f}s"
            ) from exc
        except OSError as exc:
            raise BackendUnavailable(f"{self.name}: cannot execute {exe} ({exc})") from exc
        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()[-1:] or [""]
            raise BackendError(
                f"{self.name}: exit {proc.returncode}: {tail[0][:200]}"
            )
        text = (proc.stdout or "").strip()
        if not text:
            raise BackendError(f"{self.name}: empty completion")
        return BackendReply(text=text, tokens=_word_count(text),
                            backend=self.name, raw={"binary": exe})


# ------------------------------------------------------------------------ mock


class MockBackend(LLMBackend):
    """Placeholder for the deterministic in-model mock path.

    The real mock generation lives in :class:`zoe.layers.l3_llm.LlamaCppModel`
    because it needs the reservoir feature and the adapter. It is listed here so
    ``resolve_backend`` and ``zoe doctor`` can name it uniformly.
    """

    name = "mock"
    label = "Deterministic mock (no model, no network)"

    def available(self) -> bool:
        return True

    def complete(self, prompt: str, *, max_tokens: int = 128,
                 temperature: float = 0.7,
                 stop: Optional[Sequence[str]] = None) -> BackendReply:
        raise BackendUnavailable(
            "mock: generation is handled by LlamaCppModel._mock_generate"
        )


# ------------------------------------------------------------------ resolution

BACKENDS: Dict[str, type] = {
    "ollama": OllamaBackend,
    "llama-server": LlamaServerBackend,
    "llamacpp": LlamaCppBackend,
    "llama-cli": LlamaCliBackend,
    "mock": MockBackend,
}

#: Preference order for ``ZOE_LLM_BACKEND=auto``.
AUTO_ORDER: tuple = ("ollama", "llama-server", "llamacpp", "llama-cli")


def build_backend(name: str, cfg: Any) -> LLMBackend:
    """Instantiate one backend from a :class:`ZoeConfig` (no probing)."""
    key = (name or "").strip().lower().replace("_", "-")
    aliases = {
        "llama.cpp": "llamacpp",
        "llama-cpp": "llamacpp",
        "llama_cpp": "llamacpp",
        "llamaserver": "llama-server",
        "llama_server": "llama-server",
        "server": "llama-server",
        "cli": "llama-cli",
        "llama_cli": "llama-cli",
    }
    key = aliases.get(key, key)
    if key not in BACKENDS:
        raise BackendUnavailable(
            f"unknown backend {name!r}; choose from {', '.join(BACKENDS)} or auto"
        )
    timeout = float(getattr(cfg, "llm_timeout_s", 120.0))
    probe = float(getattr(cfg, "llm_probe_timeout_s", 1.5))
    context = int(getattr(cfg, "context_tokens", 2048))
    model_path = str(getattr(cfg, "gguf_path", "") or "")

    if key == "ollama":
        return OllamaBackend(
            host=str(getattr(cfg, "ollama_host", "http://127.0.0.1:11434")),
            model=str(getattr(cfg, "ollama_model", "qwen2.5:0.5b")),
            timeout=timeout,
            probe_timeout=probe,
            keep_alive=str(getattr(cfg, "ollama_keep_alive", "5m")),
        )
    if key == "llama-server":
        return LlamaServerBackend(
            url=str(getattr(cfg, "llama_server_url", "http://127.0.0.1:8080")),
            model=str(getattr(cfg, "llama_server_model", "zoe")),
            timeout=timeout,
            probe_timeout=probe,
        )
    if key == "llamacpp":
        return LlamaCppBackend(model_path=model_path, context=context,
                               timeout=timeout,
                               threads=int(getattr(cfg, "llm_threads", 0)) or None)
    if key == "llama-cli":
        return LlamaCliBackend(
            model_path=model_path,
            binary=str(getattr(cfg, "llama_cli_binary", "llama-cli")),
            context=context,
            timeout=timeout,
            extra_args=str(getattr(cfg, "llama_cli_args", "") or ""),
        )
    return MockBackend()


def available_backends(cfg: Any) -> Dict[str, Dict[str, Any]]:
    """Describe every backend without raising (used by ``zoe doctor``)."""
    report: Dict[str, Dict[str, Any]] = {}
    for name in BACKENDS:
        try:
            backend = build_backend(name, cfg)
            report[name] = backend.describe()
        except Exception as exc:  # pragma: no cover - defensive
            report[name] = {"name": name, "available": False, "error": str(exc)}
    return report


def resolve_backend(cfg: Any) -> LLMBackend:
    """Pick a usable backend or raise :class:`BackendUnavailable`.

    ``ZOE_LLM_BACKEND=auto`` walks :data:`AUTO_ORDER` and returns the first
    engine that actually answers. An explicit name is honoured strictly: if it
    is not usable the caller decides whether to fall back to mock.
    """
    choice = str(getattr(cfg, "llm_backend", "mock") or "mock").strip().lower()
    if choice in {"", "mock", "none", "off"}:
        raise BackendUnavailable("mock backend selected (no model)")

    if choice != "auto":
        backend = build_backend(choice, cfg)
        if not backend.available():
            raise BackendUnavailable(
                f"{backend.name} is not available: {backend.describe()}"
            )
        return backend

    reasons: List[str] = []
    for name in AUTO_ORDER:
        backend = build_backend(name, cfg)
        if backend.available():
            return backend
        reasons.append(f"{name}: unavailable")
    raise BackendUnavailable(
        "auto: no local engine answered (" + "; ".join(reasons) + ")"
    )
