import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail
from unittest.mock import patch, MagicMock
import json
import pandas as pd
from datetime import datetime

from don_home.models import Ably_token, Cafe24, AblyProductInfo, AblySalesInfo


@pytest.mark.django_db
class TestAuthViews:
    """인증 관련 뷰 테스트"""
    
    def setup_method(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
    
    def test_index_anonymous(self):
        """익명 사용자 인덱스 페이지 접근"""
        response = self.client.get(reverse('app:index'))
        assert response.status_code == 200
        assert '로그인이 필요합니다.' in str(response.context['login'])
    
    def test_index_authenticated(self):
        """인증된 사용자 인덱스 페이지 접근"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('app:index'))
        assert response.status_code == 200
        assert response.context['login'] == self.user
    
    def test_signup_get(self):
        """회원가입 페이지 GET 요청"""
        response = self.client.get(reverse('app:signup'))
        assert response.status_code == 200
    
    def test_signup_post_success(self):
        """회원가입 성공"""
        data = {
            'username': 'newuser',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'fullname': 'Test User',
            'email': 'newuser@example.com'
        }
        response = self.client.post(reverse('app:signup'), data)
        assert response.status_code == 200
        assert User.objects.filter(username='newuser').exists()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == '계정 활성화 확인 이메일'
    
    def test_signup_password_mismatch(self):
        """비밀번호 불일치"""
        data = {
            'username': 'newuser',
            'password1': 'testpass123',
            'password2': 'different123',
            'fullname': 'Test User',
            'email': 'newuser@example.com'
        }
        response = self.client.post(reverse('app:signup'), data)
        assert response.status_code == 200
        assert not User.objects.filter(username='newuser').exists()
    
    def test_login_success(self):
        """로그인 성공"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(reverse('app:login'), data)
        assert response.status_code == 302
        assert response.url == reverse('app:index')
    
    def test_login_failure(self):
        """로그인 실패"""
        data = {
            'username': 'testuser',
            'password': 'wrongpass'
        }
        response = self.client.post(reverse('app:login'), data)
        assert response.status_code == 200
        assert '아이디 또는 패스워드가 일치하지 않습니다.' in response.content.decode()
    
    def test_logout(self):
        """로그아웃"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('app:logout'))
        assert response.status_code == 302
        assert response.url == reverse('app:index')
    
    def test_check_username_exists(self):
        """사용자명 중복 체크 - 존재하는 경우"""
        response = self.client.get(
            reverse('app:checkeusername'),
            {'username': 'testuser'}
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['result'] == 'success'
        assert data['data'] == 'exist'
    
    def test_check_username_not_exists(self):
        """사용자명 중복 체크 - 존재하지 않는 경우"""
        response = self.client.get(
            reverse('app:checkeusername'),
            {'username': 'nonexistent'}
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['result'] == 'success'
        assert data['data'] == 'not exist'


@pytest.mark.django_db
class TestAblyViews:
    """Ably 관련 뷰 테스트"""
    
    def setup_method(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_ably_get(self):
        """Ably 토큰 페이지 GET"""
        response = self.client.get(reverse('app:ably'))
        assert response.status_code == 200
    
    def test_ably_post_create(self):
        """Ably 토큰 생성"""
        data = {
            'ablyid': 'test_ably_id',
            'ablypw': 'test_ably_pw'
        }
        response = self.client.post(reverse('app:ably'), data)
        assert response.status_code == 200
        assert Ably_token.objects.filter(
            user=self.user,
            ably_id='test_ably_id'
        ).exists()
    
    def test_ably_post_update(self):
        """Ably 토큰 업데이트"""
        Ably_token.objects.create(
            user=self.user,
            ably_id='old_id',
            ably_pw='old_pw'
        )
        
        data = {
            'ablyid': 'new_id',
            'ablypw': 'new_pw'
        }
        response = self.client.post(reverse('app:ably'), data)
        assert response.status_code == 200
        
        token = Ably_token.objects.get(user=self.user)
        assert token.ably_id == 'new_id'
        assert token.ably_pw == 'new_pw'
    
    def test_delete_ably_data(self):
        """Ably 데이터 삭제"""
        Ably_token.objects.create(
            user=self.user,
            ably_id='test_id',
            ably_pw='test_pw'
        )
        
        response = self.client.get(reverse('app:ably_delete'))
        assert response.status_code == 302
        assert not Ably_token.objects.filter(user=self.user).exists()
    
    def test_get_ably_data_authenticated(self):
        """인증된 사용자 Ably 데이터 조회"""
        AblySalesInfo.objects.create(
            user=self.user,
            productOrderNumber='ORDER001',
            paymentDate=datetime.now(),
            orderNumber='ORD001',
            productName='Test Product',
            total=10000
        )
        
        response = self.client.get(reverse('app:getablydata'))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data) == 1
        assert data[0]['productOrderNumber'] == 'ORDER001'
    
    @patch('don_home.views.AblyDataInfo')
    def test_usertoken_post_success(self, mock_ably_data):
        """사용자 토큰으로 데이터 수집 성공"""
        mock_df = pd.DataFrame({
            'paymentDate': [datetime.now()],
            'productOrderNumber': ['ORDER001'],
            'orderNumber': ['ORD001'],
            'productName': ['Test Product'],
            'options': ['Option1'],
            'total': [10000],
            'orderName': ['Test Order'],
            'phoneNumber': ['010-1234-5678'],
            'orderStatus': ['Completed']
        })
        mock_df_pro = pd.DataFrame({
            'productNumber': ['PROD001'],
            'productName': ['Test Product'],
            'price': [10000],
            'discountPeriod': ['2023-12-31'],
            'discountPrice': [9000],
            'registrationDate': ['2023-01-01'],
            'statusDisplay': ['Active'],
            'stock': [100],
            'totalReview': [5],
            'parcel': ['CJ대한통운'],
            'returnShippingCost': [2500],
            'extraShippingCost': [0]
        })
        mock_ably_data.return_value = (mock_df, mock_df_pro)
        
        Ably_token.objects.create(
            user=self.user,
            ably_id='test_id',
            ably_pw='test_pw'
        )
        
        response = self.client.post(reverse('app:usertoken'))
        assert response.status_code == 200
        
        assert AblySalesInfo.objects.filter(user=self.user).count() == 1
        assert AblyProductInfo.objects.filter(user=self.user).count() == 1


@pytest.mark.django_db
class TestCafe24Views:
    """Cafe24 관련 뷰 테스트"""
    
    def setup_method(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_cafe24_get(self):
        """Cafe24 토큰 페이지 GET"""
        response = self.client.get(reverse('app:cafe24'))
        assert response.status_code == 200
    
    def test_cafe24_post_create(self):
        """Cafe24 토큰 생성"""
        data = {
            'cafe24id': 'test_cafe24_id',
            'cafe24pw': 'test_cafe24_pw',
            'cafe24_clientid': 'client_id',
            'cafe24_client_secret': 'client_secret',
            'cafe24_mallid': 'mall_id',
            'cafe24_encode_csrf_token': 'csrf_token',
            'cafe24_redirect_uri': 'http://redirect.uri',
            'cafe24_service_key': 'service_key'
        }
        response = self.client.post(reverse('app:cafe24'), data)
        assert response.status_code == 200
        assert Cafe24.objects.filter(user=self.user).exists()
    
    def test_delete_cafe24_data(self):
        """Cafe24 데이터 삭제"""
        Cafe24.objects.create(
            user=self.user,
            cafe24_id='test_id',
            cafe24_pw='test_pw',
            cafe24_clientid='client_id',
            cafe24_client_secret='secret',
            cafe24_mallid='mall_id'
        )
        
        response = self.client.get(reverse('app:cafe24_delete'))
        assert response.status_code == 302
        assert not Cafe24.objects.filter(user=self.user).exists()


@pytest.mark.django_db
class TestAPIViews:
    """API 뷰 테스트"""
    
    def setup_method(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    @patch('don_home.views.AblyDataInfo')
    def test_ablyproduct_api_get_success(self, mock_ably_data):
        """Ably 상품 API GET 성공"""
        mock_df = pd.DataFrame({'test': [1]})
        mock_df_pro = pd.DataFrame({
            'productNumber': ['PROD001'],
            'productName': ['Test Product'],
            'price': [10000],
            'discountPeriod': ['2023-12-31'],
            'discountPrice': [9000],
            'registrationDate': ['2023-01-01'],
            'statusDisplay': ['Active'],
            'stock': [100],
            'totalReview': [5],
            'parcel': ['CJ대한통운'],
            'returnShippingCost': [2500],
            'extraShippingCost': [0]
        })
        mock_ably_data.return_value = (mock_df, mock_df_pro)
        
        Ably_token.objects.create(
            user=self.user,
            ably_id='test_id',
            ably_pw='test_pw'
        )
        
        response = self.client.get('/api/ablyproduct/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert isinstance(data, list)
    
    def test_ablyproduct_api_no_token(self):
        """Ably 상품 API - 토큰 없음"""
        response = self.client.get('/api/ablyproduct/')
        assert response.status_code == 404
        data = json.loads(response.content)
        assert 'error' in data
    
    @patch('don_home.views.cafe24_df')
    def test_cafe24all_api_success(self, mock_cafe24_df):
        """Cafe24 전체 API 성공"""
        mock_cafe24_df.return_value = (
            pd.DataFrame({'category': [1]}),
            pd.DataFrame({'product': [1]}),
            pd.DataFrame({'order': [1]}),
            pd.DataFrame({'coupon': [1]})
        )
        
        Cafe24.objects.create(
            user=self.user,
            cafe24_id='test_id',
            cafe24_pw='test_pw',
            cafe24_clientid='client_id',
            cafe24_client_secret='secret',
            cafe24_mallid='mall_id',
            cafe24_encode_csrf_token='token',
            cafe24_redirect_uri='http://test.com'
        )
        
        response = self.client.get('/api/cafe24all/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'


@pytest.mark.django_db
class TestDashboardView:
    """대시보드 뷰 테스트"""
    
    def setup_method(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    @patch('don_home.views.detail_order_year')
    @patch('don_home.views.total_sales_year')
    @patch('don_home.views.total_order_year')
    @patch('don_home.views.Chart_pre_year')
    @patch('don_home.views.Product_total_year')
    @patch('don_home.views.Product_re_year')
    def test_dashboard_year(self, mock_re, mock_total, mock_chart, 
                           mock_order, mock_sales, mock_detail):
        """대시보드 연간 데이터"""
        mock_detail.return_value = (1, 2, 3, 4)
        mock_sales.return_value = (100, 50, 30, 20)
        mock_order.return_value = (10, 5, 3, 2)
        mock_chart.return_value = ([1,2], [10,20], [5,10], [1,2], 
                                  [3,6], [1,2], [2,4], [1,2])
        mock_total.return_value = (['a'], [1], ['b'], [2], 
                                  ['c'], [3], ['d'], [4])
        mock_re.return_value = (1, 2, 3, 4)
        
        response = self.client.get(reverse('app:dashboard'))
        assert response.status_code == 200
        assert 'total' in response.context
        assert response.context['total'] == 100
    
    @patch('don_home.views.get_dashboard_data')
    def test_dashboard_cache(self, mock_get_data):
        """대시보드 캐싱 테스트"""
        mock_data = {
            'detail': (1, 2, 3, 4),
            'sales': (100, 50, 30, 20),
            'orders': (10, 5, 3, 2),
            'charts': ([1], [2], [3], [4], [5], [6], [7], [8]),
            'products': ([1], [2], [3], [4], [5], [6], [7], [8]),
            'returns': (1, 2, 3, 4)
        }
        mock_get_data.return_value = mock_data
        
        response1 = self.client.get(reverse('app:dashboard'))
        assert response1.status_code == 200
        
        response2 = self.client.get(reverse('app:dashboard'))
        assert response2.status_code == 200
        
        assert mock_get_data.call_count >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])