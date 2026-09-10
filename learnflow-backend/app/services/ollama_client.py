"""Ollama 客户端 (纯 stdlib, 同步 HTTP)。

无可用本地服务时回退到 ``MockOllama``, 保证「LLM 干预生成」管线不中断
(论文工程要求: 系统在任何环境下均可演示, 不依赖外部 GPU 服务)。
"""
from __future__ import annotations

import json
import urllib.request
from typing import Optional

DEFAULT_BASE = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b"


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: str = DEFAULT_BASE, model: str = DEFAULT_MODEL, timeout: int = 30):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        payload = {"model": self.model, "prompt": prompt,
                   "system": system, "stream": False}
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()
        except Exception as e:  # 网络/服务不可用 -> 上层回退
            raise OllamaError(str(e))

    def available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False


class MockOllama:
    """无本地模型时的安全回退: 返回模板化、非操控性文案。"""

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        return "你今天已经很努力了，记得按时休息，学习是为了更好的自己，而不是和别人比。"

    def available(self) -> bool:
        return False


_singleton = None


def get_ollama() -> "OllamaClient | MockOllama":
    """返回 Ollama 单例; 若服务不可用则返回 MockOllama。"""
    global _singleton
    if _singleton is None:
        c = OllamaClient()
        _singleton = c if c.available() else MockOllama()
    return _singleton
