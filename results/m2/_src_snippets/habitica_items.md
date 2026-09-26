# Habitica 机制实例清点（A4 外部系统，跨系统复现）

> 用途：为 M2「多干预并存学习系统的冲突结构审计」提供**非 PHP、非 Moodle 生态**的第四个外部系统样本，
> 供两名人类编码者独立编码。本文件只做**源码级清点**，不含任何 target_construct / direction / channel 的归类判断。

## 元信息

| 字段 | 值 |
| --- | --- |
| repo | `HabitRPG/habitica` |
| default branch | `develop` |
| HEAD commit (pinned) | `bce89c627c756d72e6b2403a91e8ac2cf7116e4d` |
| HEAD commit date | 2026-09-24T21:09:26Z |
| HEAD commit message | `5.50.6` |
| 取样时间 | 2026-09-27 |
| 生态 | JavaScript / Node.js + Vue；服务端 Express + MongoDB (Mongoose)，共享逻辑位于 `website/common/script` |
| 实例数 | 8（另有 8 个已验证的备选锚点，见附录） |

**可复现性说明**：全部引用均使用 pinned commit SHA，不引用分支名，因此行号永不漂移。
所有锚点均通过 `curl --noproxy '*' -s -o /dev/null -w "%{http_code}" https://raw.githubusercontent.com/HabitRPG/habitica/<commit>/<path>` 实测返回 **200**。

行号取自该文件在此 commit 下的原始文本（1-based）。核心游戏逻辑文件行数：
`website/common/script/ops/scoreTask.js` = 447 行；`website/server/libs/cron.js` = 516 行；
`website/common/script/fns/updateStats.js` = 101 行；`website/common/script/fns/randomDrop.js` = 159 行。

---

## 汇总表

| item_id | commit | file:line | source_path | evidence（源码原文） | HTTP |
| --- | --- | --- | --- | --- | --- |
| HABI_1 | `bce89c6` | `scoreTask.js:36` | `website/common/script/ops/scoreTask.js` | `let nextDelta = (0.9747 ** currVal) * (direction === 'down' ? -1 : 1);` | 200 |
| HABI_2 | `bce89c6` | `scoreTask.js:117` | `website/common/script/ops/scoreTask.js` | `const hpMod = delta * conBonus * task.priority * 2; // constant 2 multiplier for better results` | 200 |
| HABI_3 | `bce89c6` | `scoreTask.js:143` | `website/common/script/ops/scoreTask.js` | `const streakBonus = currStreak / 100 + 1; // eg, 1-day streak is 1.01, 2-day is 1.02, etc` | 200 |
| HABI_4 | `bce89c6` | `scoreTask.js:342` | `website/common/script/ops/scoreTask.js` | `if (user.addNotification) user.addNotification('STREAK_ACHIEVEMENT');` | 200 |
| HABI_5 | `bce89c6` | `cron.js:268` | `website/server/libs/cron.js` | `if (!user.preferences.sleep) {` | 200 |
| HABI_6 | `bce89c6` | `cron.js:332` | `website/server/libs/cron.js` | `if (perfect && atLeastOneDailyDue) {` | 200 |
| HABI_7 | `bce89c6` | `updateStats.js:35` | `website/common/script/fns/updateStats.js` | `user.stats.hp = MAX_HEALTH;` | 200 |
| HABI_8 | `bce89c6` | `randomDrop.js:51` | `website/common/script/fns/randomDrop.js` | `* (1 + (task.streak / 100 \|\| 0)) // Streak bonus: +1% per streak` | 200 |

---

## 实例详情

### HABI_1

- **repo**: `HabitRPG/habitica`
- **commit**: `bce89c627c756d72e6b2403a91e8ac2cf7116e4d`
- **source_path**: `website/common/script/ops/scoreTask.js`
- **file:line**: `scoreTask.js:36`（上下文块：`scoreTask.js:33-56`，边界常量见 `scoreTask.js:18-19`）
- **desc_zh**:
  这段代码位于 `_calculateDelta` 函数内，在任务被勾选（direction 为 `up`）或被反向取消（direction 为 `down`）时计算本次该任务 `value` 的增减步长，公式为以 0.9747 为底、以任务当前 value 为指数的幂，方向为 down 时取负。由于 0.9747 小于 1，同一任务被反复向同一方向打卡时，单次步长会随之变小，源码注释把这一数值的取值范围称为 "task redness"（第 34 行）。`value` 的取值被 `_getTaskValue` 限制在 -47.27（`MIN_TASK_VALUE`）到 21.27（`MAX_TASK_VALUE`）之间。若任务带有检查清单且为每日任务在跨日重置中被反向打卡，步长按清单完成比例缩减；若为待办任务在非重置场景下打卡，步长按已完成清单项数放大。
