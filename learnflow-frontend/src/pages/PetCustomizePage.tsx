import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { studentApi, gamificationApi } from '../services/api';
import { ArrowLeft, Sparkles, Palette } from 'lucide-react';

const PET_EMOJIS: Record<string, string> = {
  cat: '🐱', dog: '🐶', rabbit: '🐰', owl: '🦉', dragon: '🐉',
};

const MOOD_LABELS: Record<string, string> = {
  happy: '开心', focused: '专注', tired: '疲惫', encouraging: '鼓励中', confident: '自信', curious: '好奇',
};

const COSMETICS = [
  { key: 'crown', emoji: '👑', name: '小皇冠' },
  { key: 'hat', emoji: '🎩', name: '礼帽' },
  { key: 'bow', emoji: '🎀', name: '蝴蝶结' },
  { key: 'star', emoji: '🌟', name: '星星' },
  { key: 'glasses', emoji: '👓', name: '眼镜' },
  { key: 'cape', emoji: '🦸', name: '披风' },
];

export default function PetCustomizePage() {
  const navigate = useNavigate();
  const [pet, setPet] = useState<any>(null);
  const [name, setName] = useState('');
  const [visuals, setVisuals] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const loadPet = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await studentApi.pet();
      setPet(data.pet);
      setName(data.pet.name);
      setVisuals(data.pet.visuals_state || {});
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载宠物信息失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPet();
  }, []);

  const toggleCosmetic = (key: string) => {
    setVisuals((prev) => {
      const next = { ...prev };
      if (next[key]) {
        delete next[key];
      } else {
        next[key] = true;
      }
      return next;
    });
  };

  const handleSave = async () => {
    setMessage('');
    try {
      await gamificationApi.updatePet({ name, visuals_state: visuals });
      setMessage('宠物装扮已保存');
      setPet((prev: any) => ({ ...prev, name, visuals_state: visuals }));
    } catch (err) {
      setMessage('保存失败');
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}>加载宠物中...</div>;
  if (error) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>宠物加载失败</div>
      <div style={{ color: '#64748b', marginBottom: 20 }}>{error}</div>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
        <button className="btn btn-primary" onClick={loadPet}>重试</button>
        <button className="btn btn-ghost" onClick={() => navigate('/student')}>返回首页</button>
      </div>
    </div>
  );
  if (!pet) return <div className="card">还没有宠物</div>;

  const activeCosmetics = Object.keys(visuals).filter((k) => visuals[k]).map((k) => COSMETICS.find((c) => c.key === k)?.emoji).filter(Boolean).join('');

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button className="btn btn-ghost" onClick={() => navigate('/student')}><ArrowLeft size={18} /></button>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>🐾 宠物装扮</h1>
      </div>

      <div className="card" style={{ textAlign: 'center', marginBottom: 20 }}>
        <div style={{ fontSize: 80, marginBottom: 8 }}>
          {PET_EMOJIS[pet.breed] || '🐱'}
          {activeCosmetics && <span style={{ fontSize: 40, marginLeft: 8 }}>{activeCosmetics}</span>}
        </div>
        <div style={{ fontSize: 20, fontWeight: 700 }}>{pet.name}</div>
        <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
          Lv.{pet.level} · {MOOD_LABELS[pet.mood] || '开心'} · 总分 {pet.total_score}
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Sparkles size={18} color="#6366f1" /> 宠物名字
        </h2>
        <input
          className="input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ width: '100%', padding: 12, borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 16 }}
        />
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Palette size={18} color="#f59e0b" /> 装扮选择
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))', gap: 12 }}>
          {COSMETICS.map((c) => (
            <button
              key={c.key}
              onClick={() => toggleCosmetic(c.key)}
              style={{
                padding: 16,
                borderRadius: 12,
                border: '1px solid #e2e8f0',
                background: visuals[c.key] ? '#eef2ff' : 'white',
                cursor: 'pointer',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 32, marginBottom: 4 }}>{c.emoji}</div>
              <div style={{ fontSize: 13, color: visuals[c.key] ? '#6366f1' : '#64748b', fontWeight: visuals[c.key] ? 600 : 400 }}>{c.name}</div>
            </button>
          ))}
        </div>
      </div>

      <button className="btn btn-primary" onClick={handleSave} style={{ width: '100%', padding: 14, fontSize: 16 }}>
        保存装扮
      </button>
      {message && <p style={{ marginTop: 12, textAlign: 'center', color: message.includes('失败') ? '#ef4444' : '#22c55e' }}>{message}</p>}
    </div>
  );
}
