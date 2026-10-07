import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { researchApi, ResearchStudyView, ResearchNext } from '../services/api';

const phases = ['pretest', 'practice', 'posttest', 'delayed'] as const;
const labels = { pretest: '前测', practice: '练习', posttest: '即时后测', delayed: '延迟测验' };

export default function ResearchSessionPage() {
  const { studyId } = useParams();
  const [study, setStudy] = useState<ResearchStudyView>();
  const [agreed, setAgreed] = useState(false);
  const [adult, setAdult] = useState(false);
  const [consented, setConsented] = useState(false);
  const [withdrawn, setWithdrawn] = useState(false);
  const [topic, setTopic] = useState('');
  const [phase, setPhase] = useState<(typeof phases)[number]>('pretest');
  const [session, setSession] = useState('');
  const [next, setNext] = useState<ResearchNext>();
  const [answer, setAnswer] = useState('');
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const issuedAt = useRef(0);
  const run = async (action: () => Promise<void>) => {
    setBusy(true); setError('');
    try { await action(); } catch (e: any) { setError(e.response?.data?.detail || '请求失败，请重试。'); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    if (!studyId) return;
    let active = true;
    researchApi.study(studyId).then(({ data }) => {
      if (active) { setStudy(data); setTopic(data.topics[0]); }
    }).catch(() => { if (active) setError('无法读取研究，请检查登录状态及链接。'); });
    return () => { active = false; };
  }, [studyId]);
  const loadNext = async (id: string) => {
    const { data } = await researchApi.next(id);
    setNext(data); setAnswer(''); issuedAt.current = performance.now();
  };
  if (!study) return <main style={{ padding: 32 }}>{error || '正在加载研究说明…'}</main>;
  return <main style={{ maxWidth: 760, margin: '40px auto', padding: 24, color: '#172033', background: '#fff' }}>
    <h1>{study.title}</h1>
    <p>{study.mode === 'dry_run' ? '技术演练：本会话不代表正式人体研究或已获伦理批准。' : '正式研究会话'}</p>
    <p>协议 {study.protocol_version} · 同意书 {study.consent_version}</p>
    {error && <p role="alert" style={{ color: '#a32424' }}>{error}</p>}
    {withdrawn ? <p>已退出研究，记录将从默认研究导出中排除。</p> : !consented ? <section>
      <p style={{ whiteSpace: 'pre-wrap' }}>{study.consent_text}</p>
      <p><label><input type="checkbox" checked={adult} onChange={e => setAdult(e.target.checked)} /> 我确认已满18岁</label></p>
      <p><label><input type="checkbox" checked={agreed} onChange={e => setAgreed(e.target.checked)} /> 我已阅读说明，自愿参加并同意当前版本</label></p>
      <button disabled={busy || !adult || !agreed || study.status !== 'active'} onClick={() => run(async () => {
        await researchApi.consent(study.id, study.consent_version); setConsented(true);
      })}>同意并进入</button>
    </section> : <section>
      <p>请填写数值、分数或单变量等式（例如 x=7）。测验阶段不显示正误反馈。</p>
      {!next || next.complete ? <>
        {next?.complete && <p role="status">本阶段已完成。延迟测验需在后测完成至少 {study.delay_days} 天后进行。</p>}
        <label>主题 <select value={topic} onChange={e => setTopic(e.target.value)}>{study.topics.map(t => <option key={t}>{t}</option>)}</select></label>{' '}
        <label>阶段 <select value={phase} onChange={e => setPhase(e.target.value as typeof phase)}>{phases.map(p => <option key={p} value={p}>{labels[p]}</option>)}</select></label>{' '}
        <button disabled={busy} onClick={() => run(async () => {
          const { data } = await researchApi.start(study.id, topic, phase);
          setSession(data.session_id); setFeedback(''); await loadNext(data.session_id);
        })}>开始或恢复阶段</button>
      </> : <>
        <p>{labels[next.phase]} · 已答 {next.progress} / 最多 {next.total} 题</p>
        <p style={{ fontSize: 20, whiteSpace: 'pre-wrap' }}>{next.task?.content}</p>
        {feedback && <p role="status">{feedback}</p>}
        <form onSubmit={e => { e.preventDefault(); run(async () => {
          if (!next.trial_id) return;
          const { data } = await researchApi.answer(next.trial_id, answer, Math.round(performance.now() - issuedAt.current));
          setFeedback(data.is_correct === null ? '答案已记录。' : data.is_correct ? '上一题回答正确。' : '上一题回答不正确。');
          await loadNext(session);
        }); }}>
          <label>答案 <input value={answer} maxLength={80} autoComplete="off" onChange={e => setAnswer(e.target.value)} /></label>{' '}
          <button disabled={busy || !answer.trim()}>提交首答并继续</button>
        </form>
      </>}
      <hr />
      <button disabled={busy} onClick={() => run(async () => {
        await researchApi.withdraw(study.id); setWithdrawn(true); setNext(undefined);
      })}>撤回参与</button>
    </section>}
  </main>;
}
