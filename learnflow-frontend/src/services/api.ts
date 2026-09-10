import axios from 'axios';

// CloudBase 后端 API 地址
const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

// ─── 类型增强：为 AxiosRequestConfig 增加可选的缓存控制 ─────────
declare module 'axios' {
  export interface AxiosRequestConfig {
    /** 开启响应缓存：true 使用默认 TTL，或传入毫秒数自定义 TTL */
    cache?: boolean | number;
    /** 跳过进行中的请求去重（极少需要） */
    skipDedup?: boolean;
  }
}

const DEFAULT_TTL = 5 * 60 * 1000; // 5 分钟

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// ─── 响应缓存（内存）+ 并发去重 ────────────────────────────────
interface CacheEntry {
  expiry: number;
  value: any;
}
const responseCache = new Map<string, CacheEntry>();
const inflight = new Map<string, Promise<any>>();

function buildKey(method: string, url: string, config?: any): string {
  const token = localStorage.getItem('access_token') || '';
  const params = config?.params ? JSON.stringify(config.params) : '';
  return `${method}::${token}::${url}::${params}`;
}

/** 失效缓存（可按前缀批量，如 '/student' 使所有学生端缓存失效） */
export function invalidateCache(prefix?: string): void {
  if (!prefix) {
    responseCache.clear();
    return;
  }
  for (const key of responseCache.keys()) {
    if (key.includes(`::${prefix}`)) responseCache.delete(key);
  }
}

const originalGet = api.get.bind(api);

/**
 * 包装后的 GET：
 * - 同一进行中 GET 自动去重（按 method+token+url+params）
 * - config.cache 为真时启用内存响应缓存（TTL 可配）
 * 仅作用于 GET；POST/PUT/DELETE 等直接走原方法，保证既有调用不变。
 */
function cachedGet(url: string, config?: any): Promise<any> {
  const key = buildKey('GET', url, config);
  const shouldDedup = !config?.skipDedup;

  // 1) 并发去重
  if (shouldDedup && inflight.has(key)) {
    return inflight.get(key)!;
  }

  const run = async (): Promise<any> => {
    // 2) 响应缓存命中（仅当显式开启 cache）
    const cacheOpt = config?.cache;
    if (cacheOpt) {
      const hit = responseCache.get(key);
      if (hit && Date.now() < hit.expiry) {
        return hit.value;
      }
    }

    const res = await originalGet(url, config);

    if (cacheOpt && res?.status === 200) {
      const ttl = typeof cacheOpt === 'number' ? cacheOpt : DEFAULT_TTL;
      responseCache.set(key, { expiry: Date.now() + ttl, value: res });
    }
    return res;
  };

  const promise = run();
  if (shouldDedup) {
    inflight.set(key, promise);
    promise.finally(() => inflight.delete(key));
  }
  return promise;
}

// 用包装后的 GET 替换实例方法（保留 post/put/delete 原样）
(api as any).get = cachedGet;

// 请求拦截：自动注入 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截：自动刷新 token
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          // 必须继承 VITE_API_BASE：部署到独立 API 域名时，不能回退到前端当前域名。
          const refreshUrl = `${API_BASE.replace(/\/$/, '')}/auth/refresh`;
          const { data } = await axios.post(refreshUrl, { refresh_token: refreshToken });
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return api.request(error.config);
        } catch {
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// ─── API 方法 ──────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login/json', { email, password }),
  register: (data: { email: string; password: string; name: string; role: string; grade?: string }) =>
    api.post('/auth/register', data),
  oauthLogin: (data: { provider: 'qq' | 'wechat'; oauth_uid: string; name: string; role: string }) =>
    api.post('/auth/login/oauth', data),
  me: () => api.get('/auth/me'),
  refresh: (refresh_token: string) =>
    api.post('/auth/refresh', { refresh_token }),
};

export const studentApi = {
  dashboard: () => api.get('/student/dashboard'),
  nextTask: (topic?: string) => api.get('/student/next-task', { params: { topic } }),
  submitAnswer: (data: { task_id: string; answer: string; time_spent?: number; hints_used?: number; is_retry?: boolean }) =>
    api.post('/student/submit-answer', data),
  recoveryChoice: (data: { task_id: string; choice: string }) =>
    api.post('/student/recovery-choice', data),
  pet: () => api.get('/student/pet'),
  relaxationGuide: () => api.get('/student/relaxation-guide'),
  updateConsent: (data: { consent_type: string; granted: boolean }) =>
    api.post('/student/consent', data),
  dueReviews: () => api.get('/student/due-reviews'),
  healthCheck: () => api.get('/student/health-check'),

  // ── Spec §4 新增端点（K12 自适应）──
  submitAttempt: (data: { task_id: string; correct: boolean; rt_ms: number }) =>
    api.post('/student/attempt', data),
  challenge: () => api.get('/student/challenge', { cache: true }),
};

