# LearnFlow 难度适配引擎 v2（Difficulty Adaptation Engine v2）设计

> **版本** v2.0-draft | **日期** 2026-09-02 | **作者** 顾因果（计量经济学 / 因果推断）
> **上游文档** `docs/LearnFlow_学术论文转化方案.md`（§5.3 参数标定、§8 实验设计）
> **代码基线** `learnflow-backend/app/services/`：`optimal_difficulty.py`(564) · `learning_orchestrator.py`(667) · `dda.py`(170) · `knowledge_tracing.py`(217) · `placement_test_engine.py`(383) · `spaced_repetition.py`(93)
> **需求原话** "优化学习难度适配模块确保能够通过 ai 和算法给出适合学习的难度（有挑战又不会想放弃）"

---

## 0. 结论先行

v1 的问题不是"参数没调好"，而是**架构层面的范畴错误**：`optimal_difficulty.py` 输出的是**优化问题的解**（目标难度），BKT 输出的是**知识状态的估计**，DDA 输出的是**上一个动作的增量修正**。把三者当作"对同一隐变量的三次带噪测量"做线性加权（`orchestrator.py:511-516`），在统计上说不通，也无法推导权重。

v2 的重构只有一句话：

> **把三个源全部转成对同一个潜变量（学习者能力 $\theta$）的估计并给出方差，用精度加权融合；然后用一个显式的、可证伪的目标函数把后验映射为决策。**

由此得到四个可发表的结果：

| # | 结果 | 位置 |
|---|---|---|
| R1 | 统一潜变量尺度 **LDS**（logit 单位）下，v1 的 Elo↔FSRS 线性桥接隐含难度区分度 $\kappa_{v1}=0.8954$ logit/点，**约为可标定值的 2 倍**，v1 的难度阶梯实际只有 4–5 个可用层级 | §2 |
| R2 | 心流通道定义为**留存折现学习率目标的超水平集** $\mathcal{F}_\eta$；一阶条件给出 $\Delta^{*2}=1-\psi(A)\Delta\phi(\Delta)\frac{dA}{dp}$，**85% 规则是 $\frac{dA}{dp}=0$ 时的特例**，偏离方向与幅度由放弃梯度决定 | §3 |
| R3 | 难度是**有序+连续**动作空间，用**层级化理论基 Thompson 采样（HTI-TS）**；探索同时是放弃模型与异质最优正确率的**识别装置** | §4–§5 |
| R4 | 离线反事实评估必须**三层递进**（IPS/DR → 半合成回放 → 多学习者模型秩稳定性检验），单一方法不足以支撑任何 claim | §11.1 |

**最大技术风险**：放弃概率 $A(\cdot)$ 的识别。它是稀有事件、在静态数据中不存在标签、且与难度内生共线。若识别失败，$\mathcal{J}$ 退化为 $G$，v2 退化为 85% 规则。缓解方案与"精度闸门"见 §3.5、§11.4。

---

## 1. 现状解剖：六处可数值验证的缺陷

以下每一条都能用现有代码直接算出，不是定性抱怨。

### D1 · 难度阶梯斜率过陡（隐含区分度失真）

v1 的两条桥接（`optimal_difficulty.py:56-57, 536-542`）：

$$d = 1 + \frac{\text{Elo}-800}{1400}\cdot 9,\qquad \text{Elo} = 800 + \frac{d-1}{9}\cdot 1400$$

Elo 的期望得分是 logistic：$P = 1/(1+10^{(d_{Elo}-\theta)/400}) = \sigma\!\big(\lambda(\theta-d_{Elo})\big)$，其中

$$\lambda = \frac{\ln 10}{400} = 5.7565\times 10^{-3}\ \text{logit/分}$$

复合得到 **1 个 FSRS 难度点对应的 logit 变化**：

$$\kappa_{v1} = \lambda\cdot\frac{1400}{9} = \frac{\ln 10\cdot 1400}{400\cdot 9} = \frac{3223.6}{3600} = 0.8954\ \text{logit/点}$$

验证：$\theta=1500$ 的学习者，d=5 → $P=0.610$，d=6 → $P=0.390$。跨一个难度等级，成功率掉 22 个百分点；1→10 全程 logit 跨度 $9\times0.8954 = 8.06$， odds ratio $=e^{8.06}\approx 3166$。

对比：标定过的数学题库（如 ASSISTments 2017）的难度参数跨度通常 3–5 logit。若 10 级阶梯对应 4 logit，则 $\kappa\approx0.44$。**可证伪预测 H-κ：$\hat\kappa = 0.40 \pm 0.15$，v1 高估约 2 倍。**

### D2 · $\sigma$（不确定性）恒为常数，自适应机制是死代码

`EloRating.update:276-280`：

```python
rd_factor = (1.0 - e) * e * k * k
new_sigma = math.sqrt(max(25.0, self.DEFAULT_SIGMA**2 - rd_factor))
```

分子用的是**类常量** `DEFAULT_SIGMA=350`，不是用户的当前 $\sigma$。取 $e=0.5,\ k=32$：$rd\_factor = 0.25\times1024 = 256$，$\sqrt{122500-256}=349.63$；$k$ 衰减到 8 时 $\to 349.98$。**$\sigma\in[349.6, 350.0]$ 恒成立**，永不下降，也永不随时间膨胀（无遗忘）。

后果：`compute_optimal_difficulty:442-445` 的 `uncertainty = clamp((σ-25)/325) = 1.0`，`regression_weight = 0.2` **对所有用户、所有时刻恒定**。所谓"新用户回归中等难度"从未生效。

更糟的是系统里存在**三套互不一致的 $\sigma$**：`AbilityEstimate.sigma`（≈350 恒定）、`orchestrator.py:110` 的 `350 - min(325, n*6)`（55 题后触底 25）、以及上面的 Elo RD。

### D3 · BKT→难度有两套映射，取决于缓存是否命中

```python
orchestrator.py:99   bkt_recommended = int(max(1, min(10, round(m*9+1))))     # 缓存命中
orchestrator.py:108  bkt_recommended = bkt_engine.recommend_difficulty(...)   # 未命中 → int(m*10)+1，再 ±1
```

$m=0.5$ 时前者给 6，后者给 6（$0.5\times10+1=6$，再因 expected_success$=0.5(0.9)+0.5(0.08)=0.49 < 0.80$ 减 1 → **5**）。同一学生、同一时刻，缓存命中与否给出不同难度。

### D4 · 前向映射与后向更新不构成互逆，定点不是 MLE

前向（`_elo_to_fsrs_difficulty`，Elo 一致）；后向（`FSRSStyleDifficulty.update_difficulty`）：

$$D' = w_7 D_0 + (1-w_7)\big(D - w_6(r-3)\big),\quad r\in\{1,3,4\}$$

步长 $\Delta D \in \{+0.32,\ 0,\ -0.16\}$（乘上 $1-w_7=0.8$）——**与学习者能力 $\theta$ 无关、与当前 $D-\theta$ 的距离无关**。一个 $\theta$ 极高的学生答错，和一个 $\theta$ 极低的学生答错，产生相同的难度漂移。该更新不是任何似然的梯度，复合映射的定点不是 $\hat\beta_{MLE}$。

