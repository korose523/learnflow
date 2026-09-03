import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, ArrowLeft, Check, ShieldCheck, GraduationCap } from 'lucide-react';
import { k12Api } from '../services/api';
import { useMotionPref } from '../contexts/MotionContext';
import { EASE_SOFT, subjectColor, subjectMeta } from '../theme/tokens';
import SubjectBadge from '../components/learn/SubjectBadge';

const GRADE_BANDS = [
  { band: '小学', grades: ['G1', 'G2', 'G3', 'G4', 'G5', 'G6'] },
  { band: '初中', grades: ['G7', 'G8', 'G9'] },
  { band: '高中', grades: ['G10', 'G11', 'G12'] },
];

type Step = 'grade' | 'subjects' | 'consent';

export default function OnboardingPage() {
  const navigate = useNavigate();
  const { reduced } = useMotionPref();
  const [step, setStep] = useState<Step>('grade');
  const [grade, setGrade] = useState<string>('');
  const [subjects, setSubjects] = useState<string[]>([]);
  const [subjectOptions, setSubjectOptions] = useState<string[]>(['math', 'chinese', 'english', 'science']);
  const [consentName, setConsentName] = useState('');
  const [consentAgreed, setConsentAgreed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 拉取真实学科枚举（Spec §4 /k12/subjects，auth=any）
    k12Api.subjects()
      .then(({ data }) => {
        const list = data?.subjects as string[] | undefined;
        if (Array.isArray(list) && list.length) setSubjectOptions(list);
      })
      .catch(() => { /* 用默认学科兜底 */ })
      .finally(() => setLoading(false));
  }, []);

  const toggleSubject = (s: string) =>
    setSubjects(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);

  const canNext =
    step === 'grade' ? !!grade :
    step === 'subjects' ? subjects.length > 0 :
    step === 'consent' ? consentAgreed && consentName.trim().length > 0 : false;

  const finish = () => {
    // 引导完成：实际落库由后端 Onboarding 端点负责；此处本地保存选择并进入学习
    try {
      localStorage.setItem('lf_onboarding', JSON.stringify({ grade, subjects, consentName, consentedAt: new Date().toISOString() }));
    } catch { /* ignore */ }
    navigate('/student');
  };

  const StepShell = ({ children }: { children: React.ReactNode }) => (
    <motion.div
      key={step}
      initial={reduced ? false : { opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: EASE_SOFT }}
      style={{ maxWidth: 720, margin: '0 auto' }}
    >
      {children}
    </motion.div>
  );

  return (
    <div className="login-bg" style={{ minHeight: '100vh', padding: '40px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <h1 style={{ fontFamily: "'Baloo 2','Nunito',sans-serif", fontSize: 34, fontWeight: 800, color: '#fff', margin: 0 }}>
          🎒 欢迎来到 LearnFlow
        </h1>
        <p style={{ color: '#94A3B8', marginTop: 6 }}>三步开启你的学习冒险</p>
      </div>

      {/* 步骤指示器 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {(['grade', 'subjects', 'consent'] as Step[]).map((s, i) => (
          <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              width: 28, height: 28, borderRadius: 999, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              background: step === s ? '#3BA9C9' : 'rgba(255,255,255,0.12)', color: step === s ? '#fff' : '#94A3B8', fontWeight: 700, fontSize: 13,
            }}>{i + 1}</span>
            {i < 2 && <span style={{ width: 24, height: 2, background: 'rgba(255,255,255,0.15)' }} />}
          </div>
        ))}
      </div>

      <div className="card-dark" style={{ width: '100%', maxWidth: 720, minHeight: 320 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60, color: '#94A3B8' }}>准备中...</div>
        ) : step === 'grade' && (
          <StepShell>
            <h2 style={{ color: '#F8FAFC', fontSize: 20, fontWeight: 700, marginBottom: 4 }}>你在上几年级？</h2>
            <p style={{ color: '#94A3B8', fontSize: 14, marginTop: 0, marginBottom: 16 }}>选一个最接近的年级，后面可以随时调整。</p>
            {GRADE_BANDS.map(({ band, grades }) => (
              <div key={band} style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 13, color: '#A78BFA', fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <GraduationCap size={14} /> {band}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {grades.map(g => (
                    <button
                      key={g} className="tap-target"
                      onClick={() => setGrade(g)}
                      style={{
                        padding: '10px 18px', borderRadius: 14, border: '1px solid', cursor: 'pointer',
                        background: grade === g ? '#3BA9C9' : 'rgba(255,255,255,0.05)',
                        color: grade === g ? '#fff' : '#CBD5E1', fontWeight: 600, fontSize: 14,
                        borderColor: grade === g ? '#3BA9C9' : 'rgba(255,255,255,0.12)',
                      }}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </StepShell>
        )}

        {step === 'subjects' && (
          <StepShell>
            <h2 style={{ color: '#F8FAFC', fontSize: 20, fontWeight: 700, marginBottom: 4 }}>想先学哪些学科？</h2>
            <p style={{ color: '#94A3B8', fontSize: 14, marginTop: 0, marginBottom: 16 }}>多选没关系，挑你感兴趣的就好。</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
              {subjectOptions.map(s => {
                const selected = subjects.includes(s);
                const c = subjectColor(s);
                return (
                  <button
                    key={s} className="tap-target"
                    onClick={() => toggleSubject(s)}
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: 8, padding: '12px 18px', borderRadius: 16,
                      border: `2px solid ${selected ? c : 'rgba(255,255,255,0.12)'}`, cursor: 'pointer',
                      background: selected ? `${c}22` : 'rgba(255,255,255,0.04)', color: selected ? '#fff' : '#CBD5E1', fontWeight: 600,
                    }}
                  >
                    <span style={{ fontSize: 18 }}>{subjectMeta(s).emoji}</span>
                    {subjectMeta(s).label}
                    {selected && <Check size={16} color={c} />}
                  </button>
                );
              })}
            </div>
            <div style={{ marginTop: 16, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {subjects.map(s => <SubjectBadge key={s} subject={s} />)}
            </div>
          </StepShell>
        )}

        {step === 'consent' && (
          <StepShell>
            <h2 style={{ color: '#F8FAFC', fontSize: 20, fontWeight: 700, marginBottom: 4 }}>家长知情同意</h2>
            <p style={{ color: '#94A3B8', fontSize: 14, marginTop: 0, marginBottom: 16 }}>为保障未成年人安全，需要家长（监护人）确认。</p>

            <div style={{ background: 'rgba(59,169,201,0.08)', border: '1px solid rgba(59,169,201,0.25)', borderRadius: 16, padding: 16, fontSize: 13, color: '#CBD5E1', lineHeight: 1.7 }}>
              <p style={{ margin: '0 0 8px' }}>📜 我已知悉并同意：</p>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                <li>LearnFlow 会按中国课标为孩子提供自适应练习，并记录学习时长与掌握度（非公开排名）。</li>
                <li>平台设有 25 分钟休息提醒与奖励冷却，保护孩子的身心健康。</li>
                <li>孩子的学习数据仅用于个性化辅导，家长可随时查看与导出。</li>
              </ul>
            </div>

            <div style={{ marginTop: 16 }}>
              <label style={{ fontSize: 13, color: '#94A3B8', display: 'block', marginBottom: 6 }}>家长姓名 / 监护人</label>
              <input
                value={consentName}
                onChange={e => setConsentName(e.target.value)}
                placeholder="请输入家长姓名"
                className="input-dark"
                style={{ height: 44, borderRadius: 14 }}
              />
            </div>

            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginTop: 16, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={consentAgreed}
                onChange={e => setConsentAgreed(e.target.checked)}
                style={{ width: 20, height: 20, marginTop: 2, accentColor: '#3BA9C9' }}
              />
              <span style={{ fontSize: 13, color: '#CBD5E1', lineHeight: 1.6 }}>
                <ShieldCheck size={14} color="#3BA9C9" style={{ verticalAlign: 'middle' }} /> 我已阅读并同意上述条款，作为孩子的监护人授权其使用 LearnFlow。
              </span>
            </label>
          </StepShell>
        )}
      </div>

      {/* 导航按钮 */}
      <div style={{ display: 'flex', gap: 12, marginTop: 20, width: '100%', maxWidth: 720 }}>
        {step !== 'grade' && (
          <button className="lf-btn lf-btn-ghost" style={{ background: 'rgba(255,255,255,0.1)', color: '#CBD5E1' }} onClick={() => setStep(step === 'subjects' ? 'grade' : 'subjects')}>
            <ArrowLeft size={16} /> 上一步
          </button>
        )}
        <div style={{ flex: 1 }} />
        {step !== 'consent' ? (
          <button className="lf-btn lf-btn-primary" disabled={!canNext} onClick={() => setStep(step === 'grade' ? 'subjects' : 'consent')}>
            下一步 <ArrowRight size={16} />
          </button>
        ) : (
          <button className="lf-btn lf-btn-primary" disabled={!canNext} onClick={finish}>
            开始学习 <ArrowRight size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