- **evidence**: `let nextDelta = (0.9747 ** currVal) * (direction === 'down' ? -1 : 1);`

### HABI_2

- **repo**: `HabitRPG/habitica`
- **commit**: `bce89c627c756d72e6b2403a91e8ac2cf7116e4d`
- **source_path**: `website/common/script/ops/scoreTask.js`
- **file:line**: `scoreTask.js:117`（上下文块：`scoreTask.js:112-124`）
- **desc_zh**:
  这是 `_subtractPoints` 函数中的一行，该函数用于减少用户的生命值（`stats.hp`）。它在两类情形下被调用：一是习惯被打卡后计算出的增量 `delta` 不为正时（`scoreTask.js:281`），二是每日任务在跨日重置中被判为到期未完成时（`scoreTask.js:308`）。伤害量由本次任务的增量 `delta`、一个基于用户体质属性（`statsComputed(user).con`）的减免系数 `conBonus`（第 114-115 行，下限 0.1）、任务难度系数 `task.priority` 以及常数 2 相乘得到；若算出的结果为 -1 以内的负值，则仍至少扣除 1 点生命值。该函数在开头对「属于某个小组看板且类型为每日任务」的任务直接返回原生命值，不执行扣减。
- **evidence**: `const hpMod = delta * conBonus * task.priority * 2; // constant 2 multiplier for better results`

### HABI_3

- **repo**: `HabitRPG/habitica`
- **commit**: `bce89c627c756d72e6b2403a91e8ac2cf7116e4d`
- **source_path**: `website/common/script/ops/scoreTask.js`
- **file:line**: `scoreTask.js:143`（上下文块：`scoreTask.js:141-156`）
- **desc_zh**:
  在 `_addPoints` 中，若任务带有非零的连续打卡计数 `task.streak`，本行会以 `currStreak / 100 + 1` 计算出一个系数，再乘到本次任务的金币收益 `gpMod` 上；源码注释给出的例子是 1 天连胜对应 1.01、2 天对应 1.02。第 145-147 行规定，当该系数带来的增益不足 1 枚金币时，按方向强制保底 ±1 枚。因连胜多出的这部分金币会被写入 `user._tmp.streakBonus`（第 150 行），源码注释说明这是为了后续向用户发送连胜加成的通知。
- **evidence**: `const streakBonus = currStreak / 100 + 1; // eg, 1-day streak is 1.01, 2-day is 1.02, etc`

### HABI_4

- **repo**: `HabitRPG/habitica`
- **commit**: `bce89c627c756d72e6b2403a91e8ac2cf7116e4d`
- **source_path**: `website/common/script/ops/scoreTask.js`
- **file:line**: `scoreTask.js:342`（上下文块：`scoreTask.js:337-344`；对称的撤销逻辑见 `scoreTask.js:371-374`）
- **desc_zh**:
  在每日任务被勾选（direction 为 `up`）且不属于小组任务时，第 338 行先把该任务的 `streak` 计数加 1；若加 1 后的 streak 为 21 的整数倍（第 340 行），则用户的 `achievements.streak` 计数加 1，并随即调用本行向用户推送一条 `STREAK_ACHIEVEMENT` 通知。第 372-374 行存在对称逻辑：当用户撤销（direction 为 `down`）一次完成、且撤销前的 streak 恰为 21 的倍数时，该计数减 1（下限 0）。
- **evidence**: `if (user.addNotification) user.addNotification('STREAK_ACHIEVEMENT');`

### HABI_5

- **repo**: `HabitRPG/habitica`
- **commit**: `bce89c627c756d72e6b2403a91e8ac2cf7116e4d`
- **source_path**: `website/server/libs/cron.js`
- **file:line**: `cron.js:268`（上下文块：`cron.js:250-288`；同一 sleep 判断在 `cron.js:359` 另有出现）
- **desc_zh**:
  这是每日重置（`cron` 函数）处理未完成每日任务时的条件判断。当某每日任务在跨日时被判定为到期未完成（`scheduleMisses > evadeTask`，第 250 行）且 cron 未运行在安全模式下，代码先置 `perfect = false` 并累计未完成计数，随后仅在本行条件成立——即用户未开启「休息」偏好 `user.preferences.sleep`——时才调用 `scoreTask` 以 down 方向对该任务执行扣分与生命值扣减。同一分支内在非半安全模式下还会把这次负增量乘以难度系数累加到 `user.party.quest.progress.down`（第 279 行）。处于「休息」状态时，上述分数扣减与生命值扣减、以及该 boss 伤害累加均不执行；同文件第 359 行对每日魔力补给使用了相同的 `sleep` 判断条件。