### D5 · `challenge_band` 是纯字面量

```python
orchestrator.py:195-199
"current": int(task.difficulty * 10),   # 难度 5 → 50
"low": 75, "high": 85,                  # 硬编码
```

`current` 是难度×10，而 `low/high` 被当作**成功率百分比**。量纲不同、且当 `difficulty ≤ 7` 时 `current < low` 恒成立。前端的心流指示器与后端的任何计算无关。

### D6 · 间隔复习系统在选题路径上完全缺席

`SpacedRepetitionService` 与 `SpacedReview` 表存在，`process_submission:309-322` 也在写复习计划，但 `build_next_task` **从不查询 `SpacedReview`**。到期复习题永不出现在下一题里，遗忘曲线与难度决策完全脱钩。

---

## 2. 统一量纲：Latent Difficulty Scale（LDS）

### 2.1 尺度定义

定义潜变量尺度 $\mathcal{Z}=\mathbb{R}$，**单位为"成功 odds 的 1 个 logit"**。

- 学习者能力 $\theta_u \in \mathcal{Z}$；题目难度 $\beta_i \in \mathcal{Z}$。
- 锚定：总体中位题目难度 $\beta=0$；基线时刻总体中位能力 $\theta=0$。

**测量模型（2PL + 猜测参数）**

$$P(y_{ui}=1\mid\theta_u,\beta_i) = c_i + (1-c_i)\,\sigma\!\big(a_i(\theta_u-\beta_i)\big),\qquad \sigma(x)=\frac{1}{1+e^{-x}}$$

