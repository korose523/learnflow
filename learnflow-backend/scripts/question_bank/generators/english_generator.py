"""小学英语题库生成器 — 覆盖1-6年级全部核心知识点
包含：词汇、语法、句型、阅读理解等
"""
import json
import random
import os
from dataclasses import dataclass, field

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@dataclass
class Question:
    topic: str
    difficulty: int
    content: str
    correct_answer: str
    explanation: str
    grade: int
    question_type: str = "vocabulary"
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
            "source": "english_generator",
            "content_type": "text",
            "is_approved": True,
            "grade": self.grade,
            "question_type": self.question_type,
        }

# ─── 英语知识库 ─────────────────────────────────────────

# 词汇库 (按年级)
GRADE_VOCABULARY = {
    1: [
        ("apple", "苹果"), ("banana", "香蕉"), ("cat", "猫"), ("dog", "狗"),
        ("egg", "鸡蛋"), ("fish", "鱼"), ("girl", "女孩"), ("hat", "帽子"),
        ("ice", "冰"), ("juice", "果汁"), ("kite", "风筝"), ("lion", "狮子"),
        ("milk", "牛奶"), ("nose", "鼻子"), ("orange", "橙子"), ("pen", "钢笔"),
        ("queen", "女王"), ("red", "红色"), ("sun", "太阳"), ("tree", "树"),
        ("umbrella", "雨伞"), ("van", "面包车"), ("water", "水"), ("box", "盒子"),
        ("yellow", "黄色"), ("zoo", "动物园"), ("one", "一"), ("two", "二"),
        ("three", "三"), ("four", "四"), ("five", "五"), ("book", "书"),
        ("bag", "书包"), ("desk", "课桌"), ("chair", "椅子"), ("door", "门"),
        ("window", "窗户"), ("teacher", "老师"), ("student", "学生"), ("school", "学校"),
        ("mother", "妈妈"), ("father", "爸爸"), ("brother", "兄弟"), ("sister", "姐妹"),
        ("bird", "鸟"), ("flower", "花"), ("star", "星星"), ("moon", "月亮"),
    ],
    2: [
        ("blue", "蓝色"), ("green", "绿色"), ("white", "白色"), ("black", "黑色"),
        ("pink", "粉色"), ("purple", "紫色"), ("brown", "棕色"), ("gray", "灰色"),
        ("big", "大"), ("small", "小"), ("long", "长"), ("short", "短"),
        ("tall", "高"), ("fat", "胖"), ("thin", "瘦"), ("new", "新"),
        ("old", "旧"), ("good", "好"), ("bad", "坏"), ("happy", "开心的"),
        ("sad", "伤心的"), ("hot", "热"), ("cold", "冷"), ("warm", "温暖的"),
        ("cool", "凉爽的"), ("eat", "吃"), ("drink", "喝"), ("run", "跑"),
        ("jump", "跳"), ("swim", "游泳"), ("sing", "唱歌"), ("dance", "跳舞"),
        ("read", "阅读"), ("write", "写"), ("draw", "画"), ("play", "玩"),
        ("sleep", "睡觉"), ("walk", "走"), ("fly", "飞"), ("cook", "做饭"),
        ("head", "头"), ("hand", "手"), ("foot", "脚"), ("eye", "眼睛"),
        ("ear", "耳朵"), ("mouth", "嘴"), ("arm", "手臂"), ("leg", "腿"),
        ("spring", "春天"), ("summer", "夏天"), ("autumn", "秋天"), ("winter", "冬天"),
    ],
    3: [
        ("beautiful", "美丽的"), ("wonderful", "精彩的"), ("delicious", "美味的"),
        ("favorite", "最喜欢的"), ("different", "不同的"), ("important", "重要的"),
        ("interesting", "有趣的"), ("difficult", "困难的"), ("easy", "容易的"),
        ("hungry", "饥饿的"), ("thirsty", "口渴的"), ("tired", "累的"),
        ("angry", "生气的"), ("afraid", "害怕的"), ("excited", "兴奋的"),
        ("breakfast", "早餐"), ("lunch", "午餐"), ("dinner", "晚餐"),
        ("vegetable", "蔬菜"), ("fruit", "水果"), ("chicken", "鸡肉"),
        ("noodle", "面条"), ("rice", "米饭"), ("bread", "面包"),
        ("weather", "天气"), ("rainy", "下雨的"), ("sunny", "晴朗的"),
        ("cloudy", "多云的"), ("windy", "有风的"), ("snowy", "下雪的"),
        ("animal", "动物"), ("elephant", "大象"), ("monkey", "猴子"),
        ("panda", "熊猫"), ("tiger", "老虎"), ("rabbit", "兔子"),
        ("subject", "科目"), ("Chinese", "语文"), ("math", "数学"),
        ("English", "英语"), ("science", "科学"), ("music", "音乐"),
        ("art", "美术"), ("PE", "体育"), ("computer", "电脑"),
        ("hospital", "医院"), ("library", "图书馆"), ("supermarket", "超市"),
        ("cinema", "电影院"), ("park", "公园"), ("museum", "博物馆"),
        ("behind", "在后面"), ("between", "在...之间"), ("beside", "在...旁边"),
        ("under", "在...下面"), ("above", "在...上面"), ("near", "在...附近"),
    ],
    4: [
        ("always", "总是"), ("usually", "通常"), ("sometimes", "有时候"),
        ("never", "从不"), ("often", "经常"), ("already", "已经"),
        ("tomorrow", "明天"), ("yesterday", "昨天"), ("today", "今天"),
        ("morning", "早晨"), ("afternoon", "下午"), ("evening", "傍晚"),
        ("night", "夜晚"), ("week", "周"), ("month", "月"), ("year", "年"),
        ("January", "一月"), ("February", "二月"), ("March", "三月"),
        ("April", "四月"), ("Monday", "星期一"), ("Tuesday", "星期二"),
        ("Wednesday", "星期三"), ("Thursday", "星期四"), ("Friday", "星期五"),
        ("Saturday", "星期六"), ("Sunday", "星期日"),
        ("doctor", "医生"), ("nurse", "护士"), ("driver", "司机"),
        ("policeman", "警察"), ("firefighter", "消防员"), ("farmer", "农民"),
        ("cook_chef", "厨师"), ("singer", "歌手"), ("writer", "作家"),
        ("bedroom", "卧室"), ("bathroom", "浴室"), ("kitchen", "厨房"),
        ("living room", "客厅"), ("garden", "花园"), ("balcony", "阳台"),
        ("mountain", "山"), ("river", "河流"), ("lake", "湖"),
        ("forest", "森林"), ("island", "岛屿"), ("bridge", "桥"),
        ("bicycle", "自行车"), ("bus", "公共汽车"), ("train", "火车"),
        ("plane", "飞机"), ("ship", "轮船"), ("subway", "地铁"),
        ("strong", "强壮的"), ("weak", "虚弱的"), ("brave", "勇敢的"),
        ("clever", "聪明的"), ("kind", "善良的"), ("friendly", "友好的"),
        ("quiet", "安静的"), ("noisy", "吵闹的"), ("clean", "干净的"), ("dirty", "脏的"),
    ],
    5: [
        ("prepare", "准备"), ("remember", "记得"), ("forget", "忘记"),
        ("believe", "相信"), ("decide", "决定"), ("enjoy", "享受"),
        ("finish", "完成"), ("practice", "练习"), ("travel", "旅行"),
        ("collect", "收集"), ("protect", "保护"), ("explain", "解释"),
        ("describe", "描述"), ("imagine", "想象"), ("invent", "发明"),
        ("discover", "发现"), ("explore", "探索"), ("celebrate", "庆祝"),
        ("environment", "环境"), ("pollution", "污染"), ("energy", "能源"),
        ("recycle", "回收"), ("nature", "自然"), ("earth", "地球"),
        ("culture", "文化"), ("festival", "节日"), ("tradition", "传统"),
        ("national", "国家的"), ("international", "国际的"), ("foreign", "外国的"),
        ("experience", "经历"), ("education", "教育"), ("knowledge", "知识"),
        ("information", "信息"), ("technology", "科技"), ("invention", "发明"),
        ("adventure", "冒险"), ("challenge", "挑战"), ("competition", "比赛"),
        ("exercise", "锻炼"), ("health", "健康"), ("medicine", "药"),
        ("problem", "问题"), ("solution", "解决办法"), ("suggestion", "建议"),
        ("opinion", "意见"), ("conversation", "对话"), ("communication", "交流"),
        ("natural", "自然的"), ("modern", "现代的"), ("ancient", "古代的"),
        ("popular", "流行的"), ("special", "特别的"), ("common", "普通的"),
    ],
    6: [
        ("achieve", "实现"), ("continue", "继续"), ("develop", "发展"),
        ("improve", "提高"), ("increase", "增加"), ("reduce", "减少"),
        ("require", "需要"), ("support", "支持"), ("include", "包括"),
        ("provide", "提供"), ("receive", "收到"), ("express", "表达"),
        ("opportunity", "机会"), ("responsibility", "责任"), ("achievement", "成就"),
        ("government", "政府"), ("society", "社会"), ("community", "社区"),
        ("relationship", "关系"), ("attitude", "态度"), ("behavior", "行为"),
        ("character", "性格"), ("personality", "个性"), ("confidence", "自信"),
        ("encouragement", "鼓励"), ("independence", "独立"), ("cooperation", "合作"),
        ("graduation", "毕业"), ("ceremony", "典礼"), ("celebration", "庆祝"),
        ("volunteer", "志愿者"), ("charity", "慈善"), ("donation", "捐赠"),
        ("climate", "气候"), ("temperature", "温度"), ("condition", "条件"),
        ("article", "文章"), ("paragraph", "段落"), ("sentence", "句子"),
        ("grammar", "语法"), ("vocabulary", "词汇"), ("pronunciation", "发音"),
        ("conversation", "会话"), ("presentation", "展示"), ("introduction", "介绍"),
        ("imagination", "想象力"), ("creation", "创造"), ("curiosity", "好奇心"),
        ("patient", "耐心的"), ("responsible", "负责的"), ("independent", "独立的"),
        ("confident", "自信的"), ("creative", "有创造力的"), ("generous", "慷慨的"),
        ("honest", "诚实的"), ("polite", "有礼貌的"), ("humorous", "幽默的"),
    ],
}

