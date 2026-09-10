import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { teacherApi } from '../services/api';
import { AlertTriangle, CheckCircle2, TrendingUp, Users, Lightbulb, Plus, Search, X, BookOpen, ShieldAlert } from 'lucide-react';

interface Student {
  id: string;
  name: string;
  grade: string;
  avg_score: number;
  skill_count: number;
  has_alerts: boolean;
}

interface AlertItem {
  id: string;
  student_id: string;
  student_name: string;
  type: string;
  severity: string;
  title: string;
  created_at: string;
}

interface Suggestion {
  type: string;
  student_id: string;
  student_name: string;
  reason: string;
  severity: string;
  suggested_difficulty?: number;
}

export default function TeacherDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<{ total_students: number; class_avg_score: number; students: Student[]; alerts: AlertItem[] } | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedStudent, setSelectedStudent] = useState<any>(null);
  const [studentDetailLoading, setStudentDetailLoading] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [createTaskForm, setCreateTaskForm] = useState({
    title: '', content: '', topic: '', difficulty: 5, correct_answer: '', explanation: '', time_estimate: 120,
  });
  const [createTaskMessage, setCreateTaskMessage] = useState('');
  const [activeTab, setActiveTab] = useState<'overview' | 'students' | 'alerts' | 'ai'>('overview');

  const loadDashboard = async () => {
    setLoading(true);
    setError('');
    try {
      const [classData, sugData] = await Promise.all([teacherApi.classroom(), teacherApi.suggestions()]);
      setData(classData.data);
      setSuggestions(sugData.data.suggestions || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || '加载教师仪表盘失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const openStudentDetail = async (id: string) => {
    setStudentDetailLoading(true);
    setAiLoading(true);
    setSelectedStudent(null);
    try {
      const [detail, analysis] = await Promise.all([
        teacherApi.studentDetail(id),
        teacherApi.aiStudentAnalysis(id).catch(() => ({ data: null })),
      ]);
      setSelectedStudent(detail.data);
      setAiAnalysis(analysis.data);
    } catch (err) {
      console.error('获取学生详情失败', err);
    } finally {
      setStudentDetailLoading(false);
      setAiLoading(false);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateTaskMessage('');
    try {
      await teacherApi.createTask(createTaskForm);
      setCreateTaskMessage('题目已创建，等待管理员审核');
      setCreateTaskForm({ title: '', content: '', topic: '', difficulty: 5, correct_answer: '', explanation: '', time_estimate: 120 });
    } catch (err) {
      setCreateTaskMessage('创建失败，请检查字段');
    }
  };

  const resolveAlert = async (alertId: string) => {
    try {
      await teacherApi.resolveAlert(alertId);
      setData((prev) => prev ? { ...prev, alerts: prev.alerts.filter((a) => a.id !== alertId) } : prev);
    } catch (err) {
      console.error('处理告警失败', err);
    }
  };

  const applyDifficulty = async (studentId: string, newDifficulty: number) => {
    try {
      await teacherApi.adjustDifficulty({ student_id: studentId, new_difficulty: newDifficulty });
      alert(`已将学生难度调整为 ${newDifficulty}`);
    } catch (err) {
      console.error('调整难度失败', err);
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}>加载中...</div>;
  if (!data) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>教师仪表盘无法加载</div>
      <div style={{ color: '#64748b', marginBottom: 20 }}>{error || '请检查网络或稍后重试'}</div>
      <button className="lf-btn lf-btn-primary" onClick={loadDashboard}>重试</button>
    </div>
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>👩‍🏫 班级仪表盘</h1>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="lf-btn lf-btn-primary" onClick={() => setShowCreateTask(true)} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Plus size={18} /> 创建题目
          </button>
          <button className="lf-btn" onClick={() => navigate('/teacher/class-pet')} style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#EAF6FB', color: '#2C6E8F' }}>
            🐾 班级宠物园
          </button>
        </div>
      </div>

      {/* Tab 切换 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {[
          { key: 'overview', label: '概览', icon: TrendingUp },
          { key: 'students', label: '学生', icon: Users },
          { key: 'alerts', label: '告警', icon: ShieldAlert },
          { key: 'ai', label: 'AI 建议', icon: Lightbulb },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key as any)}
            className="lf-btn"
            style={{
              background: activeTab === key ? '#2C6E8F' : '#f1f5f9',
              color: activeTab === key ? 'white' : '#64748b',
              display: 'flex', alignItems: 'center', gap: 6, fontSize: 14,
            }}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 }}>
            <div className="lf-card" style={{ textAlign: 'center' }}>
              <Users size={24} color="#2C6E8F" style={{ marginBottom: 8 }} />
              <div style={{ fontSize: 28, fontWeight: 700 }}>{data.total_students}</div>
              <div style={{ fontSize: 13, color: '#64748b' }}>学生总数</div>
            </div>
            <div className="lf-card" style={{ textAlign: 'center' }}>
              <TrendingUp size={24} color="#22c55e" style={{ marginBottom: 8 }} />
              <div style={{ fontSize: 28, fontWeight: 700, color: '#22c55e' }}>{data.class_avg_score}</div>
              <div style={{ fontSize: 13, color: '#64748b' }}>班级均分</div>
            </div>
            <div className="lf-card" style={{ textAlign: 'center' }}>
              <CheckCircle2 size={24} color="#2C6E8F" style={{ marginBottom: 8 }} />
              <div style={{ fontSize: 28, fontWeight: 700 }}>{suggestions.filter((s) => s.severity === 'green').length}</div>
              <div style={{ fontSize: 13, color: '#64748b' }}>表现优异</div>
            </div>
            <div className="lf-card" style={{ textAlign: 'center' }}>
              <AlertTriangle size={24} color="#ef4444" style={{ marginBottom: 8 }} />
              <div style={{ fontSize: 28, fontWeight: 700, color: '#ef4444' }}>{suggestions.filter((s) => s.severity === 'red').length}</div>
              <div style={{ fontSize: 13, color: '#64748b' }}>需要关注</div>
            </div>
          </div>

          <div className="lf-card" style={{ marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>📋 学生掌握度</h2>
            <StudentTable students={data.students} onSelect={openStudentDetail} />
          </div>
        </>
      )}

      {activeTab === 'students' && (
        <div className="lf-card">
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>📋 学生掌握度</h2>
          <StudentTable students={data.students} onSelect={openStudentDetail} />
        </div>
      )}

      {activeTab === 'alerts' && (
        <div className="lf-card">
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>🚨 风险告警</h2>
          {data.alerts.length === 0 ? (
            <p style={{ color: '#64748b' }}>暂无未处理告警</p>
          ) : (
            <div style={{ display: 'grid', gap: 10 }}>
              {data.alerts.map((alert) => (
                <div key={alert.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 14, background: alert.severity === 'red' ? '#fef2f2' : '#fefce8', borderRadius: 10, borderLeft: `4px solid ${alert.severity === 'red' ? '#ef4444' : '#f59e0b'}` }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{alert.student_name} — {alert.title}</div>
                    <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{alert.type} · {new Date(alert.created_at).toLocaleString()}</div>
                  </div>
                  <button className="lf-btn" style={{ background: '#f1f5f9', color: '#64748b' }} onClick={() => resolveAlert(alert.id)}>已处理</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'ai' && (
        <div className="lf-card">
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Lightbulb size={18} color="#f59e0b" /> AI 教学建议
          </h2>
          {suggestions.length === 0 ? (
            <p style={{ color: '#64748b', fontSize: 14 }}>目前所有学生状态良好，暂无特殊建议。</p>
          ) : (
            <div style={{ display: 'grid', gap: 10 }}>
              {suggestions.map((s, i) => (
                <div key={i} style={{ padding: '12px 16px', borderRadius: 10, background: s.severity === 'red' ? '#fef2f2' : s.severity === 'green' ? '#f0fdf4' : '#fefce8', borderLeft: `4px solid ${s.severity === 'red' ? '#ef4444' : s.severity === 'green' ? '#22c55e' : '#f59e0b'}` }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{s.student_name}</div>
                  <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>{s.reason}</div>
                  {s.suggested_difficulty && (
                    <button className="lf-btn" style={{ marginTop: 8, background: 'var(--lf-sem-hint-soft)', color: '#2C6E8F', fontSize: 13 }} onClick={() => applyDifficulty(s.student_id, s.suggested_difficulty!)}>
                      应用建议难度 {s.suggested_difficulty}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 学生详情弹窗 */}
      {selectedStudent && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div className="lf-card" style={{ width: 700, maxHeight: '80vh', overflow: 'auto', position: 'relative' }}>
            <button style={{ position: 'absolute', top: 16, right: 16 }} className="lf-btn lf-btn-ghost" onClick={() => setSelectedStudent(null)}><X size={18} /></button>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{selectedStudent.student.name} 的学习画像</h2>
            <p style={{ color: '#64748b', fontSize: 13, marginBottom: 16 }}>{selectedStudent.student.grade}</p>

            {selectedStudent.pet && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, background: '#f8fafc', borderRadius: 10, marginBottom: 16 }}>
                <span style={{ fontSize: 40 }}>🐱</span>
                <div>
                  <div style={{ fontWeight: 600 }}>{selectedStudent.pet.name} Lv.{selectedStudent.pet.level}</div>
                  <div style={{ fontSize: 12, color: '#64748b' }}>总分 {selectedStudent.pet.total_score} · 心情 {selectedStudent.pet.mood}</div>
                </div>
              </div>
            )}

            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>🎯 技能掌握</h3>
              <div style={{ display: 'grid', gap: 8 }}>
                {selectedStudent.skills.map((skill: any) => (
                  <div key={skill.skill} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ fontSize: 13, width: 100 }}>{skill.skill}</span>
                    <div className="progress-bar" style={{ flex: 1 }}>
                      <div className="progress-bar-fill" style={{ width: `${skill.score}%`, background: skill.score >= 80 ? '#22c55e' : skill.score >= 60 ? '#f59e0b' : '#ef4444' }} />
                    </div>
                    <span style={{ fontSize: 12, width: 50 }}>{skill.score}分</span>
                  </div>
                ))}
              </div>
            </div>

            {aiLoading ? (
              <div style={{ padding: 12, background: '#f8fafc', borderRadius: 10, marginBottom: 16, color: '#64748b' }}>AI 分析加载中...</div>
            ) : aiAnalysis ? (
              <div style={{ padding: 12, background: 'var(--lf-sem-hint-soft)', borderRadius: 10, marginBottom: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>🤖 AI 分析</h3>
                <p style={{ fontSize: 13, color: '#64748b' }}>{aiAnalysis.recommended_action || aiAnalysis.risk_reasons?.join('；') || '暂无分析'}</p>
              </div>
            ) : (
              <div style={{ padding: 12, background: '#f8fafc', borderRadius: 10, marginBottom: 16, color: '#64748b' }}>暂无 AI 分析数据</div>
            )}

            <div>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>📝 最近活动</h3>
              {selectedStudent.recent_activity.slice(0, 5).map((a: any, i: number) => (
                <div key={i} style={{ fontSize: 13, color: '#64748b', padding: '4px 0', borderBottom: '1px solid #f1f5f9' }}>
                  {a.task_topic} · {a.is_correct ? '✅' : '❌'} · 难度{a.difficulty_at_time}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 创建题目弹窗 */}
      {showCreateTask && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div className="lf-card" style={{ width: 500, position: 'relative' }}>
            <button style={{ position: 'absolute', top: 16, right: 16 }} className="lf-btn lf-btn-ghost" onClick={() => setShowCreateTask(false)}><X size={18} /></button>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <BookOpen size={18} /> 创建新题目
            </h2>
            <form onSubmit={handleCreateTask} style={{ display: 'grid', gap: 12 }}>
              <input className="input" placeholder="标题" value={createTaskForm.title} onChange={(e) => setCreateTaskForm({ ...createTaskForm, title: e.target.value })} required />
              <textarea className="input" placeholder="题目内容" rows={3} value={createTaskForm.content} onChange={(e) => setCreateTaskForm({ ...createTaskForm, content: e.target.value })} required />
              <input className="input" placeholder="知识点/主题" value={createTaskForm.topic} onChange={(e) => setCreateTaskForm({ ...createTaskForm, topic: e.target.value })} required />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <input className="input" type="number" min={1} max={10} placeholder="难度 1-10" value={createTaskForm.difficulty} onChange={(e) => setCreateTaskForm({ ...createTaskForm, difficulty: Number(e.target.value) })} required />
                <input className="input" type="number" placeholder="预计耗时（秒）" value={createTaskForm.time_estimate} onChange={(e) => setCreateTaskForm({ ...createTaskForm, time_estimate: Number(e.target.value) })} required />
              </div>
              <input className="input" placeholder="正确答案" value={createTaskForm.correct_answer} onChange={(e) => setCreateTaskForm({ ...createTaskForm, correct_answer: e.target.value })} required />
              <textarea className="input" placeholder="解析（可选）" rows={2} value={createTaskForm.explanation} onChange={(e) => setCreateTaskForm({ ...createTaskForm, explanation: e.target.value })} />
              <button type="submit" className="lf-btn lf-btn-primary">提交审核</button>
              {createTaskMessage && <p style={{ fontSize: 13, color: createTaskMessage.includes('失败') ? '#ef4444' : '#22c55e' }}>{createTaskMessage}</p>}
            </form>
          </div>
        </div>
      )}

      {studentDetailLoading && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div className="lf-card">加载学生详情中...</div>
        </div>
      )}
    </div>
  );
}

