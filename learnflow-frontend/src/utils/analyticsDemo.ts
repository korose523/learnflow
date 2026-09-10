// AI 实时分析层 · 演示数据生成器
// 把合成行为事件灌入 /api/v1/analytics/ingest，使线上风险模型（已训练，AUROC≈0.97）
// 产生可演示的、彼此分离的风险分布。事件 schema 与后端 feature_store 严格对应：
//   user_id, created_at(epoch s), is_correct, hints_used, thinking_ms,
//   skipped, session_id, decision_snapshot{fused_d, zone}
//
// 三种画像对应论文「成瘾签名」：
//   healthy —— 日间、正确率高、少提示、心流区、思考充分
//   watch   —— 傍晚/夜间混合、正确率中等、提示偏多
//   high    —— 深夜高发、提示依赖、思考浅、连续错、非沉浸

export type RiskProfile = 'healthy' | 'watch' | 'high';

export interface DemoStudent {
  id: string;
  name: string;
  profile: RiskProfile;
}

export const DEMO_CLASS_ID = 'demo-class';

export const DEMO_STUDENTS: DemoStudent[] = [
  { id: 's-anna', name: '安娜', profile: 'healthy' },
  { id: 's-ben', name: '本本', profile: 'healthy' },
  { id: 's-coco', name: '可可', profile: 'healthy' },
  { id: 's-dora', name: '朵拉', profile: 'healthy' },
  { id: 's-evan', name: '伊凡', profile: 'healthy' },
  { id: 's-faye', name: '菲儿', profile: 'healthy' },
  { id: 's-gabe', name: '格格', profile: 'watch' },
  { id: 's-hugo', name: ' Hugo', profile: 'watch' },
  { id: 's-iris', name: '艾莉', profile: 'watch' },
  { id: 's-jack', name: '杰克', profile: 'high' },
  { id: 's-kira', name: '琪拉', profile: 'high' },
  { id: 's-leo', name: '雷欧', profile: 'high' },
];

function localEpoch(hour: number, dayOffset = 0): number {
  const d = new Date();
  d.setDate(d.getDate() + dayOffset);
  d.setHours(hour, Math.floor(Math.random() * 60), Math.floor(Math.random() * 60), 0);
  return Math.floor(d.getTime() / 1000);
}

function rand(min: number, max: number): number {
  return min + Math.random() * (max - min);
}
function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function makeEvent(studentId: string, profile: RiskProfile, i: number): any {
  const cfg = {
    healthy: {
      hours: [9, 10, 11, 14, 15, 16, 19, 20],
      correct: 0.86, hints: [0, 1], think: [8000, 32000], skip: 0.08,
      zones: ['flow', 'deep', 'immersive', 'focus'], fused: [40, 68],
    },
    watch: {
      hours: [13, 14, 20, 21, 22],
      correct: 0.6, hints: [1, 2, 3], think: [4000, 16000], skip: 0.22,
      zones: ['focus', 'focus', 'surface'], fused: [55, 82],
    },
    high: {
      hours: [22, 23, 0, 1, 2, 6, 21],
      correct: 0.34, hints: [3, 4, 5, 6, 8], think: [1000, 6500], skip: 0.42,
      zones: ['surface', 'focus', 'surface'], fused: [70, 96],
    },
  }[profile];

  const isCorrect = Math.random() < cfg.correct;
  const zone = pick(cfg.zones);
  return {
    user_id: studentId,
    event_type: 'ANSWERED',
    created_at: localEpoch(pick(cfg.hours)),
    is_correct: isCorrect,
    hints_used: pick(cfg.hints),
    thinking_ms: Math.round(rand(cfg.think[0], cfg.think[1])),
    skipped: Math.random() < cfg.skip,
    session_id: `${studentId}-s1`,
    decision_snapshot: {
      fused_d: Math.round(rand(cfg.fused[0], cfg.fused[1])),
      zone,
    },
  };
}

export function generateStudentEvents(student: DemoStudent, n = 45): any[] {
  return Array.from({ length: n }, (_, i) => makeEvent(student.id, student.profile, i));
}

/** 把所有演示学生的合成事件灌入后端 /ingest。返回学生列表供后续查询。 */
export async function seedDemoEvents(ingest: (events: any[]) => Promise<any>): Promise<DemoStudent[]> {
  const all: any[] = [];
  for (const s of DEMO_STUDENTS) all.push(...generateStudentEvents(s));
  await ingest(all);
  return DEMO_STUDENTS;
}
