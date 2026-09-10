"""应用配置管理"""
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import Optional, List


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """全局配置"""

    # 应用
    APP_NAME: str = "LearnFlow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # 服务
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://learnflow-d5gapot1tc7d4debd-1256129125.tcloudbaseapp.com",
        "https://learnflow-frontend-9gawx5qy1c958c1f-1256129125.tcloudbaseapp.com",
    ]

    # 数据库
    # 本地开发默认零依赖运行；生产环境通过环境变量切换到受管 MySQL/PostgreSQL。
    DATABASE_URL: str = "sqlite+aiosqlite:///./learnflow.dev.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    # 开发环境未配置时生成临时密钥；生产环境必须显式注入稳定密钥。
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # 学习参数
    MAX_LEARNING_SESSION_MINUTES: int = 90  # 连续学习上限
    REST_REMINDER_MINUTES: int = 10         # 强制休息时间
    DDA_WINDOW_SIZE: int = 10               # DDA 评估窗口（最近N题）
    DDA_TARGET_SUCCESS_RATE: float = 0.80   # 心流通道目标成功率

    # 风险监控
    DAILY_USAGE_ALERT_HOURS: float = 3.5    # 日均使用告警阈值
    CONSECUTIVE_USAGE_ALERT_MINUTES: int = 120  # 连续使用告警
    NIGHT_HOURS_START: int = 22             # 夜间时段开始
    NIGHT_HOURS_END: int = 6                # 夜间时段结束

    # 外部服务
    S3_BUCKET: Optional[str] = None
    S3_REGION: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None

    # 演示账号种子密码（可从 .env 或环境变量加载）
    SEED_ADMIN_PASSWORD: Optional[str] = None
    SEED_TEACHER_PASSWORD: Optional[str] = None
    SEED_STUDENT_PASSWORD: Optional[str] = None
    SEED_PARENT_PASSWORD: Optional[str] = None
    DEMO_DATA_ENABLED: bool = False

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def resolve_sqlite_path(cls, v: str) -> str:
        """将相对路径的 SQLite 数据库解析为项目根目录下的绝对路径，
        避免 cwd 不同导致多个数据库文件。"""
        if not v.startswith("sqlite"):
            return v
        # 提取数据库文件路径部分（sqlite+aiosqlite:///./xxx.db）
        prefix = "sqlite+aiosqlite:///"
        if v.startswith(prefix):
            path_part = v[len(prefix):]
            # 保留绝对路径不变，只处理相对路径
            if path_part.startswith("./") or path_part.startswith("../") or not Path(path_part).is_absolute():
                abs_path = (PROJECT_ROOT / path_part).resolve()
                return f"{prefix}{abs_path}"
        return v

    @model_validator(mode="after")
    def validate_runtime_security(self) -> "Settings":
        """让开发可零配置启动，同时拒绝不安全的生产配置。"""
        environment = self.ENVIRONMENT.strip().lower()
        is_production = environment in {"production", "prod"}

        if not self.JWT_SECRET_KEY:
            if is_production:
                raise ValueError("生产环境必须设置 JWT_SECRET_KEY")
            self.JWT_SECRET_KEY = secrets.token_hex(32)

        if is_production and self.DEBUG:
            raise ValueError("生产环境不得启用 DEBUG")
        if is_production and "*" in self.ALLOWED_ORIGINS:
            raise ValueError("生产环境不得使用通配 CORS 来源")
        if is_production and self.DEMO_DATA_ENABLED:
            raise ValueError("生产环境不得自动创建演示账号")
        return self

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
