# AJAX 전용 뷰 함수들
from django.http import JsonResponse
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.core.cache import cache
import json
import logging

from .models import Ably_token, AblySalesInfo, AblyProductInfo
from .apis.ably import AblyDataInfo
from .Dashboard.chart_year import (
    Chart_pre_year, Product_total_year, Product_re_year, 
    total_order_year, total_sales_year, detail_order_year
)

logger = logging.getLogger(__name__)


def ajax_required(view_func):
    """AJAX 요청인지 확인하는 데코레이터"""
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'AJAX 요청만 허용됩니다.'}, status=400)
        return view_func(request, *args, **kwargs)
    return wrapper


@csrf_protect
@ajax_required
def ajax_login(request):
    """AJAX 로그인 처리"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return JsonResponse({
                    'status': 'error',
                    'message': '아이디와 비밀번호를 입력해주세요.'
                })
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    auth_login(request, user)
                    return JsonResponse({
                        'status': 'success',
                        'message': '로그인 성공',
                        'redirect': '/dashboard/'
                    })
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': '계정이 활성화되지 않았습니다. 이메일을 확인해주세요.'
                    })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': '아이디 또는 비밀번호가 올바르지 않습니다.'
                })
                
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '잘못된 요청입니다.'
            })
    
    return JsonResponse({'status': 'error', 'message': '잘못된 요청입니다.'})


@csrf_protect
@ajax_required
def ajax_signup(request):
    """AJAX 회원가입 처리"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            username = data.get('username')
            email = data.get('email')
            password1 = data.get('password1')
            password2 = data.get('password2')
            fullname = data.get('fullname')
            
            if not all([username, email, password1, password2, fullname]):
                return JsonResponse({
                    'status': 'error',
                    'message': '모든 필드를 입력해주세요.'
                })
            
            if password1 != password2:
                return JsonResponse({
                    'status': 'error',
                    'message': '비밀번호가 일치하지 않습니다.'
                })
            
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': '이미 사용중인 아이디입니다.'
                })
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': '이미 사용중인 이메일입니다.'
                })
            
            user = User.objects.create_user(
                username=username,
                password=password1,
                first_name=fullname,
                email=email
            )
            user.is_active = False
            user.save()
            
            from .views import send_activation_email
            send_activation_email(user, request)
            
            return JsonResponse({
                'status': 'success',
                'message': '회원가입이 완료되었습니다. 이메일을 확인해주세요.'
            })
            
        except Exception as e:
            logger.error(f"회원가입 오류: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': '회원가입 중 오류가 발생했습니다.'
            })
    
    return JsonResponse({'status': 'error', 'message': '잘못된 요청입니다.'})


@ajax_required
def ajax_check_username(request):
    """AJAX 아이디 중복 확인"""
    username = request.GET.get('username')
    
    if not username:
        return JsonResponse({
            'status': 'error',
            'message': '아이디를 입력해주세요.'
        })
    
    exists = User.objects.filter(username=username).exists()
    
    return JsonResponse({
        'status': 'success',
        'data': 'exist' if exists else 'not exist'
    })


