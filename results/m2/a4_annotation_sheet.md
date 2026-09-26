# M2 A4 · 双编码注释表（coder B 用）

> **用途**：把 `a4_coderB.csv` 里 17 个 `source_anchor` 指向的源码片段抓到一起，供 coder B 定位与判读。

> **不含任何判定**：本表不替 coder B 填写 `target_construct` / `direction` / `channel`，那三列由 coder B **独立**判定。

> **数据来源**：Ludilearn @ commit `eb69582fb4def6e4cbb26c2146ceb90435951c53`（已从 GitHub 抓取，行号经核对一致）；Level Up XP @ `danbetcher/moodle-levelup`（**仓库在 GitHub 返回 404，源码不可获取**）。

## 一、Ludilearn（6 项，已抓取源码）

### LUDI_1 · Ludilearn · `lang/en/format_ludilearn.php:202`

- 锚点命中行：**202**

```php
2. For non-graded activities with activity completion, learners are awarded Gold badges directly upon activity completion.<br>
3. In the case of a graded activity with completion of the activity, learners will be able to obtain one of the 3 levels of badges (Gold, Silver, Bronze) and a bonus badge linked to completion.</p>';
$string['settings:progressiondescription'] = '<p>The progress game element displays the learner\'s overall progress through the course in the form of a journey. It automatically adapts to the different types of activities.<br><br>
1. For graded activities, progress corresponds directly to the percentage of the grade obtained. For example, if a learner obtains 80% in a quiz, their progression for this activity will be 80%.<br>
2. For activities with completion only, progress increases by 100%  as soon as the activity is marked as completed.<br>
3. For activities that combine marking and completion, it is the mark achieved that determines progress, completion has no additional impact.</p>';
$string['settings:avatardescription'] = '<p>The avatar game element allows learners to earn items and customise their visual representation in the course. Learners unlock items such as hairstyles, clothing and accessories as they progress through the course. <br><br>
1. For graded activities, unlocking avatar items is based on achieving a score above the threshold to earn an item. For example, if the threshold is set at 80%, the learner will need to score above 80% in a graded activity to unlock a new avatar item.<br>
2. For completion-only activities, completion of the activity unlocks an avatar item. <br>
3. For activities that combine scoring and completion, the score achieved is used. Activity completion has no additional impact.</p>';
$string['settings:timerdescription'] = '<p>The timer game element adds a time dimension to your course quizzes. <strong>It works exclusively with test (or quiz)</strong> type activities. The element displays the time taken by the learner to complete the test, with overtime penalties applied for errors.<br>
- The time used by the learner is counted at the quiz level.<br>
- The learner\'s best time is recorded and displayed in the quiz, and the average quiz time is displayed in the course section.<br>
```

- 中性说明（仅描述代码本身，非构念判定）：语言字符串：头像（avatar）游戏元素的描述——学习者随课程进度解锁发型/服饰/配饰等，自定义在课程中的可视化形象。

- **coder B 请独立判定**：`target_construct` / `direction` / `channel`

### LUDI_2 · Ludilearn · `lang/en/format_ludilearn.php:194`

- 锚点命中行：**194**

```php
Adjust this threshold according to the difficulty of your activities and the frequency with which you want learners to unlock new avatar elements.';
$string['settings:scoredescription'] = '<p>The score game element allows learners to accumulate points by completing course activities. It adapts automatically to the different types of activities offered.<br><br>
1. For graded activities, the score is based directly on the mark obtained. For example, a mark of 16 out of 20 translates into 16 points.<br>
A multiplication coefficient is applied to transform these points into a score, as in games. For example, a coefficient of 80 will show 1280 points in the scoring system.<br>
2. For activities with only completion, a fixed number called the completion bonus is awarded when the activities are completed. For example, at the end of the activity, the learner is awarded 150 points.<br>
3. In the case of activities combining grade and completion, the score takes into account both the grade and an additional percentage added to the grade. For example, completing the activity will add an additional 20% to the total score that can be achieved.</p>';
$string['settings:badgedescription'] = '<p>This game element rewards learners with badges for completing activities. It adapts automatically to the different types of activities in the course<br><br>.
1. For graded activities, three levels of badges (Gold, Silver, Bronze) are awarded automatically when the learner\'s grade reaches or exceeds the threshold defined for each level.<br>
2. For non-graded activities with activity completion, learners are awarded Gold badges directly upon activity completion.<br>
3. In the case of a graded activity with completion of the activity, learners will be able to obtain one of the 3 levels of badges (Gold, Silver, Bronze) and a bonus badge linked to completion.</p>';
$string['settings:progressiondescription'] = '<p>The progress game element displays the learner\'s overall progress through the course in the form of a journey. It automatically adapts to the different types of activities.<br><br>
1. For graded activities, progress corresponds directly to the percentage of the grade obtained. For example, if a learner obtains 80% in a quiz, their progression for this activity will be 80%.<br>
2. For activities with completion only, progress increases by 100%  as soon as the activity is marked as completed.<br>
```

