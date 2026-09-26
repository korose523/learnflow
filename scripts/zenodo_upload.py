#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zenodo v0.2.0 上传器（就绪即传 · 默认 dry-run）。

本脚本为 LearnFlow E 任务（Zenodo v0.2.0 上传）的就绪工具：
  - 读取仓库根 .zenodo.json 作为 deposition 元数据；
  - 用 `git archive` 生成源码 tarball（自动尊重 .gitignore，排除 data/.venv/
    node_modules/artifacts/state/experiments.json 等）；
  - 对已有 deposition 建 newversion（接续 v0.1.0），或新建 deposition；
  - 上传 tarball 并 publish。

安全约束：
  - 默认 dry-run：仅打印计划，不发起任何网络请求；
  - 仅当显式传 --yes 且设置好 token 才执行写操作；
  - 绝不删除任何 deposition；publish 为一次性的、需你确认。

前置（外部，须作者提供）：
  - ZENODO_TOKEN（生产）或 ZENODO_SANDBOX_TOKEN（沙盒测试）；
  - ZENODO_DEPOSITION_ID（v0.1.0 记录 ID；用于 newversion；不填则新建）；
  - 建议先打 git tag v0.2.0 并 git push --tags（用 --ref v0.2.0 取该快照）。

依赖：仅 Python 3 标准库。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ZENODO_JSON = REPO_ROOT / ".zenodo.json"


def load_meta():
    with open(ZENODO_JSON, encoding="utf-8") as f:
        return json.load(f)


def build_tarball(ref: str) -> str:
    tar = tempfile.NamedTemporaryFile(prefix="learnflow-", suffix=".tar.gz", delete=False)
    tar.close()
    subprocess.run(
        ["git", "archive", "--format=tar.gz", "--output", tar.name, ref],
        cwd=str(REPO_ROOT),
        check=True,
    )
    size = os.path.getsize(tar.name)
    return tar.name, size


def api_base(sandbox: bool) -> str:
    return "https://sandbox.zenodo.org/api" if sandbox else "https://zenodo.org/api"


def _http(method: str, url: str, token: str, data=None, file_path=None):
    headers = {"Authorization": f"Bearer {token}"}
    if file_path is None:
        body = json.dumps(data).encode("utf-8") if data is not None else None
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    else:
        boundary = "----zenodoboundary%s" % uuid.uuid4().hex
        with open(file_path, "rb") as fh:
            filedata = fh.read()
        fname = os.path.basename(file_path).encode("utf-8")
        crlf = b"\r\n"
        body = (
            b"--" + boundary.encode() + crlf
            + b'Content-Disposition: form-data; name="file"; filename="' + fname + b'"' + crlf
            + b"Content-Type: application/octet-stream" + crlf + crlf
            + filedata + crlf
            + b"--" + boundary.encode() + b"--" + crlf
        )
        headers["Content-Type"] = "multipart/form-data; boundary=%s" % boundary.decode()
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit("✗ HTTP %s on %s:\n%s" % (e.code, url, e.read().decode("utf-8")[:800]))


def main():
    ap = argparse.ArgumentParser(description="Zenodo v0.2.0 uploader (dry-run by default)")
    ap.add_argument("--yes", action="store_true", help="实际执行写操作（默认 dry-run）")
    ap.add_argument("--sandbox", action="store_true", help="指向 sandbox.zenodo.org（先测）")
    ap.add_argument("--ref", default="HEAD", help="git ref 用于打包（默认 HEAD；建议 v0.2.0）")
    ap.add_argument("--tarball", default=None, help="直接用已有 tarball，跳过 git archive")
    ap.add_argument("--deposition-id", default=os.environ.get("ZENODO_DEPOSITION_ID"))
    args = ap.parse_args()

    token_env = "ZENODO_SANDBOX_TOKEN" if args.sandbox else "ZENODO_TOKEN"
    token = os.environ.get(token_env)
    if args.yes and not token:
        sys.exit("✗ 缺少 %s。dry-run 可无 token；实际发布必须提供。" % token_env)

    meta = load_meta()
    if args.tarball:
        tarball, size = args.tarball, os.path.getsize(args.tarball)
    else:
        tarball, size = build_tarball(args.ref)

    base = api_base(args.sandbox)
    mode = "newversion of %s" % args.deposition_id if args.deposition_id else "new deposition"

    plan = {
        "zenodo_api": base,
        "mode": mode,
        "metadata_title": meta.get("title"),
        "version": meta.get("version"),
        "license": meta.get("license"),
        "upload_type": meta.get("upload_type"),
        "tarball": tarball,
        "tarball_bytes": size,
        "will_publish": args.yes,
    }
    print(json.dumps(plan, indent=2, ensure_ascii=False))

    if not args.yes:
        print("\n[dry-run] 未执行任何网络请求。设置好 token 后加 --yes 执行实际上传；")
        print("          接续 v0.1.0 请设 ZENODO_DEPOSITION_ID；建议先打 git tag v0.2.0 --ref v0.2.0。")
        return

    # ── 实际执行（需 token）──
    if args.deposition_id:
        r = _http("POST", f"{base}/deposit/depositions/{args.deposition_id}/actions/newversion",
                  token)
        draft_url = r["links"]["latest_draft"]
        dep_id = draft_url.rstrip("/").split("/")[-1]
        # newversion 复制旧元数据，须用 v0.2.0 的 .zenodo.json 覆盖
        _http("PUT", f"{base}/deposit/depositions/{dep_id}", token, data={"metadata": meta})
    else:
        r = _http("POST", f"{base}/deposit/depositions", token, data={"metadata": meta})
        dep_id = r["id"]

    _http("PUT", f"{base}/deposit/depositions/{dep_id}/files", token, file_path=tarball)
    pub = _http("POST", f"{base}/deposit/depositions/{dep_id}/actions/publish", token)
    print("\n✓ 已发布 deposition")
    print("  DOI :", pub.get("doi"))
    print("  id  :", pub.get("id"))
    print("  URL :", pub.get("links", {}).get("html"))


if __name__ == "__main__":
    main()