能力估计的不确定性 $\theta_u\sim\mathcal{N}(\mu_u, s_u^2)$，题目难度不确定性 $\beta_i\sim\mathcal{N}(\hat\beta_i, \varsigma_i^2$。

### 2.2 三条桥接（可逆）

**桥接 1 · Elo → Z.** Elo/400 本质是 **logistic IRT**，尺度为 $\lambda=\ln 10/400$：

$$\boxed{\ \theta = \lambda(\theta^{Elo} - \theta_0^{Elo}),\qquad \beta = \lambda(\beta^{Elo}-\theta_0^{Elo}),\qquad \lambda=\tfrac{\ln 10}{400}\ }$$

锚点 $\theta_0^{Elo}$ 任意（模型只看差值）。代入后 $P=\sigma(\theta-\beta)$，即标准 Rasch。**这是 v1 已经隐含、但从未显式利用的事实。**

**桥接 2 · FSRS $D$ → Z（斜率可标定，这是 R1 的载体）**

$$\boxed{\ \beta = \kappa\,(D - D_{mid}),\qquad D = D_{mid} + \frac{\beta}{\kappa}\ }$$

$D_{mid}=5.5$，$\kappa>0$ 为**全局标定参数**（单位 logit / FSRS 点），取代硬编码的 $\kappa_{v1}=0.8954$。

**桥接 3 · BKT 掌握度 → Z.** BKT 不产生难度，它产生**预测成功率**：

$$p_{BKT} = m(1-s) + (1-m)g,\qquad s=p_{slip},\ g=p_{guess}\ \ \text{(Corbett \& Anderson 1995)}$$

与测量模型联立，反解出能力：

$$\boxed{\ \hat\theta_{BKT} = \beta_{last} + \mathrm{logit}(p_{BKT}) = \beta_{last} + \ln\frac{p_{BKT}}{1-p_{BKT}}\ }$$

其中 $\beta_{last}$ 是最近一题的难度。**v1 的 `int(m*10)+1` 丢弃了这层结构。**

### 2.3 能力融合：精度加权，而非难度加权

| 源 | 原生输出 | → $\hat\theta$ | 方差 $\widehat{\mathrm{Var}}$ |
|---|---|---|---|
| BKT | $m$（按知识点 $k$） | $\beta_{last} + \mathrm{logit}(p_{BKT})$ | delta 法：$\left[\frac{1-s-g}{p(1-p)}\right]^2\frac{m(1-m)}{\nu_k+1} + \varsigma^2_{last}$ |
| Elo/Glicko | $\theta^{Elo}$ | $\lambda(\theta^{Elo}-\theta_0^{Elo})$ | $(\lambda\,\mathrm{RD})^2$，RD 按正确 Glicko 递推（修复 D2） |
| DDA 窗口 | 近 $W$ 题结果 | **Rasch 窗口 MLE** | $1/\mathcal{I}$，$\mathcal{I}=\sum_{j\in W}\hat p_j(1-\hat p_j)$ |
| LLM 题目先验 | —（作用于 $\beta$ 侧） | — | 见 §9 |

**DDA 升级为 Rasch 窗口 MLE**（替换 `dda.py` 的原始窗口成功率）：

$$\hat\theta_{DDA} = \arg\max_\theta \sum_{j\in W}\Big[y_j\log\sigma(\theta-\beta_j) + (1-y_j)\log\big(1-\sigma(\theta-\beta_j)\big)\Big]$$

单参数 logistic 回归，Newton 迭代 3 步收敛。当窗口内所有 $\beta_j=\bar\beta$ 相等时，退化为 $\hat\theta = \bar\beta + \mathrm{logit}(\hat p)$——**v1 的窗口成功率是它的特例**，且 $\widehat{\mathrm{Var}} = 1/\mathcal{I}$ 直接替代了 `dda.py:128` 那个无意义的 `confidence = len(window)/window_size`。

**层级结构**（解决 BKT 按知识点、Elo 全局的量纲错配）：

$$\theta_{u,k} = \theta_u^{global} + \delta_{u,k},\qquad \delta_{u,k}\sim\mathcal{N}(0,\ \omega^2)$$

BKT 贡献 $\delta_{u,k}$ 的信息，Elo/Glicko 贡献 $\theta_u^{global}$，二者在同一可加空间内，无需任何"权重"。

**融合（正态-正态共轭）**

$$\hat\theta_u = \frac{\sum_k \tau_k \hat\theta_k + \tau_0\mu_0}{\sum_k\tau_k + \tau_0},\qquad s_u^2 = \frac{1}{\sum_k\tau_k + \tau_0},\qquad \tau_k = 1/\mathrm{Var}_k$$

**这就是 0.45/0.35/0.20 的替代品**：权重不再是常量，而是**数据驱动的精度**，且每一次决策的 $(\hat\theta_k, \tau_k, \hat\theta_u, s_u)$ 全部落库（`DifficultyDecisionLog`，见 §10），因此权重本身**可被 A/B、可被审计、可被报告置信区间**。这是 v1 做不到的（`ability_estimates` 表只有 θ/σ）。

### 2.4 不确定性如何进入决策（替换魔法数字 0.2）

Logistic-高斯积分的标准近似：

$$p(\beta_i) = \mathbb{E}\big[\sigma(\theta-\beta_i)\big] \approx \sigma\!\left(-\frac{\beta_i - \mu_u}{\sqrt{1 + \frac{\pi^2}{8}(s_u^2 + \varsigma_i^2)}}\right)$$

**不确定性把预测成功率曲线压平**，使早期决策自动趋于保守。这是 D2 中"σ 自适应回归"的**有理论依据的替代品**：不是人工回归到 $d=5$，而是方差进入似然后的必然结果，且当 $s_u\to0,\varsigma_i\to0$ 时自动恢复点估计。

---

## 3. 心流通道的形式化定义

### 3.1 学习增益项 $G$

沿用 Wilson et al. (2019, *Nat. Commun.*)，并做如下推广：设反馈噪声密度为 $f$、CDF 为 $F$，则单题期望学习增益

$$G \propto \Delta\,f(\Delta),\qquad \Delta := F^{-1}(p)$$

最大化：$\frac{d}{d\Delta}[\Delta f(\Delta)] = 0$。三种分布（**v1 的 `DISTRIBUTION_TARGETS` 已正确实现，无需修改**）：

| 噪声 | $f(\Delta)$ | $\arg\max$ | $p^*=F(\Delta^*)$ |
|---|---|---|---|
| Gaussian | $\phi(\Delta)$ | $\Delta^*=1$ | $\Phi(1)=0.8413$ ✓ |
| Laplace | $\tfrac12 e^{-|\Delta|}$ | $\Delta^*=1$ | $1-\tfrac12 e^{-1}=0.8161$ ✓ |
| Cauchy | $\frac{1}{\pi(1+\Delta^2)}$ | $\Delta^*=1$ | $\tfrac12+\tfrac{\arctan 1}{\pi}=0.7500$ ✓ |

取标准 Gaussian，归一化使峰值 $=G_{max}$：

$$\boxed{\ G(p) = G_{max}\cdot\frac{\Delta(p)\,\phi(\Delta(p))}{\phi(1)},\qquad \Delta(p)=\Phi^{-1}(p)\ }$$

注：$p<0.5$ 时 $G<0$，即"反馈方向与已有表征反相关"。我们不人为截断，因为下面的放弃项会在该区域主导，使 $\arg\max$ 自然落在 $p>0.5$（§3.4 证明）。

### 3.2 放弃概率 $A$：可估计的估计器

**放弃的可观测定义**（需要新增 `TaskServe` 表，见 §10）：

令 $\Delta_{max}=7$ 天为会话截断窗。以下任一命中记 $A_t=1$：

| 代理 | 定义 | 现有数据可得性 |
|---|---|---|
| $S_1$ 跳过 | 派发后 $3\times$`time_estimate` 内无 `Attempt` | ❌ 需 `TaskServe` |
| $S_2$ 超时 | `time_spent > 3 × time_estimate` | ✅ |
| $S_3$ 连败退出 | $k\!\geq\!2$ 连败后 $\geq\Delta_{max}$ 无作答 | ✅ |
| $S_4$ 提示耗尽 | `hints_used == 3` 且仍答错 | ✅ |
| $S_5$ 末题失败 | 会话最后一个事件是失败 | ✅ |

**两层脆弱性（frailty）logistic 模型**

$$\mathrm{logit}\, P(A_t = 1) = \underbrace{\alpha_u}_{\text{学习者脆弱性}} + \gamma_1\mathbb{1}[y_t=0] + \gamma_2 f_{streak}(c_t) + \gamma_3 g(\rho_t) + b^{+}[m_t]_{+} - b^{-}[-m_t]_{+} + \mathbf{x}_t^\top\boldsymbol\delta$$

$$m_t := \beta_t - \hat\theta_u \quad(\text{难度失配，logit}),\qquad c_t = \text{此前连败数},\qquad \rho_t = \frac{time\_spent}{time\_estimate}$$

$$\alpha_u \sim \mathcal{N}(\alpha_0 + \mathbf{z}_u^\top\boldsymbol\zeta,\ \tau_\alpha^2)$$

$m_t$ 的**双向**项是关键：过度简单（$b^{-}$，无聊性放弃）与过度困难（$b^{+}$，焦虑性放弃）都提高放弃概率，这正是 Csikszentmihalyi 通道的统计形态。

**识别问题（必须正面处理）**：$\beta_t$ 由策略根据 $\hat\theta_u$ 选择，故 $\mathrm{Corr}(\beta_t,\alpha_u)\neq0$，直接回归 $A$ 对 $m$ 是内生的。

> **识别装置 = §4 的探索。** 策略注入已知随机扰动 $\varepsilon_t$，$\beta_t = \beta^*_t + \varepsilon_t$。条件于状态 $h_t$，$\varepsilon_t$ 与 $\alpha_u$ 独立，是一个**合法的工具变量 / 随机剂量**。仅用 $\varepsilon_t$ 诱导的变异估计 $b^{\pm}$。

### 3.3 目标函数与推导

设学习者面对（近似）恒定的难度 $\beta$，每题放弃概率 $A(\beta)$，规划视界 $T$ 题。存活到第 $k$ 题的概率 $(1-A)^k$，故**有效视界**

$$H(A) := \sum_{k=0}^{T-1}(1-A)^k = \frac{1-(1-A)^T}{A},\qquad H\in[1,\,T]$$

期望总学习量：

$$\boxed{\ \mathcal{J}(\beta;\ \theta_u, T) \;=\; \underbrace{G\big(p(\beta)\big)}_{\text{单题学习增益}}\;\cdot\;\underbrace{H\big(A(\beta)\big)}_{\text{留存折现有效视界}}\ }$$

**定义（心流通道）**：给定容忍度 $\eta\in(0,1)$，

$$\boxed{\ \beta^* = \arg\max_{\beta}\ \mathcal{J}(\beta),\qquad \mathcal{F}_\eta = \big\{\beta:\ \mathcal{J}(\beta)\geq (1-\eta)\,\mathcal{J}(\beta^*)\big\}\ }$$

这就是"**有挑战又不会想放弃**"的可计算定义：它不是固定的 $[0.75,0.85]$ 成功率区间，而是**留存折现学习率目标的超水平集**——随学习者、随能力、随时间变化，且完全由数据决定。前端 `challenge_band` 应渲染 $\mathcal{F}_\eta$ 在 0–100 尺度上的投影（修复 D5）。

### 3.4 一阶条件与比较静态（核心定理）

令 $\ell = \ln\mathcal{J}$。用 $p=\sigma(-m)$、$\frac{d\Delta}{dm} = -\frac{p(1-p)}{\phi(\Delta)}$，得

$$\frac{d\ln G}{dm} = \frac{(\Delta^2-1)\,p(1-p)}{\Delta\,\phi(\Delta)}$$

定义**留存敏感度** $\psi(A) := -\dfrac{H'(A)}{H(A)} > 0$（$H$ 在 $A$ 上单调递减，且 $\psi(0)=\frac{T-1}{2}$ 有限，无奇点）。由 $A'(m) = -p(1-p)\frac{dA}{dp}$，一阶条件化简为：

$$\boxed{\ \Delta^{*2}\;=\;1\;-\;\psi(A^*)\,\Delta^*\,\phi(\Delta^*)\,\left.\frac{dA}{dp}\right|_{p^*}\ }$$

**推论（比较静态）**

1. $\left.\frac{dA}{dp}\right|_{p^*}=0$（放弃对难度不敏感）$\Rightarrow \Delta^*=1 \Rightarrow p^*=0.8413$。**85% 规则是本目标函数的特例。**
2. $\frac{dA}{dp}<0$（焦虑主导，越难越放弃）$\Rightarrow \Delta^*>1 \Rightarrow \boxed{p^*>0.8413}$，最优难度**比 85% 规则更容易**。
3. $\frac{dA}{dp}>0$（无聊主导，越易越放弃）$\Rightarrow \Delta^*<1 \Rightarrow p^*<0.8413$，最优难度**比 85% 规则更难**。

**推论 4（内点解存在性）**：$G(p)$ 在 $p=0.5$ 与 $p\to1$ 处均为 0，于 $p=\Phi(1)$ 取正的最大值；$H(A)\in[1,T]$ 有界正。故 $\mathcal{J}$ 在 $p\in(0.5,1)$ 上连续、两端趋于 0 或很小，最大值必在**内点**取得。$\blacksquare$

**数值示例**（说明效应量可测）：取 $T=40$，$A(p)=\mathrm{expit}(a_0 + 2(1-p))$，标定使 $A(0.8413)=0.06$。
则 $\frac{dA}{dp} = -2\cdot0.06\cdot0.94 = -0.1128$；$H(0.06)=15.27$，$H'(0.06)=-194.7$，$\psi=12.75$。
$$\Delta^{*2} = 1 + 12.75\times0.2420\times0.1128 = 1.348 \Rightarrow \Delta^*=1.161 \Rightarrow p^*=\Phi(1.161)=\mathbf{0.877}$$
即：**84.1% → 87.7%，3.6 个百分点的可测偏移。** 预注册假设 H6 检验的正是这个量。

### 3.5 数值求解与主循环

$\mathcal{J}$ 对 $\beta$ 一维光滑。用 Brent 法在 $[\mu_u-4,\ \mu_u+4]$（logit）上求极大，或直接对 FOC 做 Newton。确定性、可复现、**无 LLM 参与**。

```python
def flow_optimal_beta(mu, s2, A_model, T, kappa, guard):
    """返回 (beta_star, J_star, F_eta_band)"""
    def J(beta):
        p = sigmoid(-(beta - mu) / sqrt(1 + pi**2 * (s2 + var_beta) / 8))
        if p <= 0.5:  return 0.0                 # G <= 0 区域
        Dl = norm.ppf(p)
        G  = G_max * Dl * norm.pdf(Dl) / norm.pdf(1.0)
        A  = clip(A_model.predict(p=p, m=beta - mu), 1e-4, 0.95)
        H  = (1 - (1 - A) ** T) / A
        return G * H
    beta_star = brent_max(J, mu - 4, mu + 4)
    # 安全护栏：放弃概率硬上限 + 无聊下限
    beta_star = clamp(beta_star, guard.beta_min, guard.beta_max)
    band = level_set(J, (1 - ETA) * J(beta_star))   # F_eta
    return beta_star, J(beta_star), band
```

**安全护栏（不可绕过）**：$\hat A(\beta) \leq A_{max}=0.35$（"不会想放弃"的硬约束，对未成年人学段收紧至 0.25）；$\beta \geq \mu_u - 3.0$（无聊下限）。护栏优先于 $\arg\max$，且护栏触发事件单独落库审计。

---

## 4. 探索-利用：有序 + 连续动作空间上的结构化 Bandit

### 4.1 为什么标准 TS/UCB 在这里不合适

1. **臂不独立**：难度 5 与难度 6 的回报高度相关。独立臂假设下需要 $O(K)$ 次探索，$K=10$ 时样本效率极低。
2. **"10 个臂"是 UI 的假象**：FSRS 难度 $D$ 与 LDS 的 $\beta$ 本质连续，1–10 只是前端刻度。**正确 framing 是连续臂 Lipschitz bandit**（Kleinberg et al. 2008），regret $\tilde O(T^{2/3})$ **与 $K$ 无关**。
3. **纯贪心导致不可识别**：无探索则 $\beta$ 与 $\theta$ 完全共线，§3.2 的 $A$ 与 §5 的 $p^*_u$ 均无法估计。

### 4.2 HTI-TS：层级化理论基 Thompson 采样

**理论基**：不用无结构 GP，而用理论给出的**基函数 + 学到的系数**：

$$r(\beta) = \underbrace{\boldsymbol\phi(\beta)^\top\mathbf{w}_u}_{\text{结构化}} + \underbrace{\eta(\beta)}_{\mathcal{GP}(0,k)},\qquad \boldsymbol\phi(\beta) = \big[1,\ \tilde G(\beta),\ -\tilde A(\beta),\ \tilde G\!\cdot\!\tilde A\big]$$

其中 $\tilde G,\tilde A$ 是 §3 的归一化分量。$k(\beta,\beta')=\sigma_f^2\exp\!\big(-\tfrac{(\beta-\beta')^2}{2\ell^2}\big) + \sigma_{lin}^2\beta\beta'$（RBF 编码相邻相关，线性项编码"越难教得越多"的趋势）。