- 中性说明（仅描述代码本身，非构念判定）：语言字符串：徽章（badge）游戏元素的描述文本。

- **coder B 请独立判定**：`target_construct` / `direction` / `channel`

### LUDI_3 · Ludilearn · `lang/en/format_ludilearn.php:198`

- 锚点命中行：**198**

```php
2. For activities with only completion, a fixed number called the completion bonus is awarded when the activities are completed. For example, at the end of the activity, the learner is awarded 150 points.<br>
3. In the case of activities combining grade and completion, the score takes into account both the grade and an additional percentage added to the grade. For example, completing the activity will add an additional 20% to the total score that can be achieved.</p>';
$string['settings:badgedescription'] = '<p>This game element rewards learners with badges for completing activities. It adapts automatically to the different types of activities in the course<br><br>.
1. For graded activities, three levels of badges (Gold, Silver, Bronze) are awarded automatically when the learner\'s grade reaches or exceeds the threshold defined for each level.<br>
2. For non-graded activities with activity completion, learners are awarded Gold badges directly upon activity completion.<br>
3. In the case of a graded activity with completion of the activity, learners will be able to obtain one of the 3 levels of badges (Gold, Silver, Bronze) and a bonus badge linked to completion.</p>';
$string['settings:progressiondescription'] = '<p>The progress game element displays the learner\'s overall progress through the course in the form of a journey. It automatically adapts to the different types of activities.<br><br>
1. For graded activities, progress corresponds directly to the percentage of the grade obtained. For example, if a learner obtains 80% in a quiz, their progression for this activity will be 80%.<br>
2. For activities with completion only, progress increases by 100%  as soon as the activity is marked as completed.<br>
3. For activities that combine marking and completion, it is the mark achieved that determines progress, completion has no additional impact.</p>';
$string['settings:avatardescription'] = '<p>The avatar game element allows learners to earn items and customise their visual representation in the course. Learners unlock items such as hairstyles, clothing and accessories as they progress through the course. <br><br>
1. For graded activities, unlocking avatar items is based on achieving a score above the threshold to earn an item. For example, if the threshold is set at 80%, the learner will need to score above 80% in a graded activity to unlock a new avatar item.<br>
2. For completion-only activities, completion of the activity unlocks an avatar item. <br>
```

- 中性说明（仅描述代码本身，非构念判定）：语言字符串：进度（progression）游戏元素的描述文本。

- **coder B 请独立判定**：`target_construct` / `direction` / `channel`

### LUDI_4 · Ludilearn · `lang/en/format_ludilearn.php:133`

- 锚点命中行：**133**

```php
$string['propulsion'] = 'Propulsion';
$string['theme'] = 'Theme';
$string['timer'] = 'Timer';
$string['besttime'] = 'Best time';
$string['averagetime'] = 'Average time';
$string['reference_time'] = 'Reference time';
$string['ranking'] = 'Ranking';
$string['report'] = 'Participant tracking';
$string['report_description'] = 'This page allows you to track participants\' progress and view the game element assigned to them. To personalize the gaming experience, you can change a participant\'s game element at any time: click on the name of the game element in the table and select a new element from the drop-down menu.';
$string['manually_assigned'] = 'Custom assignment';
$string['progression'] = 'Progression';
$string['missinganswers'] = 'You must answer this question to validate the questionnaire';
$string['equip'] = 'Equip';
```

- 中性说明（仅描述代码本身，非构念判定）：语言字符串：排行榜（ranking）元素的标签文本。

- **coder B 请独立判定**：`target_construct` / `direction` / `channel`

### LUDI_5 · Ludilearn · `lang/en/format_ludilearn.php:189`

- 锚点命中行：**189**

