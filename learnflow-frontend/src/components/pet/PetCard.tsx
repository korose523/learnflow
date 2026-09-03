import React from 'react';
import { Heart, Brain, Lightbulb, Users } from 'lucide-react';

const PET_EMOJIS: Record<string, string> = {
  cat: '🐱', dog: '🐶', rabbit: '🐰', owl: '🦉', dragon: '🐉',
};

const MOOD_LABELS: Record<string, { emoji: string; label: string }> = {
  happy: { emoji: '😊', label: '开心' },
  focused: { emoji: '🧘', label: '专注' },
  tired: { emoji: '😴', label: '疲惫' },
  encouraging: { emoji: '💪', label: '鼓励中' },
  confident: { emoji: '😎', label: '自信' },
  curious: { emoji: '🤔', label: '好奇' },
};

interface PetProps {
  pet: {
    name: string;
    breed: string;
    level: number;
    mood: string;
    dimensions: {
      understanding: number;
      persistence: number;
      creativity: number;
      collaboration: number;
    };
    total_score: number;
    dominant_trait: string;
    level_progress: number;
    visuals_state?: Record<string, any>;
  } | null;
}

// 四维属性映射到学科/语义色，童趣圆润
const DIMENSIONS = [
  { key: 'understanding', label: '理解力', icon: Brain, color: '#3BA9C9', value: 0 },
  { key: 'persistence', label: '坚持力', icon: Heart, color: '#E0533D', value: 0 },
  { key: 'creativity', label: '创造力', icon: Lightbulb, color: '#E68A3C', value: 0 },
  { key: 'collaboration', label: '协作力', icon: Users, color: '#3FA66A', value: 0 },
];

export default function PetCard({ pet }: PetProps) {
  if (!pet) {
    return (
      <div className="lf-card" style={{ textAlign: 'center', padding: 40 }}>
        <span style={{ fontSize: 48 }}>🥚</span>
        <p style={{ color: '#64748b', marginTop: 12 }}>还没有宠物，快去创建吧！</p>
      </div>
    );
  }

  const mood = MOOD_LABELS[pet.mood] || { emoji: '😊', label: '开心' };
  const petEmoji = PET_EMOJIS[pet.breed] || '🐱';

  const dimensions = DIMENSIONS.map(d => ({
    ...d,
    value: pet.dimensions[d.key as keyof typeof pet.dimensions] ?? 0,
  }));

  return (
    <div className="lf-card" style={{ textAlign: 'center' }}>
      {/* 宠物形象（圆润呼吸动画） */}
      <div className="pet-breathing" style={{ fontSize: 64, marginBottom: 8 }}>
        {petEmoji}
      </div>

      <div style={{ fontSize: 18, fontWeight: 700, color: '#2C6E8F' }}>{pet.name}</div>
      <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
        Lv.{pet.level} · {mood.emoji} {mood.label}
      </div>

      {/* 等级进度 */}
      <div style={{ margin: '12px 0' }}>
        <div className="progress-bar" style={{ background: '#EAF6FB' }}>
          <div className="progress-bar-fill" style={{ width: `${pet.level_progress}%`, background: '#3BA9C9' }} />
        </div>
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
          升级进度 {pet.level_progress}%
        </div>
      </div>

      {/* 四维属性 */}
      <div style={{ display: 'grid', gap: 8 }}>
        {dimensions.map(({ key, label, icon: Icon, color, value }) => (
          <div key={key} style={{ textAlign: 'left' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 3 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#64748b' }}>
                <Icon size={14} color={color} />
                {label}
              </div>
              <span style={{ fontSize: 12, fontWeight: 600 }}>{value}</span>
            </div>
            <div className="progress-bar" style={{ height: 6, background: '#EAF6FB', borderRadius: 999 }}>
              <div className="progress-bar-fill" style={{ width: `${value}%`, background: color, borderRadius: 999 }} />
            </div>
          </div>
        ))}
      </div>

      {/* 主导特质 */}
      <div style={{
        marginTop: 12,
        padding: '8px 12px',
        background: '#EAF6FB',
        borderRadius: 14,
        fontSize: 12,
        color: '#2C6E8F',
      }}>
        🏅 主导特质：{dimensions.find(d => d.key === pet.dominant_trait)?.label || '探索者'}
      </div>
    </div>
  );
}
