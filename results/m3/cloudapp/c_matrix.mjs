import { createWorkBuddyCloud } from '@tencent-ai/workbuddy-cloud-sdk';
import { readFileSync, writeFileSync } from 'node:fs';

const cloud = createWorkBuddyCloud({
  endpoint: 'https://learnflow-m3.app.workbuddy.host',
  publishableKey: 'wbpk_hQLryzm3q8l7pV0ICsheMd_OE7SPIY1Z3OiGqyWv62vVMEB07nbmbUs',
});

const DBE_Q = 'E:/learnflow/data/dbe_kt22/csv/Questions.csv';
const DBE_T = 'E:/learnflow/data/dbe_kt22/csv/Transaction.csv';
const OUT = 'E:/learnflow/results/m3/c_matrix_results.json';

// ── 3 families × 3 scales ───────────────────────────────────────────────
const MODELS = [
  { family: 'Hunyuan', scale: 'small', id: 'hy3' },
  { family: 'Hunyuan', scale: 'large', id: 'hy4-preview' },
  { family: 'Hunyuan', scale: 'thinking', id: 'hunyuan-2.0-thinking' },
  { family: 'GLM', scale: 'small', id: 'glm-4.7' },
  { family: 'GLM', scale: 'mid', id: 'glm-5.1' },
  { family: 'GLM', scale: 'flagship', id: 'glm-5.3' },
  { family: 'DeepSeek', scale: 'small', id: 'deepseek-v3-2-volc' },
  { family: 'DeepSeek', scale: 'flash', id: 'deepseek-v4-flash' },
  { family: 'DeepSeek', scale: 'pro', id: 'deepseek-v4-pro' },
];
const PER_LABEL = 20; // 20 × 3 labels = 60 items

// ── manual CSV line reader (handles quoted commas) ──────────────────────
function readCsv(path) {
  const text = readFileSync(path, 'utf-8');
  const rows = [];
  let i = 0, n = text.length, row = [], field = '', q = false;
  while (i < n) {
    const c = text[i];
    if (q) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 2; continue; }
        q = false; i++; continue;
      }
      field += c; i++; continue;
    }
    if (c === '"') { q = true; i++; continue; }
    if (c === ',') { row.push(field); field = ''; i++; continue; }
    if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); rows.push(row); row = []; field = ''; i++; continue;
    }
    field += c; i++;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows;
}

// ── build benchmark sample ──────────────────────────────────────────────
function buildSample() {
  const qrows = readCsv(DBE_Q);
  const header = qrows[0];
  const idx = Object.fromEntries(header.map((h, k) => [h, k]));
  const items = {}; // id -> {label, text}
  for (let r = 1; r < qrows.length; r++) {
    const row = qrows[r];
    const id = row[idx['id']];
    const label = parseInt(row[idx['difficulty']], 10);
    if (![1, 2, 3].includes(label)) continue;
    let text = row[idx['question_text']] || row[idx['question_rich_text']] || '';
    text = text.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 1400);
    items[id] = { label, text };
  }
  // empirical success rate
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
  // keep items with transactions
  const cand = {};
  for (const [id, it] of Object.entries(items)) {
    if (succ[id] && succ[id][1] > 0) {
      cand[id] = { ...it, emp_diff: -(succ[id][0] / succ[id][1]) }; // higher = harder
    }
  }
  // stratified deterministic sample: 20 per label
  const byLabel = { 1: [], 2: [], 3: [] };
  for (const [id, it] of Object.entries(cand)) byLabel[it.label].push(id);
  // seeded shuffle (mulberry32) for determinism
  const rng = (() => { let a = 20260923; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; })();
  const sample = [];
  for (const L of [1, 2, 3]) {
    const arr = byLabel[L].slice();
    for (let i = arr.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [arr[i], arr[j]] = [arr[j], arr[i]]; }
    for (const id of arr.slice(0, PER_LABEL)) sample.push({ id, ...cand[id] });
  }
  return sample;
}

