import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft, PawPrint, Users, Brain, Heart, Lightbulb, Trophy,
  ShieldCheck, ShieldAlert, Gift, Sparkles, RefreshCw, Settings, Star,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useMotionPref } from '../contexts/MotionContext';
import { classPetApi, teacherApi } from '../services/api';
import { EASE_SOFT } from '../theme/tokens';

// 八级形态（与后端 app/services/class_pet_service.py MORPHOLOGY_STAGES 对齐）
const MORPHOLOGY_STAGES = [
  '🥚 孵化中', '😴 闭眼打盹', '🍼 抱奶瓶', '🐾 蹒跚学步',
  '🌟 活泼好动', '🎀 盛装打扮', '👑 神兽觉醒', '✨ 酷炫进化体',
];
const stageLabel = (stage?: number) =>
  MORPHOLOGY_STAGES[Math.max(1, Math.min(8, stage || 1)) - 1] || '🥚 孵化中';

const PET_EMOJIS: Record<string, string> = {
  cat: '🐱', dog: '🐶', rabbit: '🐰', owl: '🦉', dragon: '🐉',
};
const MOOD_LABELS: Record<string, string> = {
  happy: '开心', focused: '专注', tired: '疲惫',
  encouraging: '鼓励中', confident: '自信', curious: '好奇',
};
const BEHAVIORS = [
  { key: 'homework', label: '作业/订正（→坚持力）' },
  { key: 'participation', label: '课堂发言（→理解力）' },
  { key: 'help', label: '助人/小组（→协作力）' },
  { key: 'creativity', label: '创意解法（→创造力）' },
  { key: 'general', label: '综合表现' },
];
const DIMS = [
  { key: 'understanding', label: '理解力', color: '#3BA9C9' },
  { key: 'persistence', label: '坚持力', color: '#E0533D' },
  { key: 'creativity', label: '创造力', color: '#E68A3C' },
  { key: 'collaboration', label: '协作力', color: '#3FA66A' },
];

