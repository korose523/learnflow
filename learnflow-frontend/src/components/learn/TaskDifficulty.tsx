import React from 'react';

/** The stored 1–10 item category is not an estimated success probability. */
export default function TaskDifficulty({ value }: { value?: number }) {
  if (value === undefined || !Number.isFinite(value) || value < 1 || value > 10) {
    return <p style={{ color: '#64748b', fontSize: 13 }}>题目难度等级未提供</p>;
  }
  return <div aria-label={`题目难度等级 ${value}/10`}>
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#64748b', marginBottom: 6 }}>
      <span>题目难度等级</span><strong>{value}/10</strong>
    </div>
    <div style={{ height: 8, background: '#eaf6fb', borderRadius: 8 }}>
      <div style={{ height: '100%', width: `${value * 10}%`, borderRadius: 8, background: '#3ba9c9' }} />
    </div>
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
      <span>1（较低）</span><span>10（较高）</span>
    </div>
  </div>;
}