# 语法点库
GRAMMAR_POINTS = {
    3: [
        ("a/an 用法", "a用于辅音开头的单词前，an用于元音开头的单词前"),
        ("be动词", "am/is/are 的用法：I用am，he/she/it用is，you/we/they用are"),
        ("名词复数", "大多数名词加s，以s/x/sh/ch结尾加es"),
    ],
    4: [
        ("现在进行时", "am/is/are + 动词ing，表示正在进行的动作"),
        ("一般过去时", "动词过去式，表示过去发生的动作"),
        ("比较级", "形容词比较级：-er或more，用于两者比较"),
    ],
    5: [
        ("一般将来时", "will + 动词原形 或 be going to + 动词原形"),
        ("现在完成时", "have/has + 过去分词"),
        ("情态动词", "can/could/must/should/may + 动词原形"),
    ],
    6: [
        ("被动语态", "be + 过去分词"),
        ("定语从句", "who/that/which引导的从句修饰名词"),
        ("条件状语从句", "if引导的条件句"),
    ],
}

# 句型模板
SENTENCE_PATTERNS = {
    3: [
        ("I like ___.", "我喜欢___。", "like"),
        ("This is my ___.", "这是我的___。", "my"),
        ("I have a ___.", "我有一个___。", "have"),
        ("Can you ___?", "你能___吗？", "can"),
        ("What is your ___?", "你的___是什么？", "what"),
    ],
    4: [
        ("I am ___ing ___.", "我正在___。", "现在进行时"),
        ("There is/are ___.", "有___。", "there be"),
        ("I want to ___.", "我想要___。", "want"),
        ("He/She is ___ than ___.", "他/她比___更___。", "比较级"),
    ],
    5: [
        ("I will ___ tomorrow.", "我明天将___。", "将来时"),
        ("I have ___ed ___.", "我已经___了___。", "完成时"),
        ("You should ___.", "你应该___。", "情态动词"),
        ("If it ___, I will ___.", "如果___，我就___。", "条件句"),
    ],
    6: [
        ("It is ___ that ___.", "___是___的。", "it句型"),
        ("I think that ___.", "我认为___。", "宾语从句"),
        ("The ___ which ___ is ___.", "那个___的___是___。", "定语从句"),
    ],
}


