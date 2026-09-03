"""竞技组队排位系统 — Team Competition & Ranked League

参考: League of Legends 排位 + 电竞战队 + 科目竞技

核心设计:
1. 战队系统 (Team/Clan) — 创建/加入/管理战队
2. 科目排位 (Subject Ranked) — 每个科目独立排位段位
3. 战队联赛 (Team League) — 战队间基于科目总分的升降级
4. 赛季系统 (Season) — 每月/每季度重置
5. 战队任务 (Team Quests) — 战队协作挑战
6. MVP 系统 — 每场/每日/每周 MVP
7. 战队贡献值 — 量化每个成员的贡献
8. 战队对抗赛 (Team vs Team) — 直接对战模式

排位段位 (LoL风格):
  Iron → Bronze → Silver → Gold → Platinum → Emerald → Diamond → Master → Grandmaster → Challenger
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import random
import uuid

from app.services.state_store import StateStore, MemoryStateStore


# ═══════════════════════════════════════════════════════════
# 1. 排位段位 — Rank Tier System
# ═══════════════════════════════════════════════════════════

class RankTier(str, Enum):
    IRON = "iron"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    EMERALD = "emerald"
    DIAMOND = "diamond"
    MASTER = "master"
    GRANDMASTER = "grandmaster"
    CHALLENGER = "challenger"


class RankDivision(str, Enum):
    IV = "IV"
    III = "III"
    II = "II"
    I = "I"


@dataclass
class SubjectRank:
    """单个科目的排位状态"""
    subject: str                       # 科目名 (如 "数学", "英语", "物理")
    tier: RankTier = RankTier.IRON
    division: RankDivision = RankDivision.IV
    lp: int = 0                        # 联赛分 (League Points) 0-100
    wins: int = 0
    losses: int = 0
    win_streak: int = 0
    total_games: int = 0
    promotion_series: bool = False     # 晋级赛
    promotion_wins: int = 0
    promotion_needed: int = 2          # 晋级赛需要赢几场
    season_high: str = ""              # 本赛季最高段位


@dataclass
class TeamMember:
    """战队成员"""
    user_id: str
    name: str
    role: str = "member"               # captain / member / vice_captain
    joined_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    contribution_xp: int = 0           # 对战队的总贡献
    mvp_count: int = 0                 # 获得MVP次数


@dataclass
class Team:
    """战队"""
    id: str
    name: str
    tag: str                           # 战队简称 (2-4字符)
    description: str = ""
    captain_id: str = ""
    members: List[TeamMember] = field(default_factory=list)
    total_xp: int = 0
    total_wins: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    # 战队排位
    team_tier: RankTier = RankTier.IRON
    team_lp: int = 0
    season_wins: int = 0
    season_games: int = 0
    # 各科目战队总分
    subject_scores: Dict[str, int] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# 2. 个人排位引擎 — Solo Queue Ranked
# ═══════════════════════════════════════════════════════════

class SoloRankEngine:
    """个人排位引擎

    每个科目独立排位。赢一把+LP，输一把-LP。
    段位是身份的象征。
    """

    LP_GAIN_BASE = 20
    LP_LOSS_BASE = 15
    LP_GAIN_STREAK_BONUS = 3       # 连胜每场额外+3 LP
    PROMOTION_GAMES = 3             # 晋级赛：3局2胜

    @classmethod
    def record_game(cls, rank: SubjectRank, won: bool) -> dict:
        """记录一场排位赛"""
        rank.total_games += 1

        if won:
            rank.wins += 1
            rank.win_streak += 1

            # LP 计算
            lp_gain = cls.LP_GAIN_BASE + min(rank.win_streak * cls.LP_GAIN_STREAK_BONUS, 15)

            if rank.promotion_series:
                return cls._handle_promotion_game(rank, True)
        else:
            rank.losses += 1
            rank.win_streak = 0
            lp_gain = -cls.LP_LOSS_BASE

            if rank.promotion_series:
                return cls._handle_promotion_game(rank, False)

        rank.lp = max(0, min(100, rank.lp + lp_gain))

        # 晋级检查
        if rank.lp >= 100 and rank.tier not in (RankTier.MASTER, RankTier.GRANDMASTER, RankTier.CHALLENGER):
            return cls._start_promotion_series(rank)

        # 降级检查
        if rank.lp <= 0 and rank.tier != RankTier.IRON and rank.division == RankDivision.IV:
            return cls._demote(rank)

        return {
            "result": "win" if won else "loss",
            "lp_change": lp_gain,
            "current_lp": rank.lp,
            "tier": rank.tier.value,
            "division": rank.division.value,
            "win_streak": rank.win_streak,
            "promotion_series": rank.promotion_series,
        }

    @classmethod
    def _start_promotion_series(cls, rank: SubjectRank) -> dict:
        """开始晋级赛"""
        rank.promotion_series = True
        rank.promotion_wins = 0
        rank.lp = 100
        return {
            "result": "promotion_series_started",
            "message": f"晋级赛开始！{cls.PROMOTION_GAMES}局{cls.PROMOTION_GAMES//2+1}胜即可晋级！",
            "tier": rank.tier.value,
            "division": rank.division.value,
            "promotion_series": True,
        }

    @classmethod
    def _handle_promotion_game(cls, rank: SubjectRank, won: bool) -> dict:
        """处理晋级赛中的一场"""
        if won:
            rank.promotion_wins += 1

        games_played = rank.promotion_wins + (1 if not won else 0)
        needed = cls.PROMOTION_GAMES // 2 + 1

        if rank.promotion_wins >= needed:
            return cls._promote(rank)
        elif games_played >= cls.PROMOTION_GAMES:
            return cls._fail_promotion(rank)
        else:
            return {
                "result": "promotion_game",
                "won": won,
                "promotion_wins": rank.promotion_wins,
                "promotion_games_played": games_played,
                "needed": needed,
                "message": f"晋级赛 {rank.promotion_wins}-{games_played - rank.promotion_wins}",
            }

    @classmethod
    def _promote(cls, rank: SubjectRank) -> dict:
        """晋级"""
        rank.promotion_series = False
        rank.promotion_wins = 0
        rank.lp = 20  # 晋级后初始 LP

        if rank.division == RankDivision.I:
            # 升段
            tiers = list(RankTier)
            idx = tiers.index(rank.tier)
            if idx < len(tiers) - 1:
                rank.tier = tiers[idx + 1]
                rank.division = RankDivision.IV
            else:
                rank.division = RankDivision.I  # 最高段位
        else:
            # 升小段
            divisions = list(RankDivision)
            idx = divisions.index(rank.division)
            rank.division = divisions[idx + 1]

        # 更新赛季最高
        if rank.tier.value > rank.season_high or not rank.season_high:
            rank.season_high = rank.tier.value

        return {
            "result": "promoted",
            "message": f"🎉 晋级 {rank.tier.value.upper()} {rank.division.value}！",
            "tier": rank.tier.value,
            "division": rank.division.value,
            "lp": rank.lp,
        }

    @classmethod
    def _fail_promotion(cls, rank: SubjectRank) -> dict:
        """晋级赛失败"""
        rank.promotion_series = False
        rank.promotion_wins = 0
        rank.lp = 75  # 退回 75 LP
        return {
            "result": "promotion_failed",
            "message": "晋级赛失败…回到75 LP，继续努力！",
            "lp": rank.lp,
        }

    @classmethod
    def _demote(cls, rank: SubjectRank) -> dict:
        """降级"""
        if rank.division != RankDivision.IV:
            divisions = list(RankDivision)
            idx = divisions.index(rank.division)
            rank.division = divisions[idx - 1]
        elif rank.tier != RankTier.IRON:
            tiers = list(RankTier)
            idx = tiers.index(rank.tier)
            rank.tier = tiers[idx - 1]
            rank.division = RankDivision.I
        rank.lp = 75
        return {
            "result": "demoted",
            "message": f"降级至 {rank.tier.value.upper()} {rank.division.value}",
            "tier": rank.tier.value,
            "division": rank.division.value,
            "lp": rank.lp,
        }

    @classmethod
    def get_rank_display(cls, rank: SubjectRank) -> dict:
        """获取排位展示信息"""
        tier_colors = {
            RankTier.IRON: "#51484A", RankTier.BRONZE: "#CD7F32",
            RankTier.SILVER: "#C0C0C0", RankTier.GOLD: "#FFD700",
            RankTier.PLATINUM: "#08A89D", RankTier.EMERALD: "#50C878",
            RankTier.DIAMOND: "#B9F2FF", RankTier.MASTER: "#9B59B6",
            RankTier.GRANDMASTER: "#E74C3C", RankTier.CHALLENGER: "#F1C40F",
        }
        return {
            "tier": rank.tier.value,
            "division": rank.division.value,
            "lp": rank.lp,
            "color": tier_colors.get(rank.tier, "#CCC"),
            "display": f"{rank.tier.value.upper()} {rank.division.value} ({rank.lp} LP)",
            "winrate": round(rank.wins / max(rank.total_games, 1) * 100),
            "win_streak": rank.win_streak,
            "total_games": rank.total_games,
            "season_high": rank.season_high,
        }


# ═══════════════════════════════════════════════════════════
# 3. 战队管理引擎 — Team Management
# ═══════════════════════════════════════════════════════════

class TeamManagementEngine:
    """战队管理引擎"""

    MAX_MEMBERS = 10
    # 战队容器 —— 迁移到可插拔 StateStore 后端（对齐 BOX_STATES 示范）
    # TEAMS 的值为 Team 且被 TeamLeagueEngine/MVPEngine 就地累加（total_xp、members），
    # JSON 后端会丢失就地修改；PLAYER_TEAMS 虽为 str→str 可序列化，但与 TEAMS 同事务
    # 写入（create/join/leave），单独落库会在重启后留下悬空 team_id，故两者统一用内存后端。
    # TODO(persist): add asdict serialization for JSONFileStateStore
    TEAMS: StateStore = MemoryStateStore()
    PLAYER_TEAMS: StateStore = MemoryStateStore()  # user_id → team_id

    @classmethod
    def create_team(cls, name: str, tag: str, captain_id: str,
                     captain_name: str) -> Team:
        """创建战队"""
        if len(tag) < 2 or len(tag) > 4:
            raise ValueError("战队简称需2-4字符")

        team_id = str(uuid.uuid4())[:8]
        captain = TeamMember(user_id=captain_id, name=captain_name, role="captain")
        team = Team(id=team_id, name=name, tag=tag, captain_id=captain_id,
                     members=[captain])
        cls.TEAMS.set(team_id, team)
        cls.PLAYER_TEAMS.set(captain_id, team_id)
        return team

    @classmethod
    def join_team(cls, team_id: str, user_id: str, name: str) -> dict:
        """加入战队"""
        team = cls.TEAMS.get(team_id)
        if not team:
            return {"success": False, "message": "战队不存在"}

        if len(team.members) >= cls.MAX_MEMBERS:
            return {"success": False, "message": f"战队已满 ({cls.MAX_MEMBERS}人)"}

        if cls.PLAYER_TEAMS.get(user_id) is not None:
            return {"success": False, "message": "你已加入其他战队，请先退出"}

        member = TeamMember(user_id=user_id, name=name)
        team.members.append(member)
        cls.PLAYER_TEAMS.set(user_id, team_id)
        return {"success": True, "message": f"成功加入 {team.name} [{team.tag}]！", "team": cls.get_team_info(team)}

    @classmethod
    def leave_team(cls, user_id: str) -> dict:
        """离开战队"""
        team_id = cls.PLAYER_TEAMS.get(user_id)
        if not team_id:
            return {"success": False, "message": "你不在任何战队中"}

        team = cls.TEAMS.get(team_id)
        if team.captain_id == user_id and len(team.members) > 1:
            return {"success": False, "message": "队长需要先移交队长或解散战队"}

        team.members = [m for m in team.members if m.user_id != user_id]
        cls.PLAYER_TEAMS.delete(user_id)

        if not team.members:
            cls.TEAMS.delete(team_id)

        return {"success": True, "message": "已离开战队"}

    @classmethod
    def get_team_info(cls, team: Team) -> dict:
        """获取战队信息"""
        members_sorted = sorted(team.members, key=lambda m: m.contribution_xp, reverse=True)
        return {
            "id": team.id,
            "name": team.name,
            "tag": team.tag,
            "description": team.description,
            "member_count": len(team.members),
            "max_members": cls.MAX_MEMBERS,
            "total_xp": team.total_xp,
            "team_tier": team.team_tier.value,
            "team_lp": team.team_lp,
            "season_wins": team.season_wins,
            "members": [
                {"name": m.name, "role": m.role, "contribution": m.contribution_xp, "mvp_count": m.mvp_count}
                for m in members_sorted
            ],
            "captain": next((m.name for m in team.members if m.role == "captain"), ""),
        }

    @classmethod
    def list_teams(cls, page: int = 1, page_size: int = 10) -> dict:
        """战队列表"""
        teams = [cls.TEAMS.get(k) for k in cls.TEAMS.keys()]
        teams.sort(key=lambda t: t.total_xp, reverse=True)
        start = (page - 1) * page_size
        return {
            "total": len(teams),
            "teams": [
                {"id": t.id, "name": t.name, "tag": t.tag, "member_count": len(t.members),
                 "total_xp": t.total_xp, "team_tier": t.team_tier.value}
                for t in teams[start:start+page_size]
            ],
        }


# ═══════════════════════════════════════════════════════════
# 4. 战队联赛引擎 — Team League
# ═══════════════════════════════════════════════════════════

class TeamLeagueEngine:
    """战队联赛引擎

    战队间的对抗基于各科目的总分。
    每周结算一次战队排名。
    """

    @classmethod
    def record_team_contribution(cls, team_id: str, user_id: str,
                                   subject: str, xp_earned: int) -> dict:
        """记录战队贡献（学生答题后调用）"""
        team = TeamManagementEngine.TEAMS.get(team_id)
        if not team:
            return {"recorded": False}

        team.total_xp += xp_earned
        team.subject_scores[subject] = team.subject_scores.get(subject, 0) + xp_earned

        for member in team.members:
            if member.user_id == user_id:
                member.contribution_xp += xp_earned
                break

        return {
            "recorded": True,
            "team_xp": team.total_xp,
            "subject_score": team.subject_scores.get(subject, 0),
        }

    @classmethod
    def get_subject_leaderboard(cls, subject: str) -> dict:
        """获取某科目的战队排行榜"""
        teams = [TeamManagementEngine.TEAMS.get(k) for k in TeamManagementEngine.TEAMS.keys()]
        teams = [t for t in teams if t.subject_scores.get(subject, 0) > 0]
        teams.sort(key=lambda t: t.subject_scores.get(subject, 0), reverse=True)

        return {
            "subject": subject,
            "rankings": [
                {"rank": i+1, "team_name": t.name, "tag": t.tag,
                 "score": t.subject_scores.get(subject, 0),
                 "member_count": len(t.members)}
                for i, t in enumerate(teams[:20])
            ],
        }

    @classmethod
    def get_global_leaderboard(cls) -> dict:
        """获取全局战队排行榜"""
        teams = sorted((TeamManagementEngine.TEAMS.get(k)
                        for k in TeamManagementEngine.TEAMS.keys()),
                       key=lambda t: t.total_xp, reverse=True)
        return {
            "rankings": [
                {"rank": i+1, "team_name": t.name, "tag": t.tag, "total_xp": t.total_xp,
                 "team_tier": t.team_tier.value, "members": len(t.members)}
                for i, t in enumerate(teams[:20])
            ],
        }

    @classmethod
    def weekly_settlement(cls) -> dict:
        """每周结算（降级/升级）"""
        results = []
        teams = sorted((TeamManagementEngine.TEAMS.get(k)
                        for k in TeamManagementEngine.TEAMS.keys()),
                       key=lambda t: t.total_xp, reverse=True)

        for i, team in enumerate(teams):
            old_tier = team.team_tier
            tiers = list(RankTier)

            # 前20%晋级
            if i < len(teams) * 0.2 and team.team_tier != RankTier.CHALLENGER:
                idx = tiers.index(team.team_tier)
                team.team_tier = tiers[min(idx + 1, len(tiers) - 1)]

            # 后20%降级
            elif i >= len(teams) * 0.8 and team.team_tier != RankTier.IRON:
                idx = tiers.index(team.team_tier)
                team.team_tier = tiers[max(idx - 1, 0)]

            if old_tier != team.team_tier:
                results.append({
                    "team": team.name,
                    "from": old_tier.value,
                    "to": team.team_tier.value,
                    "action": "promoted" if team.team_tier.value > old_tier.value else "demoted",
                })

            team.season_wins = 0
            team.season_games = 0

        return {"settled": True, "changes": results}


# ═══════════════════════════════════════════════════════════
# 5. 战队 MVP 系统
# ═══════════════════════════════════════════════════════════

class MVPEngine:
    """MVP 评选引擎"""

    @classmethod
    def calculate_mvp(cls, team: Team, period: str = "weekly") -> dict:
        """计算战队 MVP"""
        if not team.members:
            return {"has_mvp": False}

        # 按贡献排序
        members_sorted = sorted(team.members, key=lambda m: m.contribution_xp, reverse=True)
        mvp = members_sorted[0]

        if mvp.contribution_xp == 0:
            return {"has_mvp": False}

        # MVP 荣誉
        mvp.mvp_count += 1

        return {
            "has_mvp": True,
            "period": period,
            "mvp_name": mvp.name,
            "mvp_contribution": mvp.contribution_xp,
            "mvp_total": mvp.mvp_count,
            "team_contribution_pct": round(mvp.contribution_xp / max(team.total_xp, 1) * 100),
            "message": f"🏆 {period} MVP: {mvp.name}！贡献了团队{mvp.contribution_xp} XP！",
            "honor_roll": [
                {"rank": i+1, "name": m.name, "xp": m.contribution_xp}
                for i, m in enumerate(members_sorted[:3])
            ],
        }

    @classmethod
    def get_mvp_badge(cls, mvp_count: int) -> dict:
        """MVP 徽章"""
        badges = {
            1: {"name": "新星", "icon": "⭐", "desc": "首次MVP"},
            5: {"name": "稳定输出", "icon": "🌟", "desc": "5次MVP"},
            10: {"name": "队伍核心", "icon": "💫", "desc": "10次MVP"},
            25: {"name": "传奇选手", "icon": "👑", "desc": "25次MVP"},
            50: {"name": "MVP收割机", "icon": "🏆", "desc": "50次MVP"},
        }
        for threshold, badge in sorted(badges.items(), reverse=True):
            if mvp_count >= threshold:
                return badge
        return {}


# ═══════════════════════════════════════════════════════════
# 6. 战队对抗赛 — Team vs Team Match
# ═══════════════════════════════════════════════════════════

@dataclass
class TeamMatch:
    """战队对抗赛"""
    id: str
    team_a_id: str
    team_b_id: str
    subject: str
    duration_hours: int = 24          # 比赛持续24小时
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    score_a: int = 0
    score_b: int = 0
    status: str = "active"            # active / completed
    participants_a: Dict[str, int] = field(default_factory=dict)
    participants_b: Dict[str, int] = field(default_factory=dict)


class TeamMatchEngine:
    """战队对抗赛引擎"""

    # 对抗赛容器 —— 迁移到可插拔 StateStore 后端
    # 值为 TeamMatch 且 contribute_to_match 就地累加 score/participants，沿用内存后端。
    # TODO(persist): add asdict serialization for JSONFileStateStore
    MATCHES: StateStore = MemoryStateStore()

    @classmethod
    def create_match(cls, team_a_id: str, team_b_id: str,
                      subject: str, duration_hours: int = 24) -> dict:
        """创建战队对抗赛"""
        team_a = TeamManagementEngine.TEAMS.get(team_a_id)
        team_b = TeamManagementEngine.TEAMS.get(team_b_id)
        if not team_a or not team_b:
            return {"success": False, "message": "战队不存在"}

        match_id = f"m_{len(cls.MATCHES.keys()) + 1}"
        match = TeamMatch(id=match_id, team_a_id=team_a_id, team_b_id=team_b_id,
                           subject=subject, duration_hours=duration_hours)
        cls.MATCHES.set(match_id, match)

        return {
            "success": True,
            "match_id": match_id,
            "team_a": team_a.name,
            "team_b": team_b.name,
            "subject": subject,
            "duration_hours": duration_hours,
            "message": f"⚔️ {team_a.name} [{team_a.tag}] vs {team_b.name} [{team_b.tag}] — {subject}对抗赛开始！",
        }

    @classmethod
    def contribute_to_match(cls, match_id: str, team_id: str,
                              user_id: str, xp: int) -> dict:
        """为对抗赛贡献分数"""
        match = cls.MATCHES.get(match_id)
        if not match or match.status != "active":
            return {"contributed": False, "message": "比赛已结束或不存在"}

        # 检查比赛是否超时
        if (datetime.now(UTC) - match.start_time).total_seconds() > match.duration_hours * 3600:
            match.status = "completed"
            return {"contributed": False, "message": "比赛时间已到"}

        if team_id == match.team_a_id:
            match.score_a += xp
            match.participants_a[user_id] = match.participants_a.get(user_id, 0) + xp
        elif team_id == match.team_b_id:
            match.score_b += xp
            match.participants_b[user_id] = match.participants_b.get(user_id, 0) + xp
        else:
            return {"contributed": False, "message": "该战队不在这场比赛中"}

        return {
            "contributed": True,
            "score_a": match.score_a,
            "score_b": match.score_b,
            "your_contribution": xp,
            "time_left_hours": max(0, match.duration_hours -
                (datetime.now(UTC) - match.start_time).total_seconds() / 3600),
        }

    @classmethod
    def get_match_status(cls, match_id: str) -> dict:
        """获取比赛状态"""
        match = cls.MATCHES.get(match_id)
        if not match:
            return {"exists": False}

        team_a = TeamManagementEngine.TEAMS.get(match.team_a_id)
        team_b = TeamManagementEngine.TEAMS.get(match.team_b_id)

        return {
            "exists": True,
            "match_id": match.id,
            "team_a": team_a.name if team_a else "未知",
            "team_b": team_b.name if team_b else "未知",
            "subject": match.subject,
            "score_a": match.score_a,
            "score_b": match.score_b,
            "status": match.status,
            "time_elapsed_hours": round((datetime.now(UTC) - match.start_time).total_seconds() / 3600, 1),
            "time_left_hours": max(0, match.duration_hours -
                (datetime.now(UTC) - match.start_time).total_seconds() / 3600),
            "winner": team_a.name if match.score_a > match.score_b else
                      team_b.name if match.score_b > match.score_a else "平局",
            "top_contributors_a": dict(sorted(match.participants_a.items(),
                                              key=lambda x: x[1], reverse=True)[:3]),
            "top_contributors_b": dict(sorted(match.participants_b.items(),
                                              key=lambda x: x[1], reverse=True)[:3]),
        }


# ═══════════════════════════════════════════════════════════
# 7. 赛季系统 — Season Management
# ═══════════════════════════════════════════════════════════

class SeasonEngine:
    """赛季管理引擎"""

    CURRENT_SEASON = 1
    SEASON_DURATION_MONTHS = 1
    SEASON_START = datetime(2026, 6, 1, tzinfo=UTC)

    SEASON_REWARDS = {
        RankTier.IRON: {"reward": "铁牌头像框", "icon": "⚙️"},
        RankTier.BRONZE: {"reward": "铜牌头像框", "icon": "🥉"},
        RankTier.SILVER: {"reward": "银牌头像框 + 1张双倍经验卡", "icon": "🥈"},
        RankTier.GOLD: {"reward": "金牌头像框 + 2张双倍经验卡", "icon": "🥇"},
        RankTier.PLATINUM: {"reward": "白金头像框 + 3张双倍经验卡 + 限定皮肤", "icon": "💠"},
        RankTier.EMERALD: {"reward": "翡翠头像框 + 限定宠物皮肤", "icon": "💚"},
        RankTier.DIAMOND: {"reward": "钻石头像框 + 钻石宠物皮肤 + 5张双倍经验卡", "icon": "💎"},
        RankTier.MASTER: {"reward": "大师框 + 传奇宠物皮肤 + 10张双倍经验卡", "icon": "👑"},
        RankTier.GRANDMASTER: {"reward": "宗师框 + 专属名牌 + 赛季纪念", "icon": "🌟"},
        RankTier.CHALLENGER: {"reward": "王者框 + 全服广播 + 永久专属名牌", "icon": "🏆"},
    }

    @classmethod
    def get_season_info(cls) -> dict:
        now = datetime.now(UTC)
        end = cls.SEASON_START + timedelta(days=30 * cls.SEASON_DURATION_MONTHS)
        days_left = max(0, (end - now).days)

        return {
            "season": cls.CURRENT_SEASON,
            "name": f"第{cls.CURRENT_SEASON}赛季",
            "days_left": days_left,
            "end_date": end.isoformat(),
            "message": f"赛季还剩{days_left}天！" if days_left > 0 else "赛季已结束！",
        }

    @classmethod
    def get_season_reward(cls, tier: RankTier) -> dict:
        reward = cls.SEASON_REWARDS.get(tier, cls.SEASON_REWARDS[RankTier.IRON])
        return {"tier": tier.value, **reward, "message": f"赛季结算奖励: {reward['reward']}"}

    @classmethod
    def end_season(cls, subject_ranks: Dict[str, SubjectRank]) -> dict:
        """赛季结算"""
        rewards = {}
        for subject, rank in subject_ranks.items():
            rewards[subject] = cls.get_season_reward(rank.tier)

            # 重置段位 (软重置: 降2个段位)
            tiers = list(RankTier)
            current_idx = tiers.index(rank.tier)
            new_idx = max(0, current_idx - 2)
            rank.tier = tiers[new_idx]
            rank.division = RankDivision.IV
            rank.lp = 0
            rank.wins = 0
            rank.losses = 0
            rank.win_streak = 0
            rank.total_games = 0
            rank.season_high = ""

        cls.CURRENT_SEASON += 1
        return {"season_ended": True, "rewards": rewards, "new_season": cls.CURRENT_SEASON}
