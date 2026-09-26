# Anki 学习干预机制代码点清点（M2 / A4 跨系统复现）

## 元信息

| 字段 | 值 |
| --- | --- |
| repo | `ankitects/anki` |
| default branch | `main` |
| **HEAD commit SHA** | `1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748` |
| HEAD commit 时间 | 2026-09-25T20:51:07Z |
| HEAD commit message | `fix: Use canonical shared decks URL (#5692)` |
| 主语言 | Rust（另有 Python / TypeScript / Svelte） |
| 取数方式 | GitHub REST API + `raw.githubusercontent.com`（`curl --noproxy '*'`），未使用本地克隆 |
| 实例数 | 8（`ANKI_1` … `ANKI_8`） |
| 锚点验证 | 8/8 返回 HTTP 200 |

原始文件 URL 模板：

```
https://raw.githubusercontent.com/ankitects/anki/1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748/<source_path>
```

---

## 汇总表

| item_id | file:line | source_path | HTTP | 一句话功能（中性） |
| --- | --- | --- | --- | --- |
| ANKI_1 | `rslib/src/deckconfig/mod.rs:44` | `rslib/src/deckconfig/mod.rs` | 200 | 卡组配置的"每天最多引入多少张新卡"默认值 |
| ANKI_2 | `rslib/src/deckconfig/mod.rs:45` | `rslib/src/deckconfig/mod.rs` | 200 | 卡组配置的"每天最多安排多少张复习卡"默认值 |
| ANKI_3 | `rslib/src/deckconfig/mod.rs:96` | `rslib/src/deckconfig/mod.rs` | 200 | 新卡学习阶段的重温步骤分钟数序列默认值 |
| ANKI_4 | `rslib/src/config/mod.rs:233` | `rslib/src/config/mod.rs` | 200 | "提前学习"时间窗秒数的取值与缺省值 |
| ANKI_5 | `rslib/src/scheduler/mod.rs:69` | `rslib/src/scheduler/mod.rs` | 200 | 一天从几点开始往前推一天的 rollover 小时取值/兜底 |
| ANKI_6 | `rslib/src/scheduler/answering/mod.rs:194` | `rslib/src/scheduler/answering/mod.rs` | 200 | 回答完成后按 leech 状态把卡片移入暂停队列 |
| ANKI_7 | `rslib/src/scheduler/states/review.rs:294` | `rslib/src/scheduler/states/review.rs` | 200 | 判断遗忘次数是否触发 leech 的阈值函数 |
| ANKI_8 | `rslib/src/scheduler/states/load_balancer.rs:324` | `rslib/src/scheduler/states/load_balancer.rs` | 200 | 按星期几对卡片分配日期做负载加权偏移 |

> 说明：本清单**不做**任何干预构念 / 方向 / 通道的归类判断，归类由人类编码者完成。
> 描述全部基于上述 commit 实际读到的源码；未在该仓库中找到的机制（例如成就系统、连续学习天数 streak 的专门统计模块）不予编造，见文末"未纳入项"。

---

## 实例详情

### ANKI_1 — 每日新卡数量上限默认值（20 张/天）

- **item_id**: `ANKI_1`
- **repo**: `ankitects/anki`
- **commit**: `1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748`
- **file:line**: `rslib/src/deckconfig/mod.rs:44`
- **source_path**: `rslib/src/deckconfig/mod.rs`
- **HTTP 验证**: 200

**desc_zh**：
这是新建卡组配置时所用的默认值表 `DEFAULT_DECK_CONFIG_INNER` 中的一个字段，其整数值 20 表示该卡组默认每天最多引入 20 张此前未学习过的新卡。它在用户未曾修改相关设置时被写入卡组配置的持久化记录，并在后续构建每日待学队列时读取。用户界面上表现为：当用户当日已引入的新卡达到该数值后，队列不再提供新的新卡。同一文件第 227 行定义的 `ensure_deck_config_values_valid()`（其中第 229 行为本字段的校验调用）会把数据库中读出时越界（不在 0~9999 内）的值改回该默认值。

**evidence**：
```rust
    new_per_day: 20,
```

---

### ANKI_2 — 每日复习卡数量上限默认值（200 张/天）

- **item_id**: `ANKI_2`
- **repo**: `ankitects/anki`
- **commit**: `1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748`
- **file:line**: `rslib/src/deckconfig/mod.rs:45`
- **source_path**: `rslib/src/deckconfig/mod.rs`
- **HTTP 验证**: 200

