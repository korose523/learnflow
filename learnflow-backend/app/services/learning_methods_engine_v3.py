"""学习方法引擎 v3：思维导图、双重编码、交错练习、精细加工、生成效应"""
import random
from typing import Dict, Any, List, Optional


class MindMappingEngine:
    """思维导图引擎

    原理：用可视化方式组织知识结构，增强理解和记忆。
    帮助学习者看到知识点之间的联系。

    功能：
    - 自动生成知识结构树
    - 关联知识点可视化
    - 概念连接桥
    """

    @staticmethod
    def generate_knowledge_map(topic: str, sub_topics: List[str]) -> Dict[str, Any]:
        """生成知识图谱结构"""
        nodes = [{"id": "root", "label": topic, "type": "core"}]
        edges = []
        
        for i, st in enumerate(sub_topics):
            node_id = f"sub_{i}"
            nodes.append({"id": node_id, "label": st, "type": "branch"})
            edges.append({"from": "root", "to": node_id})
        
        return {
            "method": "思维导图",
            "description": "将知识点可视化为连接图，帮助理解知识结构",
            "nodes": nodes,
            "edges": edges,
            "tip": "尝试找出这些概念之间的联系，有助于深度理解",
            "action": "花2分钟在纸上画出这个知识结构图",
        }

    @staticmethod
    def generate_concept_bridge(concept_a: str, concept_b: str) -> Dict[str, Any]:
        """生成概念连接桥"""
        return {
            "method": "思维导图 - 概念桥",
            "concept_a": concept_a,
            "concept_b": concept_b,
            "prompt": f"请思考：'{concept_a}' 和 '{concept_b}' 有什么联系？它们如何相互影响？",
            "tip": "找到不同知识点之间的联系是深度学习的标志",
        }


class DualCodingEngine:
    """双重编码引擎

    原理：同时使用文字和视觉信息编码，记忆效果远优于单一编码。

    功能：
    - 文字→图表转换提示
    - 图形化解释生成
    - 视觉记忆卡片
    """

    VISUAL_SYMBOLS = {
        "math": "📐 尝试画一个数轴或坐标系来表示这个概念",
        "science": "🔬 画一个流程图或循环图来表示这个过程",
        "history": "📅 画一个时间线来表示事件顺序",
        "language": "📝 用不同颜色的便签标注不同词性",
        "general": "🎨 用简单的图示来表示这个概念",
    }

    @staticmethod
    def get_visual_prompt(topic: str, category: str = "general") -> Dict[str, Any]:
        """获取可视化提示"""
        return {
            "method": "双重编码",
            "description": "将文字信息转化为视觉图像，双重记忆更牢固",
            "topic": topic,
            "visual_suggestion": DualCodingEngine.VISUAL_SYMBOLS.get(category, DualCodingEngine.VISUAL_SYMBOLS["general"]),
            "tip": "研究表明：图文结合的记忆效果比纯文字高 50% 以上",
        }

    @staticmethod
    def generate_visual_card(content: str) -> Dict[str, Any]:
        """生成视觉记忆卡片"""
        return {
            "method": "双重编码 - 视觉卡片",
            "content": content,
            "instruction": "闭上眼睛，在脑海中想象这个概念的图像",
            "sketch_prompt": f"尝试用简单的线条画出 '{content[:30]}...' 的示意图",
        }