class EnglishGenerator:
    """小学英语题库生成器"""

    # ─── 词汇（英译中）──────────────────────────────────
    def _gen_vocab_en2cn(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            grade = random.randint(1, 6)
            if grade not in GRADE_VOCABULARY:
                continue
            word, chinese = random.choice(GRADE_VOCABULARY[grade])
            q = Question(
                topic="词汇英译中",
                difficulty=min(grade, 5),
                content=f"写出下面英文单词的中文意思：\n「{word}」",
                correct_answer=chinese,
                explanation=f"「{word}」的中文意思是「{chinese}」。",
                grade=grade,
                time_estimate=40,
                hint_levels=[f"这个单词和日常生活有关", f"想想你学过的单词"],
            )
            qs.append(q)
        return qs

    # ─── 词汇（中译英）──────────────────────────────────
    def _gen_vocab_cn2en(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            grade = random.randint(1, 6)
            if grade not in GRADE_VOCABULARY:
                continue
            word, chinese = random.choice(GRADE_VOCABULARY[grade])
            q = Question(
                topic="词汇中译英",
                difficulty=min(grade + 1, 7),
                content=f"写出下面中文词语对应的英文单词：\n「{chinese}」",
                correct_answer=word,
                explanation=f"「{chinese}」的英文是「{word}」。",
                grade=grade,
                time_estimate=50,
                hint_levels=[f"这个单词的第一个字母是 {word[0]}", f"这个单词有 {len(word)} 个字母"],
            )
            qs.append(q)
        return qs

    # ─── 单词拼写 ──────────────────────────────────────
    def _gen_spelling(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            grade = random.randint(1, 4)
            if grade not in GRADE_VOCABULARY:
                continue
            word, chinese = random.choice(GRADE_VOCABULARY[grade])
            if len(word) < 3:
                continue
            missing_idx = random.randint(0, len(word) - 1)
            masked = word[:missing_idx] + " _ " + word[missing_idx+1:]
            q = Question(
                topic="单词拼写",
                difficulty=min(grade + 2, 6),
                content=f"补全单词（{chinese}）：\n{masked}",
                correct_answer=word[missing_idx],
                explanation=f"完整的单词是「{word}」，缺失的字母是「{word[missing_idx]}」。",
                grade=grade,
                time_estimate=45,
                hint_levels=[f"这个单词的中文意思是{chinese}", f"单词是 {word[:missing_idx+1]}..."],
            )
            qs.append(q)
        return qs

    # ─── 选择题 ────────────────────────────────────────
    def _gen_multiple_choice(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            grade = random.randint(2, 6)
            if grade not in GRADE_VOCABULARY or len(GRADE_VOCABULARY[grade]) < 4:
                continue
            correct, chinese = random.choice(GRADE_VOCABULARY[grade])
            # Select 3 wrong options
            all_words = [w for w, _ in GRADE_VOCABULARY[grade] if w != correct]
            if len(all_words) < 3:
                wrong = random.sample(all_words, len(all_words))
            else:
                wrong = random.sample(all_words, 3)

            options = [correct] + wrong
            random.shuffle(options)
            labels = ["A", "B", "C", "D"]
            option_text = "\n".join([f"{labels[i]}. {options[i]}" for i in range(len(options))])
            correct_label = labels[options.index(correct)]

            q = Question(
                topic="词汇选择",
                difficulty=min(grade + 1, 5),
                content=f"选择与「{chinese}」对应的英文单词：\n{option_text}",
                correct_answer=correct_label,
                explanation=f"「{chinese}」的英文是「{correct}」，选{correct_label}。",
                grade=grade,
                time_estimate=60,
                hint_levels=[f"这个单词的第一个字母是 {correct[0]}", f"排除不认识的选项"],
            )
            qs.append(q)
        return qs

    # ─── 语法 ──────────────────────────────────────────
    def _gen_grammar(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            grade = random.randint(3, 6)
            if grade not in GRAMMAR_POINTS:
                continue
            topic, rule = random.choice(GRAMMAR_POINTS[grade])

            # Generate specific grammar questions
            if "a/an" in topic:
                # a/an question
                words_an = ["apple", "egg", "orange", "umbrella", "elephant", "ice cream"]
                words_a = ["book", "cat", "dog", "pen", "sun", "tree"]
                if random.random() < 0.5:
                    word = random.choice(words_an)
                    ans = "an"
                else:
                    word = random.choice(words_a)
                    ans = "a"
                q = Question(
                    topic="语法-a/an",
                    difficulty=3,
                    content=f"选择 a 或 an 填空：\nI have ___ {word}.",
                    correct_answer=ans,
                    explanation=f"{word}开头是{'元音' if ans=='an' else '辅音'}，所以用{ans}。",
                    grade=3, time_estimate=40,
                    hint_levels=[f"{word}的第一个字母是什么？", "元音字母开头用an"],
                )

            elif "be动词" in topic:
                subjects = [("I", "am"), ("He", "is"), ("She", "is"), ("It", "is"),
                           ("You", "are"), ("We", "are"), ("They", "are")]
                subj, ans = random.choice(subjects)
                q = Question(
                    topic="语法-be动词",
                    difficulty=3,
                    content=f"用 am/is/are 填空：\n{subj} ___ a student.",
                    correct_answer=ans,
                    explanation=f"主语「{subj}」搭配be动词「{ans}」。",
                    grade=3, time_estimate=40,
                    hint_levels=["I用am，he/she/it用is", "you/we/they用are"],
                )

            elif "现在进行时" in topic:
                verbs_ing = [("play", "playing"), ("run", "running"), ("swim", "swimming"),
                            ("read", "reading"), ("eat", "eating"), ("dance", "dancing")]
                v, ing = random.choice(verbs_ing)
                q = Question(
                    topic="语法-现在进行时",
                    difficulty=4,
                    content=f"用所给词的适当形式填空：\nLook! The boy is ___ ( {v} ) now.",
                    correct_answer=ing,
                    explanation=f"{v}的现在分词是{ing}。（注意：{'双写末尾辅音加ing' if ing[-3] == ing[-2] else '直接加ing' if ing.endswith('ing') and not ing.endswith('eing') else '去e加ing'}）",
                    grade=4, time_estimate=60,
                    hint_levels=["现在进行时 = be + 动词ing", f"{v}如何变成ing形式？"],
                )

            elif "一般过去时" in topic:
                verbs_past = [("play", "played"), ("watch", "watched"), ("visit", "visited"),
                             ("go", "went"), ("eat", "ate"), ("see", "saw"),
                             ("have", "had"), ("do", "did"), ("come", "came")]
                v, past = random.choice(verbs_past)
                q = Question(
                    topic="语法-一般过去时",
                    difficulty=5,
                    content=f"用所给词的适当形式填空：\nYesterday, I ___ ( {v} ) a movie.",
                    correct_answer=past,
                    explanation=f"{v}的过去式是{past}{'（不规则变化）' if past != v+'ed' else '（规则变化，加ed）'}。",
                    grade=4, time_estimate=60,
                    hint_levels=["yesterday提示用一般过去时", f"{v}的过去式是？"],
                )

            elif "比较级" in topic:
                adj_pairs = [("big", "bigger"), ("small", "smaller"), ("tall", "taller"),
                            ("short", "shorter"), ("beautiful", "more beautiful")]
                adj, comp = random.choice(adj_pairs)
                q = Question(
                    topic="语法-比较级",
                    difficulty=5,
                    content=f"用所给词的适当形式填空：\nTom is ___ ( {adj} ) than Jack.",
                    correct_answer=comp,
                    explanation=f"{adj}的比较级是{comp}。",
                    grade=4, time_estimate=60,
                    hint_levels=["than提示用比较级", f"{adj}如何变成比较级？"],
                )

            elif "一般将来时" in topic:
                v = random.choice(["go", "play", "visit", "have", "do", "see"])
                ans = f"will {v}"
                q = Question(
                    topic="语法-一般将来时",
                    difficulty=5,
                    content=f"用一般将来时填空：\nI ___ ( {v} ) to Beijing next week.",
                    correct_answer=ans,
                    explanation=f"一般将来时用 will + 动词原形。下周去北京：will {v}。",
                    grade=5, time_estimate=60,
                    hint_levels=["next week提示用将来时", "将来时 = will + 动词原形"],
                )

            elif "现在完成时" in topic:
                v = random.choice(["finish", "see", "visit", "read", "eat"])
                past_p = {"finish": "finished", "see": "seen", "visit": "visited",
                          "read": "read", "eat": "eaten"}
                ans = f"have {past_p[v]}"
                q = Question(
                    topic="语法-现在完成时",
                    difficulty=7,
                    content=f"用现在完成时填空：\nI ___ already ___ ( {v} ) my homework.",
                    correct_answer=f"have {past_p[v]}",
                    explanation=f"现在完成时：have/has + 过去分词。{v}的过去分词是{past_p[v]}。",
                    grade=6, time_estimate=60,
                    hint_levels=["already提示用完成时", f"{v}的过去分词是什么？"],
                )

            elif "情态动词" in topic:
                modals = [("can", "能"), ("must", "必须"), ("should", "应该"), ("may", "可以")]
                modal, meaning = random.choice(modals)
                q = Question(
                    topic="语法-情态动词",
                    difficulty=5,
                    content=f"选择适当的情态动词填空（{meaning}）：\nYou ___ finish your homework before playing.",
                    correct_answer=modal,
                    explanation=f"表示「{meaning}」用情态动词「{modal}」。\n情态动词后跟动词原形。",
                    grade=5, time_estimate=60,
                    hint_levels=["表示「必须」用must", "情态动词后跟动词原形"],
                )

            elif "被动语态" in topic:
                items = [("make", "made"), ("write", "written"), ("build", "built"),
                        ("invent", "invented"), ("use", "used")]
                v, pp = random.choice(items)
                ans = f"is {pp}"
                q = Question(
                    topic="语法-被动语态",
                    difficulty=8,
                    content=f"用被动语态填空：\nThis book ___ ( {v} ) in China.",
                    correct_answer=ans,
                    explanation=f"被动语态：be + 过去分词。{v}的过去分词是{pp}。主语是单数，用is。",
                    grade=6, time_estimate=90,
                    hint_levels=["书是被制造的，用被动语态", f"{v}的过去分词是{pp}"],
                )

            else:
                # generic fallback
                q = Question(
                    topic=f"语法-{topic}",
                    difficulty=min(grade + 2, 8),
                    content=f"关于{topic}，请写出一个规则：{rule[:20]}...",
                    correct_answer=f"（参考）{rule}",
                    explanation=rule,
                    grade=grade, time_estimate=90,
                )

            qs.append(q)
        return qs

    # ─── 连词成句 ──────────────────────────────────────
    def _gen_sentence_reorder(self, count: int) -> list[Question]:
        qs = []
        sentences = {
            3: [
                ("I like apples.", "我喜欢苹果。"),
                ("This is my book.", "这是我的书。"),
                ("He is a teacher.", "他是一位老师。"),
                ("She has a dog.", "她有一只狗。"),
                ("Can you swim?", "你会游泳吗？"),
                ("What is your name?", "你叫什么名字？"),
                ("How old are you?", "你多大了？"),
                ("I have two eyes.", "我有两只眼睛。"),
                ("The cat is cute.", "这只猫很可爱。"),
                ("We go to school.", "我们去上学。"),
            ],
            4: [
                ("He is playing football.", "他正在踢足球。"),
                ("There is a book on the desk.", "桌上有一本书。"),
                ("I want to be a doctor.", "我想成为一名医生。"),
                ("She is taller than me.", "她比我高。"),
                ("Yesterday I went to the park.", "昨天我去了公园。"),
                ("My favorite color is blue.", "我最喜欢的颜色是蓝色。"),
            ],
            5: [
                ("I will visit my grandparents tomorrow.", "我明天将去看祖父母。"),
                ("He has already finished his homework.", "他已经完成了作业。"),
                ("You should eat more vegetables.", "你应该多吃蔬菜。"),
                ("If it rains, I will stay at home.", "如果下雨，我就待在家。"),
            ],
        }

        for grade, sent_list in sentences.items():
            for _ in range(min(count // 3, len(sent_list) * 2)):
                english, chinese = random.choice(sent_list)
                words = english.rstrip(".").rstrip("?").split()
                random.shuffle(words)
                shuffled = " / ".join(words)

                q = Question(
                    topic="连词成句",
                    difficulty=min(grade + 1, 6),
                    content=f"连词成句（{chinese}）：\n{shuffled}",
                    correct_answer=english,
                    explanation=f"正确的句子是：{english}\n中文意思：{chinese}",
                    grade=grade, time_estimate=90,
                    hint_levels=[f"第一个词可能是 {english.split()[0]}", "检查首字母要大写"],
                )
                qs.append(q)
        return qs

    # ─── 翻译句子 ──────────────────────────────────────
    def _gen_translation(self, count: int) -> list[Question]:
        qs = []
        translations = [
            ("我喜欢苹果。", "I like apples.", 3),
            ("这是一本书。", "This is a book.", 3),
            ("她是我的妈妈。", "She is my mother.", 3),
            ("我有一支钢笔。", "I have a pen.", 3),
            ("他正在踢足球。", "He is playing football.", 4),
            ("桌上有一个苹果。", "There is an apple on the desk.", 4),
            ("她比我高。", "She is taller than me.", 4),
            ("昨天我去公园了。", "I went to the park yesterday.", 4),
            ("我明天将去北京。", "I will go to Beijing tomorrow.", 5),
            ("你应该多喝水。", "You should drink more water.", 5),
            ("如果下雨我就待在家。", "If it rains, I will stay at home.", 5),
            ("我已经完成了我的作业。", "I have already finished my homework.", 6),
            ("这本书是在中国制造的。", "This book is made in China.", 6),
            ("我认为他是对的。", "I think he is right.", 6),
        ]
        for _ in range(count):
            cn, en, grade = random.choice(translations)
            q = Question(
                topic="句子翻译",
                difficulty=min(grade + 2, 8),
                content=f"把下面的中文翻译成英文：\n「{cn}」",
                correct_answer=en,
                explanation=f"翻译：{en}\n关键词：{cn}",
                grade=grade, time_estimate=120,
                hint_levels=[f"关键结构：{en.split()[0]}...", "检查时态和单复数"],
            )
            qs.append(q)
        return qs

    # ─── 阅读理解 (小学英语) ───────────────────────────
    def _gen_reading(self, count: int) -> list[Question]:
        qs = []
        passages = [
            {
                "title": "My Family",
                "text": "Hello! My name is Tom. I am ten years old. There are four people in my family. My father is a doctor. My mother is a teacher. I have a sister. Her name is Lily. She is seven years old. I love my family.",
                "grade": 4,
                "questions": [
                    ("How old is Tom?", "Ten years old.", "第二句说\"I am ten years old.\""),
                    ("What does Tom's father do?", "He is a doctor.", "第四句说\"My father is a doctor.\""),
                    ("How many people are there in Tom's family?", "Four.", "第三句说\"There are four people in my family.\""),
                ]
            },
            {
                "title": "A Busy Day",
                "text": "Today is Monday. I get up at 6:30 in the morning. I have breakfast at 7:00. I go to school at 7:30. We have four classes in the morning. I have lunch at 12:00. In the afternoon, I play football with my friends. I do my homework at 5:00. I go to bed at 9:00.",
                "grade": 5,
                "questions": [
                    ("What day is it today?", "Monday.", "第一句说\"Today is Monday.\""),
                    ("When does the writer get up?", "At 6:30.", "第二句说\"I get up at 6:30.\""),
                    ("What does the writer do in the afternoon?", "Plays football with friends.", "第八句说\"I play football with my friends.\""),
                ]
            },
            {
                "title": "Protecting the Environment",
                "text": "Our Earth is beautiful, but it is getting dirty now. People throw rubbish everywhere. Factories pour dirty water into rivers. Cars make the air dirty. We should protect our environment. We can plant more trees. We can use fewer plastic bags. We can take the bus instead of driving. If everyone does something, our Earth will become clean again.",
                "grade": 6,
                "questions": [
                    ("What is happening to our Earth?", "It is getting dirty.", "第一句说\"it is getting dirty now.\""),
                    ("Name one way to protect the environment according to the passage.", "Plant more trees / Use fewer plastic bags / Take the bus.", "文章列举了多种环保方法。"),
                    ("What will happen if everyone does something?", "The Earth will become clean again.", "最后一句说明。"),
                ]
            },
        ]

        for passage in passages:
            for q_data in passage["questions"]:
                q_text, answer, explanation = q_data
                q = Question(
                    topic="英语阅读理解",
                    difficulty=passage["grade"] + 1,
                    content=f"阅读短文，回答问题：\n\n【{passage['title']}】\n{passage['text']}\n\n问题：{q_text}",
                    correct_answer=answer,
                    explanation=explanation,
                    grade=passage["grade"],
                    time_estimate=180,
                    hint_levels=["仔细阅读短文", "答案可以在文中直接找到"],
                )
                qs.append(q)
                if len(qs) >= count:
                    return qs
        return qs

    # ─── 情景对话 ──────────────────────────────────────
    def _gen_dialogue(self, count: int) -> list[Question]:
        qs = []
        dialogues = [
            ("A: Hello! How are you?\nB: ___", "Fine, thank you.", "问候", 3),
            ("A: What's your name?\nB: ___", "My name is ____.", "介绍", 3),
            ("A: Nice to meet you.\nB: ___", "Nice to meet you, too.", "见面", 3),
            ("A: How old are you?\nB: ___", "I am ___ years old.", "年龄", 3),
            ("A: Where is the library?\nB: ___", "It's over there.", "问路", 4),
            ("A: What time is it?\nB: ___", "It's 3 o'clock.", "时间", 4),
            ("A: May I speak to Tom?\nB: ___", "This is Tom speaking.", "电话", 5),
            ("A: Would you like some tea?\nB: ___", "Yes, please. / No, thank you.", "邀请", 4),
            ("A: What's the weather like today?\nB: ___", "It's sunny.", "天气", 4),
            ("A: How much is this book?\nB: ___", "It's ten yuan.", "购物", 5),
            ("A: Excuse me, can you help me?\nB: ___", "Of course.", "求助", 5),
            ("A: Happy birthday!\nB: ___", "Thank you!", "祝福", 4),
        ]

        for _ in range(count):
            prompt, answer, topic, grade = random.choice(dialogues)
            q = Question(
                topic=f"情景对话-{topic}",
                difficulty=min(grade + 1, 5),
                content=f"补全对话：\n{prompt}",
                correct_answer=answer,
                explanation=f"这是{topic}场景的常用表达：{answer}",
                grade=grade, time_estimate=60,
                hint_levels=[f"这是{topic}场景", "想想常用的回答"],
            )
            qs.append(q)
        return qs

    # ─── 主生成入口 ─────────────────────────────────────
    def generate_all(self, questions_per_topic: int = 100) -> list[Question]:
        all_qs = []
        generators = [
            (self._gen_vocab_en2cn, questions_per_topic * 3),
            (self._gen_vocab_cn2en, questions_per_topic * 2),
            (self._gen_spelling, questions_per_topic),
            (self._gen_multiple_choice, questions_per_topic),
            (self._gen_grammar, questions_per_topic * 2),
            (self._gen_sentence_reorder, questions_per_topic),
            (self._gen_translation, questions_per_topic),
            (self._gen_reading, questions_per_topic // 2),
            (self._gen_dialogue, questions_per_topic),
        ]
        for gen, count in generators:
            try:
                qs = gen(count)
                all_qs.extend(qs)
            except Exception as e:
                print(f"  ⚠ {gen.__name__} 出错: {e}")

        return all_qs

    def generate_and_save(self, questions_per_topic: int = 100,
                          filename: str = "english_questions.json"):
        os.makedirs(DATA_DIR, exist_ok=True)
        questions = self.generate_all(questions_per_topic)
        output = [q.to_task_dict() for q in questions]

        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 英语题库生成完成！")
        print(f"   总题数: {len(questions)}")
        print(f"   保存至: {filepath}")

        by_topic = {}
        for q in questions:
            by_topic[q.topic] = by_topic.get(q.topic, 0) + 1
        for t, c in sorted(by_topic.items()):
            print(f"   {t}: {c} 题")
        return filepath


if __name__ == "__main__":
    gen = EnglishGenerator()
    gen.generate_and_save(questions_per_topic=120)
