"""可插拔 key→value 持久化后端

为治理文档 §4.2 所列的 11 个进程内内存容器提供统一的落库抽象。
默认 ``MemoryStateStore`` 与改造前行为完全一致（进程重启即丢）；
``JSONFileStateStore`` 实现真正的文件落库，满足 90 天追踪与可复现性。

设计上完全镜像已上线的 ``ab_test_framework.ExperimentStore`` 模式，
方便后续把 BOX_STATES 等容器逐一切换到 SQL 后端。
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class StateStore(ABC):
    """key→value 持久化后端抽象。默认内存实现与既有行为一致；可换 JSON/SQL。"""

    @abstractmethod
    def get(self, key: str) -> Any:
        """返回 key 对应的值；不存在时返回 None。"""
        ...

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """写入/覆盖 key。"""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除 key（不存在时静默忽略）。"""
        ...

    @abstractmethod
    def keys(self) -> List[str]:
        """返回当前所有 key 的列表。"""
        ...

    @abstractmethod
    def close(self) -> None:
        """释放资源 / 刷盘。"""
        ...


class MemoryStateStore(StateStore):
    """内存后端 —— 与改造前的行为完全一致（进程重启即丢）。"""

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def keys(self) -> List[str]:
        return list(self._data.keys())

    def close(self) -> None:
        return None


class JSONFileStateStore(StateStore):
    """JSON 文件后端 —— 真正落库，进程重启不丢。

    每次写入都以「临时文件 + os.replace 原子替换」刷盘，避免半写损坏；
    值为任意 JSON 可序列化对象（``ensure_ascii=False`` 以保留中文）。
    生产可替换为 SQLStateStore（建表见 scripts/schema_core_assets.sql）。
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(self._dir, exist_ok=True)
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _flush(self) -> None:
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._flush()

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._flush()

    def keys(self) -> List[str]:
        return list(self._data.keys())

    def close(self) -> None:
        self._flush()