```php
For example, if the penalty is set to 20 seconds and a learner gets 0 points on a 2-point quiz, 40 seconds will be added to the learner\'s final time.';
$string['settings:thresholdtoearn'] = 'Threshold for unlocking an avatar element';
$string['settings:thresholdtoearn_help'] = 'This parameter defines the minimum score (as a percentage) that a learner must achieve in a graded activity to unlock a new avatar element. For example, if the threshold is set at 80%:<br />
* A score of 81% in a quiz will unlock an avatar element <br />.
* A score of 79%  will not unlock anything, even if the activity is completed.
Adjust this threshold according to the difficulty of your activities and the frequency with which you want learners to unlock new avatar elements.';
$string['settings:scoredescription'] = '<p>The score game element allows learners to accumulate points by completing course activities. It adapts automatically to the different types of activities offered.<br><br>
1. For graded activities, the score is based directly on the mark obtained. For example, a mark of 16 out of 20 translates into 16 points.<br>
A multiplication coefficient is applied to transform these points into a score, as in games. For example, a coefficient of 80 will show 1280 points in the scoring system.<br>
2. For activities with only completion, a fixed number called the completion bonus is awarded when the activities are completed. For example, at the end of the activity, the learner is awarded 150 points.<br>
3. In the case of activities combining grade and completion, the score takes into account both the grade and an additional percentage added to the grade. For example, completing the activity will add an additional 20% to the total score that can be achieved.</p>';
$string['settings:badgedescription'] = '<p>This game element rewards learners with badges for completing activities. It adapts automatically to the different types of activities in the course<br><br>.
1. For graded activities, three levels of badges (Gold, Silver, Bronze) are awarded automatically when the learner\'s grade reaches or exceeds the threshold defined for each level.<br>
```

- 中性说明（仅描述代码本身，非构念判定）：语言字符串：分数（score）游戏元素的描述文本。

- **coder B 请独立判定**：`target_construct` / `direction` / `channel`

### LUDI_6 · Ludilearn · `classes/local/gameelements/timer.php`

- 锚点命中行：**51**

```php
     */
    protected int $penalties;

    /**
     * @var int DEFAULT_PENALTIES Penalties by point lost.
     */
    const DEFAULT_PENALTIES = 20;

    /**
     * Constructor.
     *
     * @param int $id             Id of the game element.
     * @param int $courseid       Id of the course.
```

- 中性说明（仅描述代码本身，非构念判定）：类常量 DEFAULT_PENALTIES = 20，定义计时器（timer）游戏元素每扣 1 分对应的惩罚量；构造时在 sectionparameters 中写入 penalties。

- **coder B 请独立判定**：`target_construct` / `direction` / `channel`


## 二、Level Up XP（11 项，⚠️ 源码不可获取）

> 引用的 `danbetcher/moodle-levelup` 仓库在 GitHub 返回 **404**（已更名 / 删除 / 私有）。以下仅列原始锚点；待你提供本地克隆路径或新仓库地址后，我再补抓片段。

| item | 原始锚点（coder A 记录） | 状态 |
|---|---|---|
| LUXP_1 | `classes/local/badge/badge_manager.php` | ⚠️ 不可获取（仓库 404） |
| LUXP_2 | `classes/form/cheatguard.php` | ⚠️ 不可获取（仓库 404） |
| LUXP_3 | `classes/local/division/group_division.php` | ⚠️ 不可获取（仓库 404） |
| LUXP_4 | `classes/local/leaderboard/course_user_leaderboard.php` | ⚠️ 不可获取（仓库 404） |
| LUXP_5 | `classes/local/xp/levels_info.php, level.php` | ⚠️ 不可获取（仓库 404） |
| LUXP_6 | `classes/local/notification/course_level_up_notification_service.php` | ⚠️ 不可获取（仓库 404） |
| LUXP_7 | `classes/form/promo.php` | ⚠️ 不可获取（仓库 404） |
| LUXP_8 | `classes/local/xp/rank.php, state_rank.php` | ⚠️ 不可获取（仓库 404） |
| LUXP_9 | `classes/local/ruletype/limit_spec.php（H/D/W/M 窗口 + timesallowed）` | ⚠️ 不可获取（仓库 404） |
| LUXP_10 | `classes/local/rule/the_dictator.php, ruletype/*.php` | ⚠️ 不可获取（仓库 404） |
| LUXP_11 | `classes/local/xp/state.php, user_state.php` | ⚠️ 不可获取（仓库 404） |
