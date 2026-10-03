# 环境痕迹脱敏：`--replace-text` 规则依据与排除项说明

生成者：path-scrub　日期：2026-10-02　配套文件：`results/_replace_text_rules.txt`

---

## 0. 一句话结论

`results/_replace_text_rules.txt` 只含 **8 条**本机私有片段（③ 类），零注释、零装饰。
另有 3 类 `workbuddy` 相关字样（① ② 类）**明确保留**——理由是"披露"而非"抹除"（见 §2）。
本文档存入全部实测证据，供复核。

---

## 1. 三类字样的区分

| 类 | 字面量 | 处置 | 原因 |
|---|---|---|---|
| ③ | `C:\Users\mac`（及各类变体）、`C:/Users/Administrator`、`pytest-of-mac`、`~\.workbuddy` 等 | **替换** | 本机私有片段：暴露真实用户名、账户名、临时目录名，纯卫生问题 |
| ① | `learnflow-m3.app.workbuddy.host` | **保留** | 对外公开可访问的成果链接，保留有利于复现；非本机/个人痕迹 |
| ② | `@tencent-ai/workbuddy-cloud-sdk` | **保留** | 第三方依赖包名，属代码语义；替换会破坏 `package.json` / lock 及其引用文档 |
| ② | `WORKBUDDY_DIR` | **保留** | `results/e_upload/find_zenodo_token.py` 中的环境变量标识符，属代码语义；替换即破坏该脚本 |

关于 `.workbuddy` / `WorkBuddy`（AI 工具会话与工具链目录名）：**暂不替换**，理由见 §5。

---

## 2. 被排除的串：逐条理由

- **`learnflow-m3.app.workbuddy.host`** —— 公有主机名。它是 M3 云端端点的公开地址，属"成果链接"而非"本机痕迹"；抹去反而削弱可复现性、也不符合导师 §2.3 的"披露"取向。
- **`@tencent-ai/workbuddy-cloud-sdk`** —— 第三方包名。出现在 `results/m3/cloudapp/package.json`、`package-lock.json` 以及 `docs/M3_*.md` 的正文引用中；替换会破坏依赖解析与文档准确性。
- **`WORKBUDDY_DIR`** —— 代码标识符。`find_zenodo_token.py` 用它接收"内部工具链目录"路径；替换会破坏该脚本的运行语义。

---

## 3. 生效的 8 条规则（`results/_replace_text_rules.txt`）

全部带 `literal:` 前缀（理由见 §4）。当前命中数按 **721 个 tracked 文件**逐个实测得出。

| # | 规则（literal 源串 → 替换目标） | 当前命中 | 命中文件 |
|---|---|---|---|
| 1 | `C:\\Users\\mac` → `C:\\Users\\<user>` | 4 | `results/code/full_suite_after_change.txt`、`results/code/llm_labeling.json`、`results/code/llm_labeling_v2.json`、`results/code/llm_model_manifest.json` |
| 2 | `C:\Users\mac` → `C:\Users\<user>` | 7 | `results/M1_instability.md`、`results/M3_simulator.md`、`results/m2/check_impl_ref.stdout.txt`、`results/m2/scan_mechanism_landing.stdout.txt`、`results/m2/verify_asset_numbers.stdout.txt`、`results/m2/verify_asset_numbers_with_pytest.stdout.txt`、`results/m2/verify_counts.stdout.txt` |
| 3 | `C:/Users/mac` → `C:/Users/<user>` | 7 | `results/m3/_f4_e1b_out.txt`(x4)、`results/m3/_resume_deepseek_e1b_out.txt`(x3) |
| 4 | `/c/Users/mac` → `/c/Users/<user>` | 1 | `results/M2_results.md` |
| 5 | `C:/Users/Administrator` → `C:/Users/<user>` | 2 | `output/20260928-en-submissions/pipeline-state.yaml`、`output/20260928-m3-final-docx/submission_checklist_remaining.md` |
| 6 | `pytest-of-mac` → `<pytest-tmp>` | 1 | `results/code/full_suite_after_change.txt` |
| 7 | `~\.workbuddy` → `<home>\.workbuddy` | **0（历史专属）** | 见 §8 |
| 8 | `~/.workbuddy` → `<home>/.workbuddy` | **0（历史专属）** | 见 §8 |

