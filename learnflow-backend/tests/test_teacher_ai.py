"""教师AI助手 + 前端架构测试"""
import pytest


class TestTeacherAIAssistant:
    def test_analyze_student(self):
        from app.services.teacher_ai_assistant import TeacherAIAssistant, StudentAnalysisReport
        report = TeacherAIAssistant.analyze_student(
            {"id": "s1", "name": "小明", "grade": "五年级"},
            {
                "avg_mastery": 0.65,
                "skill_scores": {"分数": 0.8, "几何": 0.3, "代数": 0.6},
                "recent_accuracy": [1.0, 1.0, 0.0, 1.0, 1.0],
                "current_streak": 3,
                "weekly_attempts": 35,
                "avg_difficulty": 5,
                "skip_ratio": 0.1,
                "help_others": 2,
                "hook_loops": 25,
                "total_attempts": 120,
                "identity_labels": ["坚持者", "分享者"],
                "identity_count": 2,
            }
        )
        assert report.student_name == "小明"
        assert report.overall_mastery == 0.65
        assert report.strongest_skill == "分数"
        assert report.weakest_skill == "几何"
        assert report.addiction_stage in ["exploring", "forming", "hooked", "automated"]
        assert len(report.identity_labels) >= 1

    def test_analyze_risk_red(self):
        from app.services.teacher_ai_assistant import TeacherAIAssistant
        report = TeacherAIAssistant.analyze_student(
            {"id": "s2", "name": "小红", "grade": "五年级"},
            {
                "avg_mastery": 0.2,
                "skill_scores": {"分数": 0.2},
                "recent_accuracy": [0.0, 0.0, 0.0, 0.0, 0.0],
                "current_streak": 0,
                "weekly_attempts": 3,
                "avg_difficulty": 2,
                "skip_ratio": 0.5,
                "consecutive_failures": 6,
                "hook_loops": 0,
                "total_attempts": 80,
                "identity_labels": [],
                "identity_count": 0,
            }
        )
        assert report.risk_level == "red"
        assert report.needs_attention
        assert report.recommended_action == "intervention"

    def test_calculate_engagement(self):
        from app.services.teacher_ai_assistant import TeacherAIAssistant
        eng = TeacherAIAssistant._calculate_engagement({
            "current_streak": 10,
            "weekly_attempts": 35,
            "hook_loops": 25,
            "help_others": 3,
            "identity_count": 3,
        })
        assert eng > 0.5

    def test_addiction_stage(self):
        from app.services.teacher_ai_assistant import TeacherAIAssistant
        assert TeacherAIAssistant._assess_addiction_stage({"hook_loops": 100, "current_streak": 30}) == "automated"
        assert TeacherAIAssistant._assess_addiction_stage({"hook_loops": 30, "current_streak": 7}) == "hooked"
        assert TeacherAIAssistant._assess_addiction_stage({"hook_loops": 5, "current_streak": 3}) == "forming"

    def test_suggest_difficulty_adjustment(self):
        from app.services.teacher_ai_assistant import TeacherAIAssistant
        result = TeacherAIAssistant.suggest_difficulty_adjustment("s1", 5, 0.9, 0.9)
        assert result["suggested_difficulty"] > 5
        assert result["confidence"] > 0.8
        assert result["teacher_can_override"]

    def test_suggest_difficulty_down(self):
        from app.services.teacher_ai_assistant import TeacherAIAssistant
        result = TeacherAIAssistant.suggest_difficulty_adjustment("s1", 5, 0.2, 0.3)
        assert result["suggested_difficulty"] < 5

    def test_trend_detection(self):
        from app.services.teacher_ai_assistant import TeacherAIAssistant
        assert TeacherAIAssistant._detect_trend([0.5, 0.6, 0.7, 0.8]) == "improving"
        assert TeacherAIAssistant._detect_trend([0.8, 0.7, 0.6, 0.5]) == "declining"
        assert TeacherAIAssistant._detect_trend([0.6, 0.61, 0.6, 0.62]) == "stable"

    def test_analyze_classroom(self):
        from app.services.teacher_ai_assistant import TeacherAIAssistant, ClassAnalysisReport
        students = [
            {"name": "A", "overall_mastery": 0.9, "trend_score": 0.95, "hook_loops": 50, "total_attempts": 200},
            {"name": "B", "overall_mastery": 0.3, "trend_score": 0.3, "hook_loops": 5, "total_attempts": 30},
        ]
        class_stats = {
            "total_students": 2, "active_today": 2, "class_avg_mastery": 0.6,
            "topic_mastery": {"math": 0.6},
            "topic_difficulty": {}, "difficulty_distribution": {},
            "most_active_hour": "19:00", "weekend_ratio": 0.3,
        }
        report = TeacherAIAssistant.analyze_classroom(students, class_stats)
        assert report.total_students == 2
        assert report.avg_mastery == 0.6
        assert report.most_improving_student == "A"
        assert len(report.class_wide_suggestions) >= 1

    def test_batch_adjust_difficulty(self):
        from app.services.teacher_ai_assistant import TeacherAIAssistant
        students = [
            {"id": "s1", "current_difficulty": 5, "bkt_mastery": 0.9, "recent_accuracy": 0.9},
            {"id": "s2", "current_difficulty": 5, "bkt_mastery": 0.2, "recent_accuracy": 0.3},
        ]
        results = TeacherAIAssistant.batch_adjust_difficulty(students)
        assert len(results) == 2
        assert results[0]["suggested_difficulty"] > 5
        assert results[1]["suggested_difficulty"] < 5


class TestFrontendSeparation:
    """验证前端分层的 API 设计完整性"""

    def test_student_endpoints_exist(self):
        """学生端应有完整端点"""
        from app.api.student import router
        paths = [r.path for r in router.routes]
        assert any("dashboard" in p for p in paths)
        assert any("next-task" in p for p in paths)
        assert any("submit" in p for p in paths)

    def test_teacher_endpoints_exist(self):
        """教师端应有完整端点"""
        from app.api.teacher import router
        paths = [r.path for r in router.routes]
        assert any("classroom" in p for p in paths)
        assert any("student" in p for p in paths)
        assert any("ai/" in p for p in paths)

    def test_teacher_ai_endpoints(self):
        """教师AI端点应有classroom-analysis, student-analysis, difficulty-suggestions"""
        from app.api.teacher import router
        paths = [r.path for r in router.routes]
        assert any("ai/classroom-analysis" in p for p in paths)
        assert any("ai/student-analysis" in p for p in paths)
        assert any("ai/difficulty-suggestions" in p for p in paths)
        assert any("ai/intervention-plan" in p for p in paths)
