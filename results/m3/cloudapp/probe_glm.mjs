import { createWorkBuddyCloud } from '@tencent-ai/workbuddy-cloud-sdk';
import { readFileSync } from 'node:fs';

const cloud = createWorkBuddyCloud({
  endpoint: 'https://learnflow-m3.app.workbuddy.host',
  publishableKey: 'wbpk_hQLryzm3q8l7pV0ICsheMd_OE7SPIY1Z3OiGqyWv62vVMEB07nbmbUs',
});

const DBE_Q = 'E:/learnflow/data/dbe_kt22/csv/Questions.csv';
function readCsv(path) {
  const text = readFileSync(path, 'utf-8');
  const rows = []; let i = 0, n = text.length, row = [], field = '', q = false;
  while (i < n) { const c = text[i];
    if (q) { if (c === '"') { if (text[i+1]==='"'){field+='"';i+=2;continue;} q=false;i++;continue;} field+=c;i++;continue; }
    if (c === '"') { q=true;i++;continue; }
    if (c === ',') { row.push(field);field='';i++;continue; }
    if (c === '\n' || c === '\r') { if (c==='\r'&&text[i+1]==='\n') i++; row.push(field);rows.push(row);row=[];field='';i++;continue; }
    field+=c;i++; }
  if (field.length||row.length){row.push(field);rows.push(row);} return rows;
}
const qrows = readCsv(DBE_Q);
const header = qrows[0]; const idx = Object.fromEntries(header.map((h,k)=>[h,k]));
let text = '';
for (let r=1; r<qrows.length; r++){ const row=qrows[r]; const label=parseInt(row[idx['difficulty']],10); if(label!==1) continue; text=(row[idx['question_text']]||'').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim().slice(0,600); if(text) break; }
const prompt = `Rate the difficulty of this math problem on a 1-3 scale (1=easiest, 3=hardest). Reply with ONLY a single integer 1, 2, or 3.\n\nProblem: ${text}`;

const CANDIDATES = ['glm-4.5','glm-4.5-air','glm-4.6','glm-4.6-plus','glm-4.7','glm-4.7-plus','glm-5.0','glm-5.0-air','glm-5.1-air','glm-4.7v','glm-4.7v-flash'];
function parseRating(resp){ const m=resp.match(/[123]/); return m?parseInt(m[0],10):null; }
for (const mid of CANDIDATES) {
  let answer=''; let err='';
  for (let attempt=0; attempt<2; attempt++){
    try {
      for await (const chunk of cloud.llm.chat.completions.create({ model: mid, messages:[{role:'system',content:'You are a precise math difficulty rater. Reply with only a single integer 1, 2, or 3.'},{role:'user',content:prompt}], stream:true })){ const d=chunk.choices?.[0]?.delta?.content; if(d) answer+=d; }
      break;
    } catch(e){ err='ERR:'+(e?.error?.message||e?.message||String(e)).slice(0,50); await new Promise(r=>setTimeout(r,800)); }
  }
  const rating = parseRating(answer);
  console.log(`${mid.padEnd(14)} -> ${rating!=null?'VALID('+rating+')':('INVALID raw='+(answer||err).slice(0,40))}`);
  await new Promise(r=>setTimeout(r,300));
}
