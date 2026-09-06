"""可插拔 key→value 持久化后端

为治理文档 §4.2 所列的 11 个进程内内存容器提供统一的落库抽象。
默认 ``MemoryStateStore`` 与改造前行为完全一致（进程重启即丢）；
``JSONFileStateStore`` 实现真正的文件落库，满足 90 天追踪与可复现性。

设计上完全镜像已上线的 ``ab_test_framework.ExperimentStore`` 模式，
方便后续把 BOX_STATES 等容器逐一切换到 SQL 后端。
"""
from __future__ import annotations

import dataclasses
import enum
import json
import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

logger = logging.getLogger(__name__)


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

    # ── 非抽象方法：就地修改的安全封装 ───────────────────────────
    #
    # 内存后端与文件后端有一个**极易踩且无声的差异**：
    #   * 内存后端 get() 返回对象**本身**，调用方就地修改后改动自动可见；
    #   * 文件后端只有 set() 才刷盘，调用方若只 get() 后就地修改而不再 set()，
    #     改动会被**静默丢弃**——下次 get 拿到的是上次 set 的快照。
    #
    # 本项目 9 个容器中有 7 个存在就地修改（SessionMemory.record_answer、
    # FriendQuest.contribute_xp、SelfRegulationGoal.progress 等），这正是它们
    # 此前无法直接换文件后端的根因。mutate() 把「读—改—写」收拢为一处，
    # 使同一份调用代码在两种后端下语义一致，是容器后端切换的前置设施。
    def mutate(
        self,
        key: str,
        fn: "Callable[[Optional[Any]], Optional[Any]]",
    ) -> Optional[Any]:
        """原子地「读—改—写」一个条目。

        Args:
            key: 条目键。
            fn: 接收当前值（不存在时为 None），返回新值；
                返回 None 表示删除该条目。

        Returns:
            fn 的返回值（即写回后的新值）。
        """
        current = self.get(key)
        updated = fn(current)
        if updated is None:
            self.delete(key)
        else:
            self.set(key, updated)
        return updated


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
    生产可替换为 SQLStateStore（可执行建表见
    scripts/schema_core_assets.mysql.sql 与 scripts/schema_core_assets.sqlite.sql，
    分别面向 MySQL 8.0 与 SQLite 3 环境；原 scripts/schema_core_assets.sql 为
    Postgres 方言，在 MySQL/SQLite 环境下不可直接执行，仅作论文附录归档）。
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


