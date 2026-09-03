"""UI 上瘾设计系统 — Backend Specification Engine

基于 UX 行为设计的界面成瘾机制。
每一个交互都是一个微型 Hook 循环。

设计原则:
  1. 美学可用性效应 (Aesthetic-Usability) — 好看的=好用的
  2. 微交互闭环 (Micro-interaction) — 每点击一次都有完整反馈
  3. 渐进揭示 (Progressive Disclosure) — 不要一次给太多
  4. 空间锚定 (Spatial Anchoring) — 按钮在固定位置形成肌肉记忆
  5. 色彩心理学 — 暖色激励 / 冷色信任 / 中性安全
  6. 触觉节奏 (Haptic Rhythm) — 成功-休息-期待的循环
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, List, Optional
import random


# ═══════════════════════════════════════════════════════════
# 1. 微交互编排引擎 — Micro-Interaction Orchestrator
# ═══════════════════════════════════════════════════════════

class MicroInteractionEngine:
    """微交互编排

    每一个用户操作都是一个微交互闭环:
    Trigger(触发) → Rules(规则) → Feedback(反馈) → Loops(循环)

    目标: 让每个点击都有"咔嗒"一样的满足感。
    """

    INTERACTION_PATTERNS = {
        "answer_submit": {
            "trigger": {"animation": "button_press_depth", "duration_ms": 100, "scale": 0.97},
            "processing": {"animation": "thinking_ripple", "duration_ms": 400, "color": "#F5A623"},
            "success": {"animation": "correct_explosion", "particles": 12, "color": "#4CAF50", "duration_ms": 800, "haptic": "light"},
            "failure": {"animation": "gentle_shake", "amplitude": 4, "duration_ms": 500, "haptic": "warning"},
            "near_miss": {"animation": "pulse_glow", "color": "#FF9800", "duration_ms": 1000, "haptic": "double_light"},
        },
        "next_question": {
            "trigger": {"animation": "card_slide_transition", "direction": "from_right", "duration_ms": 300, "easing": "cubic-bezier(0.16,1,0.3,1)"},
        },
        "level_up": {
            "trigger": {"animation": "celebration_burst", "confetti": True, "particles": 30, "duration_ms": 2000},
            "process": {"animation": "bar_fill_glow", "color": "#FFD700", "duration_ms": 1000},
            "complete": {"animation": "badge_pop", "scale": 1.2, "bounce": True, "duration_ms": 600},
        },
        "pet_interaction": {
            "trigger": {"animation": "pet_bounce", "amplitude": 8, "duration_ms": 400, "easing": "spring"},
            "response": {"animation": "pet_emote", "emote_duration_ms": 2000, "hairstyle": "react"},
        },
        "daily_login": {
            "trigger": {"animation": "greeting_sequence", "steps": ["fade_in", "pet_wave", "streak_show"]},
            "streak_show": {"animation": "counter_tick_up", "duration_per_digit_ms": 150, "final_pulse": True},
        },
        "idle_state": {
            "trigger": {"animation": "pet_idle_loop", "actions": ["blink", "tail_wag", "look_around", "sleepy"],
                         "interval_seconds": [3, 5, 8, 15]},
        },
    }

    @classmethod
    def get_interaction_spec(cls, interaction_type: str, context: dict = None) -> dict:
        """获取微交互规格 — 前端直接根据这个渲染"""
        pattern = cls.INTERACTION_PATTERNS.get(interaction_type, {})

        # 动态调整反馈强度
        context = context or {}
        streak = context.get("streak", 0)
        if interaction_type == "answer_submit" and streak >= 5:
            pattern = dict(pattern)
            if "success" in pattern:
                pattern["success"] = dict(pattern["success"])
                pattern["success"]["particles"] = min(30, pattern["success"]["particles"] + streak)
                pattern["success"]["duration_ms"] += 200

        return {
            "interaction_type": interaction_type,
            "spec": pattern,
            "accessibility": {
                "prefers_reduced_motion": "reduce animations by 70%",
                "high_contrast_mode": "use solid borders instead of shadows",
            },
        }

    @classmethod
    def generate_loading_anticipation(cls, estimated_ms: int) -> dict:
        """生成加载期待 — 把等待变成悬念

        无聊的 loading = 流失
        有趣的 loading = 期待
        """
        if estimated_ms < 500:
            return {"type": "instant", "animation": "none"}

        tips = [
            "你知道吗？大脑在你休息时学得最快。",
            "每一个数学家的第一步都是1+1。",
            "你正在创造新的神经连接...",
            "学习让大脑分泌的BDNF是慢跑时的3倍。",
            "下一题来自一个古老的知识体系...",
        ]

        return {
            "type": "educational_loader",
            "animation": "pulsing_dots",
            "tip": random.choice(tips),
            "tip_rotation_ms": 2000,
            "progress_indicator": "brain_growing",  # 大脑图标在变大
            "estimated_ms": estimated_ms,
        }


# ═══════════════════════════════════════════════════════════
# 2. 渐进揭示引擎 — Progressive Disclosure
# ═══════════════════════════════════════════════════════════

class ProgressiveDisclosureEngine:
    """渐进揭示

    不要一次性展示所有功能 → 在用户准备好的时候才展示。
    每一步揭示都是一个"小惊喜"。
    """

    DISCLOSURE_LADDER = [
        {"session": 1, "reveal": "basic_ui", "message": "开始你的第一道题"},
        {"session": 2, "reveal": "pet_intro", "message": "这是你的学习伙伴——小豆！它会陪你一起成长。"},
        {"session": 3, "reveal": "streak_tracker", "message": "看看你的学习记录——你已经坚持3天了！"},
        {"session": 5, "reveal": "topic_map", "message": "你的知识版图已经展开——看看你掌握了什么。"},
        {"session": 7, "reveal": "class_insight", "message": "想看看其他同学的学习方式吗？（匿名数据）"},
        {"session": 10, "reveal": "challenge_mode", "message": "你已经准备好迎接挑战模式了！"},
        {"session": 14, "reveal": "create_path", "message": "现在你可以创建自己的学习路径了。"},
        {"session": 21, "reveal": "become_helper", "message": "你可以帮助新同学了。教学相长。"},
        {"session": 30, "reveal": "all_unlocked", "message": "所有功能已解锁。你是学习的主人。"},
    ]

    @classmethod
    def get_disclosure_state(cls, session_count: int) -> dict:
        """根据会话数返回当前应展示的功能"""
        revealed = []
        next_reveal = None

        for step in cls.DISCLOSURE_LADDER:
            if session_count >= step["session"]:
                revealed.append(step["reveal"])
            elif next_reveal is None:
                next_reveal = step

        return {
            "revealed_features": revealed,
            "hidden_count": len(cls.DISCLOSURE_LADDER) - len(revealed),
            "next_reveal": next_reveal,
            "session_count": session_count,
        }

    @classmethod
    def generate_reveal_moment(cls, feature: str, pet_name: str = "小豆") -> dict:
        """生成揭示时刻 — 每次解锁新功能都是一次小惊喜"""
        moments = {
            "pet_intro": {
                "title": "认识你的学习伙伴",
                "animation": "pet_hatching",
                "duration_ms": 3000,
                "message": f"从蛋里孵出了 {pet_name}！它会根据你的学习表现成长和变化。",
                "dismissible": False,
            },
            "streak_tracker": {
                "title": "连续学习记录已解锁",
                "animation": "fire_ignite",
                "duration_ms": 2000,
                "message": "每次学习都会延长你的记录。记录越长，越不想让它断掉。",
                "dismissible": True,
            },
            "topic_map": {
                "title": "知识版图展开",
                "animation": "map_unfold",
                "duration_ms": 2500,
                "message": "这是你的知识版图。每一个被你点亮的区域，都是你掌握的知识。",
                "dismissible": True,
            },
            "challenge_mode": {
                "title": "挑战模式已激活",
                "animation": "sword_unsheath",
                "duration_ms": 2000,
                "message": "你已经准备好了。挑战模式会给你更难但更快的成长。",
                "dismissible": True,
            },
            "become_helper": {
                "title": "你可以帮助他人了",
                "animation": "light_spread",
                "duration_ms": 3000,
                "message": "最好的学习方式是教别人。现在你可以帮助遇到困难的同学。",
                "dismissible": False,
            },
        }
        return moments.get(feature, {
            "title": "新功能解锁",
            "animation": "sparkle_reveal",
            "duration_ms": 1500,
            "message": "探索新功能",
            "dismissible": True,
        })


# ═══════════════════════════════════════════════════════════
# 3. 色彩心理学引擎 — Color Psychology
# ═══════════════════════════════════════════════════════════

class ColorPsychologyEngine:
    """色彩心理学

    颜色直接影响情绪和决策。
    用于微调界面氛围以增强学习动机。
    """

    # 色彩配置 — 学习界面专用
    COLOR_PALETTE = {
        "success": {
            "primary": "#4CAF50",
            "secondary": "#A5D6A7",
            "bg": "rgba(76,175,80,0.08)",
            "emotion": "achievement",
        },
        "near_miss": {
            "primary": "#FF9800",
            "secondary": "#FFCC80",
            "bg": "rgba(255,152,0,0.08)",
            "emotion": "anticipation",
        },
        "encourage": {
            "primary": "#42A5F5",
            "secondary": "#90CAF9",
            "bg": "rgba(66,165,245,0.08)",
            "emotion": "support",
        },
        "rare": {
            "primary": "#9C27B0",
            "secondary": "#CE93D8",
            "bg": "rgba(156,39,176,0.1)",
            "emotion": "excitement",
        },
        "legendary": {
            "primary": "#FFD700",
            "secondary": "#FFF176",
            "bg": "rgba(255,215,0,0.12)",
            "emotion": "awe",
        },
        "progress": {
            "primary": "#00BCD4",
            "secondary": "#80DEEA",
            "bg": "rgba(0,188,212,0.06)",
            "emotion": "momentum",
        },
    }

    @classmethod
    def get_theme_for_context(cls, context: str) -> dict:
        """根据场景返回色彩主题"""
        return cls.COLOR_PALETTE.get(context, cls.COLOR_PALETTE["progress"])

    @classmethod
    def generate_gradient_pair(cls, mood: str) -> dict:
        """生成渐变色对 — 用于按钮、卡片、背景"""
        gradients = {
            "motivation": {"start": "#667eea", "end": "#764ba2", "angle": 135},
            "achievement": {"start": "#f093fb", "end": "#f5576c", "angle": 45},
            "focus": {"start": "#4facfe", "end": "#00f2fe", "angle": 90},
            "warmth": {"start": "#fa709a", "end": "#fee140", "angle": 180},
            "growth": {"start": "#43e97b", "end": "#38f9d7", "angle": 135},
        }
        return gradients.get(mood, gradients["motivation"])

    @classmethod
    def get_emotional_palette(cls, emotion: str) -> dict:
        """情感→色彩映射"""
        palettes = {
            "proud": {"bg": "#FFF8E1", "accent": "#FFB300", "text": "#4E342E"},
            "curious": {"bg": "#E8EAF6", "accent": "#5C6BC0", "text": "#1A237E"},
            "determined": {"bg": "#FCE4EC", "accent": "#EC407A", "text": "#880E4F"},
            "calm": {"bg": "#E0F7FA", "accent": "#00ACC1", "text": "#004D40"},
        }
        return palettes.get(emotion, {"bg": "#FFFFFF", "accent": "#1976D2", "text": "#212121"})


# ═══════════════════════════════════════════════════════════
# 4. 空间锚定引擎 — Spatial Anchoring
# ═══════════════════════════════════════════════════════════

class SpatialAnchoringEngine:
    """空间锚定

    按钮放在固定位置 → 肌肉记忆 → 不需要思考就能操作。
    降低认知负担 = 提高使用频率。
    """

    ANCHOR_ZONES = {
        "primary_action": {
            "position": "bottom_center",
            "size": "large",
            "label": "答题/继续",
            "priority": "highest",
            "finger_zone": "thumb_reach",  # 大拇指最容易触碰的位置
        },
        "secondary_action": {
            "position": "bottom_right",
            "size": "medium",
            "label": "提示/跳过",
            "priority": "medium",
        },
        "tertiary_action": {
            "position": "top_right",
            "size": "small",
            "label": "菜单/设置",
            "priority": "low",
        },
    }

    @classmethod
    def get_layout_spec(cls) -> dict:
        """获取空间布局规范"""
        return {
            "zones": cls.ANCHOR_ZONES,
            "principle": "thumb_zone_optimization",
            "explanation": "主要操作放在拇指最容易到达的位置（屏幕底部中央）",
            "consistency_rule": "所有页面的主操作按钮保持在相同位置",
        }

    @classmethod
    def get_gesture_spec(cls) -> dict:
        """手势规范 — 减少点击，增加流畅感"""
        return {
            "swipe_left": {"action": "next_question", "resistance": "low"},
            "swipe_right": {"action": "previous_question", "resistance": "medium"},
            "swipe_up": {"action": "show_explanation", "resistance": "medium"},
            "long_press": {"action": "pet_interaction", "resistance": "low", "duration_ms": 500},
            "double_tap": {"action": "quick_answer_select", "resistance": "low"},
        }


# ═══════════════════════════════════════════════════════════
# 5. 触觉节奏引擎 — Haptic Rhythm
# ═══════════════════════════════════════════════════════════

class HapticRhythmEngine:
    """触觉节奏引擎

    手机的振动反馈形成"触觉旋律"。
    正确的回答有轻快的振动，错误有温柔的提醒。
    触觉=情感的直接传递。
    """

    HAPTIC_PATTERNS = {
        "correct_answer": {
            "pattern": [50],  # 一次短振动
            "intensity": "light",
            "description": "清脆的确认",
            "frequency_hz": 180,
        },
        "correct_streak": {
            "pattern": [30, 50, 80],  # 三连振动
            "intensity": "medium",
            "description": "兴奋的庆祝",
            "frequency_hz": 220,
        },
        "near_miss": {
            "pattern": [80, 30, 80],  # 长-短-长
            "intensity": "medium",
            "description": "差一点的提醒",
            "frequency_hz": 160,
        },
        "incorrect_answer": {
            "pattern": [100],  # 一次长振动
            "intensity": "light",
            "description": "温柔的提示",
            "frequency_hz": 120,
        },
        "level_up": {
            "pattern": [30, 30, 30, 80, 200],  # 哆-哆-哆-咪-嗦
            "intensity": "medium",
            "description": "升级旋律",
            "frequency_hz": 250,
        },
        "treasure_open": {
            "pattern": [20, 20, 20, 20, 20, 150],  # 快速的期待 + 长满足
            "intensity": "medium",
            "description": "宝箱开启",
            "frequency_hz": 200,
        },
    }

    @classmethod
    def get_haptic_for_event(cls, event: str, streak: int = 0) -> dict:
        """获取事件的触觉反馈模式"""
        if event == "correct_answer" and streak >= 5:
            return cls.HAPTIC_PATTERNS["correct_streak"]
        return cls.HAPTIC_PATTERNS.get(event, {"pattern": [50], "intensity": "light"})

    @classmethod
    def get_idle_haptic(cls, idle_seconds: int) -> Optional[dict]:
        """空闲触觉提醒"""
        if idle_seconds >= 30:
            return {"pattern": [200, 100], "intensity": "very_light",
                    "message": "小豆轻轻碰了碰你"}
        return None


# ═══════════════════════════════════════════════════════════
# 6. 空状态转化引擎 — Delightful Empty States
# ═══════════════════════════════════════════════════════════

class EmptyStateEngine:
    """空状态转化引擎

    把"什么都没有"变成"马上就有了"。
    空状态是最容易被忽视的转化机会。
    """

    @classmethod
    def get_empty_state(cls, context: str, pet_name: str = "小豆") -> dict:
        """获取空状态设计"""
        states = {
            "no_questions_done": {
                "illustration": "pet_sitting_alone",
                "title": "你还没有做过任何题目",
                "message": f"{pet_name}在这里等你。做第一道题，它就活过来了。",
                "cta": "开始第一题",
                "cta_style": "primary_glowing",  # 发光按钮
            },
            "no_topics_mastered": {
                "illustration": "empty_knowledge_map",
                "title": "知识版图还是一片空白",
                "message": "这不是空白，是无限的可能性。做完今天的题目，第一个知识点就会点亮。",
                "cta": "点亮第一个",
            },
            "streak_zero": {
                "illustration": "streak_calendar_empty",
                "title": "连续学习记录未开始",
                "message": "今天就是第一天。从今天开始，每一天都是一个点数，连成一条线。",
                "cta": "开始今天的点亮",
            },
            "no_badges": {
                "illustration": "trophy_case_empty",
                "title": "徽章展示柜空空的",
                "message": f"{pet_name}相信你很快就能填满它。每个徽章都有一个故事。",
                "cta": "去赢取第一个徽章",
            },
        }
        return states.get(context, states["no_questions_done"])

    @classmethod
    def get_almost_there_state(cls, context: str, remaining: int) -> dict:
        """"快完成了"状态 — 比空状态和满状态更激励人"""
        states = {
            "almost_daily_goal": {
                "illustration": "pet_cheering",
                "title": f"只差{remaining}题！",
                "message": f"再完成{remaining}题就达成今天的目标了。{remaining}题，你可以的。",
                "cta": "冲刺完成",
                "urgency": "high",
            },
            "almost_streak": {
                "illustration": "pet_counting_days",
                "title": f"再坚持{remaining}天就有里程碑！",
                "message": f"你已经很接近了。坚持{remaining}天，一个重要的里程碑在等你。",
                "cta": "现在学习",
            },
            "almost_collection": {
                "illustration": "incomplete_set",
                "title": f"还差{remaining}个徽章就成套了！",
                "message": "收藏家都知道：最后几个是最珍贵的。",
                "cta": "继续收集",
            },
        }
        return states.get(context, {"title": f"只差{remaining}", "message": "近在咫尺！"})


# ═══════════════════════════════════════════════════════════
# 7. 声音层设计 — Sonic Branding
# ═══════════════════════════════════════════════════════════

class SonicBrandingEngine:
    """声音品牌设计

    独特的声音=独特的记忆。
    听到那个"叮"就知道是LearnFlow。
    """

    SONIC_IDENTITY = {
        "app_open": {"sound": "gentle_ascend", "notes": "C-E-G", "duration_ms": 800, "instrument": "marimba"},
        "question_load": {"sound": "page_turn", "notes": "C", "duration_ms": 300, "instrument": "soft_paper"},
        "correct": {"sound": "bright_confirm", "notes": "C-E", "duration_ms": 400, "instrument": "bell"},
        "correct_streak": {"sound": "ascending_celebration", "notes": "C-E-G-C", "duration_ms": 800, "instrument": "chimes"},
        "near_miss": {"sound": "curious_tilt", "notes": "D-F", "duration_ms": 500, "instrument": "xylophone"},
        "incorrect": {"sound": "soft_drop", "notes": "A", "duration_ms": 300, "instrument": "soft_pad"},
        "level_up": {"sound": "victory_fanfare", "notes": "C-E-G-C-E", "duration_ms": 1500, "instrument": "orchestra"},
        "treasure_open": {"sound": "chest_reveal", "notes": "random_major", "duration_ms": 1200, "instrument": "harp"},
        "session_complete": {"sound": "peaceful_close", "notes": "G-E-C", "duration_ms": 2000, "instrument": "piano"},
        "idle_ambient": {"sound": "gentle_breeze", "notes": "pad", "duration_ms": "loop", "instrument": "synth_pad", "volume": 0.15},
    }

    @classmethod
    def get_sound_for_event(cls, event: str, streak: int = 0) -> dict:
        """获取事件音效"""
        if event == "correct" and streak >= 5:
            return cls.SONIC_IDENTITY["correct_streak"]
        return cls.SONIC_IDENTITY.get(event, {"sound": "gentle_click", "duration_ms": 200})

    @classmethod
    def get_silent_mode_alternative(cls, event: str) -> dict:
        """无声模式下的视觉替代"""
        alternatives = {
            "correct": {"visual": "screen_edge_glow", "color": "#4CAF50", "duration_ms": 400},
            "incorrect": {"visual": "subtle_pulse", "color": "#90CAF9", "duration_ms": 300},
            "level_up": {"visual": "full_screen_sparkle", "color": "#FFD700", "duration_ms": 1500},
        }
        return alternatives.get(event, {"visual": "pulse", "duration_ms": 200})


# ═══════════════════════════════════════════════════════════
# 8. 排版动力学 — Kinetic Typography
# ═══════════════════════════════════════════════════════════

class TypographyKineticEngine:
    """动感排版引擎

    文字不是静止的——它在跳动、呼吸、生长。
    每个字都可以是活的。
    """

    @classmethod
    def get_animated_text_spec(cls, text_type: str, value: int = 0) -> dict:
        """获取文字动画规格"""
        animations = {
            "streak_counter": {
                "animation": "tick_up",
                "character_delay_ms": 80,
                "easing": "cubic-bezier(0.34, 1.56, 0.64, 1)",  # overshoot
                "final_pulse": True,
                "font_weight_increase": True,
            },
            "xp_gain": {
                "animation": "float_up_and_fade",
                "duration_ms": 1200,
                "travel_distance": 40,
                "color": "#FFD700",
            },
            "score_increase": {
                "animation": "scale_bounce",
                "scale_from": 0.8,
                "scale_to": 1.15,
                "settle_to": 1.0,
                "duration_ms": 600,
            },
            "title_reveal": {
                "animation": "typewriter",
                "char_per_ms": 60,
                "cursor_blink": True,
            },
        }
        return animations.get(text_type, {"animation": "fade_in", "duration_ms": 300})

    @classmethod
    def get_feedback_text_animation(cls, sentiment: str) -> dict:
        """情感文字的动画方式"""
        styles = {
            "proud": {"animation": "gentle_float", "amplitude": 3, "duration_ms": 2000, "loop": True},
            "encourage": {"animation": "wave_in", "letter_delay": 30, "direction": "from_bottom"},
            "celebrate": {"animation": "confetti_text", "particles_per_char": 2, "duration_ms": 2500},
        }
        return styles.get(sentiment, {"animation": "fade_in", "duration_ms": 500})


# ═══════════════════════════════════════════════════════════
# 总成瘾界面编排器
# ═══════════════════════════════════════════════════════════

class AddictionUxOrchestrator:
    """成瘾界面总编排

    整合所有UI层引擎，为前端提供完整的体验规格。
    每个API响应都应包含 ux_spec 字段。
    """

    @classmethod
    def generate_answer_ux_spec(cls, is_correct: bool, streak: int,
                                  pet_name: str, is_near_miss: bool = False,
                                  session_progress: float = 0.0) -> dict:
        """生成题目提交后的完整UX规格"""
        event = "correct" if is_correct else ("near_miss" if is_near_miss else "incorrect")

        return {
            # 微交互
            "micro_interaction": MicroInteractionEngine.get_interaction_spec(
                "answer_submit", {"streak": streak}),
            # 色彩
            "color_theme": ColorPsychologyEngine.get_theme_for_context(
                "success" if is_correct else "near_miss" if is_near_miss else "encourage"),
            # 触觉
            "haptic": HapticRhythmEngine.get_haptic_for_event(
                f"{event}_answer", streak),
            # 声音
            "sound": SonicBrandingEngine.get_sound_for_event(event, streak),
            "silent_alternative": SonicBrandingEngine.get_silent_mode_alternative(event),
            # 动感文字
            "text_animation": TypographyKineticEngine.get_feedback_text_animation(
                "proud" if is_correct else "encourage"),
            # "完成了吗"检测
            "almost_there": cls._check_almost_there(session_progress),
            # 随机惊喜注入
            "serendipity": cls._inject_serendipity() if random.random() < 0.05 else None,
        }

    @classmethod
    def generate_session_complete_ux_spec(cls, stats: dict, pet_name: str) -> dict:
        """会话完成的UX规格"""
        return {
            "animation_sequence": [
                {"step": 1, "animation": "summary_card_slide", "duration_ms": 500},
                {"step": 2, "animation": "stats_counter_up", "duration_ms": 1000},
                {"step": 3, "animation": "pet_celebration", "duration_ms": 2000},
                {"step": 4, "animation": "cliffhanger_reveal", "duration_ms": 1500},
            ],
            "color_theme": ColorPsychologyEngine.generate_gradient_pair("achievement"),
            "sound": SonicBrandingEngine.get_sound_for_event("session_complete"),
            "haptic": HapticRhythmEngine.get_haptic_for_event("level_up"),
            "cliffhanger": CuriosityEngine.generate_cliffhanger(
                stats.get("next_topic", "新知识"), stats.get("next_difficulty", 5)),
        }

    @classmethod
    def _check_almost_there(cls, progress: float) -> Optional[dict]:
        if 0.7 <= progress < 1.0:
            return EmptyStateEngine.get_almost_there_state(
                "almost_daily_goal", max(1, round((1 - progress) * 10)))
        return None

    @classmethod
    def _inject_serendipity(cls) -> dict:
        from app.services.deep_addiction_engine import SerendipityEngine
        return SerendipityEngine.roll_serendipity()

    @classmethod
    def generate_idle_ux_spec(cls, idle_seconds: int) -> dict:
        """空闲状态UX规格 — 让离开也有吸引力"""
        haptic = HapticRhythmEngine.get_idle_haptic(idle_seconds)
        return {
            "animation": MicroInteractionEngine.INTERACTION_PATTERNS["idle_state"]["trigger"],
            "haptic": haptic,
            "message": f"小豆等了你{idle_seconds}秒了..." if idle_seconds >= 15 else "",
        }


# Import from deep_addiction_engine for CuriosityEngine reference
from app.services.deep_addiction_engine import CuriosityEngine
