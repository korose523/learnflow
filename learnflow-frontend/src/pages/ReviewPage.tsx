import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { studentApi, invalidateCache } from '../services/api';
import MathContent from '../components/content/MathContent';
import TaskDifficulty from '../components/learn/TaskDifficulty';

interface ReviewItem { id: string; task_id: string; content: string; topic: string; difficulty: number }
export default function ReviewPage() {
  const navigate = useNavigate();
  const [item, setItem] = useState<ReviewItem | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [answer, setAnswer] = useState('');
  const [result, setResult] = useState<any>(null);
  const lock = useRef(false);
  const start = useRef(Date.now());
  const load = async () => {
    setLoading(true); setError(''); setResult(null); setAnswer('');
    try {
      const { data } = await studentApi.dueReviews();
      setItem(data.due_reviews[0] || null); setTotal(data.total_due); start.current = Date.now();
    } catch { setItem(null); setError('复习列表加载失败，请重试。'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const submit = async () => {
    if (!item || !answer.trim() || lock.current) return;
    lock.current = true; setBusy(true); setError('');
    try {
      const { data } = await studentApi.answerReview(item.id, { answer: answer.trim(), time_spent: Math.max(1, Math.floor((Date.now() - start.current) / 1000)) });
      setResult(data); setTotal(count => Math.max(0, count - 1)); invalidateCache('/student');
    } catch (err: any) { setError(err.response?.data?.detail || '提交失败，复习尚未确认完成。请重试。'); }
    finally { lock.current = false; setBusy(false); }
  };
  return <div style={{ maxWidth: 720, margin: '0 auto' }}>
    <h1>到期复习</h1>
    {error && <p role="alert">{error} {loading ? null : <button className="lf-btn" onClick={load}>刷新列表</button>}</p>}
    {loading ? <p>加载复习记录...</p> : error && !item ? <p>尚未取得复习列表。</p> : !item ? <div className="lf-card"><p>当前没有到期复习。</p><button className="lf-btn" onClick={load}>刷新列表</button></div> : <div className="lf-card">
      <p>当前有 {total} 道到期复习 · {item.topic}</p>
      <div style={{ fontSize: 18, padding: '16px 0' }}><MathContent content={item.content} /></div>
      <TaskDifficulty value={item.difficulty} />
      {!result ? <><input className="input" style={{ width: '100%', margin: '16px 0' }} placeholder="输入复习答案..." value={answer} onChange={e => setAnswer(e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} /><button className="lf-btn lf-btn-primary" onClick={submit} disabled={busy || !answer.trim()}>{busy ? '提交中...' : '提交复习答案'}</button></> : <>
        <p role="status">{result.is_correct ? '本次复习回答正确。' : '本次复习回答不正确，请参考反馈。'}</p>
        <p>{result.feedback?.feedback_text}</p>
        {result.review_explanation && <div><strong>题目讲解</strong><p><MathContent content={result.review_explanation} /></p></div>}
        {result.spaced_review && <p>下次复习安排在 {new Date(result.spaced_review.scheduled_date).toLocaleDateString()}。</p>}
        <button className="lf-btn lf-btn-primary" onClick={load}>继续复习</button>
      </>}
    </div>}
    <button className="lf-btn" style={{ marginTop: 16 }} onClick={() => navigate('/student')}>返回学生首页</button>
  </div>;
}