规则 1–6 合计 **22 处**，全部落在 §7 的 **16 个 tracked 文件**内。
（同两条规则还会命中两个**未跟踪**日志 `results/m3/ollama_serve_full.log`、`results/m3/_ollama_serve_worker.log`；它们不在 git 内，`filter-repo` 不会触碰，属可重生成日志。）

---

## 4. 为什么每条规则都写 `literal:` 前缀

`git_filter_repo.py::FilteringOptions.get_replace_text()`（L2340-2351）的解析顺序是：
先判 `regex:`、再判 `glob:`，二者都不匹配才当字面量；字面量若以 `literal:` 开头则剥掉该前缀。
因此**显式 `literal:` 前缀可彻底排除**"源串恰以 `regex:`/`glob:` 开头而被误当正则/通配"的歧义。8 条源串虽都不以这两者开头，但显式标注是零成本的保险。

---

## 5. 关于 `.workbuddy` / `WorkBuddy` 目录名：暂不替换

**采纳 team-lead 的裁决与理由（更强于"风险最小"）**：导师 §2.3 的要求是**披露**（把工具名、交给工具做的事、学生审阅范围写清楚），不是抹除。既然 §10.1 的"角色与工具表"会如实写出工具名称，那么代码里保留 `.workbuddy` 与环境变量名并不构成隐瞒，反而与披露一致；而 `C:/Users/<user>/.workbuddy/...` 这种**本机路径**属纯卫生问题，已由规则 1–3 覆盖。
另注：裸替换 `.workbuddy` 会误伤 ① 的公有主机名与 `workbuddy-builtin` 子目录，故也不能做无差别子串替换。若日后决定连工具目录名一并中性化，须改用**带前导分隔符的路径级规则**（如 `.workbuddy\binaries`、`/.workbuddy/plugins`、`\WorkBuddy\20`）。

---

## 6. 为什么规则文件"零注释"—— 97 行草稿的教训（存档）

首版草稿 `results/_replace_text_rules_draft.txt`（97 行）曾把说明写成 `#` 注释行。经核实 **`--replace-text` 没有注释语法**：

```
line = line.rstrip(b'\r\n')
if b'==>' in line: line, replacement = line.rsplit(b'==>', 1)
...
if regex: ... else:
    if line.startswith(b'literal:'): line = line[8:]
    if not line: continue          # ← 唯一的"跳过"条件是空行
    replace_literals.append((line, replacement))
```

（源码 L2328–2355；帮助里"`#` 行被忽略"那句属于 `--paths-from-file`，**不属于** `--replace-text`。team-lead 已逐字独立复核确认。）

**据此得到的实测存档（草稿文件 97 行）**：
- 用 filter-repo 自身的 `get_replace_text()` 解析该草稿 → **85 条 literal 规则、0 条 regex 规则**；
- 其中 **`#` 单字符规则 = 0 条**（关键：首版曾有 5 行"只有 `#`"的空注释行，那会被解析成"把全仓历史里每个 `#` 字符都替换掉"的规则，属**高危**；已修正）；
- 说明行随后改用 nonce 前缀 `#NOP:` 包裹（nonce 不存在于 HEAD、系本次新造），实为无害 no-op；
- **但该 `#NOP:` 写法本次不再采用**（仅存档）——因它依赖"nonce 恰好不命中"的侥幸，不够干净。最终规则文件改为**零注释纯规则**（见 `results/_replace_text_rules.txt`）。

---

## 7. 含私有片段的 16 个 tracked 文件（当前 HEAD）

```
output/20260928-en-submissions/pipeline-state.yaml
output/20260928-m3-final-docx/submission_checklist_remaining.md
results/M1_instability.md
results/M2_results.md
results/M3_simulator.md
results/code/full_suite_after_change.txt
results/code/llm_labeling.json
results/code/llm_labeling_v2.json
results/code/llm_model_manifest.json
results/m2/check_impl_ref.stdout.txt
results/m2/scan_mechanism_landing.stdout.txt
results/m2/verify_asset_numbers.stdout.txt
results/m2/verify_asset_numbers_with_pytest.stdout.txt
results/m2/verify_counts.stdout.txt
results/m3/_f4_e1b_out.txt
results/m3/_resume_deepseek_e1b_out.txt
```
全部归 **(B) 本机运行产物**（`output/**` 构建产物 + `results/**` 运行日志/结果），不含 **docs/README/CITATION/.zenodo.json/artifacts** 等 (A) 类提交件。

