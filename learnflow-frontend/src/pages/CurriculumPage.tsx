import React, { useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { BookOpen, Link2, ChevronRight } from 'lucide-react';
import { k12Api } from '../services/api';
import { useMotionPref } from '../contexts/MotionContext';
import { EASE_SOFT, subjectColor, subjectMeta } from '../theme/tokens';
import SubjectBadge from '../components/learn/SubjectBadge';

interface CurriculumNode {
  id: string;
  subject_id?: string;
  title: string;
  chapter?: string;
  grade_id?: string;
  prerequisites?: string[] | null;
}
interface CurriculumResp {
  subjects?: { id: string; name: string; code?: string }[];
  nodes?: CurriculumNode[];
}

export default function CurriculumPage() {
  const { reduced } = useMotionPref();
  const [data, setData] = useState<CurriculumResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    k12Api.curriculum()
      .then(({ data }) => setData(data))
      .catch((err: any) => setError(err?.response?.data?.detail || '课标加载失败'))
      .finally(() => setLoading(false));
  }, []);

  const nodes = data?.nodes ?? [];
  const subjects = data?.subjects ?? [];

  const filtered = useMemo(
    () => filter === 'all' ? nodes : nodes.filter(n => (n.subject_id || '').toLowerCase().includes(filter.toLowerCase())),
    [nodes, filter]
  );

  // 以 subject 分组
  const grouped = useMemo(() => {
    const map = new Map<string, CurriculumNode[]>();
    for (const n of filtered) {
      const key = n.subject_id || '其他';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(n);
    }
    return Array.from(map.entries());
  }, [filtered]);

  if (loading) return <div style={{ textAlign: 'center', padding: 60, color: '#64748b' }}>课标加载中...</div>;
  if (error) return <div style={{ textAlign: 'center', padding: 60, color: '#E0533D' }}>{error}</div>;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: '#2C6E8F', margin: 0, fontFamily: "'Baloo 2',sans-serif" }}>📚 课标浏览</h1>
          <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: 14 }}>按中国课标体系，逐级解锁你的知识点。</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="tap-target" onClick={() => setFilter('all')}
            style={{ padding: '8px 14px', borderRadius: 14, border: '1px solid #E3EEF3', background: filter === 'all' ? '#3BA9C9' : '#fff', color: filter === 'all' ? '#fff' : '#64748b', fontWeight: 600, cursor: 'pointer', fontSize: 13 }}>
            全部
          </button>
          {subjects.map(s => (
            <button key={s.id} className="tap-target" onClick={() => setFilter(s.code || s.id)}
              style={{ padding: '8px 14px', borderRadius: 14, border: `1px solid ${subjectColor(s.code || s.name)}33`, background: filter === (s.code || s.id) ? subjectColor(s.code || s.name) : '#fff', color: filter === (s.code || s.id) ? '#fff' : '#64748b', fontWeight: 600, cursor: 'pointer', fontSize: 13 }}>
              {subjectMeta(s.code || s.name).emoji} {s.name}
            </button>
          ))}
        </div>
      </div>

      {grouped.length === 0 && (
        <div className="lf-card" style={{ textAlign: 'center', color: '#94A3B8' }}>
          暂无课标数据，教师可在后台标注知识点 ✨
        </div>
      )}

      <div style={{ display: 'grid', gap: 16 }}>
        {grouped.map(([subjectId, ns]) => (
          <div key={subjectId} className="lf-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <SubjectBadge subject={subjectId} />
              <span style={{ fontSize: 13, color: '#94A3B8' }}>{ns.length} 个知识点</span>
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              {ns.map((n, i) => (
                <motion.div
                  key={n.id}
                  initial={reduced ? false : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i * 0.03, 0.3), duration: 0.3, ease: EASE_SOFT }}
                  style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', borderRadius: 14, background: '#F7FBFD', border: '1px solid #EAF2F6' }}
                >
                  <BookOpen size={16} color={subjectColor(subjectId)} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, color: '#2C6E8F', fontSize: 14 }}>{n.title}</div>
                    {n.chapter && <div style={{ fontSize: 12, color: '#94A3B8' }}>{n.chapter}</div>}
                  </div>
                  {n.prerequisites && n.prerequisites.length > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#9B7EDE' }}>
                      <Link2 size={12} />
                      {n.prerequisites.length} 个前备
                    </div>
                  )}
                  <ChevronRight size={16} color="#CBD5E1" />
                </motion.div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