**desc_zh**：
这是同一张默认值表中的一个字段，其整数值 200 表示该卡组默认每天最多安排 200 张到期复习卡。与新卡上限一样，该值随新建卡组配置一并持久化，并在构建每日待复习队列时作为当日可提供的复习卡总量上限被读取。用户当日已回答的复习卡达到该数值后，队列将不再提供进一步到期的复习卡。`ensure_deck_config_values_valid()`（同文件第 230–235 行）通过 `ensure_u32_valid()` 把数据库中读出时越界（不在 0~9999 内）的值改回该默认值。

**evidence**：
```rust
    reviews_per_day: 200,
```

---

### ANKI_3 — 学习步骤序列默认值（1 分钟、10 分钟）

- **item_id**: `ANKI_3`
- **repo**: `ankitects/anki`
- **commit**: `1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748`
- **file:line**: `rslib/src/deckconfig/mod.rs:96`
- **source_path**: `rslib/src/deckconfig/mod.rs`
- **HTTP 验证**: 200

**desc_zh**：
这是 `DeckConfig::default()` 实现中给出的默认学习步骤序列：由 1.0 与 10.0 两个分钟值组成的列表。新卡在学习阶段每按一次"Good"就沿该序列前进一格，序列走完后卡片即脱离当日的分钟级（intraday）学习队列；序列的第一项（此处为 1 分钟）同时用作按"Again"后的重排延迟。用户可见效果是一张新卡在当天会被以 1 分钟、然后 10 分钟的间隔反复呈现，直到走完该序列。紧随其后的第 97 行（`relearn_steps: vec![10.0],`）给出复习阶段遗忘后的重学步骤默认值。

**evidence**：
```rust
                learn_steps: vec![1.0, 10.0],
```

---

### ANKI_4 — "提前学习"时间窗（默认 1200 秒 / 20 分钟）

- **item_id**: `ANKI_4`
- **repo**: `ankitects/anki`
- **commit**: `1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748`
- **file:line**: `rslib/src/config/mod.rs:233`
- **source_path**: `rslib/src/config/mod.rs`
- **HTTP 验证**: 200

**desc_zh**：
这是集合（collection）级配置读取函数 `learn_ahead_secs()`，它读取配置键 `LearnAheadSecs`（底层存储键名为 `collapseTime`），当该键不存在时返回缺省值 1200（秒，即 20 分钟）。该秒数在构建队列时被用作时间窗：到期时间落在"当前时刻 + 该秒数"之前的当日学习卡会被提前纳入当前队列，而非等到其精确到期时刻。用户可见效果是：当天的学习卡会出现在其标记到期时刻之前最多 20 分钟，用户不必等到精确的整分钟到期点才有卡可看。同一文件第 238 行的 `set_learn_ahead_secs()` 为该键的写入入口。

**evidence**：
```rust
    pub(crate) fn learn_ahead_secs(&self) -> u32 {
        self.get_config_optional(ConfigKey::LearnAheadSecs)
            .unwrap_or(1200)
    }
```

---

### ANKI_5 — 每日分界 rollover 小时取值与兜底（默认第 4 小时）

- **item_id**: `ANKI_5`
- **repo**: `ankitects/anki`
- **commit**: `1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748`
- **file:line**: `rslib/src/scheduler/mod.rs:69`
- **source_path**: `rslib/src/scheduler/mod.rs`
- **HTTP 验证**: 200

**desc_zh**：
这段代码位于 `timing_for_timestamp()` 内，处理 V2 调度器读取不到已配置的 rollover 小时的情形：若配置键缺失，它会把值写回 4（并同时返回 4），即以本地时间当天的第 4 小时作为"新的一天"起点。该小时值随后被传入 `sched_timing_today()`，用于决定 `days_elapsed`（自集合创建以来的天数）以及"下一次分界"的时间戳。用户可见效果是：在此小时之前进行的作答被计入上一个日历天，在此之后才计入新的一天，因而每日的配额、到期判定与"今天"的定义都以此为界。读取侧另有 `rollover_for_current_scheduler()`（同文件第 117–122 行），在配置缺失时同样以 `.unwrap_or(4)` 返回 4。

**evidence**：
```rust
                        // an older Anki version failed to set this; correct
                        // the issue
                        self.set_v2_rollover(4)?;
                        Some(4)
```

---

### ANKI_6 — 回答后按 leech 状态把卡片移入暂停队列