@login_required
@ajax_required
def ajax_token_info(request):
    """AJAX 토큰 정보 조회/처리"""
    if request.method == 'GET':
        try:
            ably_data = AblySalesInfo.objects.filter(
                user_id=request.user.id
            ).values(
                'productOrderNumber', 'productName', 'orderStatus'
            ).distinct()[:100] 
            
            return JsonResponse({
                'status': 'success',
                'ably_data': list(ably_data)
            })
            
        except Exception as e:
            logger.error(f"토큰 정보 조회 오류: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': '데이터 조회 중 오류가 발생했습니다.'
            })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'ablycrawling':
                token_data = Ably_token.objects.filter(
                    user_id=request.user.id
                ).values('ably_id', 'ably_pw').first()
                
                if not token_data:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Ably 토큰을 먼저 등록해주세요.'
                    })
                
                with transaction.atomic():
                    df, df_pro = AblyDataInfo(
                        token_data['ably_id'], 
                        token_data['ably_pw']
                    )
                    
                    AblySalesInfo.objects.filter(user_id=request.user.id).delete()
                    
                    sales_objects = []
                    for _, row in df.iterrows():
                        sales_objects.append(
                            AblySalesInfo(
                                paymentDate=row['paymentDate'],
                                productOrderNumber=row['productOrderNumber'],
                                orderNumber=row['orderNumber'],
                                productName=row['productName'],
                                options=row['options'],
                                total=row['total'],
                                orderName=row['orderName'],
                                phoneNumber=row['phoneNumber'],
                                orderStatus=row['orderStatus'],
                                user_id=request.user.id
                            )
                        )
                    
                    if sales_objects:
                        AblySalesInfo.objects.bulk_create(sales_objects)
                    
                    ably_data = AblySalesInfo.objects.filter(
                        user_id=request.user.id
                    ).values(
                        'productOrderNumber', 'productName', 'orderStatus'
                    ).distinct()[:100]
                    
                    return JsonResponse({
                        'status': 'success',
                        'message': '데이터를 성공적으로 가져왔습니다.',
                        'ably_data': list(ably_data)
                    })
                    
        except Exception as e:
            logger.error(f"토큰 정보 처리 오류: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': '데이터 처리 중 오류가 발생했습니다.'
            })
    
    return JsonResponse({'status': 'error', 'message': '잘못된 요청입니다.'})


@login_required
@ajax_required 
def ajax_dashboard(request):
    """AJAX 대시보드 데이터"""
    try:
        order_date = request.GET.get('order_date', 'odyear')
        
        cache_key = f'dashboard_{request.user.id}_{order_date}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return JsonResponse({
                'status': 'success',
                'data': cached_data
            })
        
        if order_date == 'odyear':
            to_mon, to_data, ab_mon, ab_data, cf_mon, cf_data, na_mon, na_data = Chart_pre_year()
            tpn, tpt, apn, apt, cpn, cpt, npn, npt = Product_total_year()
            
        elif order_date == 'odmonth':
            from .Dashboard.chart_month import Chart_pre_month, Product_total_month
            to_mon, to_data, ab_mon, ab_data, cf_mon, cf_data, na_mon, na_data = Chart_pre_month()
            tpn, tpt, apn, apt, cpn, cpt, npn, npt = Product_total_month()
        
        else:
            from .Dashboard.chart_week import Chart_pre_week, Product_total_week
            to_mon, to_data, ab_mon, ab_data, cf_mon, cf_data, na_mon, na_data = Chart_pre_week()
            tpn, tpt, apn, apt, cpn, cpt, npn, npt = Product_total_week()
        
        total, ably_plat, cafe_plat, naver_plat = total_sales_year()
        total_order, ably_order, cafe_order, naver_order = total_order_year()
        total_re, ably_re, cafe_re, naver_re = Product_re_year()
        td, ab, cf, na = detail_order_year()
        
        dashboard_data = {
            'to_mon': to_mon, 'to_data': to_data,
            'ab_mon': ab_mon, 'ab_data': ab_data,
            'cf_mon': cf_mon, 'cf_data': cf_data,
            'na_mon': na_mon, 'na_data': na_data,
            
            'tpn': tpn, 'tpt': tpt,
            'apn': apn, 'apt': apt,
            'cpn': cpn, 'cpt': cpt,
            'npn': npn, 'npt': npt,
            
            'total': total,
            'ably_plat': ably_plat,
            'cafe_plat': cafe_plat,
            'naver_plat': naver_plat,
            
            'total_order': total_order,
            'ably_order': ably_order,
            'cafe_order': cafe_order,
            'naver_order': naver_order,
            
            'total_re': total_re,
            'ably_re': ably_re,
            'cafe_re': cafe_re,
            'naver_re': naver_re,
            
            'td': td,
            'ab': ab,
            'cf': cf,
            'na': na
        }
        
        cache.set(cache_key, dashboard_data, 300)
        
        return JsonResponse({
            'status': 'success',
            'data': dashboard_data
        })
        
    except Exception as e:
        logger.error(f"대시보드 데이터 조회 오류: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': '대시보드 데이터 조회 중 오류가 발생했습니다.'
        })