**层级**：$\mathbf{w}_u = \mathbf{w}_0 + \boldsymbol\xi_u,\ \boldsymbol\xi_u\sim\mathcal{N}(0,\Sigma_w)$。新用户直接借用总体，只需学残差 $\boldsymbol\xi_u$ → **冷启动与探索量同时被压到最小**。

**算法**

```
HTI-TS(learner u, state (mu_u, s_u), population posterior p(w0, Σw), GP posterior):
  # 1. 个体后验（层级收缩，正态-正态共轭）
  post_wu = N( (Σw⁻¹ + XᵀX/σₙ²)⁻¹ (Σw⁻¹w0 + Xᵀr/σₙ²),  (Σw⁻¹ + XᵀX/σₙ²)⁻¹ )

  # 2. Thompson 采样（M = 2000 次）
  for m in 1..M:
      w̃ ~ post_wu ;  f̃ ~ GP posterior ;  ã ~ post(abandonment params)
      for d in candidate_grid:                      # 连续 β 网格，非 1..10
          Ĵ_m(d) = φ(d)ᵀw̃ + f̃(d)                    # 或直接用 §3.5 的 J(d; ã)
      Ĵ_m ← UnimodalProject(Ĵ_m)                     # 单峰锥投影（有序结构约束）
      d_m* = argmax_d Ĵ_m(d)
  π_TS(d) = (1/M) Σ_m 1[d_m* = d]                    # 精确的 TS 选择概率 → 可记录

  # 3. ε-混合，保证 positivity（offline IPS 的必要条件）
  π(d) = (1-ε)·π_TS(d) + ε/|grid| ,  ε = 0.10  ⇒  π(d) ≥ 0.01 > 0

  # 4. 安全护栏截断 + 重归一化
  π ← π · 1[Â(d) ≤ A_max] ; π ← π / Σ π

  # 5. 采样、派发，并记录 (candidates, scores, π, policy_version)
```

三个结构装置对应三个 novelty：