class InterleavingEngine:
    """交错练习引擎

    原理：混合练习不同类型的问题比集中练习同一类型的长期效果更好。

    功能：
    - 自动生成交错练习序列
    - 不同知识点的混合题目
    - 难度交替策略
    """

    @staticmethod
    def generate_interleaved_plan(topics: List[str], rounds: int = 3) -> Dict[str, Any]:
        """生成交错练习计划"""
        # 轮转排列，确保不同topic交替出现
        schedule = []
        for r in range(rounds):
            rotated = topics[r % len(topics):] + topics[:r % len(topics)]
            schedule.extend(rotated)
        
        return {
            "method": "交错练习",
            "description": "混合不同知识点练习比集中练习效果更好",
            "schedule": [{"round": i+1, "topic": s} for i, s in enumerate(schedule)],
            "tip": "虽然感觉更难，但交错练习的长期保持率比集中练习高 40%！",
        }

    @staticmethod
    def get_adaptive_interleave(user_mastery: Dict[str, float]) -> Dict[str, Any]:
        """根据掌握程度自适应交错"""
        weak = [(k, v) for k, v in user_mastery.items() if v < 0.5]
        strong = [(k, v) for k, v in user_mastery.items() if v >= 0.7]
        
        plan = []
        for i in range(min(len(weak), 5)):
            plan.append({"type": "weak", "topic": weak[i][0], "mastery": round(weak[i][1], 2)})
        for i in range(min(len(strong), 3)):
            plan.append({"type": "strong", "topic": strong[i][0], "mastery": round(strong[i][1], 2)})
        
        # 交错排列：弱-强-弱-强
        interleaved = []
        for i in range(max(len(plan)//2, 3)):
            if i < len(plan):
                interleaved.append(plan[i])
        
        return {
            "method": "自适应交错练习",
            "plan": interleaved,
            "tip": "先巩固薄弱点，再通过强项建立信心！",
        }


class ElaborationEngine:
    """精细加工引擎

    原理：用自己的话解释新知识，建立与已有知识的联系，大幅提升理解深度。

    功能：
    - 自我解释提示
    - 类比生成
    - 向他人解释（费曼技巧增强版）
    """

    @staticmethod
    def get_elaboration_prompt(concept: str, difficulty: int = 5) -> Dict[str, Any]:
        """获取精细加工提示"""
        prompts = [
            f"用自己的话解释'{concept}'是什么意思？",
            f"'{concept}'和你之前学过的什么知识有关联？",
            f"你能举一个关于'{concept}'的生活实例吗？",
            f"如果有人不懂'{concept}'，你会怎么教他？",
            f"'{concept}'的反面或例外是什么？",
        ]
        
        return {
            "method": "精细加工",
            "description": "用自己的话解释和联系知识，建立深层理解",
            "concept": concept,
            "prompts": [{"level": i+1, "prompt": p} for i, p in enumerate(prompts[:max(1, min(difficulty//2 + 1, 5))])],
            "tip": "能够用自己的话解释清楚，才是真正的理解",
        }

    @staticmethod
    def generate_analogy(concept: str) -> Dict[str, Any]:
        """生成类比"""
        analogies = [
            {"target": "图书馆", "connection": f"'{concept}'就像图书馆的分类系统，帮助你快速找到需要的信息"},
            {"target": "乐高积木", "connection": f"'{concept}'就像乐高积木，你可以用它搭建出更大的知识体系"},
            {"target": "地图", "connection": f"'{concept}'就像地图上的坐标，帮你在知识海洋中定位"},
            {"target": "食谱", "connection": f"'{concept}'就像食谱中的关键步骤，掌握了它就能做出完整的'知识大餐'"},
        ]
        
        return {
            "method": "精细加工 - 类比",
            "concept": concept,
            "analogy": random.choice(analogies),
            "tip": "好的类比让抽象概念变得具体可感",
            "action": "尝试自己想一个关于这个概念的类比",
        }


class GenerationEffectEngine:
    """生成效应引擎

    原理：自己生成答案比被动接收（选择/识别）的记忆效果更好。

    功能：
    - 填空题模式（比选择题效果好）
    - 自由回忆提示
    - 生成式测验
    """

    @staticmethod
    def generate_fill_blank(content: str, mask_keywords: List[str]) -> Dict[str, Any]:
        """生成填空题"""
        masked = content
        for kw in mask_keywords:
            masked = masked.replace(kw, "____", 1)
        
        return {
            "method": "生成效应 - 填空",
            "description": "填空题比选择题更能促进记忆",
            "original": content,
            "masked": masked,
            "keywords": mask_keywords,
            "tip": "主动回忆比被动识别效果高出 2-3 倍！",
        }

    @staticmethod
    def free_recall_prompt(topic: str) -> Dict[str, Any]:
        """自由回忆提示"""
        return {
            "method": "生成效应 - 自由回忆",
            "description": "合上书本，尽可能多地写下你记住的内容",
            "prompt": f"请在30秒内写出关于'{topic}'你记住的所有内容",
            "tip": "这是最强大的学习方法之一！研究表明自由回忆比重复阅读有效得多",
        }


class LearningMethodOrchestratorV3:
    """学习方法编排器 v3：整合所有新方法"""

    @staticmethod
    def recommend_for_mastery_level(mastery: float, topic: str, sub_topics: List[str]) -> Dict[str, Any]:
        """根据掌握程度推荐学习方法"""
        if mastery < 0.3:
            methods = [
                DualCodingEngine.get_visual_prompt(topic),
                {"method": "基础", "tip": "先用双重编码打好基础，建立知识图像"},
            ]
        elif mastery < 0.6:
            methods = [
                ElaborationEngine.get_elaboration_prompt(topic),
                ElaborationEngine.generate_analogy(topic),
            ]
        elif mastery < 0.8:
            methods = [
                InterleavingEngine.generate_interleaved_plan(sub_topics),
                GenerationEffectEngine.free_recall_prompt(topic),
            ]
        else:
            methods = [
                MindMappingEngine.generate_knowledge_map(topic, sub_topics),
                GenerationEffectEngine.free_recall_prompt(topic),
            ]
        
        return {
            "mastery": mastery,
            "recommended_methods": methods,
            "tip": "不同掌握阶段适用不同方法：基础→精细加工→交错练习→思维导图",
        }

    @staticmethod
    def get_loading_tip() -> str:
        """获取加载时的学习方法提示"""
        tips = [
            "🧠 思维导图：用可视化方式组织知识，比线性笔记记忆效果高30%",
            "👁️ 双重编码：同时使用文字和图像，记忆更牢固！",
            "🔀 交错练习：混合不同知识点练习，长期记忆效果更好",
            "📝 精细加工：用自己的话解释知识，真正理解而非死记硬背",
            "✍️ 生成效应：主动回忆比被动阅读效果好2-3倍",
            "🎯 峰终定律：学习结束时保持积极体验，明天更愿意回来",
            "🎪 惊喜奖励：随机彩蛋让学习更有趣，激活多巴胺系统",
            "🔰 蔡格尼克效应：未完成的任务会被大脑记住，驱动你回来完成",
            "📅 新起点效应：周一和月初是最佳的开始时机",
        ]
        return random.choice(tips)
