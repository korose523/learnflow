"""学习方法 v2 引擎 — 把「28 种学习方法」从宣称变为真实可调度的实现

背景
----
LearnFlow 历史宣称"28 种学习方法", 真实只有 23 个 (见 scripts/verify_counts.py
的 learning_methods=23)。本项目不"把数字改掉", 而是**补上 5 个真实、证据充分、
且与现有 23 个无语义重叠的学习方法**, 让 28 成为可复算的真值。

选这 5 个的判据 (见 docs/LearnFlow_学习方法候选核验.md):
1. 与现有 23 个不构成重复 (各自有明确的区分边界);
2. 有可靠的一手实证文献支撑;
3. 在 K12 数学/语文在线练习场景可真实实施 (不是纯理论构想)。

本模块的每个引擎都**真实产出内容** (不是只返回一条 tip 文案), 因此
method_registry 里它们的 delivery 标注为 interactive/plan/quiz, 与仅 tip 的方法
区分开。
"""
from typing import Any, Dict, List, Optional


# ────────────────────────────────────────────────────────────
# LF-L24  例题-解题对 (worked examples / example-problem pairs)
#   Sweller (1988); Renkl (2005, Educational Psychology Review)
#   区分边界: 与 L17 generation(自生成答案)不同 —— 这里是"先示范完整解,
#   再逐步渐隐 (fading), 最后交给你独立做", 是范例学习的经典范式。
# ────────────────────────────────────────────────────────────

class WorkedExamplesEngine:
    """例题-解题对引擎: 把一个完整例题拆成「完整范例 → 渐隐 → 空白」三阶段。"""

    @staticmethod
    def build_faded_sequence(
        problem: str,
        full_solution: List[str],
        blanks_from_stage: int = 2,
    ) -> Dict[str, Any]:
        """生成渐隐训练序列。

        Args:
            problem: 题目
            full_solution: 完整解题步骤 (每行一步)
            blanks_from_stage: 从第几阶段开始把步骤留空 (默认 2: 第1阶段全展示)

        Returns:
            含 method / problem / stages 的 dict, stages[i] 的 steps 里
            ``solution`` 为 None 表示该步需学习者自己填。
        """
        n = len(full_solution)
        stages: List[Dict[str, Any]] = []
        for stage in range(n + 1):
            # stage 0: 全展示; stage k: 末 k 步留空
            steps = [
                {"step": i + 1, "solution": (s if i < n - stage else None)}
                for i, s in enumerate(full_solution)
            ]
            stages.append({
                "stage": stage,
                "label": "完整范例" if stage == 0 else f"渐隐第{stage}步" if stage < n else "独立完成",
                "steps": steps,
            })
        return {
            "method": "例题-解题对",
            "method_key": "worked_examples",
            "problem": problem,
            "stages": stages,
            "tip": "先看完整解, 再尝试只补全最后几步, 最后独立做 —— 渐隐比直接刷题记得牢。",
        }


# ────────────────────────────────────────────────────────────
# LF-L25  关键词记忆法 (keyword mnemonic)
#   Atkinson & Raugh (1975)
#   区分边界: 与 L01 memory_palace(空间记忆法)不同 —— 关键词法专攻
#   外语/生词: 用母语中发音相近的词做"声音桥", 再配一幅夸张意象。
# ────────────────────────────────────────────────────────────

class KeywordMnemonicEngine:
    """关键词记忆法引擎: 为生词构造 acoustic+imagery 记忆桥。"""

    @staticmethod
    def build_mnemonic(
        target: str,
        target_lang: str,
        native_keyword: str,
        imagery: str,
    ) -> Dict[str, Any]:
        """构造关键词记忆条。

        Args:
            target: 目标词 (如英语 "ambulance")
            target_lang: 目标语言名 (如 "英语")
            native_keyword: 母语中发音相近的词 (如 "俺不能死")
            imagery: 连接意象 (如 "一辆救护车呼啸而过, 车上人喊'俺不能死'")

        Returns:
            含 method / keyword / story 的 dict
        """
        if not native_keyword or not imagery:
            raise ValueError("关键词记忆法必须同时给出母语关键词与意象")
        return {
            "method": "关键词记忆法",
            "method_key": "keyword_mnemonic",
            "target": target,
            "target_lang": target_lang,
            "keyword": native_keyword,
            "story": f"把「{target}」联想成「{native_keyword}」: {imagery}",
            "tip": "声音桥 + 一幅夸张的画面, 生词就钉进长期记忆了。",
        }


