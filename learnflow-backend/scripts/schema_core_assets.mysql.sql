-- ===========================================================================
-- LearnFlow 核心资产持久化 DDL —— MySQL 8.0 可执行版（可复现性交付物·便携版）
-- ===========================================================================
-- 背景：
--   原始交付物 scripts/schema_core_assets.sql 使用 Postgres 专有类型
--   (JSONB / TIMESTAMPTZ / BIGSERIAL / now())，在 LearnFlow 实际运行环境
--   （默认 MySQL，见 app/core/config.py:32 的 DATABASE_URL）下无法直接执行，
--   审稿人按论文附录复现会在第一步失败。
--   本文件是该表结构在 MySQL 8.0 下的等价实现，保证「每条语句都能在 MySQL 8.0 执行成功」。
--
-- 与论文附录的关系：
--   schema_core_assets.sql 作为 Postgres 原稿保留（论文方法学附录的归档价值）。
--   schema_core_assets.mysql.sql 与 schema_core_assets.sqlite.sql 为可移植版本，
--   随论文一并交付，确保任一目标环境都可真正把表建出来。
--
-- 语义对应关系（相对 Postgres 原稿）：
--   JSONB        -> MySQL JSON
--   TIMESTAMPTZ  -> MySQL DATETIME(6)
--   BIGSERIAL    -> MySQL BIGINT AUTO_INCREMENT PRIMARY KEY
--   BOOLEAN      -> MySQL BOOLEAN（自动同义为 TINYINT(1)）
--
-- 关于 users / classes 外键：
--   原 Postgres 稿中 user_xp_state.user_id、experiment_assignments.user_id 等带有
--   REFERENCES users(id) ON DELETE CASCADE 外键。本便携版仅声明列、省略这些外键约束
--   （users / classes 为系统既有表，不在本脚本范围内），以保证核心资产表可独立建出。
--   生产部署时请按需补回外键，或依赖应用层保证引用完整性。
--
-- 重新执行说明：建表用 CREATE TABLE IF NOT EXISTS；索引用普通 CREATE INDEX（MySQL 8
--   不支持 CREATE INDEX IF NOT EXISTS）。重复执行前请先 DROP 或在新库上运行。
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 4.2.1 user_xp_state (LF-M19) —— 最高优先级修复（XP 伪持久化）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_xp_state (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         BIGINT      NOT NULL,
    total_xp        BIGINT      NOT NULL DEFAULT 0,
    level           INTEGER     NOT NULL DEFAULT 1,
    xp_into_level   BIGINT      NOT NULL DEFAULT 0,
    current_streak  INTEGER     NOT NULL DEFAULT 0,
    longest_streak  INTEGER     NOT NULL DEFAULT 0,
    last_active_date DATE       NULL,
    streak_freeze_used INTEGER  NOT NULL DEFAULT 0,   -- LF-M12 连胜神圣化
    daily_goal_xp   INTEGER     NOT NULL DEFAULT 20,  -- LF-M16
    updated_at      DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT uq_user_xp UNIQUE (user_id)
);
CREATE INDEX idx_xp_level   ON user_xp_state (level DESC);
CREATE INDEX idx_xp_streak  ON user_xp_state (current_streak DESC);
CREATE INDEX idx_xp_lastact ON user_xp_state (last_active_date DESC);

-- ---------------------------------------------------------------------------
-- 4.2.2 user_skill_tree (LF-M40, 16 技能树)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_defs (
    skill_id      VARCHAR(64) PRIMARY KEY,
    name_zh       VARCHAR(64)  NOT NULL,
    category      VARCHAR(32)  NOT NULL,     -- MEMORY/UNDERSTANDING/PRACTICE/FOCUS/MINDSET
    prerequisites JSON         NOT NULL DEFAULT (JSON_ARRAY()),
    max_level     INTEGER      NOT NULL DEFAULT 5
);

CREATE TABLE IF NOT EXISTS user_skill_tree (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT      NOT NULL,
    skill_id     VARCHAR(64) NOT NULL,
    level        INTEGER     NOT NULL DEFAULT 0,
    skill_xp     BIGINT      NOT NULL DEFAULT 0,
    unlocked     BOOLEAN     NOT NULL DEFAULT FALSE,
    unlocked_at  DATETIME(6) NULL,
    updated_at   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT uq_user_skill UNIQUE (user_id, skill_id),
    CONSTRAINT fk_skilltree_skill FOREIGN KEY (skill_id) REFERENCES skill_defs(skill_id)
);
CREATE INDEX idx_skilltree_user  ON user_skill_tree (user_id);
CREATE INDEX idx_skilltree_skill ON user_skill_tree (skill_id, level DESC);

-- ---------------------------------------------------------------------------
-- 4.2.3 实验数据三表 (A/B 框架)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiments (
    id                   VARCHAR(64) PRIMARY KEY,
    name                 VARCHAR(255) NOT NULL,
    description          TEXT,
    gate_level           SMALLINT     NOT NULL DEFAULT 1,   -- 0/1/2 检验序层级
    mechanism_toggles    JSON         NOT NULL DEFAULT (JSON_OBJECT()), -- {"LF-M44": false}
    primary_metric       VARCHAR(64)  NOT NULL,
    mde                  REAL         NOT NULL,
    alpha_alloc          REAL         NOT NULL,
    required_n_per_group INTEGER      NOT NULL,
    cluster_randomized   BOOLEAN      NOT NULL DEFAULT TRUE,
    deff                 REAL         NOT NULL DEFAULT 1.0,
    phase                VARCHAR(16)  NOT NULL,
    registry_fingerprint VARCHAR(16)  NOT NULL,             -- 可复现性锚点
    created_at           DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    started_at           DATETIME(6)  NULL,
    completed_at         DATETIME(6)  NULL
);

CREATE TABLE IF NOT EXISTS experiment_assignments (
    experiment_id VARCHAR(64) NOT NULL,
    user_id       BIGINT      NOT NULL,
    cluster_id    BIGINT      NULL,                          -- 班级 ID（整群随机）
    group_name    VARCHAR(16) NOT NULL,                      -- control/treatment
    assigned_at   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (experiment_id, user_id),
    CONSTRAINT fk_assign_exp FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);
CREATE INDEX idx_assign_cluster ON experiment_assignments (experiment_id, cluster_id);

CREATE TABLE IF NOT EXISTS experiment_results (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    experiment_id VARCHAR(64) NOT NULL,
    user_id      BIGINT      NOT NULL,
    group_name   VARCHAR(16) NOT NULL,
    metrics      JSON        NOT NULL DEFAULT (JSON_OBJECT()),
    recorded_at  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_result_exp FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);
CREATE INDEX idx_exp_results ON experiment_results (experiment_id, group_name);
