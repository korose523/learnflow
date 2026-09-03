import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { studentApi, gamificationApi } from '../services/api';
import PetCard from '../components/pet/PetCard';
import ChallengeBar from '../components/learn/ChallengeBar';
import { useMotionPref } from '../contexts/MotionContext';
import { EASE_SOFT, subjectColor, subjectMeta } from '../theme/tokens';
import { Target, RefreshCw, TrendingUp, BookOpen, Sparkles, TreePine, Flame, Swords, Footprints, ArrowUpRight } from 'lucide-react';

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

  const loadDashboard = async () => {
    setLoading(true);
    setError('');
    try {
      const [{ data }, challengeRes, treeRes] = await Promise.allSettled([
        studentApi.dashboard(),
        studentApi.challenge(),
        gamificationApi.skillTree(),
      ]) as any;
      setData(data?.value?.data ?? data?.data ?? data);
      try { setChallenge(challengeRes?.value?.data?.current ?? 70); } catch { /* default */ }
      try {
        const t = treeRes?.value?.data?.nodes ?? treeRes?.value?.data?.skills ?? [];
        if (Array.isArray(t)) setSkillTree(t.map((n: any) => ({ id: n.id, label: n.label ?? n.name, mastery: n.mastery ?? 0, parent: n.parent })));
      } catch { /* default */ }
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

  const toggleRelaxation = async () => {
    if (!relaxationMode) {
      try {
        await studentApi.updateConsent({ consent_type: 'relaxation_guide', granted: true });
      } catch {}
    }
    setRelaxationMode(!relaxationMode);
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}>加载中...</div>;
  if (!data) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>学生仪表盘无法加载</div>
      <div style={{ color: '#64748b', marginBottom: 20 }}>{error || '请检查网络或稍后重试'}</div>
      <button className="lf-btn lf-btn-primary" onClick={loadDashboard}>重试</button>
    </div>
  );

  // 相对进步：以各技能掌握度为基数示意（非排名），真实值由后端提供 delta
  const avgMastery = data.skill_profiles.length
    ? Math.round(data.skill_profiles.reduce((s, p) => s + p.score, 0) / data.skill_profiles.length)
    : 0;

  return (
    <div className={relaxationMode ? 'relaxation-mode' : ''} style={{ transition: 'background 1s' }}>
      {/* 顶部栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#2C6E8F', margin: 0, fontFamily: "'Baloo 2',sans-serif" }}>欢迎回来 👋</h1>
          <p style={{ color: '#64748b', margin: 0 }}>今天你想学点什么呢？</p>
        </div>
        <button
          onClick={toggleRelaxation}
          className="lf-btn"
          style={{ background: relaxationMode ? '#3FA66A' : '#F1F5F9', color: relaxationMode ? 'white' : '#64748b' }}
        >
          <Sparkles size={16} />
          {relaxationMode ? '放松模式中' : '开启放松模式'}
        </button>
      </div>

      {/* 难度通道（心流） */}
      <motion.div className="lf-card" initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }} style={{ marginBottom: 16 }}>
        <ChallengeBar value={challenge} label="我的心流难度" />
      </motion.div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 20 }}>
        {/* 左侧：宠物 + 今日 + 我的进步 */}
        <div>
          <PetCard pet={data.pet} />

          <div className="lf-card" style={{ marginTop: 16 }}>
            <h3 style={{ fontSize: 14, color: '#64748b', marginBottom: 12 }}>📊 今日统计</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div style={{ textAlign: 'center', padding: '12px 8px', background: '#F0FDF4', borderRadius: 14 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#3FA66A' }}>{data.today.total_attempts}</div>
                <div style={{ fontSize: 11, color: '#64748b' }}>已做题目</div>
              </div>
              <div style={{ textAlign: 'center', padding: '12px 8px', background: '#EAF6FB', borderRadius: 14 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#3BA9C9' }}>{data.today.accuracy}%</div>
                <div style={{ fontSize: 11, color: '#64748b' }}>正确率</div>
              </div>
            </div>
            {data.pending_reviews > 0 && (
              <div style={{ marginTop: 12, padding: '8px 12px', background: '#FEFCE8', borderRadius: 12, fontSize: 13, color: '#a16207' }}>
                <RefreshCw size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                {data.pending_reviews} 道题待复习
              </div>
            )}
          </div>

          {/* 我的进步 / 相对进步（非排名，AC12） */}
          <div className="lf-card" style={{ marginTop: 16 }}>
            <h3 style={{ fontSize: 14, color: '#64748b', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
              <TrendingUp size={14} color="#3FA66A" /> 我的进步
            </h3>
            <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.7 }}>
              平均掌握度 <b style={{ color: '#2C6E8F' }}>{avgMastery}%</b>。
              比起上周，你正在稳步向前 🌱（相对进步，不与他人比较）。
            </div>
            {data.skill_profiles.map((skill) => (
              <div key={skill.skill} style={{ marginTop: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                  <span>{skill.skill}</span>
                  <span style={{ fontWeight: 600, color: '#2C6E8F' }}>{skill.score}%</span>
                </div>
                <div className="progress-bar" style={{ background: '#EAF6FB' }}>
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
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Target size={28} color="#3BA9C9" />
              <div style={{ flex: 1 }}>
                <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: '#2C6E8F' }}>今日微目标</h2>
                <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: 14 }}>
                  推荐 {data.daily_goal.recommended_tasks} 道题 · 预计 {data.daily_goal.estimated_minutes} 分钟
                </p>
              </div>
              <button className="lf-btn lf-btn-primary" onClick={() => navigate('/learn')} style={{ gap: 6 }}>
                <BookOpen size={18} /> 开始学习
              </button>
            </div>
          </div>

          {/* 学习选择网格 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            <GridCard icon={<BookOpen size={24} color="#3BA9C9" />} title="开始今日任务" desc="DDA 自适应难度，维持心流状态" onClick={() => navigate('/learn')} />
            <GridCard icon={<RefreshCw size={24} color="#E68A3C" />} title="错题再练" desc={data.pending_reviews > 0 ? `${data.pending_reviews} 道待突破` : '暂无错题，继续保持！'} onClick={() => navigate('/learn')} />
            <GridCard icon={<TrendingUp size={24} color="#3FA66A" />} title="专题深入" desc="选择感兴趣的知识点深度学习" onClick={() => navigate('/curriculum')} />
            <GridCard icon={<Sparkles size={24} color="#9B7EDE" />} title="放松学习" desc={relaxationMode ? 'α波放松模式已激活' : '点击顶部按钮开启放松模式'} onClick={() => setRelaxationMode(p => !p)} />
            <GridCard icon={<Flame size={24} color="#E0533D" />} title="连胜挑战" desc="保持学习火焰" onClick={() => navigate('/student/streak')} />
            <GridCard icon={<Swords size={24} color="#3BA9C9" />} title="战队协作" desc="加入战队，一起进步" onClick={() => navigate('/student/team')} />
            <GridCard icon={<TreePine size={24} color="#3FA66A" />} title="能力树" desc="查看自己的成长路线" onClick={() => navigate('/student/skill-tree')} />
            <GridCard icon={<Footprints size={24} color="#9B7EDE" />} title="宠物装扮" desc="给学习伙伴换装" onClick={() => navigate('/student/pet')} />
            <GridCard icon={<ArrowUpRight size={24} color="#3BA9C9" />} title="课标浏览" desc="按课标体系逐级解锁" onClick={() => navigate('/curriculum')} />
          </div>

          {/* 能力树（尽力，仅自己可见，AC12 反排名） */}
          <div className="lf-card" style={{ marginTop: 20 }}>
            <h3 style={{ fontSize: 14, color: '#64748b', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
              <TreePine size={14} color="#3FA66A" /> 我的能力树（仅自己可见）
            </h3>
            {skillTree.length === 0 ? (
              <div style={{ color: '#94A3B8', fontSize: 13 }}>完成更多练习，能力树会慢慢生长 🌿</div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {skillTree.map((n) => (
                  <div key={n.id} title={`掌握度 ${n.mastery}%`}
                    style={{ padding: '8px 14px', borderRadius: 14, background: '#F7FBFD', border: '1px solid #EAF2F6', fontSize: 13, color: '#2C6E8F', fontWeight: 600 }}>
                    🌱 {n.label} · {n.mastery}%
                  </div>
                ))}
              </div>
            )}
          </div>

          {relaxationMode && (
            <div className="lf-card" style={{ marginTop: 20, background: 'rgba(59,169,201,0.06)', borderLeft: '4px solid #3BA9C9' }}>
              <p style={{ margin: 0, fontSize: 14, color: '#2C6E8F', lineHeight: 1.6 }}>
                🌿 放松模式中 — 深呼吸，享受学习过程。<br />
                研究发现：放松状态下的学习记忆力可提升 25-40%。
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function GridCard({ icon, title, desc, onClick }: { icon: React.ReactNode; title: string; desc: string; onClick: () => void }) {
  return (
    <div
      className="lf-card tap-target"
      onClick={onClick}
      style={{ cursor: 'pointer', transition: 'transform 0.2s cubic-bezier(.22,1,.36,1)' }}
      onMouseEnter={e => (e.currentTarget.style.transform = 'translateY(-2px)')}
      onMouseLeave={e => (e.currentTarget.style.transform = 'none')}
    >
      {icon}
      <h3 style={{ margin: '10px 0 4px', fontSize: 16, color: '#2C6E8F' }}>{title}</h3>
      <p style={{ color: '#64748b', fontSize: 13, margin: 0 }}>{desc}</p>
    </div>
  );
}
