from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import requests
import json
import base64
import pandas as pd
import numpy as np
import time
import pyperclip
from datetime import datetime, timedelta

# 테이블별 df 추출
def cafe24_df(admin_id, admin_pw, client_id, client_secret, mall_id, encode_csrf_token, redirect_uri):
    # 통합 API 추출
    def call_total_api():
        # code 가져오기
        def get_cafe24_code(scope):
            # code를 가져와야하는 URL
            Request_URL = f"https://{mall_id}.cafe24api.com/api/v2/oauth/authorize?response_type=code&client_id={client_id}&state={encode_csrf_token}&redirect_uri={redirect_uri}&scope={scope}"
        
            # 크롤링 구조
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('no-sandox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--start-maximized')
            # options.add_argument("headless") # 백그라운드 실행 (만일 창 보이게 하고 싶으면 주석 처리)

            # Docker 환경에서는 설치된 ChromeDriver 사용, 로컬에서는 자동 다운로드
            import os
            if os.path.exists('/usr/local/bin/chromedriver'):
                # Docker 환경 - 고정된 버전 사용
                service = Service('/usr/local/bin/chromedriver')
            else:
                # 로컬 개발 환경 - 자동 다운로드
                service = Service(ChromeDriverManager().install())
            browser = webdriver.Chrome(service=service, options=options)

            browser.get(Request_URL)

            def finds(css_selector):
                return browser.find_elements(By.CSS_SELECTOR, css_selector) # 여러개의 아이템을 찾을 때 사용

            def find(css_selector):
                return browser.find_element(By.CSS_SELECTOR, css_selector) # 한 개의 아이템을 찾을 때 사용

            def finds_xpath(xpath):
                return browser.find_elements(By.XPATH, xpath) # Xpath 찾을 떄 사용 (여러개)

            def find_xpath(xpath):
                return browser.find_element(By.XPATH, xpath) # Xpath 찾을 떄 사용 (한 개)

            input_id = find('input#mall_id') # 
            input_pw = find('input#userpasswd')

            pyperclip.copy(admin_id) # Copy - Control + c
            input_id.send_keys(Keys.CONTROL, "v") # Paste - Control + v

            pyperclip.copy(admin_pw) # Copy - Control + c
            input_pw.send_keys(Keys.CONTROL, "v") # Paste - Control + v
            input_pw.send_keys("\n") # Enter

            time.sleep(1.5) # 요소 생성까지 대기 시간

            # after_pw = find('a#iptBtnEm') # 비밀번호 다음에 변경하기 page
            after_pw = find_xpath('//*[@id="iptBtnEm"]')

            if after_pw: # 만일 '비밀번호 다음에 변경하기' 페이지가 나오면
                after_pw.click()
                browser.implicitly_wait(10)
                try :
                    find_xpath('/html/body/div/div[3]/button[2]').click()
                    time.sleep(4)
                    code_url = browser.current_url # 현재 URL 추출
                except :
                    code_url = browser.current_url # 현재 URL 추출
            else:
                code_url = browser.current_url # 현재 URL 추출
                
            browser.quit()

            return code_url


        # Access Token
        def get_cafe24_access(code_url):
            # 넣은 url에서 코드 따기
            code = code_url.split("=")[1].split("&")[0]

            # Authorization에 필요한 정보 base64 형식으로 인코딩
            origin_auth = f"{client_id}:{client_secret}"
            encode_bytes = origin_auth.encode('utf-8')
            encode_Data = base64.b64encode(encode_bytes)
            base64_String = encode_Data.decode('utf-8')

            # Access Token 요청하기
            access_url = f"https://{mall_id}.cafe24api.com/api/v2/oauth/token"
            payload = f'''grant_type=authorization_code&code={code}&redirect_uri={redirect_uri}'''
            access_headers = {
                'Authorization': f"Basic {base64_String}",
                'Content-Type': "application/x-www-form-urlencoded"
                }
            access_response = requests.request("POST", access_url, data=payload, headers=access_headers)
            access_token = json.loads(access_response.text)['access_token']

            return access_token


        # Category, Product, Coupon API 함수
        def get_cafe24_api_common_func(access_token, want_api, offset):
            api_url = f"https://{mall_id}.cafe24api.com/api/v2/admin/{want_api}"

            # header 및 param 설정
            api_headers = {
                'Authorization': f"Bearer {access_token}",
                'Content-Type': "application/json",
                }
            order_params = {
                'offset': offset,
                'limit': 100
            }
            api_response = requests.request("GET", api_url, headers=api_headers, params=order_params)
            api_json = json.loads(api_response.text)

            return api_json


        # Order API 함수
        def get_cafe24_order_api(access_token, start_date, end_date):
            api_url = f"https://{mall_id}.cafe24api.com/api/v2/admin/orders?embed=items,return,cancellation,exchange"

            # header 및 param 설정
            api_headers = {
                'Authorization': f"Bearer {access_token}",
                'Content-Type': "application/json",
                }
            order_params = {
                'start_date': str(start_date),
                'end_date': str(end_date),
                'limit': 1000
            }
            api_response = requests.request("GET", api_url, headers=api_headers, params=order_params)
            api_json = json.loads(api_response.text)

            return api_json


        # Categories API 추출
        def call_category_api():
            cate_code_url = get_cafe24_code(scope='mall.read_category')
            cate_access_token = get_cafe24_access(code_url=cate_code_url)
            cate_api = get_cafe24_api_common_func(access_token=cate_access_token, want_api='categories', offset=0)

            return cate_api


        # Products API 추출
        def call_product_api():
            prod_code_url = get_cafe24_code(scope='mall.read_product')
            prod_access_token = get_cafe24_access(code_url=prod_code_url)
            prod_api = get_cafe24_api_common_func(access_token=prod_access_token, want_api='products', offset=0)
            prod_api_2 = get_cafe24_api_common_func(access_token=prod_access_token, want_api='products', offset=100)

            for key, value in prod_api_2.items():
                if key in prod_api:
                    prod_api[key].extend(value)
                else:
                    prod_api[key] = value

            return prod_api, prod_access_token


        # Coupons API 추출
        def call_coupon_api():
            cou_code_url = get_cafe24_code(scope='mall.read_promotion')
            cou_access_token = get_cafe24_access(code_url=cou_code_url)
            cou_api = get_cafe24_api_common_func(access_token=cou_access_token, want_api='coupons', offset=0)

            return cou_api


        # Orders API 추출
        def call_order_api():
            # Order 기간 설정 (최대 3개월)
            # 1st period
            now = datetime.now()
            before = now - timedelta(days=89)

            use_now = str(now)[:10]
            use_before = str(before)[:10]

            # 2nd period
            sec_end = before - timedelta(days=1)
            sec_start = sec_end - timedelta(days=89)

            use_sec_end = str(sec_end)[:10]
            use_sec_start = str(sec_start)[:10]

            # 3rd period
            thr_end = sec_start - timedelta(days=1)
            thr_start = thr_end - timedelta(days=89)

            use_thr_end = str(thr_end)[:10]
            use_thr_start = str(thr_start)[:10]

            # 4th period
            for_end = thr_start - timedelta(days=1)
            for_start = for_end - timedelta(days=89)

            use_for_end = str(for_end)[:10]
            use_for_start = '2022-02-14'


            order_code_url = get_cafe24_code('mall.read_order')
            order_access_token = get_cafe24_access(order_code_url)
            order_api = get_cafe24_order_api(order_access_token, use_before, use_now)
            order_api_2 = get_cafe24_order_api(order_access_token, use_sec_start, use_sec_end)
            order_api_3 = get_cafe24_order_api(order_access_token, use_thr_start, use_thr_end)
            order_api_4 = get_cafe24_order_api(order_access_token, use_for_start, use_for_end)

            for key, value in order_api_2.items():
                if key in order_api:
                    order_api[key].extend(value)
                else:
                    order_api[key] = value

            for key, value in order_api_3.items():
                if key in order_api:
                    order_api[key].extend(value)
                else:
                    order_api[key] = value

            for key, value in order_api_4.items():
                if key in order_api:
                    order_api[key].extend(value)
                else:
                    order_api[key] = value

            return order_api
        
        prod_api, prod_access_token = call_product_api()

        total_api = call_category_api().copy()
        total_api.update(prod_api)
        total_api.update(call_order_api())
        total_api.update(call_coupon_api())

        return total_api, prod_access_token

    total_api, prod_access_token = call_total_api()

    # Category API to DF
    def category_api_to_df(total_api):
        category_no_list = []
        category_depth_list = []
        parent_category_no_list = []
        category_name_list = []
        display_type_list = []
        full_category_name_1_list = []
        full_category_name_2_list = []
        full_category_name_3_list = []
        full_category_name_4_list = []
        full_category_no_1_list = []
        full_category_no_2_list = []
        full_category_no_3_list = []
        full_category_no_4_list = []
        root_category_no_list = []
        use_main_list = []
        display_order_list = []

        for i in range(len(total_api['categories'])) :
            category_no = total_api['categories'][i]['category_no']
            category_depth = total_api['categories'][i]['category_depth']
            parent_category_no = total_api['categories'][i]['parent_category_no']
            category_name = total_api['categories'][i]['category_name']
            display_type = total_api['categories'][i]['display_type']
            full_category_name_1 = total_api['categories'][i]['full_category_name']['1']
            full_category_name_2 = total_api['categories'][i]['full_category_name']['2']
            full_category_name_3 = total_api['categories'][i]['full_category_name']['3']
            full_category_name_4 = total_api['categories'][i]['full_category_name']['4']
            full_category_no_1 = total_api['categories'][i]['full_category_no']['1']
            full_category_no_2 = total_api['categories'][i]['full_category_no']['2']
            full_category_no_3 = total_api['categories'][i]['full_category_no']['3']
            full_category_no_4 = total_api['categories'][i]['full_category_no']['4']
            root_category_no = total_api['categories'][i]['root_category_no']
            use_main = total_api['categories'][i]['use_main']
            display_order = total_api['categories'][i]['display_order']

            category_no_list.append(category_no)
            category_depth_list.append(category_depth)
            parent_category_no_list.append(parent_category_no)
            category_name_list.append(category_name)
            display_type_list.append(display_type)
            full_category_name_1_list.append(full_category_name_1)
            full_category_name_2_list.append(full_category_name_2)
            full_category_name_3_list.append(full_category_name_3)
            full_category_name_4_list.append(full_category_name_4)
            full_category_no_1_list.append(full_category_no_1)
            full_category_no_2_list.append(full_category_no_2)
            full_category_no_3_list.append(full_category_no_3)
            full_category_no_4_list.append(full_category_no_4)
            root_category_no_list.append(root_category_no)
            use_main_list.append(use_main)
            display_order_list.append(display_order)

        category_dic = {'category_no':category_no_list,
                'category_depth':category_depth_list,
                'parent_category_no':parent_category_no_list,
                'category_name':category_name_list,
                'display_type':display_type_list,
                'large_category':full_category_name_1_list,
                'mid_category':full_category_name_2_list,
                'small_category':full_category_name_3_list,
                'sub_category':full_category_name_4_list,
                'large_category_no':full_category_no_1_list,
                'mid_category_no':full_category_no_2_list,
                'small_category_no':full_category_no_3_list,
                'sub_category_no':full_category_no_4_list,
                'root_category_no':root_category_no_list,
                'use_main':use_main_list,
                'display_order':display_order_list}

        category_df = pd.DataFrame(category_dic)

        for i in range(7, 13):
            category_df['category_name'][i] = category_df['category_name'][i].split(") ")[1]
            category_df['small_category'][i] = category_df['small_category'][i].split(") ")[1]

        for i in [8,9,11,12]:
            category_df['sub_category'][i] = category_df['sub_category'][i].split(") ")[1]

        category_df[['mid_category_no', 'small_category_no', 'sub_category_no']] = category_df[['mid_category_no', 'small_category_no', 'sub_category_no']].fillna(0).astype('int').replace(0, None)       

        return category_df


    # Product API to DF
    def product_api_to_df(total_api):
        product_no_list = []
        product_code_list = []
        prod_category_no_list = []
        product_name_list = []
        price_excluding_tax_list = []
        price_list = []
        retail_price_list = []
        supply_price_list = []
        display_list = []
        selling_list = []
        product_condition_list = []
        created_date_list = []
        sold_out_list = []

        for i in range(len(total_api['products'])) :
            product_no = total_api['products'][i]['product_no']
            product_code = total_api['products'][i]['product_code']
            product_name = total_api['products'][i]['product_name']
            price_excluding_tax = total_api['products'][i]['price_excluding_tax']
            price = total_api['products'][i]['price']
            retail_price = total_api['products'][i]['retail_price']
            supply_price = total_api['products'][i]['supply_price']
            display = total_api['products'][i]['display']
            selling = total_api['products'][i]['selling']
            product_condition = total_api['products'][i]['product_condition']
            created_date = total_api['products'][i]['created_date'][:10]
            sold_out = total_api['products'][i]['sold_out']

            product_no_list.append(product_no)
            product_code_list.append(product_code)
            product_name_list.append(product_name)
            price_excluding_tax_list.append(price_excluding_tax)
            price_list.append(price)
            retail_price_list.append(retail_price)
            supply_price_list.append(supply_price)
            display_list.append(display)
            selling_list.append(selling)
            product_condition_list.append(product_condition)
            created_date_list.append(created_date)
            sold_out_list.append(sold_out)


        # Products API 함수
        def get_cafe24_api_product_func(access_token, number):
            api_url = f"https://{mall_id}.cafe24api.com/api/v2/admin/products/{number}"

            # header 및 param 설정
            api_headers = {
                'Authorization': f"Bearer {access_token}",
                'Content-Type': "application/json",
                }
            api_response = requests.request("GET", api_url, headers=api_headers)
            api_json = json.loads(api_response.text)

            return api_json

        for i in product_no_list :
            prod_category_no = get_cafe24_api_product_func(prod_access_token, i)['product']['category'][0]['category_no']
            prod_category_no_list.append(prod_category_no)
            time.sleep(0.5)

        product_dic = {'product_no':product_no_list,
            'product_code':product_code_list,
            'category_no':prod_category_no_list,
            'product_name':product_name_list, 
            'price_excluding_tax':price_excluding_tax_list, 
            'price':price_list,
            'retail_price':retail_price_list, 
            'supply_price':supply_price_list, 
            'display':display_list,
            'selling':selling_list, 
            'product_condition':product_condition_list, 
            'created_date':created_date_list, 
            'sold_out':sold_out_list}

        product_df = pd.DataFrame(product_dic)

        product_df[['price_excluding_tax', 'price', 'retail_price', 'supply_price']] = product_df[['price_excluding_tax', 'price', 'retail_price', 'supply_price']].astype('float').astype('int')

        return product_df


    # Order API to DF
    def order_api_to_df(total_api):
        order_id_list = []
        order_product_no_list = []
        order_product_code_list = []
        order_benefit_price_list = []
        member_id_list = []
        member_email_list = []
        billing_name_list = []
        payment_method_name_list = []
        paid_list = []
        canceled_list = []
        order_date_list = []
        first_order_list = []
        order_from_mobile_list = []
        initial_order_amount_list = []
        actual_order_amount_list = []
        payment_amount_list = []
        order_place_name_list = []
        quantity_list = []


        for i in range(len(total_api['orders'])) :
            order_id = total_api['orders'][i]['order_id']
            order_product_no = total_api['orders'][i]['items'][0]['product_no']
            order_product_code = total_api['orders'][i]['items'][0]['product_code']
            order_benefit_price = total_api['orders'][i]['actual_order_amount']['coupon_discount_price']
            member_id = total_api['orders'][i]['member_id']
            member_email = total_api['orders'][i]['member_email']
            billing_name = total_api['orders'][i]['billing_name']
            payment_method_name = total_api['orders'][i]['payment_method_name'][0]
            paid = total_api['orders'][i]['paid']
            canceled = total_api['orders'][i]['canceled']
            order_date = total_api['orders'][i]['order_date'][:10]
            first_order = total_api['orders'][i]['first_order']
            order_from_mobile = total_api['orders'][i]['order_from_mobile']
            initial_order_amount = total_api['orders'][i]['initial_order_amount']['order_price_amount']
            actual_order_amount = total_api['orders'][i]['actual_order_amount']['order_price_amount']
            payment_amount = total_api['orders'][i]['payment_amount']
            order_place_name = total_api['orders'][i]['order_place_name']
            quantity = total_api['orders'][i]['items'][0]['quantity']

            order_id_list.append(order_id)
            order_product_no_list.append(order_product_no)
            order_product_code_list.append(order_product_code)
            order_benefit_price_list.append(order_benefit_price)
            member_id_list.append(member_id)
            member_email_list.append(member_email)
            billing_name_list.append(billing_name)
            payment_method_name_list.append(payment_method_name)
            paid_list.append(paid)
            canceled_list.append(canceled)
            order_date_list.append(order_date)
            first_order_list.append(first_order)
            order_from_mobile_list.append(order_from_mobile)
            initial_order_amount_list.append(initial_order_amount)
            actual_order_amount_list.append(actual_order_amount)
            payment_amount_list.append(payment_amount)
            order_place_name_list.append(order_place_name)
            quantity_list.append(quantity)

        option_size_list = []
        option_color_list = []

        for i in range(len(total_api['orders'])) :
            if total_api['orders'][i]['items'][0]['options'][0]['option_name'] == '사이즈':
                option_size = total_api['orders'][i]['items'][0]['options'][0]['option_value']['option_text']
            else :
                option_color = total_api['orders'][i]['items'][0]['options'][0]['option_value']['option_text']

            if total_api['orders'][i]['items'][0]['options'][1]['option_name'] == '색상':
                option_color = total_api['orders'][i]['items'][0]['options'][1]['option_value']['option_text']
            else :
                option_size = total_api['orders'][i]['items'][0]['options'][1]['option_value']['option_text']

            option_size_list.append(option_size)
            option_color_list.append(option_color)

        order_dic = {'order_id':order_id_list,
            'product_no':order_product_no_list,
            'product_code':order_product_code_list,
            'benefit_price':order_benefit_price_list,
            'member_id':member_id_list,
            'member_email':member_email_list,
            'billing_name':billing_name_list,
            'payment_method_name':payment_method_name_list,
            'paid':paid_list,
            'canceled':canceled_list,
            'order_date':order_date_list,
            'first_order':first_order_list,
            'order_from_mobile':order_from_mobile_list,
            'initial_order_amount':initial_order_amount_list,
            'actual_order_amount':actual_order_amount_list,
            'payment_amount':payment_amount_list,
            'order_place_name':order_place_name_list,
            'quantity':quantity_list,
            'option_size':option_size_list,
            'option_color':option_color_list}

        order_df = pd.DataFrame(order_dic)

        order_df[['member_id', 'member_email']] = order_df[['member_id', 'member_email']].replace('', np.NaN)
        order_df[['benefit_price', 'initial_order_amount', 'actual_order_amount', 'payment_amount']] = order_df[['benefit_price', 'initial_order_amount', 'actual_order_amount', 'payment_amount']].astype('float').astype('int')

        return order_df


    # Coupon API to DF
    def coupon_api_to_df(total_api):
        coupon_no_list= []
        benefit_price_list= []
        coupon_type_list= []
        coupon_name_list= []
        created_date_list= []
        deleted_list= []
        benefit_text_list= []
        benefit_percentage_list= []
        issue_member_join_list= []
        issued_count_list= []

        for i in range(len(total_api['coupons'])) :
            coupon_no = total_api['coupons'][i]['coupon_no']
            benefit_price = total_api['coupons'][i]['benefit_price']
            coupon_type = total_api['coupons'][i]['coupon_type']
            coupon_name = total_api['coupons'][i]['coupon_name']
            created_date = total_api['coupons'][i]['created_date'][:10]
            deleted = total_api['coupons'][i]['deleted']
            benefit_text = total_api['coupons'][i]['benefit_text']
            benefit_percentage = total_api['coupons'][i]['benefit_percentage']
            issue_member_join = total_api['coupons'][i]['issue_member_join']
            issued_count = total_api['coupons'][i]['issued_count']

            coupon_no_list.append(coupon_no)
            benefit_price_list.append(benefit_price)
            coupon_type_list.append(coupon_type)
            coupon_name_list.append(coupon_name)
            created_date_list.append(created_date)
            deleted_list.append(deleted)
            benefit_text_list.append(benefit_text)
            benefit_percentage_list.append(benefit_percentage)
            issue_member_join_list.append(issue_member_join)
            issued_count_list.append(issued_count)

        coupon_dic = {'coupon_no':coupon_no_list,
            'benefit_price':benefit_price_list,
            'coupon_type':coupon_type_list,
            'coupon_name':coupon_name_list,
            'created_date':created_date_list,
            'deleted':deleted_list,
            'benefit_text':benefit_text_list,
            'benefit_percentage':benefit_percentage_list,
            'issue_member_join':issue_member_join_list,
            'issued_count':issued_count_list}

        coupon_df = pd.DataFrame(coupon_dic)

        coupon_df['benefit_price'] = coupon_df['benefit_price'].fillna(0).astype('float').astype('int').replace(0, None)

        return coupon_df
    
    category_df = category_api_to_df(total_api)    
    product_df = product_api_to_df(total_api)
    order_df = order_api_to_df(total_api)
    coupon_df = coupon_api_to_df(total_api)

    return category_df, product_df, order_df, coupon_df