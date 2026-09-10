import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { studentApi } from '../services/api';
import Celebration from '../components/common/Celebration';
import { Skeleton } from '../components/common/Skeleton';
import { useMotionPref } from '../contexts/MotionContext';
import { EASE_SOFT } from '../theme/tokens';
import { ArrowRight, CheckCircle2, XCircle, Lightbulb, RefreshCw, SkipForward, Clock, Star, Sparkles } from 'lucide-react';

type Phase = 'loading' | 'task' | 'feedback' | 'recovery' | 'complete' | 'error';

interface TaskData {
  task: { id: string; content: string; topic: string; difficulty: number; time_estimate: number };
  dda: { direction: string; pet_reaction: string; feedback_text: string; success_rate: number };
  bkt?: { mastery: number; mastery_pct: number; recommended_difficulty: number; level: string };
  learning_tip?: { method: string; title: string; icon: string; short: string; detail: string; action: string };
  risk?: { consecutive_failures: number; should_reduce_difficulty: boolean; should_switch_topic: boolean; message: string };
}

interface FeedbackData {
  is_correct: boolean;
  feedback: {
    type: string;
    feedback_text: string;
    next_preview?: string;
    pet_reaction: string;
    streak_badge?: string;
    recovery_options?: Array<{ action: string; label: string; description: string }>;
    learning_method_tip?: { title: string; short: string; detail: string; action: string };
  };
  pet_update: any;
  xp_update?: { xp_earned: number; total_xp: number; leveled_up: boolean; message: string };
  spaced_review?: { scheduled_date: string; next_interval_days: number; review_number: number };
  risk_alert?: any;
  learning_method_tip?: { title: string; short: string; detail: string; action: string };
}