function StudentTable({ students, onSelect }: { students: Student[]; onSelect: (id: string) => void }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr style={{ borderBottom: '2px solid #e2e8f0', textAlign: 'left' }}>
          <th style={{ padding: '10px 8px', fontSize: 13, color: '#64748b' }}>学生</th>
          <th style={{ padding: '10px 8px', fontSize: 13, color: '#64748b' }}>年级</th>
          <th style={{ padding: '10px 8px', fontSize: 13, color: '#64748b' }}>均分</th>
          <th style={{ padding: '10px 8px', fontSize: 13, color: '#64748b' }}>掌握度</th>
          <th style={{ padding: '10px 8px', fontSize: 13, color: '#64748b' }}>状态</th>
          <th style={{ padding: '10px 8px', fontSize: 13, color: '#64748b' }}>操作</th>
        </tr>
      </thead>
      <tbody>
        {students.map((s) => (
          <tr key={s.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
            <td style={{ padding: '10px 8px', fontWeight: 500 }}>{s.name}</td>
            <td style={{ padding: '10px 8px', color: '#64748b' }}>{s.grade}</td>
            <td style={{ padding: '10px 8px', fontWeight: 600 }}>{s.avg_score}</td>
            <td style={{ padding: '10px 8px' }}>
              <div className="progress-bar" style={{ width: 120 }}>
                <div className="progress-bar-fill" style={{ width: `${s.avg_score}%`, background: s.avg_score >= 80 ? '#22c55e' : s.avg_score >= 60 ? '#f59e0b' : '#ef4444' }} />
              </div>
            </td>
            <td style={{ padding: '10px 8px' }}>
              {s.has_alerts ? <AlertTriangle size={16} color="#ef4444" /> : <CheckCircle2 size={16} color="#22c55e" />}
            </td>
            <td style={{ padding: '10px 8px' }}>
              <button className="lf-btn" style={{ padding: '6px 12px', fontSize: 12, background: 'var(--lf-sem-hint-soft)', color: '#2C6E8F' }} onClick={() => onSelect(s.id)}>
                <Search size={14} /> 详情
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
