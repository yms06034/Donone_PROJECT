"""
pytest 설정 파일
테스트 실행을 위한 fixtures와 설정을 정의합니다.
"""
import pytest
from django.contrib.auth.models import User
from don_home.models import Ably_token, Cafe24


@pytest.fixture
def test_user(db):
    """테스트용 사용자 생성"""
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='test@example.com',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def authenticated_client(client, test_user):
    """인증된 클라이언트"""
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def ably_token(test_user):
    """테스트용 Ably 토큰"""
    return Ably_token.objects.create(
        user=test_user,
        ably_id='test_ably_id',
        ably_pw='test_ably_pw'
    )


@pytest.fixture
def cafe24_token(test_user):
    """테스트용 Cafe24 토큰"""
    return Cafe24.objects.create(
        user=test_user,
        cafe24_id='test_cafe24_id',
        cafe24_pw='test_cafe24_pw',
        cafe24_clientid='test_client_id',
        cafe24_client_secret='test_client_secret',
        cafe24_mallid='test_mall_id',
        cafe24_encode_csrf_token='test_csrf_token',
        cafe24_redirect_uri='http://test.redirect.uri',
        service_key='test_service_key'
    )


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    모든 테스트에서 DB 접근을 허용
    pytest-django는 기본적으로 DB 접근을 제한하므로
    이 fixture를 통해 모든 테스트에서 DB 사용 가능
    """
    pass