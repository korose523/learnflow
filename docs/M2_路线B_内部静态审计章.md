# 多干预学习系统的内部实现诊断

## 学位论文路线 B 章节草稿

本章使用封存时点 `audit-m2-20260911` 的内部静态审计。它说明 LearnFlow 的干预设计、登记和实际效果构造之间的差异，不报告真实用户冲突率、冲突治理效果或学习增益。当前版本是章节草稿，篇幅与目录需本人审阅后确定。

## 1 研究对象与证据层级

游戏化学习系统可以登记许多机制，却只有少量机制产生送入仲裁器的效果。若将登记数理解为运行数，就会在评价之前误认系统已经具备干预暴露。本章以 LearnFlow 为内部对象，检查机制注册、运行入口、效果构造和仲裁条件之间的对应关系。

审计材料包括封存注册表、编排器、效果类与仲裁器，以及保存的逐机制清单。当前开发分支的修改不进入历史计数。其余公开日志中的学习者也不是 LearnFlow 用户，因此不能提供本系统机制共现或冲突发生的经验频率。

证据按四层区分：登记表证明设计中列有该机制；可达函数证明存在调用路径；效果构造证明生成了送入仲裁的候选对象；有同意的用户运行记录才能说明何时被展示、被拦截及产生何种结果。这四层不能由前一层推导后一层。

## 2 登记与成熟度

| 口径 | 封存结果 | 能回答的问题 |
|---|---:|---|
| 语义去重后的登记数 | 54 | 设计账本列出多少机制 |
| 运行时效果生产者 | 2 | 哪些路径构造仲裁候选效果 |
| 完整实现 | 9 | 内部实现检查中判为 complete 的条目 |
| 部分实现 | 37 | 仍有未实现环节的条目 |
| 占位 | 8 | 仅声明、占位或缺少关键实现的条目 |

完整实现 9、部分 37、占位 8 的和为 54。成熟度反映内部实现状态，与生产者数不是同一个统计。一个完整实现的后台评估函数可以不构造可见干预，而一个效果构造点可以服务某个较大机制。不能把 9 理解为九种用户已接受的有效干预，也不能用 54 代替运行时暴露分母。

登记中的重复命名需先做语义去重，成熟度则需说明判定规则。保存的登记指纹和代码基准共同限定此处数字的适用时点。本章不将修改后新增候选生产者追溯加入封存基准。

## 3 干预七元组与实际可得字段

设计用七元组 I=〈trigger, target_construct, direction, channel, cost, side_effect, precedence〉描述一个干预。触发条件说明何时产生候选；作用构念说明想改变什么；方向说明促进或抑制；通道说明如何呈现；预算说明成本；副作用说明已知代价；优先级说明冲突时的处理次序。

| 字段 | 封存实现中的可得性 | 对自动审计的影响 |
|---|---|---|
| trigger | stage 在 54/54 登记中可读 | 粗阶段不是完整的运行时触发谓词 |
| direction | 方向表覆盖 12/54 | 42 项无法直接从实现读出方向 |
| target_construct | 没有对应的结构字段 | 同构念判据须依赖外部语义解释 |
| channel | 没有对应的结构字段 | 不能以通道定义共现负荷 |
| side_effect | 没有对应的结构字段 | 不能由代码自动验证副作用约束 |
| precedence | 没有完整 schema 对应字段 | 局部 Effect.priority 不等于所有登记具备优先级元数据 |
| cost | 仲裁器中有局部成本属性 | 不证明全登记预算字段完备 |

四个未实现字段是 schema 元数据层面的缺失，不能因为运行时某个对象有相近属性就补写为实现完成。方向 12/54 的覆盖率也不意味着其余 42 项没有任何心理作用，而是没有可用于这一审计判据的显式方向。

按“无 direction”的口径，42/54=77.8%。这诊断的是本系统设计与实现之间的缺口。它不证明某种外部游戏化分类学失败，也不证明真实学习中冲突很普遍。设计者与实现者同属本项目，不能把内部完成度包装为独立发现。

## 4 效果生产与仲裁入口

封存代码中构造 Effect 的两个机制为 LF-M44 与 LF-M52。LF-M44 是用户可见的促进候选，LF-M52 是健康关键的保护候选且不作为普通可见干预进入方向比较。大量机制仅写入评估记录，而未形成仲裁候选。