export default function ClassPetGardenPage() {
  const navigate = useNavigate();
  const auth = useAuth();
  const { reduced: prefersReduced } = useMotionPref();

  const role = auth.user?.role;
  const classId = auth.user?.class_id;
  const isTeacher = role === 'teacher';

  const [garden, setGarden] = useState<any>(null);
  const [myPet, setMyPet] = useState<any>(null);
  const [perStudent, setPerStudent] = useState<any[]>([]);
  const [nameMap, setNameMap] = useState<Record<string, string>>({});
  const [ritualEnabled, setRitualEnabled] = useState<boolean>(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 师端加减分表单
  const [awardStudent, setAwardStudent] = useState('');
  const [awardBehavior, setAwardBehavior] = useState('homework');
  const [awardPoints, setAwardPoints] = useState('10');
  const [awardReason, setAwardReason] = useState('');
  const [awardMsg, setAwardMsg] = useState('');

  const toast = (msg: string) => {
    setAwardMsg(msg);
    window.setTimeout(() => setAwardMsg(''), 2600);
  };

  const load = useCallback(async () => {
    if (!classId) return;
    setLoading(true);
    setError('');
    try {
      if (isTeacher) {
        const [g, t, c] = await Promise.all([
          classPetApi.garden(classId),
          classPetApi.teacher(classId),
          teacherApi.classroom().catch(() => ({ data: { students: [] } })),
        ]);
        setGarden(g.data);
        setPerStudent(t.data.per_student || []);
        setRitualEnabled(!!t.data.ritual_enabled);
        const map: Record<string, string> = {};
        (c.data?.students || []).forEach((s: any) => { map[s.id] = s.name; });
        setNameMap(map);
        if (!awardStudent && (t.data.per_student || []).length) {
          setAwardStudent(t.data.per_student[0].user_id);
        }
      } else {
        const [g, m] = await Promise.all([
          classPetApi.garden(classId),
          classPetApi.myPet(classId),
        ]);
        setGarden(g.data);
        setMyPet(m.data);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || '加载班级宠物园失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [classId, isTeacher, awardStudent]);

  useEffect(() => { load(); }, [load]);

  const toggleRitual = async () => {
    if (!classId) return;
    try {
      await classPetApi.ritual(classId, !ritualEnabled);
      setRitualEnabled(!ritualEnabled);
      toast(!ritualEnabled ? '已开启每周「喂养时间」仪式 🎉' : '已关闭每周仪式');
      load();
    } catch (err: any) {
      toast(err?.response?.data?.detail || '仪式操作失败');
    }
  };

  const submitAward = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!classId || !awardStudent) return;
    const pts = Number(awardPoints);
    if (!pts || pts === 0) { toast('积分不能为 0'); return; }
    try {
      await classPetApi.award(classId, {
        student_id: awardStudent,
        points: pts,
        behavior: awardBehavior,
        reason: awardReason,
      });
      toast(`已为 ${nameMap[awardStudent] || '该生'} ${pts > 0 ? '加' : '扣'} ${Math.abs(pts)} 分 🦴`);
      setAwardReason('');
      load();
    } catch (err: any) {
      toast(err?.response?.data?.detail || '加减分失败');
    }
  };

  if (!classId) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <div style={{ fontSize: 56, marginBottom: 12 }}>🏫</div>
        <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>你还没有加入班级</div>
        <div style={{ color: '#64748b', marginBottom: 20 }}>班级宠物园需要以班级为单位，请联系老师分配班级。</div>
        <button className="lf-btn lf-btn-ghost" onClick={() => navigate(`/${role || 'student'}`)}>
          <ArrowLeft size={16} /> 返回首页
        </button>
      </div>
    );
  }

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}>班级宠物园加载中...</div>;
  if (error) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 12 }}>加载失败</div>
      <div style={{ color: '#64748b', marginBottom: 20 }}>{error}</div>
      <button className="lf-btn lf-btn-primary" onClick={load}>重试</button>
    </div>
  );

  const cohesion = garden?.cohesion ?? 0;
  const connectionQuality = garden?.connection_quality ?? 0;
  const starvingCount = garden?.starving_pets ?? 0;

  return (
    <div>
      {/* 顶部栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button className="tap-target" onClick={() => navigate(`/${role || 'student'}`)}
            style={{ background: '#fff', border: '1px solid #E3EEF3', borderRadius: 12, padding: 8, cursor: 'pointer' }}>
            <ArrowLeft size={18} color="#2C6E8F" />
          </button>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: '#2C6E8F', margin: 0, fontFamily: "'Baloo 2',sans-serif" }}>
              🐾 班级宠物园
            </h1>
            <p style={{ color: '#64748b', margin: 0, fontSize: 13 }}>每生一只专属宠物 · 行为积分喂养 · 班级共养</p>
          </div>
        </div>
        {isTeacher && (
          <button className="lf-btn" onClick={toggleRitual}
            style={{ background: ritualEnabled ? '#3FA66A' : '#F1F5F9', color: ritualEnabled ? '#fff' : '#64748b' }}>
            <Settings size={16} /> {ritualEnabled ? '每周仪式已开启' : '开启每周仪式'}
          </button>
        )}
      </div>

      {/* 健康护栏横幅：对应多邻国「暗黑模式」对照（无付费复活 / 无负罪式提醒 / 排行榜可关） */}
      <motion.div
        className="lf-card"
        initial={prefersReduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: EASE_SOFT }}
        style={{ marginBottom: 16, background: 'rgba(63,166,106,0.08)', borderLeft: '4px solid #3FA66A' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <ShieldCheck size={18} color="#3FA66A" />
          <b style={{ color: '#2C6E8F' }}>健康护栏已开启（对照多邻国经验）</b>
        </div>
        <p style={{ margin: 0, fontSize: 13, color: '#475569', lineHeight: 1.6 }}>
          本系统无「付费复活」、无「负罪式提醒」、排行榜可关闭；以真实班级连接替代虚拟刺激。
          班级连接质量 <b style={{ color: '#3FA66A' }}>{(connectionQuality * 100).toFixed(0)}%</b>
          {starvingCount > 0
            ? `，但有 ${starvingCount} 只宠物濒临饿肚子——请下调扣分力度，避免施压式刷分。`
            : '，状态健康：以正向激励为主。'}
        </p>
      </motion.div>

      {!isTeacher && myPet && <MyPetCard pet={myPet} />}

      {/* 班级宠物园聚合视图 */}
      <motion.div className="lf-card" initial={prefersReduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }} style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: 6, color: '#2C6E8F' }}>
          <PawPrint size={18} color="#3BA9C9" /> 班级宠物园
        </h2>

        {/* 概览指标 */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px,1fr))', gap: 12, marginBottom: 16 }}>
          <Stat icon={<Users size={18} color="#2C6E8F" />} value={garden?.total_pets ?? 0} label="班级宠物数" />
          <Stat icon={<Sparkles size={18} color="#3BA9C9" />} value={garden?.active_pets ?? 0} label="活跃宠物" />
          <Stat icon={<Star size={18} color="#E68A3C" />} value={garden?.average_level ?? 0} label="平均等级" />
          <Stat icon={<Heart size={18} color="#3FA66A" />} value={`${cohesion}`} label="班级凝聚力" />
        </div>

        {/* 形态分布 */}
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 13, color: '#64748b', margin: '0 0 8px' }}>🧬 形态分布</h3>
          <div style={{ display: 'grid', gap: 6 }}>
            {garden?.morphology_distribution && Object.keys(garden.morphology_distribution).length === 0 && (
              <div style={{ color: '#94A3B8', fontSize: 13 }}>还没有宠物被喂养哦～</div>
            )}
            {garden?.morphology_distribution && Object.entries(garden.morphology_distribution).map(([stage, info]: any) => (
              <div key={stage} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 13, width: 110, color: '#475569' }}>{info.label}</span>
                <div className="progress-bar" style={{ flex: 1, background: '#EAF6FB' }}>
                  <div className="progress-bar-fill" style={{ width: `${(info.count / Math.max(1, garden.total_pets)) * 100}%`, background: '#3BA9C9', borderRadius: 999 }} />
                </div>
                <span style={{ fontSize: 12, color: '#64748b', width: 28, textAlign: 'right' }}>{info.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 排行榜（反排名处理：仅展示形态与等级，不渲染羞辱性末位） */}
        <div>
          <h3 style={{ fontSize: 13, color: '#64748b', margin: '0 0 8px', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Trophy size={14} color="#E68A3C" /> 宠物成长榜（前 10）
          </h3>
          <div style={{ display: 'grid', gap: 6 }}>
            {(garden?.leaderboard || []).map((row: any, i: number) => (
              <div key={row.pet_id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: '#F7FBFD', borderRadius: 12 }}>
                <span style={{ fontSize: 16, width: 22, color: '#94A3B8' }}>{i + 1}</span>
                <span style={{ fontSize: 22 }}>{stageLabel(row.morphology_stage).split(' ')[0]}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#2C6E8F' }}>{stageLabel(row.morphology_stage)}</div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>Lv.{row.level} · 总分 {row.total_score}</div>
                </div>
                {row.starving
                  ? <ShieldAlert size={16} color="#E0533D" />
                  : <ShieldCheck size={16} color="#3FA66A" />}
              </div>
            ))}
            {(garden?.leaderboard || []).length === 0 && (
              <div style={{ color: '#94A3B8', fontSize: 13 }}>暂无排名数据。</div>
            )}
          </div>
        </div>
      </motion.div>

      {/* 师端：加减分 + 逐生明细 */}
      {isTeacher && (
        <>
          <motion.div className="lf-card" initial={prefersReduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }} style={{ marginBottom: 16 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 12px', display: 'flex', alignItems: 'center', gap: 6, color: '#2C6E8F' }}>
              <Gift size={18} color="#E68A3C" /> 行为积分加减（喂养 / 饿肚子）
            </h2>
            <form onSubmit={submitAward} style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.4fr 0.8fr 1.2fr auto', gap: 10, alignItems: 'end' }}>
              <Field label="学生">
                <select className="input" value={awardStudent} onChange={(e) => setAwardStudent(e.target.value)} style={selectStyle}>
                  {(perStudent.length ? perStudent : Object.keys(nameMap).map((id) => ({ user_id: id }))).map((s: any) => (
                    <option key={s.user_id} value={s.user_id}>{nameMap[s.user_id] || s.user_id?.slice(0, 8)}</option>
                  ))}
                </select>
              </Field>
              <Field label="行为类型">
                <select className="input" value={awardBehavior} onChange={(e) => setAwardBehavior(e.target.value)} style={selectStyle}>
                  {BEHAVIORS.map((b) => <option key={b.key} value={b.key}>{b.label}</option>)}
                </select>
              </Field>
              <Field label="积分 (+/-)">
                <input className="input" type="number" value={awardPoints} onChange={(e) => setAwardPoints(e.target.value)} style={inputStyle} />
              </Field>
              <Field label="备注（可选）">
                <input className="input" value={awardReason} onChange={(e) => setAwardReason(e.target.value)} placeholder="如：背课文+10口粮" style={inputStyle} />
              </Field>
              <button className="lf-btn lf-btn-primary" type="submit" style={{ height: 44 }}>
                <Gift size={16} /> 发放
              </button>
            </form>
            {awardMsg && <p style={{ marginTop: 10, fontSize: 13, color: awardMsg.includes('失败') ? '#E0533D' : '#3FA66A' }}>{awardMsg}</p>}
          </motion.div>

          <motion.div className="lf-card" initial={prefersReduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 12px', display: 'flex', alignItems: 'center', gap: 6, color: '#2C6E8F' }}>
              <Users size={18} color="#2C6E8F" /> 逐生宠物明细
            </h2>
            <div style={{ display: 'grid', gap: 8 }}>
              {perStudent.map((p: any) => (
                <div key={p.pet_id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', background: '#F7FBFD', borderRadius: 12 }}>
                  <span style={{ fontSize: 24 }}>{stageLabel(p.morphology_stage).split(' ')[0]}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#2C6E8F' }}>{nameMap[p.user_id] || p.user_id?.slice(0, 8)}</div>
                    <div style={{ fontSize: 11, color: '#64748b' }}>{stageLabel(p.morphology_stage)} · Lv.{p.level} · 总分 {p.total_score}</div>
                  </div>
                  {p.starving
                    ? <span style={{ fontSize: 12, color: '#E0533D', background: '#FEE2E2', padding: '4px 10px', borderRadius: 999 }}>濒临饿肚子</span>
                    : <span style={{ fontSize: 12, color: '#3FA66A', background: '#DCFCE7', padding: '4px 10px', borderRadius: 999 }}>健康</span>}
                </div>
              ))}
              {perStudent.length === 0 && <div style={{ color: '#94A3B8', fontSize: 13 }}>本班还没有宠物数据。</div>}
            </div>
          </motion.div>
        </>
      )}
    </div>
  );
}

// ── 子组件 ──────────────────────────────────
function MyPetCard({ pet }: { pet: any }) {
  const emoji = PET_EMOJIS[pet.breed] || '🐱';
  const mood = MOOD_LABELS[pet.mood] || '开心';
  return (
    <motion.div className="lf-card" initial={false} animate={{ opacity: 1 }} style={{ marginBottom: 16, textAlign: 'center' }}>
      <div className="pet-breathing" style={{ fontSize: 56, marginBottom: 4 }}>
        {emoji} {stageLabel(pet.morphology_stage).split(' ')[0]}
      </div>
      <div style={{ fontSize: 18, fontWeight: 700, color: '#2C6E8F' }}>{pet.name}</div>
      <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
        Lv.{pet.level} · {stageLabel(pet.morphology_stage)} · {mood}
      </div>
      {pet.starving && (
        <div style={{ marginTop: 8, display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#E0533D', background: '#FEE2E2', padding: '4px 10px', borderRadius: 999 }}>
          <ShieldAlert size={13} /> 宠物有点饿，多做点任务喂喂它吧～
        </div>
      )}
      <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
        {DIMS.map(({ key, label, color }) => {
          const v = pet.dimensions?.[key] ?? 0;
          return (
            <div key={key} style={{ textAlign: 'left' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#64748b', marginBottom: 3 }}>
                <span>{label}</span><span style={{ fontWeight: 600 }}>{v}</span>
              </div>
              <div className="progress-bar" style={{ height: 6, background: '#EAF6FB', borderRadius: 999 }}>
                <div className="progress-bar-fill" style={{ width: `${v}%`, background: color, borderRadius: 999 }} />
              </div>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}

function Stat({ icon, value, label }: { icon: React.ReactNode; value: any; label: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '12px 8px', background: '#F7FBFD', borderRadius: 14 }}>
      <div style={{ marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#2C6E8F' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#64748b' }}>{label}</div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12, color: '#64748b' }}>
      {label}
      {children}
    </label>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: 10, borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit',
};
const selectStyle: React.CSSProperties = { ...inputStyle, background: '#fff' };
