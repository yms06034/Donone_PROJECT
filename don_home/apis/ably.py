from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import time
import pyperclip
import pandas as pd

def AblyDataInfo(ably_id, ably_pw):
    # Options Setting
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('no-sandox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--start-maximized')
    options.add_argument('incognito')
    # options.add_argument('--headless')
    # Header Setting
    service = Service(ChromeDriverManager().install())
    browser = webdriver.Chrome(service=service, options=options)

    browser.get("https://my.a-bly.com/sales/order")

    def finds(css_selector):
        return browser.find_elements(By.CSS_SELECTOR, css_selector)

    def find(css_selector):
        return browser.find_element(By.CSS_SELECTOR, css_selector)

    def finds_xpath(xpath):
        return browser.find_elements(By.XPATH, xpath)

    def find_xpath(xpath):
        return browser.find_element(By.XPATH, xpath)


    input_id = find_xpath ('//*[@id="app"]/div[2]/form/div[3]/div/div/input')
    input_pw = find_xpath ('//*[@id="app"]/div[2]/form/div[4]/div/div/input')

    time.sleep(2)

    pyperclip.copy(ably_id) # Copy - Control + c
    input_id.send_keys(Keys.CONTROL, "v") # Paste - Control + v

    pyperclip.copy(ably_pw) # Copy - Control + c
    input_pw.send_keys(Keys.CONTROL, "v") # Paste - Control + v
    input_pw.send_keys("\n") # Enter

    time.sleep(2.5)

    total_date = find_xpath('//*[@id="app"]/div[2]/div[3]/section/div/div[1]/form/div[1]/div/div')
    total_date.click()

    time.sleep(0.5)

    last_year = find_xpath('/html/body/div[3]/div[1]/div[1]/button[3]')
    last_year.click()

    time.sleep(0.5)

    search_btn = find_xpath('//*[@id="app"]/div[2]/div[3]/section/div/div[1]/form/div[3]/div/button')
    search_btn.click()

    browser.implicitly_wait(10)

    count_sort = find_xpath('//*[@id="app"]/div[2]/div[3]/section/div/div[4]/div/div/span[2]/div/div/input')
    count_sort.click()

    sort_100 = find_xpath('/html/body/div[4]/div[1]/div[1]/ul/li[4]')
    sort_100.click()

    browser.implicitly_wait(10)

    right_btn = find_xpath('//*[@id="app"]/div[2]/div[3]/section/div/div[4]/div/div/button[2]')

    time.sleep(3)

    li_number = find_xpath('//*/div[2]/div[3]/section/div/div[4]/div/div/ul').text
    int(li_number[-1])

    if int(li_number[-1]) > 1:
        df = pd.read_html(browser.page_source)[1]
        for i in range(int(li_number[-1])):
            right_btn.click()
            df2 = pd.read_html(browser.page_source)[1]
            
            df = pd.concat([df, df2])
            time.sleep(3)
    else:
        df = pd.read_html(browser.page_source)[1]

    products_btn = find_xpath('//*[@id="app"]/div[2]/div[2]/div[1]/div/ul/div[3]/li/div/div')
    products_btn.click()

    pro_list = find_xpath('//*[@id="app"]/div[2]/div[2]/div[1]/div/ul/div[3]/li/ul/a[1]')
    pro_list.click()

    time.sleep(1.5)

    count_sort = find_xpath('//*[@id="app"]/div[2]/div[3]/section/div/div[4]/div/div/span[2]/div/div[1]/input')
    count_sort.click()

    time.sleep(0.5)

    sort_100 = find_xpath('/html/body/div[3]/div[1]/div[1]/ul/li[4]')
    sort_100.click()

    li_number = find_xpath('//*/div[2]/div[3]/section/div/div[4]/div/div/ul').text

    right_btn = find_xpath('//*[@id="app"]/div[2]/div[3]/section/div/div[4]/div/div/button[2]')

    if int(li_number[-1]) > 1:
        df_pro = pd.read_html(browser.page_source)[1]
        for i in range(int(li_number[-1])):
            right_btn.click()
            df_pro2 = pd.read_html(browser.page_source)[1]
            
            df_pro = pd.concat([df_pro, df_pro2])
            time.sleep(3)
    else:
        df_pro = pd.read_html(browser.page_source)[1]

    df.drop_duplicates(inplace=True)
    df.columns = ['paymentDate', 'productOrderNumber', 'orderNumber', 'productName', 'options', 'total', 'orderName', 'phoneNumber', 'orderStatus']    

    df_pro.drop_duplicates(inplace=True)
    df_pro = df_pro.drop(columns=[0, 2, 3, 4, 12], axis=1)
    df_pro.columns = ['productNumber', 'productName', 'price', 'discountPeriod', 'discountPrice', 'registrationDate', 'statusDisplay', 'stock', 'totalReview', 'parcel', 'returnShippingCost', 'extraShippingCost']
    
    df_pro['price'] = df_pro['price'].str.replace(',', '')
    df_pro['price'] = df_pro['price'].str.replace('원', '')
    df_pro['price'] = df_pro['price'].astype('int')

    df_pro['totalReview'] = df_pro['totalReview'].str.replace('개', '')
    df_pro['totalReview'] = df_pro['totalReview'].astype('int')
    
    df['paymentDate'] = pd.to_datetime(df['paymentDate'])

    df_pro['returnShippingCost'] = df_pro['returnShippingCost'].str.replace('원', '')
    df_pro['returnShippingCost'] = df_pro['returnShippingCost'].str.replace(',', '')
    df_pro['returnShippingCost'] = df_pro['returnShippingCost'].astype('int')

    df_pro['extraShippingCost'] = df_pro['extraShippingCost'].str.replace('원', '')
    df_pro['extraShippingCost'] = df_pro['extraShippingCost'].str.replace(',', '')
    df_pro['extraShippingCost'] = df_pro['extraShippingCost'].astype('int')

    df_pro['registrationDate'] = pd.to_datetime(df_pro['registrationDate'])
    df_pro.reset_index(inplace=True)

    return df, df_pro