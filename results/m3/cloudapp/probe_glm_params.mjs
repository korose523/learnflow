// probe_glm_params.mjs —— 定位「目录 enabled=true 但调用返回『请求参数无效』」的根因。
//
// 背景：目录（cloud.llm.models.list()）显示 glm-4.7 / glm-4.6 / glm-4.6v 均 enabled=true，
// 但用 c_matrix.mjs 的请求体（messages=[system,user] + stream:true）调用 60/60 全败，
// 错误一律为「请求参数无效。」。同一请求体对 hy3 / glm-5.1 / glm-5.3 等却成功。
//
// 本脚本做受控对照：固定模型、逐项变动请求参数，打印**完整 error 对象**（code / param / status），
// 以判定是「模型不可用」还是「某个参数组合被拒」。
//
// 用法：node probe_glm_params.mjs
// 输出：stdout（不写文件）

import { createWorkBuddyCloud } from '@tencent-ai/workbuddy-cloud-sdk';

const cloud = createWorkBuddyCloud({
  endpoint: 'https://learnflow-m3.app.workbuddy.host',
  publishableKey: 'wbpk_hQLryzm3q8l7pV0ICsheMd_OE7SPIY1Z3OiGqyWv62vVMEB07nbmbUs',
});

const SYS = 'You are a precise math difficulty rater. Reply with only a single integer 1, 2, or 3.';
const USER = 'Rate the difficulty of this math problem on a 1-3 scale. Reply with ONLY 1, 2, or 3.\n\nProblem: 2 + 2 = ?';

// 变体：从最接近 c_matrix 的请求体出发，逐项去掉/改动可疑参数
const VARIANTS = [
  { tag: 'A_system+user (c_matrix 原样)', messages: [{ role: 'system', content: SYS }, { role: 'user', content: USER }] },
  { tag: 'B_user_only (无 system 消息)', messages: [{ role: 'user', content: USER }] },
  { tag: 'C_system+user + temperature:0.7', messages: [{ role: 'system', content: SYS }, { role: 'user', content: USER }], temperature: 0.7 },
  { tag: 'D_system+user + response_format json_object', messages: [{ role: 'system', content: SYS }, { role: 'user', content: USER }], response_format: { type: 'json_object' } },
];

const MODELS = ['glm-4.7', 'glm-4.6', 'hy3', 'glm-5.1'];

function brief(o, n = 400) {
  try { return JSON.stringify(o).slice(0, n); } catch { return String(o).slice(0, n); }
}

async function callOnce(model, v) {
  let answer = '';
  const params = { model, messages: v.messages, stream: true };
  if (v.temperature !== undefined) params.temperature = v.temperature;
  if (v.response_format !== undefined) params.response_format = v.response_format;
  try {
    for await (const chunk of cloud.llm.chat.completions.create(params)) {
      const d = chunk.choices?.[0]?.delta?.content;
      if (d) answer += d;
    }
    return { ok: true, text: answer.slice(0, 60) };
  } catch (e) {
    return {
      ok: false,
      message: e?.error?.message ?? e?.message ?? String(e),
      code: e?.error?.code ?? null,
      status: e?.status ?? e?.response?.status ?? null,
      type: e?.error?.type ?? null,
      param: e?.error?.param ?? null,
      // 逐级把可能的嵌套对象也带出来，避免漏掉诊断信息
      errorKeys: e?.error && typeof e.error === 'object' ? Object.keys(e.error) : null,
      topKeys: e && typeof e === 'object' ? Object.keys(e) : null,
      raw: brief(e, 600),
    };
  }
}

console.log('=== probe_glm_params ===');
for (const m of MODELS) {
  console.log(`\n--- model ${m} ---`);
  for (const v of VARIANTS) {
    const r = await callOnce(m, v);
    if (r.ok) {
      console.log(`  ${v.tag.padEnd(42)} OK   text=${JSON.stringify(r.text)}`);
    } else {
      console.log(`  ${v.tag.padEnd(42)} FAIL msg=${JSON.stringify(r.message)} code=${JSON.stringify(r.code)} status=${JSON.stringify(r.status)} param=${JSON.stringify(r.param)}`);
      console.log(`      errorKeys=${JSON.stringify(r.errorKeys)} topKeys=${JSON.stringify(r.topKeys)}`);
      console.log(`      raw=${r.raw}`);
    }
    await new Promise((res) => setTimeout(res, 300));
  }
}
console.log('\n=== done ===');
