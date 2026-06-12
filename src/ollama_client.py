from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import requests


class OllamaError(RuntimeError):
    pass


@dataclass
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "translategemma:27b"
    timeout_seconds: int = 300
    temperature: float = 0.0
    num_ctx: int = 4096
    keep_alive: str = "10m"


class OllamaClient:
    def __init__(self, config: OllamaConfig):
        self.config = config
        self.host = config.host.rstrip("/")

    def check_server(self) -> list[str]:
        """Return available local model names, or raise a readable error."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise OllamaError(
                f"Could not reach Ollama at {self.host}. Is `ollama serve` running?"
            ) from exc
        except ValueError as exc:
            raise OllamaError("Ollama returned a non-JSON response from /api/tags.") from exc

        return [item.get("name", "") for item in payload.get("models", []) if item.get("name")]

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.config.keep_alive,
            "options": {
                "temperature": self.config.temperature,
                "num_ctx": self.config.num_ctx,
            },
        }
        if system:
            payload["system"] = system

        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = response.text
            except Exception:
                pass
            raise OllamaError(f"Ollama generation failed: {exc}. {detail}") from exc
        except requests.RequestException as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        except ValueError as exc:
            raise OllamaError("Ollama returned a non-JSON generation response.") from exc

        if "error" in data:
            raise OllamaError(str(data["error"]))
        return (data.get("response") or "").strip()
