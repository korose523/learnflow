import { createWorkBuddyCloud } from '@tencent-ai/workbuddy-cloud-sdk';
import { readFileSync, writeFileSync } from 'node:fs';

const cloud = createWorkBuddyCloud({
  endpoint: 'https://learnflow-m3.app.workbuddy.host',
  publishableKey: 'wbpk_hQLryzm3q8l7pV0ICsheMd_OE7SPIY1Z3OiGqyWv62vVMEB07nbmbUs',
});

const DBE_Q = 'E:/learnflow/data/dbe_kt22/csv/Questions.csv';
const DBE_T = 'E:/learnflow/data/dbe_kt22/csv/Transaction.csv';
const OUT = 'E:/learnflow/results/m3/c_matrix_results.json';

function readCsv(path) {
  const text = readFileSync(path, 'utf-8');
  const rows = [];
  let i = 0, n = text.length, row = [], field = '', q = false;
  while (i < n) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i += 2; continue; } q = false; i++; continue; }
      field += c; i++; continue;
    }
    if (c === '"') { q = true; i++; continue; }
    if (c === ',') { row.push(field); field = ''; i++; continue; }
    if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(field); rows.push(row); row = []; field = ''; i++; continue; }
    field += c; i++;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows;
}

function buildSample() {
  const qrows = readCsv(DBE_Q);
  const header = qrows[0];
  const idx = Object.fromEntries(header.map((h, k) => [h, k]));
  const items = {};
  for (let r = 1; r < qrows.length; r++) {
    const row = qrows[r];
    const id = row[idx['id']];
    const label = parseInt(row[idx['difficulty']], 10);
    if (![1, 2, 3].includes(label)) continue;
    let text = row[idx['question_text']] || row[idx['question_rich_text']] || '';
    text = text.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 1400);
    items[id] = { label, text };
  }
  const trows = readCsv(DBE_T);
  const th = trows[0];
  const ti = Object.fromEntries(th.map((h, k) => [h, k]));
  const succ = {};
  for (let r = 1; r < trows.length; r++) {
    const row = trows[r];
    const qid = row[ti['question_id']];
    if (!(qid in items)) continue;
    const c = row[ti['answer_state']]?.trim().toLowerCase() === 'true' ? 1 : 0;
    if (!succ[qid]) succ[qid] = [0, 0];
    succ[qid][0] += c; succ[qid][1] += 1;
  }
  const cand = {};
  for (const [id, it] of Object.entries(items)) {
    if (succ[id] && succ[id][1] > 0) cand[id] = { ...it, emp_diff: -(succ[id][0] / succ[id][1]) };
  }
  const byLabel = { 1: [], 2: [], 3: [] };
  for (const [id, it] of Object.entries(cand)) byLabel[it.label].push(id);
  const rng = (() => { let a = 20260923; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; })();
  const sample = [];
  for (const L of [1, 2, 3]) {
    const arr = byLabel[L].slice();
    for (let i = arr.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [arr[i], arr[j]] = [arr[j], arr[i]]; }
    for (const id of arr.slice(0, 20)) sample.push({ id, ...cand[id] });
  }
  return sample;
}

function spearman(a, b) {
  const n = a.length;
  if (n < 2) return NaN;
  const rank = (xs) => {
    const order = xs.map((_, i) => i).sort((p, q) => xs[p] - xs[q]);
    const r = new Array(n).fill(0); let i = 0;
    while (i < n) { let j = i; while (j + 1 < n && xs[order[j + 1]] === xs[order[i]]) j++; const avg = (i + j) / 2 + 1; for (let k = i; k <= j; k++) r[order[k]] = avg; i = j + 1; }
    return r;
  };
  const ra = rank(a), rb = rank(b);
  const ma = ra.reduce((s, x) => s + x, 0) / n, mb = rb.reduce((s, x) => s + x, 0) / n;
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < n; i++) { num += (ra[i] - ma) * (rb[i] - mb); da += (ra[i] - ma) ** 2; db += (rb[i] - mb) ** 2; }
  if (da === 0 || db === 0) return NaN;
  return num / Math.sqrt(da * db);
}