| 机制 | 属性 | 结构作用 |
|---|---|---|
| LF-M44 | user_visible=True；health_critical=False | 普通可见候选 |
| LF-M52 | user_visible=False；health_critical=True | 健康关键保护候选 |

这一区别改变“冲突处理已实现”的含义。方向比较针对可见效果，而当普通可见生产者只有一个时，不能形成两个普通可见效果之间的方向对。LF-M52 对 LF-M44 的保护作用由健康否决处理，不能将它计为第二层方向消解的运行证据。

预算竞争同样需要多个参与预算的候选同时存在。保护候选绕过普通预算，而普通候选只有一个。因此，零预算竞争的静态结论说明该时点结构中缺少竞争参与者，不说明未来用户会话的竞争频率为零。

## 5 三种容易混淆的比较

### 5.1 潜在方向对与可触达冲突

方向表中促进方向有 9 个、抑制方向有 3 个，笛卡尔积有 27 对。这个数仅是忽略其他条件的静态上界。若要求同构念、触发可同时为真及真实候选生产者存在，可比较集合会缩小。

只依方向表推断 27 对运行冲突，会同时忽略作用构念和生产者入口。相反，仅看到运行结构中很少候选便推断设计无需治理，也同样越过证据。应分别说明设计潜在对、可达候选对与实际会话共现率；第三项当前没有用户数据。

### 5.2 分类归属与字段完备

治理文档的 A–H 分类回答“这个机制在设计中归入哪类”，七元组回答“运行审计所需字段是否可读取”。所有条目有类别归属并不能保证方向、通道、副作用、优先级都已实现。因此类别覆盖率不能替代 schema 字段完备率。

保存的分类映射跨多个代码类别说明两套账本服务于不同用途。若将它们合并，须先定义映射规则，不能将不同名字的同一项重复计数，也不能将不同功能的项目按近似名字强行合并。

### 5.3 工程测试与经验验证

测试可以检查健康否决不会被普通奖励覆盖、仲裁顺序是否确定、预算边界是否按代码执行。这些测试是工程正确性证据。要证明机制维持学习动机或减少不良影响，需要独立结果、随机或可识别设计以及真实用户数据。

内部合成会话即使生成了分布，也不能替代上述经验评价。先看到合成结果再改指标定义的历史输出也不作为本章结果。没有身份可核验的独立第二编码者，不报告 Cohen κ 或双人盲编结论。

## 6 审计可支持的工程要求

每个候选效果需携带明确机制 ID、触发时点、作用构念、方向、通道、成本、保护优先级及协议版本，才有可能对完整 schema 进行运行审计。字段缺失应显式记录为未知，不能由默认值产生似乎完备的元数据。

运行日志需区分候选生成、进入仲裁、被否决、实际展示、用户响应。评估记录不是已展示干预。需要独立会话 ID 和条件记录才能估计候选共现率；研究导出还需同意与匿名化。上述是从缺口导出的设计要求，当前没有完成运行效果评价。

对未成年人，健康关键约束应有明确优先级与验证。局部代码存在保护逻辑不代表临床健康评分获得验证；未验证量表及风险标签应从研究实验界面关闭。研究用版本应先保证处理条件与结果观测不被这些反馈污染。

## 7 解释边界与后续评价

本章不能外推到其他学习平台，不能判断游戏化通常有效或通常冲突，也不能给出 LearnFlow 的用户效果。它的价值在于把“写在设计中的干预”与“可接受经验评价的实现”分开，并给出下一阶段必须补齐的字段与日志。

进一步运行评价需先选择要真正实现的机制，说明其触发、剂量及对照，再以预先固定指标分析。增加生产者数本身不是研究结果，不能以常量候选工厂制造更多效果来证明机制有效。本章不延续路线 A 的生产者扩充与合成冲突率主张。

对治理效果的经验主张还需要独立评价。未来若重新开展，应在运行之前定义治理与无治理条件、健康否决边界、冲突候选分母及主要结果。当前路线 B 只保留内部静态审计和实现诊断。

## 8 封存逐项证据

以下表按封存注册表直接抽取，不依据当前开发状态重新给成熟度评分。最后一列是新工具在封存源码中的字面量扫描证据，未识别不能解释为没有实现或不可达。此表不将生命周期stage填入trigger，也不将局部priority当作全登记precedence。

