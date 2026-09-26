# Wilson, Shenhav, Straccia & Cohen (2019) 引语核对底本

- 文献：Wilson, R. C., Shenhav, A., Straccia, M., & Cohen, J. D. (2019). The Eighty Five Percent Rule for optimal learning. *Nature Communications*, 10(1), 4646. DOI: 10.1038/s41467-019-12552-4
- 底本来源：Europe PMC 全文 XML（PMC6831579），检索日 2026-09-25
  - https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6831579/fullTextXML
  - https://europepmc.org/article/PMC/PMC6831579
- **版本警示**：本文的 **bioRxiv 预印本（10.1101/255182v1）Discussion 与发表版显著不同**——预印本写 "gradient-descent learning rules"（无 *stochastic*）、贝叶斯反例**无** "with a perfect memory"、且 Discussion 中**没有** 85/82/75 那句。**正文引用一律以 Nat Commun 发表版为准，不得混用预印本措辞。**
- 段落定位：Discussion 共 8 段，PMC XML 段落 id = Par26–Par33（Discussion = Sec9）。

## Q1（二分类 + SGD 特例）
Discussion 第 1 段（Par26）首句：
> "In this article we considered the effect of training accuracy on learning in the case of binary classification tasks and stochastic gradient-descent-based learning rules. We found that the rate of learning is maximized when the difficulty of training is adjusted to keep the training accuracy at around 85%. ..."

Discussion 第 5 段（Par30）末句（位置最精确）：
> "In this context, our work offers a way of deriving the desired difficulty and the region of proximal learning in the special case of binary classification tasks for which stochastic gradient-descent learning rules apply."

## Q2（尚待推广到多选题与其他学习算法）
与 Q1 同段（Par30）最后一句，紧接上句：
> "As such our work represents the first step towards a more mathematical instantiation of these theories, although it remains to be generalized to a broader class of circumstances, such as multi-choice tasks and different learning algorithms."
（原文为 "multi-choice"，非 "multiple-choice"。）

## Q3（并非所有模型都有难度甜点区 + 贝叶斯反例）
Discussion 第 6 段（Par31）首句与反例：
> "With regard to different learning algorithms, it is important to note that **not all models will exhibit** a sweet spot of difficulty for learning. As an example, consider how **a Bayesian learner with a perfect memory** would infer parameters φ by computing the posterior distribution given past stimuli ..."
> "Clearly this posterior distribution over parameters is independent of the ordering of the trials meaning that a Bayesian learner (with perfect memory) would learn equally well if hard or easy examples are presented first."
（⚠️ 原文为 "will exhibit" 与 "**with a perfect memory**"，**不是** "exhibit" 或 "ideal Bayesian learner"。）

## Q4（关于"学生/人类学习者"的引语是否存在）
**不存在。** 对 PMC6831579 全文 XML 正则检索，"student" / "students" **出现 0 次**（含 references、图注、Methods、声明）。
→ 此前被更正掉的那句所谓直接引语确证为伪造。**且须注意**：原文并未把人类学习者排除在框架外，反而明确纳入（如 "a model from computational neuroscience that is thought to describe human and animal perceptual learning"；Law & Gold 一节 "the Law and Gold model still implements stochastic gradient descent on the error rate and learning should be optimized at 85%"）。
→ **因此不得写成"作者自己说该规则不适用于学生"**；可写的只有 Q1–Q3 的**适用边界限定**。

## Q5（85% / 82% / 75% 与 15.87%）
Discussion 第 2 段（Par27）逐字：
> "...relaxing the assumption that the noise is Gaussian leads to changes in the optimal training accuracy: from 85% for Gaussian, to 82% for Laplacian noise, to 75% for Cauchy noise (Eq. (31) in the "Methods")."
Methods（Eq. 31）给出的是**错误率**：`ER*_Laplace = ½exp(−1) ≈ 0.1839`；`ER*_Cauchy = (1/π)arctan(−1) + ½ = 0.25`。换算 1−0.1839 ≈ 81.6% ≈ 82%，1−0.25 = 75%。
→ 82% / 75% 是**准确率**表述，出自 Discussion；Methods 里是 0.1839 / 0.25 两个**错误率**。引用时勿混。

"15.87%" 在原文中确实出现，共 5 处（Abstract、Introduction、Results Eq.6 后、Perceptron 节、Methods），另公式中写作 ≈0.1587。
