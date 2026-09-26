import { createWorkBuddyCloud } from '@tencent-ai/workbuddy-cloud-sdk';

const cloud = createWorkBuddyCloud({
  endpoint: 'https://learnflow-m3.app.workbuddy.host',
  publishableKey: 'wbpk_hQLryzm3q8l7pV0ICsheMd_OE7SPIY1Z3OiGqyWv62vVMEB07nbmbUs',
});

const model = 'glm-5.3-flash';
const prompt = 'Rate the difficulty of this math problem on a 1-3 scale (1=easiest, 3=hardest). Reply with ONLY a single integer.\n\nProblem: Consider two transactions T1 and T2 executed in the schedule below. Is the schedule conflict serializable? Explain.';

let answer = '';
try {
  for await (const chunk of cloud.llm.chat.completions.create({
    model,
    messages: [
      { role: 'system', content: 'You are a precise math difficulty rater. Reply with only a single integer 1, 2, or 3.' },
      { role: 'user', content: prompt },
    ],
    stream: true,
  })) {
    const delta = chunk.choices?.[0]?.delta?.content;
    if (delta) answer += delta;
  }
  console.log('MODEL:', model);
  console.log('ANSWER:', JSON.stringify(answer));
} catch (e) {
  console.error('ERR:', JSON.stringify(e?.error || e?.message || String(e)));
}
