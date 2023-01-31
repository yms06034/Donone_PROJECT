import requests
import json
import base64
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import pyperclip
from datetime import datetime, timedelta

admin_id = ""
admin_pw = ""

client_id = ""
client_secret = ""
service_key = ""

mall_id = ""
encode_csrf_token = "" # 임의로 정하기
redirect_uri = ""


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

        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36")

        browser = webdriver.Chrome("./chromedriver.exe" ,options=options)

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
        api_url = f"https://{mall_id}.cafe24api.com/api/v2/admin/orders"

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

        return prod_api


    # Coupons API 추출
    def call_coupon_api():
        cou_code_url = get_cafe24_code(scope='mall.read_promotion')
        cou_access_token = get_cafe24_access(code_url=cou_code_url)
        cou_api = get_cafe24_api_common_func(access_token=cou_access_token, want_api='coupons', offset=0)

        return cou_api


    # Orders API 추출
    def call_order_api():
        # Order 기간 설정 (최대 3개월)
        now = datetime.now()
        before = now-timedelta(days=89)

        use_now = str(now)[:10]
        use_before = str(before)[:10]


        order_code_url = get_cafe24_code('mall.read_order')
        order_access_token = get_cafe24_access(order_code_url)
        order_api = get_cafe24_order_api(order_access_token, use_before, use_now)

        return order_api
    
    total_api = call_category_api().copy()
    total_api.update(call_product_api())
    total_api.update(call_order_api())
    total_api.update(call_coupon_api())

    return total_api