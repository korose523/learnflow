import React, { useEffect, useState } from 'react';
import { adminApi } from '../services/api';
import { FileText, MessageSquare, BarChart3, Shield, CheckCircle2, XCircle, Plus, AlertTriangle } from 'lucide-react';

interface PendingTask {
  id: string;
  title: string;
  topic: string;
  difficulty: number;
  content: string;
  source: string;
  created_at: string;
}

interface FeedbackScript {
  id: string;
  category: string;
  sub_category: string | null;
  text: string;
  author: string;
  review_status: string;
  version: number;
}

export default function AdminPanel() {
  const [stats, setStats] = useState<any>(null);
  const [scripts, setScripts] = useState<FeedbackScript[]>([]);
  const [pendingTasks, setPendingTasks] = useState<PendingTask[]>([]);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [tab, setTab] = useState<'overview' | 'content' | 'scripts' | 'rules'>('overview');
  const [newScript, setNewScript] = useState({ category: 'correct', text: '', sub_category: '' });
  const [scriptMessage, setScriptMessage] = useState('');
  const [reviewMessage, setReviewMessage] = useState('');
  const [rules, setRules] = useState<any[]>([]);
  const [rulesLoading, setRulesLoading] = useState(false);
  const [rulesError, setRulesError] = useState('');
  const [pendingError, setPendingError] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadOverview = async () => {
    setLoading(true);
    setError('');
    try {
      const [statsRes, scriptsRes] = await Promise.all([adminApi.stats(), adminApi.feedbackScripts()]);
      setStats(statsRes.data);
      setScripts(scriptsRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载管理面板失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
    loadPendingTasks();
    loadRules();
  }, []);

  const loadRules = async () => {
    setRulesLoading(true);
    setRulesError('');
    try {
      const { data } = await adminApi.alertRules();
      setRules(data.rules || []);
    } catch (err: any) {
      setRulesError(err.response?.data?.detail || '风险规则加载失败');
    } finally {
      setRulesLoading(false);
    }
  };

  const loadPendingTasks = async () => {
    setPendingError('');
    try {
      const { data } = await adminApi.pendingTasks();
      setPendingTasks(data.tasks || []);
      setPendingTotal(data.total || 0);
    } catch (err: any) {
      setPendingError(err.response?.data?.detail || '待审核题目加载失败');
    }
  };

  const handleReview = async (taskId: string, approved: boolean) => {
    try {
      await adminApi.reviewTask({ task_id: taskId, approved });
      setReviewMessage(approved ? '题目已通过审核' : '题目已拒绝');
      loadPendingTasks();
      setTimeout(() => setReviewMessage(''), 2000);
    } catch (err) {
      setReviewMessage('审核操作失败');
    }
  };

  const handleCreateScript = async (e: React.FormEvent) => {
    e.preventDefault();
    setScriptMessage('');
    try {
      await adminApi.createFeedbackScript(newScript);
      setScriptMessage('文案已创建，等待审核');
      setNewScript({ category: 'correct', text: '', sub_category: '' });
      const { data } = await adminApi.feedbackScripts();
      setScripts(data);
    } catch (err) {
      setScriptMessage('创建失败');
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}>加载中...</div>;
  if (error) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>管理面板加载失败</div>
      <div style={{ color: '#64748b', marginBottom: 20 }}>{error}</div>
      <button className="lf-btn lf-btn-primary" onClick={loadOverview}>重试</button>
    </div>
  );

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 20 }}>🛡️ 管理面板</h1>

      {/* Tab 切换 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {[
          { key: 'overview', label: '系统概览', icon: BarChart3 },
          { key: 'content', label: '内容审核', icon: FileText },
          { key: 'scripts', label: '文案管理', icon: MessageSquare },
          { key: 'rules', label: '风险规则', icon: Shield },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key as any)}
            className="lf-btn"
            style={{
              background: tab === key ? '#2C6E8F' : '#f1f5f9',
              color: tab === key ? 'white' : '#64748b',
              display: 'flex', alignItems: 'center', gap: 6, fontSize: 14,
            }}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          <div className="lf-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 42, fontWeight: 700, color: '#2C6E8F' }}>{stats?.total_users || 0}</div>
            <div style={{ color: '#64748b', fontSize: 14 }}>总用户数</div>
          </div>
          <div className="lf-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 42, fontWeight: 700, color: '#22c55e' }}>{stats?.total_tasks || 0}</div>
            <div style={{ color: '#64748b', fontSize: 14 }}>总题目数</div>
          </div>
          <div className="lf-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 42, fontWeight: 700, color: '#f59e0b' }}>{stats?.total_attempts || 0}</div>
            <div style={{ color: '#64748b', fontSize: 14 }}>总答题数</div>
          </div>
        </div>
      )}

      {tab === 'content' && (
        <div className="lf-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600 }}>📝 待审核题目</h2>
            <span style={{ fontSize: 13, color: '#64748b' }}>共 {pendingTotal} 条</span>
          </div>
          {reviewMessage && (
            <div style={{ padding: 10, background: reviewMessage.includes('失败') ? '#fef2f2' : '#f0fdf4', color: reviewMessage.includes('失败') ? '#ef4444' : '#22c55e', borderRadius: 8, marginBottom: 12, fontSize: 14 }}>
              {reviewMessage}
            </div>
          )}
          {pendingError && (
            <div style={{ padding: 12, background: '#fef2f2', color: '#ef4444', borderRadius: 10, marginBottom: 12 }}>{pendingError}</div>
          )}
          {pendingTasks.length === 0 ? (
            <div style={{ padding: 40, background: '#f8fafc', borderRadius: 10, textAlign: 'center', color: '#64748b' }}>
              暂无待审核题目
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {pendingTasks.map((task) => (
                <div key={task.id} style={{ padding: 16, border: '1px solid #e2e8f0', borderRadius: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 8 }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>{task.title || '未命名题目'}</div>
                      <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{task.topic} · 难度 {task.difficulty} · {task.source}</div>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="lf-btn" style={{ background: '#f0fdf4', color: '#22c55e', padding: '6px 12px', fontSize: 13 }} onClick={() => handleReview(task.id, true)}>
                        <CheckCircle2 size={14} /> 通过
                      </button>
                      <button className="lf-btn" style={{ background: '#fef2f2', color: '#ef4444', padding: '6px 12px', fontSize: 13 }} onClick={() => handleReview(task.id, false)}>
                        <XCircle size={14} /> 拒绝
                      </button>
                    </div>
                  </div>
                  <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.5, background: '#f8fafc', padding: 10, borderRadius: 8 }}>
                    {task.content}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'scripts' && (
        <div className="lf-card">
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>💬 微反馈文案库</h2>
          <form onSubmit={handleCreateScript} style={{ display: 'grid', gap: 10, marginBottom: 20, padding: 16, background: '#f8fafc', borderRadius: 10 }}>
            <div style={{ fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Plus size={16} /> 新建文案
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <select className="input" value={newScript.category} onChange={(e) => setNewScript({ ...newScript, category: e.target.value })} style={{ padding: 8, borderRadius: 8, border: '1px solid #e2e8f0' }}>
                <option value="correct">答对</option>
                <option value="incorrect">答错</option>
                <option value="encouragement">鼓励</option>
                <option value="flow">心流</option>
                <option value="rest">休息</option>
                <option value="identity">身份</option>
              </select>
              <input placeholder="子分类（可选）" value={newScript.sub_category} onChange={(e) => setNewScript({ ...newScript, sub_category: e.target.value })} style={{ padding: 8, borderRadius: 8, border: '1px solid #e2e8f0' }} />
            </div>
            <textarea placeholder="文案内容" rows={2} value={newScript.text} onChange={(e) => setNewScript({ ...newScript, text: e.target.value })} required style={{ padding: 8, borderRadius: 8, border: '1px solid #e2e8f0' }} />
            <button type="submit" className="lf-btn lf-btn-primary" style={{ padding: '8px 16px' }}>创建</button>
            {scriptMessage && <p style={{ fontSize: 13, color: scriptMessage.includes('失败') ? '#ef4444' : '#22c55e' }}>{scriptMessage}</p>}
          </form>

          <p style={{ color: '#64748b', fontSize: 14, marginBottom: 16 }}>
            所有暗示/引导文案在此管理。每条文案需经心理专家审核。版本历史可追溯。
          </p>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e2e8f0', textAlign: 'left' }}>
                <th style={{ padding: '8px', fontSize: 12, color: '#64748b' }}>类别</th>
                <th style={{ padding: '8px', fontSize: 12, color: '#64748b' }}>文案</th>
                <th style={{ padding: '8px', fontSize: 12, color: '#64748b' }}>状态</th>
                <th style={{ padding: '8px', fontSize: 12, color: '#64748b' }}>版本</th>
              </tr>
            </thead>
            <tbody>
              {scripts.map((s) => (
                <tr key={s.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '8px' }}>
                    <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, background: 'var(--lf-sem-hint-soft)', color: '#2C6E8F', fontWeight: 600 }}>
                      {s.category}
                    </span>
                  </td>
                  <td style={{ padding: '8px', fontSize: 13, maxWidth: 400 }}>{s.text}</td>
                  <td style={{ padding: '8px' }}>
                    <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, background: s.review_status === 'approved' ? '#f0fdf4' : '#fefce8', color: s.review_status === 'approved' ? '#22c55e' : '#f59e0b' }}>
                      {s.review_status === 'approved' ? '已审核' : s.review_status}
                    </span>
                  </td>
                  <td style={{ padding: '8px', fontSize: 12, color: '#64748b' }}>v{s.version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'rules' && (
        <div className="lf-card">
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>🛡️ 风险告警规则</h2>
          {rulesLoading ? (
            <div className="empty-state">加载中...</div>
          ) : rulesError ? (
            <div className="empty-state" style={{ color: '#ef4444' }}>{rulesError}</div>
          ) : rules.length === 0 ? (
            <div className="empty-state">暂无风险告警规则</div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {rules.map((rule, i) => (
                <div key={i} style={{ padding: '14px 16px', borderRadius: 10, border: '1px solid #e2e8f0', borderLeft: `4px solid ${rule.severity === 'red' ? '#ef4444' : '#f59e0b'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>{rule.name}</div>
                      <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{rule.description}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <code style={{ fontSize: 11, background: '#f1f5f9', padding: '2px 6px', borderRadius: 4 }}>{rule.trigger}</code>
                      <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>{rule.action}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
