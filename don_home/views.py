# views.py 개선 버전 - 기존 코드와 호환되도록 점진적 개선

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from django.contrib import auth
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.cache import cache

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes, force_text

from .tokens import account_activation_token
from cp2_don.don_settings import MYSQL_CONN
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import pandas as pd
import json
import logging

from don_home.models import Ably_token, Cafe24, AblyProductInfo, AblySalesInfo
from don_home.serializers import AblySerializer, Cafe24Serializer, AblyProductSerializer, AblySalseSerializer
from don_home.apis.ably import AblyDataInfo
from don_home.apis.cafe24 import cafe24_df
from don_home.Dashboard.chart_year import Chart_pre_year, Product_total_year, Product_re_year, total_order_year, total_sales_year, detail_order_year
from don_home.Dashboard.chart_month import Chart_pre_month, Product_total_month, Product_re_month, total_order_month, total_sales_month, detail_order_month

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status

logger = logging.getLogger(__name__)

def get_user_from_session(request):
    """세션에서 사용자 정보를 가져오는 헬퍼 함수"""
    username = request.session.get('user')
    if username:
        try:
            return User.objects.get(pk=username)
        except User.DoesNotExist:
            return None
    return None


def send_activation_email(user, request):
    """계정 활성화 이메일 전송"""
    current_site = get_current_site(request)
    message = render_to_string('account_email.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    
    email = EmailMessage(
        subject="계정 활성화 확인 이메일",
        body=message,
        to=[user.email]
    )
    email.send()


def index(request):
    user = get_user_from_session(request)
    log = user if user else '로그인이 필요합니다.'
    return render(request, 'index.html', {'login': log})


@csrf_exempt
def signup(request):
    if request.method == 'POST':
        if request.POST['password1'] == request.POST['password2']:
            user = User.objects.create_user(
                username=request.POST['username'],
                password=request.POST['password1'],
                first_name=request.POST['fullname'],
                email=request.POST['email']
            )
            user.is_active = False
            user.save()
            
            send_activation_email(user, request)
            
            return HttpResponse(
                '<div style="font-size: 40px; width: 100%; height:100%; display:flex; text-align:center; '
                'justify-content: center; align-items: center;">'
                '입력하신 이메일로 인증 링크가 전송되었습니다.'
                '</div>'
            )
    
    return render(request, 'signup.html')


@csrf_exempt
def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        msg = '아이디 또는 패스워드가 일치하지 않습니다.'
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password')
            user = auth.authenticate(username=username, password=raw_password)
            
            if user is not None:
                auth.login(request, user)
                return redirect('app:index')
        
        return render(request, "login.html", {"form": form, "msg": msg})
    
    form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout(request):
    auth.logout(request)
    return redirect('app:index')


def activate(request, uid64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uid64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        auth.login(request, user)
        return redirect('app:index')
    
    return render(request, 'index.html', {'error': '계정 활성화 오류'})


def check_username(request):
    username = request.GET.get('username')
    exists = User.objects.filter(username=username).exists()
    
    return JsonResponse({
        'result': 'success',
        'data': "exist" if exists else "not exist"
    })


@login_required
def ably(request):
    if request.method == 'POST':
        Ably_token.objects.update_or_create(
            user_id=request.user.id,
            defaults={
                'ably_id': request.POST['ablyid'],
                'ably_pw': request.POST['ablypw']
            }
        )
        return render(request, 'user/ably_success.html')
    
    elif request.method == 'GET':
        ably_dataIn = Ably_token.objects.select_related('user').filter(user_id=request.user.id)
        return render(request, 'user/ably.html', {'ably_dataIn': ably_dataIn})


def get_ably_data(request):
    """사용자별 Ably 데이터 조회"""
    if request.method == 'GET' and request.user.is_authenticated:
        ably_data = AblySalesInfo.objects.filter(
            user_id=request.user.id
        ).values('productOrderNumber').distinct()
        
        return JsonResponse(list(ably_data), safe=False)
    
    return JsonResponse({'error': 'Unauthorized'}, status=401)


def delete_ably_data(request):
    if request.user.is_authenticated:
        Ably_token.objects.filter(user_id=request.user.id).delete()
    return redirect('app:ably')


@login_required
@transaction.atomic
def usertoken(request):
    if request.method == 'GET':
        data = Ably_token.objects.select_related('user').filter(user_id=request.user.id)
        
        if AblySalesInfo.objects.filter(user_id=request.user.id).exists():
            results = AblySalesInfo.objects.filter(
                user_id=request.user.id
            ).values(
                'productOrderNumber', 'productName', 'orderStatus'
            ).distinct()
            
            return render(request, 'user/token_info.html', {
                'data_list': data,
                'ably_data': results
            })
    
    elif request.method == 'POST':
        try:
            data2 = Ably_token.objects.filter(user_id=request.user.id).values('ably_id', 'ably_pw').first()
            
            if not data2:
                return render(request, 'user/token_info.html', {'error': 'Ably 토큰이 없습니다.'})
            
            ably_id = data2['ably_id']
            ably_pw = data2['ably_pw']
            
            df, df_pro = AblyDataInfo(ably_id, ably_pw)
            
            AblySalesInfo.objects.filter(user_id=request.user.id).delete()
            AblyProductInfo.objects.filter(user_id=request.user.id).delete()
            
            sales_objects = []
            for i in range(len(df)):
                sales_objects.append(
                    AblySalesInfo(
                        paymentDate=df['paymentDate'][i],
                        productOrderNumber=df['productOrderNumber'][i],
                        orderNumber=df['orderNumber'][i],
                        productName=df['productName'][i],
                        options=df['options'][i],
                        total=df['total'][i],
                        orderName=df['orderName'][i],
                        phoneNumber=df['phoneNumber'][i],
                        orderStatus=df['orderStatus'][i],
                        user_id=request.user.id
                    )
                )
            AblySalesInfo.objects.bulk_create(sales_objects, batch_size=1000)
            
            product_objects = []
            for i in range(len(df_pro)):
                product_objects.append(
                    AblyProductInfo(
                        productNumber=df_pro['productNumber'][i],
                        productName=df_pro['productName'][i],
                        price=df_pro['price'][i],
                        discountPeriod=df_pro['discountPeriod'][i],
                        discountPrice=df_pro['discountPrice'][i],
                        registrationDate=df_pro['registrationDate'][i],
                        statusDisplay=df_pro['statusDisplay'][i],
                        stock=df_pro['stock'][i],
                        totalReview=df_pro['totalReview'][i],
                        parcel=df_pro['parcel'][i],
                        returnShippingCost=df_pro['returnShippingCost'][i],
                        extraShippingCost=df_pro['extraShippingCost'][i],
                        user_id=request.user.id
                    )
                )
            AblyProductInfo.objects.bulk_create(product_objects, batch_size=1000)
            
            return render(request, 'user/token_info.html', {'df': df, 'df_pro': df_pro})
            
        except Exception as e:
            logger.error(f"Ably data collection error: {str(e)}")
            return render(request, 'user/token_info.html', {'error': '데이터 수집 중 오류가 발생했습니다.'})
    
    return render(request, 'user/token_info.html')


@login_required
def cafe24(request):
    if request.method == 'POST':
        Cafe24.objects.update_or_create(
            user_id=request.user.id,
            defaults={
                'cafe24_id': request.POST['cafe24id'],
                'cafe24_pw': request.POST['cafe24pw'],
                'cafe24_clientid': request.POST['cafe24_clientid'],
                'cafe24_client_secret': request.POST['cafe24_client_secret'],
                'cafe24_mallid': request.POST['cafe24_mallid'],
                'cafe24_encode_csrf_token': request.POST['cafe24_encode_csrf_token'],
                'cafe24_redirect_uri': request.POST['cafe24_redirect_uri'],
                'service_key': request.POST['cafe24_service_key']
            }
        )
        return render(request, 'user/cafe_success.html')
    
    elif request.method == 'GET':
        cafe24_info = Cafe24.objects.select_related('user').filter(user_id=request.user.id)
        return render(request, 'user/cafe24.html', {'cafe24_info': cafe24_info})


def delete_cafe24_data(request):
    if request.user.is_authenticated:
        Cafe24.objects.filter(user_id=request.user.id).delete()
    return redirect('app:cafe24')


@api_view(['GET', 'POST'])
@login_required
def ablyproduct_api(request):
    if request.method == 'GET':
        try:
            ably_info = Ably_token.objects.filter(user_id=request.user.id).values('ably_id', 'ably_pw').first()
            
            if not ably_info:
                return Response({'error': 'Ably token not found'}, status=status.HTTP_404_NOT_FOUND)
            
            ably_id = ably_info['ably_id']
            ably_pw = ably_info['ably_pw']
            
            df, df_pro = AblyDataInfo(ably_id, ably_pw)
            
            with transaction.atomic():
                AblyProductInfo.objects.filter(user_id=request.user.id).delete()
                
                product_objects = [
                    AblyProductInfo(
                        productNumber=df_pro['productNumber'][i],
                        productName=df_pro['productName'][i],
                        price=df_pro['price'][i],
                        discountPeriod=df_pro['discountPeriod'][i],
                        discountPrice=df_pro['discountPrice'][i],
                        registrationDate=df_pro['registrationDate'][i],
                        statusDisplay=df_pro['statusDisplay'][i],
                        stock=df_pro['stock'][i],
                        totalReview=df_pro['totalReview'][i],
                        parcel=df_pro['parcel'][i],
                        returnShippingCost=df_pro['returnShippingCost'][i],
                        extraShippingCost=df_pro['extraShippingCost'][i],
                        user_id=request.user.id
                    )
                    for i in range(len(df_pro))
                ]
                AblyProductInfo.objects.bulk_create(product_objects, batch_size=1000)
            
            articles = AblyProductInfo.objects.filter(user_id=request.user.id).values('productNumber').distinct()
            serializer = AblyProductSerializer(articles, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Ably product API error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'POST':
        serializer = AblyProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@login_required
def ablysales_api(request):
    if request.method == 'GET':
        try:
            ably_info = Ably_token.objects.filter(user_id=request.user.id).values('ably_id', 'ably_pw').first()
            
            if not ably_info:
                return Response({'error': 'Ably token not found'}, status=status.HTTP_404_NOT_FOUND)
            
            ably_id = ably_info['ably_id']
            ably_pw = ably_info['ably_pw']
            
            df, df_pro = AblyDataInfo(ably_id, ably_pw)
            
            with transaction.atomic():
                AblySalesInfo.objects.filter(user_id=request.user.id).delete()
                
                sales_objects = [
                    AblySalesInfo(
                        paymentDate=df['paymentDate'][i],
                        productOrderNumber=df['productOrderNumber'][i],
                        orderNumber=df['orderNumber'][i],
                        productName=df['productName'][i],
                        options=df['options'][i],
                        total=df['total'][i],
                        orderName=df['orderName'][i],
                        phoneNumber=df['phoneNumber'][i],
                        orderStatus=df['orderStatus'][i],
                        user_id=request.user.id
                    )
                    for i in range(len(df))
                ]
                AblySalesInfo.objects.bulk_create(sales_objects, batch_size=1000)
            
            articles = AblySalesInfo.objects.filter(user_id=request.user.id).values('productOrderNumber').distinct()
            serializer = AblySalseSerializer(articles, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Ably sales API error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'POST':
        serializer = AblySalseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@login_required
def cafe24all_api(request):
    if request.method == 'GET':
        try:
            cafe24_info = Cafe24.objects.filter(user_id=request.user.id).values(
                'cafe24_id', 'cafe24_pw', 'cafe24_clientid',
                'cafe24_client_secret', 'cafe24_mallid',
                'cafe24_encode_csrf_token', 'cafe24_redirect_uri'
            ).first()
            
            if not cafe24_info:
                return Response({'error': 'Cafe24 token not found'}, status=status.HTTP_404_NOT_FOUND)
            
            cafe24_id = cafe24_info['cafe24_id']
            cafe24_pw = cafe24_info['cafe24_pw']
            clientid = cafe24_info['cafe24_clientid']
            client_secret = cafe24_info['cafe24_client_secret']
            mallid = cafe24_info['cafe24_mallid']
            encode_csrf_token = cafe24_info['cafe24_encode_csrf_token']
            redirect_uri = cafe24_info['cafe24_redirect_uri']
            
            category_df, product_df, order_df, coupon_df = cafe24_df(
                cafe24_id, cafe24_pw, clientid, client_secret, 
                mallid, encode_csrf_token, redirect_uri
            )
            
            engine = create_engine(MYSQL_CONN)
            with engine.begin() as conn:
                category_df.to_sql(name='don_home_cafe24category', con=conn, index=False, if_exists='replace')
                product_df.to_sql(name='don_home_cafe24product', con=conn, index=False, if_exists='replace')
                order_df.to_sql(name='don_home_cafe24order', con=conn, index=False, if_exists='replace')
                coupon_df.to_sql(name='don_home_cafe24coupon', con=conn, index=False, if_exists='replace')
            
            return Response({'status': 'success', 'message': 'Data collected successfully'})
            
        except Exception as e:
            logger.error(f"Cafe24 API error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_dashboard_data(period='year'):
    """대시보드 데이터를 가져오는 헬퍼 함수"""
    cache_key = f'dashboard_data_{period}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    if period == 'month':
        data = {
            'detail': detail_order_month(),
            'sales': total_sales_month(),
            'orders': total_order_month(),
            'charts': Chart_pre_month(),
            'products': Product_total_month(),
            'returns': Product_re_month()
        }
    else:
        data = {
            'detail': detail_order_year(),
            'sales': total_sales_year(),
            'orders': total_order_year(),
            'charts': Chart_pre_year(),
            'products': Product_total_year(),
            'returns': Product_re_year()
        }
    
    cache.set(cache_key, data, 300)
    return data


def dashboard(request):
    """대시보드 뷰 - 중복 코드 제거"""
    select_box = request.GET.get('order_date', 'odyear')
    
    if select_box == 'odmonth':
        data = get_dashboard_data('month')
    else:
        data = get_dashboard_data('year')
    
    detail = data['detail']
    sales = data['sales']
    orders = data['orders']
    charts = data['charts']
    products = data['products']
    returns = data['returns']
    
    context = {
        'td': detail[0], 'ab': detail[1], 'cf': detail[2], 'na': detail[3],
        'total': sales[0], 'ably_plat': sales[1], 
        'cafe_plat': sales[2], 'naver_plat': sales[3],
        'total_order': orders[0], 'ably_order': orders[1],
        'cafe_order': orders[2], 'naver_order': orders[3],
        'total_re': returns[3], 'ably_re': returns[2],
        'cafe_re': returns[1], 'naver_re': returns[0],
        'to_mon': charts[0], 'to_data': charts[1],
        'ab_mon': charts[3], 'ab_data': charts[2],
        'cf_mon': charts[5], 'cf_data': charts[4],
        'na_mon': charts[7], 'na_data': charts[6],
        'tpn': products[0], 'tpt': products[1],
        'apn': products[2], 'apt': products[3],
        'cpn': products[4], 'cpt': products[5],
        'npn': products[6], 'npt': products[7]
    }
    
    return render(request, 'dashboard.html', context=context)