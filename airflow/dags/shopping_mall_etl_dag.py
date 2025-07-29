from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.models import Variable
from airflow.hooks.base import BaseHook
import sys
import os

sys.path.insert(0, '/opt/airflow')
sys.path.insert(0, '/opt/airflow/cp2_don')
sys.path.insert(0, '/opt/airflow/don_home')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cp2_don.settings')
import django
django.setup()

from don_home.apis import ably, cafe24
from don_home.models import Ably_token, Cafe24, AblySalesInfo, AblyProductInfo
from don_home.models import Cafe24Product, Cafe24Order, NaverProductInfo, NaverSalesPerformance
import logging


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 2, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email': ['yms06034@gmail.com'],
}

dag = DAG(
    'shopping_mall_etl_pipeline',
    default_args=default_args,
    description='쇼핑몰 데이터 수집 ETL 파이프라인',
    schedule_interval='0 8 * * *',
    catchup=False,
    tags=['etl', 'shopping_mall', 'ably', 'cafe24', 'naver'],
)

def get_active_tokens():
    """활성화된 토큰 정보 조회"""
    ably_tokens = Ably_token.objects.filter(ably_using=True).values()
    cafe24_tokens = Cafe24.objects.filter(cafe24_using=True).values()
    
    return {
        'ably_tokens': list(ably_tokens),
        'cafe24_tokens': list(cafe24_tokens)
    }

def extract_ably_data(**context):
    """에이블리 데이터 추출"""
    tokens_info = context['task_instance'].xcom_pull(task_ids='get_tokens')
    ably_tokens = tokens_info['ably_tokens']
    
    extracted_data = []
    for token in ably_tokens:
        try:
            logging.info(f"Extracting Ably data for user: {token['ably_user_id']}")
            
            # Ably 크롤링을 통한 데이터 수집
            # AblyDataInfo는 (sales_df, products_df) 튜플을 반환
            sales_df, products_df = ably.AblyDataInfo(
                token['ably_id'], 
                token['ably_pw']
            )
            
            extracted_data.append({
                'user_id': token['ably_user_id'],
                'sales_data': sales_df,
                'product_data': products_df
            })
            
        except Exception as e:
            logging.error(f"Error extracting Ably data for {token['ably_user_id']}: {str(e)}")
            continue
    
    return extracted_data

def extract_cafe24_data(**context):
    """카페24 데이터 추출"""
    tokens_info = context['task_instance'].xcom_pull(task_ids='get_tokens')
    cafe24_tokens = tokens_info['cafe24_tokens']
    
    extracted_data = []
    for token in cafe24_tokens:
        try:
            logging.info(f"Extracting Cafe24 data for mall: {token['mall_id']}")
            
            # Cafe24 API를 통한 데이터 수집
            # cafe24_df는 (category_df, product_df, order_df, coupon_df) 튜플을 반환
            category_df, product_df, order_df, coupon_df = cafe24.cafe24_df(
                token['admin_id'],
                token['admin_pw'],
                token['client_id'],
                token['client_secret'],
                token['mall_id'],
                token['encode_csrf_token'],
                token['redirect_uri']
            )
            
            extracted_data.append({
                'user_id': token['cafe24_user_id'],
                'mall_id': token['mall_id'],
                'category_data': category_df,
                'product_data': product_df,
                'order_data': order_df,
                'coupon_data': coupon_df
            })
            
        except Exception as e:
            logging.error(f"Error extracting Cafe24 data for {token['mall_id']}: {str(e)}")
            continue
    
    return extracted_data

def transform_ably_data(**context):
    """에이블리 데이터 변환"""
    raw_data = context['task_instance'].xcom_pull(task_ids='extract_ably')
    
    transformed_data = []
    for item in raw_data:
        try:
            sales_df = item['sales_data']
            product_df = item['product_data']
            
            # 데이터 변환은 이미 ably.py에서 수행됨
            # 추가 변환이 필요한 경우 여기서 수행
            
            # user_id 컬럼 추가
            sales_df['user_id'] = item['user_id']
            product_df['user_id'] = item['user_id']
            
            transformed_data.append({
                'user_id': item['user_id'],
                'product_data': product_df,
                'sales_data': sales_df
            })
            
        except Exception as e:
            logging.error(f"Error transforming Ably data: {str(e)}")
            continue
    
    return transformed_data

