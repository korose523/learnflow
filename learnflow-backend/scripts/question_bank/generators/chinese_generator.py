"""小学语文题库生成器 — 覆盖1-6年级全部核心知识点
包含：拼音、汉字、词语、成语、古诗、阅读理解、写作等
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
    question_type: str = "chinese"
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
            "source": "chinese_generator",
            "content_type": "text",
            "is_approved": True,
            "grade": self.grade,
            "question_type": self.question_type,
        }

# ─── 语文知识库 ─────────────────────────────────────────

# 各年级核心汉字
GRADE_CHARS = {
    1: ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
        "人", "口", "手", "足", "目", "耳", "日", "月", "水", "火",
        "山", "石", "田", "土", "木", "禾", "米", "竹", "花", "鸟",
        "大", "小", "多", "少", "上", "下", "左", "右", "前", "后",
        "天", "地", "风", "云", "雨", "雪", "春", "夏", "秋", "冬",
        "爸", "妈", "哥", "姐", "弟", "妹", "老", "师", "同", "学"],
    2: ["跑", "跳", "唱", "说", "写", "读", "看", "听", "想", "做",
        "红", "黄", "蓝", "绿", "白", "黑", "美丽", "高兴", "快乐", "难过",
        "学校", "教室", "操场", "公园", "超市", "医院", "动物", "植物", "水果", "蔬菜"],
    3: ["观察", "实验", "研究", "发现", "创造", "梦想", "勇敢", "坚强", "努力", "成功",
        "祖国", "人民", "家乡", "风景", "古迹", "传说", "故事", "寓言", "童话", "诗歌"],
    4: ["繁茂", "葱茏", "挺拔", "壮观", "雄伟", "辽阔", "清澈", "宁静", "热闹", "繁华",
        "勤学", "好问", "专心", "刻苦", "钻研", "思考", "探索", "创新", "实践", "总结"],
    5: ["借鉴", "融合", "传承", "弘扬", "创新", "突破", "超越", "巅峰", "卓越", "辉煌",
        "环境", "生态", "保护", "资源", "可持续发展", "和谐", "文明", "进步", "发展", "未来"],
    6: ["底蕴", "内涵", "精髓", "灵魂", "境界", "格局", "视野", "胸怀", "气度", "风范",
        "历史", "文化", "传统", "精神", "价值", "意义", "使命", "责任", "担当", "奉献"],
}

# 成语库（带释义）
CHENGYU = [
    ("一心一意", "形容心思专一，没有杂念。"),
    ("三心二意", "形容心思不专，犹豫不决。"),
    ("画蛇添足", "比喻多此一举，反而坏事。"),
    ("守株待兔", "比喻不主动努力，存在侥幸心理。"),
    ("亡羊补牢", "比喻出了问题后想办法补救，以免再受损失。"),
    ("刻舟求剑", "比喻办事刻板，不知变通。"),
    ("掩耳盗铃", "比喻自己欺骗自己。"),
    ("狐假虎威", "比喻依仗别人的势力欺压人。"),
    ("叶公好龙", "比喻表面上爱好某事物，实际上并不真正喜欢。"),
    ("井底之蛙", "比喻见识短浅的人。"),
    ("画龙点睛", "比喻在关键处加上精辟语句，使内容更加生动有力。"),
    ("杯弓蛇影", "比喻疑神疑鬼，妄自恐慌。"),
    ("买椟还珠", "比喻没有眼光，取舍不当。"),
    ("邯郸学步", "比喻模仿别人不成，反而丢失了原有的技能。"),
    ("对牛弹琴", "比喻说话不看对象，白费口舌。"),
    ("鹤立鸡群", "比喻一个人的才能或仪表在众人中显得很突出。"),
    ("百发百中", "形容射击或做事极有把握。"),
    ("胸有成竹", "比喻做事之前已经有通盘考虑。"),
    ("一鸣惊人", "比喻平时没有表现，一下子做出惊人的成绩。"),
    ("纸上谈兵", "比喻空谈理论，不能解决实际问题。"),
    ("悬梁刺股", "形容刻苦学习。"),
    ("凿壁偷光", "形容刻苦学习。"),
    ("闻鸡起舞", "比喻有志报国者及时奋发。"),
    ("手不释卷", "形容勤奋读书。"),
    ("博览群书", "形容读了很多书，学识渊博。"),
    ("持之以恒", "长久坚持下去。"),
    ("锲而不舍", "比喻做事有恒心，坚持不懈。"),
    ("精益求精", "比喻已经很好了，还要求更好。"),
    ("不耻下问", "比喻谦虚好学。"),
    ("学以致用", "学了知识后在实践中运用。"),
]

# 古诗词库
POEMS = [
    ("静夜思", "李白", "床前明月光，疑是地上霜。举头望明月，低头思故乡。", "表达了诗人对故乡的深深思念。"),
    ("春晓", "孟浩然", "春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少。", "描写春天早晨的景色，表达了惜春之情。"),
    ("登鹳雀楼", "王之涣", "白日依山尽，黄河入海流。欲穷千里目，更上一层楼。", "表达了站得高望得远的哲理。"),
    ("悯农", "李绅", "锄禾日当午，汗滴禾下土。谁知盘中餐，粒粒皆辛苦。", "表达了对农民辛勤劳动的同情，提醒人们珍惜粮食。"),
    ("咏鹅", "骆宾王", "鹅鹅鹅，曲项向天歌。白毛浮绿水，红掌拨清波。", "生动描写了鹅在水中游动的优美姿态。"),
    ("望庐山瀑布", "李白", "日照香炉生紫烟，遥看瀑布挂前川。飞流直下三千尺，疑是银河落九天。", "描绘了庐山瀑布的壮观景象。"),
    ("绝句", "杜甫", "两个黄鹂鸣翠柳，一行白鹭上青天。窗含西岭千秋雪，门泊东吴万里船。", "描绘了春天的美好景色。"),
    ("江雪", "柳宗元", "千山鸟飞绝，万径人踪灭。孤舟蓑笠翁，独钓寒江雪。", "描绘了雪中江景和孤独的渔翁。"),
    ("游子吟", "孟郊", "慈母手中线，游子身上衣。临行密密缝，意恐迟迟归。谁言寸草心，报得三春晖。", "歌颂了母爱的伟大。"),
    ("元日", "王安石", "爆竹声中一岁除，春风送暖入屠苏。千门万户曈曈日，总把新桃换旧符。", "描写了春节的喜庆景象。"),
    ("小池", "杨万里", "泉眼无声惜细流，树阴照水爱晴柔。小荷才露尖尖角，早有蜻蜓立上头。", "描绘了初夏小池的生动画面。"),
    ("村居", "高鼎", "草长莺飞二月天，拂堤杨柳醉春烟。儿童散学归来早，忙趁东风放纸鸢。", "描写了春天乡村的欢乐景象。"),
    ("所见", "袁枚", "牧童骑黄牛，歌声振林樾。意欲捕鸣蝉，忽然闭口立。", "刻画了牧童天真可爱的形象。"),
    ("山行", "杜牧", "远上寒山石径斜，白云生处有人家。停车坐爱枫林晚，霜叶红于二月花。", "描写了深秋山中的美丽景色。"),
    ("赠汪伦", "李白", "李白乘舟将欲行，忽闻岸上踏歌声。桃花潭水深千尺，不及汪伦送我情。", "表达了朋友间的深厚情谊。"),
    ("望天门山", "李白", "天门中断楚江开，碧水东流至此回。两岸青山相对出，孤帆一片日边来。", "描绘了天门山的壮丽景色。"),
    ("饮湖上初晴后雨", "苏轼", "水光潋滟晴方好，山色空蒙雨亦奇。欲把西湖比西子，淡妆浓抹总相宜。", "写出了西湖晴雨皆美的景色。"),
    ("题西林壁", "苏轼", "横看成岭侧成峰，远近高低各不同。不识庐山真面目，只缘身在此山中。", "表达了要全面认识事物的哲理。"),
    ("示儿", "陆游", "死去元知万事空，但悲不见九州同。王师北定中原日，家祭无忘告乃翁。", "表达了诗人至死不渝的爱国情怀。"),
    ("出塞", "王昌龄", "秦时明月汉时关，万里长征人未还。但使龙城飞将在，不教胡马度阴山。", "表达了边塞将士的壮志豪情。"),
]

# 修辞手法库
RHETORIC_EXAMPLES = [
    ("比喻", "她的脸像红苹果一样。", "把脸比作红苹果，更生动形象。"),
    ("拟人", "小鸟在枝头欢快地唱歌。", "把小鸟当成人来写，赋予人的动作。"),
    ("排比", "时间就是生命，时间就是速度，时间就是力量。", "三个相同结构的句子并列，增强气势。"),
    ("夸张", "他的嗓门大得整个操场都能听到。", "故意把声音说得大，突出特点。"),
    ("反问", "这难道不是一个伟大的成就吗？", "用疑问表达肯定的意思，增强语气。"),
    ("设问", "什么是幸福？幸福就是家人的陪伴。", "自问自答，引起思考。"),
    ("对偶", "两个黄鹂鸣翠柳，一行白鹭上青天。", "两句结构相同，意义相关。"),
    ("借代", "一群红领巾走过来了。", "用\"红领巾\"代指少先队员。"),
]

# 阅读理解短文
READING_PASSAGES = {
    3: [
        {
            "title": "小草",
            "passage": "春天来了，小草从泥土里钻了出来。嫩嫩的，绿绿的，像给大地铺上了一层绿色的地毯。风一吹，小草就跳起了舞。太阳出来了，小草上的露珠闪闪发光，像一颗颗小珍珠。",
            "questions": [
                ("小草是什么颜色的？", "绿色", "从\"绿绿的\"可以知道小草是绿色的。"),
                ("露珠像什么？", "小珍珠", "文章最后一句说\"像一颗颗小珍珠\"。"),
                ("这篇文章主要写的是什么季节？", "春天", "文章开头说\"春天来了\"。"),
            ]
        },
        {
            "title": "我的文具盒",
            "passage": "我有一个漂亮的文具盒，是妈妈送给我的生日礼物。文具盒是蓝色的，上面画着一只可爱的小熊。打开文具盒，里面有铅笔、橡皮、尺子。它们都是我的好朋友，每天陪我一起学习。",
            "questions": [
                ("文具盒是谁送的？", "妈妈", "第二句说\"是妈妈送给我的生日礼物\"。"),
                ("文具盒是什么颜色的？", "蓝色", "第三句说\"文具盒是蓝色的\"。"),
                ("文具盒里有什么？", "铅笔、橡皮、尺子", "第四句列举了文具盒里的物品。"),
            ]
        },
    ],
    5: [
        {
            "title": "坚持的力量",
            "passage": "爱迪生发明电灯时，为了找到合适的灯丝材料，他试验了一千六百多种材料，经历了无数次失败。有人问他：\"你失败了这么多次，不觉得沮丧吗？\"爱迪生回答：\"我没有失败，我只是发现了一千六百多种不适合做灯丝的材料。\"正是这种坚持不懈的精神，让他最终取得了成功。",
            "questions": [
                ("爱迪生为了找到合适的灯丝，试验了多少种材料？", "一千六百多种", "文章明确提到\"试验了一千六百多种材料\"。"),
                ("爱迪生认为自己失败了吗？为什么？", "没有，他认为自己只是发现了不适合的材料", "爱迪生说\"我没有失败，我只是发现了一千六百多种不适合做灯丝的材料\"。"),
                ("这个故事告诉我们什么道理？", "坚持不懈才能成功", "文章最后一句总结了这个道理。"),
                ("用文中的一个词概括爱迪生的精神：", "坚持不懈", "文章最后用了\"坚持不懈\"这个词。"),
            ]
        },
    ],
}


class ChineseGenerator:
    """小学语文题库生成器"""

    # ─── 拼音 ─────────────────────────────────────────
    def _gen_pinyin(self, count: int) -> list[Question]:
        qs = []
        pin_yin_pairs = [
            ("妈", "mā"), ("爸", "bà"), ("花", "huā"), ("火", "huǒ"),
            ("水", "shuǐ"), ("天", "tiān"), ("山", "shān"), ("人", "rén"),
            ("月", "yuè"), ("学", "xué"), ("小", "xiǎo"), ("大", "dà"),
            ("多", "duō"), ("少", "shǎo"), ("上", "shàng"), ("下", "xià"),
            ("春", "chūn"), ("秋", "qiū"), ("冬", "dōng"), ("风", "fēng"),
            ("云", "yún"), ("雨", "yǔ"), ("雪", "xuě"), ("鸟", "niǎo"),
            ("鱼", "yú"), ("草", "cǎo"), ("树", "shù"), ("河", "hé"),
            ("海", "hǎi"), ("马", "mǎ"), ("牛", "niú"), ("羊", "yáng"),
        ]
        for _ in range(count):
            char, pinyin = random.choice(pin_yin_pairs)
            if random.random() < 0.5:
                # 看字写拼音
                q = Question(
                    topic="拼音", difficulty=1,
                    content=f"看字写拼音：\n「{char}」的拼音是什么？",
                    correct_answer=pinyin,
                    explanation=f"{char}的拼音是{pinyin}。",
                    grade=1, time_estimate=30,
                    hint_levels=[f"想一想这个字怎么读", f"声母和韵母分别是？"],
                )
            else:
                q = Question(
                    topic="拼音", difficulty=2,
                    content=f"看拼音写汉字：\n「{pinyin}」对应的汉字是什么？",
                    correct_answer=char,
                    explanation=f"{pinyin}的汉字是{char}。",
                    grade=1, time_estimate=30,
                    hint_levels=[f"这个拼音读{char}", "想想学过的常用字"],
                )
            qs.append(q)
        return qs

    # ─── 汉字笔顺/笔画 ─────────────────────────────────
    def _gen_strokes(self, count: int) -> list[Question]:
        qs = []
        stroke_count = {
            "一": 1, "二": 2, "三": 3, "人": 2, "大": 3,
            "天": 4, "日": 4, "月": 4, "水": 4, "火": 4,
            "木": 4, "目": 5, "田": 5, "白": 5, "石": 5,
            "禾": 5, "米": 6, "羊": 6, "耳": 6, "虫": 6,
            "花": 7, "我": 7, "学": 8, "鱼": 8, "春": 9,
        }
        for _ in range(count):
            char, strokes = random.choice(list(stroke_count.items()))
            q = Question(
                topic="汉字笔画",
                difficulty=random.randint(1, 3),
                content=f"「{char}」这个字一共有几画？",
                correct_answer=f"{strokes}画",
                explanation=f"{char}字的笔画数为{strokes}画。",
                grade=random.randint(1, 2),
                time_estimate=45,
                hint_levels=[f"数一数{char}字的笔画", f"先写第一笔"],
            )
            qs.append(q)
        return qs

    # ─── 组词 ─────────────────────────────────────────
    def _gen_word_formation(self, count: int) -> list[Question]:
        qs = []
        char_words = {
            "大": ["大人", "大树", "大小", "大学", "伟大", "巨大"],
            "小": ["小鸟", "小心", "小学", "小草", "大小", "渺小"],
            "天": ["天空", "天气", "春天", "蓝天", "天真", "天地"],
            "学": ["学习", "学校", "同学", "上学", "学问", "科学"],
            "花": ["花朵", "花园", "开花", "鲜花", "花费", "花样"],
            "水": ["水果", "水杯", "河水", "开水", "水平", "水滴"],
            "心": ["心情", "爱心", "开心", "中心", "心情", "心意"],
            "生": ["生活", "生命", "学生", "生日", "花生", "生意"],
            "光": ["阳光", "月光", "光明", "灯光", "光滑", "光荣"],
            "风": ["风筝", "吹风", "台风", "风景", "风光", "风气"],
        }
        for _ in range(count):
            char, words = random.choice(list(char_words.items()))
            correct = random.choice(words)
            wrong_opts = random.sample([w for w in words if w != correct], min(3, len(words)-1))
            # Make it a fill-in or choice
            if random.random() < 0.5:
                q = Question(
                    topic="组词",
                    difficulty=random.randint(2, 3),
                    content=f"用「{char}」字组一个词：\n{char} _ _（两个字的词）",
                    correct_answer=correct.replace(char, correct),
                    explanation=f"用{char}可以组成词语「{correct}」。",
                    grade=random.randint(1, 3),
                    time_estimate=60,
                    hint_levels=[f"{char}可以和另一个字组合", f"比如{char}___"],
                )
            else:
                q = Question(
                    topic="组词",
                    difficulty=2,
                    content=f"下面哪个词写得对？\nA. {char}{correct[1] if len(correct)==2 else ''}\nB. {char}{wrong_opts[0][1] if len(wrong_opts[0])==2 else ''}",
                    correct_answer="A",
                    explanation=f"正确答案是A，「{correct}」是正确的词语。",
                    grade=2, time_estimate=45,
                )
            qs.append(q)
        return qs

    # ─── 近义词/反义词 ────────────────────────────────
    def _gen_synonym_antonym(self, count: int) -> list[Question]:
        qs = []
        pairs_syn = [
            ("美丽", "漂亮"), ("高兴", "快乐"), ("难过", "悲伤"),
            ("巨大", "庞大"), ("迅速", "快速"), ("安静", "宁静"),
            ("坚强", "刚强"), ("聪明", "智慧"), ("著名", "闻名"),
            ("茂盛", "繁茂"), ("特别", "特殊"), ("立刻", "马上"),
        ]
        pairs_ant = [
            ("大", "小"), ("多", "少"), ("高", "矮"), ("胖", "瘦"),
            ("快乐", "悲伤"), ("勇敢", "胆小"), ("勤劳", "懒惰"),
            ("节约", "浪费"), ("成功", "失败"), ("开始", "结束"),
            ("光明", "黑暗"), ("善良", "邪恶"), ("前进", "后退"),
        ]
        for _ in range(count):
            is_syn = random.random() < 0.5
            if is_syn:
                word, syn = random.choice(pairs_syn)
                q = Question(
                    topic="近义词", difficulty=random.randint(3, 5),
                    content=f"写出「{word}」的近义词。",
                    correct_answer=syn,
                    explanation=f"「{word}」和「{syn}」意思相近，是近义词。",
                    grade=random.randint(3, 5), time_estimate=60,
                    hint_levels=[f"意思和{word}差不多的词", f"两个字，形容很好的样子"],
                )
            else:
                word, ant = random.choice(pairs_ant)
                q = Question(
                    topic="反义词", difficulty=random.randint(2, 4),
                    content=f"写出「{word}」的反义词。",
                    correct_answer=ant,
                    explanation=f"「{word}」和「{ant}」意思相反，是反义词。",
                    grade=random.randint(2, 4), time_estimate=60,
                    hint_levels=[f"和{word}相反的词"],
                )
            qs.append(q)
        return qs

    # ─── 成语 ─────────────────────────────────────────
    def _gen_chengyu(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            chengyu, meaning = random.choice(CHENGYU)
            q_type = random.randint(1, 3)
            if q_type == 1:
                # 成语填空
                chars = list(chengyu)
                blank_idx = random.randint(1, 3)
                blank_char = chars[blank_idx]
                masked = chars.copy()
                masked[blank_idx] = "（ ）"
                q = Question(
                    topic="成语填空", difficulty=random.randint(4, 6),
                    content=f"把成语补充完整：\n{''.join(masked)}",
                    correct_answer=blank_char,
                    explanation=f"完整成语是「{chengyu}」，意思是：{meaning}",
                    grade=random.randint(3, 5), time_estimate=60,
                    hint_levels=[f"这个成语的意思是{meaning}", f"成语是{chengyu[:blank_idx]}?"],
                )
            elif q_type == 2:
                wrong_chengyu = random.choice([c for c, _ in CHENGYU if c != chengyu])
                q = Question(
                    topic="成语释义", difficulty=random.randint(4, 6),
                    content=f"「{chengyu}」这个成语的意思是：\nA. {meaning}\nB. {dict(CHENGYU).get(wrong_chengyu, '其他意思')}",
                    correct_answer="A",
                    explanation=f"「{chengyu}」的意思是{meaning}。",
                    grade=random.randint(4, 6), time_estimate=90,
                )
            else:
                q = Question(
                    topic="成语运用", difficulty=random.randint(5, 7),
                    content=f"请你用「{chengyu}」造一个句子。",
                    correct_answer=f"（示例）{random.choice(['他', '小明', '我'])}做事情{chengyu}，从不分心。" if "心" in chengyu else f"{random.choice(['他', '小明'])}的举动真是{chengyu}。",
                    explanation=f"「{chengyu}」意思是{meaning}，可以在相关语境中使用。",
                    grade=random.randint(4, 6), time_estimate=120,
                    hint_levels=[f"这个成语的意思是：{meaning}", "想想在什么场景可以用"],
                )
            qs.append(q)
        return qs

    # ─── 古诗词 ───────────────────────────────────────
    def _gen_poetry(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            title, author, content, meaning = random.choice(POEMS)
            lines = [l.strip("，。") for l in content.replace("，", "|").replace("。", "|").split("|") if l.strip()]
            q_type = random.randint(1, 3)

            if q_type == 1:
                # 补全诗句
                line_idx = random.randint(0, len(lines)-1)
                line = lines[line_idx]
                if len(line) >= 5:
                    blank_pos = random.randint(0, len(line)-3)
                    masked = line[:blank_pos] + "____" + line[blank_pos+2:]
                else:
                    masked = "____" + line[2:]
                q = Question(
                    topic="古诗词默写", difficulty=random.randint(3, 6),
                    content=f"补全诗句（{title}·{author}）：\n「{masked}」",
                    correct_answer=line,
                    explanation=f"原诗是{author}的《{title}》：{content}。意思是：{meaning}",
                    grade=random.randint(3, 6), time_estimate=90,
                    hint_levels=[f"这是{author}的《{title}》", f"全诗是：{content}"],
                )
            elif q_type == 2:
                q = Question(
                    topic="古诗理解", difficulty=random.randint(4, 7),
                    content=f"「{content[:20]}...」出自哪首诗？作者是谁？表达了什么感情？",
                    correct_answer=f"《{title}》·{author}，{meaning}",
                    explanation=f"这是{author}的《{title}》，{meaning}。",
                    grade=random.randint(4, 6), time_estimate=120,
                    hint_levels=[f"这是{author}的诗", f"诗名可能是《{title}》"],
                )
            else:
                q = Question(
                    topic="古诗作者", difficulty=random.randint(2, 4),
                    content=f"《{title}》的作者是？\nA. {author}\nB. {random.choice([a for _, a, _, _ in POEMS if a != author])}",
                    correct_answer="A",
                    explanation=f"《{title}》的作者是{author}。",
                    grade=random.randint(2, 5), time_estimate=45,
                )
            qs.append(q)
        return qs

    # ─── 修改病句 ─────────────────────────────────────
    def _gen_sentence_correction(self, count: int) -> list[Question]:
        qs = []
        errors = [
            ("他虽然很努力，但是取得了好成绩。", "他因为很努力，所以取得了好成绩。", "关联词语使用不当", 5),
            ("我断定他大概会来。", "我断定他会来。", "前后矛盾", 5),
            ("王老师被评为\u201c优秀教师\u201d的光荣称号。", "王老师获得\u201c优秀教师\u201d的光荣称号。", "搭配不当", 4),
            ("经过老师的教育，使我认识到了错误。", "老师的教育，使我认识到了错误。", "主语残缺", 5),
            ("我们要养成认真学习的好方法。", "我们要养成认真学习的好习惯。", "搭配不当", 5),
            ("同学们都到齐了，只有小明没来。", "除了小明，同学们都到齐了。", "前后矛盾", 4),
            ("公园里开满了五颜六色的红花。", "公园里开满了五颜六色的花。", "语义重复", 4),
            ("这本书对我很感兴趣。", "我对这本书很感兴趣。", "语序不当", 5),
        ]
        for _ in range(count):
            wrong, correct, reason, diff = random.choice(errors)
            q = Question(
                topic="修改病句", difficulty=diff,
                content=f"修改下面的病句：\n「{wrong}」\n请写出修改后的正确句子。",
                correct_answer=correct,
                explanation=f"错误类型：{reason}。\n修改为：{correct}",
                grade=random.randint(4, 6), time_estimate=120,
                hint_levels=[f"这个句子的问题是{reason}", f"注意{'关联词' if '关联' in reason else '主谓搭配'}"],
            )
            qs.append(q)
        return qs

    # ─── 修辞手法 ─────────────────────────────────────
    def _gen_rhetoric(self, count: int) -> list[Question]:
        qs = []
        for _ in range(count):
            name, example, desc = random.choice(RHETORIC_EXAMPLES)
            if random.random() < 0.5:
                q = Question(
                    topic="修辞手法", difficulty=random.randint(4, 6),
                    content=f"下面的句子使用了什么修辞手法？\n「{example}」",
                    correct_answer=name,
                    explanation=f"这个句子使用了{name}的修辞手法。{desc}",
                    grade=random.randint(4, 6), time_estimate=60,
                    hint_levels=["注意句子中的表达方式", f"有没有把A比作B？有没有把事物当成人写？"],
                )
            else:
                q = Question(
                    topic="修辞手法", difficulty=5,
                    content=f"请用「{name}」的修辞手法写一个句子。",
                    correct_answer=f"（示例）{example}",
                    explanation=f"{name}的特点是：{desc}\n示例：{example}",
                    grade=random.randint(4, 6), time_estimate=120,
                    hint_levels=[f"{name}的要点：{desc}"],
                )
            qs.append(q)
        return qs

    # ─── 阅读 ─────────────────────────────────────────
    def _gen_reading(self, count: int) -> list[Question]:
        qs = []
        all_passages = []
        for grade_level, passages in READING_PASSAGES.items():
            for p in passages:
                all_passages.append((grade_level, p))

        if not all_passages:
            return qs

        for _ in range(min(count, len(all_passages) * 3)):
            grade_level, passage = random.choice(all_passages)
            q_data = random.choice(passage["questions"])
            question_text, answer, explanation = q_data

            q = Question(
                topic="阅读理解",
                difficulty=random.randint(3, 7),
                content=f"阅读短文回答问题：\n\n【{passage['title']}】\n{passage['passage']}\n\n问题：{question_text}",
                correct_answer=answer,
                explanation=explanation,
                grade=grade_level,
                time_estimate=180,
                hint_levels=["仔细阅读短文，答案在文中可以找到", "注意关键句子"],
            )
            qs.append(q)
        return qs

    # ─── 常识 ─────────────────────────────────────────
    def _gen_general_knowledge(self, count: int) -> list[Question]:
        qs = []
        knowledge = [
            ("中国\u201c四大发明\u201d指什么？", "造纸术、印刷术、火药、指南针", "中国古代四大发明对世界文明产生了深远影响。"),
            ("中国的全称是什么？", "中华人民共和国", "我国的全称。"),
            ("一年有几个季节？分别是什么？", "四个季节：春、夏、秋、冬", "四季是由于地球公转造成的。"),
            ("中国最长的河流是什么？", "长江", "长江全长约6300公里，是中国第一大河。"),
            ("说出三个中国传统节日：", "春节、中秋节、端午节等", "中国传统节日承载着丰富的文化内涵。"),
            ("三字经的开头是？", "人之初，性本善", "这是中国传统启蒙读物。"),
            ("端午节是为了纪念谁？", "屈原", "屈原是战国时期楚国的爱国诗人。"),
        ]
        for _ in range(count):
            question, answer, explanation = random.choice(knowledge)
            q = Question(
                topic="语文常识",
                difficulty=random.randint(3, 5),
                content=question,
                correct_answer=answer,
                explanation=explanation,
                grade=random.randint(3, 6),
                time_estimate=90,
            )
            qs.append(q)
        return qs

    # ─── 主生成入口 ─────────────────────────────────────
    def generate_all(self, questions_per_topic: int = 80) -> list[Question]:
        """生成全部语文题"""
        all_qs = []
        generators = [
            (self._gen_pinyin, questions_per_topic * 2),
            (self._gen_strokes, questions_per_topic),
            (self._gen_word_formation, questions_per_topic * 2),
            (self._gen_synonym_antonym, questions_per_topic),
            (self._gen_chengyu, questions_per_topic),
            (self._gen_poetry, questions_per_topic),
            (self._gen_sentence_correction, questions_per_topic // 2),
            (self._gen_rhetoric, questions_per_topic // 2),
            (self._gen_reading, questions_per_topic // 3),
            (self._gen_general_knowledge, questions_per_topic // 3),
        ]
        for gen, count in generators:
            try:
                qs = gen(count)
                all_qs.extend(qs)
            except Exception as e:
                print(f"  ⚠ {gen.__name__} 出错: {e}")

        return all_qs

    def generate_and_save(self, questions_per_topic: int = 80,
                          filename: str = "chinese_questions.json"):
        os.makedirs(DATA_DIR, exist_ok=True)
        questions = self.generate_all(questions_per_topic)
        output = [q.to_task_dict() for q in questions]

        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 语文题库生成完成！")
        print(f"   总题数: {len(questions)}")
        print(f"   保存至: {filepath}")

        by_topic = {}
        for q in questions:
            by_topic[q.topic] = by_topic.get(q.topic, 0) + 1
        for t, c in sorted(by_topic.items()):
            print(f"   {t}: {c} 题")
        return filepath


if __name__ == "__main__":
    gen = ChineseGenerator()
    gen.generate_and_save(questions_per_topic=100)
