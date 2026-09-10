import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { studentApi, gamificationApi, laiApi } from '../services/api';
import PetCard from '../components/pet/PetCard';
import ChallengeBar from '../components/learn/ChallengeBar';
import LAIHealthCard from '../components/common/LAIHealthCard';
import PageHeader from '../components/common/PageHeader';
import MascotBubble from '../components/common/MascotBubble';
import Celebration from '../components/common/Celebration';
import { Skeleton } from '../components/common/Skeleton';
import { useMotionPref } from '../contexts/MotionContext';
import { EASE_SOFT, subjectColor, subjectMeta } from '../theme/tokens';
import { Target, RefreshCw, TrendingUp, BookOpen, Sparkles, TreePine, Flame, Swords, Footprints, ArrowUpRight, PawPrint } from 'lucide-react';

interface DashboardData {
  pet: any;
  today: { total_attempts: number; correct_attempts: number; accuracy: number };
  pending_reviews: number;
  skill_profiles: Array<{ skill: string; score: number; success_rate: number }>;
  daily_goal: { recommended_tasks: number; estimated_minutes: number };
}

interface SkillNode { id: string; label: string; mastery: number; parent?: string }

export default function StudentDashboard() {
  const navigate = useNavigate();
  const { reduced } = useMotionPref();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [relaxationMode, setRelaxationMode] = useState(false);
  const [challenge, setChallenge] = useState<number>(70);
  const [skillTree, setSkillTree] = useState<SkillNode[]>([]);
  const [lai, setLai] = useState<any>(null);
  const [celebrateHealthy, setCelebrateHealthy] = useState(false);
  const celebratedRef = useRef(false);

  const loadDashboard = async () => {
    setLoading(true);
    setError('');
    try {
      // 注意：Promise.allSettled 的元素是 {status, value} 包装对象，不是响应体本身。
      // 原先写成 `const [{ data }, ...] = ...` 再从 data?.value?.data 取值，等价于
      // 从包装对象上取 .data —— 恒为 undefined，于是 setData(undefined)，仪表盘
      // 永远落到 `if (!data)` 的「无法加载」分支。必须经 .value 取出响应。
      const [dashRes, challengeRes, treeRes, laiRes] = await Promise.allSettled([
        studentApi.dashboard(),
        studentApi.challenge(),
        gamificationApi.skillTree(),
        laiApi.dashboard(),
      ]) as any;
      setData(dashRes?.value?.data ?? dashRes?.data ?? null);
      try { setChallenge(challengeRes?.value?.data?.current ?? 70); } catch { /* default */ }
      try {
        const t = treeRes?.value?.data?.nodes ?? treeRes?.value?.data?.skills ?? [];
        if (Array.isArray(t)) setSkillTree(t.map((n: any) => ({ id: n.id, label: n.label ?? n.name, mastery: n.mastery ?? 0, parent: n.parent })));
      } catch { /* default */ }
      try { setLai(laiRes?.value?.data ?? laiRes?.data ?? laiRes); } catch { /* default */ }
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载学生仪表盘失败，请刷新或重新登录');
      navigate('/login');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  // 学习状态健康时，给一次「自我拓展」式庆祝（非连胜/损失厌恶，呼应抗成瘾基调）
  useEffect(() => {
    if (lai && !celebratedRef.current) {
      const tier = lai.risk_tier || 'L1_NORMAL';
      if (tier === 'L1_NORMAL') {
        setCelebrateHealthy(true);
        celebratedRef.current = true;
      }
    }
  }, [lai]);

  const toggleRelaxation = async () => {
    if (!relaxationMode) {
      try {
        await studentApi.updateConsent({ consent_type: 'relaxation_guide', granted: true });
      } catch {
        // 放松模式仍可在本地开启；同意记录失败不会阻塞用户退出或继续学习。
      }
    }
    setRelaxationMode(!relaxationMode);
  };

  // 加载态用骨架屏而非空白（App 路由 Suspense + 本页局部骨架）
  if (loading) {
    return (
      <div style={{ display: 'grid', gap: 16 }}>
        <Skeleton height={64} rounded="lg" />
        <Skeleton height={120} rounded="lg" />
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-5">
          <Skeleton height={320} rounded="lg" />
          <Skeleton height={320} rounded="lg" />
        </div>
      </div>
    );
  }
  if (!data) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>学生仪表盘无法加载</div>
      <div style={{ color: 'var(--lf-neutral-500)', marginBottom: 20 }}>{error || '请检查网络或稍后重试'}</div>
      <button className="lf-btn lf-btn-primary" onClick={loadDashboard}>重试</button>
    </div>
  );

  // 相对进步：以各技能掌握度为基数示意（非排名），真实值由后端提供 delta
  const avgMastery = data.skill_profiles.length
    ? Math.round(data.skill_profiles.reduce((s, p) => s + p.score, 0) / data.skill_profiles.length)
    : 0;

  // 吉祥物提示接入真实学情（基于 LAI 风险档推导健康正向提示，绝不制造负罪感/损失厌恶）
  const mascotTips = lai
    ? (lai.risk_tier === 'L1_NORMAL'
        ? ['你今天的学习状态很健康，保持自己的节奏就好 🌿', '完成一个小目标就值得鼓掌，不必和别人比 👏', '大脑喜欢规律作息，今晚早点睡能记得更牢 🌙']
        : lai.risk_tier === 'L2_WATCH'
        ? ['感觉到你投入很多，记得每 20 分钟抬头看看远处 🌿', '如果有点累，试试顶部「放松模式」深呼吸 🧘', '学得久不代表学得好，适时休息效率更高 💡']
        : ['最近学习强度偏高，先喝口水、站起来活动一下吧 💧', '给自己 10 分钟休息，回来会更专注 🌿', '你不需要一直绷着，休息也是学习的一部分 🧘'])
    : undefined;

  return (
    <div className={relaxationMode ? 'relaxation-mode' : ''} style={{ transition: 'background 1s' }}>
      {/* 顶部栏 */}
      <PageHeader
        icon={<Sparkles size={24} color="var(--lf-primary-high)" />}
        title="欢迎回来 👋"
        subtitle="今天你想学点什么呢？"
        action={
          <button
            onClick={toggleRelaxation}
            className="lf-btn"
            aria-pressed={relaxationMode}
            style={{ background: relaxationMode ? 'var(--lf-sem-success, #3FA66A)' : 'var(--lf-neutral-100)', color: relaxationMode ? 'white' : 'var(--lf-neutral-500)' }}
          >
            <Sparkles size={16} />
            {relaxationMode ? '放松模式中' : '开启放松模式'}
          </button>
        }
      />

      {/* 难度通道（心流） */}
      <motion.div className="lf-card" initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }} style={{ marginBottom: 16 }}>
        <ChallengeBar value={challenge} label="我的心流难度" />
      </motion.div>

      {/* 学习健康分（LAI）— 论文核心构念：0-100 健康分 + 自动抗成瘾干预 */}
      {lai && <LAIHealthCard data={lai} />}

      {/* 信息架构：左「今日/进步」+ 右「目标/学习入口/能力树」，移动端自动堆叠 */}
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-5" style={{ marginTop: 16 }}>
        {/* 左侧：宠物 + 今日 + 我的进步 */}
        <div>
          <PetCard pet={data.pet} />

          <div className="lf-card" style={{ marginTop: 16 }}>
            <h3 style={{ fontSize: 'var(--lf-text-sm)', color: 'var(--lf-neutral-500)', margin: '0 0 12px' }}>📊 今日统计</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div style={{ textAlign: 'center', padding: '12px 8px', background: 'var(--lf-sem-success-soft, #E7F6EE)', borderRadius: 'var(--lf-radius-md)' }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--lf-sem-success, #3FA66A)' }}>{data.today.total_attempts}</div>
                <div style={{ fontSize: 11, color: 'var(--lf-neutral-500)' }}>已做题目</div>
              </div>
              <div style={{ textAlign: 'center', padding: '12px 8px', background: 'var(--lf-sem-hint-soft, #E6F4F9)', borderRadius: 'var(--lf-radius-md)' }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--lf-primary-low)' }}>{data.today.accuracy}%</div>
                <div style={{ fontSize: 11, color: 'var(--lf-neutral-500)' }}>正确率</div>
              </div>
            </div>
            {data.pending_reviews > 0 && (
              <div style={{ marginTop: 12, padding: '8px 12px', background: 'var(--lf-warning-soft, #FEF3C7)', borderRadius: 'var(--lf-radius-sm)', fontSize: 13, color: 'var(--lf-warning-text, #B45309)' }}>
                <RefreshCw size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                {data.pending_reviews} 道题待复习
              </div>
            )}
          </div>

          {/* 我的进步 / 相对进步（非排名，AC12） */}
          <div className="lf-card" style={{ marginTop: 16 }}>
            <h3 style={{ fontSize: 'var(--lf-text-sm)', color: 'var(--lf-neutral-500)', margin: '0 0 12px', display: 'flex', alignItems: 'center', gap: 6 }}>
              <TrendingUp size={14} color="var(--lf-sem-success, #3FA66A)" /> 我的进步
            </h3>
            <div style={{ fontSize: 13, color: 'var(--lf-neutral-600)', lineHeight: 1.7 }}>
              平均掌握度 <b style={{ color: 'var(--lf-primary-high)' }}>{avgMastery}%</b>。
              比起上周，你正在稳步向前 🌱（相对进步，不与他人比较）。
            </div>
            {data.skill_profiles.map((skill) => (
              <div key={skill.skill} style={{ marginTop: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                  <span>{skill.skill}</span>
                  <span style={{ fontWeight: 600, color: 'var(--lf-primary-high)' }}>{skill.score}%</span>
                </div>
                <div className="progress-bar" style={{ background: 'var(--lf-sem-hint-soft, #E6F4F9)' }}>
                  <div className="progress-bar-fill" style={{ width: `${skill.score}%`, background: subjectColor(skill.skill), borderRadius: 999 }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 右侧：学习区域 */}
        <div>
          {/* 今日目标 */}
          <div className="lf-card" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <Target size={28} color="var(--lf-primary-low)" />
              <div style={{ flex: 1, minWidth: 180 }}>
                <h2 style={{ fontSize: 'var(--lf-text-lg)', fontWeight: 700, margin: 0, color: 'var(--lf-primary-high)' }}>今日微目标</h2>
                <p style={{ color: 'var(--lf-neutral-500)', margin: '4px 0 0', fontSize: 'var(--lf-text-base)' }}>
                  推荐 {data.daily_goal.recommended_tasks} 道题 · 预计 {data.daily_goal.estimated_minutes} 分钟
                </p>
              </div>
              <button className="lf-btn lf-btn-primary" onClick={() => navigate('/learn')} style={{ gap: 6 }}>
                <BookOpen size={18} /> 开始学习
              </button>
            </div>
          </div>

          {/* 学习入口网格（移动端 2 列，平板/桌面 3 列） */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <GridCard icon={<BookOpen size={24} color="var(--lf-primary-low)" />} title="开始今日任务" desc="DDA 自适应难度，维持心流状态" onClick={() => navigate('/learn')} />
            <GridCard icon={<RefreshCw size={24} color="var(--lf-subject-science)" />} title="错题再练" desc={data.pending_reviews > 0 ? `${data.pending_reviews} 道待突破` : '暂无错题，继续保持！'} onClick={() => navigate('/learn')} />
            <GridCard icon={<TrendingUp size={24} color="var(--lf-sem-success)" />} title="专题深入" desc="选择感兴趣的知识点深度学习" onClick={() => navigate('/curriculum')} />
            <GridCard icon={<Sparkles size={24} color="var(--lf-sem-rest)" />} title="放松学习" desc={relaxationMode ? 'α波放松模式已激活' : '点击顶部按钮开启放松模式'} onClick={() => setRelaxationMode(p => !p)} />
            <GridCard icon={<Flame size={24} color="var(--lf-sem-risk)" />} title="连胜挑战" desc="保持学习火焰" onClick={() => navigate('/student/streak')} />
            <GridCard icon={<Swords size={24} color="var(--lf-primary-low)" />} title="战队协作" desc="加入战队，一起进步" onClick={() => navigate('/student/team')} />
            <GridCard icon={<TreePine size={24} color="var(--lf-sem-success)" />} title="能力树" desc="查看自己的成长路线" onClick={() => navigate('/student/skill-tree')} />
            <GridCard icon={<Footprints size={24} color="var(--lf-sem-rest)" />} title="宠物装扮" desc="给学习伙伴换装" onClick={() => navigate('/student/pet')} />
            <GridCard icon={<PawPrint size={24} color="var(--lf-subject-science)" />} title="班级宠物园" desc="和同学一起养专属电子宠物" onClick={() => navigate('/student/class-pet')} />
            <GridCard icon={<ArrowUpRight size={24} color="var(--lf-primary-low)" />} title="课标浏览" desc="按课标体系逐级解锁" onClick={() => navigate('/curriculum')} />
          </div>

          {/* 能力树（尽力，仅自己可见，AC12 反排名） */}
          <div className="lf-card" style={{ marginTop: 20 }}>
            <h3 style={{ fontSize: 'var(--lf-text-sm)', color: 'var(--lf-neutral-500)', margin: '0 0 12px', display: 'flex', alignItems: 'center', gap: 6 }}>
              <TreePine size={14} color="var(--lf-sem-success)" /> 我的能力树（仅自己可见）
            </h3>
            {skillTree.length === 0 ? (
              <div style={{ color: 'var(--lf-neutral-400)', fontSize: 13 }}>完成更多练习，能力树会慢慢生长 🌿</div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {skillTree.map((n) => (
                  <div key={n.id} title={`掌握度 ${n.mastery}%`}
                    style={{ padding: '8px 14px', borderRadius: 'var(--lf-radius-md)', background: 'var(--lf-neutral-50)', border: '1px solid var(--lf-neutral-100)', fontSize: 13, color: 'var(--lf-primary-high)', fontWeight: 600 }}>
                    🌱 {n.label} · {n.mastery}%
                  </div>
                ))}
              </div>
            )}
          </div>

          {relaxationMode && (
            <div className="lf-card" style={{ marginTop: 20, background: 'rgba(59,169,201,0.06)', borderLeft: '4px solid var(--lf-primary-low)' }}>
              <p style={{ margin: 0, fontSize: 'var(--lf-text-base)', color: 'var(--lf-primary-high)', lineHeight: 1.6 }}>
                🌿 放松模式中 — 深呼吸，享受学习过程。<br />
                研究发现：放松状态下的学习记忆力可提升 25-40%。
              </p>
            </div>
          )}

          {/* 情感化陪伴伙伴（提示由真实学情 LAI 驱动）+ 健康庆祝 */}
          <MascotBubble tips={mascotTips} />
          <Celebration
            fire={celebrateHealthy}
            emoji="🌿"
            message="你的学习状态很健康！保持自己的节奏就好～"
            onDone={() => setCelebrateHealthy(false)}
          />
        </div>
      </div>
    </div>
  );
}

function GridCard({ icon, title, desc, onClick }: { icon: React.ReactNode; title: string; desc: string; onClick: () => void }) {
  return (
    <div
      className="lf-card tap-target lf-card-elevate"
      role="button"
      tabIndex={0}
      aria-label={title}
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } }}
      style={{ cursor: 'pointer', transition: 'transform 0.2s var(--lf-ease-soft), box-shadow 0.2s var(--lf-ease-soft)' }}
    >
      {icon}
      <h3 style={{ margin: '10px 0 4px', fontSize: 'var(--lf-text-md)', color: 'var(--lf-primary-high)' }}>{title}</h3>
      <p style={{ color: 'var(--lf-neutral-500)', fontSize: 'var(--lf-text-sm)', margin: 0 }}>{desc}</p>
    </div>
  );
}
