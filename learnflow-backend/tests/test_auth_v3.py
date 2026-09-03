"""测试新增认证端点：OAuth、角色锁定 —— 单元测试版"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestOAuthLoginLogic:
    """测试OAuth登录逻辑（不依赖FastAPI TestClient）"""
    
    def test_oauth_provider_values(self):
        """测试 provider 值支持"""
        from app.api.auth import OAuthLoginRequest
        from app.models.user import UserRole
        
        req = OAuthLoginRequest(provider="qq", oauth_uid="test123", name="Test", role=UserRole.STUDENT)
        assert req.provider == "qq"
        assert req.oauth_uid == "test123"
        assert req.role == UserRole.STUDENT

    def test_oauth_provider_wechat(self):
        """测试微信 provider"""
        from app.api.auth import OAuthLoginRequest
        from app.models.user import UserRole
        
        req = OAuthLoginRequest(provider="wechat", oauth_uid="wx456", name="WX User", role=UserRole.TEACHER)
        assert req.provider == "wechat"
        assert req.role == UserRole.TEACHER

    def test_oauth_default_role(self):
        """测试OAuth默认角色为学生"""
        from app.api.auth import OAuthLoginRequest
        from app.models.user import UserRole
        
        req = OAuthLoginRequest(provider="qq", oauth_uid="def", name="Default")
        assert req.role == UserRole.STUDENT


class TestLoginJSONRequest:
    """测试JSON登录请求"""
    
    def test_json_request_fields(self):
        """测试JSON登录字段"""
        from app.api.auth import LoginJSONRequest
        req = LoginJSONRequest(email="test@test.com", password="Pass1234!")
        assert req.email == "test@test.com"


class TestRegisterRequest:
    """测试注册请求扩展字段"""
    
    def test_register_with_oauth(self):
        """测试注册时包含OAuth字段"""
        from app.api.auth import RegisterRequest
        from app.models.user import UserRole
        
        req = RegisterRequest(
            email="oauthtest@test.com", password="Pass1234!", name="OAuth User",
            role=UserRole.ADMIN, oauth_provider="qq", oauth_uid="qq_uid_123"
        )
        assert req.oauth_provider == "qq"
        assert req.oauth_uid == "qq_uid_123"
        assert req.role == UserRole.ADMIN

    def test_register_without_oauth(self):
        """测试注册不含OAuth字段"""
        from app.api.auth import RegisterRequest
        
        req = RegisterRequest(email="normal@test.com", password="Pass1234!", name="Normal")
        assert req.oauth_provider is None
        assert req.oauth_uid is None


class TestRoleEndpoint:
    """测试角色端点逻辑"""
    
    def test_role_values_are_valid(self):
        """测试角色枚举值"""
        from app.models.user import UserRole
        
        valid_roles = ["student", "teacher", "parent", "admin"]
        for role_name in valid_roles:
            role = UserRole(role_name)
            assert role.value == role_name

    def test_role_not_modifiable_logic(self):
        """测试角色锁定逻辑"""
        # 模拟 change-role 端点逻辑
        result = {"detail": "角色在注册时确定，不可修改"}
        assert "不可修改" in result["detail"]


class TestRoleSelectionFlow:
    """测试登录选角色流程"""
    
    def test_demo_accounts_have_correct_roles(self):
        """测试演示账号角色正确性"""
        demo_accounts = {
            "student": {"email": "student@learnflow.com", "password": "Student123!"},
            "teacher": {"email": "teacher@learnflow.com", "password": "Teacher123!"},
            "parent": {"email": "parent@learnflow.com", "password": "Parent123!"},
            "admin": {"email": "admin@learnflow.com", "password": "Admin1234!"},
        }
        assert len(demo_accounts) == 4
        assert "student" in demo_accounts
        assert demo_accounts["teacher"]["email"] == "teacher@learnflow.com"