- **evidence**: `if (!user.preferences.sleep) {`

### HABI_6

- **repo**: `HabitRPG/habitica`
- **commit**: `bce89c627c756d72e6b2403a91e8ac2cf7116e4d`
- **source_path**: `website/server/libs/cron.js`
- **file:line**: `cron.js:332`（上下文块：`cron.js:332-352`）
- **desc_zh**:
  在每日重置遍历完所有每日任务之后，本行检查两项条件：标志 `perfect` 仍为 true（即当天没有到期未完成的每日任务，参见第 256 行），且当天至少有一个每日任务到期（`atLeastOneDailyDue`）。两项同时成立时，用户的 `achievements.perfect` 计数加 1，并把 `str` / `int` / `per` / `con` 四项 buff 统一设为「用户等级经 `common.capByLevel` 限制后再除以 2 并向上取整」的数值（第 334-342 行）。若条件不成立，第 344-351 行把这四项 buff 连同 `stealth`、`streaks` 一起重置为 0。
- **evidence**: `if (perfect && atLeastOneDailyDue) {`

### HABI_7

- **repo**: `HabitRPG/habitica`
- **commit**: `bce89c627c756d72e6b2403a91e8ac2cf7116e4d`
- **source_path**: `website/common/script/fns/updateStats.js`
- **file:line**: `updateStats.js:35`（上下文块：`updateStats.js:21-56`；等级上限见同文件第 28 行）
- **desc_zh**:
  这是 `updateStats` 升级循环内的一步。当累计经验 `stats.exp` 达到当前等级的升级阈值时，代码进入 while 循环（第 26 行）；每次迭代先扣除该级所需的经验并把等级加 1（受 `MAX_LEVEL_HARD_CAP` 限制，第 28-32 行），随后在本行把用户的生命值直接设为常量 `MAX_HEALTH`（该常量与 `MAX_LEVEL_HARD_CAP`、`MAX_STAT_POINTS` 一同从 `../constants` 引入）。之后按用户是否开启 `automaticAllocation` 决定调用 `autoAllocate` 还是把可得属性点写回 `user.stats.points`（第 42-55 行）。
- **evidence**: `user.stats.hp = MAX_HEALTH;`

### HABI_8

- **repo**: `HabitRPG/habitica`
- **commit**: `bce89c627c756d72e6b2403a91e8ac2cf7116e4d`
- **source_path**: `website/common/script/fns/randomDrop.js`
- **file:line**: `randomDrop.js:51`（上下文块：`randomDrop.js:47-63`；每日掉落上限见 `randomDrop.js:79-86`）
- **desc_zh**:
  `randomDrop` 用于决定用户完成任务时是否掉落物品（蛋、孵化药水、食物等）。掉落概率 `chance` 在第 47 行以「任务当前 value 与常数 21.27 之差的绝对值」为基线（上限 37.5，除以 150 再加 0.02），随后依次乘以任务难度 `task.priority`、随等级线性衰减的新手加成（第 50 行）、本行的连续打卡天数加成、感知属性加成（第 52 行）、贡献者等级（第 53 行）、转生次数（第 54 行）、连胜成就次数（第 55 行）、暴击系数（第 57 行）与检查清单完成项加成（第 58-62 行），最后经 `diminishingReturns(chance, 0.75)` 收敛（第 63 行）。此外第 79-86 行依据订阅状态、感知与贡献等级算出每日掉落数上限，达到上限时本函数直接返回不再掉落。
- **evidence**: `* (1 + (task.streak / 100 || 0)) // Streak bonus: +1% per streak`

---

## 附录：已验证的备选锚点（未纳入上述 8 项，可用于扩容）

以下锚点同属 pinned commit，均已用同一 `curl --noproxy '*'` 方式实测返回 **200**，行内容与下表 evidence 一致。若后期需要扩充实例或替换，可直接取用。