- **item_id**: `ANKI_6`
- **repo**: `ankitects/anki`
- **commit**: `1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748`
- **file:line**: `rslib/src/scheduler/answering/mod.rs:194`
- **source_path**: `rslib/src/scheduler/answering/mod.rs`
- **HTTP 验证**: 200

**desc_zh**：
这段代码位于 `apply_study_state()` 中，在一次作答所产生的状态落盘前执行：若新状态被标记为 leeched（`next.leeched()`），且当前卡组配置的 `leech_action` 取值为 `LeechAction::Suspend`，则把该卡的队列字段改写为 `CardQueue::Suspended`。用户可见效果是这张此后不再出现在任何学习/复习队列中，除非用户手动解除暂停。同一份作答流程中另有一处与之并行、且不依赖 `leech_action` 取值的处理（同文件第 361–363 行 `if answer.new_state.leeched() { self.add_leech_tag(card.note_id)?; }`），它会给对应笔记加上名为 `leech` 的标签。

**evidence**：
```rust
        if next.leeched() && self.config.inner.leech_action() == LeechAction::Suspend {
            self.card.queue = CardQueue::Suspended;
        }
```

---

### ANKI_7 — 遗忘次数是否触发 leech 的阈值判定

- **item_id**: `ANKI_7`
- **repo**: `ankitects/anki`
- **commit**: `1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748`
- **file:line**: `rslib/src/scheduler/states/review.rs:294`
- **source_path**: `rslib/src/scheduler/states/review.rs`
- **HTTP 验证**: 200

**desc_zh**：
这是函数 `leech_threshold_met(lapses, threshold)`，用于判断某张卡当前的连续遗忘次数是否达到"顽固卡（leech）"触发条件。其判定为：当阈值为正数时，先取阈值的一半并向上取整（最小为 1）作为 `half_threshold`，然后在遗忘次数不小于阈值、且"遗忘次数减阈值"能被该半数整除时返回真；阈值为 0 或更小时恒返回假。于是遗忘次数达到阈值那一次之后，卡片会在阈值处、以及此后每隔半个阈值的遗忘次数处被反复标记为 leeched。调用点在同文件第 95–104 行 `answer_again()`：每多一次遗忘就把 `lapses` 加一并重新调用本函数，结果写入 `ReviewState.leeched`。所引用的阈值来自卡组配置，其默认值 8 定义在 `rslib/src/deckconfig/mod.rs:63`（`leech_threshold: 8,`），默认处置动作 `LeechAction::TagOnly` 定义在第 62 行，读取时会被夹取到 1~9999 区间。

**evidence**：
```rust
fn leech_threshold_met(lapses: u32, threshold: u32) -> bool {
    if threshold > 0 {
        let half_threshold = (threshold as f32 / 2.0).ceil().max(1.0) as u32;
        // at threshold, and every half threshold after that, rounding up
        lapses >= threshold && (lapses - threshold) % half_threshold == 0
```

---

### ANKI_8 — 按星期几调节排期分布的 "easy days" 负载修正

- **item_id**: `ANKI_8`
- **repo**: `ankitects/anki`
- **commit**: `1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748`
- **file:line**: `rslib/src/scheduler/states/load_balancer.rs:324`
- **source_path**: `rslib/src/scheduler/states/load_balancer.rs`
- **HTTP 验证**: 200

**desc_zh**：
这是函数 `calculate_easy_days_modifiers(easy_days_load, weekdays, review_counts)`，它为一组候选到期日期逐个计算 0~1 之间的浮点权重，权重由该日期落在星期几、以及该星期几在三档（`Minimum` / `Reduced` / `Normal`）中的配置决定（`load_modifier()` 分别返回 0.0001、0.5、1.0，见同文件第 53–63 行）。除了这三档的直接映射，本函数还含一项额外的降级规则：若某星期几被设为 `Reduced`，它会比较该日期归一化后的卡量与其他日期的平均承容量，超过阈值时自动降级为 `Minimum`。这些权重最终进入 `select_weighted_interval(intervals, fuzz_seed)`（调用点在同文件第 264 行），影响某张到期卡牌被实际安排在哪一天出现；用户侧看到的仅是到期日分布的变化，Balancer 本身不产生任何提示文案。配置来源为卡组配置的 `easy_days_percentages` 字段，其值经 `From<f32> for EasyDay`（同文件第 43–51 行）映射：1.0 为 `Normal`、0.0 为 `Minimum`、其余值为 `Reduced`；其默认值为全 1.0 的七元向量（`easy_days_percentages: vec![1.0; 7],`，定义在 `rslib/src/deckconfig/mod.rs:98`），即默认情况下本机制不产生任何偏移。此外，本机制仅在 `BoolKey::LoadBalancerEnabled` 为真时才会被构建与调用（见 `rslib/src/scheduler/queue/builder/mod.rs:152-165`）。