function parseRating(resp) { const m = resp.match(/[123]/); return m ? parseInt(m[0], 10) : null; }

async function rateOne(modelId, item, diag) {
  const prompt = `Rate the difficulty of this math problem on a 1-3 scale (1=easiest, 3=hardest). Reply with ONLY a single integer 1, 2, or 3.\n\nProblem: ${item.text}`;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      let answer = '';
      for await (const chunk of cloud.llm.chat.completions.create({
        model: modelId,
        messages: [
          { role: 'system', content: 'You are a precise math difficulty rater. Reply with only a single integer 1, 2, or 3.' },
          { role: 'user', content: prompt },
        ],
        stream: true,
      })) {
        const d = chunk.choices?.[0]?.delta?.content;
        if (d) answer += d;
      }
      if (diag && diag.length < 5) diag.push(answer.slice(0, 60));
      const rating = parseRating(answer);
      if (rating) return { rating, raw: answer.slice(0, 40) };
      if (attempt < 2) continue;
      return { rating: null, raw: answer.slice(0, 40) };
    } catch (e) {
      const code = e?.error?.code || '';
      if (attempt < 2 && (code.startsWith('gateway_') || code.startsWith('model_') || code.startsWith('quota_'))) { await new Promise((r) => setTimeout(r, 1500)); continue; }
      if (diag && diag.length < 5) diag.push('ERR:' + (e?.error?.message || e?.message || String(e)).slice(0, 60));
      return { rating: null, raw: 'ERR:' + (e?.error?.message || e?.message || String(e)).slice(0, 60) };
    }
  }
  return { rating: null, raw: 'ERR:max-attempts' };
}

const sample = buildSample();
console.log(`[rerun] sample=${sample.length}`);

const CANDIDATES = ['glm-4.7', 'glm-4.6', 'glm-4.6v'];
let chosen = null;
for (const mid of CANDIDATES) {
  console.log(`\n=== trying model ${mid} ===`);
  const diag = [];
  const ratings = [];
  for (let i = 0; i < sample.length; i++) {
    const r = await rateOne(mid, sample[i], diag);
    ratings.push(r.rating);
    if ((i + 1) % 10 === 0) console.log(`   ... ${i + 1}/${sample.length}`);
    await new Promise((res) => setTimeout(res, 120));
  }
  console.log(`  raw samples: ${JSON.stringify(diag)}`);
  const valid = sample.map((s, i) => i).filter((i) => ratings[i] != null);
  const lab = valid.map((i) => sample[i].label);
  const emp = valid.map((i) => sample[i].emp_diff);
  const rt = valid.map((i) => ratings[i]);
  const rho_expert = spearman(rt, lab);
  const rho_emp = spearman(rt, emp);
  const meanRt = rt.reduce((s, x) => s + x, 0) / (rt.length || 1);
  console.log(`  n_valid=${valid.length}/${sample.length} ρ(expert)=${rho_expert.toFixed(3)} ρ(emp)=${rho_emp.toFixed(3)} mean=${meanRt.toFixed(2)}`);
  if (valid.length >= 50) {
    chosen = { model: mid, n_valid: valid.length, n_total: sample.length, rho_expert, rho_emp, meanRt };
    break;
  }
}
if (!chosen) { console.log('[rerun] ALL candidates failed — abort, leaving JSON unchanged'); process.exit(1); }

console.log(`\n[rerun] CHOSEN ${chosen.model} (n_valid=${chosen.n_valid})`);
const data = JSON.parse(readFileSync(OUT, 'utf-8'));
const cell = data.cells.find((c) => c.family === 'GLM' && c.scale === 'small');
if (!cell) { console.log('[rerun] GLM/small cell not found in JSON'); process.exit(1); }
cell.model = chosen.model;
cell.n_valid = chosen.n_valid;
cell.n_total = chosen.n_total;
cell.spearman_expert_label = +chosen.rho_expert.toFixed(4);
cell.spearman_empirical_difficulty = +chosen.rho_emp.toFixed(4);
cell.mean_rating = +chosen.meanRt.toFixed(3);
writeFileSync(OUT, JSON.stringify(data, null, 2));
console.log('[rerun] DONE →', OUT);