---

## 8. ⚠️ 关于"是否存在只存在于历史的漏网项"—— 更正一处结论

team-lead 转述的结论是"**无任何一条规则只存在于历史、现在已无命中**"。**实测显示这条结论是反的**，特此更正：

- 规则 **1–6** 均有当前命中（合计 22 处，见 §3）；
- 规则 **7、8**（`~\.workbuddy`、`~/.workbuddy`）**当前命中为 0**——它们是**历史专属**串：脱敏前的 `results/e_upload/find_zenodo_token.py` 曾含 `os.path.expanduser(r"~\.workbuddy\MEMORY.md")`，该串在当前 HEAD 已被我移除，但**仍存在于历史版本**。

所以正确表述是：
> **规则 7、8 恰恰是"只存在于历史、当前零命中"的串；把它们显式纳入规则，正是为了消除"改了 HEAD、历史仍脏"的漏网风险**——而不是"不存在这样的串"。

**这意味着**：不能仅凭"HEAD 已干净"判断历史已干净；必须保留 7、8，并执行 §10 的历史级核验。
（另需注意：我只能枚举我**观测到**的串——当前 HEAD 全部 tracked 文件 + 我脱敏前读过的 17 个脚本旧版。是否存在更早历史版本里的其它私有串，须由 §10 的全历史扫描来确认。）

---

## 9. 一处必须记住的教训：别把"HEAD 已无命中"当成"历史已安全"

本节记录本轮一次**自相矛盾及其更正**，供日后任何人重做同类重写时对照。

**① 前一轮测量曾错误得出"不存在仅历史规则"。**
在 `results/_replace_text_rules_draft.txt` 那一轮的交付说明里，同一段文字既给出一句"没有一条规则只存在于历史"式的小结，又同时注明"`~\.workbuddy` / `~/.workbuddy` 当前 0 命中，属"仅历史"、保留"。**这两句互相矛盾**；下游提炼时取了前半句、丢了后半句，遂形成一处错误结论：*"不存在只存在于历史、当前已无命中的规则"*。

**② 复测后确认：规则 7、8 就是"仅历史"串。**
对 **721 个 tracked 文件**逐条实测：规则 1–6 命中 22 处；规则 **7、8 命中 0**。它们来源于脱敏前 `results/e_upload/find_zenodo_token.py` 的 `os.path.expanduser(r"~\.workbuddy\MEMORY.md")`——该串在 HEAD 已被移除，但**仍留在历史版本**中。

**③ 因此，任何"HEAD 已无命中 ⇒ 历史已安全"的推断都是无效的。**
私有串可能**只存在于历史**：HEAD 干净只说明当前快照干净，不代表早期提交不脏。据此两点硬性要求（本案已执行）：
- **规则 7、8 必须保留**（`results/_replace_text_rules.txt` 共 8 条，一条不减）——它们存在的唯一目的，就是覆盖历史版本；
- **必须做历史级核验**（见 §10），而不是只看 HEAD。

> 一句话：**当泄漏藏在历史里时，只有"重写历史 + 逐版本核验"才能证明干净；"HEAD 干净"从来不是证据。**

**方法论教训**：结论必须回到实测数据、逐条对齐，不能从"看起来合理的表述"里提炼；一旦发现说明自相矛盾，宁可停在数据上、也不为任一表述背书。

---

## 10. 重写后的历史级核验（由 team-lead 执行）

```sh
# 遍历全部可达提交，逐版本 grep，确认私有串在任何历史版本中零命中
for c in $(git rev-list --all); do
  git grep -n -I -E "Users[\\/]{1,2}(mac|Administrator)|/c/Users/mac|pytest-of-mac|~\\.workbuddy" "$c" && echo "!! dirty at $c"
done
```

期望：除被重写替换后的 `C:\\Users\\<user>` 等中性占位外，无任何真实私有串命中。