export default function LearningSession() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>('loading');
  const [taskData, setTaskData] = useState<TaskData | null>(null);
  const [feedback, setFeedback] = useState<FeedbackData | null>(null);
  const [answer, setAnswer] = useState('');
  const [startTime, setStartTime] = useState(Date.now());
  const [completedCount, setCompletedCount] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [isRelaxationMode, setIsRelaxationMode] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [celebrate, setCelebrate] = useState(false);
  const [celebrateComplete, setCelebrateComplete] = useState(false);
  const { reduced } = useMotionPref();
  const recoveryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (recoveryTimerRef.current) {
        clearTimeout(recoveryTimerRef.current);
      }
    };
  }, []);

  const fetchNextTask = useCallback(async () => {
    setPhase('loading');
    setFetchError(null);
    try {
      const { data } = await studentApi.nextTask();
      setTaskData(data);
      setAnswer('');
      setFeedback(null);
      setPhase('task');
      setStartTime(Date.now());
    } catch (err: any) {
      setFetchError('获取下一题失败，请检查网络或稍后重试');
      setPhase('error');
    }
  }, []);

  useEffect(() => {
    fetchNextTask();
  }, [fetchNextTask]);

  useEffect(() => {
    if (phase === 'complete') setCelebrateComplete(true);
  }, [phase]);

  const handleSubmit = async () => {
    if (!taskData || !answer.trim()) return;
    const timeSpent = Math.round((Date.now() - startTime) / 1000);

    try {
      const { data } = await studentApi.submitAnswer({
        task_id: taskData.task.id,
        answer: answer.trim(),
        time_spent: timeSpent,
      });
      setFeedback(data);
      setCompletedCount(c => c + 1);
      if (data.is_correct) {
        setCorrectCount(c => c + 1);
        setCelebrate(true); // 答对即庆祝「掌握」（正向能力反馈，非强迫回流）
      }
      setPhase('feedback');
    } catch (err) {
      console.error('提交失败', err);
    }
  };

  const handleRecovery = async (choice: string) => {
    if (!taskData) return;
    try {
      await studentApi.recoveryChoice({ task_id: taskData.task.id, choice });
      if (choice === 'watch_tutorial' || choice === 'skip') {
        recoveryTimerRef.current = setTimeout(fetchNextTask, 1500);
      }
    } catch (err) {
      console.error('恢复操作失败', err);
    }
  };

  if (phase === 'loading') {
    return (
      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <Skeleton width={120} height={20} rounded="lg" />
          <div style={{ flex: 1 }}>
            <Skeleton height={8} rounded="full" />
          </div>
        </div>
        <div className="lf-card">
          <div className="pet-breathing" style={{ fontSize: 48, textAlign: 'center' }}>🎓</div>
          <p style={{ color: 'var(--lf-neutral-500)', marginTop: 16, textAlign: 'center' }}>准备你的专属题目...</p>
        </div>
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div style={{ maxWidth: 520, margin: '0 auto', textAlign: 'center', padding: 80 }}>
        <div style={{ fontSize: 48 }}>⚠️</div>
        <h2 style={{ margin: '16px 0 8px' }}>任务加载失败</h2>
        <p style={{ color: 'var(--lf-neutral-500)', marginBottom: 24 }}>{fetchError || '请稍后重试'}</p>
        <button className="lf-btn lf-btn-primary" onClick={fetchNextTask} style={{ marginRight: 12 }}>重试</button>
        <button className="lf-btn lf-btn-ghost" onClick={() => navigate('/student')}>返回首页</button>
      </div>
    );
  }

  if (phase === 'complete') {
    return (
      <div style={{ maxWidth: 500, margin: '0 auto', textAlign: 'center', padding: 40 }}>
        <div style={{ fontSize: 64 }}>🎉</div>
        <h2 style={{ margin: '16px 0 8px' }}>学习会话完成！</h2>
        <p style={{ color: 'var(--lf-neutral-500)', marginBottom: 24 }}>
          本次完成 {completedCount} 道题，正确 {correctCount} 题
          {completedCount > 0 && `，正确率 ${Math.round(correctCount / completedCount * 100)}%`}
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button className="lf-btn lf-btn-primary" onClick={fetchNextTask}>继续学习</button>
          <button className="lf-btn lf-btn-ghost" onClick={() => navigate('/student')}>返回首页</button>
        </div>
        <Celebration
          fire={celebrateComplete}
          emoji="🏆"
          message="这一程你走得很稳，给自己鼓个掌吧 👏"
          onDone={() => setCelebrateComplete(false)}
        />
      </div>
    );
  }

  return (
    <div className={isRelaxationMode ? 'relaxation-mode' : ''} style={{ maxWidth: 700, margin: '0 auto' }}>
      {/* 进度条：已完成题数（真实计数，不作假百分比/假倒计时） */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 'var(--lf-text-base)', color: 'var(--lf-neutral-500)' }} aria-live="polite">已完成 {completedCount} 题</div>
        <div className="progress-bar lf-shimmer-fill" style={{ flex: 1, minWidth: 160 }}>
          <motion.div
            className="progress-bar-fill"
            initial={reduced ? false : { width: 0 }}
            animate={{ width: `${Math.min(100, completedCount * 10)}%` }}
            transition={{ duration: 0.5, ease: EASE_SOFT }}
            style={{ background: 'linear-gradient(90deg, var(--lf-primary-low), var(--lf-primary-high))', borderRadius: 4 }}
          />
        </div>
        <button
          className="lf-btn lf-btn-ghost"
          style={{ padding: '6px 12px', fontSize: 13 }}
          onClick={() => setIsRelaxationMode(prev => !prev)}
          aria-pressed={isRelaxationMode}
        >
          <Sparkles size={16} />
          {isRelaxationMode ? '退出放松模式' : '开启放松模式'}
        </button>
        <button className="lf-btn lf-btn-ghost" style={{ padding: '6px 12px', fontSize: 13 }} onClick={() => navigate('/student')}>
          退出
        </button>
      </div>

      {/* 题目卡片 */}
      {phase === 'task' && taskData && (
        <div className="lf-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, gap: 8, flexWrap: 'wrap' }}>
            <span style={{
              background: 'var(--lf-sem-hint-soft, #E6F4F9)', color: 'var(--lf-sem-hint-text, #1F7393)', padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
            }}>
              {taskData.task.topic}
            </span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--lf-neutral-500)' }}>
                <Clock size={12} style={{ verticalAlign: 'middle', marginRight: 2 }} />
                约 {taskData.task.time_estimate}秒
              </span>
              <span style={{
                padding: '2px 8px', borderRadius: 6, fontSize: 12, fontWeight: 600,
                background: taskData.task.difficulty >= 7 ? 'var(--lf-sem-risk-soft, #FCEDEC)' : taskData.task.difficulty >= 4 ? 'var(--lf-warning-soft, #FEF3C7)' : 'var(--lf-sem-success-soft, #E7F6EE)',
                color: taskData.task.difficulty >= 7 ? 'var(--lf-sem-risk-text, #C0392B)' : taskData.task.difficulty >= 4 ? 'var(--lf-warning-text, #B45309)' : 'var(--lf-sem-success-text, #1F8A51)',
              }}>
                {'⭐'.repeat(Math.min(5, Math.ceil(taskData.task.difficulty / 2)))}
              </span>
            </div>
          </div>

          {/* DDA 提示 */}
          <div style={{ fontSize: 13, color: 'var(--lf-sem-hint-text, #1F7393)', marginBottom: 16, fontStyle: 'italic' }}>
            💡 {taskData.dda.feedback_text}
          </div>
          {isRelaxationMode && (
            <div style={{ padding: 12, background: 'var(--lf-sem-success-soft, #E7F6EE)', borderRadius: 10, marginBottom: 16, fontSize: 13, color: 'var(--lf-sem-success-text, #1F8A51)' }}>
              🌿 放松模式已启用，专注于思考题目而不是速度。慢下来，享受解答过程。
            </div>
          )}

          {/* 题目内容 */}
          <div style={{ fontSize: 18, lineHeight: 1.7, marginBottom: 24, padding: '16px', background: 'var(--lf-neutral-50)', borderRadius: 'var(--lf-radius-md)' }}>
            {taskData.task.content}
          </div>

          {/* BKT 掌握度提示 */}
          {taskData.bkt && (
            <div style={{ padding: 12, background: 'var(--lf-sem-success-soft, #E7F6EE)', borderRadius: 10, marginBottom: 16, fontSize: 13, color: 'var(--lf-sem-success-text, #1F8A51)' }}>
              🎯 {taskData.task.topic} 掌握度 {taskData.bkt.mastery_pct}% · 推荐难度 {taskData.bkt.recommended_difficulty}
            </div>
          )}

          {/* 学习方法提示 */}
          {taskData.learning_tip && (
            <div style={{ padding: 14, background: 'var(--lf-sem-hint-soft, #E6F4F9)', borderRadius: 10, marginBottom: 16, borderLeft: '4px solid var(--lf-primary-low)' }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--lf-sem-hint-text, #1F7393)', marginBottom: 4 }}>
                {taskData.learning_tip.icon} {taskData.learning_tip.title}
              </div>
              <div style={{ fontSize: 13, color: 'var(--lf-neutral-600)', marginBottom: 4 }}>{taskData.learning_tip.short}</div>
              <div style={{ fontSize: 12, color: 'var(--lf-neutral-500)' }}>{taskData.learning_tip.action}</div>
            </div>
          )}

          {/* 风险提醒（健康关怀，非胁迫） */}
          {taskData.risk && taskData.risk.message && (
            <div style={{ padding: 12, background: 'var(--lf-warning-soft, #FEF3C7)', borderRadius: 10, marginBottom: 16, fontSize: 13, color: 'var(--lf-warning-text, #B45309)' }}>
              ⚠️ {taskData.risk.message}
            </div>
          )}

          {/* 答案输入 */}
          <div style={{ marginBottom: 16 }}>
            <input
              type="text"
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="输入你的答案..."
              aria-label="输入你的答案"
              autoFocus
              className="input"
              style={{
                width: '100%', padding: '14px 16px', borderRadius: 'var(--lf-radius-md)', border: '2px solid var(--lf-neutral-200)',
                fontSize: 17, boxSizing: 'border-box', outline: 'none',
              }}
            />
          </div>

          <button
            className="lf-btn lf-btn-primary"
            onClick={handleSubmit}
            disabled={!answer.trim()}
            style={{ width: '100%', padding: 14, fontSize: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
          >
            提交答案 <ArrowRight size={18} />
          </button>
        </div>
      )}

      {/* 反馈卡片 */}
      {phase === 'feedback' && feedback && (
        <motion.div
          className="lf-card"
          key={feedback.feedback.feedback_text}
          initial={reduced ? false : { opacity: 0, scale: 0.96 }}
          animate={feedback.is_correct ? { opacity: 1, scale: 1 } : { opacity: 1, scale: 1, x: [0, -6, 6, -4, 4, 0] }}
          transition={{ duration: feedback.is_correct ? 0.35 : 0.4, ease: EASE_SOFT }}
          style={{ textAlign: 'center' }}
        >
          <motion.div
            initial={reduced ? false : { scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 320, damping: 16 }}
            style={{ fontSize: 48, marginBottom: 12 }}
          >
            {feedback.is_correct ? <CheckCircle2 size={48} color="var(--lf-sem-success)" /> : <XCircle size={48} color="var(--lf-warning)" />}
          </motion.div>

          <h2 style={{ margin: '0 0 8px', fontSize: 'var(--lf-text-xl)' }}>
            {feedback.is_correct ? '答对了！' : '差一点！'}
          </h2>

          {/* 反馈文案对屏幕阅读器实时朗读（正向/温和，无羞辱） */}
          <p role="status" aria-live="polite" style={{ fontSize: 15, color: 'var(--lf-neutral-500)', lineHeight: 1.6, marginBottom: 16 }}>
            {feedback.feedback.feedback_text}
          </p>

          {feedback.feedback.streak_badge && (
            <div style={{
              display: 'inline-block', padding: '6px 16px', background: 'var(--lf-warning-soft, #FEF3C7)',
              borderRadius: 20, fontSize: 14, fontWeight: 600, color: 'var(--lf-warning-text, #B45309)', marginBottom: 16,
            }}>
              <Star size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
              {feedback.feedback.streak_badge}
            </div>
          )}

          {/* 下一步预告 */}
          {feedback.feedback.next_preview && (
            <div style={{
              padding: '12px', background: 'var(--lf-sem-hint-soft, #E6F4F9)', borderRadius: 10, fontSize: 14, color: 'var(--lf-sem-hint-text, #1F7393)', marginBottom: 16,
            }}>
              {feedback.feedback.next_preview}
            </div>
          )}

          {/* XP 奖励（庆祝掌握，非损失厌恶） */}
          {feedback.xp_update && (
            <div style={{
              display: 'inline-block', padding: '6px 16px', background: 'var(--lf-sem-success-soft, #E7F6EE)',
              borderRadius: 20, fontSize: 14, fontWeight: 600, color: 'var(--lf-sem-success)', marginBottom: 16,
            }}>
              ⚡ {feedback.xp_update.message} (+{feedback.xp_update.xp_earned} XP)
            </div>
          )}

          {/* 学习方法提示 */}
          {(feedback.feedback.learning_method_tip || feedback.learning_method_tip) && (
            <div style={{
              padding: '12px', background: 'var(--lf-warning-soft, #FEF3C7)', borderRadius: 10, fontSize: 14, color: 'var(--lf-warning-text, #B45309)', marginBottom: 16,
            }}>
              💡 {(feedback.feedback.learning_method_tip || feedback.learning_method_tip)?.title}<br />
              <span style={{ fontSize: 13 }}>{(feedback.feedback.learning_method_tip || feedback.learning_method_tip)?.action}</span>
            </div>
          )}

          {/* 错误恢复选项（温和引导，不羞辱、不强制） */}
          {!feedback.is_correct && feedback.feedback.recovery_options && (
            <div style={{ display: 'grid', gap: 8, marginBottom: 16 }}>
              {feedback.feedback.recovery_options.map(opt => (
                <button
                  key={opt.action}
                  onClick={() => handleRecovery(opt.action)}
                  className="lf-btn"
                  style={{
                    width: '100%', textAlign: 'left', padding: '12px 16px',
                    background: opt.action === 'watch_tutorial' ? 'var(--lf-sem-hint-soft, #E6F4F9)' : opt.action === 'retry' ? 'var(--lf-sem-success-soft, #E7F6EE)' : 'var(--lf-warning-soft, #FEF3C7)',
                    color: 'var(--lf-neutral-700)', border: '1px solid var(--lf-neutral-200)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {opt.action === 'watch_tutorial' && <Lightbulb size={16} color="var(--lf-sem-hint)" />}
                    {opt.action === 'retry' && <RefreshCw size={16} color="var(--lf-sem-success)" />}
                    {opt.action === 'skip' && <SkipForward size={16} color="var(--lf-warning)" />}
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>{opt.label}</div>
                      <div style={{ fontSize: 12, color: 'var(--lf-neutral-500)' }}>{opt.description}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          <button className="lf-btn lf-btn-primary" onClick={fetchNextTask} style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '0 auto' }}>
            下一题 <ArrowRight size={16} />
          </button>

          {/* 答对庆祝：即时正反馈（庆祝掌握，非损失厌恶） */}
          <Celebration
            fire={celebrate}
            emoji="✨"
            message={feedback.is_correct ? '掌握了一项新技能！大脑又长出了连接 🧠' : ''}
            onDone={() => setCelebrate(false)}
          />
        </motion.div>
      )}
    </div>
  );
}