| 装置 | 作用 | 代价 |
|---|---|---|
| GP / 连续臂 | 相邻难度共享信息；regret 与 $K$ 无关 | 核超参需标定（用历史数据 EB 估计 $\ell,\sigma_f$） |
| 单峰锥投影 | 与理论一致的后验收缩，剪枝搜索 | 近似（精确做法是约束 GP 后验，见 Lin & Dunson 2014） |
| 层级先验 | 新用户零探索启动；个体仅学残差 | 需总体后验持续更新（周级批处理） |

**$\pi_TS$ 的 Monte-Carlo 估计与 $\varepsilon$ 混合是 §11.1 离线评估的前提**——没有可重建的倾向得分，IPS 根本无法计算。这是 v1 完全缺失的基础设施。

### 4.3 探索作为识别装置（跨章节的关键连接）

探索不是"为了长期 regret"，在本设计中它承担三项**统计识别**职责：

1. 打破 $\beta_t$ 与 $\alpha_u$ 的共线 → 识别放弃梯度 $b^{\pm}$（§3.2）
2. 提供 $m_t$ 的变异 → 识别个体最优 $\Delta^*_u$（§5）
3. 提供候选集的随机化 → 题目难度的在线标定不偏（§9）

---

## 5. 异质性最优正确率 $p^*_u$

85% 是群体均值。个体最优可能系统偏离，且**这本身就是可发表的贡献**。

### 5.1 识别策略：嵌入式微随机试验（EMRT）

核心困难：$\delta_t := \hat\theta_{t+1}-\hat\theta_t$ 既是因变量又与 $y_t$ 机械相关，且 $\beta_t$ 由策略选择 → 双重内生。

**解法**：在每个学习者的题流中，以概率 $q=0.12$ 插入**探针题**——从 $[\hat\theta-2.5,\ \hat\theta+2.5]$ logit 内**均匀随机**抽难度，且**不参与能力更新**、不计入游戏化奖励。探针题构成每个学习者内部的**随机化剂量实验**。

由此得到无选择的 $(m, y, \delta)$ 样本，估计：

$$\delta_{it} = c_u + \rho_u\cdot g\big(\Delta(m_{it});\ \Delta^*_u\big) + \varepsilon_{it}$$

$g$ 为增益形状，$p^*_u = \Phi(\Delta^*_u)$ 是**位置参数**，$\Delta^*_u$ 为每个学习者的待估参数。

**层级贝叶斯（小样本稳定）**

$$\Delta^*_u \sim \mathcal{N}\big(\Delta_0 + \mathbf{z}_u^\top\boldsymbol\beta_z,\ \tau_\Delta^2\big),\quad \tau_\Delta\sim \text{Half-}t(3,0,0.5),\quad \Delta_0 \mathrel{\text{先验}} 1.0$$

收缩强度由 $\tau_\Delta$ 与抽样误差之比自动决定，无需人工设定。报告**收缩因子** $\lambda_u = \tau_\Delta^2/(\tau_\Delta^2 + \mathrm{SE}_u^2)$。

### 5.2 DML 估计异质性的调节因子（人群层面）

用 Double Machine Learning (Chernozhukov et al. 2018) 估计**条件平均处理效应**：

$$\delta = \theta_0(\mathbf{z})\cdot m + g_0(\mathbf{z}) + \varepsilon,\qquad \mathbb{E}[\varepsilon\mid m,\mathbf{z}]=0$$

Neyman 正交得分 + $K=5$ 折交叉拟合：

```
1. 按折分割；对每折 k：
   a. 用 ¬k 折拟合 η̂ = (m̂(z), δ̂(z))  ← 梯度提升 / 随机森林
2. 计算残差 m̃ = m - m̂(z),  δ̃ = δ - δ̂(z)
3. θ̂(z) 由 δ̃ = θ(z)·m̃ + e 的（加权）最小二乘给出
4. 用正交矩条件构造置信区间 → 对 η̂ 的一阶误差不敏感
```

用途：检验**哪些**学习者特征（基线能力、年龄学段、先前投入、自我效能）调节最优难度，可直接写成论文的 Table。其正交性保证即使混淆关系用 ML 估计，$\hat\theta(\mathbf{z})$ 仍 $\sqrt{n}$-一致。

### 5.3 预注册的异质性假设

**H5**：$\tau_\Delta > 0.10$ logit（个体最优确实存在有意义的异质性）。
**H6**：$\mathrm{sign}(\hat p^* - 0.8413) = -\mathrm{sign}\big(\widehat{dA/dp}\big)$，且 $| \hat p^* - 0.8413 | > 0.01$。**这是 §3.4 比较静态的直接检验，也是本设计最具可证伪性的预测。**

---

## 6. 时间衰减与遗忘

### 6.1 FSRS 可提取性进入有效能力

FSRS-4 的可提取性（$S$ = 稳定性，定义为 $R=0.9$ 时的间隔；验证：$(1+\tfrac{19}{81})^{-1/2}=(100/81)^{-1/2}=0.9$ ✓）：

$$R(t) = \left(1 + \frac{19}{81}\cdot\frac{t}{S}\right)^{-1/2}$$

**有效能力衰减**：对知识点 $k$，

$$\theta_{u,k}(t) = \theta_{u,k}^{struct} - \underbrace{\zeta_k\big(1 - R_{u,k}(t)\big)}_{\text{遗忘罚项}},\qquad R_{u,k}(t) = \left(1+\frac{19}{81}\cdot\frac{t-t^{last}_{u,k}}{S_{u,k}}\right)^{-1/2}$$

$\zeta_k>0$ 为标定参数（单位 logit）。后果：长期未练的知识点自动降难度（重激活），随 $R$ 回升难度自动爬升。$S_{u,k}$ 用 FSRS-4 的稳定性递推更新。

### 6.2 复习/新题门控（修复 D6）

`build_next_task` 增加一次 `SpacedReview` 查询：若存在 $R < 0.9$ 的到期复习项，则候选集 = 到期复习题 ∪ 新题，并为复习题加入 $s_{time}$ 加分（§8）。

### 6.3 回归者的动机保护

放弃模型 $\mathbf{x}_t$ 中加入 $\log(1+\Delta t^{session}_{gap})$；并对"距上次会话 > 7 天"的回归者，首题难度额外下压 $0.5$ logit（对 $A$ 的乘性折扣），直接服务"不会想放弃"。

---

## 7. 冷启动

| 阶段 | 策略 |
|---|---|
| **T0 注册** | $\theta_u\sim\mathcal{N}(\mu_0(\mathbf{z}_u),\ \sigma_0^2)$，$\mu_0$ 由人口学/学段先验给出；$\mathbf{w}_u = \mathbf{w}_0$（§4.2 层级先验） |
| **T1 定级测试** | 把 `placement_test_engine.py` 从 ±2/±1 启发式升级为 **IRT-CAT**（见下） |
| **T2 前 5 题** | 难度夹在 $[\mu_u-1.0,\ \mu_u+0.5]$，探索率提到 $\varepsilon=0.20$（信息价值最高时多探索） |
| **T3 稳态** | $\varepsilon$ 衰减至 0.10；$\varsigma_i^2$ 随 $n_i$ 收缩 |
| **冷题目** | 用 §9 的 LLM 校准先验 $\mathcal{N}(\mu_{0i},\varsigma^2_{0i})$，随作答数据收缩 |

