"""班级宠物园（ClassPetGarden）：积分养宠系统的班级聚合层

真实的「班级电子养宠 / 积分养宠」产品形态（金华、绍兴、长沙等多地小学实践）：

- **每个学生一只专属电子宠物**：实体是 ``PetProfile``（见 pet.py），由学生本人
  认领、用行为积分喂养、随等级解锁形态进化。
- **积分来源 = 行为表现**：作业全对 / 课堂发言 / 助人 / 拾金不昧等加积分；
  迟到 / 打闹 / 拖沓等扣积分。积分即「口粮」，喂养宠物升级、进化形态。
- **班级宠物园 = 聚合视图**：全班宠物的排行榜、班级凝聚力、每周「喂养时间」
  仪式，由老师或班干部统一操作加减分。宠物本身是**个人**的，班级层面只做
  聚合与仪式，从而把个体激励升华为集体连接（Hari C1「连接替代」）。

本模型是**班级维度**的轻量容器：只保存班级宠物园自身的设置与聚合态
（单元名称、凝聚力、每周仪式开关/时间），不重复存储每个学生的宠物数据
（那些在 ``pet_profiles`` 表里）。这样「每生一只宠物」与「班级一园」两个
尺度各归其位，符合真实产品，也避免双重事实源。

机制标识：MECHANISM_KEY = "class_pet"（在 class_pet_service.py 中）供落地扫描识别。
"""
import uuid
from datetime import datetime, UTC

from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Boolean

from app.core.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class ClassPetGarden(Base):
    """班级宠物园 —— 一园对应一个班级（class_id 唯一）

    tablename: class_pet_gardens
    """

    __tablename__ = "class_pet_gardens"

    id = Column(String(36), primary_key=True, default=_new_id)
    # 一个班级只有一个宠物园
    class_id = Column(
        String(36), ForeignKey("classes.id"), nullable=False, unique=True, index=True
    )

    name = Column(String(50), default="班级宠物园")          # 园名，老师可改
    cohesion = Column(Float, default=50.0)                  # 班级凝聚力（聚合自学生宠物 collaboration，0-100）
    weekly_ritual_enabled = Column(Boolean, default=True)   # 是否开启每周「喂养时间」仪式
    last_ritual_at = Column(DateTime, nullable=True)        # 上次仪式时间

    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "班级宠物园")
        kwargs.setdefault("cohesion", 50.0)
        kwargs.setdefault("weekly_ritual_enabled", True)
        super().__init__(**kwargs)

    @property
    def ritual_due(self) -> bool:
        """是否需要触发本周「喂养时间」：开启且距上次超过 7 天（或从未）"""
        if not self.weekly_ritual_enabled:
            return False
        if self.last_ritual_at is None:
            return True
        # 用 naive UTC 比较，避免时区 tzinfo 不一致
        now = datetime.now(UTC).replace(tzinfo=None)
        return (now - self.last_ritual_at.replace(tzinfo=None)).days >= 7

    def __repr__(self):
        return f"<ClassPetGarden {self.name} class={self.class_id} cohesion={self.cohesion:.0f}>"
