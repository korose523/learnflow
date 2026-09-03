import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { studentApi } from '../services/api';
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
      if (data.is_correct) setCorrectCount(c => c + 1);
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
      <div style={{ textAlign: 'center', padding: 80 }}>
        <div className="pet-breathing" style={{ fontSize: 64 }}>🎓</div>
        <p style={{ color: '#64748b', marginTop: 16 }}>准备你的专属题目...</p>
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div style={{ maxWidth: 520, margin: '0 auto', textAlign: 'center', padding: 80 }}>
        <div style={{ fontSize: 48 }}>⚠️</div>
        <h2 style={{ margin: '16px 0 8px' }}>任务加载失败</h2>
        <p style={{ color: '#64748b', marginBottom: 24 }}>{fetchError || '请稍后重试'}</p>
        <button className="btn btn-primary" onClick={fetchNextTask} style={{ marginRight: 12 }}>重试</button>
        <button className="btn btn-ghost" onClick={() => navigate('/student')}>返回首页</button>
      </div>
    );
  }

  if (phase === 'complete') {
    return (
      <div style={{ maxWidth: 500, margin: '0 auto', textAlign: 'center', padding: 40 }}>
        <div style={{ fontSize: 64 }}>🎉</div>
        <h2 style={{ margin: '16px 0 8px' }}>学习会话完成！</h2>
        <p style={{ color: '#64748b', marginBottom: 24 }}>
          本次完成 {completedCount} 道题，正确 {correctCount} 题
          {completedCount > 0 && `，正确率 ${Math.round(correctCount / completedCount * 100)}%`}
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <button className="btn btn-primary" onClick={fetchNextTask}>继续学习</button>
          <button className="btn btn-ghost" onClick={() => navigate('/student')}>返回首页</button>
        </div>
      </div>
    );
  }

  return (
    <div className={isRelaxationMode ? 'relaxation-mode' : ''} style={{ maxWidth: 700, margin: '0 auto' }}>
      {/* 进度条 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 14, color: '#64748b' }}>已完成 {completedCount} 题</div>
        <div className="progress-bar" style={{ flex: 1, minWidth: 160 }}>
          <div className="progress-bar-fill" style={{ width: `${Math.min(100, completedCount * 10)}%`, background: '#6366f1' }} />
        </div>
        <button
          className="btn btn-ghost"
          style={{ padding: '6px 12px', fontSize: 13, borderRadius: 10 }}
          onClick={() => setIsRelaxationMode(prev => !prev)}
        >
          <Sparkles size={16} />
          {isRelaxationMode ? '退出放松模式' : '开启放松模式'}
        </button>
        <button className="btn btn-ghost" style={{ padding: '6px 12px', fontSize: 13 }} onClick={() => navigate('/student')}>
          退出
        </button>
      </div>

      {/* 题目卡片 */}
      {phase === 'task' && taskData && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <span style={{
              background: '#eef2ff', color: '#6366f1', padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
            }}>
              {taskData.task.topic}
            </span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: '#64748b' }}>
                <Clock size={12} style={{ verticalAlign: 'middle', marginRight: 2 }} />
                约 {taskData.task.time_estimate}秒
              </span>
              <span style={{
                padding: '2px 8px', borderRadius: 6, fontSize: 12, fontWeight: 600,
                background: taskData.task.difficulty >= 7 ? '#fef2f2' : taskData.task.difficulty >= 4 ? '#fefce8' : '#f0fdf4',
                color: taskData.task.difficulty >= 7 ? '#ef4444' : taskData.task.difficulty >= 4 ? '#a16207' : '#22c55e',
              }}>
                {'⭐'.repeat(Math.min(5, Math.ceil(taskData.task.difficulty / 2)))}
              </span>
            </div>
          </div>

          {/* DDA 提示 */}
          <div style={{ fontSize: 13, color: '#6366f1', marginBottom: 16, fontStyle: 'italic' }}>
            💡 {taskData.dda.feedback_text}
          </div>
          {isRelaxationMode && (
            <div style={{ padding: 12, background: '#ecfdf5', borderRadius: 10, marginBottom: 16, fontSize: 13, color: '#166534' }}>
              🌿 放松模式已启用，专注于思考题目而不是速度。慢下来，享受解答过程。
            </div>
          )}

          {/* 题目内容 */}
          <div style={{ fontSize: 18, lineHeight: 1.7, marginBottom: 24, padding: '16px', background: '#f8fafc', borderRadius: 12 }}>
            {taskData.task.content}
          </div>

          {/* BKT 掌握度提示 */}
          {taskData.bkt && (
            <div style={{ padding: 12, background: '#f0fdf4', borderRadius: 10, marginBottom: 16, fontSize: 13, color: '#166534' }}>
              🎯 {taskData.task.topic} 掌握度 {taskData.bkt.mastery_pct}% · 推荐难度 {taskData.bkt.recommended_difficulty}
            </div>
          )}

          {/* 学习方法提示 */}
          {taskData.learning_tip && (
            <div style={{ padding: 14, background: '#eef2ff', borderRadius: 10, marginBottom: 16, borderLeft: '4px solid #6366f1' }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#6366f1', marginBottom: 4 }}>
                {taskData.learning_tip.icon} {taskData.learning_tip.title}
              </div>
              <div style={{ fontSize: 13, color: '#475569', marginBottom: 4 }}>{taskData.learning_tip.short}</div>
              <div style={{ fontSize: 12, color: '#64748b' }}>{taskData.learning_tip.action}</div>
            </div>
          )}

          {/* 风险提醒 */}
          {taskData.risk && taskData.risk.message && (
            <div style={{ padding: 12, background: '#fefce8', borderRadius: 10, marginBottom: 16, fontSize: 13, color: '#a16207' }}>
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
              autoFocus
              style={{
                width: '100%', padding: '14px 16px', borderRadius: 12, border: '2px solid #e2e8f0',
                fontSize: 17, boxSizing: 'border-box',
                outline: 'none',
              }}
              onFocus={e => (e.target.style.borderColor = '#6366f1')}
              onBlur={e => (e.target.style.borderColor = '#e2e8f0')}
            />
          </div>

          <button
            className="btn btn-primary"
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
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>
            {feedback.is_correct ? <CheckCircle2 size={48} color="#22c55e" /> : <XCircle size={48} color="#f59e0b" />}
          </div>

          <h2 style={{ margin: '0 0 8px', fontSize: 20 }}>
            {feedback.is_correct ? '答对了！' : '差一点！'}
          </h2>

          <p style={{ fontSize: 15, color: '#64748b', lineHeight: 1.6, marginBottom: 16 }}>
            {feedback.feedback.feedback_text}
          </p>

          {feedback.feedback.streak_badge && (
            <div style={{
              display: 'inline-block', padding: '6px 16px', background: '#fef3c7',
              borderRadius: 20, fontSize: 14, fontWeight: 600, color: '#a16207', marginBottom: 16,
            }}>
              <Star size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
              {feedback.feedback.streak_badge}
            </div>
          )}

          {/* 下一步预告 */}
          {feedback.feedback.next_preview && (
            <div style={{
              padding: '12px', background: '#eef2ff', borderRadius: 10, fontSize: 14, color: '#6366f1', marginBottom: 16,
            }}>
              {feedback.feedback.next_preview}
            </div>
          )}

          {/* XP 奖励 */}
          {feedback.xp_update && (
            <div style={{
              display: 'inline-block', padding: '6px 16px', background: '#f0fdf4',
              borderRadius: 20, fontSize: 14, fontWeight: 600, color: '#22c55e', marginBottom: 16,
            }}>
              ⚡ {feedback.xp_update.message} (+{feedback.xp_update.xp_earned} XP)
            </div>
          )}

          {/* 学习方法提示 */}
          {(feedback.feedback.learning_method_tip || feedback.learning_method_tip) && (
            <div style={{
              padding: '12px', background: '#fefce8', borderRadius: 10, fontSize: 14, color: '#a16207', marginBottom: 16,
            }}>
              💡 {(feedback.feedback.learning_method_tip || feedback.learning_method_tip)?.title}<br />
              <span style={{ fontSize: 13 }}>{(feedback.feedback.learning_method_tip || feedback.learning_method_tip)?.action}</span>
            </div>
          )}

          {/* 错误恢复选项 */}
          {!feedback.is_correct && feedback.feedback.recovery_options && (
            <div style={{ display: 'grid', gap: 8, marginBottom: 16 }}>
              {feedback.feedback.recovery_options.map(opt => (
                <button
                  key={opt.action}
                  onClick={() => handleRecovery(opt.action)}
                  className="btn"
                  style={{
                    width: '100%', textAlign: 'left', padding: '12px 16px',
                    background: opt.action === 'watch_tutorial' ? '#eef2ff' : opt.action === 'retry' ? '#f0fdf4' : '#fefce8',
                    color: '#1e293b', border: '1px solid #e2e8f0',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {opt.action === 'watch_tutorial' && <Lightbulb size={16} color="#6366f1" />}
                    {opt.action === 'retry' && <RefreshCw size={16} color="#22c55e" />}
                    {opt.action === 'skip' && <SkipForward size={16} color="#a16207" />}
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>{opt.label}</div>
                      <div style={{ fontSize: 12, color: '#64748b' }}>{opt.description}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          <button className="btn btn-primary" onClick={fetchNextTask} style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '0 auto' }}>
            下一题 <ArrowRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