export const gamificationApi = {
  streak: () => api.get('/student/gamification/streak'),
  xp: () => api.get('/student/gamification/xp'),
  leaderboard: () => api.get('/student/gamification/leaderboard'),
  team: () => api.get('/student/gamification/team'),
  skillTree: () => api.get('/student/gamification/skill-tree'),
  openBox: () => api.post('/student/gamification/open-box'),
  memoryPalace: () => api.get('/student/gamification/memory-palace'),
  dailyQuests: () => api.get('/student/gamification/daily-quests'),
  completeQuest: (questId: string) =>
    api.post('/student/gamification/complete-quest', { quest_id: questId }),
  updatePet: (data: { name?: string; visuals_state?: Record<string, any> }) =>
    api.post('/student/gamification/pet', data),
  createTeam: (data: { name: string; tag: string; description?: string }) =>
    api.post('/student/gamification/team', data),
  joinTeam: (teamId: string) =>
    api.post('/student/gamification/team/join', { team_id: teamId }),
  leaveTeam: () => api.post('/student/gamification/team/leave'),
};

export const teacherApi = {
  classroom: () => api.get('/teacher/classroom'),
  studentDetail: (id: string) => api.get(`/teacher/student/${id}`),
  suggestions: () => api.get('/teacher/suggestions'),
  createTask: (data: any) => api.post('/teacher/tasks', data),
  listTasks: (topic?: string) => api.get('/teacher/tasks', { params: { topic } }),
  alerts: () => api.get('/teacher/alerts'),
  resolveAlert: (id: string) => api.post(`/teacher/alerts/${id}/resolve`),
  aiClassroomAnalysis: () => api.get('/teacher/ai/classroom-analysis'),
  aiStudentAnalysis: (id: string) => api.get(`/teacher/ai/student-analysis/${id}`),
  aiDifficultySuggestions: () => api.get('/teacher/ai/difficulty-suggestions'),
  aiInterventionPlan: () => api.get('/teacher/ai/intervention-plan'),
  adjustDifficulty: (data: { student_id: string; new_difficulty: number }) =>
    api.post('/teacher/ai/adjust-difficulty', data),

  // ── Spec §4 新增端点（作业布置 + 班级掌握）──
  listAssignments: (classId?: string) =>
    api.get('/teacher/assignments', { params: { class_id: classId }, cache: true }),
  createAssignment: (data: { class_id: string; node_ids: string[]; due_at: string }) =>
    api.post('/teacher/assignments', data),
  classMastery: (classId: string) =>
    api.get('/teacher/class-mastery', { params: { class_id: classId }, cache: true }),
};

export const parentApi = {
  children: () => api.get('/parent/children'),
  childSummary: (childId: string) => api.get(`/parent/child/${childId}/summary`),
  consentSettings: (childId: string) => api.get(`/parent/consent-settings/${childId}`),
  updateConsent: (data: { child_id: string; consent_type: string; granted: boolean }) =>
    api.post('/parent/consent', data),
  exportData: (childId: string) =>
    api.get(`/parent/child/${childId}/export`, { responseType: 'blob' as const }),

  // ── Spec §4 新增端点（家长周报）──
  weeklyReport: (params: { student_id: string; week?: string }) =>
    api.get('/parent/weekly-report', { params, cache: true }),

  // ── 每日使用时长上限（持久化到后端，作用于孩子端）──
  dailyLimit: (childId: string) => api.get(`/parent/child/${childId}/daily-limit`),
  setDailyLimit: (childId: string, minutes: number | null) =>
    api.put(`/parent/child/${childId}/daily-limit`, { daily_limit_minutes: minutes }),
};

export const adminApi = {
  pendingTasks: (page?: number, pageSize?: number) =>
    api.get('/admin/pending-tasks', { params: { page, page_size: pageSize } }),
  reviewTask: (data: { task_id: string; approved: boolean; review_notes?: string }) =>
    api.post('/admin/review-task', data),
  feedbackScripts: (category?: string) =>
    api.get('/admin/feedback-scripts', { params: { category } }),
  createFeedbackScript: (data: { category: string; text: string; sub_category?: string; author?: string }) =>
    api.post('/admin/feedback-scripts', data),
  alertRules: () => api.get('/admin/alert-rules'),
  stats: () => api.get('/admin/stats'),
};

