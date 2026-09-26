// dump_model_catalog.mjs —— 把本应用可得的云端 LLM 模型目录 dump 成溯源产物。
//
// 用途：为 M3 稿 §8 ④b（≥3 模型族 × ≥3 规模标注矩阵）的**可得性判定**提供
// 权威、可复现的证据锚点。原试点只记录了「Qwen/Llama/Mistral 端点返回
// 「请求参数无效」」，那是脚本侧观察；本脚本直接取平台目录，说明**平台是否
// 真的提供这些族**，从而把「不可达」从脚本错误升级为平台事实（或反之）。
//
// 同时：目录若给出 family / version / provider 字段，可用于权威地判定模型族归属，
// 避免按模型名猜族。字段缺失一律记 null，**不猜**。
//
// 用法：
//   node dump_model_catalog.mjs
// 输出：
//   E:/learnflow/results/m3/cloud_model_catalog.json

import { createWorkBuddyCloud } from '@tencent-ai/workbuddy-cloud-sdk';
import { writeFileSync } from 'node:fs';

const OUT = 'E:/learnflow/results/m3/cloud_model_catalog.json';

const cloud = createWorkBuddyCloud({
  endpoint: 'https://learnflow-m3.app.workbuddy.host',
  publishableKey: 'wbpk_hQLryzm3q8l7pV0ICsheMd_OE7SPIY1Z3OiGqyWv62vVMEB07nbmbUs',
});

// 方案 §2 预设的四个族，及其模型名的公开前缀（用于判定「平台是否提供该族」）
const PRESET_FAMILY_PREFIXES = {
  F1_Qwen: ['qwen', 'qwq'],
  F2_Llama: ['llama', 'meta-llama'],
  F3_Mistral: ['mistral', 'ministral', 'mixtral', 'magistral', 'codestral'],
  F4_DeepSeek: ['deepseek', 'deepseek-ai'],
};

function norm(s) {
  return String(s == null ? '' : s).toLowerCase().trim();
}

const models = await cloud.llm.models.list();

const rows = models.map((m) => ({
  id: m.id,
  name: m.name ?? null,
  provider: m.provider ?? null,
  vendor: m.vendor ?? null,
  family: m.family ?? null,        // 目录若给出族，则以目录为准；缺失记 null 不猜
  version: m.version ?? null,
  enabled: m.enabled === true,
  disabled: m.disabled ?? null,
  maxInputTokens: m.maxInputTokens ?? null,
  maxOutputTokens: m.maxOutputTokens ?? null,
  supportsImages: m.supportsImages ?? null,
  supportsToolCall: m.supportsToolCall ?? null,
  supportsReasoning: m.supportsReasoning ?? null,
  credits: m.credits ?? null,
  descriptionZh: m.descriptionZh ?? null,
}));

const enabledRows = rows.filter((r) => r.enabled);

// 参数规模可得性：目录是否公开参数量（parames / parameter_size 之类字段）
const paramFieldsSeen = [];
for (const m of models) {
  for (const k of Object.keys(m)) {
    if (/param|size|billion|\bB\b/.test(k) && !paramFieldsSeen.includes(k)) paramFieldsSeen.push(k);
  }
}

const presetCheck = {};
for (const [fam, prefixes] of Object.entries(PRESET_FAMILY_PREFIXES)) {
  const hit = enabledRows.filter((r) => prefixes.some((p) => norm(r.id).startsWith(p)));
  presetCheck[fam] = {
    prefixes_probed: prefixes,
    n_enabled_hits: hit.length,
    ids: hit.map((r) => r.id),
    available_on_platform: hit.length > 0,
  };
}

// 目录 family 字段覆盖情况（决定能否权威判族）
const withFamily = enabledRows.filter((r) => r.family != null);
const familyValues = [...new Set(withFamily.map((r) => r.family))].sort();

const payload = {
  generated_by: 'results/m3/cloudapp/dump_model_catalog.mjs',
  source: 'cloud.llm.models.list() — GET /.cloud/llm/models（平台公开模型目录，只读）',
  endpoint: 'https://learnflow-m3.app.workbuddy.host',
  generated_at_utc: new Date().toISOString(),
  n_models_total: rows.length,
  n_models_enabled: enabledRows.length,
  models: rows,
  preset_family_availability: presetCheck,
  family_field_coverage: {
    n_enabled_with_family_field: withFamily.length,
    n_enabled_without_family_field: enabledRows.length - withFamily.length,
    distinct_family_values: familyValues,
    note: '目录 family 字段缺失时不得按模型名推断族归属；缺失即记 null。',
  },
  parameter_count_disclosure: {
    fields_seen_matching_param_pattern: paramFieldsSeen,
    n_enabled_models_with_explicit_param_count: enabledRows.filter(
      (r) => r.parameter_count_billions != null,
    ).length,
    note: '方案 §3 的 S1–S4 档位按**总参数量**划分；目录若不公开参数量，则无法据目录填档，'
      + '不得以「小/中/大/旗舰」等厂商营销档位冒充参数规模档。',
  },
};

writeFileSync(OUT, JSON.stringify(payload, null, 2));
console.log(`[catalog] models total=${rows.length} enabled=${enabledRows.length} -> ${OUT}`);
for (const [fam, v] of Object.entries(presetCheck)) {
  console.log(`  ${fam.padEnd(12)} available=${v.available_on_platform}  ids=${JSON.stringify(v.ids)}`);
}
console.log(`  family 字段：有 ${withFamily.length} / 无 ${enabledRows.length - withFamily.length}；值=${JSON.stringify(familyValues)}`);
console.log(`  参数量字段：${JSON.stringify(paramFieldsSeen)}`);
