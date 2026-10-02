"""认证 API：登录、注册、令牌刷新"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token, decode_token
)
from app.models.user import User, UserRole
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: UserRole = UserRole.STUDENT
    grade: str | None = None
    phone: str | None = None
    oauth_provider: str | None = None  # qq / wechat
    oauth_uid: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码长度至少为8位")
        if not any(c.isupper() for c in v):
            raise ValueError("密码需包含至少一个大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码需包含至少一个小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码需包含至少一个数字")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从JWT令牌获取当前用户"""
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")

    return user


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户"""
    import traceback, logging
    logger = logging.getLogger(__name__)
    try:
        # 检查邮箱是否已存在
        result = await db.execute(select(User).where(User.email == req.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该邮箱已注册")

        user = User(
            email=req.email,
            hashed_password=hash_password(req.password),
            name=req.name,
            role=req.role,
            grade=req.grade,
            phone=req.phone,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

        # 统一 onboarding：默认宠物、技能画像、consents、演示家长绑定
        await OnboardingService.onboard(user, db)

        access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={
                "id": str(user.id),
                "name": user.name,
                "role": user.role.value,
                "grade": user.grade,
                "consents": user.consents,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """用户登录（form-urlencoded / OAuth2 标准）"""
    return await _do_login(form_data.username, form_data.password, db)


class LoginJSONRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login/json", response_model=TokenResponse)
async def login_json(req: LoginJSONRequest, db: AsyncSession = Depends(get_db)):
    """用户登录（JSON格式，前端专用）"""
    return await _do_login(req.email, req.password, db)


class OAuthLoginRequest(BaseModel):
    provider: str  # qq / wechat
    oauth_uid: str
    name: str
    avatar: str | None = None
    role: str = "student"  # 用字符串，内部转枚举


@router.post("/login/oauth", response_model=TokenResponse)
async def login_oauth(req: OAuthLoginRequest, db: AsyncSession = Depends(get_db)):
    """OAuth登录（QQ/微信）- 自动创建账号"""
    # 用 oauth_uid + provider 查用户，不存在则自动注册
    lookup_email = f"{req.oauth_uid}@{req.provider}.oauth"
    result = await db.execute(select(User).where(User.email == lookup_email))
    user = result.scalar_one_or_none()
    
    if not user:
        # 自动注册 OAuth 用户
        user = User(
            email=lookup_email,
            hashed_password=hash_password(f"oauth_{req.provider}_{req.oauth_uid}"),
            name=req.name,
            role=UserRole(req.role) if req.role in ("student","teacher","parent","admin") else UserRole.STUDENT,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

        # 统一 onboarding
        await OnboardingService.onboard(user, db)
    
    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"id": str(user.id), "name": user.name, "role": user.role.value, "grade": user.grade, "consents": user.consents},
    )


async def _do_login(email: str, password: str, db: AsyncSession):
    """内部登录逻辑"""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已被禁用")

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": str(user.id),
            "name": user.name,
            "role": user.role.value,
            "grade": user.grade,
        },
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """刷新令牌"""
    payload = decode_token(req.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user={"id": str(user.id), "name": user.name, "role": user.role.value},
    )


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role.value,
        "grade": user.grade,
        "class_id": user.class_id,
        "consents": user.consents,
    }


@router.get("/role")
async def get_role(user: User = Depends(get_current_user)):
    """快速获取当前用户角色"""
    return {"role": user.role.value}


@router.post("/change-role")
async def change_role():
    """角色锁定——不支持修改"""
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="角色在注册时确定，不可修改")