**IRT-CAT 定级**（替换 `placement_test_engine.py:147-190`）：

$$\text{选题：}\quad i_{next} = \arg\max_{i}\ \mathcal{I}_i(\hat\theta) = \arg\max_i\ a_i^2\,\hat p_i(1-\hat p_i)$$
$$\text{估计：}\quad \hat\theta = \arg\max_\theta\ \Big[\log p(\theta) + \textstyle\sum_j \log p(y_j\mid\theta,\beta_{i_j})\Big]\quad(\text{EAP/MAP})$$
$$\text{停止：}\quad \mathrm{SE}(\hat\theta) = \Big(\textstyle\sum_j \mathcal{I}_{i_j}(\hat\theta) + \sigma_0^{-2}\Big)^{-1/2} \leq 0.4\ \text{logit}\quad \text{或题数} \geq 15$$

本身就是一项 ablation：IRT-CAT vs 现有 ±2 启发式，用**达到同等 SE 所需题数**作为指标。

---

## 8. 选题：从等值匹配到候选排序

替换 `orchestrator.py:130-152` 的 `WHERE difficulty == fused ORDER BY RANDOM() LIMIT 1`。

### 8.1 打分函数

$$s(i) = w_{fit}\,s_{fit}(i) + w_{info}\,s_{info}(i) + w_{cov}\,s_{cov}(i) + w_{div}\,s_{div}(i) + w_{exp}\,s_{exp}(i) + w_{time}\,s_{time}(i)$$

| 项 | 定义 | 说明 |
|---|---|---|
| $s_{fit}$ | $\mathcal{J}(\beta_i)$ 归一化 | **核心：用真实目标而非到整数的距离** |
| $s_{info}$ | $a_i^2\,\hat p_i(1-\hat p_i)$ | Fisher 信息：题目对能力的诊断力 |
| $s_{cov}$ | 知识点图的边际信息增益 | 复用 `curriculum_node_id`；优先低掌握 / 高不确定 / 前置节点 |
| $s_{div}$ | MMR：$-\max_{j\in S_{W}}\mathrm{sim}(i,j)$ | $\mathrm{sim}$ = 主题嵌入余弦 × 题型指示 × 难度邻近 |
| $s_{exp}$ | $-\log(1+n_{serve}(i))$ | 曝光度去偏（类似推荐系统的 popularity 修正） |
| $s_{time}$ | $\max(0,\ 0.9 - R_i(t))$ | 到期复习优先（§6.2） |

**MMR 多样性重排**（$S$ = 最近 $W=10$ 题的滑动窗口）：

$$s_{MMR}(i) = \lambda_{mmr}\,s_{fit}(i) - (1-\lambda_{mmr})\max_{j\in S}\mathrm{sim}(i,j),\qquad \lambda_{mmr}=0.7$$

### 8.2 Softmax 采样与可评估性

$$P(i) = \frac{\exp\big(s_{MMR}(i)/\tau_{sel}\big)}{\sum_{j\in\mathcal{C}}\exp\big(s_{MMR}(j)/\tau_{sel}\big)},\qquad \tau_{sel}=0.15$$

Softmax 而非 argmax 的三个理由：(a) 提供**已知且可记录**的倾向得分；(b) 天然实现探索；(c) 避免病态确定性。

> **工程硬要求（决定 §11 能否做）**：每次决策必须落库 `(policy_version, 候选集 \mathcal{C}, 各分量得分, 最终 s(i), P(i), 采样结果)`。**没有候选集与倾向得分日志，离线反事实评估在数学上不可能。** 这是 v1 缺失的、且比任何算法改动都更关键的基础设施。

---

## 9. LLM 的合理定位：离线标注 + 在线决策

### 9.1 诚实划定边界

**应该用（离线、批处理、版本冻结、可缓存）**

| 环节 | 理由 |
|---|---|
| **题目难度的语义先验标注** | 真正的价值点。题库中大量题目作答数 $n_i\leq5$，统计估计方差极大。LLM 读题面给出难度估计，作为**先验均值** |
| **跨知识点迁移先验** | 新知识点无数据时，用 LLM 估计其与已锚定知识点的相对难度 |
| **题目特征提取** | 主题标签、所需子技能、题型、认知层级（Bloom）、"陷阱"标记 → 作为**统计难度模型的协变量** $\mathbf{x}_i$，LLM 误差不直接进入决策 |
| **解释生成** | 面向学生/教师的 `explanation`。与决策解耦，幻觉风险是**体验问题而非决策问题** |

**不应该用**

1. **实时难度决策。** 三条理由：
   - **延迟**：`GET /next-task` 在每个题目的关键路径上，1–3 s 的 LLM 调用在课堂场景不可接受；
   - **不可复现（决定性理由）**：模型版本漂移使策略非平稳，**已记录的倾向得分不可重建**，§11.1 的 IPS/DR 估计因此不一致，RCT 的 ceteris paribus 对比也因此失效；
   - **成本**。
2. **个体能力估计。** IRT 滤波器已做这件事；LLM 只能通过 prompt 看到压缩后的历史，有损且不可验证。
3. **任何会混淆 ablation 的环节。** 若 LLM 在决策环内，无法分离"算法有效"与"LLM 有效"，审稿人必问。

### 9.2 混合架构

```
【离线 · 每周或题库变更触发 · 版本冻结】
  题面 ──► LLM 标注器（3 模型独立投票）
              │  输出 (d̂_LLM, 投票离散度 ŝ²_vote, 特征向量 x_i)
              ▼
      ┌────────────────────────────────────────────┐
      │ 难度先验校准器（有监督回归，黄金集拟合）      │
      │  μ_0i = α₀ + α₁·d̂_LLM + α₂ᵀx_i              │
      │  ς²_0i = σ²_reg + λ_disp·ŝ²_vote,i          │  ← 不确定性传播
      └────────────────────────────────────────────┘
              │  (μ_0i, ς²_0i, llm_label_version) 落库
════════════════════════════════════════════════════════
【在线 · 每次 next-task · 无 LLM】
  作答流 ──► 2PL 在线更新（Laplace 近似）──► (β̂_i, ς̂²_i)
```

### 9.3 先验与数据的贝叶斯融合

$$\varsigma_i^2 = \left(\frac{1}{\varsigma_{0i}^2} + \mathcal{I}_i\right)^{-1},\qquad \beta_i = \varsigma_i^2\left(\frac{\mu_{0i}}{\varsigma_{0i}^2} + \mathrm{score}_i\right),\qquad \mathcal{I}_i = \sum_j a_i^2\hat p_{ij}(1-\hat p_{ij})$$

**可证明的性质**：LLM 先验的影响以 $O(1/n_i)$ 衰减；$n_i\to\infty$ 时被完全冲掉。不确定性经 $\varsigma_i$ 进入 §2.4 的方差膨胀项，使高不确定题目自动被"少信任"。

### 9.4 噪声控制的四道闸