**evidence**：
```rust
pub(crate) fn calculate_easy_days_modifiers(
    easy_days_load: &[EasyDay; 7],
    weekdays: &[usize],
    review_counts: &[usize],
) -> Vec<f32> {
```

---

## 未纳入项（诚实性说明）

以下机制曾按 team-lead 提示清单在本次 commit 的仓库中检索，但因**在当前 commit 中不存在**而不写入实例，特此记录以免被误认为遗漏：

| 候选方向 | 检索方法与结果 |
| --- | --- |
| 成就系统（achievements） | 对 commit 的 `git/trees?recursive=1` 返回的**全部 2108 个 blob 路径**做子串匹配：`achievement` = 0 命中、`levelup` = 0、`level_up` = 0、`points` 仅命中 `ts/lib/sass/breakpoints.scss`（样式断点）、`xp` 仅命中导出/导入模块与图标资源（`.xpm`）、`reward` = 0、`gamif` = 0、`badge` 的 6 个命中全为 Svelte 通用 UI 组件（`Badge.svelte` 等）。结论：该 commit 无成就/积分/徽章发放逻辑。 |
| 连续学习天数（streak） | 上述全量路径匹配中 `streak` = 0 命中；`rslib/src/stats/` 下共 15 个模块，均为按日计数、按答案按钮、eases、间隔、到期、future due、留存率等图表数据的获取与 SQL 语句，无"连续天数"累计逻辑。 |
| 复习提醒 / 通知推送 | 上述全量路径匹配中 `reminder` = 0、`notif` 仅命中 `ts/routes/editor/Notification.svelte`（编辑器内的通用提示条组件）；`rslib/` 中无定时/到点提醒的用户通知调度逻辑。 |
| 埋卡（bury） | `rslib/src/scheduler/bury_and_suspend.rs` 确实存在（已取回，HTTP 200），但为控制实例数上限（≤8）本次未纳入；保留为备选锚点。 |

保留为备选的属性型锚点（同样已读到源码、HTTP 200，本次未纳入 8 项清单）：

- `rslib/src/deckconfig/mod.rs:62` — `leech_action: LeechAction::TagOnly as i32,`
- `rslib/src/deckconfig/mod.rs:63` — `leech_threshold: 8,`
- `rslib/src/deckconfig/mod.rs:47` — `initial_ease: 2.5,`
- `rslib/src/deckconfig/mod.rs:52` — `maximum_review_interval: 36_500,`
- `rslib/src/deckconfig/mod.rs:65` — `cap_answer_time_to_secs: 60,`
- `rslib/src/deckconfig/mod.rs:80` — `desired_retention: 0.9,`
- `rslib/src/deckconfig/mod.rs:98` — `easy_days_percentages: vec![1.0; 7],`
- `rslib/src/decks/limits.rs:127` — `cap_to()`，父级卡组配额向下传递时取较小值的操作
- `rslib/src/scheduler/states/steps.rs:55` — `hard_delay_secs_for_first_step()`，首步 Hard 间隔的取中规则

---

## 复现命令

```bash
# 1. 取 HEAD SHA（本次记录值应与下列一致）
curl --noproxy '*' -s "https://api.github.com/repos/ankitects/anki/commits/HEAD" \
  | python -c "import sys,json; print(json.load(sys.stdin)['sha'])"
# 期望输出：1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748

# 2. 逐个锚点验证 HTTP 状态码（8 次调用均应输出 200）
SHA=1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748
for p in \
  rslib/src/deckconfig/mod.rs \
  rslib/src/config/mod.rs \
  rslib/src/scheduler/mod.rs \
  rslib/src/scheduler/answering/mod.rs \
  rslib/src/scheduler/states/review.rs \
  rslib/src/scheduler/states/load_balancer.rs \
  rslib/src/decks/limits.rs \
  rslib/src/scheduler/states/steps.rs ; do
  echo "$(curl --noproxy '*' -s -o /dev/null -w '%{http_code}' \
    https://raw.githubusercontent.com/ankitects/anki/$SHA/$p)  $p"
done
```
