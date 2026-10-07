import MathContent from '../components/content/MathContent';
import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, CheckCircle2, XCircle, Clock, RefreshCw } from 'lucide-react';
import { studentApi, invalidateCache } from '../services/api';
import { useMotionPref } from '../contexts/MotionContext';
import { EASE_SOFT } from '../theme/tokens';
import TaskDifficulty from '../components/learn/TaskDifficulty';
import RestGuide from '../components/learn/RestGuide';
import DualCodeViz from '../components/learn/DualCodeViz';
import SubjectBadge from '../components/learn/SubjectBadge';

interface TaskData {
  task?: {
    id: string;
    content: string;
    topic?: string;
    subject?: string;
    difficulty?: number;
    time_estimate?: number;
  };
  challenge_band?: { low?: number; high?: number; current?: number };
}

export default function LearnPage() {
  const navigate = useNavigate();
  const { reduced } = useMotionPref();

  const [taskData, setTaskData] = useState<TaskData | null>(null);
  const [phase, setPhase] = useState<'loading' | 'task' | 'feedback' | 'error'>('loading');
  const [answer, setAnswer] = useState('');
  const [feedbackText, setFeedbackText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [lastCorrect, setLastCorrect] = useState<boolean | null>(null);
  const [elapsedMin, setElapsedMin] = useState(0);
  const [restDismissed, setRestDismissed] = useState(false);
  const startRef = useRef(Date.now());

  const fetchNext = () => {
    setPhase('loading');
    setAnswer('');
    setFeedbackText('');
    setLastCorrect(null);
    startRef.current = Date.now();
    setElapsedMin(0);
    studentApi.nextTask()
      .then(({ data }) => { setTaskData(data); setPhase('task'); })
      .catch(() => setPhase('error'));
  };

  useEffect(() => { fetchNext(); }, []);

  // 专注计时（每分钟更新，用于 25 分钟休息提醒 AC9）
  useEffect(() => {
    const t = setInterval(() => {
      setElapsedMin(Math.floor((Date.now() - startRef.current) / 60000));
    }, 30000);
    return () => clearInterval(t);
  }, []);

  const submit = async () => {
    if (!taskData?.task || !answer.trim() || submitting) return;
    setSubmitting(true);
    setFeedbackText('');
    try {
      const { data } = await studentApi.submitAnswer({
        task_id: taskData.task.id, answer: answer.trim(),
        time_spent: Math.max(1, Math.floor((Date.now() - startRef.current) / 1000)),
      });
      invalidateCache('/student');
      setLastCorrect(data.is_correct);
      setFeedbackText(data.feedback?.feedback_text || (data.is_correct ? '答案正确。' : '答案不正确，请再试一次。'));
      setPhase('feedback');
    } catch {
      setFeedbackText('提交失败，答案尚未确认保存。请重试。');
    } finally {
      setSubmitting(false);
    }
  };

  if (phase === 'loading') return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div className="pet-breathing" style={{ fontSize: 64 }}>🎓</div>
      <p style={{ color: '#64748b', marginTop: 16 }}>准备你的专属题目...</p>
    </div>
  );

  if (phase === 'error') return (
    <div style={{ maxWidth: 520, margin: '0 auto', textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 48 }}>⚠️</div>
      <h2 style={{ margin: '16px 0 8px' }}>题目加载失败</h2>
      <button className="lf-btn lf-btn-primary" onClick={fetchNext}>重试</button>
    </div>
  );

  const task = taskData?.task;

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      {/* 顶部：进度 + 休息提醒 */}
      <div style={{ marginBottom: 16 }}>
        <RestGuide minutes={elapsedMin} threshold={25} onDismiss={() => setRestDismissed(true)} key={`${elapsedMin}-${restDismissed}`} />
      </div>

      <motion.div className="lf-card" initial={reduced ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: EASE_SOFT }}>
        {task && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {task.subject && <SubjectBadge subject={task.subject} />}
              {task.topic && <span style={{ fontSize: 12, color: '#94A3B8' }}>{task.topic}</span>}
            </div>
            <span style={{ fontSize: 12, color: '#94A3B8', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <Clock size={12} /> 约 {task.time_estimate ?? 60} 秒
            </span>
          </div>
        )}

        {/* 题目内容 */}
        <div style={{ fontSize: 18, lineHeight: 1.7, padding: '16px', background: '#F7FBFD', borderRadius: 14, marginBottom: 16 }}>
          <MathContent content={task?.content || '（暂无题目内容）'} />
        </div>

        {/* 难度通道 */}
        <div style={{ marginBottom: 16 }}>
          <TaskDifficulty value={task?.difficulty} />
        </div>

        {/* 双编码可视化（按学科） */}
        <div style={{ marginBottom: 16 }}>
          <DualCodeViz subject={task?.subject} />
        </div>

        {/* 作答区 */}
        {phase === 'task' && (
          <>
            <input
              type="text"
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && submit()}
              placeholder="输入你的答案..."
              autoFocus
              className="input"
              style={{ width: '100%', padding: '14px 16px', borderRadius: 14, fontSize: 17, boxSizing: 'border-box', marginBottom: 12 }}
            />
            <button className="lf-btn lf-btn-primary" style={{ width: '100%' }} disabled={!answer.trim() || submitting} onClick={() => submit()}>
              提交答案 <ArrowRight size={18} />
            </button>
            {feedbackText && <p role="alert">{feedbackText}</p>}
          </>
        )}

        {/* 反馈 */}
        {phase === 'feedback' && (
          <div style={{ textAlign: 'center', padding: '8px 0' }}>
            <div style={{ fontSize: 40, marginBottom: 8 }}>
              {lastCorrect ? <CheckCircle2 size={40} color="#3FA66A" /> : <XCircle size={40} color="#E68A3C" />}
            </div>
            <p style={{ color: '#475569', fontSize: 15 }}>{feedbackText}</p>
            <button className="lf-btn lf-btn-primary" style={{ marginTop: 12 }} onClick={fetchNext}>
              <RefreshCw size={16} /> 下一题
            </button>
          </div>
        )}
      </motion.div>

      <button className="lf-btn lf-btn-ghost" style={{ marginTop: 12 }} onClick={() => navigate('/student')}>
        返回首页
      </button>
    </div>
  );
}