class DataclassJSONStateStore(JSONFileStateStore):
    """支持 dataclass 值、且支持泛型容器值的 JSON 文件后端。

    在 ``JSONFileStateStore`` 的原子刷盘基础上，增加值的序列化/反序列化：
    ``set`` 时把 dataclass 实例（及嵌套的 Enum/datetime/set/容器）转成 JSON 原生结构
    落库；``get`` 时（若构造时给定 ``value_type``）按注解还原：

    - ``value_type`` 为普通 dataclass：把读回的 dict 还原成 ``value_type(**data)`` 实例；
    - ``value_type`` 为泛型容器注解（``List[X]`` / ``Dict[K, V]`` / ``Optional[X]`` /
      ``Set[X]`` / ``Tuple[X, ...]``）：整体按容器注解逐元素还原，例如
      ``value_type=List[SelfRegulationGoal]`` 时读回的 list 中每个元素都会被还原成
      ``SelfRegulationGoal`` 实例。嵌套组合（``Optional[List[X]]``、
      ``Dict[str, List[X]]``）同样层层还原。

    ⚠️ 就地修改（in-place mutation）陷阱（务必阅读）：

    内存后端 ``MemoryStateStore`` 的 ``get`` 返回对象**本身**，调用方就地修改
    （``obj.x = 1`` 或 ``obj.method()`` 且 method 修改 self）会自动生效；
    但本后端是「**set 才刷盘**」，调用方若只 ``get`` 后就地修改、**不调用 set**，
    改动会**静默丢失**（下次 get 拿到的是上次 set 的快照）。

    因此未来把某个容器切到本后端时，必须同时排查该容器的所有调用点：凡是存在
    就地修改的地方，都要改为「取出 → 改 → set 回写」的写法。本类只负责存储，
    不负责纠正调用方语义。各容器当前是否踩坑，见排查记录。

    容错策略（状态存储失败绝不让主流程 500）：
    - ``set`` 时遇到不可序列化的值，回退用 ``str()`` 兜底，不抛异常；
    - ``get`` 时遇到字段增减 / 类型不匹配 / 数据损坏 / 注解解析失败，记 warning 并
      回退返回原始值（dict / list / 字符串 / None），不让调用方崩溃。
    """

    def __init__(self, path: str, value_type: Optional[type] = None) -> None:
        self._value_type = value_type
        super().__init__(path)

    # ---- 序列化 ----
    def _to_jsonable(self, obj: Any) -> Any:
        """把任意值递归转成可 JSON 序列化的结构。

        处理 dataclass / Enum / datetime / set / frozenset / tuple / dict / list，
        其余类型一律 ``str()`` 兜底，绝不抛异常打断主流程。
        """
        # 基础 JSON 原生类型直接返回
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        # dataclass 实例：asdict 后再递归处理每个字段（含嵌套 Enum/datetime/set）
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return {k: self._to_jsonable(v) for k, v in dataclasses.asdict(obj).items()}
        # Enum → 其 .value
        if isinstance(obj, enum.Enum):
            return obj.value
        # datetime → ISO 8601 字符串
        if isinstance(obj, datetime):
            return obj.isoformat()
        # set / frozenset / tuple → list
        if isinstance(obj, (set, frozenset, tuple)):
            return [self._to_jsonable(v) for v in obj]
        # dict → 递归（key 统一转 str，避免非字符串 key 无法落库）
        if isinstance(obj, dict):
            return {str(k): self._to_jsonable(v) for k, v in obj.items()}
        # list → 递归
        if isinstance(obj, list):
            return [self._to_jsonable(v) for v in obj]
        # 兜底：不抛异常，转为字符串
        return str(obj)

    # ---- 反序列化 ----
    def _from_jsonable(self, raw: Any) -> Any:
        """把读回的 JSON 数据按需还原为 value_type 实例。

        除顶层构造外，还会按字段类型注解做**类型感知还原**：
        ``datetime`` ← ISO 字符串、``Enum`` ← 其 value、``set``/``tuple`` ← list、
        嵌套 dataclass ← dict（递归）。此外已覆盖泛型容器：

        - ``Optional[X]``（即 ``Union[X, None]``）：value 非 None 时按 ``X`` 还原，
          None 原样返回；多于一个有效类型（真 Union）则原样返回，不瞎猜；
        - ``List[X]`` / ``Set[X]`` / ``Tuple[X, ...]``：逐元素按 ``X`` 还原（嵌套
          ``List[List[X]]``、``Optional[List[X]]`` 之类也层层还原）；
        - ``Dict[K, V]``：只对 value 递归（key 必为字符串，强行还原 key 反而出错）；
        - 顶层 ``value_type`` 本身为泛型容器注解（如 ``List[SelfRegulationGoal]``）
          时，整体交给 ``_coerce_to_hint`` 还原，不要求 raw 是 dict。

        为什么必须做：时间戳与研究数据强相关，若 ``created_at`` 读回后仍是字符串，
        所有基于时间的比较/排序/聚合都会在下游静默出错；同理 ``List[SomeDataclass]``
        若退化成 ``List[dict]``，下游访问 ``.user_id`` 等属性会直接 ``AttributeError``，
        这正是本次修复要消除的线上崩溃缺口。Enum 字段若退化成裸 value，``is`` 比较
        与 ``.value`` 访问也都会失败。

        容错：任何一步解析失败、注解解析失败或数据形状异常都退化为原始值并记
        warning，**绝不让调用方崩溃**；状态存储的失败绝不能让学生的答题提交返回 500。
        """
        if self._value_type is None:
            return raw

        # 顶层 value_type 是泛型容器注解（List[...] / Dict[...] / Optional[...] /
        # Set[...] / Tuple[...] 等，``get_origin`` 非 None）时，整个 ``raw`` 就是容器
        # 本体（可能是 list / dict / None），不能走「``value_type(**data)`` 这种按字段
        # 构造 dataclass」的路线，必须整体交给 ``_coerce_to_hint`` 逐元素还原。
        # 这正是 ``GOALS`` 这类「值本身就是 ``List[X]``」容器的形态。
        if get_origin(self._value_type) is not None:
            try:
                return _coerce_to_hint(raw, self._value_type)
            except Exception:
                logger.warning(
                    "DataclassJSONStateStore: 泛型容器值还原失败，返回原始值；"
                    "value_type=%s，raw=%r",
                    self._value_type,
                    raw,
                    exc_info=True,
                )
                return raw

        # 以下为「普通 dataclass」语义：raw 必须是 dict。
        if not isinstance(raw, dict):
            # 形状异常（如数据损坏导致非 dict），容错返回原始值，不让调用方崩溃。
            logger.warning(
                "DataclassJSONStateStore: %s 期望 dict，但读到 %s，返回原始值；raw=%r",
                getattr(self._value_type, "__name__", self._value_type),
                type(raw).__name__,
                raw,
            )
            return raw
        try:
            hints = _resolve_hints(self._value_type)
            kwargs = {
                name: _coerce_to_hint(value, hints.get(name))
                for name, value in raw.items()
            }
            return self._value_type(**kwargs)
        except Exception:
            logger.warning(
                "DataclassJSONStateStore: 无法把数据还原为 %s，返回原始 dict；raw=%r",
                getattr(self._value_type, "__name__", self._value_type),
                raw,
                exc_info=True,
            )
            return raw

    # ---- StateStore 接口（复用 JSONFileStateStore.set 的原子刷盘）----
    def set(self, key: str, value: Any) -> None:
        try:
            # 先转成可 JSON 序列化的结构；转换失败（含兜底 str）绝不抛异常打断主流程
            jsonable = self._to_jsonable(value)
        except Exception:
            logger.warning(
                "DataclassJSONStateStore.set 序列化失败，跳过本次写入；key=%r",
                key,
                exc_info=True,
            )
            return
        # 交给父类 set：self._data[key] = jsonable + 原子 _flush，不重写刷盘逻辑
        try:
            super().set(key, jsonable)
        except Exception:
            logger.warning(
                "DataclassJSONStateStore.set 刷盘失败；key=%r", key, exc_info=True
            )

    def get(self, key: str) -> Any:
        raw = self._data.get(key)
        if raw is None:
            return None
        return self._from_jsonable(raw)


