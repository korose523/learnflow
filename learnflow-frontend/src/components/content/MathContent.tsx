import React, { useMemo } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import { splitMathContent } from './mathContent';

/** Only KaTeX-generated markup enters HTML; source text stays React-escaped. */
export default function MathContent({ content }: { content: string }) {
  const parts = useMemo(() => splitMathContent(content).map(part => {
    if (part.kind === 'text') return { ...part, html: null };
    try {
      return { ...part, html: katex.renderToString(part.value, {
        displayMode: part.display, throwOnError: true, trust: false,
        maxSize: 10, maxExpand: 1000, output: 'htmlAndMathml', macros: {},
      }) };
    } catch {
      return { ...part, html: null };
    }
  }), [content]);
  return <span className="math-content" style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
    {parts.map((part, index) => part.html === null
      ? <span key={index} {...(part.kind === 'math' ? { 'data-math-error': true, title: '公式暂时无法排版，保留原文' } : {})}>{part.raw}</span>
      : <span key={index} style={{ display: part.display ? 'block' : 'inline-block', maxWidth: '100%', overflowX: 'auto', verticalAlign: 'middle' }} dangerouslySetInnerHTML={{ __html: part.html }} />)}
  </span>;
}