1. **多模型投票**：3 个不同家族的模型独立标注，取中位数 $\hat d$ 与 MAD 离散度；报告 **ICC(2,3)** 与**二次加权 Cohen's $\kappa$**（适用于有序等级）。
2. **人工校验抽样**：按 $(\hat d,\ \text{离散度})$ 分层抽 $n_{val}\approx 200$ 题，双专家独立标注。用途不是"验证 LLM 对不对"，而是**拟合校准回归** $(\alpha_0,\alpha_1,\boldsymbol\alpha_2)$——把 LLM 输出当作**有偏、有尺度误差的测量值**，而非真值。这是测量误差校正的标准做法，也是整个 LLM 部分能否站住脚的关键。
3. **不确定性传播**：投票离散度 $\to \varsigma^2_{0i} \to$ 方差膨胀 $\to$ 决策保守化，端到端可验证。
4. **漂移控制**：`llm_label_version` 冻结落库；任何重标注触发新版本号与 $(\alpha_0,\alpha_1)$ 重拟合；禁止静默覆盖。

### 9.5 LLM 层的可证伪假设

- **H-LLM1**（聚合效度）：$\mathrm{Spearman}\ \rho(\hat d^{LLM},\ \hat\beta^{IRT})\geq 0.5$，报告 95% CI。
- **H-LLM2**（冷启动增益）：对 $n_i\leq5$ 的题目，$\mathrm{RMSE}(\hat\beta^{v2}) < \mathrm{RMSE}(\hat\beta^{v1})$（题目级配对检验）。
- **H-LLM3**（先验被冲掉）：对 $n_i\geq 50$ 的题目，$|\hat\beta^{v2} - \hat\beta^{\text{no-LLM}}| < 0.05$ logit。

**H-LLM3 是防御性的核心**：它证明 LLM 只做先验工作、不承载决策——正面回应"你只是套了个 LLM"的审稿意见。

---

## 10. 迁移映射表

### 10.1 代码改动

| 文件:行 | 现状 | v2 改动 | 优先级 |
|---|---|---|---|
| `optimal_difficulty.py:56-57` | `elo_difficulty` 硬编码 `800+(d-1)/9*1400` | 删除 → `LDSBridge.fsrs_to_z(d, kappa)`，`kappa` 可标定 | P0 |
| `optimal_difficulty.py:88-97` | 分布目标常量 | **保留**（已验证正确，见 §3.1） | — |
| `optimal_difficulty.py:100-121` | `learning_rate_factor` | **保留**为实现 $G(p)$；新增 $\psi(A)$、$H(A)$ | P0 |
| `optimal_difficulty.py:276-280` | Glicko RD 用类常量 | 修复为正确的 RD 递推 + 时间膨胀（D2） | P0 |
| `optimal_difficulty.py:426-434` | PID 修正 `gain=0.3` | **删除**，由 §3 目标函数取代 | P0 |
| `optimal_difficulty.py:438-445` | σ→回归 `d=5.0`、权重 `0.2` | **删除**，由 §2.4 方差膨胀取代 | P0 |
| `optimal_difficulty.py:514-532` | `rank_tasks` 用 $1-\|p-0.85\|$ | 改为按 $\mathcal{J}$ 排序 | P1 |
| `dda.py:57-137` | 窗口成功率 + ±1 阶梯 | 改为 Rasch 窗口 MLE + Fisher 方差；保留 `DDAResult` 的**文案层**（宠物反应、鼓励语）不变 | P0 |
| `knowledge_tracing.py:117-144` | `recommend_difficulty` = `int(m*10)+1` | 改为返回 $(\hat\theta_{BKT}, \mathrm{Var})$，不再直接产出难度 | P0 |
| `knowledge_tracing.py:34-37` | `p_learn0=0.35, p_transit=0.12` | EM 标定（`fit_bkt_em`），按知识点估计并报告 CI | P0 |
| `orchestrator.py:42-44` | 权重常量 0.45/0.35/0.20 | **删除**，改为 §2.3 精度加权 | P0 |
| `orchestrator.py:95-110` | 缓存/非缓存两套 BKT 映射 | 统一；$\sigma$ 单一来源（D2/D3） | P0 |
| `orchestrator.py:113-119` | 丢弃 `expected_success`/`zone`/`lr_factor`/`explanation` | 改为消费完整 `FlowObjectiveResult` | P0 |
| `orchestrator.py:122` | `dda_engine.calculate(recent_results, current_difficulty)` | 传入窗口内每题的 $\beta_j$（不再只传整数难度） | P0 |
| `orchestrator.py:130-152` | `WHERE difficulty == fused ORDER BY RANDOM()` | 改为 §8 候选排序 + softmax + 全量日志 | P0 |
| `orchestrator.py:195-199` | `challenge_band{low:75, high:85}` | 改为 $\mathcal{F}_\eta$ 投影（D5） | P1 |
| `orchestrator.py:64-71` | 只查 `Attempt` | 增加 `SpacedReview` 查询（D6） | P1 |
| `placement_test_engine.py:147-190` | ±2/±1 启发式 + "最近3题"收敛 | 改为 IRT-CAT（§7） | P1 |
| `spaced_repetition.py:22-65` | 简化艾宾浩斯（×2.5 / ÷2） | 改为 FSRS-4 稳定性递推，`R(t)` 供 §6 使用 | P1 |
| `ab_test_framework.py:130-159` | `md5(exp:user)%100 < traffic`，2 臂、无分层 | 升级为**分层置换区组随机化**（§11.2） | P0 |

### 10.2 数据模型改动

**新增 `TaskServe`**（放弃行为的最小记录单元，D-§3.2 的前提）

```python
class TaskServe(Base):
    __tablename__ = "task_serves"
    id, user_id, task_id
    served_at: DateTime
    candidate_set: JSON        # 候选题目 id 列表
    candidate_scores: JSON     # 各分量得分
    propensity: Float          # P(i)，offline IPS 必需
    policy_version: String
    was_answered: Boolean      # = False → S1 跳过
    time_to_first_action: Integer   # 秒
    session_id, is_probe: Boolean, probe_difficulty_override: Float
```

**新增 `DifficultyDecisionLog`**（让权重可 A/B、可审计）

```python
theta_hats: JSON    # {bkt: (θ,τ), elo: (θ,τ), dda: (θ,τ)}
theta_fused, sigma_fused: Float
kappa, T_eff, A_hat, dA_dp, p_star_u, delta_star_u: Float   # 关键中间量全部落库
beta_star, J_star, F_eta_low, F_eta_high: Float
guardrail_triggered: Boolean
```

**`AbilityEstimate` 扩展**：`theta` → LDS logit 单位；新增 `n_attempts`、`rd_updated_at`、`skill_offsets: JSON`（$\delta_{u,k}$）。

**`Task` 扩展**：`difficulty_lds: Float`（$\hat\beta_i$）、`difficulty_se: Float`（$\varsigma_i$）、`discrimination: Float`（$a_i$）、`guessing: Float`（$c_i$）、`llm_prior_mu/sd: Float`、`llm_label_version: String`。`difficulty` 整数列保留为前端显示刻度，由 $\hat\beta$ 经 $\kappa$ 映射生成。

---

## 11. 实验设计

### 11.1 离线：把"难度选择"规约为静态数据上可评估的问题