def _resolve_hints(cls: Any) -> Dict[str, Any]:
    """解析 dataclass 的字段类型注解；失败时返回空 dict（退化为不还原）。

    放在模块级而非类体内：解析注解是纯函数，与具体存储实例无关。
    """
    if not dataclasses.is_dataclass(cls):
        return {}
    try:
        return get_type_hints(cls)
    except Exception:
        # 字符串注解 / 前向引用解析失败时，退化为不还原，绝不影响主流程
        logger.debug("无法解析 %s 的类型注解，跳过类型感知还原", cls, exc_info=True)
        return {}


def _coerce_to_hint(value: Any, hint: Any) -> Any:
    """按类型注解把一个 JSON 原生值还原为更贴近原类型的值。

    任何失败都返回原值——还原是尽力而为的，不能因数据形状异常而崩溃。
    """
    if hint is None or value is None:
        return value

    # Enum：裸 value → 枚举成员
    try:
        if isinstance(hint, type) and issubclass(hint, enum.Enum):
            return hint(value)
    except Exception:
        return value

    # datetime：ISO 字符串 → datetime
    if hint is datetime:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return value
        return value

    # 嵌套 dataclass：dict → 实例（递归）
    try:
        if dataclasses.is_dataclass(hint) and isinstance(value, dict):
            sub_hints = _resolve_hints(hint)
            return hint(**{
                k: _coerce_to_hint(v, sub_hints.get(k)) for k, v in value.items()
            })
    except Exception:
        return value

    # set / frozenset / tuple：list → 原容器类型
    try:
        if hint in (set, frozenset) and isinstance(value, list):
            return hint(value)
        if hint is tuple and isinstance(value, list):
            return tuple(value)
    except Exception:
        return value

    # 泛型容器：Optional[X] / List[X] / Dict[K,V] / Set[X] / Tuple[X,...]
    # 用 typing.get_origin / get_args 解析。Python 3.13 下 ``typing.List[X]`` 与
    # 内置 ``list[X]`` 的 get_origin 都返回内置 list，下面统一按 ``list`` 判断即可。
    try:
        origin = get_origin(hint)
        if origin is not None:
            args = get_args(hint)

            # Optional[X] == Union[X, None]：先过滤掉 NoneType，剩一个就按它还原
            if origin is Union:
                real = [a for a in args if a is not type(None)]
                if len(real) == 1:
                    # 递归：让 Optional[List[X]] / Optional[Dict[...]] 也层层还原
                    return _coerce_to_hint(value, real[0])
                # 真 Union（多于一个有效类型）：不瞎猜，原样返回
                return value

            # List[X]（也可写 typing.List[X]）；裸 list（args 为空）逐元素按 None 还原即原样
            if origin in (list, List) and isinstance(value, list):
                elem = args[0] if args else None
                return [_coerce_to_hint(v, elem) for v in value]

            # Dict[K, V]：只对 value 递归（key 必为字符串，强行还原反而出错）
            if origin in (dict, Dict) and isinstance(value, dict):
                val_hint = args[1] if len(args) >= 2 else None
                return {k: _coerce_to_hint(v, val_hint) for k, v in value.items()}

            # Set[X] / FrozenSet[X]：从 list 逐元素还原（裸 set 由上方分支处理）
            if origin in (set, frozenset) and isinstance(value, list):
                elem = args[0] if args else None
                return hint(_coerce_to_hint(v, elem) for v in value)

            # Tuple[X, ...]（变长）/ Tuple[X1, X2, ...]（定长）：从 list/tuple 还原
            if origin is tuple and isinstance(value, (list, tuple)):
                if len(args) == 2 and args[1] is Ellipsis:
                    elem = args[0]
                    return tuple(_coerce_to_hint(v, elem) for v in value)
                return tuple(
                    _coerce_to_hint(v, args[i] if i < len(args) else None)
                    for i, v in enumerate(value)
                )

            # 其他未覆盖的泛型（如裸 dict 无 args 等）原样返回
            return value
    except Exception:
        return value

    return value


