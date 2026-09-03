"""竞技组队排位系统测试"""
import pytest
from datetime import datetime, UTC


class TestSoloRankEngine:
    def test_initial_rank(self):
        from app.services.team_competition_engine import SubjectRank, SoloRankEngine
        rank = SubjectRank(subject="数学")
        assert rank.tier.value == "iron"
        assert rank.division.value == "IV"
        assert rank.lp == 0

    def test_win_gains_lp(self):
        from app.services.team_competition_engine import SubjectRank, SoloRankEngine
        rank = SubjectRank(subject="数学")
        result = SoloRankEngine.record_game(rank, True)
        assert result["lp_change"] > 0
        assert rank.lp > 0

    def test_loss_loses_lp(self):
        from app.services.team_competition_engine import SubjectRank, SoloRankEngine
        rank = SubjectRank(subject="数学", lp=50)
        result = SoloRankEngine.record_game(rank, False)
        assert result["lp_change"] < 0

    def test_win_streak_bonus(self):
        from app.services.team_competition_engine import SubjectRank, SoloRankEngine
        rank = SubjectRank(subject="数学", win_streak=5)
        result = SoloRankEngine.record_game(rank, True)
        assert result["lp_change"] >= 20 + 5 * 3  # base + streak bonus

    def test_promotion_series_triggers(self):
        from app.services.team_competition_engine import SubjectRank, SoloRankEngine, RankTier, RankDivision
        rank = SubjectRank(subject="数学", tier=RankTier.SILVER, division=RankDivision.I, lp=99)
        result = SoloRankEngine.record_game(rank, True)
        assert result["promotion_series"]

    def test_get_rank_display(self):
        from app.services.team_competition_engine import SubjectRank, SoloRankEngine
        rank = SubjectRank(subject="数学")
        display = SoloRankEngine.get_rank_display(rank)
        assert "IRON IV" in display["display"]

    def test_promotion_through_divisions(self):
        from app.services.team_competition_engine import SubjectRank, SoloRankEngine, RankTier, RankDivision
        rank = SubjectRank(subject="数学", tier=RankTier.IRON, division=RankDivision.I, lp=99)
        # 赢一场触发晋级赛
        result = SoloRankEngine.record_game(rank, True)
        assert result["promotion_series"]
        # 赢两场晋级
        SoloRankEngine.record_game(rank, True)
        result = SoloRankEngine.record_game(rank, True)
        assert result["result"] == "promoted"


class TestTeamManagementEngine:
    def test_create_team(self):
        from app.services.team_competition_engine import TeamManagementEngine
        team = TeamManagementEngine.create_team("火箭队", "RKT", "u1", "小明")
        assert team.name == "火箭队"
        assert team.tag == "RKT"
        assert len(team.members) == 1
        assert team.members[0].role == "captain"

    def test_join_team(self):
        from app.services.team_competition_engine import TeamManagementEngine
        team = TeamManagementEngine.create_team("闪电队", "FLS", "u1", "小红")
        result = TeamManagementEngine.join_team(team.id, "u2", "小刚")
        assert result["success"]

    def test_cannot_join_full_team(self):
        from app.services.team_competition_engine import TeamManagementEngine
        team = TeamManagementEngine.create_team("满员队", "FUL", "u1", "C")
        for i in range(10):
            TeamManagementEngine.join_team(team.id, f"u{i+2}", f"M{i}")
        result = TeamManagementEngine.join_team(team.id, "u12", "overflow")
        assert not result["success"]

    def test_leave_team(self):
        from app.services.team_competition_engine import TeamManagementEngine
        team = TeamManagementEngine.create_team("离队测试", "LTD", "c1", "队长")
        TeamManagementEngine.join_team(team.id, "m1", "成员")
        result = TeamManagementEngine.leave_team("m1")
        assert result["success"]

    def test_list_teams(self):
        from app.services.team_competition_engine import TeamManagementEngine
        TeamManagementEngine.create_team("A队", "AA", "u1", "a")
        TeamManagementEngine.create_team("B队", "BB", "u2", "b")
        result = TeamManagementEngine.list_teams()
        assert result["total"] >= 2


