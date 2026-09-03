import React from 'react';
import { motion } from 'framer-motion';
import { subjectMeta, EASE_SOFT } from '../../theme/tokens';
import { useMotionPref } from '../../contexts/MotionContext';

interface NumberLine {
  points: { value: number; label?: string }[];
  min?: number;
  max?: number;
}
interface PosToken {
  text: string;
  pos: 'noun' | 'verb' | 'adj' | 'adv' | 'func' | 'other';
}
interface TimelineEvent {
  time: string;
  text: string;
}
interface FlowSteps {
  steps: string[];
}

interface DualCodeVizProps {
  subject?: string | null;
  numberLine?: NumberLine;
  posTokens?: PosToken[];
  timeline?: TimelineEvent[];
  flow?: FlowSteps;
}

// 词性色标
const POS_COLORS: Record<PosToken['pos'], string> = {
  noun: '#4F5BD5',   // 名词-靛
  verb: '#E0533D',   // 动词-朱
  adj: '#3FA66A',    // 形容词-绿
  adv: '#E68A3C',    // 副词-橙
  func: '#9B7EDE',   // 虚词-休息紫
  other: '#6B7C99',  // 其他
};
const POS_LABELS: Record<PosToken['pos'], string> = {
  noun: '名词', verb: '动词', adj: '形容词', adv: '副词', func: '虚词', other: '其他',
};

function NumberLineViz({ data }: { data: NumberLine }) {
  const min = data.min ?? 0;
  const max = data.max ?? 100;
  const span = max - min || 1;
  return (
    <div>
      <div style={{ position: 'relative', height: 40, margin: '8px 6px 0' }}>
        <div style={{ position: 'absolute', left: 0, right: 0, top: 18, height: 4, background: '#EAF6FB', borderRadius: 999 }} />
        {data.points.map((p, i) => {
          const pct = ((p.value - min) / span) * 100;
          return (
            <div key={i} style={{ position: 'absolute', left: `${pct}%`, top: 8, transform: 'translateX(-50%)', textAlign: 'center' }}>
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: i * 0.05, duration: 0.3, ease: EASE_SOFT }}
                style={{ width: 22, height: 22, borderRadius: 999, background: '#3BA9C9', color: '#fff', fontSize: 11, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}
              >
                {p.value}
              </motion.div>
              {p.label && <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>{p.label}</div>}
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94A3B8', marginTop: 4 }}>
        <span>{min}</span><span>{max}</span>
      </div>
    </div>
  );
}

function PosColorViz({ tokens }: { tokens: PosToken[] }) {
  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
        {tokens.map((t, i) => (
          <motion.span
            key={i}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03, duration: 0.25 }}
            title={POS_LABELS[t.pos]}
            style={{ padding: '4px 10px', borderRadius: 12, background: `${POS_COLORS[t.pos]}18`, color: POS_COLORS[t.pos], fontSize: 13, fontWeight: 600, borderBottom: `2px solid ${POS_COLORS[t.pos]}` }}
          >
            {t.text}
          </motion.span>
        ))}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 8, fontSize: 11, color: '#64748b' }}>
        {(Object.keys(POS_COLORS) as PosToken['pos'][]).map(pos => (
          <span key={pos} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: POS_COLORS[pos] }} />
            {POS_LABELS[pos]}
          </span>
        ))}
      </div>
    </div>
  );
}

function TimelineViz({ events }: { events: TimelineEvent[] }) {
  return (
    <div style={{ marginTop: 4 }}>
      {events.map((e, i) => (
        <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', paddingBottom: i < events.length - 1 ? 12 : 0 }}>
          <div style={{ flexShrink: 0, textAlign: 'right', width: 56, fontSize: 12, color: '#2C6E8F', fontWeight: 600, paddingTop: 2 }}>{e.time}</div>
          <div style={{ flexShrink: 0, marginTop: 5 }}>
            <span style={{ width: 12, height: 12, borderRadius: 999, background: '#3FA66A', display: 'inline-block', border: '3px solid #EAF6FB' }} />
            {i < events.length - 1 && <span style={{ width: 2, height: 24, background: '#EAF6FB', display: 'block', margin: '2px auto' }} />}
          </div>
          <div style={{ flex: 1, fontSize: 13, color: '#475569' }}>{e.text}</div>
        </div>
      ))}
    </div>
  );
}

