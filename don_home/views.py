from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from django.contrib import auth
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_text

from .tokens import account_activation_token
from cp2_don.don_settings import MYSQL_CONN
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql import text, intersect
import pandas as pd
import numpy as np
import json

from don_home.models import Ably_token, Cafe24, AblyProductInfo, AblySalesInfo
from don_home.serializers import AblySerializer, Cafe24Serializer, AblyProductSerializer, AblySalseSerializer
from don_home.apis.ably import AblyDataInfo
from don_home.apis.cafe24 import cafe24_df

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.parsers import JSONParser



# Create your views here.
def index(request):
    username = request.session.get('user')
    if username:
        log = User.objects.get(pk=username)
    else:
        log = '로그인이 필요합니다.'
    return render(request, 'index.html', {'login' : log})

@csrf_exempt
def signup(request):
    if request.method == 'POST':
        if request.POST['password1'] == request.POST['password2']:
            user = User.objects.create_user(
                username=request.POST['username'], 
                password=request.POST['password1'], 
                first_name = request.POST['fullname'],
                email=request.POST['email'])
            user.is_active = False 
            user.save()
            current_site = get_current_site(request) 
            message = render_to_string('account_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            mail_title = "계정 활성화 확인 이메일"
            mail_to = request.POST["email"]
            email = EmailMessage(mail_title, message, to=[mail_to])
            email.send()
            return HttpResponse(
                '<div style="font-size: 40px; width: 100%; height:100%; display:flex; text-align:center; '
                'justify-content: center; align-items: center;">'
                '입력하신 이메일<span>로 인증 링크가 전송되었습니다.</span>'
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
                msg = '로그인 성공'
                auth.login(request, user)
                return redirect('app:index')
        return render(request, "login.html", {"form": form, "msg" : msg})
    else:
        form = AuthenticationForm()
        return render(request, 'login.html', {'form' : form})

def logout(request):
    auth.logout(request)
    return redirect('app:index')


def activate(request, uid64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uid64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        auth.login(request, user)
        return redirect('app:index')
    else:
        return render(request, 'index.hmlt', {'error' : '계정 활성화 오류'})

def checkeusername(request):
    try:
        user = User.objects.get(username=request.GET['username'])
    except Exception as e:
        user = None
    result = {
        'result':'success',
        # 'data' : model_to_dict(user)  # console에서 확인
        'data' : "not exist" if user is None else "exist"
    }
    return JsonResponse(result)

# ABLY
@login_required
def ably(request):
    if request.method == 'POST':
        ably_user = Ably_token(
            ably_id=request.POST['ablyid'], 
            ably_pw=request.POST['ablypw'],
            user_id = request.user.id)
        ably_user.save()
        return render(request, 'user/ably_success.html')
    elif request.method == 'GET':
        ably_dataIn = Ably_token.objects.select_related('user').filter(user_id=request.user.id)
        return render(request, 'user/ably.html', {'ably_dataIn' : ably_dataIn})
    

def get_ably_data(reqeust):
    if reqeust.method == 'GET':
        try:
            ably_data = AblySalesInfo.objects.distinct()
        except:
            ably_data = AblySalesInfo.objects.all()
        return JsonResponse(ably_data)

def delete_ably_data(request):
    Ably_token.objects.all().delete()
    return redirect('app:ably')

@login_required
def usertoken(request):
    if request.method == 'GET':
        data = Ably_token.objects.select_related('user').filter(user_id=request.user.id)
        if AblySalesInfo.objects.all():
            results = AblySalesInfo.objects.raw('SELECT * FROM don_home_ablysalesinfo GROUP BY productOrderNumber')

            return render(request, 'user/token_info.html', {'data_list' : data,
                                                            'ably_data' : results})
    elif request.method == 'POST':
        data2 = Ably_token.objects.select_related('user').filter(user_id=request.user.id).values('ably_id', 'ably_pw')
        ably_id = data2[0]['ably_id']
        ably_pw = data2[0]['ably_pw']
        df, df_pro = AblyDataInfo(ably_id, ably_pw)
        for i in range(len(df['paymentDate'])):
            ably_sales = AblySalesInfo (
                paymentDate = df['paymentDate'][i],
                productOrderNumber = df['productOrderNumber'][i],
                orderNumber = df['orderNumber'][i],
                productName = df['productName'][i],
                options = df['options'][i],
                total = df['total'][i],
                orderName = df['orderName'][i],
                phoneNumber = df['phoneNumber'][i],
                orderStatus = df['orderStatus'][i],
                user_id = request.user.id)
            ably_sales.save()
        for i in range(len(df_pro['productNumber'])):
            ably_product = AblyProductInfo (
                productNumber = df_pro['productNumber'][i],
                productName = df_pro['productName'][i],
                price = df_pro['price'][i],
                discountPeriod = df_pro['discountPeriod'][i],
                discountPrice = df_pro['discountPrice'][i],
                registrationDate = df_pro['registrationDate'][i],
                statusDisplay = df_pro['statusDisplay'][i],
                stock = df_pro['stock'][i],
                totalReview = df_pro['totalReview'][i],
                parcel = df_pro['parcel'][i],
                returnShippingCost = df_pro['returnShippingCost'][i],
                extraShippingCost = df_pro['extraShippingCost'][i],
                user_id = request.user.id)
            ably_product.save()

            # try:
            #     data = AblySalesInfo.objects.raw('SELECT * FROM don_home_ablysalesinfo GROUP BY productOrderNumber')
            #     data.delete()
            # except:
            #     pass
        # data3 = Cafe24.objects.select_related('user').filter(user_id=request.user.id).values()
        # admin_id = data3[0]['cafe24_id']
        # admin_pw = data3[0]['cafe24_pw']
        # client_id = data3[0]['cafe24_clientid']
        # client_secret = data3[0]['cafe24_client_secret']
        # mall_id = data3[0]['cafe24_mallid']
        # encode_csrf_token = data3[0]['cafe24_encode_csrf_token']
        # redirect_uri = data3[0]['cafe24_redirect_uri']
        # total_api = call_total_api(admin_id, admin_pw, client_id, client_secret, mall_id, encode_csrf_token, redirect_uri)
        # categories = total_api['categories']
        # products = total_api['products']
        # orders = total_api['orders']
        # coupons = total_api['coupons']
        return render(request, 'user/token_info.html', {'df' : df, 
                                                        'df_pro' : df_pro,})
    return render(request, 'user/token_info.html')


# CAFE24
@login_required
def cafe24(request):
    if request.method == 'POST':
        cafe24_user = Cafe24(
            cafe24_id = request.POST['cafe24id'],
            cafe24_pw = request.POST['cafe24pw'],
            cafe24_clientid = request.POST['cafe24_clientid'],
            cafe24_client_secret = request.POST['cafe24_client_secret'],
            cafe24_mallid = request.POST['cafe24_mallid'],
            cafe24_encode_csrf_token = request.POST['cafe24_encode_csrf_token'],
            cafe24_redirect_uri = request.POST['cafe24_redirect_uri'],
            service_key = request.POST['cafe24_service_key'],
            user_id = request.user.id)
        cafe24_user.save()
        return render(request, 'user/cafe24_success.html')
    elif request.method == 'GET':
        cafe24_info = Cafe24.objects.select_related('user').filter(user_id=request.user.id)
        return render(request, 'user/cafe24.html', {'cafe24_info': cafe24_info})

def delete_cafe24_data(request):
    Cafe24.objects.all().delete()
    return redirect('app:cafe24')

# DRF
@api_view(['GET', 'POST'])
def ablyproduct_api(request):
    if request.method == 'GET':
        ably_info = Ably_token.objects.select_related('user').values('ably_id', 'ably_pw')
        ably_id = ably_info[0]['ably_id']
        ably_pw = ably_info[0]['ably_pw']

        df, df_pro = AblyDataInfo(ably_id, ably_pw)
        for i in range(len(df_pro['productNumber'])):
            ably_product = AblyProductInfo (
                productNumber = df_pro['productNumber'][i],
                productName = df_pro['productName'][i],
                price = df_pro['price'][i],
                discountPeriod = df_pro['discountPeriod'][i],
                discountPrice = df_pro['discountPrice'][i],
                registrationDate = df_pro['registrationDate'][i],
                statusDisplay = df_pro['statusDisplay'][i],
                stock = df_pro['stock'][i],
                totalReview = df_pro['totalReview'][i],
                parcel = df_pro['parcel'][i],
                returnShippingCost = df_pro['returnShippingCost'][i],
                extraShippingCost = df_pro['extraShippingCost'][i],
                user_id = request.user.id)
            ably_product.save()
        
        articles = AblyProductInfo.objects.raw('SELECT * FROM don_home_ablyproductinfo GROUP BY productNumber')
        serializer = AblyProductSerializer(articles, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = AblyProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def ablysales_api(request):
    if request.method == 'GET':
        ably_info = Ably_token.objects.select_related('user').values('ably_id', 'ably_pw')
        ably_id = ably_info[0]['ably_id']
        ably_pw = ably_info[0]['ably_pw']

        df, df_pro = AblyDataInfo(ably_id, ably_pw)
        for i in range(len(df['paymentDate'])):
            ably_sales = AblySalesInfo (
                paymentDate = df['paymentDate'][i],
                productOrderNumber = df['productOrderNumber'][i],
                orderNumber = df['orderNumber'][i],
                productName = df['productName'][i],
                options = df['options'][i],
                total = df['total'][i],
                orderName = df['orderName'][i],
                phoneNumber = df['phoneNumber'][i],
                orderStatus = df['orderStatus'][i],
                user_id = request.user.id)
            ably_sales.save()

        articles = AblySalesInfo.objects.raw('SELECT * FROM don_home_ablysalesinfo GROUP BY productOrderNumber')
        serializer = AblySalseSerializer(articles, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = AblySalseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def cafe24all_api(request):
    if request.method == 'GET':
        cafe24_info = Cafe24.objects.select_related('user').values('cafe24_id','cafe24_pw','cafe24_clientid',
                                                                   'cafe24_client_secret','cafe24_mallid',
                                                                   'cafe24_encode_csrf_token','cafe24_redirect_uri',)
        cafe24_id = cafe24_info[0]['cafe24_id']
        cafe24_pw = cafe24_info[0]['cafe24_pw']
        clientid = cafe24_info[0]['cafe24_clientid']
        client_secret = cafe24_info[0]['cafe24_client_secret']
        mallid = cafe24_info[0]['cafe24_mallid']
        encode_csrf_token = cafe24_info[0]['cafe24_encode_csrf_token']
        redirect_uri = cafe24_info[0]['cafe24_redirect_uri']
        
        category_df, product_df, order_df, coupon_df = cafe24_df(cafe24_id, cafe24_pw, clientid, client_secret, mallid, encode_csrf_token, redirect_uri)

        engine = create_engine(MYSQL_CONN)

        tableName='don_home_cafe24category'
        category_df.to_sql(name=tableName, con=engine, index=False, if_exists='replace')

        tableName1='don_home_cafe24product'
        product_df.to_sql(name=tableName1, con=engine, index=False, if_exists='replace')

        tableName2='don_home_cafe24order'
        order_df.to_sql(name=tableName2, con=engine, index=False, if_exists='replace')

        tableName3='don_home_cafe24coupon'
        coupon_df.to_sql(name=tableName3, con=engine, index=False, if_exists='replace')

        return Response(cafe24_info)


def dashboard(request):
    engine = create_engine(MYSQL_CONN)
    Session = scoped_session(sessionmaker(bind=engine))
    s = Session()
    conn = engine.raw_connection()
    select_box = request.GET.get('order_date')
    to_de_order = []
    ab_de_order = []
    cf_de_order = []
    na_de_order = []

    
    ably_plat = []
    cafe_plat = []
    naver_plat = []

    # total_order_d = []
    # ably_order = []
    # cafe_order = []
    # naver_order = []

    # total_re = []
    # ably_re = []
    # cafe_re = []
    # naver_re = []

    if select_box == 'odyear':
        # 주문 내역 상세
        SQL_DE = """
        SELECT Platform, `주문번호`, Status, `주문일자`, `고객명`, `상품명`, `수량`, `판매가`, Profit 
        FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        ORDER BY `주문일자` DESC;
        """
        to_d = s.execute(text(SQL_DE))
        SQL_DE_AB = """
        SELECT Platform, `주문번호`, Status, `주문일자`, `고객명`, `상품명`, `수량`, `판매가`, Profit
        FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        HAVING Platform = 'ABLY';
        """
        ab_d = s.execute(text(SQL_DE_AB))
        SQL_DE_CF = """
        SELECT Platform, `주문번호`, Status, `주문일자`, `고객명`, `상품명`, `수량`, `판매가`, Profit
        FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        HAVING Platform = 'Homepage';
        """
        cf_d = s.execute(text(SQL_DE_CF))
        SQL_DE_NA = """
        SELECT Platform, `주문번호`, Status, `주문일자`, `고객명`, `상품명`, `수량`, `판매가`, Profit
        FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        HAVING Platform = '스마트스토어';
        """
        na_d = s.execute(text(SQL_DE_NA))

        # 총 판매가
        SQL1 = """
        SELECT SUM(판매가)
        FROM don_home_unionorder dhu
        WHERE 주문일자 >= date_add(now(), interval -1 YEAR)
        """
        result = s.execute(text(SQL1))
        for re in result:
            result_t = re[0]

        SQL2 = """
        SELECT SUM(판매가)
        FROM don_home_unionorder dhu
        WHERE 주문일자 >= date_add(now(), interval -1 YEAR)
        GROUP BY Platform
        HAVING Platform = 'ABLY';
        """
        a_result = s.execute(text(SQL2))
        for re in a_result:
            ab_sales = re[0]

        SQL3 = """
        SELECT SUM(판매가)
        FROM don_home_unionorder dhu
        WHERE 주문일자 >= date_add(now(), interval -1 YEAR)
        GROUP BY Platform
        HAVING Platform = 'Homepage';
        """
        cf_result = s.execute(text(SQL3))
        for re in cf_result:
            cf_sales = re[0]

        SQL4 = """
        SELECT SUM(판매가)
        FROM don_home_unionorder dhu
        WHERE 주문일자 >= date_add(now(), interval -1 YEAR)
        GROUP BY Platform
        HAVING Platform = '스마트스토어';
        """
        na_result = s.execute(text(SQL4))
        for re in na_result:
            na_sales = re[0]

        # 총 주문 건수
        ORDER1 = """
        SELECT COUNT(Status) as total
        FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR));
        """
        to_order = s.execute(text(ORDER1))
        for to in to_order:
            to_cou_order = to[0]

        ORDER2 = """
        SELECT COUNT(Status) as total
        FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        GROUP BY Platform 
        HAVING Platform = 'ABLY';
        """
        ab_order = s.execute(text(ORDER2))
        for to in ab_order:
            ab_cou_order = to[0]

        ORDER3 = """
        SELECT COUNT(Status) as total
        FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        GROUP BY Platform 
        HAVING Platform = 'ABLY';
        """
        cf_order = s.execute(text(ORDER3))
        for to in cf_order:
            cf_cou_order = to[0]

        ORDER4 = """
        SELECT COUNT(Status) as total
        FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        GROUP BY Platform 
        HAVING Platform = 'ABLY';
        """
        na_order = s.execute(text(ORDER4))
        for to in na_order:
            na_cou_order = to[0]

        # 총 반품 건수
        RE1 = """
        SELECT COUNT(`취소/반품`)
        FROM don_home_unionorder dhu 
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        GROUP BY `취소/반품`
        HAVING `취소/반품` = 'T';
        """
        to_re = s.execute(text(RE1))
        for to in to_re:
            tore = to[0]

        RE2 = """
        SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        GROUP BY Platform, `취소/반품`
        HAVING `취소/반품` = 'T' AND Platform = 'ABLY';
        """
        ab_re = s.execute(text(RE2))
        for to in ab_re:
            abre = to[0]

        RE2 = """
        SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        GROUP BY Platform, `취소/반품`
        HAVING `취소/반품` = 'T' AND Platform = 'Homepage';
        """
        cf_re = s.execute(text(RE2))
        for to in cf_re:
            cfre = to[0]

        RE2 = """
        SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        GROUP BY Platform, `취소/반품`
        HAVING `취소/반품` = 'T' AND Platform = '스마트스토어';
        """
        na_re = s.execute(text(RE2))
        for to in na_re:
            nare = to[0]

        # 월별 주문액 확인
        MONTN_OR = """
        SELECT 
            DATE_FORMAT(`주문일자`,'%Y-%m') date
            ,SUM(판매가) 
        FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        GROUP BY date
        ORDER BY date;
        """
        to_mon = []
        to_data = []
        to_mn = s.execute(text(MONTN_OR))
        for to in to_mn:
            to_mon.append(to[0])
            to_data.append(to[1])
            
        return render(request, 'dashboard.html', {'td':to_d,
                                                  'ab':ab_d,
                                                  'cf':cf_d,
                                                  'na':na_d,
                                                  'total':result_t,
                                                  'ably_plat':ab_sales,
                                                  'cafe_plat':cf_sales,
                                                  'naver_plat':na_sales,
                                                  'total_order':to_cou_order,
                                                  'ably_order':ab_cou_order,
                                                  'cafe_order':cf_cou_order,
                                                  'naver_order':na_cou_order,
                                                  'total_re':tore,
                                                  'ably_re':abre,
                                                  'cafe_re':cfre,
                                                  'naver_re':nare,
                                                  'to_mon':to_mon,
                                                  'to_data':to_data,
                                                  })

        

    #     SQL__1 = """
    #     SELECT COUNT(Status) as or_total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
    #     GROUP BY Platform;
    #     """
    #     data1 = pd.read_sql(SQL__1, conn)
    #     data1['or_total'] = data1['or_total'].astype('int')
    #     total_order = list(np.array(data1['or_total'].tolist()))

    #     cafe_order = total_order[0]
    #     ably_order = total_order[1]
    #     naver_order = total_order[2]

    #     SQL___1 = """
    #     SELECT COUNT(Status)
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 YEAR));
    #     """
    #     s = Session()
    #     total_oresult = s.execute(text(SQL___1))
    #     for tre in total_oresult:
    #         total_order_d = tre[0]

    #     SQL2 = """
    #     SELECT COUNT(Status) as or_total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
    #     GROUP BY Platform;
    #     """
    #     data1 = pd.read_sql(SQL2, conn)
    #     data1['or_total'] = data1['or_total'].astype('int')
    #     total_order = list(np.array(data1['or_total'].tolist()))

    #     cafe_order = total_order[0]
    #     ably_order = total_order[1]
    #     naver_order = total_order[2]

    #     SQL3 = """
    #     SELECT COUNT(Status)
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 YEAR));
    #     """
    #     s = Session()
    #     total_oresult = s.execute(text(SQL___1))
    #     for tre in total_oresult:
    #         total_order_d = tre[0]

    #     # 총 반품 건수
    #     SQL_4to = """
    #     SELECT COUNT(`취소/반품`)
    #     FROM don_home_unionorder dhu 
    #     WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
    #     GROUP BY `취소/반품`
    #     HAVING `취소/반품` = 'T';
    #     """
    #     total_ret = s.execute(text(SQL_4to))
    #     for tre in total_ret:
    #         total_re = tre[0]
    #     SQL_4cf = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = 'Homepage';
    #     """
    #     cafe_ret = s.execute(text(SQL_4cf))
    #     for tre in cafe_ret:
    #         cafe_re = tre[0]
    #     SQL_4ab = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = 'ABLY';
    #     """
    #     ably_ret = s.execute(text(SQL_4ab))
    #     for tre in ably_ret:
    #         ably_re = tre[0]
    #     SQL_4na = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = '스마트스토어';
    #     """
    #     naver_ret = s.execute(text(SQL_4na))
    #     for tre in naver_ret:
    #         naver_re = tre[0]




    # elif select_box == 'odquarter':
    #     SQL2 = """
    #     SELECT SUM(판매가)
    #     FROM don_home_unionorder dhu
    #     WHERE 주문일자 >= date_add(now(), interval -3 MONTH)
    #     """
    #     s = Session()
    #     result = s.execute(text(SQL2))
    #     for re in result:
    #         result_t = re[0]

    #     SQL_2 = """
    #     SELECT SUM(`판매가`) as total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -3 MONTH))
    #     GROUP BY Platform;
    #     """
    #     data = pd.read_sql(SQL_2, conn)
    #     data['total'] = data['total'].astype('int')
    #     total_plat = list(np.array(data['total'].tolist()))

    #     cafe_plat = total_plat[0]
    #     ably_plat = total_plat[1]
    #     naver_plat = total_plat[2]

    #     SQL__2 = """
    #     SELECT COUNT(Status) as or_total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -3 MONTH))
    #     GROUP BY Platform;
    #     """
    #     data1 = pd.read_sql(SQL__2, conn)
    #     data1['or_total'] = data1['or_total'].astype('int')
    #     total_order = list(np.array(data1['or_total'].tolist()))

    #     cafe_order = total_order[0]
    #     ably_order = total_order[1]
    #     naver_order = total_order[2]

    #     SQL___2 = """
    #     SELECT COUNT(Status)
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -3 MONTH));
    #     """
    #     s = Session()
    #     total_oresult = s.execute(text(SQL___2))
    #     for tre in total_oresult:
    #         total_order_d = tre[0]

    #     # 총 반품 건수
    #     SQL_4to = """
    #     SELECT COUNT(`취소/반품`)
    #     FROM don_home_unionorder dhu 
    #     WHERE (`주문일자` >= date_add(now(), interval -3 MONTH))
    #     GROUP BY `취소/반품`
    #     HAVING `취소/반품` = 'T';
    #     """
    #     total_ret = s.execute(text(SQL_4to))
    #     for tre in total_ret:
    #         total_re = tre[0]
    #     SQL_4cf = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -3 MONTH))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = 'Homepage';
    #     """
    #     cafe_ret = s.execute(text(SQL_4cf))
    #     for tre in cafe_ret:
    #         cafe_re = tre[0]
    #     SQL_4ab = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -3 MONTH))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = 'ABLY';
    #     """
    #     ably_ret = s.execute(text(SQL_4ab))
    #     for tre in ably_ret:
    #         ably_re = tre[0]
    #     SQL_4na = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -3 MONTH))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = '스마트스토어';
    #     """
    #     naver_ret = s.execute(text(SQL_4na))
    #     for tre in naver_ret:
    #         naver_re = tre[0]


    # elif select_box == 'odmonth':
    #     SQL3 = """
    #     SELECT SUM(판매가)
    #     FROM don_home_unionorder dhu
    #     WHERE 주문일자 >= date_add(now(), interval -1 MONTH)
    #     """
    #     s = Session()
    #     result = s.execute(text(SQL3))
    #     for re in result:
    #         result_t = re[0]

    #     SQL_3 = """
    #     SELECT SUM(`판매가`) as total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    #     GROUP BY Platform;
    #     """
    #     data = pd.read_sql(SQL_3, conn)
    #     data['total'] = data['total'].astype('int')
    #     total_plat = list(np.array(data['total'].tolist()))

    #     cafe_plat = total_plat[0]
    #     ably_plat = total_plat[1]
    #     naver_plat = total_plat[2]

    #     SQL__3 = """
    #     SELECT COUNT(Status) as or_total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    #     GROUP BY Platform;
    #     """
    #     data1 = pd.read_sql(SQL__3, conn)
    #     data1['or_total'] = data1['or_total'].astype('int')
    #     total_order = list(np.array(data1['or_total'].tolist()))

    #     cafe_order = total_order[0]
    #     ably_order = total_order[1]
    #     naver_order = total_order[2]

    #     SQL___3 = """
    #     SELECT COUNT(Status)
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 MONTH));
    #     """
    #     s = Session()
    #     total_oresult = s.execute(text(SQL___3))
    #     for tre in total_oresult:
    #         total_order_d = tre[0]

    #     # 총 반품 건수
    #     SQL_4to = """
    #     SELECT COUNT(`취소/반품`)
    #     FROM don_home_unionorder dhu 
    #     WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    #     GROUP BY `취소/반품`
    #     HAVING `취소/반품` = 'T';
    #     """
    #     total_ret = s.execute(text(SQL_4to))
    #     for tre in total_ret:
    #         total_re = tre[0]
    #     SQL_4cf = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = 'Homepage';
    #     """
    #     cafe_ret = s.execute(text(SQL_4cf))
    #     for tre in cafe_ret:
    #         cafe_re = tre[0]
    #     SQL_4ab = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = 'ABLY';
    #     """
    #     ably_ret = s.execute(text(SQL_4ab))
    #     for tre in ably_ret:
    #         ably_re = tre[0]
    #     SQL_4na = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = '스마트스토어';
    #     """
    #     naver_ret = s.execute(text(SQL_4na))
    #     for tre in naver_ret:
    #         naver_re = tre[0]

        
    # elif select_box == 'odweek':
    #     SQL3 = """
    #     SELECT SUM(판매가)
    #     FROM don_home_unionorder dhu
    #     WHERE 주문일자 >= date_add(now(), interval -1 WEEK)
    #     """
    #     s = Session()
    #     result = s.execute(text(SQL3))
    #     for re in result:
    #         result_t = re[0]

    #     # 총 판매금액
    #     SQL_3cf = """
    #     SELECT SUM(`판매가`) as total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 WEEK))
    #     GROUP BY Platform
    #     HAVING Platform = 'Homepage'
    #     """
    #     total_oresult = s.execute(text(SQL_3cf))
    #     for tre in total_oresult:
    #         cafe_plat = tre[0]
    #     SQL_3ab = """
    #     SELECT SUM(`판매가`) as total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 WEEK))
    #     GROUP BY Platform
    #     HAVING Platform = 'ABLY'
    #     """
    #     total_oresult = s.execute(text(SQL_3ab))
    #     for tre in total_oresult:
    #         ably_plat = tre[0]
    #     SQL_3na = """
    #     SELECT SUM(`판매가`) as total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 WEEK))
    #     GROUP BY Platform
    #     HAVING Platform = '스마트스토어'
    #     """
    #     total_oresult = s.execute(text(SQL_3na))
    #     for tre in total_oresult:
    #         naver_plat = tre[0]

    #     # 주문 건수
    #     SQL__3cf = """
    #     SELECT COUNT(Status) as or_total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 WEEK))
    #     GROUP BY Platform
    #     HAVING Platform = 'Homepage'
    #     """
    #     cafe_oresult = s.execute(text(SQL__3cf))
    #     for tre in cafe_oresult:
    #         cafe_order = tre[0]

    #     SQL__3ab = """
    #     SELECT COUNT(Status) as or_total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 WEEK))
    #     GROUP BY Platform
    #     HAVING Platform = 'ABLY'
    #     """
    #     ably_oresult = s.execute(text(SQL__3ab))
    #     for tre in ably_oresult:
    #         ably_order = tre[0]

    #     SQL__3na = """
    #     SELECT COUNT(Status) as or_total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 WEEK))
    #     GROUP BY Platform
    #     HAVING Platform = '스마트스토어'
    #     """
    #     naver_oresult = s.execute(text(SQL__3na))
    #     for tre in naver_oresult:
    #         naver_order = tre[0]


    #     SQL___3 = """
    #     SELECT COUNT(Status)
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 WEEK))
    #     """
    #     s = Session()
    #     total_oresult = s.execute(text(SQL___3))
    #     for tre in total_oresult:
    #         total_order_d = tre[0]

    #     # 총 반품 건수
    #     SQL_4to = """
    #     SELECT COUNT(`취소/반품`)
    #     FROM don_home_unionorder dhu 
    #     WHERE (`주문일자` >= date_add(now(), interval -1 WEEK))
    #     GROUP BY `취소/반품`
    #     HAVING `취소/반품` = 'T';
    #     """
    #     total_ret = s.execute(text(SQL_4to))
    #     for tre in total_ret:
    #         total_re = tre[0]
    #     SQL_4cf = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 WEEK))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = 'Homepage';
    #     """
    #     cafe_ret = s.execute(text(SQL_4cf))
    #     for tre in cafe_ret:
    #         cafe_re = tre[0]
    #     SQL_4ab = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 WEEK))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = 'ABLY';
    #     """
    #     ably_ret = s.execute(text(SQL_4ab))
    #     for tre in ably_ret:
    #         ably_re = tre[0]
    #     SQL_4na = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 WEEK))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = '스마트스토어';
    #     """
    #     naver_ret = s.execute(text(SQL_4na))
    #     for tre in naver_ret:
    #         naver_re = tre[0]



    # elif select_box == 'oddays':
    #     SQL4 = """
    #     SELECT SUM(판매가)
    #     FROM don_home_unionorder dhu
    #     WHERE 주문일자 >= date_add(now(), interval -1 DAY)
    #     """
    #     s = Session()
    #     result = s.execute(text(SQL4))
    #     for re in result:
    #         result_t = re[0]
        
    #     # 총 판매금액
    #     SQL_3cf = """
    #     SELECT SUM(`판매가`) as total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 DAY))
    #     GROUP BY Platform
    #     HAVING Platform = 'Homepage'
    #     """
    #     total_oresult = s.execute(text(SQL_3cf))
    #     for tre in total_oresult:
    #         cafe_plat = tre[0]
    #     SQL_3ab = """
    #     SELECT SUM(`판매가`) as total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 DAY))
    #     GROUP BY Platform
    #     HAVING Platform = 'ABLY'
    #     """
    #     total_oresult = s.execute(text(SQL_3ab))
    #     for tre in total_oresult:
    #         ably_plat = tre[0]
    #     SQL_3na = """
    #     SELECT SUM(`판매가`) as total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 DAY))
    #     GROUP BY Platform
    #     HAVING Platform = '스마트스토어'
    #     """
    #     total_oresult = s.execute(text(SQL_3na))
    #     for tre in total_oresult:
    #         naver_plat = tre[0]

    #     # 주문 건수
    #     SQL__3cf = """
    #     SELECT COUNT(Status) as or_total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 DAY))
    #     GROUP BY Platform
    #     HAVING Platform = 'Homepage'
    #     """
    #     cafe_oresult = s.execute(text(SQL__3cf))
    #     for tre in cafe_oresult:
    #         cafe_order = tre[0]

    #     SQL__3ab = """
    #     SELECT COUNT(Status) as or_total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 DAY))
    #     GROUP BY Platform
    #     HAVING Platform = 'ABLY'
    #     """
    #     ably_oresult = s.execute(text(SQL__3ab))
    #     for tre in ably_oresult:
    #         ably_order = tre[0]

    #     SQL__3na = """
    #     SELECT COUNT(Status) as or_total
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 DAY))
    #     GROUP BY Platform
    #     HAVING Platform = '스마트스토어'
    #     """
    #     naver_oresult = s.execute(text(SQL__3na))
    #     for tre in naver_oresult:
    #         naver_order = tre[0]

    #     SQL___4 = """
    #     SELECT COUNT(Status)
    #     FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 DAY))
    #     """
    #     s = Session()
    #     total_oresult = s.execute(text(SQL___4))
    #     for tre in total_oresult:
    #         total_order_d = tre[0]

    #     # 총 반품 건수
    #     SQL_4to = """
    #     SELECT COUNT(`취소/반품`)
    #     FROM don_home_unionorder dhu 
    #     WHERE (`주문일자` >= date_add(now(), interval -1 DAY))
    #     GROUP BY `취소/반품`
    #     HAVING `취소/반품` = 'T';
    #     """
    #     total_ret = s.execute(text(SQL_4to))
    #     for tre in total_ret:
    #         total_re = tre[0]
    #     SQL_4cf = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 DAY))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = 'Homepage';
    #     """
    #     cafe_ret = s.execute(text(SQL_4cf))
    #     for tre in cafe_ret:
    #         cafe_re = tre[0]
    #     SQL_4ab = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 DAY))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = 'ABLY';
    #     """
    #     ably_ret = s.execute(text(SQL_4ab))
    #     for tre in ably_ret:
    #         ably_re = tre[0]
    #     SQL_4na = """
    #     SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    #     WHERE (`주문일자` >= date_add(now(), interval -1 DAY))
    #     GROUP BY Platform, `취소/반품`
    #     HAVING `취소/반품` = 'T' AND Platform = '스마트스토어';
    #     """
    #     naver_ret = s.execute(text(SQL_4na))
    #     for tre in naver_ret:
    #         naver_re = tre[0]
    conn.close()
    engine.dispose()


    return render(request, 'dashboard.html')

    # {'total': result_t,
    #                                         'cafe_plat': cafe_plat,
    #                                         'ably_plat': ably_plat,
    #                                         'naver_plat': naver_plat,
    #                                         'cafe_order': cafe_order,
    #                                         'ably_order': ably_order,
    #                                         'naver_order': naver_order,
    #                                         'total_order': total_order_d,
    #                                         'total_re': total_re,
    #                                         'ably_re': ably_re,
    #                                         'cafe_re': cafe_re,
    #                                         'naver_re': naver_re,
    #                                         }

def total_sales_info(request):
    return 