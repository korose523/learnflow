// dbe_fetch.mjs — 用 playwright-core 过 Dataverse JS 反爬并下载 DBE-KT22
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { globSync } from 'node:fs';

const OUT = String.raw`C:\Users\mac\WorkBuddy\2026-09-02-22-50-15\data\dbe_kt22`;
fs.mkdirSync(OUT, { recursive: true });

// 找 Chromium 可执行文件
function findChrome() {
  const root = path.join(process.env.LOCALAPPDATA || '', 'ms-playwright');
  if (!fs.existsSync(root)) throw new Error('no ms-playwright cache');
  const dirs = fs.readdirSync(root).filter(d => d.startsWith('chromium-')).sort().reverse();
  for (const d of dirs) {
    for (const sub of ['chrome-win64', 'chrome-win']) {
      const p = path.join(root, d, sub, 'chrome.exe');
      if (fs.existsSync(p)) return p;
    }
  }
  throw new Error('chrome.exe not found');
}

const exe = findChrome();
console.log('[chrome]', exe);
const browser = await chromium.launch({ executablePath: exe, headless: true });
const ctx = await browser.newContext({
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
});
const page = await ctx.newPage();

const API = 'https://dataverse.ada.edu.au/api/datasets/:persistentId/?persistentId=doi:10.26193/6DZWOH';
await page.goto(API, { waitUntil: 'domcontentloaded', timeout: 60000 });

// 轮询等反爬挑战放行（body 变成 JSON）
let body = '';
for (let i = 0; i < 30; i++) {
  await page.waitForTimeout(2000);
  body = await page.evaluate(() => document.body ? document.body.innerText : '');
  const t = body.trim();
  if (t.startsWith('{') || t.startsWith('[')) { console.log('[ok] challenge cleared at', (i + 1) * 2, 's'); break; }
}
const trimmed = body.trim();
if (!trimmed.startsWith('{')) {
  console.log('[FAIL] still blocked. head:', trimmed.slice(0, 200));
  await browser.close();
  process.exit(2);
}
fs.writeFileSync(path.join(OUT, '_dataset_api.json'), trimmed, 'utf-8');
const meta = JSON.parse(trimmed);
const files = (meta.data?.latestVersion?.files || []).map(f => ({
  id: f.dataFile.id,
  name: f.dataFile.filename,
  size: f.dataFile.filesize,
}));
console.log('[files]', JSON.stringify(files, null, 1));

// 用共享 cookie 的 APIRequestContext 下载每个文件
let ok = 0;
for (const f of files) {
  const url = `https://dataverse.ada.edu.au/api/access/datafile/${f.id}`;
  const dest = path.join(OUT, f.name);
  try {
    const resp = await ctx.request.get(url, { timeout: 300000 });
    if (!resp.ok()) { console.log('[FAIL]', f.name, resp.status()); continue; }
    const buf = await resp.body();
    fs.writeFileSync(dest, buf);
    ok++;
    console.log('[done]', f.name, buf.length, 'bytes');
  } catch (e) {
    console.log('[ERR]', f.name, String(e).slice(0, 200));
  }
}
console.log('[summary]', ok, '/', files.length, 'files');
await browser.close();
process.exit(ok === files.length ? 0 : 1);
