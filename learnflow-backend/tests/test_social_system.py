"""社交成瘾/名片/家长门户/虚拟礼物系统测试"""
import pytest


class TestBusinessCardEngine:
    def test_create_card(self):
        from app.services.social_addiction_engine import BusinessCardEngine
        card = BusinessCardEngine.create_card("u1", "小明", "forming")
        assert card.display_name == "小明"
        assert card.title != ""

    def test_update_from_stats(self):
        from app.services.social_addiction_engine import BusinessCardEngine, BusinessCard
        card = BusinessCard(user_id="u1", display_name="小明")
        stats = {
            "current_streak": 8,
            "topics_mastered": 3,
            "help_others": 2,
            "total_minutes": 300,
            "pet_level": 4,
            "level": 5,
            "badges_collected": [{"name": "坚持者", "rarity": "common"}, {"name": "夜猫子", "rarity": "secret"}],
            "addiction_stage": "hooked",
        }
        updated = BusinessCardEngine.update_from_stats(card, stats)
        assert updated.streak_display == 8
        assert updated.total_mastered_topics == 3
        assert updated.rarest_badge == "夜猫子"
        assert updated.avatar_frame == "silver"

    def test_to_display_json(self):
        from app.services.social_addiction_engine import BusinessCardEngine, BusinessCard
        card = BusinessCard(user_id="u1", display_name="小明", streak_display=15)
        json_data = BusinessCardEngine.to_display_json(card)
        assert "display_name" in json_data
        assert "signals" in json_data
        assert json_data["signals"]["streak"] == 15

    def test_avatar_frame_progression(self):
        from app.services.social_addiction_engine import BusinessCardEngine, BusinessCard
        card = BusinessCard(user_id="u1", display_name="小明")
        stats = {"current_streak": 30, "topics_mastered": 0, "help_others": 0,
                 "total_minutes": 0, "pet_level": 1, "level": 1,
                 "badges_collected": [], "addiction_stage": "exploring"}
        updated = BusinessCardEngine.update_from_stats(card, stats)
        assert updated.avatar_frame == "diamond"


class TestSocialAddictionEngine:
    def test_cheer_peer(self):
        from app.services.social_addiction_engine import SocialAddictionEngine, SocialProfile
        sender = SocialProfile(user_id="u1", display_name="小明")
        receiver = SocialProfile(user_id="u2", display_name="小红")
        result = SocialAddictionEngine.cheer_peer("u1", "u2", sender, receiver)
        assert result["action"] == "cheer_sent"
        assert sender.cheers_given == 1
        assert receiver.cheers_received == 1
        assert result["social_validation"]

    def test_social_score(self):
        from app.services.social_addiction_engine import SocialAddictionEngine, SocialProfile
        profile = SocialProfile(user_id="u1", display_name="小明",
                                 cheers_received=10, cheers_given=5,
                                 helped_others=3, recognition_badges=["helper", "mentor"])
        score = SocialAddictionEngine.calculate_social_score(profile)
        assert score > 20

    def test_peer_suggestions(self):
        from app.services.social_addiction_engine import SocialAddictionEngine
        peers = [
            {"id": "u2", "name": "小红", "streak": 8, "needs_help": False, "stage": "forming",
             "my_stage": "forming"},
            {"id": "u3", "name": "小刚", "streak": 0, "needs_help": False, "stage": "exploring",
             "my_stage": "forming"},
        ]
        suggestions = SocialAddictionEngine.get_peer_suggestions("u1", peers, [])
        assert len(suggestions) <= 5
        assert len(suggestions) >= 1


class TestParentPortalEngine:
    def test_weekly_digest(self):
        from app.services.social_addiction_engine import ParentPortalEngine
        digest = ParentPortalEngine.generate_weekly_digest(
            "小明", {
                "current_streak": 7,
                "weekly_accuracy": 85,
                "weekly_questions": 35,
                "addiction_stage": "forming",
                "new_topic_mastered": "分数运算",
                "weak_topics": ["几何"],
                "daily_minutes": 45,
            }, "小豆")
        assert "小明" in digest["summary"]
        assert len(digest["highlights"]) >= 1
        assert digest["addiction_report"]["is_positive"]

    def test_teacher_message_progress(self):
        from app.services.social_addiction_engine import ParentPortalEngine
        msg = ParentPortalEngine.generate_teacher_message_template(
            "小明", "progress", {"topic": "分数运算", "before": "60%", "after": "85%"})
        assert "进步" in msg["subject"]

    def test_teacher_message_addiction_good(self):
        from app.services.social_addiction_engine import ParentPortalEngine
        msg = ParentPortalEngine.generate_teacher_message_template(
            "小明", "addiction_good", {"streak": 14})
        assert "爱上学习" in msg["subject"]

    def test_parent_actions(self):
        from app.services.social_addiction_engine import ParentPortalEngine
        digest = ParentPortalEngine.generate_weekly_digest(
            "小明", {"current_streak": 5, "helped_peer": True}, "小豆")
        actions = digest["parent_action_items"]
        assert len(actions) > 0


class TestGiftEconomyEngine:
    def test_can_send_gift_yes(self):
        from app.services.social_addiction_engine import GiftEconomyEngine
        result = GiftEconomyEngine.can_send_gift(7, "star")
        assert result["can_send"]

    def test_can_send_gift_no(self):
        from app.services.social_addiction_engine import GiftEconomyEngine
        result = GiftEconomyEngine.can_send_gift(0, "trophy")
        assert not result["can_send"]

    def test_send_gift(self):
        from app.services.social_addiction_engine import GiftEconomyEngine
        result = GiftEconomyEngine.send_gift("小明", "小红", "star")
        assert "小明" in result["message"]
        assert "小红" in result["message"]

    def test_expensive_gift_costs_real_streak(self):
        from app.services.social_addiction_engine import GiftEconomyEngine
        result = GiftEconomyEngine.can_send_gift(3, "crystal")
        assert not result["can_send"]
        assert "need_more" in result
