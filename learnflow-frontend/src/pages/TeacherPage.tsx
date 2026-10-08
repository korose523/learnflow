import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Send, Grid3x3, CheckCircle2 } from 'lucide-react';
import { teacherApi, k12Api } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useMotionPref } from '../contexts/MotionContext';
import { EASE_SOFT, subjectColor, subjectMeta } from '../theme/tokens';

interface ClassInfo { id: string; name: string }
interface NodeInfo { id: string; title: string; subject_id?: string }
interface MasteryNode { id: string; mastery: number | null; title?: string; subject_id?: string }

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
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState('');
  const [catalogVersion, setCatalogVersion] = useState(0);
  const [classId, setClassId] = useState('');
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
  const [dueAt, setDueAt] = useState('');
  const [publishNewVersion, setPublishNewVersion] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [mastery, setMastery] = useState<MasteryNode[]>([]);
  const [masteryLoading, setMasteryLoading] = useState(false);
  const [masteryError, setMasteryError] = useState('');
  const [masteryVersion, setMasteryVersion] = useState(0);

  useEffect(() => {
    let alive = true;
    setCatalogLoading(true);
    setCatalogError('');
    Promise.all([teacherApi.classroom(), k12Api.curriculum()])
      .then(([classResponse, nodeResponse]) => {
        if (!alive) return;
        const cs = classResponse.data?.classes;
        const ns = nodeResponse.data?.nodes;
        if (!Array.isArray(cs) || !Array.isArray(ns)) throw new Error('invalid catalog response');
        setClasses(cs.map((c: any) => ({ id: c.id, name: c.name })));
        setNodes(ns.map((n: any) => ({ id: n.id, title: n.title, subject_id: n.subject_id })));
      })
      .catch(() => {
        if (!alive) return;
        setCatalogError('班级或知识点未能读取，请重试后再布置作业。');
      })
      .finally(() => { if (alive) setCatalogLoading(false); });
    return () => { alive = false; };
  }, [catalogVersion]);

  useEffect(() => {
    let alive = true;
    setMastery([]);
    setMasteryError('');
    if (!classId) { setMasteryLoading(false); return; }
    setMasteryLoading(true);
    teacherApi.classMastery(classId)
      .then(({ data }) => {
        if (!alive) return;
        if (!Array.isArray(data?.nodes)) throw new Error('invalid class statistics');
        setMastery(data.nodes.map((n: any) => ({ id: n.id, mastery: n.mastery ?? null, title: n.title, subject_id: n.subject_id })));
      })
      .catch(() => { if (alive) setMasteryError('班级统计读取失败，请重试。'); })
      .finally(() => { if (alive) setMasteryLoading(false); });
    return () => { alive = false; };
  }, [classId, masteryVersion]);

  const toggleNode = (id: string) =>
    setSelectedNodes(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);

  const submit = async () => {
    if (catalogLoading || catalogError) return;
    if (!classId || selectedNodes.length === 0 || !dueAt) {
      showToast('请选择班级、至少一个知识点和截止时间', 'warning');
      return;
    }
    setSubmitting(true);
    try {
      await teacherApi.createAssignment({ class_id: classId, node_ids: selectedNodes, due_at: new Date(dueAt).toISOString(), new_version: publishNewVersion });
      showToast('作业布置成功 🎉', 'success');
      setSelectedNodes([]);
      setDueAt('');
      setPublishNewVersion(false);
      setMasteryVersion(v => v + 1);
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
          {catalogError ? (
            <div role="alert">{catalogError}<button className="lf-btn" onClick={() => setCatalogVersion(v => v + 1)}>重试读取</button></div>
          ) : catalogLoading ? <p>正在读取班级与知识点…</p> : classes.length > 0 ? (
            <select className="input" value={classId} onChange={e => setClassId(e.target.value)} style={{ height: 44, borderRadius: 14, marginBottom: 12 }}>
              <option value="">— 请选择班级 —</option>
              {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          ) : (
            <p>当前没有可用班级，请先完成班级分配。</p>
          )}

          <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>选择知识点（{selectedNodes.length}）</label>
          <div style={{ maxHeight: 180, overflowY: 'auto', display: 'flex', flexWrap: 'wrap', gap: 8, padding: 10, background: '#F7FBFD', borderRadius: 14, border: '1px solid #EAF2F6', marginBottom: 12 }}>
            {!catalogLoading && !catalogError && nodes.length === 0 && <span style={{ fontSize: 12, color: '#94A3B8' }}>暂无知识点（可后台标注）</span>}
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

          <label style={{ display: 'block', marginBottom: 12 }}><input type="checkbox" checked={publishNewVersion} onChange={e => setPublishNewVersion(e.target.checked)} /> 重新布置为新版本（不继承旧提交）</label>
          <p>已有版本未勾选时仅更新截止时间，题目和答案保持原版本。</p>
          <button className="lf-btn lf-btn-primary" style={{ width: '100%' }} disabled={submitting || catalogLoading || !!catalogError || classes.length === 0 || nodes.length === 0} onClick={submit}>
            <Send size={16} /> {submitting ? '布置中...' : '布置作业'}
          </button>
        </motion.div>

        {/* 班级作答正确率（尽力） */}
        <motion.div className="lf-card" initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, fontWeight: 700, color: '#2C6E8F', marginBottom: 12 }}>
            <Grid3x3 size={16} color="#9B7EDE" /> 班级作答正确率
          </div>
          {masteryError ? <div role="alert">{masteryError}<button onClick={() => setMasteryVersion(v => v + 1)}>重试统计</button></div> : masteryLoading ? (
            <div style={{ color: '#94A3B8', fontSize: 13 }}>加载中...</div>
          ) : mastery.length === 0 ? (
            <div style={{ color: '#94A3B8', fontSize: 13 }}>{classId ? '当前班级没有可展示的知识点' : '请选择班级查看作答统计'}</div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(64px, 1fr))', gap: 6 }}>
              {mastery.map((m, i) => (
                <motion.div key={m.id}
                  initial={reduced ? false : { opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: Math.min(i * 0.02, 0.3), duration: 0.25 }}
                  title={`${m.title || m.id}: ${m.mastery === null ? "暂无作答" : m.mastery + "%"}`}
                  style={{ height: 48, borderRadius: 12, background: m.mastery === null ? '#94A3B8' : masteryColor(m.mastery), color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700 }}>
                  {m.mastery === null ? '暂无' : `${m.mastery}%`}
                </motion.div>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', gap: 10, marginTop: 12, fontSize: 11, color: '#94A3B8' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: '#E0533D' }} />低</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: '#E68A3C' }} />中</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: '#3FA66A' }} />高</span>
          </div>
        </motion.div>
      </div>
      <TeacherAssignmentResults key={classId} classId={classId} version={masteryVersion} />
    </div>
  );
}

const assignmentCellStyle: React.CSSProperties = { padding: '10px 14px', borderBottom: '1px solid #EAF2F6', textAlign: 'left', whiteSpace: 'nowrap' };
interface AssignmentSummary { id: string; node_title: string | null; due_at: string | null }
interface AssignmentStudentResult { student_id: string; student_name: string; submitted_count: number; correct_count: number; accuracy_percent: number | null; last_submitted_at: string | null; submission_state: string }
function TeacherAssignmentResults({ classId, version }: { classId: string; version: number }) {
  const [assignments, setAssignments] = useState<AssignmentSummary[]>([]);
  const [selected, setSelected] = useState('');
  const [offset, setOffset] = useState(0);
  const [versions, setVersions] = useState<{ id: string; number: number; task_count: number }[]>([]);
  const [versionChoice, setVersionChoice] = useState('');
  const [versionError, setVersionError] = useState('');
  const [retry, setRetry] = useState(0);
  const [listRetry, setListRetry] = useState(0);
  const [listLoading, setListLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState('');
  const [resultError, setResultError] = useState('');
  const [data, setData] = useState<{ students: AssignmentStudentResult[]; total_students: number; available_task_count: number; has_more: boolean; version_number?: number; task_count?: number } | null>(null);
  useEffect(() => {
    let alive = true;
    setAssignments([]); setSelected(''); setListError('');
    if (!classId) { setListLoading(false); return; }
    setListLoading(true);
    teacherApi.listAssignments(classId).then(({ data: response }) => {
      if (!alive) return;
      if (!Array.isArray(response.assignments)) throw new Error('invalid assignment list');
      setAssignments(response.assignments);
    }).catch(() => { if (alive) setListError('作业列表读取失败。'); }).finally(() => { if (alive) setListLoading(false); });
    return () => { alive = false; };
  }, [classId, version, listRetry]);
  useEffect(() => {
    let alive = true;
    setVersions([]); setVersionChoice(''); setVersionError('');
    if (!selected) return;
    teacherApi.assignmentVersions(selected).then(({ data: response }) => {
      if (!alive) return;
      if (!Array.isArray(response.versions)) throw new Error('invalid version list');
      setVersions(response.versions);
    }).catch(() => { if (alive) setVersionError('历史版本列表读取失败，可重试作业列表。'); });
    return () => { alive = false; };
  }, [selected, version]);
  useEffect(() => {
    let alive = true;
    setData(null); setResultError('');
    if (!selected) { setLoading(false); return; }
    setLoading(true);
    teacherApi.assignmentResults(selected, offset, versionChoice).then(({ data: response }) => {
      if (!alive) return;
      if (!Array.isArray(response.students)) throw new Error('invalid assignment results');
      setData(response);
    }).catch(() => { if (alive) setResultError('提交记录读取失败。'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [selected, offset, retry, versionChoice]);
  return <section className="lf-card" style={{ marginTop: 16 }}>
    <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 12 }}>作业提交记录</h2>
    <p>只统计明确关联本作业的首次提交，显示当前班级活跃学生。已记录不等于答对或整份完成。</p>
    {!classId ? <p>请先选择班级。</p> : listLoading ? <p role="status">正在读取作业列表…</p> : listError ? <p role="alert">{listError}<button className="lf-btn" style={{ margin: 8 }} onClick={() => setListRetry(v => v + 1)}>重试作业列表</button></p> : <>
      <label>选择作业<select className="input" style={{ margin: '12px 8px', width: 'auto' }} aria-label="选择作业" value={selected} onChange={e => { setSelected(e.target.value); setOffset(0); }}>
        <option value="">请选择作业</option>
        {assignments.map(a => <option key={a.id} value={a.id}>{a.node_title || '未命名知识点'}</option>)}
      </select></label>
      <label>结果版本<select aria-label="结果版本" className="input" style={{ width:'auto',margin:8 }} value={versionChoice} onChange={e => { setVersionChoice(e.target.value); setOffset(0); }}>
        <option value="">当前最新版本</option>
        {versions.map(v => <option key={v.id} value={v.id}>版本 {v.number} · {v.task_count} 题</option>)}
      </select></label>
      {versionError && <p role="alert">{versionError}</p>}
      <button className="lf-btn" style={{ margin: 8 }} onClick={() => setRetry(v => v + 1)}>刷新提交记录</button>
    </>}
    {loading ? <p role="status">正在读取提交记录…</p> : resultError ? <p role="alert">{resultError}<button className="lf-btn" style={{ margin: 8 }} onClick={() => setRetry(v => v + 1)}>重试提交记录</button></p> : data && <>
      <p>当前班级学生 {data.total_students} 人；当前已审核可用题目 {data.available_task_count} 道。{data.version_number ? `固定版本 ${data.version_number} 共 ${data.task_count} 题；全部已提交不表示全部答对。` : '历史未版本化作业不推断完成状态。'}</p>
      <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}><thead><tr><th style={assignmentCellStyle}>学生</th><th style={assignmentCellStyle}>已记录题数</th><th style={assignmentCellStyle}>答对题数</th><th style={assignmentCellStyle}>作答正确率</th><th style={assignmentCellStyle}>最近提交</th><th style={assignmentCellStyle}>提交状态</th></tr></thead>
        <tbody>{data.students.map(s => <tr key={s.student_id}><td style={assignmentCellStyle}>{s.student_name}</td><td style={assignmentCellStyle}>{s.submitted_count}</td><td style={assignmentCellStyle}>{s.correct_count}</td><td style={assignmentCellStyle}>{s.accuracy_percent === null ? '暂无作答' : `${s.accuracy_percent}%`}</td><td style={assignmentCellStyle}>{s.last_submitted_at ? new Date(s.last_submitted_at).toLocaleString() : '暂无提交'}</td><td style={assignmentCellStyle}>{s.submission_state === 'submitted' ? '全部已提交' : s.submission_state === 'blocked' ? '题目撤回待处理' : s.submission_state === 'legacy_unversioned' ? '历史未版本化' : '尚未全部提交'}</td></tr>)}</tbody>
      </table></div>
      {!data.students.length && <p>当前页没有学生。</p>}
      <button className="lf-btn" style={{ margin: 8 }} disabled={offset === 0} onClick={() => setOffset(v => Math.max(0, v - 50))}>上一页学生</button>
      <button className="lf-btn" style={{ margin: 8 }} disabled={!data.has_more} onClick={() => setOffset(v => v + 50)}>下一页学生</button>
    </>}
  </section>;
}