def transform_cafe24_data(**context):
    """카페24 데이터 변환"""
    raw_data = context['task_instance'].xcom_pull(task_ids='extract_cafe24')
    
    transformed_data = []
    for item in raw_data:
        try:
            # 각 데이터프레임에 user_id와 mall_id 추가
            category_df = item['category_data']
            product_df = item['product_data']
            order_df = item['order_data']
            coupon_df = item['coupon_data']
            
            # 메타데이터 추가
            for df in [category_df, product_df, order_df, coupon_df]:
                df['user_id'] = item['user_id']
                df['mall_id'] = item['mall_id']
            
            transformed_data.append({
                'user_id': item['user_id'],
                'mall_id': item['mall_id'],
                'category_data': category_df,
                'product_data': product_df,
                'order_data': order_df,
                'coupon_data': coupon_df
            })
            
        except Exception as e:
            logging.error(f"Error transforming Cafe24 data: {str(e)}")
            continue
    
    return transformed_data

def load_ably_data(**context):
    """에이블리 데이터 로드"""
    transformed_data = context['task_instance'].xcom_pull(task_ids='transform_ably')
    
    for item in transformed_data:
        try:
            user_id = item['user_id']
            product_data = item['product_data']
            sales_data = item['sales_data']
            
            # 기존 데이터 삭제 (오늘 날짜 기준)
            today = datetime.now().date()
            AblyProductInfo.objects.filter(
                user_id=user_id,
                created_at__date=today
            ).delete()
            
            AblySalesInfo.objects.filter(
                user_id=user_id,
                created_at__date=today
            ).delete()
            
            # 새 데이터 저장
            # 상품 정보 저장
            for _, row in product_data.iterrows():
                AblyProductInfo.objects.create(
                    user_id=user_id,
                    **row.to_dict()
                )
            
            # 판매 정보 저장
            for _, row in sales_data.iterrows():
                AblySalesInfo.objects.create(
                    user_id=user_id,
                    **row.to_dict()
                )
            
            logging.info(f"Successfully loaded Ably data for user: {user_id}")
            
        except Exception as e:
            logging.error(f"Error loading Ably data: {str(e)}")
            continue

def load_cafe24_data(**context):
    """카페24 데이터 로드"""
    transformed_data = context['task_instance'].xcom_pull(task_ids='transform_cafe24')
    
    for item in transformed_data:
        try:
            user_id = item['user_id']
            mall_id = item['mall_id']
            
            # 기존 데이터 삭제 (오늘 날짜 기준)
            today = datetime.now().date()
            
            # 모든 Cafe24 관련 테이블 정리
            from don_home.models import Cafe24Category, Cafe24Coupon
            
            Cafe24Category.objects.filter(
                mall_id=mall_id,
                created_at__date=today
            ).delete()
            
            Cafe24Product.objects.filter(
                mall_id=mall_id,
                created_at__date=today
            ).delete()
            
            Cafe24Order.objects.filter(
                mall_id=mall_id,
                created_at__date=today
            ).delete()
            
            Cafe24Coupon.objects.filter(
                mall_id=mall_id,
                created_at__date=today
            ).delete()
            
            # 새 데이터 저장
            # 카테고리 정보 저장
            for _, row in item['category_data'].iterrows():
                row_dict = row.to_dict()
                row_dict.pop('user_id', None)
                row_dict.pop('mall_id', None)
                Cafe24Category.objects.create(
                    user_id=user_id,
                    mall_id=mall_id,
                    **row_dict
                )
            
            # 상품 정보 저장
            for _, row in item['product_data'].iterrows():
                row_dict = row.to_dict()
                row_dict.pop('user_id', None)
                row_dict.pop('mall_id', None)
                Cafe24Product.objects.create(
                    user_id=user_id,
                    mall_id=mall_id,
                    **row_dict
                )
            
            # 주문 정보 저장
            for _, row in item['order_data'].iterrows():
                row_dict = row.to_dict()
                row_dict.pop('user_id', None)
                row_dict.pop('mall_id', None)
                Cafe24Order.objects.create(
                    user_id=user_id,
                    mall_id=mall_id,
                    **row_dict
                )
            
            # 쿠폰 정보 저장
            for _, row in item['coupon_data'].iterrows():
                row_dict = row.to_dict()
                row_dict.pop('user_id', None)
                row_dict.pop('mall_id', None)
                Cafe24Coupon.objects.create(
                    user_id=user_id,
                    mall_id=mall_id,
                    **row_dict
                )
            
            logging.info(f"Successfully loaded Cafe24 data for mall: {mall_id}")
            
        except Exception as e:
            logging.error(f"Error loading Cafe24 data: {str(e)}")
            continue

