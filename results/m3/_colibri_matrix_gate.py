#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_colibri_matrix_gate.py —— 对 colibri 侧标注产物跑 build_matrix_rows 的三重门禁。

做法：importlib 载入 results/m3/build_matrix_rows.py（审计过的报告器，零代码改动），
仅猴补丁其路径/锚点常量指向 colibri 产物：
    JSONL      -> local_matrix_colibri.jsonl
    SUMMARY    -> local_matrix_colibri.json
    META_SMALL -> local_matrix_meta_colibri.json
    ANCHOR_MODEL -> qwen3.6-colibri
    M3         -> 本目录（门禁 JSON 落 protocol_usability_colibri.json，避免覆盖
                  ollama 侧的 protocol_usability.json —— 落盘名由 builder 内部写死，
                  故改写其 M3 指向后在本目录收集再重命名）
输出：
    protocol_usability_colibri.json（三重门禁逐格判定）
    stdout 报告（供证据链文档引用）
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location("bmr", HERE / "build_matrix_rows.py")
bmr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bmr)

# —— 猴补丁：只改路径与锚点，不改任何判定逻辑 ——
bmr.M3 = HERE
bmr.JSONL = HERE / "local_matrix_colibri.jsonl"
bmr.SUMMARY = HERE / "local_matrix_colibri.json"
bmr.META_SMALL = HERE / "local_matrix_meta_colibri.json"
bmr.META_ANCHOR = HERE / "local_matrix_meta_colibri.json"
bmr.ANCHOR_MODEL = "qwen3.6-colibri"

sys.argv = ["_colibri_matrix_gate.py"]          # builder 的 argparse 不接收额外参数
rc = bmr.main()

# builder 把门禁写死到 M3/protocol_usability.json；本目录名即 results/m3，
# 先挪走 colibri 门禁产物再恢复原名，避免覆盖 ollama 侧文件
gate = HERE / "protocol_usability.json"
if gate.is_file():
    shutil.move(str(gate), str(HERE / "protocol_usability_colibri.json"))
    print(f"[moved] protocol_usability.json -> protocol_usability_colibri.json")

sys.exit(rc or 0)
