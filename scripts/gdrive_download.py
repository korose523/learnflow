#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Google Drive 数据集下载器（stdlib，带 confirm-token 与 cookie 处理）"""
import re
import sys
import json
import http.cookiejar
from pathlib import Path
from urllib.request import build_opener, HTTPCookieProcessor, Request
from urllib.error import HTTPError, URLError

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
OUT = Path(r"E:/learnflow\data")

FILES = {
    # id: (出力名, 是否大文件)
    "1NNXHFRxcArrU0ZJSb9BIL56vmUt5FhlE": "assist09_corrected.csv",
    "1eFiIYyh5O2V90RA0brammGH6EpHvPDQe": "XES3G5M.zip",
}

def make_opener():
    cj = http.cookiejar.CookieJar()
    return build_opener(HTTPCookieProcessor(cj)), cj

def download(fid: str, name: str):
    out = OUT / name
    if out.exists() and out.stat().st_size > 1_000_000:
        print(f"[skip] {name} already {out.stat().st_size} bytes", flush=True)
        return True
    op, cj = make_opener()
    url = f"https://drive.google.com/uc?export=download&id={fid}"
    req = Request(url, headers={"User-Agent": UA})
    try:
        r = op.open(req, timeout=60)
        head = r.read(2048)
        ctype = r.headers.get("Content-Type", "")
        print(f"[info] first response: {ctype}", flush=True)
        rest = b""
        # 若返回 HTML（病毒扫描警告页），解析 usercontent 直链
        if b"text/html" in ctype.encode():
            html = head + r.read()
            # 解析 form action + 全部 hidden input，拼成完整 GET url
            m = re.search(rb'action="([^"]*drive\.usercontent\.google\.com[^"]*)"', html)
            pairs = re.findall(rb'name="([^"]+)"\s+value="([^"]*)"', html)
            params = {}
            for k, v in pairs:
                params[k.decode("utf-8", "replace")] = v.decode("utf-8", "replace")
            if m:
                base = m.group(1).decode("utf-8", "replace").replace("&amp;", "&")
                from urllib.parse import urlencode
                url = base + ("&" if "?" in base else "?") + urlencode(params)
                print(f"[info] confirm url: {url[:160]}", flush=True)
            else:
                from urllib.parse import urlencode
                base = f"https://drive.usercontent.google.com/download"
                params.setdefault("id", fid)
                params.setdefault("export", "download")
                params.setdefault("confirm", "t")
                url = base + "?" + urlencode(params)
                print(f"[warn] no form found, fallback url", flush=True)
            req = Request(url, headers={"User-Agent": UA})
            r = op.open(req, timeout=120)
        else:
            # 已是数据流：把已读的 head 放回
            def gen():
                yield head
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    yield chunk
                return
            total = 0
            tmp = out.with_suffix(out.suffix + ".part")
            with open(tmp, "wb") as f:
                for chunk in gen():
                    f.write(chunk)
                    total += len(chunk)
                    if total % (50 << 20) < (1 << 20):
                        print(f"[dl] {name}: {total/1e6:.1f} MB", flush=True)
            tmp.rename(out)
            print(f"[done] {name}: {total} bytes", flush=True)
            return True
        # usercontent 分支
        total = 0
        tmp = out.with_suffix(out.suffix + ".part")
        with open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
                if total % (50 << 20) < (1 << 20):
                    print(f"[dl] {name}: {total/1e6:.1f} MB", flush=True)
        tmp.rename(out)
        print(f"[done] {name}: {total} bytes", flush=True)
        return True
    except (HTTPError, URLError, OSError) as e:
        print(f"[FAIL] {name}: {e}", flush=True)
        return False

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    targets = sys.argv[1:] or list(FILES)
    ok = {}
    for fid in targets:
        name = FILES[fid]
        ok[name] = download(fid, name)
    print(json.dumps(ok, ensure_ascii=False), flush=True)
