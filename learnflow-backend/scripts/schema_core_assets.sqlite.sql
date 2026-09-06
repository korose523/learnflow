-- ===========================================================================
-- LearnFlow 核心资产持久化 DDL —— SQLite 3 可执行版（可复现性交付物·便携版）
-- ===========================================================================
-- 背景：
--   原始交付物 scripts/schema_core_assets.sql 使用 Postgres 专有类型
--   (JSONB / TIMESTAMPTZ / BIGSERIAL / now())，在 LearnFlow 的 SQLite 测试/轻量
--   环境（见 app/core/config.py:32 默认走 MySQL，但测试与本地常回退 SQLite）下无法
--   直接执行，审稿人按论文附录复现会在第一步失败。
--   本文件是该表结构在 SQLite 3 下的等价实现，保证「每条语句都能在 SQLite 3 执行成功」。
--
-- 与论文附录的关系：
--   schema_core_assets.sql 作为 Postgres 原稿保留（论文方法学附录的归档价值）。
--   schema_core_assets.mysql.sql 与 schema_core_assets.sqlite.sql 为可移植版本，
--   随论文一并交付，确保任一目标环境都可真正把表建出来。
--
-- 语义对应关系（相对 Postgres 原稿）：
--   JSONB        -> SQLite TEXT（存 JSON 字符串；读回时按 JSON 解析）
--   TIMESTAMPTZ  -> SQLite TEXT（存 ISO8601 字符串；默认值用 datetime('now')）
--   BIGSERIAL    -> SQLite INTEGER PRIMARY KEY AUTOINCREMENT
--   BOOLEAN      -> SQLite INTEGER（0/1）
--   BIGINT/INTEGER 数值 -> SQLite INTEGER
--
-- 关于 users / classes 外键：
--   原 Postgres 稿中 user_xp_state.user_id、experiment_assignments.user_id 等带有
--   REFERENCES users(id) ON DELETE CASCADE 外键。本便携版仅声明列、省略这些外键约束
--   （users / classes 为系统既有表，不在本脚本范围内）；experiment_assignments 保留了
--   REFERENCES experiments(id) 的写法——SQLite 默认【不强制】外键（需 PRAGMA
--   foreign_keys=ON 才启用），此处仅作结构声明、不影响建表成功，特此说明。
--   生产部署时请按需补回对 users / classes 的引用完整性保证。
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 4.2.1 user_xp_state (LF-M19)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_xp_state (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER     NOT NULL,
    total_xp        INTEGER     NOT NULL DEFAULT 0,
    level           INTEGER     NOT NULL DEFAULT 1,
    xp_into_level   INTEGER     NOT NULL DEFAULT 0,
    current_streak  INTEGER     NOT NULL DEFAULT 0,
    longest_streak  INTEGER     NOT NULL DEFAULT 0,
    last_active_date TEXT,
    streak_freeze_used INTEGER  NOT NULL DEFAULT 0,   -- LF-M12 连胜神圣化
    daily_goal_xp   INTEGER     NOT NULL DEFAULT 20,  -- LF-M16
    updated_at      TEXT        NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_user_xp UNIQUE (user_id)
);
CREATE INDEX IF NOT EXISTS idx_xp_level   ON user_xp_state (level DESC);
CREATE INDEX IF NOT EXISTS idx_xp_streak  ON user_xp_state (current_streak DESC);
CREATE INDEX IF NOT EXISTS idx_xp_lastact ON user_xp_state (last_active_date DESC);

-- ---------------------------------------------------------------------------
-- 4.2.2 user_skill_tree (LF-M40, 16 技能树)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_defs (
    skill_id      TEXT    PRIMARY KEY,
    name_zh       TEXT    NOT NULL,
    category      TEXT    NOT NULL,     -- MEMORY/UNDERSTANDING/PRACTICE/FOCUS/MINDSET
    prerequisites TEXT    NOT NULL DEFAULT '[]',
    max_level     INTEGER NOT NULL DEFAULT 5
);

CREATE TABLE IF NOT EXISTS user_skill_tree (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    skill_id     TEXT    NOT NULL,
    level        INTEGER NOT NULL DEFAULT 0,
    skill_xp     INTEGER NOT NULL DEFAULT 0,
    unlocked     INTEGER NOT NULL DEFAULT 0,   -- 0/1 语义布尔
    unlocked_at  TEXT,
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_user_skill UNIQUE (user_id, skill_id),
    CONSTRAINT fk_skilltree_skill FOREIGN KEY (skill_id) REFERENCES skill_defs(skill_id)
);
CREATE INDEX IF NOT EXISTS idx_skilltree_user  ON user_skill_tree (user_id);
CREATE INDEX IF NOT EXISTS idx_skilltree_skill ON user_skill_tree (skill_id, level DESC);

-- ---------------------------------------------------------------------------
-- 4.2.3 实验数据三表 (A/B 框架)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiments (
    id                   TEXT    PRIMARY KEY,
    name                 TEXT    NOT NULL,
    description          TEXT,
    gate_level           INTEGER NOT NULL DEFAULT 1,   -- 0/1/2 检验序层级
    mechanism_toggles    TEXT    NOT NULL DEFAULT '{}', -- {"LF-M44": false}
    primary_metric       TEXT    NOT NULL,
    mde                  REAL    NOT NULL,
    alpha_alloc          REAL    NOT NULL,
    required_n_per_group INTEGER NOT NULL,
    cluster_randomized   INTEGER NOT NULL DEFAULT 1,   -- 0/1 语义布尔
    deff                 REAL    NOT NULL DEFAULT 1.0,
    phase                TEXT    NOT NULL,
    registry_fingerprint TEXT   NOT NULL,             -- 可复现性锚点
    created_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    started_at           TEXT,
    completed_at         TEXT
);

CREATE TABLE IF NOT EXISTS experiment_assignments (
    experiment_id TEXT    NOT NULL,
    user_id       INTEGER NOT NULL,
    cluster_id    INTEGER,                            -- 班级 ID（整群随机）
    group_name    TEXT    NOT NULL,                   -- control/treatment
    assigned_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (experiment_id, user_id),
    CONSTRAINT fk_assign_exp FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);
CREATE INDEX IF NOT EXISTS idx_assign_cluster ON experiment_assignments (experiment_id, cluster_id);

CREATE TABLE IF NOT EXISTS experiment_results (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT    NOT NULL,
    user_id      INTEGER NOT NULL,
    group_name   TEXT    NOT NULL,
    metrics      TEXT    NOT NULL DEFAULT '{}',
    recorded_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT fk_result_exp FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);
CREATE INDEX IF NOT EXISTS idx_exp_results ON experiment_results (experiment_id, group_name);