def data_quality_check(**context):
    """데이터 품질 검증"""
    today = datetime.now().date()
    
    from don_home.models import Cafe24Category, Cafe24Coupon
    
    # 에이블리 데이터 검증
    ably_product_count = AblyProductInfo.objects.filter(created_at__date=today).count()
    ably_sales_count = AblySalesInfo.objects.filter(created_at__date=today).count()
    
    # 카페24 데이터 검증
    cafe24_category_count = Cafe24Category.objects.filter(created_at__date=today).count()
    cafe24_product_count = Cafe24Product.objects.filter(created_at__date=today).count()
    cafe24_order_count = Cafe24Order.objects.filter(created_at__date=today).count()
    cafe24_coupon_count = Cafe24Coupon.objects.filter(created_at__date=today).count()
    
    logging.info(f"Data Quality Check - Today: {today}")
    logging.info(f"Ably - Products: {ably_product_count}, Sales: {ably_sales_count}")
    logging.info(f"Cafe24 - Categories: {cafe24_category_count}, Products: {cafe24_product_count}, Orders: {cafe24_order_count}, Coupons: {cafe24_coupon_count}")
    
    # 최소 데이터 검증
    if ably_product_count == 0 and cafe24_product_count == 0:
        raise ValueError("No data was loaded today. Please check the extraction process.")
    
    return {
        'ably': {'products': ably_product_count, 'sales': ably_sales_count},
        'cafe24': {
            'categories': cafe24_category_count,
            'products': cafe24_product_count, 
            'orders': cafe24_order_count,
            'coupons': cafe24_coupon_count
        }
    }

# Task 정의
start_task = DummyOperator(
    task_id='start',
    dag=dag,
)

get_tokens_task = PythonOperator(
    task_id='get_tokens',
    python_callable=get_active_tokens,
    dag=dag,
)

# Extract Tasks
extract_ably_task = PythonOperator(
    task_id='extract_ably',
    python_callable=extract_ably_data,
    dag=dag,
)

extract_cafe24_task = PythonOperator(
    task_id='extract_cafe24',
    python_callable=extract_cafe24_data,
    dag=dag,
)

# Transform Tasks
transform_ably_task = PythonOperator(
    task_id='transform_ably',
    python_callable=transform_ably_data,
    dag=dag,
)

transform_cafe24_task = PythonOperator(
    task_id='transform_cafe24',
    python_callable=transform_cafe24_data,
    dag=dag,
)

# Load Tasks
load_ably_task = PythonOperator(
    task_id='load_ably',
    python_callable=load_ably_data,
    dag=dag,
)

load_cafe24_task = PythonOperator(
    task_id='load_cafe24',
    python_callable=load_cafe24_data,
    dag=dag,
)

# Data Quality Check
quality_check_task = PythonOperator(
    task_id='data_quality_check',
    python_callable=data_quality_check,
    dag=dag,
)

end_task = DummyOperator(
    task_id='end',
    dag=dag,
)

# Task Dependencies
start_task >> get_tokens_task

get_tokens_task >> [extract_ably_task, extract_cafe24_task]

extract_ably_task >> transform_ably_task >> load_ably_task
extract_cafe24_task >> transform_cafe24_task >> load_cafe24_task

[load_ably_task, load_cafe24_task] >> quality_check_task >> end_task