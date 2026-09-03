# LearnFlow 新增引擎说明：记忆科学与习惯化

## 1. 新增服务模块

### `app/services/memory_science_engine.py`

- **FSRSSpacedRepetitionEngine**：基于难度（D）、稳定性（S）和可提取性（R）的简化FSRS间隔重复调度器。
- **MemoryConsolidationEngine**：提供睡眠和运动建议，促进学习后记忆巩固。
- **MnemonicEngine**：生成首字母缩略、关键词法和挂钩法。
- **ConcreteExamplesEngine**：为抽象概念生成学科相关的具体例子。
- **DesirableDifficultiesOrchestrator**：根据掌握度和遗忘曲线推荐学习方法。
- **MemoryScienceOrchestrator**：整合上述模块，生成复习计划和记忆辅助包。

### `app/services/habit_addiction_engine.py`

- **HabitStackingEngine**：推荐习惯触发点和习惯链。
- **TemptationBundlingEngine**：绑定学习与即时奖励。
- **ImplementationIntentionsEngine**：生成 if-then 计划和挫折恢复计划。
- **AutonomySupportEngine**：提供选择和理由解释，满足自主性需求。
- **SelfRegulationEngine**：目标设定、进度监控和反思。
- **HabitAddictionOrchestrator**：整合为个人习惯培养方案。

## 2. 新增 API 接口

挂载在 `/api/v1/student/gamification` 下：

| 接口 | 说明 |
|------|------|
| GET /memory-science/review-plan | FSRS风格复习计划 |
| GET /memory-science/aid | 单个概念记忆辅助包 |
| GET /memory-science/consolidation | 睡眠与运动巩固建议 |
| GET /memory-science/mnemonic | 记忆术生成 |
| GET /memory-science/example | 具体例子生成 |
| GET /memory-science/recommend | 基于遗忘曲线推荐方法 |
| GET /habit-formation/plan | 个人习惯培养方案 |

## 3. 新增测试

- `tests/test_memory_science.py`：18 个测试用例
- `tests/test_habit_addiction.py`：15 个测试用例

运行测试：

```bash
cd learnflow-backend
.venv/Scripts/python.exe -m pytest tests/test_memory_science.py tests/test_habit_addiction.py -v
```

## 4. 理论基础

- **间隔重复**：基于艾宾浩斯遗忘曲线与FSRS算法。
- **主动回忆与生成效应**：Roediger & Karpicke (2006), Karpicke & Blunt (2011)。
- **适难性**：Bjork (1994) desirable difficulties。
- **睡眠与记忆巩固**：Walker (2017)。
- **运动与BDNF**：Ratey (2008)。
- **习惯叠加**：Clear (2018)。
- **诱惑捆绑**：Milkman et al. (2014)。
- **执行意图**：Gollwitzer (1999)。
- **自我决定理论**：Deci & Ryan (1985)。
- **自我调节学习**：Zimmerman (2002)。