def _safe_state_name(name: str) -> str:
    """把容器名转成安全的文件名，防止路径穿越（../ 等）。

    先去掉任何目录成分（``os.path.basename``），再把非
    ``[A-Za-z0-9_.-]`` 的字符替换为下划线；空结果回退为 ``state``。
    """
    base = os.path.basename(name)
    safe = re.sub(r"[^A-Za-z0-9_.\-]", "_", base)
    if not safe:
        safe = "state"
    return safe


def _state_dir() -> str:
    """落库根目录：<后端根目录>/artifacts/state（不存在自动创建，不改动既有文件）。

    ``__file__`` 为 ``<后端根目录>/app/services/state_store.py``，上溯三级即后端根目录。
    抽成独立函数便于测试时重定向到临时目录。
    """
    backend_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    artifacts_dir = os.path.join(backend_root, "artifacts", "state")
    os.makedirs(artifacts_dir, exist_ok=True)
    return artifacts_dir


def default_state_store(name: str, value_type: Optional[type] = None) -> StateStore:
    """按环境变量 ``LEARNFLOW_STATE_BACKEND`` 选择后端，全局可配、逐容器可切。

    - ``memory``（默认）：``MemoryStateStore()``，与改造前行为完全一致（进程重启即丢）；
    - ``json``：``DataclassJSONStateStore(path=..., value_type=value_type)``，
      落库到 ``<后端根目录>/artifacts/state/<name>.json``，目录不存在自动创建；
      ``name`` 会经 :func:`_safe_state_name` 做文件名安全化，防路径穿越；
    - 未知取值：记 warning 并回退 ``MemoryStateStore()``。

    **默认必须是 memory**，这样现有 720 个测试的行为完全不变。每个容器将来切换后端
    只需把 ``MemoryStateStore()`` 换成 ``default_state_store("<NAME>", value_type=...)``。

    参数：
        name: 容器名，同时作为落库文件名（会安全化处理）。
        value_type: 可选，指定后 ``get`` 会把读回的 dict 还原为该类型实例。
    """
    backend = os.environ.get("LEARNFLOW_STATE_BACKEND", "memory").strip().lower()
    if backend == "memory":
        return MemoryStateStore()
    if backend == "json":
        path = os.path.join(_state_dir(), _safe_state_name(name) + ".json")
        return DataclassJSONStateStore(path=path, value_type=value_type)
    logger.warning(
        "未知的 LEARNFLOW_STATE_BACKEND=%r，回退 MemoryStateStore", backend
    )
    return MemoryStateStore()
