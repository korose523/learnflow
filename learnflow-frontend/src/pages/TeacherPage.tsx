import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Send, Grid3x3, CheckCircle2 } from 'lucide-react';
import { teacherApi, k12Api } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useMotionPref } from '../contexts/MotionContext';
import { EASE_SOFT, subjectColor, subjectMeta } from '../theme/tokens';

interface ClassInfo { id: string; name: string }
interface NodeInfo { id: string; title: string; subject_id?: string }
interface MasteryNode { id: string; mastery: number; title?: string; subject_id?: string }

function masteryColor(v: number): string {
  if (v >= 80) return '#3FA66A';
  if (v >= 60) return '#9CC773';
  if (v >= 40) return '#E68A3C';
  return '#E0533D';
}

export default function TeacherPage() {
  const { showToast } = useToast();
  const { reduced } = useMotionPref();

  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [nodes, setNodes] = useState<NodeInfo[]>([]);
  const [classId, setClassId] = useState('');
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
  const [dueAt, setDueAt] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [mastery, setMastery] = useState<MasteryNode[]>([]);
  const [masteryLoading, setMasteryLoading] = useState(false);

  // 班级与知识点（尽力）
  useEffect(() => {
    teacherApi.classroom()
      .then(({ data }) => {
        const cs = data?.classes || data?.data?.classes || [];
        if (Array.isArray(cs) && cs.length) setClasses(cs.map((c: any) => ({ id: c.id, name: c.name })));
      })
      .catch(() => { /* 无班级时手动输入 */ });

    k12Api.curriculum()
      .then(({ data }) => {
        const ns = data?.nodes || [];
        if (Array.isArray(ns) && ns.length) setNodes(ns.map((n: any) => ({ id: n.id, title: n.title, subject_id: n.subject_id })));
      })
      .catch(() => {});
  }, []);

  const loadMastery = (cid: string) => {
    if (!cid) return;
    setMasteryLoading(true);
    teacherApi.classMastery(cid)
      .then(({ data }) => {
        const arr = data?.nodes || [];
        setMastery(Array.isArray(arr) ? arr.map((n: any) => ({ id: n.id, mastery: n.mastery ?? n.mastery_pct ?? 0, title: n.title, subject_id: n.subject_id })) : []);
      })
      .catch(() => setMastery([]))
      .finally(() => setMasteryLoading(false));
  };

  useEffect(() => { if (classId) loadMastery(classId); }, [classId]);

  const toggleNode = (id: string) =>
    setSelectedNodes(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);

  const submit = async () => {
    if (!classId || selectedNodes.length === 0 || !dueAt) {
      showToast('请选择班级、至少一个知识点和截止时间', 'warning');
      return;
    }
    setSubmitting(true);
    try {
      await teacherApi.createAssignment({ class_id: classId, node_ids: selectedNodes, due_at: new Date(dueAt).toISOString() });
      showToast('作业布置成功 🎉', 'success');
      setSelectedNodes([]);
      setDueAt('');
    } catch (err: any) {
      showToast(err?.response?.data?.detail || '布置失败', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 800, color: '#2C6E8F', margin: '0 0 4px', fontFamily: "'Baloo 2',sans-serif" }}>
        👩‍🏫 教师作业台
      </h1>
      <p style={{ color: '#64748b', margin: '0 0 20px', fontSize: 14 }}>选班级、选课标知识点、设定截止，把任务精准派发给课堂。</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* 作业布置表单 */}
        <motion.div className="lf-card" initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#2C6E8F', marginBottom: 12 }}>布置作业</div>

          <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>选择班级</label>
          {classes.length > 0 ? (
            <select className="input" value={classId} onChange={e => setClassId(e.target.value)} style={{ height: 44, borderRadius: 14, marginBottom: 12 }}>
              <option value="">— 请选择班级 —</option>
              {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          ) : (
            <input className="input" placeholder="班级 ID（如 class-1）" value={classId} onChange={e => setClassId(e.target.value)} style={{ height: 44, borderRadius: 14, marginBottom: 12 }} />
          )}

          <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>选择知识点（{selectedNodes.length}）</label>
          <div style={{ maxHeight: 180, overflowY: 'auto', display: 'flex', flexWrap: 'wrap', gap: 8, padding: 10, background: '#F7FBFD', borderRadius: 14, border: '1px solid #EAF2F6', marginBottom: 12 }}>
            {nodes.length === 0 && <span style={{ fontSize: 12, color: '#94A3B8' }}>暂无知识点（可后台标注）</span>}
            {nodes.map(n => {
              const sel = selectedNodes.includes(n.id);
              const c = subjectColor(n.subject_id);
              return (
                <button key={n.id} className="tap-target" onClick={() => toggleNode(n.id)}
                  style={{ padding: '6px 12px', borderRadius: 12, border: `2px solid ${sel ? c : '#EAF2F6'}`, background: sel ? `${c}1A` : '#fff', color: sel ? c : '#64748b', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                  {subjectMeta(n.subject_id).emoji} {n.title}
                </button>
              );
            })}
          </div>

          <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>截止时间</label>
          <input type="datetime-local" className="input" value={dueAt} onChange={e => setDueAt(e.target.value)} style={{ height: 44, borderRadius: 14, marginBottom: 16 }} />

          <button className="lf-btn lf-btn-primary" style={{ width: '100%' }} disabled={submitting} onClick={submit}>
            <Send size={16} /> {submitting ? '布置中...' : '布置作业'}
          </button>
        </motion.div>

        {/* 班级掌握热力图（尽力） */}
        <motion.div className="lf-card" initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, fontWeight: 700, color: '#2C6E8F', marginBottom: 12 }}>
            <Grid3x3 size={16} color="#9B7EDE" /> 班级掌握热力图
          </div>
          {masteryLoading ? (
            <div style={{ color: '#94A3B8', fontSize: 13 }}>加载中...</div>
          ) : mastery.length === 0 ? (
            <div style={{ color: '#94A3B8', fontSize: 13 }}>选择班级后展示各知识点掌握度</div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(64px, 1fr))', gap: 6 }}>
              {mastery.map((m, i) => (
                <motion.div key={m.id}
                  initial={reduced ? false : { opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: Math.min(i * 0.02, 0.3), duration: 0.25 }}
                  title={`${m.title || m.id}: ${m.mastery}%`}
                  style={{ height: 48, borderRadius: 12, background: masteryColor(m.mastery), color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700 }}>
                  {m.mastery}%
                </motion.div>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', gap: 10, marginTop: 12, fontSize: 11, color: '#94A3B8' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: '#E0533D' }} />弱</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: '#E68A3C' }} />中</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: '#3FA66A' }} />强</span>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