class TestTeamLeagueEngine:
    def test_record_contribution(self):
        from app.services.team_competition_engine import TeamManagementEngine, TeamLeagueEngine
        team = TeamManagementEngine.create_team("贡献测试", "GT", "u1", "队长")
        result = TeamLeagueEngine.record_team_contribution(team.id, "u1", "数学", 50)
        assert result["recorded"]
        assert result["team_xp"] == 50

    def test_subject_leaderboard(self):
        from app.services.team_competition_engine import TeamManagementEngine, TeamLeagueEngine
        t1 = TeamManagementEngine.create_team("数A", "SA", "u1", "C")
        t2 = TeamManagementEngine.create_team("数B", "SB", "u2", "C")
        TeamLeagueEngine.record_team_contribution(t1.id, "u1", "数学", 100)
        TeamLeagueEngine.record_team_contribution(t2.id, "u2", "数学", 50)
        result = TeamLeagueEngine.get_subject_leaderboard("数学")
        assert result["rankings"][0]["score"] == 100

    def test_global_leaderboard(self):
        from app.services.team_competition_engine import TeamManagementEngine, TeamLeagueEngine
        t1 = TeamManagementEngine.create_team("全A", "GA", "u1", "a")
        t2 = TeamManagementEngine.create_team("全B", "GB", "u2", "b")
        TeamLeagueEngine.record_team_contribution(t1.id, "u1", "数学", 100)
        TeamLeagueEngine.record_team_contribution(t2.id, "u2", "英语", 200)
        result = TeamLeagueEngine.get_global_leaderboard()
        assert result["rankings"][0]["total_xp"] == 200


class TestMVPEngine:
    def test_calculate_mvp(self):
        from app.services.team_competition_engine import TeamManagementEngine, MVPEngine
        team = TeamManagementEngine.create_team("MVP队", "MVP", "mvp_c", "小明")
        TeamManagementEngine.join_team(team.id, "mvp_m", "小红")
        team = TeamManagementEngine.TEAMS[team.id]
        team.members[0].contribution_xp = 500
        team.members[1].contribution_xp = 300
        result = MVPEngine.calculate_mvp(team)
        assert result["has_mvp"]
        assert "小明" in result["mvp_name"]

    def test_mvp_badge(self):
        from app.services.team_competition_engine import MVPEngine
        badge = MVPEngine.get_mvp_badge(10)
        assert badge["name"] == "队伍核心"


class TestTeamMatchEngine:
    def test_create_match(self):
        from app.services.team_competition_engine import TeamManagementEngine, TeamMatchEngine
        t1 = TeamManagementEngine.create_team("红队", "RED", "u1", "C")
        t2 = TeamManagementEngine.create_team("蓝队", "BLU", "u2", "C")
        result = TeamMatchEngine.create_match(t1.id, t2.id, "数学")
        assert result["success"]
        assert "红队" in result["message"]

    def test_contribute_to_match(self):
        from app.services.team_competition_engine import TeamManagementEngine, TeamMatchEngine
        t1 = TeamManagementEngine.create_team("攻队", "ATK", "u1", "C")
        t2 = TeamManagementEngine.create_team("守队", "DEF", "u2", "C")
        match_result = TeamMatchEngine.create_match(t1.id, t2.id, "英语")
        result = TeamMatchEngine.contribute_to_match(match_result["match_id"], t1.id, "u1", 50)
        assert result["contributed"]

    def test_match_status(self):
        from app.services.team_competition_engine import TeamManagementEngine, TeamMatchEngine
        t1 = TeamManagementEngine.create_team("T1", "TT", "u1", "C")
        t2 = TeamManagementEngine.create_team("T2", "UU", "u2", "C")
        mr = TeamMatchEngine.create_match(t1.id, t2.id, "物理")
        status = TeamMatchEngine.get_match_status(mr["match_id"])
        assert status["exists"]
        assert status["subject"] == "物理"


class TestSeasonEngine:
    def test_season_info(self):
        from app.services.team_competition_engine import SeasonEngine
        info = SeasonEngine.get_season_info()
        assert "days_left" in info

    def test_season_reward(self):
        from app.services.team_competition_engine import SeasonEngine, RankTier
        reward = SeasonEngine.get_season_reward(RankTier.DIAMOND)
        assert "钻石" in reward["reward"]

    def test_end_season(self):
        from app.services.team_competition_engine import SeasonEngine, SubjectRank, RankTier, RankDivision
        ranks = {
            "数学": SubjectRank(subject="数学", tier=RankTier.GOLD, division=RankDivision.II, lp=50)
        }
        result = SeasonEngine.end_season(ranks)
        assert result["season_ended"]
        assert "数学" in result["rewards"]
        # 软重置: Gold → 降2 → Bronze
        assert ranks["数学"].tier == RankTier.BRONZE
