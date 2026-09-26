import io

p = "E:/learnflow/docs/M3_有序难度决策与大模型先验边界_完整稿.md"
s = open(p, encoding="utf-8").read()

MINUS = "\u2212"   # U+2212
EM = "\u2014"      # em dash
ENDASH = "\u2013"  # en dash
RUN = "\u8fd0\u884c\u4e2d"   # 运行中
OK = "\u2705"               # ✅

repls = []

# Edit 1: §5.8 table deepseek row
old1 = "| deepseek-v2:16b | F4_DeepSeek | S2 (7" + ENDASH + "30B) | 15.7B | " + EM + \
       " | 0.1206 [" + MINUS + "0.0350, 0.2635] | 0.3571 | 0.0642 | 100% | " + RUN + " | " + OK + " |"
new1 = "| deepseek-v2:16b | F4_DeepSeek | S2 (7" + ENDASH + "30B) | 15.7B | " + EM + \
       " | 0.2521 [0.1380, 0.3617] | 0.4057 | 0.1132 | 100% | 96 | " + OK + " |"
repls.append(("E1", old1, new1))

# Edit 2a: L506 (i) deepseek E1-B generating -> 96/108 + E1-A value
old2a = "deepseek-v2:16b 的 E1-B 截至本文撰写时仍在生成中**\uff08\u5176 E1-A 已\u8dd1\u6ee1 DBE-212 \u5168\u91cf\u3001\u03c1=0.1206\uff0cCI[" + MINUS + "0.0350, 0.2635]\uff0c\u6545 F4_DeepSeek \u65cf\u5df2\u5165\u8868\uff09"
new2a = ("deepseek-v2:16b 的 E1-B 已跑满 108 批中的 96 批（覆盖率 89% < 90% 门限，ρ=0.0141 不得与满批单元格并列比较）；"
         "其 E1-A 已跑满 DBE-212 全量、ρ=0.2521（CI[0.1380, 0.3617]，显著；早次运行曾得 ρ=0.1206、CI 含 0 不显著，"
         "二次运行显著性翻转，属单运行重测不稳定性，见 §5.8 末段），故 F4_DeepSeek 族已入表）")
repls.append(("E2a", old2a, new2a))

# Edit 2b: L506 E1-B coverage list add deepseek
old2b = "其余 E1-B 覆盖率均低于 90% 门限（mistral 89%、llama3.1:8b 86%、qwen36 83%、qwen3:1.7b 77%、llama3.2:1b 33%）"
new2b = "其余 E1-B 覆盖率均低于 90% 门限（deepseek 89%、mistral 89%、llama3.1:8b 86%、qwen36 83%、qwen3:1.7b 77%、llama3.2:1b 33%）"
repls.append(("E2b", old2b, new2b))

# Edit 3: L508 append deepseek re-test note
old3 = '\uff08"其余单元格噪声同量级"为**【合理推断】**\uff09'
app3 = ("**deepseek-v2:16b 的 E1-A 在收尾重跑中给出第二例重测不稳定性**：同一模型、同一 DBE-212、"
        "同一 E1-A 协议，早次运行 ρ=0.1206（CI[" + MINUS + "0.0350, 0.2635] 含 0，不显著），收尾重跑 "
        "ρ=0.2521（CI[0.1380, 0.3617] 不含 0，显著），点估计摆动 0.13、远超 qwen36 的 " + "\u00b1" +
        "0.045 且显著性翻转" + "\u2014\u2014" + "故 deepseek 的 E1-A 同样不得被单独当作稳定证据；"
        "跨模型 ρ 比较须以覆盖 ≥90% 的 E1-B 或重复运行一致性为前置。**【数据支撑】**")
new3 = old3 + app3
repls.append(("E3", old3, new3))

# Edit 4: L514 (c) deepseek E1-A + E1-B
old4 = "F4_DeepSeek 已入表（deepseek-v2:16b 的 E1-A 已跑满 DBE-212，ρ=0.1206），qwen36 的 E1-B 已跑但仅 90/108=83.3% 未达 E1-B 可比性门限；"
new4 = ("F4_DeepSeek 已入表（deepseek-v2:16b 的 E1-A 已跑满 DBE-212，ρ=0.2521 [0.1380, 0.3617] 显著；"
        "早次运行曾得 ρ=0.1206 不显著、显著性翻转见 §5.8 末段），其 E1-B 已跑但仅 96/108=89% 未达 E1-B 可比性门限；"
        "qwen36 的 E1-B 已跑但仅 90/108=83.3% 未达 E1-B 可比性门限；")
repls.append(("E4", old4, new4))

# Edit 5: L518 first occurrence
old5 = "deepseek 的 E1-B 仍在生成中、qwen36 的 E1-B 仅 90/108=83.3% 未达可比性门限、qwen3:1.7b 单元格被判不可用；"
new5 = "deepseek 的 E1-B 已跑但 96/108=89% 未达可比性门限、qwen36 的 E1-B 仅 90/108=83.3% 未达可比性门限、qwen3:1.7b 单元格被判不可用；"
repls.append(("E5", old5, new5))

# Edit 5b: L518 second occurrence
old5b = "F4_DeepSeek 已入表（deepseek-v2:16b 的 E1-A 已跑满 DBE-212，ρ=0.1206），但 deepseek 的 E1-B 仍在生成中、qwen36 的 E1-B 仅 90/108=83.3% 未达可比性门限，"
new5b = ("F4_DeepSeek 已入表（deepseek-v2:16b 的 E1-A 已跑满 DBE-212，ρ=0.2521 [0.1380, 0.3617] 显著；"
         "早次运行 ρ=0.1206 不显著、显著性翻转见 §5.8 末段），但 deepseek 的 E1-B 已跑 96/108=89% 未达可比性门限、"
         "qwen36 的 E1-B 仅 90/108=83.3% 未达可比性门限，")
repls.append(("E5b", old5b, new5b))

# Edit 6: L711 (i)
old6 = "ρ=0.1206，CI[" + MINUS + "0.0350, 0.2635]，属 S2 档），F4 族已入表；但其 E1-B 截至本文撰写时仍在生成中；"
new6 = ("ρ=0.2521，CI[0.1380, 0.3617]（显著；早次运行 ρ=0.1206、CI 含 0 不显著，二次运行显著性翻转，"
        "属单运行重测不稳定性，见 §5.8 末段），属 S2 档），F4 族已入表；但其 E1-B 已跑（96/108=89% < 90% 门限，"
        "未达 E1-B 可比性），其 E1-B ρ 不得与满批单元格并列比较；")
repls.append(("E6", old6, new6))

# Edit 7: L711 (iii) gate quote 6 -> 7 cells
old7 = "当前 6 单元格为 EVALUATED"
new7 = "当前 7 单元格为 EVALUATED"
repls.append(("E7", old7, new7))

# Apply with assertions
for name, o, n in repls:
    cnt = s.count(o)
    assert cnt == 1, f"[{name}] expected exactly 1 match, found {cnt}"
    s = s.replace(o, n)
    print(f"[{name}] OK replaced 1")

open(p, "w", encoding="utf-8").write(s)
print("WRITTEN")