# ────────────────────────────────────────────────────────────
# LF-L26  有效失败 (productive failure)
#   Kapur (2008, Cognition and Instruction, 26(3):379-424)
#   区分边界: 与 L16 pretesting(先行测试, 测后再学)不同 —— 有效失败是
#   "先尝试**解决/生成方案**再接受教学", 且强调随后的结构化归纳
#   (consolidation) 必须建立在学习者自己的尝试之上。
# ────────────────────────────────────────────────────────────

class ProductiveFailureEngine:
    """有效失败引擎: 先探索后归纳的两阶段学习设计。"""

    @staticmethod
    def build_session(
        problem: str,
        target_concept: str,
        min_attempts: int = 2,
    ) -> Dict[str, Any]:
        """生成一次有效失败学习会话的提示与归纳引导。

        Args:
            problem: 超出当前能力、但可探索的复杂问题
            target_concept: 目标概念
            min_attempts: 进入归纳阶段前要求的最少尝试数

        Returns:
            含 exploration_prompt / consolidation_guide 的 dict
        """
        return {
            "method": "有效失败",
            "method_key": "productive_failure",
            "target_concept": target_concept,
            "exploration_prompt": (
                f"在学「{target_concept}」之前, 先试着解决: {problem}。"
                f"至少想出 {min_attempts} 种不同的思路 (哪怕都不完美), 并说明每种思路"
                f"可能哪里行得通、哪里会卡住。你的尝试是后续讲解的原材料。"
            ),
            "consolidation_guide": (
                f"现在对照标准解法: 你刚才的哪种思路最接近? 哪种思路漏掉了关键? "
                f"哪一步让你第一次意识到'这里我原来不懂'?"  # 即 Kapur 的 failure awareness
            ),
            "warn": "无归纳的纯失败是'无效失败', 不会带来同等收益 —— 必须有结构化归纳阶段。",
        }


# ────────────────────────────────────────────────────────────
# LF-L27  摘要法 (summarization)
#   Wittwer & Renkl (2010, Educational Psychology Review, 22:351-371)
#   区分边界: 与 L05 elaborative_rehearsal(用自己的话重述)/L18 self_explanation
#   (解释为什么)不同 —— 摘要法是"对一段文本抽取主干, 压缩成 1-3 句",
#   训练的是选择性与压缩能力。
# ────────────────────────────────────────────────────────────

class SummarizationEngine:
    """摘要法引擎: 引导对一段文本做主干压缩。"""

    @staticmethod
    def build_prompt(
        passage: str,
        max_sentences: int = 3,
    ) -> Dict[str, Any]:
        """生成摘要练习提示。

        Args:
            passage: 待摘要的文本
            max_sentences: 要求的最多句数

        Returns:
            含 method / scaffolding 的 dict
        """
        return {
            "method": "摘要法",
            "method_key": "summarization",
            "passage": passage,
            "scaffolding": [
                "划出这段文字在讲的核心主张 (一句话能说清的那个)",
                f"删掉例子、修饰和重复, 只留主干, 压缩到 {max_sentences} 句以内",
                "对比你的摘要和原文: 有没有丢掉不该丢的关键信息?",
            ],
            "tip": "能压缩成 3 句话, 才说明你真的读懂了。",
        }


# ────────────────────────────────────────────────────────────
# LF-L28  变异练习 (varied practice)
#   Schmidt & Bjork (1992, Psychological Science, 3(2):77-82)
#   区分边界: 与 L04 interleaving(不同题型混排)不同 —— 变异练习保持同一
#   任务类型, 但改变其**表面特征/情境**, 迫使学习者抓本质而非套模板。
# ────────────────────────────────────────────────────────────

class VariedPracticeEngine:
    """变异练习引擎: 给同一知识点换不同表面情境, 防止套模板。"""

    @staticmethod
    def generate_variants(
        topic: str,
        base_template: str,
        contexts: List[str],
    ) -> Dict[str, Any]:
        """生成同型异境的练习变体。

        Args:
            topic: 知识点
            base_template: 题干模板 (含 {context} 占位符)
            contexts: 不同情境列表 (如 ["买苹果", "分糖果", "切披萨"])

        Returns:
            含 method / variants 的 dict
        """
        if not contexts:
            raise ValueError("变异练习必须提供至少 1 个情境")
        variants = [
            {"index": i + 1, "context": c,
             "problem": base_template.format(context=c, topic=topic)}
            for i, c in enumerate(contexts)
        ]
        return {
            "method": "变异练习",
            "method_key": "varied_practice",
            "topic": topic,
            "variants": variants,
            "tip": "题面在变, 本质不变 —— 练的是'换汤不换药'时还能认出它。",
        }