function FlowViz({ steps }: { steps: FlowSteps }) {
  return (
    <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6 }}>
      {steps.steps.map((s, i) => (
        <React.Fragment key={i}>
          <span style={{ padding: '6px 12px', borderRadius: 14, background: '#EAF6FB', color: '#2C6E8F', fontSize: 13, fontWeight: 600 }}>{i + 1}. {s}</span>
          {i < steps.steps.length - 1 && <span style={{ color: '#94A3B8' }}>→</span>}
        </React.Fragment>
      ))}
    </div>
  );
}

/**
 * 双编码可视化（视觉 + 语言双重表征，Spec §6 Learn / DualCodeViz）。
 * 按学科切换：数学=数轴线 / 语文=词性色标 / 英语=时间线 / 科学=流程图。
 * 无对应数据时显示友好的说明占位，绝不抛错。
 */
export default function DualCodeViz({ subject, numberLine, posTokens, timeline, flow }: DualCodeVizProps) {
  const { reduced } = useMotionPref();
  const meta = subjectMeta(subject);
  const key = (subject || '').toLowerCase();

  let body: React.ReactNode = null;
  let caption = '';

  if (key.includes('math') || key.includes('数')) {
    caption = '数轴线：把数量放在连续的刻度上，帮助建立大小关系。';
    body = numberLine ? <NumberLineViz data={numberLine} /> : <Placeholder subject={meta.label} type="数轴线" />;
  } else if (key.includes('chinese') || key.includes('语文') || key.includes('语')) {
    caption = '词性色标：用颜色区分词的作用，帮助理解句子结构。';
    body = posTokens ? <PosColorViz tokens={posTokens} /> : <Placeholder subject={meta.label} type="词性色标" />;
  } else if (key.includes('english') || key.includes('英语') || key.includes('英')) {
    caption = '时间线：把事件按顺序排开，帮助记忆先后与因果。';
    body = timeline ? <TimelineViz events={timeline} /> : <Placeholder subject={meta.label} type="时间线" />;
  } else if (key.includes('science') || key.includes('科学') || key.includes('科')) {
    caption = '流程图：把步骤串成顺序，帮助理解过程与逻辑。';
    body = flow ? <FlowViz steps={flow} /> : <Placeholder subject={meta.label} type="流程图" />;
  } else {
    caption = '双编码：用图 + 文字一起记，记得更牢。';
    body = <Placeholder subject={meta.label} type="双编码图" />;
  }

  return (
    <motion.div
      initial={reduced ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, ease: EASE_SOFT }}
      style={{
        padding: '16px 18px',
        borderRadius: 20,
        background: '#F7FBFD',
        border: '1px solid #E3EEF3',
      }}
      aria-label={`${meta.label}双编码可视化：${caption}`}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <span style={{ fontSize: 18 }} aria-hidden>{meta.emoji}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#2C6E8F' }}>{meta.label}·双编码</span>
      </div>
      {body}
      <p style={{ fontSize: 12, color: '#64748b', margin: '10px 0 0' }}>{caption}</p>
    </motion.div>
  );
}

function Placeholder({ subject, type }: { subject: string; type: string }) {
  return (
    <div style={{ padding: 16, textAlign: 'center', color: '#94A3B8', fontSize: 13, background: '#fff', borderRadius: 14, border: '1px dashed #E3EEF3' }}>
      {subject}的{type}将在此随题目展示 ✨
    </div>
  );
}
