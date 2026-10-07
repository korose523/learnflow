export interface ContentPart {
  kind: 'text' | 'math';
  value: string;
  raw: string;
  display: boolean;
}

function escaped(source: string, index: number): boolean {
  let slashes = 0;
  for (let i = index - 1; i >= 0 && source[i] === '\\'; i--) slashes++;
  return slashes % 2 === 1;
}

/** Preserve source text; XES uses $$ even for inline numbers. */
export function splitMathContent(source: string): ContentPart[] {
  const parts: ContentPart[] = [];
  let start = 0;
  for (let i = 0; i < source.length; i++) {
    if (escaped(source, i)) continue;
    let opening = '', closing = '', display = false;
    if (source.startsWith('$$', i)) opening = closing = '$$';
    else if (source[i] === '$') opening = closing = '$';
    else if (source.startsWith('\\(', i)) { opening = '\\('; closing = '\\)'; }
    else if (source.startsWith('\\[', i)) { opening = '\\['; closing = '\\]'; display = true; }
    if (!opening) continue;
    let end = i + opening.length;
    while (end < source.length && (!source.startsWith(closing, end) || escaped(source, end))) end++;
    if (end === source.length) {
      i += opening.length - 1;
      continue;
    }
    if (start < i) parts.push({ kind: 'text', value: source.slice(start, i), raw: source.slice(start, i), display: false });
    const raw = source.slice(i, end + closing.length);
    parts.push({ kind: 'math', value: source.slice(i + opening.length, end), raw, display });
    i = end + closing.length - 1;
    start = i + 1;
  }
  if (start < source.length) parts.push({ kind: 'text', value: source.slice(start), raw: source.slice(start), display: false });
  return parts;
}
