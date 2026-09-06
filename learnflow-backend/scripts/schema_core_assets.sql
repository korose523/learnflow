-- [2026-09-06 追加说明] 本文件为 Postgres 方言原稿（JSONB/TIMESTAMPTZ/BIGSERIAL/now()），
--   仅作论文方法学附录归档；项目实际环境为 MySQL（见 app/core/config.py:32），
--   Postgres 原稿无法直接执行。可在 MySQL 8.0 / SQLite 3 真正执行的等价版本见：
--     - scripts/schema_core_assets.mysql.sql   (MySQL 8.0)
--     - scripts/schema_core_assets.sqlite.sql  (SQLite 3)
--   验证方式见 scripts/verify_schema_portable.py。
-- ===========================================================================
-- LearnFlow 核心资产持久化 DDL (治理方案 §4.2)
-- 说明: 本文件为「数据落库」改造的建表脚本，提交即作为论文方法学附录与可复现性交付物。
--       生产执行需配合 Alembic 迁移；实验框架当前以 JSONFileExperimentStore 落库，
--       待数据规模稳定后切换为下述 SQLExperimentStore。
-- 依赖: users(id), classes(id) 已存在。

-- ---------------------------------------------------------------------------
-- 4.2.1 user_xp_state (LF-M19) —— 最高优先级修复（XP 伪持久化）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_xp_state (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_xp        BIGINT      NOT NULL DEFAULT 0,
    level           INTEGER     NOT NULL DEFAULT 1,
    xp_into_level   BIGINT      NOT NULL DEFAULT 0,
    current_streak  INTEGER     NOT NULL DEFAULT 0,
    longest_streak  INTEGER     NOT NULL DEFAULT 0,
    last_active_date DATE,
    streak_freeze_used INTEGER  NOT NULL DEFAULT 0,   -- LF-M12 连胜神圣化
    daily_goal_xp   INTEGER     NOT NULL DEFAULT 20,  -- LF-M16
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_xp UNIQUE (user_id)
);
CREATE INDEX IF NOT EXISTS idx_xp_level    ON user_xp_state (level DESC);
CREATE INDEX IF NOT EXISTS idx_xp_streak   ON user_xp_state (current_streak DESC);
CREATE INDEX IF NOT EXISTS idx_xp_lastact  ON user_xp_state (last_active_date DESC);

-- ---------------------------------------------------------------------------
-- 4.2.2 user_skill_tree (LF-M40, 16 技能树)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_defs (
    skill_id      VARCHAR(64) PRIMARY KEY,
    name_zh       VARCHAR(64)  NOT NULL,
    category      VARCHAR(32)  NOT NULL,     -- MEMORY/UNDERSTANDING/PRACTICE/FOCUS/MINDSET
    prerequisites JSONB        NOT NULL DEFAULT '[]',
    max_level     INTEGER      NOT NULL DEFAULT 5
);

CREATE TABLE IF NOT EXISTS user_skill_tree (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id     VARCHAR(64) NOT NULL REFERENCES skill_defs(skill_id),
    level        INTEGER     NOT NULL DEFAULT 0,
    skill_xp     BIGINT      NOT NULL DEFAULT 0,
    unlocked     BOOLEAN     NOT NULL DEFAULT false,
    unlocked_at  TIMESTAMPTZ,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_skill UNIQUE (user_id, skill_id)
);
CREATE INDEX IF NOT EXISTS idx_skilltree_user  ON user_skill_tree (user_id);
CREATE INDEX IF NOT EXISTS idx_skilltree_skill ON user_skill_tree (skill_id, level DESC);

-- ---------------------------------------------------------------------------
-- 4.2.3 实验数据三表 (A/B 框架)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiments (
    id                   VARCHAR(64) PRIMARY KEY,
    name                 VARCHAR(255) NOT NULL,
    description          TEXT,
    gate_level           SMALLINT   NOT NULL DEFAULT 1,   -- 0/1/2 检验序层级
    mechanism_toggles    JSONB      NOT NULL DEFAULT '{}', -- {"LF-M44": false}
    primary_metric       VARCHAR(64) NOT NULL,
    mde                  REAL       NOT NULL,
    alpha_alloc          REAL       NOT NULL,
    required_n_per_group INTEGER    NOT NULL,
    cluster_randomized   BOOLEAN    NOT NULL DEFAULT true,
    deff                 REAL       NOT NULL DEFAULT 1.0,
    phase                VARCHAR(16) NOT NULL,
    registry_fingerprint VARCHAR(16) NOT NULL,             -- 可复现性锚点
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at           TIMESTAMPTZ,
    completed_at         TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS experiment_assignments (
    experiment_id VARCHAR(64) NOT NULL REFERENCES experiments(id),
    user_id       BIGINT      NOT NULL REFERENCES users(id),
    cluster_id    BIGINT,                                  -- 班级 ID（整群随机）
    group_name    VARCHAR(16) NOT NULL,                    -- control/treatment
    assigned_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (experiment_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_assign_cluster ON experiment_assignments (experiment_id, cluster_id);

CREATE TABLE IF NOT EXISTS experiment_results (
    id           BIGSERIAL PRIMARY KEY,
    experiment_id VARCHAR(64) NOT NULL REFERENCES experiments(id),
    user_id      BIGINT      NOT NULL,
    group_name   VARCHAR(16) NOT NULL,
    metrics      JSONB      NOT NULL,
    recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_exp_results ON experiment_results (experiment_id, group_name);