// ── spearman (rank-avg) ─────────────────────────────────────────────────
function spearman(a, b) {
  const n = a.length;
  if (n < 2) return NaN;
  const rank = (xs) => {
    const order = xs.map((_, i) => i).sort((p, q) => xs[p] - xs[q]);
    const r = new Array(n).fill(0);
    let i = 0;
    while (i < n) {
      let j = i;
      while (j + 1 < n && xs[order[j + 1]] === xs[order[i]]) j++;
      const avg = (i + j) / 2 + 1;
      for (let k = i; k <= j; k++) r[order[k]] = avg;
      i = j + 1;
    }
    return r;
  };
  const ra = rank(a), rb = rank(b);
  const ma = ra.reduce((s, x) => s + x, 0) / n, mb = rb.reduce((s, x) => s + x, 0) / n;
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < n; i++) { num += (ra[i] - ma) * (rb[i] - mb); da += (ra[i] - ma) ** 2; db += (rb[i] - mb) ** 2; }
  if (da === 0 || db === 0) return NaN;
  return num / Math.sqrt(da * db);
}

// ── LLM call with retry ──────────────────────────────────────────────────
function stripTags(s) { return s.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(); }
function parseRating(resp) {
  const m = resp.match(/[123]/);
  return m ? parseInt(m[0], 10) : null;
}
async function rateOne(modelId, item) {
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
      const rating = parseRating(answer);
      if (rating) return { rating, raw: answer.slice(0, 40) };
      if (attempt < 2) continue;
      return { rating: null, raw: answer.slice(0, 40) };
    } catch (e) {
      const code = e?.error?.code || '';
      if (attempt < 2 && (code.startsWith('gateway_') || code.startsWith('model_') || code.startsWith('quota_'))) {
        await new Promise((r) => setTimeout(r, 1500));
        continue;
      }
      return { rating: null, raw: 'ERR:' + (e?.error?.message || e?.message || String(e)).slice(0, 60) };
    }
  }
  return { rating: null, raw: 'ERR:max-attempts' };
}

// ── main ─────────────────────────────────────────────────────────────────
const sample = buildSample();
console.log(`[C] benchmark sample = ${sample.length} items (labels: ${[1,2,3].map(L => sample.filter(s=>s.label===L).length).join('/')})`);
const results = [];
for (const m of MODELS) {
  console.log(`[C] model ${m.family}/${m.scale} (${m.id}) ...`);
  const ratings = [];
  for (let i = 0; i < sample.length; i++) {
    const r = await rateOne(m.id, sample[i]);
    ratings.push(r.rating);
    if ((i + 1) % 10 === 0) console.log(`   ... ${i + 1}/${sample.length}`);
    await new Promise((res) => setTimeout(res, 120));
  }
  const valid = sample.map((s, i) => i).filter((i) => ratings[i] != null);
  const lab = valid.map((i) => sample[i].label);
  const emp = valid.map((i) => sample[i].emp_diff);
  const rt = valid.map((i) => ratings[i]);
  const rho_expert = spearman(rt, lab);
  const rho_emp = spearman(rt, emp);
  const meanRt = rt.reduce((s, x) => s + x, 0) / (rt.length || 1);
  results.push({
    family: m.family, scale: m.scale, model: m.id,
    n_valid: valid.length, n_total: sample.length,
    spearman_expert_label: +rho_expert.toFixed(4),
    spearman_empirical_difficulty: +rho_emp.toFixed(4),
    mean_rating: +meanRt.toFixed(3),
  });
  console.log(`   → ρ(expert)=${rho_expert.toFixed(3)}  ρ(empirical)=${rho_emp.toFixed(3)}  mean=${meanRt.toFixed(2)}`);
}
const out = {
  benchmark: 'DBE-KT22 stratified sample (20 per expert label 1/2/3, n=' + sample.length + ')',
  ground_truth: { expert_label: '1/2/3 (reference prior)', empirical_difficulty: '-success_rate (behavioral)' },
  cells: results,
};
writeFileSync(OUT, JSON.stringify(out, null, 2));
console.log('[C] DONE →', OUT);