// ── Spec §4 新增端点（K12 课标 + 学科枚举）──
export const k12Api = {
  subjects: () => api.get('/k12/subjects', { cache: true }),
  curriculum: (params?: { subject?: string; grade?: string }) =>
    api.get('/k12/curriculum', { params, cache: true }),
};

// ── 新用户引导（Onboarding）：步骤下发 + 完成/跳过落库 ──
export const onboardingApi = {
  // ── 产品导览（无状态奖励查询：后端 complete 只查表返回奖励，不写库）──
  steps: (role: string) => api.get('/onboarding/steps', { params: { role } }),
  complete: (role: string, stepId: string) =>
    api.post('/onboarding/complete', { role, step_id: stepId }),
  skip: (role: string) => api.post('/onboarding/skip', { role }),
  // ── 引导向导的学习档案真实落库（grade → subjects → consent，写 users 表）──
  saveProfile: (payload: {
    grade?: string | null;
    subjects?: string[] | null;
    consent_name?: string | null;
    consent_agreed?: boolean;
  }) => api.put('/onboarding/profile', payload),
};

// ── AI 实时分析层（消费 /api/v1/analytics，无鉴权，依赖内存特征存储）──
// 注意：这些端点由 analytics.py 的内存单例服务提供，需先 /ingest 事件才能产生风险。
export const analyticsApi = {
  /** 批量摄入行为事件（演示：可先用 seedDemoEvents 灌入合成数据） */
  ingest: (events: any[]) => api.post('/analytics/ingest', { events }),
  /** 单事件在线更新，返回该生实时风险 */
  studentEvent: (userId: string, event: any) =>
    api.post(`/analytics/student/${userId}/event`, { event }),
  /** 单生风险快照：ml_risk(0-1) / risk_tier(0-3) / top_factors */
  studentRisk: (userId: string) => api.get(`/analytics/student/${userId}/risk`),
  /** 班级风险：mean_risk / students / distribution(t0-t3) */
  classRisk: (classId: string, userIds?: string[]) =>
    api.get(`/analytics/class/${classId}/risk`, { params: userIds ? { user_ids: userIds } : {} }),
  /** 班级早期预警：threshold 之上且按风险降序的 warnings 列表 */
  earlyWarning: (classId: string, threshold = 0.5, userIds?: string[]) =>
    api.get(`/analytics/class/${classId}/early-warning`, {
      params: userIds ? { threshold, user_ids: userIds } : { threshold },
    }),
};

// ── LAI 学习成瘾化指数（论文核心构念：0-100 健康分 + L1-L4 风险档 + 五维 + 自动干预）──
// 端点位于 /api/v1/student/gamification（需登录），baseURL 已为 /api/v1。
export const laiApi = {
  /** 当前用户（或家长/老师查看某学生）的学习成瘾化指数仪表盘 */
  dashboard: (studentId?: string) =>
    api.get('/student/gamification/lai/dashboard', { params: studentId ? { student_id: studentId } : {}, cache: false }),
  /** 提交五维自评/日志数据，计算一次 LAI 评估 */
  assess: (payload: {
    daily_minutes?: number; session_minutes?: number; night_ratio?: number;
    content_attention_ratio?: number; leaderboard_views?: number;
    planned_stop_failures?: number; intrinsic_motivation_ratio?: number;
    external_reward_dependency?: number; time_perception_bias?: number;
    sleep_impact?: number; social_impact?: number; age_group?: string;
  }) => api.post('/student/gamification/lai/assess', payload),
};

// ── LF-M54 班级宠物园（积分养宠系统的班级聚合与师/班干部操作）──
// 真实「班级电子养宠」：每生一只专属宠物，用行为积分喂养；班级宠物园为聚合视图。
export const classPetApi = {
  /** 班级宠物园视图（学生/老师可见）：排行榜、形态分布、凝聚力、连接质量 */
  garden: (classId: string) =>
    api.get(`/class-pet/${classId}/garden`, { cache: false }),
  /** 当前学生的专属宠物 + 形态阶段 + 是否「饿肚子」 */
  myPet: (classId: string) =>
    api.get(`/class-pet/${classId}/my-pet`, { cache: false }),
  /** 老师给某学生加减分（行为积分 → 喂养其专属宠物） */
  award: (classId: string, data: { student_id: string; points: number; behavior?: string; reason?: string }) =>
    api.post(`/class-pet/${classId}/award`, data),
  /** 老师触发/开关每周「喂养时间」仪式 */
  ritual: (classId: string, enabled: boolean) =>
    api.post(`/class-pet/${classId}/ritual`, { enabled }),
  /** 老师视图：完整班级宠物园 + 逐生宠物明细 */
  teacher: (classId: string) =>
    api.get(`/class-pet/${classId}/teacher`, { cache: false }),
};