| 候选 id | file:line | source_path | evidence（源码原文） | HTTP |
| --- | --- | --- | --- | --- |
| A1 | `cron.js:279` | `website/server/libs/cron.js` | `user.party.quest.progress.down += delta * (task.priority < 1 ? task.priority : 1);` | 200 |
| A2 | `cron.js:183` | `website/server/libs/cron.js` | `awardLoginIncentives(user);` | 200 |
| A3 | `loginIncentives.js:1076` | `website/common/script/content/loginIncentives.js` | `loginIncentives[index].nextRewardAt = nextRewardKey;` | 200 |
| A4 | `crit.js:6` | `website/common/script/fns/crit.js` | `if (predictableRandom(user) <= chance * (1 + s / 100)) {` | 200 |
| A5 | `scoreTask.js:435` | `website/common/script/ops/scoreTask.js` | `stats.gp -= task.value;` | 200 |
| A6 | `buyArmoire.js:40` | `website/common/script/ops/buy/buyArmoire.js` | `&& (armoireResult < YIELD_EQUIPMENT_THRESHOLD \|\| !user.flags.armoireOpened)` | 200 |
| A7 | `updateStats.js:28` | `website/common/script/fns/updateStats.js` | `if (user.stats.lvl >= MAX_LEVEL_HARD_CAP) {` | 200 |
| A8 | `scoreTask.js:272` | `website/common/script/ops/scoreTask.js` | `if (task.value > user.stats.gp && task.type === 'reward') throw new NotAuthorized(i18n.t('messageNotEnoughGold', req.language));` | 200 |

---

## 验证日志

### 1. HEAD commit 确定

```
curl --noproxy '*' -s https://api.github.com/repos/HabitRPG/habitica
  -> default_branch: develop

curl --noproxy '*' -s "https://api.github.com/repos/HabitRPG/habitica/commits/develop"
  -> SHA: bce89c627c756d72e6b2403a91e8ac2cf7116e4d
  -> date: 2026-09-24T21:09:26Z
  -> msg: 5.50.6
```

### 2. 锚点逐点验证（全部 200）

```
200  HABI_1  website/common/script/ops/scoreTask.js
200  HABI_2  website/common/script/ops/scoreTask.js
200  HABI_3  website/common/script/ops/scoreTask.js
200  HABI_4  website/common/script/ops/scoreTask.js
200  HABI_5  website/server/libs/cron.js
200  HABI_6  website/server/libs/cron.js
200  HABI_7  website/common/script/fns/updateStats.js
200  HABI_8  website/common/script/fns/randomDrop.js
200  A1      website/server/libs/cron.js
200  A2      website/server/libs/cron.js
200  A3      website/common/script/content/loginIncentives.js
200  A4      website/common/script/fns/crit.js
200  A5      website/common/script/ops/scoreTask.js
200  A6      website/common/script/ops/buy/buyArmoire.js
200  A7      website/common/script/fns/updateStats.js
200  A8      website/common/script/ops/scoreTask.js
```

使用的命令形式（对每个 path 执行一次）：

```
curl --noproxy '*' -s -o /dev/null -w "%{http_code}" \
  https://raw.githubusercontent.com/HabitRPG/habitica/bce89c627c756d72e6b2403a91e8ac2cf7116e4d/<path>
```

此外还逐行拉取了锚点行的原文内容，与 evidence 字段逐字比对一致（含缩进）。

---

## 清点范围说明（诚实性边界）

- 未使用本地克隆，全部经 GitHub REST API 与 raw.githubusercontent.com 在线取得。
- 本仓库的核心游戏化逻辑集中在 `website/common/script`（共 186 个 blob），服务端日程重置集中在 `website/server/libs/cron.js`。本次 8 项中有 4 项取自 `ops/scoreTask.js`（单人任务评分最核心的入口），2 项取自 `server/libs/cron.js`（跨日重置），另外 2 项分别取自 `fns/updateStats.js` 与 `fns/randomDrop.js`。
- **未纳入本次 8 项但确实存在于本仓库**、且已定位到的机制（供后续扩容参考，锚点尚未全部验证）： achievements 数据定义（`website/common/script/content/achievements.js`）、签到奖励表（`content/loginIncentives.js`）、任务卷轴/时之沙 `content/quests*` 与 `content/time-travelers.js`、宠物孵化 `ops/hatch.js`、喂养 `ops/feed.js`、装备加成 `ops/equip.js`、技能 `content/spells.js`、属性点分配 `ops/stats/allocate*.js`、转生 `ops/rebirth.js`、复活 `ops/revive.js`、金币与银币 `libs/gold.js` 与 `libs/silver.js`、组队任务看板 `server/libs/groupTasks.js`、公会与挑战 `server/libs/challenges/*`、推送通知 `server/libs/pushNotifications.js`、待办整理与历史修剪 `libs/preenTodos.js` 与 `server/libs/preening.js`、新手引导 `libs/onboarding.js`。
- 本文件不做任何干预构念/方向/通道的归类判断；`desc_zh` 仅陈述从源码读到的行为、触发条件与可见效果。
