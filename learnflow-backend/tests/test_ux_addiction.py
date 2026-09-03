"""UI上瘾设计系统测试"""
import pytest


class TestMicroInteractionEngine:
    def test_answer_submit_correct(self):
        from app.services.ux_addiction_engine import MicroInteractionEngine
        spec = MicroInteractionEngine.get_interaction_spec("answer_submit")
        assert "spec" in spec
        assert "success" in spec["spec"]

    def test_answer_submit_streak_boost(self):
        from app.services.ux_addiction_engine import MicroInteractionEngine
        spec = MicroInteractionEngine.get_interaction_spec("answer_submit", {"streak": 7})
        assert spec["spec"]["success"]["particles"] > 12

    def test_loading_anticipation(self):
        from app.services.ux_addiction_engine import MicroInteractionEngine
        spec = MicroInteractionEngine.generate_loading_anticipation(1500)
        assert spec["type"] == "educational_loader"
        assert "tip" in spec

    def test_instant_loading(self):
        from app.services.ux_addiction_engine import MicroInteractionEngine
        spec = MicroInteractionEngine.generate_loading_anticipation(300)
        assert spec["type"] == "instant"


class TestProgressiveDisclosureEngine:
    def test_first_session_minimal_ui(self):
        from app.services.ux_addiction_engine import ProgressiveDisclosureEngine
        state = ProgressiveDisclosureEngine.get_disclosure_state(1)
        assert "basic_ui" in state["revealed_features"]
        assert state["hidden_count"] > 3

    def test_tenth_session_more_unlocked(self):
        from app.services.ux_addiction_engine import ProgressiveDisclosureEngine
        state = ProgressiveDisclosureEngine.get_disclosure_state(10)
        assert "challenge_mode" in state["revealed_features"]

    def test_full_unlock_at_30(self):
        from app.services.ux_addiction_engine import ProgressiveDisclosureEngine
        state = ProgressiveDisclosureEngine.get_disclosure_state(30)
        assert "all_unlocked" in state["revealed_features"]

    def test_reveal_moment(self):
        from app.services.ux_addiction_engine import ProgressiveDisclosureEngine
        moment = ProgressiveDisclosureEngine.generate_reveal_moment("pet_intro")
        assert "animation" in moment


class TestColorPsychologyEngine:
    def test_success_palette(self):
        from app.services.ux_addiction_engine import ColorPsychologyEngine
        palette = ColorPsychologyEngine.get_theme_for_context("success")
        assert palette["emotion"] == "achievement"

    def test_gradient_pair(self):
        from app.services.ux_addiction_engine import ColorPsychologyEngine
        gradient = ColorPsychologyEngine.generate_gradient_pair("motivation")
        assert "start" in gradient and "end" in gradient

    def test_emotional_palette(self):
        from app.services.ux_addiction_engine import ColorPsychologyEngine
        palette = ColorPsychologyEngine.get_emotional_palette("proud")
        assert "accent" in palette


class TestSpatialAnchoringEngine:
    def test_layout_spec(self):
        from app.services.ux_addiction_engine import SpatialAnchoringEngine
        spec = SpatialAnchoringEngine.get_layout_spec()
        assert "zones" in spec
        assert "primary_action" in spec["zones"]

    def test_gesture_spec(self):
        from app.services.ux_addiction_engine import SpatialAnchoringEngine
        spec = SpatialAnchoringEngine.get_gesture_spec()
        assert "swipe_left" in spec
        assert spec["swipe_left"]["action"] == "next_question"


class TestHapticRhythmEngine:
    def test_correct_haptic(self):
        from app.services.ux_addiction_engine import HapticRhythmEngine
        result = HapticRhythmEngine.get_haptic_for_event("correct_answer")
        assert len(result["pattern"]) > 0

    def test_streak_haptic(self):
        from app.services.ux_addiction_engine import HapticRhythmEngine
        result = HapticRhythmEngine.get_haptic_for_event("correct_answer", streak=6)
        assert len(result["pattern"]) > 1  # 连对振动更复杂

    def test_idle_haptic_short(self):
        from app.services.ux_addiction_engine import HapticRhythmEngine
        result = HapticRhythmEngine.get_idle_haptic(10)
        assert result is None

    def test_idle_haptic_long(self):
        from app.services.ux_addiction_engine import HapticRhythmEngine
        result = HapticRhythmEngine.get_idle_haptic(45)
        assert result is not None


class TestEmptyStateEngine:
    def test_no_questions(self):
        from app.services.ux_addiction_engine import EmptyStateEngine
        state = EmptyStateEngine.get_empty_state("no_questions_done")
        assert "开始" in state["cta"]

    def test_almost_there(self):
        from app.services.ux_addiction_engine import EmptyStateEngine
        state = EmptyStateEngine.get_almost_there_state("almost_daily_goal", 3)
        assert "差3" in state["title"] or "只差" in state["title"]


class TestSonicBrandingEngine:
    def test_correct_sound(self):
        from app.services.ux_addiction_engine import SonicBrandingEngine
        sound = SonicBrandingEngine.get_sound_for_event("correct")
        assert sound["sound"] == "bright_confirm"

    def test_streak_sound(self):
        from app.services.ux_addiction_engine import SonicBrandingEngine
        sound = SonicBrandingEngine.get_sound_for_event("correct", streak=6)
        assert "streak" in sound["sound"] or "celebration" in sound["sound"]

    def test_silent_mode_alternative(self):
        from app.services.ux_addiction_engine import SonicBrandingEngine
        alt = SonicBrandingEngine.get_silent_mode_alternative("correct")
        assert "visual" in alt


class TestTypographyKineticEngine:
    def test_streak_counter_animation(self):
        from app.services.ux_addiction_engine import TypographyKineticEngine
        spec = TypographyKineticEngine.get_animated_text_spec("streak_counter")
        assert spec["animation"] == "tick_up"
        assert spec["final_pulse"]

    def test_xp_gain_animation(self):
        from app.services.ux_addiction_engine import TypographyKineticEngine
        spec = TypographyKineticEngine.get_animated_text_spec("xp_gain")
        assert spec["animation"] == "float_up_and_fade"


class TestAddictionUxOrchestrator:
    def test_answer_ux_spec_correct(self):
        from app.services.ux_addiction_engine import AddictionUxOrchestrator
        spec = AddictionUxOrchestrator.generate_answer_ux_spec(True, 0, "小豆")
        assert "micro_interaction" in spec
        assert "color_theme" in spec
        assert "haptic" in spec
        assert "sound" in spec

    def test_answer_ux_spec_with_progress(self):
        from app.services.ux_addiction_engine import AddictionUxOrchestrator
        spec = AddictionUxOrchestrator.generate_answer_ux_spec(
            True, 3, "小豆", session_progress=0.85)
        # 进度80%+应触发almost_there
        assert spec.get("almost_there") is not None

    def test_session_complete_ux_spec(self):
        from app.services.ux_addiction_engine import AddictionUxOrchestrator
        spec = AddictionUxOrchestrator.generate_session_complete_ux_spec(
            {"next_topic": "几何", "next_difficulty": 6}, "小豆")
        assert len(spec["animation_sequence"]) == 4

    def test_idle_ux_spec(self):
        from app.services.ux_addiction_engine import AddictionUxOrchestrator
        spec = AddictionUxOrchestrator.generate_idle_ux_spec(20)
        assert "小豆" in spec["message"]