| ID | 登记key | 历史成熟度 | 封存实现引用 | 新扫描证据 |
|---|---|---|---|---|
| LF-M01 | variable_ratio_reward | complete | gamification_service.py:GamificationService | 本扫描未识别字面量候选 |
| LF-M02 | near_miss | complete | gamification_service.py:139 | 本扫描未识别字面量候选 |
| LF-M03 | dopamine_rhythm | partial | gamification_service.py:460 | 本扫描未识别字面量候选 |
| LF-M04 | instant_gratification | partial | positive_addiction_engine.py:588 | 本扫描未识别字面量候选 |
| LF-M05 | surprise_delight | partial | addiction_engine_v3.py:199 | 本扫描未识别字面量候选 |
| LF-M06 | time_based_bonus | complete | duolingo_addiction_engine.py:TimeBasedBonusEngine | 本扫描未识别字面量候选 |
| LF-M07 | collection | partial | deep_addiction_engine.py:CollectionEngine | 本扫描未识别字面量候选 |
| LF-M08 | scarcity | partial | deep_addiction_engine.py:461 | 本扫描未识别字面量候选 |
| LF-M09 | loss_aversion | partial | addiction_engine_v3.py:7 | 本扫描未识别字面量候选 |
| LF-M10 | sunk_cost_reminder | partial | addiction_engine_v3.py:36 | 本扫描未识别字面量候选 |
| LF-M11 | streak | complete | duolingo_addiction_engine.py:DuolingoStreakEngine | 本扫描未识别字面量候选 |
| LF-M12 | streak_sanctification | partial | deep_addiction_engine.py:308 | 本扫描未识别字面量候选 |
| LF-M13 | zeigarnik | partial | addiction_engine_v3.py:108 | 本扫描未识别字面量候选 |
| LF-M14 | peak_end | partial | addiction_engine_v3.py:163 | 本扫描未识别字面量候选 |
| LF-M15 | goal_gradient | partial | gamification_service.py:GamificationService.get_goal_progress | 本扫描未识别字面量候选 |
| LF-M16 | daily_challenge | complete | duolingo_addiction_engine.py:MonthlyChallengeEngine | 本扫描未识别字面量候选 |
| LF-M17 | autonomy_support | partial | habit_addiction_engine.py:159 | 本扫描未识别字面量候选 |
| LF-M18 | ikea_effect | partial | gamification_service.py:623,615 | 本扫描未识别字面量候选 |
| LF-M19 | xp_leveling | placeholder | duolingo_addiction_engine.py:XPEngine | 本扫描未识别字面量候选 |
| LF-M20 | progress_visualization | partial | positive_addiction_engine.py:649 | 本扫描未识别字面量候选 |
| LF-M21 | progressive_disclosure | partial | ux_addiction_engine.py:119 | 本扫描未识别字面量候选 |
| LF-M22 | pet_companion | complete | pet_service.py | 本扫描未识别字面量候选 |
| LF-M23 | social_proof | partial | gamification_service.py:659 | 本扫描未识别字面量候选 |
| LF-M24 | social_contagion | partial | positive_addiction_engine.py:506 | 本扫描未识别字面量候选 |
| LF-M25 | peer_progress | partial | deep_addiction_engine.py:292 | 本扫描未识别字面量候选 |
| LF-M26 | friendly_competition | partial | positive_addiction_engine.py:538 | 本扫描未识别字面量候选 |
| LF-M27 | leaderboard | complete | duolingo_addiction_engine.py:LeagueEngine | 本扫描未识别字面量候选 |
| LF-M28 | business_card | placeholder | social_addiction_engine.py:55 | 本扫描未识别字面量候选 |
| LF-M29 | gift_economy | placeholder | social_addiction_engine.py:411 | 本扫描未识别字面量候选 |
| LF-M30 | friend_quest | partial | duolingo_addiction_engine.py:FriendQuestEngine | 本扫描未识别字面量候选 |
| LF-M31 | team_competition | partial | team_competition_engine.py:103,288,389,487,556,651 | 本扫描未识别字面量候选 |
| LF-M32 | parent_portal | placeholder | social_addiction_engine.py:288 | 本扫描未识别字面量候选 |
| LF-M33 | hook_model | partial | positive_addiction_engine.py:67 | 本扫描未识别字面量候选 |
| LF-M34 | habit_loop | partial | positive_addiction_engine.py:262 | 本扫描未识别字面量候选 |
| LF-M35 | cue_prompting | partial | positive_addiction_engine.py:322 | 本扫描未识别字面量候选 |
| LF-M36 | habit_stacking | partial | habit_addiction_engine.py:27 | 本扫描未识别字面量候选 |
| LF-M37 | temptation_bundling | partial | habit_addiction_engine.py:80 | 本扫描未识别字面量候选 |
| LF-M38 | implementation_intentions | partial | habit_addiction_engine.py:109 | 本扫描未识别字面量候选 |
| LF-M39 | self_regulation_goals | partial | habit_addiction_engine.py:SelfRegulationEngine | 本扫描未识别字面量候选 |
| LF-M40 | skill_tree | partial | meta_learning_skilltree.py:157 | 本扫描未识别字面量候选 |
| LF-M41 | commitment_device | partial | deep_addiction_engine.py:388 | 本扫描未识别字面量候选 |
| LF-M42 | fresh_start | partial | addiction_engine_v3.py:51 | 本扫描未识别字面量候选 |
| LF-M43 | curiosity_gap | partial | deep_addiction_engine.py:25 | 本扫描未识别字面量候选 |
| LF-M44 | fomo | partial | deep_addiction_engine.py:238 | 字面量候选 |
| LF-M45 | serendipity | placeholder | deep_addiction_engine.py:542 | 本扫描未识别字面量候选 |
| LF-M46 | identity_motivation | partial | positive_addiction_engine.py:348 | 本扫描未识别字面量候选 |
| LF-M47 | micro_interaction | partial | ux_addiction_engine.py:24 | 本扫描未识别字面量候选 |
| LF-M48 | color_psychology | partial | ux_addiction_engine.py:210 | 本扫描未识别字面量候选 |
| LF-M49 | spatial_anchoring | placeholder | ux_addiction_engine.py:290 | 本扫描未识别字面量候选 |
| LF-M50 | multisensory_packaging | placeholder | ux_addiction_engine.py:345,482,524 | 本扫描未识别字面量候选 |
| LF-M51 | forced_rest | partial | feedback_service.py:198 | 本扫描未识别字面量候选 |
| LF-M52 | minor_protection | complete | anti_addiction_compliance.py:MinorProtectionEngine | 字面量候选 |
| LF-M53 | lai_downgrade | placeholder | learning_addiction_index.py | 本扫描未识别字面量候选 |
| LF-M54 | class_pet | complete | class_pet_service.py | 本扫描未识别字面量候选 |

