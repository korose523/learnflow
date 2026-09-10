"""班级宠物园（LF-M54）单元测试 —— 积分养宠核心逻辑

验证真实「班级电子养宠」语义：
- 每生一只专属宠物（PetProfile），用行为积分喂养升级、进化形态；
- 负分使宠物「饿肚子」（starvation_risk）；
- 班级宠物园聚合视图（排行榜 / 形态分布 / 凝聚力 / 连接质量）。
"""
import pytest

from app.models.pet import PetProfile
from app.services.class_pet_service import ClassPetService


def _pet(level: int = 1, collaboration: float = 50.0,
        understanding: float = 50.0, persistence: float = 50.0,
        creativity: float = 50.0) -> PetProfile:
    p = PetProfile(user_id=f"u_{level}_{collaboration}")
    p.level = level
    p.understanding = understanding
    p.persistence = persistence
    p.creativity = creativity
    p.collaboration = collaboration
    return p


class TestMorphology:
    def test_stage_bounds(self):
        assert ClassPetService.morphology_stage(1) == 1
        assert ClassPetService.morphology_stage(10) == 8
        assert 1 <= ClassPetService.morphology_stage(5) <= 8

    def test_label_matches_stage(self):
        for lvl in range(1, 11):
            label = ClassPetService.morphology_label(lvl)
            assert isinstance(label, str) and label


class TestFeedWithPoints:
    def test_positive_points_raise_dimensions_and_level(self):
        pet = _pet(level=1)
        before = pet.total_score
        ClassPetService.feed_pet_with_points(pet, points=20, behavior="homework")
        assert pet.persistence > 50.0           # 作业 → 坚持力增益
        assert pet.total_score > before
        assert pet.mood.value == "happy"

    def test_negative_points_starve_pet(self):
        pet = _pet(level=1)
        ClassPetService.feed_pet_with_points(pet, points=-30, behavior="general")
        # 四维等比例下降，情绪转 tired
        assert pet.persistence < 50.0
        assert pet.understanding < 50.0
        assert pet.mood.value == "tired"
        # 单次 -30 仅轻微下降（未跌破 30 阈值），不应直接判为「饿肚子」
        assert ClassPetService.starvation_risk(pet) is False

    def test_behavior_routes_dimension(self):
        pet = _pet()
        ClassPetService.feed_pet_with_points(pet, points=10, behavior="help")
        # 助人 → 协作力，其余维度不变
        assert pet.collaboration > 50.0
        assert pet.understanding == 50.0


class TestStarvationRisk:
    def test_healthy_pet_not_starving(self):
        pet = _pet()
        pet.understanding = pet.persistence = pet.creativity = pet.collaboration = 60.0
        assert ClassPetService.starvation_risk(pet) is False

    def test_low_score_starving(self):
        pet = _pet()
        pet.understanding = pet.persistence = pet.creativity = pet.collaboration = 20.0
        assert ClassPetService.starvation_risk(pet) is True


class TestGardenView:
    def test_empty_garden(self):
        view = ClassPetService.build_garden_view([], "c1", 50.0)
        assert view["total_pets"] == 0
        assert view["leaderboard"] == []

    def test_aggregation_and_connection_quality(self):
        pets = [_pet(level=10, collaboration=80), _pet(level=1, collaboration=40), _pet(level=5)]
        view = ClassPetService.build_garden_view(pets, "c1", cohesion=60.0, active_ratio=0.8)
        assert view["total_pets"] == 3
        assert view["leaderboard"][0]["level"] == 10          # 按等级降序
        assert "morphology_distribution" in view
        # 连接质量在 0..1 且随凝聚力上升
        assert 0.0 <= view["connection_quality"] <= 1.0
        assert view["connection_quality"] > 0.7 * 0.6

    def test_weekly_report_includes_risk(self):
        # 三只都严重 neglected：四维均 20（total=20 < 30 阈值）→ 饿肚子
        pets = [_pet(level=1, understanding=20, persistence=20, creativity=20, collaboration=20)
                for _ in range(3)]
        report = ClassPetService.class_weekly_report(pets, "c1", cohesion=50.0, ritual_due=True)
        assert report["starving_pets"] == 3
        assert "health_note" in report
