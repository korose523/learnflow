import React, { useEffect, useState } from 'react';
import { parentApi } from '../services/api';
import { ShieldCheck, Download, AlertTriangle, CheckCircle2, XCircle, Users } from 'lucide-react';
import { useToast } from '../contexts/ToastContext';

interface ChildSummary {
  child: { id: string; name: string; grade: string };
  weekly: { total_attempts: number; correct_attempts: number; accuracy: number };
  skills: Array<{ skill: string; score: number; mastery: number }>;
  pet: { name: string; level: number; mood: string; total_score: number } | null;
  alerts: Array<{ type: string; severity: string; title: string }>;
  risk_level: string;
}

interface ConsentSetting {
  type: string;
  granted: boolean;
}

const CONSENT_LABELS: Record<string, string> = {
  relaxation_guide: '放松引导',
  eeg_integration: '脑电集成',
  data_research: '数据研究',
  parent_binding: '家长绑定',
};

export default function ParentSummary() {
  const [data, setData] = useState<ChildSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [childId, setChildId] = useState<string>('');
  const [showConsent, setShowConsent] = useState(false);
  const [consents, setConsents] = useState<Record<string, boolean>>({});
  const [consentLoading, setConsentLoading] = useState(false);
  const [consentMessage, setConsentMessage] = useState('');
  const [exporting, setExporting] = useState(false);
  const { showToast } = useToast();

  useEffect(() => {
    const stored = localStorage.getItem('parent_child_id');
    if (stored) {
      setChildId(stored);
      loadChildSummary(stored);
    } else {
      setLoading(false);
      setError('请先选择或绑定孩子账号');
    }
  }, []);

  const loadChildSummary = async (id: string) => {
    setLoading(true);
    setError('');
    try {
      const { data } = await parentApi.childSummary(id);
      setData(data);
      localStorage.setItem('parent_child_id', id);
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载孩子数据失败');
    } finally {
      setLoading(false);
    }
  };

  const loadConsents = async () => {
    if (!data?.child?.id) return;
    setConsentLoading(true);
    setConsentMessage('');
    try {
      const { data: consentData } = await parentApi.consentSettings(data.child.id);
      setConsents(consentData.consents || {});
    } catch (err: any) {
      setConsentMessage(err.response?.data?.detail || '加载同意设置失败');
    } finally {
      setConsentLoading(false);
    }
  };

  const toggleConsent = async (type: string) => {
    if (!data?.child?.id) return;
    const newValue = !consents[type];
    setConsentLoading(true);
    try {
      await parentApi.updateConsent({ child_id: data.child.id, consent_type: type, granted: newValue });
      setConsents(prev => ({ ...prev, [type]: newValue }));
      setConsentMessage(`${CONSENT_LABELS[type] || type} 已${newValue ? '开启' : '关闭'}`);
      setTimeout(() => setConsentMessage(''), 2000);
    } catch (err: any) {
      setConsentMessage(err.response?.data?.detail || '更新失败');
    } finally {
      setConsentLoading(false);
    }
  };

  const openConsent = () => {
    setShowConsent(true);
    loadConsents();
  };

  const handleClearChild = () => {
    localStorage.removeItem('parent_child_id');
    setChildId('');
    setData(null);
    setError('请先选择或绑定孩子账号');
  };

  const handleExport = async () => {
    if (!data?.child?.id) return;
    setExporting(true);
    try {
      const response = await parentApi.exportData(data.child.id);
      const contentType = (response.headers['content-type'] as string | undefined) || 'application/octet-stream';
      const contentDisposition = (response.headers['content-disposition'] as string | undefined) || '';
      const blob = new Blob([response.data], { type: contentType });
      const fileNameMatch = contentDisposition.match(/filename\*?=(?:UTF-8'')?"?([^";\n]+)/i);
      const fileName = fileNameMatch?.[1] ? decodeURIComponent(fileNameMatch[1]) : `learnflow_export_${data.child.id}.json`;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      showToast('导出已生成，下载已开始', 'success');
    } catch (err: any) {
      const message = err.response?.data?.detail || '导出失败，请稍后重试';
      showToast(message, 'error');
    } finally {
      setExporting(false);
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}>加载中...</div>;

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>👨‍👧 孩子学习摘要</h1>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input
            className="input"
            placeholder="输入孩子ID"
            value={childId}
            onChange={(e) => setChildId(e.target.value)}
            style={{ width: 180 }}
          />
          <button className="lf-btn" style={{ background: 'var(--lf-sem-hint-soft)', color: '#2C6E8F' }} onClick={() => childId && loadChildSummary(childId)}>
            查看
          </button>
          {data && (
            <button className="lf-btn" style={{ background: '#fef2f2', color: '#ef4444' }} onClick={handleClearChild}>
              解绑孩子
            </button>
          )}
        </div>
      </div>

      {error && !data && (
        <div className="lf-card" style={{ background: '#fef2f2', color: '#ef4444', marginBottom: 20 }}>
          {error}
          <p style={{ fontSize: 13, color: '#64748b', marginTop: 8 }}>
            演示环境可输入任意学生ID，例如从教师端获取的学生ID。
          </p>
        </div>
      )}

      {data && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
            <div className="lf-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 36, marginBottom: 4 }}>📝</div>
              <div style={{ fontSize: 28, fontWeight: 700 }}>{data.weekly.total_attempts}</div>
              <div style={{ fontSize: 13, color: '#64748b' }}>本周做题数</div>
            </div>
            <div className="lf-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 36, marginBottom: 4 }}>🎯</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#22c55e' }}>{data.weekly.accuracy}%</div>
              <div style={{ fontSize: 13, color: '#64748b' }}>正确率</div>
            </div>
            <div className="lf-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 36, marginBottom: 4 }}>
                {data.risk_level === 'green' ? '🟢' : data.risk_level === 'yellow' ? '🟡' : '🔴'}
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, color: data.risk_level === 'red' ? '#ef4444' : data.risk_level === 'yellow' ? '#f59e0b' : '#22c55e' }}>
                {data.risk_level === 'green' ? '状态良好' : data.risk_level === 'yellow' ? '需要注意' : '需要关注'}
              </div>
              <div style={{ fontSize: 13, color: '#64748b' }}>风险等级</div>
            </div>
          </div>

          <div className="lf-card" style={{ marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>📊 技能掌握情况</h2>
            {data.skills.map((skill) => (
              <div key={skill.skill} style={{ marginBottom: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 14 }}>
                  <span>{skill.skill}</span>
                  <span style={{ fontWeight: 600 }}>{skill.score}分</span>
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${skill.score}%`,
                      background: skill.score >= 80 ? '#22c55e' : skill.score >= 60 ? '#f59e0b' : '#ef4444',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          {data.pet && (
            <div className="lf-card" style={{ marginBottom: 20 }}>
              <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>🐱 学习宠物</h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ fontSize: 48 }}>🐱</div>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 600 }}>{data.pet.name}</div>
                  <div style={{ color: '#64748b', fontSize: 14 }}>等级 {data.pet.level} · 总分 {data.pet.total_score}</div>
                </div>
              </div>
              <p style={{ fontSize: 13, color: '#64748b', marginTop: 12, lineHeight: 1.6 }}>
                💡 宠物的成长反映的是{data.child.name}四个学习维度的进步：理解力、坚持力、创造力和协作力。
                宠物不会饿死，只会随着学习而进化——它是有生命的"学习画像"。
              </p>
            </div>
          )}

          {data.alerts.length > 0 && (
            <div className="lf-card" style={{ marginBottom: 20, background: '#fef2f2' }}>
              <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, color: '#ef4444' }}>⚠️ 风险提醒</h2>
              {data.alerts.map((a, i) => (
                <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid #fecaca', fontSize: 14 }}>
                  <strong>{a.title}</strong> — {a.severity}
                </div>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: 12 }}>
            <button className="lf-btn" style={{ background: 'var(--lf-sem-hint-soft)', color: '#2C6E8F' }} onClick={openConsent}>
              <ShieldCheck size={16} style={{ marginRight: 6 }} />
              管理同意设置
            </button>
            <button className="lf-btn" style={{ background: '#f0fdf4', color: '#22c55e' }} onClick={handleExport} disabled={exporting}>
              <Download size={16} style={{ marginRight: 6 }} />
              {exporting ? '导出中...' : '导出学习数据'}
            </button>
          </div>
        </>
      )}

      {/* 同意设置弹窗 */}
      {showConsent && data && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 200, padding: 20,
        }} onClick={() => setShowConsent(false)}>
          <div className="lf-card" style={{ maxWidth: 480, width: '100%', maxHeight: '80vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700 }}>🛡️ 管理同意设置</h2>
              <button onClick={() => setShowConsent(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}>
                <XCircle size={20} />
              </button>
            </div>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 16 }}>
              管理孩子{data.child.name}的功能授权。所有设置均可在本平台随时关闭。
            </p>
            {consentMessage && (
              <div style={{
                padding: 10, borderRadius: 8, marginBottom: 12, fontSize: 13,
                background: consentMessage.includes('失败') ? '#fef2f2' : '#f0fdf4',
                color: consentMessage.includes('失败') ? '#ef4444' : '#22c55e',
              }}>
                {consentMessage}
              </div>
            )}
            <div style={{ display: 'grid', gap: 12 }}>
              {Object.entries(CONSENT_LABELS).map(([type, label]) => (
                <div key={type} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 12, border: '1px solid #e2e8f0', borderRadius: 10 }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{label}</div>
                    <div style={{ fontSize: 12, color: '#64748b' }}>
                      {consents[type] ? '已授权' : '未授权'}
                    </div>
                  </div>
                  <button
                    className="lf-btn"
                    disabled={consentLoading}
                    onClick={() => toggleConsent(type)}
                    style={{
                      padding: '6px 12px', fontSize: 13,
                      background: consents[type] ? '#fef2f2' : '#f0fdf4',
                      color: consents[type] ? '#ef4444' : '#22c55e',
                    }}
                  >
                    {consents[type] ? '关闭' : '开启'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