## 9 静态诊断如何进入工程复核

可追溯审计应先固定输入代码，而非只固定表格数字。本文的注册表抽取采用ast.literal_eval，不导入应用，也不运行数据库初始化。代码引用、源码SHA256与版本共同构成定位依据。单行号或多行号引用只能定位文本，不能自动证明该位置仍对应登记机制；文件级引用还缺具体符号。因此，当前报告将40条行号引用和3条文件引用保留为待核读，并不推断43条都是错误实现。

新原型的显式字段覆盖口径与本章四字段缺失诊断不同。新工具只问七字段是否逐项写入literal登记，得到54×7的缺失记录；本章同时参考stage、外部方向账本及运行对象属性，说明四个schema部分没有对应实现。两种证据可并列，不能把378当成独立缺陷数量或追溯更改封存结果。

研究任务的下一层是独立审计方法，而不是提高生产者数量。它需要定义诊断规则、保留未知、固定正常与异常样例、说明扫描不支持的语法，并在相同输入下复算。新增的M2工程原型位于tools/intervention_audit，其构造基准与外部源引用检查是另行评价，不能追溯为历史LearnFlow用户冲突率。详细方法与证据以M2_engineering_EN.md为准。

对源码构造、运行仲裁、实际展示和用户响应，应使用不同日志事件与分母。若将来需要运行评价，应验证每个事件确实经过真实路径，并对拒绝展示、重复提交、撤回和保护约束分别测试。当前没有采集此类用户事件，因此本章不计算冲突处理成功率或学习收益。工程测试可以不招募真人，但其结论必须限定在工程属性。

## 10 结论

本章的可复核结论是内部登记与实际可用审计证据之间的差距。54项登记、2个历史效果生产者、9/37/8成熟度分别回答不同问题。缺字段和引用不确定性为补齐装置提供具体任务，不是对游戏化心理理论的普遍反证。单作者兼任系统设计与实现，使判断独立性受限；外部源引用测试不能消除此限制。本章保留学位论文定位，新工程稿独立论证可复用工具，避免重新把旧路线A的未接受结果作为投稿依据。