**先说清楚难点。** 静态数据集（ASSISTments 2017、EdNet-KT1）没有难度选择的反事实标签。这个困难要拆成三个**不同**的问题，混为一谈是常见错误：

- **P1 动作反事实**：策略派发了题 $i$，题 $i'$ 的结果未观测。
- **P2 奖励不可观测**：即使对已派发的题，**"学到多少"在任何日志里都没有标签**（只观测到对错）。
- **P3 放弃不存在**：KT 数据集只记录作答流，没有"因为太难而退出"的标签；按数据集构造，下一动作永远是另一道题。

**三层递进设计，逐层加假设、逐层设有效性闸门。**

#### Layer 1 · 重要性采样反事实评估（针对 P1）

日志策略 $\mu$（未知），目标策略 $\pi$，逐步重要性比 $\rho_t = \pi(a_t\mid h_t)/\mu(a_t\mid h_t)$。

$$\hat V_{PDIS} = \frac{1}{N}\sum_{n}\sum_{t}\Big(\prod_{t'=1}^{t}\rho_{t'}^{(n)}\Big) r_t^{(n)}$$

$$\hat V_{WIS} = \frac{\sum_n w_n\sum_t r_t^{(n)}}{\sum_n w_n},\qquad \hat V_{CWIS} = \frac{\sum_n \min(w_n,c)\sum_t r_t^{(n)}}{\sum_n \min(w_n,c)},\quad w_n=\prod_t\rho_t^{(n)}$$

$$\hat V_{DR} = \frac{1}{N}\sum_n\sum_t\Big[\rho_{1:t}^{(n)}\big(r_t^{(n)} - \hat Q(h_t^{(n)},a_t^{(n)})\big) + \rho_{1:t-1}^{(n)}\,\hat V^{\pi}(h_t^{(n)})\Big],\quad \hat V^\pi(h)=\sum_a\pi(a\mid h)\hat Q(h,a)$$

三个估计量**同时报告**：一致则互为佐证，分歧则红旗。DR 的双重稳健性意味着 $\hat Q$ 与 $\mu$ **只要一个正确即一致**。

**日志倾向得分 $\hat\mu$**：用行为克隆（以状态特征预测 10 个难度等级的分类器）拟合， held-out log-likelihood 验证。

**必须报告的诊断量（预注册为有效性闸门）**

$$\mathrm{ESS} = \frac{(\sum_n w_n)^2}{\sum_n w_n^2},\qquad \text{闸门：}\ \mathrm{ESS}/N \geq 0.05$$

**positivity 的现实警告**：ASSISTments/EdNet 的题目序列由教师布置与学生自选决定，**接近确定性**，大量 (学生, 难度) 单元概率 ≈ 0。缓解：(a) 将动作空间限制到数据实际支撑的 $[\hat\theta-1.5,\hat\theta+1.5]$ logit 带；(b) 截断 $\hat\mu \geq 0.02$；(c) 报告**覆盖率** $\frac{1}{NT}\sum\mathbb{1}[\hat\mu > 0.02]$。若覆盖率 < 0.30，则声明 IPS 路线不可行，降级到 Layer 3。

#### Layer 2 · 可观测的替代奖励（针对 P2）

$$r_t = \omega_1\underbrace{a_i^2\hat p_t(1-\hat p_t)}_{\text{Fisher 信息量}} + \omega_2\underbrace{y_t}_{\text{正确性}} - \omega_3\underbrace{\tilde A_t}_{\text{放弃代理}}$$

诚实说明：$\omega$ 的选取是**价值判断**，不是从数据推出的。因此预注册：

> Layer 1–2 的结果**仅作为排序检查**，不构成效果 claim。最终的验证是：一旦 RCT 数据到手，计算离线 $\hat V$ 排序与在线主结局的**秩相关**；若 $\mathrm{Spearman}\ \rho < 0.6$，则该离线代理被废弃，并在论文中如实报告。

更强的替代主指标（推荐）：**留出后测**。用学习者后期在**难度分层、从未用于训练**的题目上的真实表现作为结果变量——这是静态数据里最接近真实学习产出的东西。

#### Layer 3 · 反事实轨迹重构（CTR）+ 多学习者模型秩稳定性（针对 P1+P2+P3）

1. 在真实数据训练 split 上拟合作答模型 $\hat p(y\mid\theta,\beta,a,c)$ 与能力转移模型。
2. 用真实数据估计**真实题目参数** $(\hat\beta_i,\hat a_i,\hat c_i)$——**题库是真实的，不是合成的**。
3. 用真实数据初始化**真实学习者能力** $\hat\theta_u^{(0)}$。
4. 候选策略在仿真中 **on-policy** 运行：从真实题库按真实参数选题，结果由拟合作答模型抽样，能力按拟合转移模型更新。
5. 用**留出的真实题目**构成"后测"评估仿真轨迹。

**已知的方法学陷阱与对策**：Doroudi, Aleven & Brunskill (2019) 指出，模拟学习者下的策略排序**对学习者模型假设敏感，排序可能翻转**。因此**不以单一模型的结论为准**：在 BKT、DKT、"能力静态"零模型三种学习者模型下分别跑，**要求策略排序在所有模型下一致**，否则判定该结论对模型假设不稳健、不予报告。这是文献推荐的标准对策。

#### 数据集与预处理

| 数据集 | 规模 | 适用性 | 主要限制 |
|---|---|---|---|
| ASSISTments 2017 | ~1.7M 交互 / ~1,700 学生 | 有知识点标签、可估题目参数、有后测结构 | 策略接近确定性 → positivity 差 |
| EdNet-KT1 | ~96M 交互 / 784k 学生 | 题目参数估计极稳 | 纯学生自选导航，positivity 最差 |
| Algebra 2005-06 / Bridge 2006-07 | 步骤级 | 细粒度，可做步骤级难度 | 无放弃信号 |
| Junyi Academy | 大 | **自带难度字段与课程顺序** | 数学单科 |

预处理：过滤交互数 ≥50 的学生；按数据集拟合 2PL + 交叉验证（报告 AUC / RMSE / 校准 ECE）；题目难度按**经验 $\hat\beta$ 的十分位**映射为 10 个有序等级（对齐 LearnFlow 的 1–10）；状态 $h_t$ = (近期正确率, $\hat\theta$, $\hat\sigma$, 知识点, 时间间隔)。用 **pyKT** 做标准化切分。

### 11.2 在线 RCT：主实验

**设计**：4 臂平行组、个体随机、12 周（一个学期）。测量点：基线（W0）、中期（W6）、后测（W12）、随访（W20）。

| 臂 | 策略 | 角色 |
|---|---|---|
| **A** | v1 融合规则（0.45/0.35/0.20 + 等值匹配） | ** incumbent，主对照 ** |
| **B** | 纯 85% 规则：$\arg\min_d \|\hat p(d) - 0.8413\|$ | 理论基线（无留存、无异质性） |
| **C** | DKT 选难度（pyKT）→ 预测 $\hat p$ 后套 85% 规则 | 现代 KT 基线 |
| **D** | **v2 完整引擎** | treatment |

**设计原则：消融走离线，确认走在线。** 组件消融（±探索、±MMR、±LLM 先验、±遗忘