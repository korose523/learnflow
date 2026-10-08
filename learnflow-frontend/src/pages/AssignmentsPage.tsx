import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { studentApi } from '../services/api';
import MathContent from '../components/content/MathContent';
interface AssignmentItem { id: string; node_id: string; node_title: string; due_at: string | null; available_task_count: number; version_id?: string; version_number?: number; task_count?: number; submitted_count?: number; blocked_task_count?: number; submission_state?: string }
interface AssignmentList { assignments: AssignmentItem[]; total: number; has_more: boolean }
export default function AssignmentsPage() {
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [data, setData] = useState<AssignmentList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    setLoading(true); setError(''); setData(null);
    studentApi.assignments(offset).then(({ data: response }) => {
      if (!alive) return;
      if (!Array.isArray(response.assignments)) throw new Error('invalid assignment response');
      setData(response);
    }).catch(() => { if (alive) setError('作业读取失败，请重试。'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [offset, retry]);
  return <main style={{ maxWidth: 760, margin: '0 auto', padding: 20 }}>
    <Link to="/student">返回学生主页</Link>
    <h1 style={{ fontSize: 28, fontWeight: 700, margin: '16px 0' }}>教师作业</h1>
    <p>以下为当前班级布置的知识点作业。每题首次提交由服务器判分并记录作业归属；按固定版本记录提交进度，全部题目有提交记录后标记为“全部已提交”，不表示全部答对。</p>
    {loading ? <p role="status">正在读取作业…</p> : error ? <div role="alert">{error}<button className="lf-btn" onClick={() => setRetry(v => v + 1)}>重试读取</button></div> : <>
      <p>共 {data?.total ?? 0} 项作业</p>
      {!data?.assignments.length && <p>当前页没有作业；未分班时也不会显示班级作业。</p>}
      {data?.assignments.map(item => <article className="lf-card" key={item.id} style={{ padding: 16, marginBottom: 12 }}>
        <h2>{item.node_title}</h2>
        <p>截止时间：{item.due_at ? new Date(item.due_at).toLocaleString() : '未设置'}</p>
        <p>{item.version_id ? `版本 ${item.version_number} · 已提交 ${item.submitted_count}/${item.task_count} 道` : `历史未版本化作业 · 当前可用题目 ${item.available_task_count} 道`}</p>
        <p>{item.submission_state === 'submitted' ? '全部已提交' : item.submission_state === 'blocked' ? '有题目撤回审核，等待教师处理' : item.version_id ? '尚未全部提交' : '历史作业不推断整份完成'}</p>
        {(item.version_id || item.available_task_count > 0) && <AssignmentTasks key={item.id} id={item.id} onProgress={progress => setData(previous => previous ? { ...previous, assignments: previous.assignments.map(a => a.id === item.id ? { ...a, ...progress } : a) } : previous)} />}
        {item.available_task_count === 0 && <p>该知识点暂没有已审核的练习题。</p>}
      </article>)}
      <div style={{ display: 'flex', gap: 12 }}>
        <button className="lf-btn" disabled={offset === 0} onClick={() => setOffset(v => Math.max(0, v - 50))}>上一页</button>
        <button className="lf-btn" disabled={!data?.has_more} onClick={() => setOffset(v => v + 50)}>下一页</button>
      </div>
    </>}
  </main>;
}

type AssignmentProgress = { version_id: string; version_number: number; task_count: number; submitted_count: number; submission_state: string; blocked_task_count: number };
function selectProgress(data: AssignmentProgress): AssignmentProgress {
  const { version_id, version_number, task_count, submitted_count, submission_state, blocked_task_count } = data;
  return { version_id, version_number, task_count, submitted_count, submission_state, blocked_task_count };
}
function AssignmentTasks({ id, onProgress }: { id: string; onProgress: (progress: AssignmentProgress) => void }) {
  const [open, setOpen] = useState(false);
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<{ tasks: { id: string; content: string; difficulty: number; submitted: boolean }[]; total: number; has_more: boolean; version_id?: string; version_number?: number; blocked_task_count?: number; submission_state?: string } | null>(null);
  useEffect(() => {
    let alive = true;
    if (!open) return;
    setLoading(true); setError(''); setData(null);
    studentApi.assignmentTasks(id, offset).then(({ data: response }) => {
      if (!alive) return;
      if (!Array.isArray(response.tasks)) throw new Error('invalid tasks');
      setData(response);
      if (response.version_id) onProgress(selectProgress(response));
    }).catch(() => { if (alive) setError('作业题目读取失败，请重试。'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [id, open, offset, retry]);
  return <section>
    <button className="lf-btn" aria-expanded={open} onClick={() => setOpen(v => !v)}>{open ? '收起题目' : '查看作业题目'}</button>
    {open && (loading ? <p role="status">正在读取题目…</p> : error ? <div role="alert">{error}<button onClick={() => setRetry(v => v + 1)}>重试题目</button></div> : <>
      <button className="lf-btn" onClick={() => setRetry(v => v + 1)}>刷新题目与版本</button>
      <p>当前可显示 {data?.total ?? 0} 道，每题每版本仅记录一次作业提交。</p>
      {!data?.tasks.length && <p>当前没有已审核可读题目。</p>}
      {data?.tasks.map(task => <div key={task.id} style={{ padding: 12, borderTop: '1px solid #ddd' }}>
        <p>难度等级：{task.difficulty}/10</p><MathContent content={task.content} />
        <AssignmentAnswer key={`${task.id}:${data?.version_id || 'legacy'}`} assignmentId={id} taskId={task.id} submitted={task.submitted} versionId={data?.version_id} onProgress={onProgress} />
      </div>)}
      <button disabled={offset === 0} onClick={() => setOffset(v => Math.max(0, v - 50))}>上一页题目</button>
      <button disabled={!data?.has_more} onClick={() => setOffset(v => v + 50)}>下一页题目</button>
    </>)}
  </section>;
}

function AssignmentAnswer({ assignmentId, taskId, submitted, versionId, onProgress }: { assignmentId: string; taskId: string; submitted: boolean; versionId?: string; onProgress: (progress: AssignmentProgress) => void }) {
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(submitted);
  const [error, setError] = useState('');
  const [result, setResult] = useState<{ is_correct: boolean; correct_answer?: string; explanation?: string; feedback?: { message?: string } } | null>(null);
  async function submit() {
    if (busy || done || !answer.trim()) return;
    setBusy(true); setError('');
    try {
      const { data } = await studentApi.answerAssignment(assignmentId, { task_id: taskId, answer, version_id: versionId });
      setResult(data); setDone(true);
      if (data.version_id) onProgress(selectProgress(data));
    } catch (e: unknown) {
      const response = (e as { response?: { status?: number; data?: { detail?: string } } }).response;
      setError(response?.data?.detail || '提交未确认，请重试；服务器会拦截重复记录。');
      if (response?.status === 409 && response.data?.detail?.includes('已记录')) setDone(true);
    } finally { setBusy(false); }
  }
  return <div>
    {done ? <p role="status">本题作业答案已记录。</p> : <>
      <label>作业答案<input className="input" style={{ display: 'block', width: '100%', margin: '8px 0' }} aria-label="作业答案" value={answer} disabled={busy} onChange={e => setAnswer(e.target.value)} /></label>
      <button className="lf-btn" disabled={busy || !answer.trim()} onClick={submit}>{busy ? '正在提交…' : '提交作业答案'}</button>
    </>}
    {error && <p role="alert">{error}</p>}
    {result && <div><p>{result.is_correct ? '回答正确' : '回答有误'}</p>
      {result.correct_answer && <MathContent content={`参考答案：${result.correct_answer}`} />}
      {result.explanation && <MathContent content={result.explanation} />}
    </div>}
  </div>;
}
