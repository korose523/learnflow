"""小学数学题库生成器 — 覆盖1-6年级全部核心知识点
程序化生成，质量可控，单次运行可产 2万+ 道题目
"""
import json
import random
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@dataclass
class Question:
    topic: str
    difficulty: int
    content: str
    correct_answer: str
    explanation: str
    grade: int
    question_type: str = "calculation"
    hint_levels: list = field(default_factory=list)
    time_estimate: int = 120

    def to_task_dict(self) -> dict:
        return {
            "topic": self.topic,
            "difficulty": self.difficulty,
            "content": self.content,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "hint_levels": self.hint_levels,
            "time_estimate": self.time_estimate,
            "source": "math_generator",
            "content_type": "text",
            "is_approved": True,
            "grade": self.grade,
            "question_type": self.question_type,
        }


class MathGenerator:
    """小学数学题库生成器"""

    GRADE_TOPICS = {
        1: ["10以内加减法", "20以内加减法", "数的认识", "认识图形", "认识钟表", "比大小"],
        2: ["100以内加减法", "表内乘法", "表内除法", "长度单位", "角的认识", "认识时间"],
        3: ["万以内加减法", "多位数乘一位数", "除数是一位数的除法", "分数初步", "周长", "面积初步"],
        4: ["大数的认识", "三位数乘两位数", "除数是两位数的除法", "四则运算", "小数的意义", "三角形"],
        5: ["小数乘法", "小数除法", "分数加减法", "分数乘除法", "简易方程", "多边形面积"],
        6: ["分数混合运算", "百分数", "比和比例", "圆的周长和面积", "圆柱与圆锥", "负数"],
    }

    GRADE_DIFFICULTY_RANGE = {
        1: (1, 2), 2: (2, 4), 3: (3, 5),
        4: (4, 6), 5: (5, 8), 6: (6, 9),
    }

    # ─── 一年级 ─────────────────────────────────────────
    def _gen_grade1_add_sub_10(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            a = random.randint(0, 10)
            b = random.randint(0, 10 - a) if random.random() < 0.5 else random.randint(0, a)
            op = "+" if a + b <= 10 else "-"
            if op == "+":
                answer = a + b
            else:
                answer = a - b
            q = Question(
                topic="10以内加减法",
                difficulty=random.randint(1, 2),
                content=f"计算：{a} {op} {b} = ？",
                correct_answer=str(answer),
                explanation=f"{a} {op} {b} = {answer}",
                grade=1,
                time_estimate=60,
                hint_levels=[f"用数手指的方法", f"{a}和{b}，{'相加' if op=='+' else '相减'}"],
            )
            qs.append(q)
        return qs

    def _gen_grade1_add_sub_20(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            a = random.randint(10, 19)
            b = random.randint(1, 9)
            op = random.choice(["+", "-"])
            if op == "+":
                answer = a + b
            else:
                answer = a - b
            q = Question(
                topic="20以内加减法",
                difficulty=2,
                content=f"计算：{a} {op} {b} = ？",
                correct_answer=str(answer),
                explanation=f"{a} {op} {b} = {answer}",
                grade=1,
                time_estimate=60,
                hint_levels=["先凑十再计算", f"{a}分成10和{a-10}，用10去加减"],
            )
            qs.append(q)
        return qs

    def _gen_grade1_compare(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            if a > b:
                answer, symbol = "大于", ">"
            elif a < b:
                answer, symbol = "小于", "<"
            else:
                answer, symbol = "等于", "="
            q = Question(
                topic="比大小",
                difficulty=1,
                content=f"{a} 和 {b} 比较大小，在括号里填 >、< 或 =：{a}（ ）{b}",
                correct_answer=symbol,
                explanation=f"{a} 比 {b} {'大' if a>b else '小' if a<b else '一样大'}，所以填 {symbol}",
                grade=1,
                time_estimate=45,
                hint_levels=[f"哪个数大？开口朝大的数", f"数轴上{a}在{b}的{'右边' if a>b else '左边'}"],
            )
            qs.append(q)
        return qs

    def _gen_grade1_shapes(self, count: int) -> list[Question]:
        qs = []
        shapes = [
            ("正方形", "有4条一样长的边，4个直角"),
            ("长方形", "有4条边，对边一样长，4个直角"),
            ("三角形", "有3条边，3个角"),
            ("圆形", "没有角，边是弯的"),
        ]
        for _ in range(count):
            name, desc = random.choice(shapes)
            q = Question(
                topic="认识图形",
                difficulty=1,
                content=f"下面描述的是哪种图形？\n「{desc}」\n请写出图形的名称。",
                correct_answer=name,
                explanation=f"根据描述：{desc}，这是{name}的特征。",
                grade=1,
                time_estimate=60,
                hint_levels=[f"数一数有几条边", f"想一想角的数量"],
            )
            qs.append(q)
        return qs

    # ─── 二年级 ─────────────────────────────────────────
    def _gen_grade2_add_sub_100(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            a = random.randint(10, 99)
            b = random.randint(1, 99)
            op = random.choice(["+", "-"])
            if op == "+":
                answer = a + b
            else:
                if a < b:
                    a, b = b, a
                answer = a - b
            q = Question(
                topic="100以内加减法",
                difficulty=random.randint(2, 3),
                content=f"计算：{a} {op} {b} = ？",
                correct_answer=str(answer),
                explanation=f"{a} {op} {b} = {answer}（注意{'进位' if op=='+' and a%10+b%10>=10 else '退位' if op=='-' and a%10<b%10 else '直接'}计算）",
                grade=2,
                time_estimate=90,
                hint_levels=["先算个位，再算十位", f"个位：{a%10} {op} {b%10}"],
            )
            qs.append(q)
        return qs

    def _gen_grade2_multiplication(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            a = random.randint(1, 9)
            b = random.randint(1, 9)
            q = Question(
                topic="表内乘法",
                difficulty=random.randint(2, 3),
                content=f"计算：{a} × {b} = ？",
                correct_answer=str(a * b),
                explanation=f"{a} × {b} = {a * b}（{a}个{b}相加等于{a * b}）",
                grade=2,
                time_estimate=60,
                hint_levels=[f"就是{a}个{b}相加", f"{a}×{b}={a}×({b}-1)+{a}={a*(b-1)}+{a}"],
            )
            qs.append(q)
        return qs

    def _gen_grade2_division(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            b = random.randint(1, 9)
            c = random.randint(1, 9)
            a = b * c
            q = Question(
                topic="表内除法",
                difficulty=random.randint(2, 3),
                content=f"计算：{a} ÷ {b} = ？",
                correct_answer=str(c),
                explanation=f"{a} ÷ {b} = {c}（因为 {b} × {c} = {a}）",
                grade=2,
                time_estimate=60,
                hint_levels=[f"想：{b}乘以几等于{a}？", f"乘法口诀：{b}×{c}={a}"],
            )
            qs.append(q)
        return qs

    def _gen_grade2_length(self, count: int) -> list[Question]:
        qs = []
        units = [("厘米", "cm"), ("米", "m")]
        for _ in range(count):
            unit_cn, unit_en = random.choice(units)
            val = random.randint(1, 100)
            if unit_cn == "米":
                val_cm = val * 100
                q = Question(
                    topic="长度单位",
                    difficulty=3,
                    content=f"{val} 米 = （ ）厘米",
                    correct_answer=str(val_cm),
                    explanation=f"1米 = 100厘米，{val} × 100 = {val_cm}厘米",
                    grade=2,
                    time_estimate=60,
                    hint_levels=["1米等于100厘米", f"{val}个100厘米"],
                )
            else:
                val_m = val / 100
                q = Question(
                    topic="长度单位",
                    difficulty=3,
                    content=f"{val} 厘米 = （ ）米",
                    correct_answer=str(val_m) if val_m == int(val_m) else f"{val_m:.2f}",
                    explanation=f"100厘米 = 1米，{val} ÷ 100 = {val_m}米",
                    grade=2,
                    time_estimate=60,
                )
            qs.append(q)
        return qs

    # ─── 三年级 ─────────────────────────────────────────
    def _gen_grade3_multi_digit(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            a = random.randint(100, 999)
            b = random.randint(2, 9)
            q = Question(
                topic="多位数乘一位数",
                difficulty=random.randint(3, 4),
                content=f"竖式计算：{a} × {b} = ？",
                correct_answer=str(a * b),
                explanation=f"{a} × {b} = {a * b}（从个位乘起，注意进位）",
                grade=3,
                time_estimate=120,
                hint_levels=[f"先算{a}×{b}的个位", "注意进位加到十位和百位"],
            )
            qs.append(q)
        return qs

    def _gen_grade3_division_1digit(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            b = random.randint(3, 9)
            c = random.randint(10, 100)
            a = b * c
            q = Question(
                topic="除数是一位数的除法",
                difficulty=random.randint(3, 5),
                content=f"计算：{a} ÷ {b} = ？",
                correct_answer=str(c),
                explanation=f"{a} ÷ {b} = {c}（从高位除起，每次看一位或两位）",
                grade=3,
                time_estimate=120,
                hint_levels=[f"先看{a}的前一位够不够除", f"商是{c}"],
            )
            qs.append(q)
        return qs

    def _gen_grade3_fractions_intro(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            num = random.randint(1, 5)
            den = random.randint(2, 8)
            if num >= den:
                num = den - 1
            # Word problem style
            q = Question(
                topic="分数初步",
                difficulty=random.randint(3, 4),
                content=f"把一个蛋糕平均分成{den}份，吃了其中的{num}份。吃了这个蛋糕的几分之几？",
                correct_answer=f"{num}/{den}",
                explanation=f"分母表示总份数{den}，分子表示吃的份数{num}，所以是{num}/{den}。",
                grade=3,
                time_estimate=90,
                hint_levels=[f"总共{den}份，吃了{num}份", "分母是总份数，分子是吃的份数"],
            )
            qs.append(q)
        return qs

    def _gen_grade3_perimeter(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            l = random.randint(3, 15)
            w = random.randint(2, 10)
            shape = random.choice(["长方形", "正方形"])
            if shape == "正方形":
                w = l
                answer = 4 * l
                q = Question(
                    topic="周长",
                    difficulty=4,
                    content=f"一个正方形，边长是{l}厘米，它的周长是多少厘米？",
                    correct_answer=str(answer),
                    explanation=f"正方形周长 = 4 × 边长 = 4 × {l} = {answer}厘米",
                    grade=3,
                    time_estimate=90,
                    hint_levels=["正方形有4条相同的边", f"4 × {l} = ?"],
                )
            else:
                answer = 2 * (l + w)
                q = Question(
                    topic="周长",
                    difficulty=4,
                    content=f"一个长方形，长{l}厘米，宽{w}厘米，它的周长是多少厘米？",
                    correct_answer=str(answer),
                    explanation=f"长方形周长 = 2 × (长 + 宽) = 2 × ({l} + {w}) = {answer}厘米",
                    grade=3,
                    time_estimate=90,
                    hint_levels=["周长 = (长+宽)×2", f"先算 {l}+{w}"],
                )
            qs.append(q)
        return qs

    # ─── 四年级 ─────────────────────────────────────────
    def _gen_grade4_large_numbers(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            num = random.randint(10000, 99999999)
            q = Question(
                topic="大数的认识",
                difficulty=random.randint(4, 5),
                content=f"读出下面各数：\n{num}\n这个数读作什么？",
                correct_answer=self._num_to_chinese(num),
                explanation=self._explain_large_number(num),
                grade=4,
                time_estimate=90,
                hint_levels=["先分级，从右往左每4位一级", "从高位往低位读"],
            )
            qs.append(q)
        return qs

    @staticmethod
    def _num_to_chinese(num: int) -> str:
        digits = "零一二三四五六七八九"
        units = ["", "十", "百", "千"]
        big_units = ["", "万", "亿"]
        if num == 0:
            return "零"
        s = str(num)
        n = len(s)
        result = ""
        for i, ch in enumerate(s):
            d = int(ch)
            pos = (n - i - 1) % 4
            if d != 0:
                result += digits[d] + units[pos]
            elif result and not result.endswith("零"):
                result += "零"
        result = result.rstrip("零")
        return result

    @staticmethod
    def _explain_large_number(num: int) -> str:
        s = str(num)
        n = len(s)
        parts = []
        big_idx = (n - 1) // 4
        for i in range(big_idx, -1, -1):
            start = max(0, n - (i + 1) * 4)
            end = n - i * 4
            part = s[start:end]
            part_val = int(part) if part else 0
            big_name = ["", "万", "亿"][i]
            if part_val > 0:
                parts.append(f"{part_val}{big_name}")
        return f"分级读法：{' + '.join(parts)}"

    def _gen_grade4_multiplication_2digit(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            a = random.randint(10, 99)
            b = random.randint(10, 99)
            q = Question(
                topic="三位数乘两位数",
                difficulty=random.randint(4, 6),
                content=f"竖式计算：{a} × {b} = ？",
                correct_answer=str(a * b),
                explanation=f"{a} × {b} = {a * b}（先用{b%10}乘{a}，再用{b//10}乘{a}，错位相加）",
                grade=4,
                time_estimate=150,
                hint_levels=[f"先算{a}×{b%10}", f"再算{a}×{b//10}，对齐十位"],
            )
            qs.append(q)
        return qs

    def _gen_grade4_division_2digit(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            b = random.randint(11, 30)
            c = random.randint(10, 50)
            a = b * c
            q = Question(
                topic="除数是两位数的除法",
                difficulty=random.randint(5, 6),
                content=f"计算：{a} ÷ {b} = ？",
                correct_answer=str(c),
                explanation=f"{a} ÷ {b} = {c}（试商：{b}×{c}={a}）",
                grade=4,
                time_estimate=150,
                hint_levels=[f"把{b}看成整十数试商", f"用{b}×20={b*20}试一试"],
            )
            qs.append(q)
        return qs

    def _gen_grade4_decimals_intro(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            a = round(random.uniform(0.1, 10), random.choice([1, 2]))
            b = round(random.uniform(0.1, 5), random.choice([1, 2]))
            op = random.choice(["+", "-"])
            if op == "+":
                answer = round(a + b, 2)
            else:
                if a < b:
                    a, b = b, a
                answer = round(a - b, 2)
            # Make sure no negative
            if op == "-" and a < b:
                a, b = b, a
                answer = round(a - b, 2)

            q = Question(
                topic="小数的意义",
                difficulty=random.randint(3, 5),
                content=f"计算：{a} {op} {b} = ？",
                correct_answer=str(answer),
                explanation=f"{a} {op} {b} = {answer}（小数点对齐后计算）",
                grade=4,
                time_estimate=120,
                hint_levels=["小数点对齐", f"按整数{a*100:.0f} {op} {b*100:.0f}，最后点小数点"],
            )
            qs.append(q)
        return qs

    def _gen_grade4_triangles(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            q_type = random.choice(["angle_sum", "classify", "sides"])
            if q_type == "angle_sum":
                a = random.randint(20, 80)
                b = random.randint(20, 80)
                c = 180 - a - b
                if c <= 0:
                    a, b = 50, 60
                    c = 70
                q = Question(
                    topic="三角形",
                    difficulty=5,
                    content=f"一个三角形的两个角分别是{a}°和{b}°，第三个角是多少度？",
                    correct_answer=str(c),
                    explanation=f"三角形内角和为180°，180° - {a}° - {b}° = {c}°",
                    grade=4,
                    time_estimate=90,
                    hint_levels=["三角形内角和是180°", f"180 - {a} - {b}"],
                )
            elif q_type == "classify":
                sides = [(3, 3, 3), (3, 4, 4), (3, 4, 5)]
                a_s, b_s, c_s = random.choice(sides)
                if a_s == b_s == c_s:
                    ans = "等边三角形"
                elif a_s == b_s or b_s == c_s or a_s == c_s:
                    ans = "等腰三角形"
                else:
                    ans = "不等边三角形"
                q = Question(
                    topic="三角形",
                    difficulty=4,
                    content=f"三角形的三条边分别是{a_s}cm、{b_s}cm、{c_s}cm，按边分类是什么三角形？",
                    correct_answer=ans,
                    explanation=f"三边{'相等' if a_s==b_s==c_s else '有两边相等' if a_s==b_s or b_s==c_s else '都不相等'}，所以是{ans}。",
                    grade=4,
                    time_estimate=90,
                )
            else:
                a_s = random.randint(3, 15)
                b_s = random.randint(3, 15)
                c_s = random.randint(3, 15)
                can_form = (a_s + b_s > c_s) and (a_s + c_s > b_s) and (b_s + c_s > a_s)
                ans = "能" if can_form else "不能"
                q = Question(
                    topic="三角形",
                    difficulty=5,
                    content=f"三条线段分别长{a_s}cm、{b_s}cm、{c_s}cm，它们{'能' if can_form else '不能'}围成三角形吗？",
                    correct_answer=ans,
                    explanation=f"三角形任意两边之和大于第三边：{'+'.join(str(x) for x in sorted([a_s,b_s,c_s])[:2])}={sum(sorted([a_s,b_s,c_s])[:2])} {'>' if can_form else '<'} {max(a_s,b_s,c_s)}，所以{ans}。",
                    grade=4,
                    time_estimate=120,
                    hint_levels=["三角形两边之和大于第三边", f"检查{a_s}+{b_s}>{c_s}吗？"],
                )
            qs.append(q)
        return qs

    # ─── 五年级 ─────────────────────────────────────────
    def _gen_grade5_decimal_ops(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            op_type = random.choice(["multiply", "divide", "mix"])
            if op_type == "multiply":
                a = round(random.uniform(0.1, 99.9), random.choice([1, 2]))
                b = random.randint(2, 99) / 10
                answer = round(a * b, 4)
                clean_answer = str(answer).rstrip("0").rstrip(".")
                q = Question(
                    topic="小数乘法",
                    difficulty=random.randint(5, 7),
                    content=f"计算：{a} × {b} = ？",
                    correct_answer=clean_answer,
                    explanation=f"先按整数乘法 {int(a*10**max(0,len(str(a).split('.')[-1])))} × {int(b*10)}\n再确定小数点位置",
                    grade=5,
                    time_estimate=120,
                    hint_levels=["先忽略小数点，按整数乘", f"因数共有几位小数，积就有几位小数"],
                )
            else:
                a = round(random.uniform(1, 100), random.choice([1, 2]))
                b = random.randint(1, 9)
                answer = round(a / b, 4)
                clean_answer = str(answer).rstrip("0").rstrip(".")
                q = Question(
                    topic="小数除法",
                    difficulty=random.randint(5, 7),
                    content=f"计算：{a} ÷ {b} = ？",
                    correct_answer=clean_answer,
                    explanation=f"{a} ÷ {b} = {clean_answer}\n（把除数变成整数，被除数同时移动小数点）",
                    grade=5,
                    time_estimate=120,
                    hint_levels=[f"把除数{b}变成整数（已经是了）", "直接除，商的小数点与被除数对齐"],
                )
            qs.append(q)
        return qs

    def _gen_grade5_fractions(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            op_type = random.choice(["add", "sub", "multiply"])
            if op_type == "add":
                den = random.randint(6, 12)
                a = random.randint(1, den - 2)
                max_b = den - a - 1
                b = random.randint(1, max(max_b, 1))
                num_result = a + b
                ans = f"{num_result}/{den}"
                q = Question(
                    topic="分数加减法",
                    difficulty=random.randint(4, 6),
                    content=f"计算：{a}/{den} + {b}/{den} = ？",
                    correct_answer=ans,
                    explanation=f"同分母分数相加，分母不变，分子相加：{a} + {b} = {num_result}，所以结果是{ans}。",
                    grade=5,
                    time_estimate=90,
                    hint_levels=["分母相同，直接加分子", f"{a} + {b} = ?"],
                )
            elif op_type == "sub":
                den = random.randint(4, 12)
                a = random.randint(2, den)
                b = random.randint(1, a - 1)
                num_result = a - b
                ans = f"{num_result}/{den}"
                q = Question(
                    topic="分数加减法",
                    difficulty=random.randint(4, 6),
                    content=f"计算：{a}/{den} - {b}/{den} = ？",
                    correct_answer=ans,
                    explanation=f"同分母分数相减，分母不变，分子相减：{a} - {b} = {num_result}，结果是{ans}。",
                    grade=5,
                    time_estimate=90,
                    hint_levels=["分母相同，直接减分子", f"{a} - {b} = ?"],
                )
            else:
                a = random.randint(1, 8)
                b = random.randint(2, 9)
                c = random.randint(1, 8)
                d = random.randint(2, 9)
                num = a * c
                den = b * d
                # Simplify fraction
                g = _gcd(num, den)
                num //= g
                den //= g
                ans = f"{num}/{den}" if den != 1 else str(num)
                q = Question(
                    topic="分数乘除法",
                    difficulty=random.randint(5, 7),
                    content=f"计算：{a}/{b} × {c}/{d} = ？",
                    correct_answer=ans,
                    explanation=f"分子乘分子：{a}×{c}={a*c}，分母乘分母：{b}×{d}={b*d}\n{a*c}/{b*d}" + (f" = {ans}" if (a*c)//_gcd(a*c,b*d) != a*c else ""),
                    grade=5,
                    time_estimate=120,
                    hint_levels=["分子乘分子，分母乘分母", f"{a}×{c}={a*c}，{b}×{d}={b*d}"],
                )
            qs.append(q)
        return qs

    def _gen_grade5_equations(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            a = random.randint(2, 9)
            b = random.randint(1, 30)
            c = random.randint(10, 100)
            # ax + b = c
            x = (c - b) / a
            if x != int(x):
                # Try: ax - b = c
                c2 = a * random.randint(3, 20) + b
                x = (c2 - b) / a
                if x != int(x):
                    continue
            x = int(x)
            q = Question(
                topic="简易方程",
                difficulty=random.randint(5, 7),
                content=f"解方程：{a}x + {b} = {a*x + b}",
                correct_answer=str(x),
                explanation=f"{a}x + {b} = {a*x + b}\n移项：{a}x = {a*x}\n两边除以{a}：x = {x}",
                grade=5,
                time_estimate=120,
                hint_levels=[f"先把{b}移到等号右边", f"{a}x = {a*x}，再解"],
            )
            qs.append(q)
        return qs

    def _gen_grade5_polygon_area(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            shape = random.choice(["parallelogram", "triangle", "trapezoid"])
            if shape == "parallelogram":
                base = random.randint(3, 15)
                height = random.randint(2, 10)
                area = base * height
                q = Question(
                    topic="多边形面积",
                    difficulty=6,
                    content=f"一个平行四边形，底是{base}厘米，高是{height}厘米，它的面积是多少平方厘米？",
                    correct_answer=str(area),
                    explanation=f"平行四边形面积 = 底 × 高 = {base} × {height} = {area}平方厘米",
                    grade=5,
                    time_estimate=90,
                    hint_levels=["平行四边形面积 = 底 × 高", f"{base} × {height}"],
                )
            elif shape == "triangle":
                base = random.randint(4, 16)
                height = random.randint(3, 12)
                area = base * height // 2
                if base * height % 2 != 0:
                    area_d = f"{base * height / 2:.1f}"
                else:
                    area_d = str(area)
                q = Question(
                    topic="多边形面积",
                    difficulty=6,
                    content=f"一个三角形，底是{base}厘米，高是{height}厘米，它的面积是多少平方厘米？",
                    correct_answer=area_d,
                    explanation=f"三角形面积 = 底 × 高 ÷ 2 = {base} × {height} ÷ 2 = {area_d}平方厘米",
                    grade=5,
                    time_estimate=90,
                    hint_levels=["三角形面积 = 底 × 高 ÷ 2", f"{base} × {height} ÷ 2"],
                )
            else:
                upper = random.randint(3, 10)
                lower = random.randint(5, 15)
                height = random.randint(3, 10)
                area = (upper + lower) * height // 2
                if (upper + lower) * height % 2 != 0:
                    area_d = f"{(upper + lower) * height / 2:.1f}"
                else:
                    area_d = str(area)
                q = Question(
                    topic="多边形面积",
                    difficulty=7,
                    content=f"一个梯形，上底{upper}厘米，下底{lower}厘米，高{height}厘米，面积是多少平方厘米？",
                    correct_answer=area_d,
                    explanation=f"梯形面积 = (上底 + 下底) × 高 ÷ 2 = ({upper}+{lower}) × {height} ÷ 2 = {area_d}平方厘米",
                    grade=5,
                    time_estimate=120,
                    hint_levels=["梯形面积 = (上底+下底)×高÷2", f"({upper}+{lower})×{height}÷2"],
                )
            qs.append(q)
        return qs

    # ─── 六年级 ─────────────────────────────────────────
    def _gen_grade6_percent(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            q_type = random.choice(["find_percent", "find_whole", "discount"])
            if q_type == "find_percent":
                part = random.randint(10, 80)
                whole = part + random.randint(10, 80)
                pct = round(part / whole * 100)
                q = Question(
                    topic="百分数",
                    difficulty=6,
                    content=f"某班有{whole}人，其中男生{part}人，男生占全班的百分之几？",
                    correct_answer=f"{pct}%",
                    explanation=f"{part} ÷ {whole} × 100% = {pct}%",
                    grade=6,
                    time_estimate=90,
                    hint_levels=[f"部分÷整体×100%", f"{part}÷{whole}×100%"],
                )
            elif q_type == "discount":
                original = random.randint(50, 500)
                discount = random.choice([5, 6, 7, 8, 9])
                sale = round(original * discount / 10)
                q = Question(
                    topic="百分数",
                    difficulty=7,
                    content=f"一件商品原价{original}元，打{discount}折出售，现价多少元？",
                    correct_answer=str(sale),
                    explanation=f"{discount}折 = {discount*10}%，\n{original} × {discount*10}% = {original} × {discount/10} = {sale}元",
                    grade=6,
                    time_estimate=90,
                    hint_levels=[f"{discount}折就是{discount*10}%", f"{original} × {discount*10}%"],
                )
            else:
                part = random.randint(20, 80)
                pct = random.choice([20, 25, 30, 40, 50, 60, 75, 80])
                whole = round(part / pct * 100)
                q = Question(
                    topic="百分数",
                    difficulty=7,
                    content=f"一个数的{pct}%是{part}，这个数是多少？",
                    correct_answer=str(whole),
                    explanation=f"已知一个数的{pct}%是{part}，\n这个数 = {part} ÷ {pct}% = {part} ÷ {pct/100} = {whole}",
                    grade=6,
                    time_estimate=120,
                    hint_levels=["已知部分和百分数求整体", f"{part} ÷ {pct}%"],
                )
            qs.append(q)
        return qs

    def _gen_grade6_ratio(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            q_type = random.choice(["simplify", "solve", "proportion"])
            if q_type == "simplify":
                a = random.randint(2, 9)
                b = random.randint(2, 9)
                c = a * random.randint(2, 6)
                d = b * random.randint(2, 6)
                g = _gcd(c, d)
                c2 = c // g
                d2 = d // g
                q = Question(
                    topic="比和比例",
                    difficulty=6,
                    content=f"化简比：{c}:{d} = ？",
                    correct_answer=f"{c2}:{d2}",
                    explanation=f"同时除以最大公因数{g}：{c}÷{g}:{d}÷{g} = {c2}:{d2}",
                    grade=6,
                    time_estimate=90,
                    hint_levels=[f"找{c}和{d}的公因数", f"最大公因数是{g}"],
                )
            elif q_type == "solve":
                a = random.randint(2, 6)
                b = random.randint(2, 6)
                x_val = random.randint(5, 20)
                c = a * x_val
                q = Question(
                    topic="比和比例",
                    difficulty=7,
                    content=f"解比例：{a}:{b} = x:{x_val * b // a}",
                    correct_answer=str(x_val),
                    explanation=f"内项积等于外项积：{b} × x = {a} × {x_val * b // a}\nx = {x_val}",
                    grade=6,
                    time_estimate=120,
                    hint_levels=["比例中外项积=内项积", f"{b}×x = {a}×?"],
                )
            else:
                # Proportional distribution
                total = random.randint(60, 300)
                r1 = random.randint(1, 5)
                r2 = random.randint(1, 5)
                r_sum = r1 + r2
                g = _gcd(r1 * total, r_sum)
                p1 = r1 * total // r_sum
                p2 = total - p1
                q = Question(
                    topic="比和比例",
                    difficulty=8,
                    content=f"把{total}按{r1}:{r2}的比例分配，两部分各是多少？",
                    correct_answer=f"{p1}和{p2}",
                    explanation=f"总份数：{r1}+{r2}={r_sum}\n每份：{total}÷{r_sum}={total//r_sum}\n第一部分：{r1}×{total//r_sum}={p1}\n第二部分：{r2}×{total//r_sum}={p2}",
                    grade=6,
                    time_estimate=150,
                    hint_levels=[f"总份数 = {r1}+{r2}", f"每份 = {total}÷{r_sum}"],
                )
            qs.append(q)
        return qs

    def _gen_grade6_circle(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            q_type = random.choice(["circumference", "area", "sector"])
            r = random.randint(3, 15)
            pi = 3.14
            if q_type == "circumference":
                c = round(2 * pi * r, 2)
                q = Question(
                    topic="圆的周长和面积",
                    difficulty=7,
                    content=f"一个圆的半径是{r}厘米，它的周长是多少厘米？（π取3.14）",
                    correct_answer=str(c),
                    explanation=f"圆周长 = 2πr = 2 × 3.14 × {r} = {c}厘米",
                    grade=6,
                    time_estimate=90,
                    hint_levels=["圆周长 = 2πr", f"2 × 3.14 × {r}"],
                )
            elif q_type == "area":
                area = round(pi * r * r, 2)
                q = Question(
                    topic="圆的周长和面积",
                    difficulty=7,
                    content=f"一个圆的半径是{r}厘米，它的面积是多少平方厘米？（π取3.14）",
                    correct_answer=str(area),
                    explanation=f"圆面积 = πr² = 3.14 × {r}² = 3.14 × {r*r} = {area}平方厘米",
                    grade=6,
                    time_estimate=90,
                    hint_levels=["圆面积 = πr²", f"{r} × {r} = {r*r}，再乘3.14"],
                )
            else:
                angle = random.choice([30, 45, 60, 90, 120, 180])
                sector_area = round(pi * r * r * angle / 360, 2)
                q = Question(
                    topic="圆的周长和面积",
                    difficulty=8,
                    content=f"一个圆半径{r}厘米，圆心角{angle}°的扇形面积是多少？（π取3.14）",
                    correct_answer=str(sector_area),
                    explanation=f"扇形面积 = πr² × {angle}/360 = 3.14 × {r*r} × {angle}/360 = {sector_area}平方厘米",
                    grade=6,
                    time_estimate=120,
                    hint_levels=[f"扇形面积占圆面积的{angle}/360", f"先算圆面积"],
                )
            qs.append(q)
        return qs

    def _gen_grade6_cylinder_cone(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            r = random.randint(2, 8)
            h = random.randint(5, 20)
            pi = 3.14
            vol = round(pi * r * r * h, 2)
            q_type = random.choice(["cylinder_vol", "cylinder_surface", "cone_vol"])
            if q_type == "cylinder_vol":
                q = Question(
                    topic="圆柱与圆锥",
                    difficulty=8,
                    content=f"一个圆柱底面半径{r}厘米，高{h}厘米，它的体积是多少立方厘米？（π取3.14）",
                    correct_answer=str(vol),
                    explanation=f"圆柱体积 = πr²h = 3.14 × {r*r} × {h} = {vol}立方厘米",
                    grade=6,
                    time_estimate=120,
                    hint_levels=["圆柱体积 = 底面积 × 高", f"底面积 = 3.14 × {r}²"],
                )
            elif q_type == "cylinder_surface":
                base_area = round(pi * r * r, 2)
                side_area = round(2 * pi * r * h, 2)
                surface = round(2 * base_area + side_area, 2)
                q = Question(
                    topic="圆柱与圆锥",
                    difficulty=9,
                    content=f"一个圆柱底面半径{r}厘米，高{h}厘米，它的表面积是多少？（π取3.14）",
                    correct_answer=str(surface),
                    explanation=f"表面积 = 2×底面积 + 侧面积\n= 2×3.14×{r*r} + 2×3.14×{r}×{h}\n= {2*base_area} + {side_area} = {surface}",
                    grade=6,
                    time_estimate=150,
                    hint_levels=["圆柱表面积 = 2个底面积 + 侧面积", "侧面积 = 底面周长 × 高"],
                )
            else:
                cone_vol = round(vol / 3, 2)
                q = Question(
                    topic="圆柱与圆锥",
                    difficulty=9,
                    content=f"一个圆锥底面半径{r}厘米，高{h}厘米，它的体积是多少？（π取3.14）",
                    correct_answer=str(cone_vol),
                    explanation=f"圆锥体积 = 1/3 × πr²h = 1/3 × 3.14 × {r*r} × {h} = {cone_vol}",
                    grade=6,
                    time_estimate=120,
                    hint_levels=["圆锥体积 = 圆柱体积 ÷ 3", f"先算圆柱体积：3.14×{r*r}×{h}"],
                )
            qs.append(q)
        return qs

    def _gen_grade6_negative(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            a = random.randint(-20, 20)
            b = random.randint(-20, 20)
            if a == 0:
                a = 5
            if b == 0:
                b = -3
            operator = random.choice(["+", "-"])
            if operator == "+":
                ans = a + b
                q = Question(
                    topic="负数",
                    difficulty=7,
                    content=f"计算：({a}) + ({b}) = ？",
                    correct_answer=str(ans),
                    explanation=f"({a}) + ({b}) = {ans}" + ("\n异号相加，取绝对值大的符号" if a * b < 0 else "\n同号相加，取相同符号"),
                    grade=6,
                    time_estimate=90,
                    hint_levels=["正数加负数，实际上是减法", f"{a} + ({b}) = {a} - {abs(b)}"],
                )
            else:
                ans = a - b
                q = Question(
                    topic="负数",
                    difficulty=7,
                    content=f"计算：({a}) - ({b}) = ？",
                    correct_answer=str(ans),
                    explanation=f"({a}) - ({b}) = ({a}) + ({-b}) = {ans}\n减去一个数等于加上它的相反数",
                    grade=6,
                    time_estimate=90,
                    hint_levels=["减去负数等于加正数", f"{a} - ({b}) = {a} + {-b}"],
                )
            qs.append(q)
        return qs

    # ─── 综合应用题 (跨年级) ─────────────────────────────
    def _gen_word_problems(self, count: int) -> list[Question]:
        """生成各年级应用题"""
        qs = []
        templates = [
            # (topic, grade, min_diff, max_diff, generator_func)
        ]
        for _ in range(count):
            grade = random.randint(1, 6)
            q_type = random.choice(self._word_problem_types_for_grade(grade))
            qs.append(self._gen_single_word_problem(grade, q_type))
        return qs

    def _word_problem_types_for_grade(self, grade: int) -> list[str]:
        types_map = {
            1: ["add_simple", "sub_simple", "compare"],
            2: ["add_sub_mixed", "multiply_simple", "divide_simple", "money"],
            3: ["multiply_word", "divide_word", "multi_step"],
            4: ["multi_step_4", "distance", "shopping"],
            5: ["equation_word", "fraction_word", "decimal_word"],
            6: ["percent_word", "ratio_word", "geometry_word"],
        }
        return types_map.get(grade, ["add_simple"])

    def _gen_single_word_problem(self, grade: int, q_type: str) -> Question:
        if q_type == "add_simple":
            a = random.randint(3, 20)
            b = random.randint(2, 10)
            return Question(
                topic="加法应用题", difficulty=1,
                content=f"小明有{a}个苹果，妈妈又给了他{b}个，小明现在一共有多少个苹果？",
                correct_answer=str(a + b),
                explanation=f"原来{a}个 + 新得{b}个 = {a+b}个",
                grade=1, time_estimate=60,
                hint_levels=["用加法", f"{a} + {b}"])

        if q_type == "sub_simple":
            a = random.randint(10, 30)
            b = random.randint(1, a)
            return Question(
                topic="减法应用题", difficulty=1,
                content=f"树上有{a}只小鸟，飞走了{b}只，树上还剩多少只？",
                correct_answer=str(a - b),
                explanation=f"原来{a}只 - 飞走{b}只 = {a-b}只",
                grade=1, time_estimate=60)

        if q_type == "multiply_simple":
            a = random.randint(2, 9)
            b = random.randint(2, 9)
            return Question(
                topic="乘法应用题", difficulty=2,
                content=f"每排有{a}棵树，共有{b}排，一共有多少棵树？",
                correct_answer=str(a * b),
                explanation=f"每排{a}棵 × {b}排 = {a*b}棵",
                grade=2, time_estimate=90,
                hint_levels=["每排棵数 × 排数 = 总棵数"])

        if q_type == "divide_simple":
            total = random.randint(12, 40)
            groups = random.choice([3, 4, 5, 6, 8])
            if total % groups == 0:
                per = total // groups
            else:
                groups_ok = [g for g in [3, 4, 5, 6, 8] if total % g == 0]
                groups = random.choice(groups_ok) if groups_ok else 4
                per = total // groups
            return Question(
                topic="除法应用题", difficulty=2,
                content=f"把{total}块糖平均分给{groups}个小朋友，每个小朋友得到几块？",
                correct_answer=str(per),
                explanation=f"{total} ÷ {groups} = {per}块",
                grade=2, time_estimate=90)

        if q_type == "money":
            price = random.randint(2, 15)
            qty = random.randint(2, 8)
            return Question(
                topic="购物应用题", difficulty=3,
                content=f"一支铅笔{price}角钱，小明买了{qty}支，一共花了多少钱？",  # 答案单位：角
                correct_answer=f"{price*qty}角",
                explanation=f"{price}角 × {qty} = {price*qty}角 = {price*qty//10}元{price*qty%10}角",
                grade=2, time_estimate=90,
                hint_levels=[f"单价 × 数量 = 总价", f"{price} × {qty}"])

        if q_type == "distance":
            speed = random.randint(30, 80)
            time_h = random.randint(1, 5)
            return Question(
                topic="路程应用题", difficulty=5,
                content=f"一辆汽车以每小时{speed}千米的速度行驶了{time_h}小时，一共行驶了多少千米？",
                correct_answer=str(speed * time_h),
                explanation=f"路程 = 速度 × 时间 = {speed} × {time_h} = {speed*time_h}千米",
                grade=4, time_estimate=120,
                hint_levels=["路程 = 速度 × 时间"])

        if q_type == "shopping":
            price = random.randint(5, 30)
            qty = random.randint(3, 20)
            return Question(
                topic="购物应用题", difficulty=5,
                content=f"一本书{price}元，学校买了{qty}本，一共花了多少钱？",
                correct_answer=str(price * qty),
                explanation=f"{price} × {qty} = {price*qty}元",
                grade=4, time_estimate=90)

        if q_type == "equation_word":
            x = random.randint(5, 30)
            a = random.randint(2, 9)
            b = random.randint(3, 20)
            total = a * x + b
            return Question(
                topic="方程应用题", difficulty=7,
                content=f"小明买了{a}本同样的书，付了{total}元，找回{b}元。每本书多少元？",
                correct_answer=str(x),
                explanation=f"设每本书x元：{a}x + {b} = {total}\n{a}x = {total-b}\nx = {x}",
                grade=5, time_estimate=150,
                hint_levels=[f"设每本书x元，列方程", f"实际花的钱 = {total}-{b}={total-b}"])

        if q_type == "percent_word":
            original = random.randint(100, 500)
            discount = random.choice([6, 7, 8, 9])
            sale = round(original * discount / 10)
            saved = original - sale
            return Question(
                topic="百分数应用题", difficulty=8,
                content=f"商店一件衣服打{discount}折后卖{sale}元，比原价便宜了多少元？",
                correct_answer=str(saved),
                explanation=f"原价 = {sale} ÷ {discount*10}% = {original}元\n便宜了：{original} - {sale} = {saved}元",
                grade=6, time_estimate=120,
                hint_levels=[f"先求原价：{sale}÷{discount*10}%", f"打折就是×{discount/10}"])

        # default fallback
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        return Question(
            topic="综合应用题", difficulty=3,
            content=f"树上有{a}只鸟，又飞来{b}只，现在有多少只？",
            correct_answer=str(a+b),
            explanation=f"{a}+{b}={a+b}",
            grade=1, time_estimate=60)

    # ─── 主生成入口 ─────────────────────────────────────
    def generate_all(self,
                     questions_per_grade_topic: int = 100) -> list[Question]:
        """生成全部年级的题目
        Args:
            questions_per_grade_topic: 每个年级每个知识点生成的题目数
        Returns:
            全部题目列表
        """
        all_questions = []

        generators_by_grade = {
            1: [
                (self._gen_grade1_add_sub_10, questions_per_grade_topic),
                (self._gen_grade1_add_sub_20, questions_per_grade_topic),
                (self._gen_grade1_compare, questions_per_grade_topic // 2),
                (self._gen_grade1_shapes, questions_per_grade_topic // 3),
            ],
            2: [
                (self._gen_grade2_add_sub_100, questions_per_grade_topic),
                (self._gen_grade2_multiplication, questions_per_grade_topic),
                (self._gen_grade2_division, questions_per_grade_topic),
                (self._gen_grade2_length, questions_per_grade_topic // 2),
            ],
            3: [
                (self._gen_grade3_multi_digit, questions_per_grade_topic),
                (self._gen_grade3_division_1digit, questions_per_grade_topic),
                (self._gen_grade3_fractions_intro, questions_per_grade_topic // 2),
                (self._gen_grade3_perimeter, questions_per_grade_topic // 2),
            ],
            4: [
                (self._gen_grade4_large_numbers, questions_per_grade_topic // 2),
                (self._gen_grade4_multiplication_2digit, questions_per_grade_topic),
                (self._gen_grade4_division_2digit, questions_per_grade_topic),
                (self._gen_grade4_decimals_intro, questions_per_grade_topic),
                (self._gen_grade4_triangles, questions_per_grade_topic // 2),
            ],
            5: [
                (self._gen_grade5_decimal_ops, questions_per_grade_topic),
                (self._gen_grade5_fractions, questions_per_grade_topic),
                (self._gen_grade5_equations, questions_per_grade_topic),
                (self._gen_grade5_polygon_area, questions_per_grade_topic),
            ],
            6: [
                (self._gen_grade6_percent, questions_per_grade_topic),
                (self._gen_grade6_ratio, questions_per_grade_topic),
                (self._gen_grade6_circle, questions_per_grade_topic),
                (self._gen_grade6_cylinder_cone, questions_per_grade_topic),
                (self._gen_grade6_negative, questions_per_grade_topic // 2),
            ],
        }

        for grade, gen_list in generators_by_grade.items():
            for gen_func, count in gen_list:
                try:
                    qs = gen_func(count)
                    all_questions.extend(qs)
                except Exception as e:
                    print(f"  ⚠ 生成 Grade{grade} {gen_func.__name__} 时出错: {e}")

        # 额外生成应用题
        word_problems = self._gen_word_problems(questions_per_grade_topic * 3)
        all_questions.extend(word_problems)

        return all_questions

    def generate_and_save(self,
                          questions_per_grade_topic: int = 100,
                          filename: str = "math_questions.json"):
        """生成并保存到 JSON 文件"""
        os.makedirs(DATA_DIR, exist_ok=True)
        questions = self.generate_all(questions_per_grade_topic)
        output = [q.to_task_dict() for q in questions]

        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 数学题库生成完成！")
        print(f"   总题数: {len(questions)}")
        print(f"   保存至: {filepath}")

        # 统计
        by_grade = {}
        for q in questions:
            by_grade[q.grade] = by_grade.get(q.grade, 0) + 1
        for g in sorted(by_grade):
            print(f"   {g}年级: {by_grade[g]} 题")

        by_topic = {}
        for q in questions:
            by_topic[q.topic] = by_topic.get(q.topic, 0) + 1
        print(f"   知识点数: {len(by_topic)}")

        return filepath


# ─── 工具函数 ─────────────────────────────────────────
def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


if __name__ == "__main__":
    gen = MathGenerator()
    gen.generate_and_save(questions_per_grade_topic=200)
