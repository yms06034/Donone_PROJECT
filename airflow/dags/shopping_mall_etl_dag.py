from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.operators.subdag import SubDagOperator
from airflow.models import Variable
from airflow.hooks.base import BaseHook
from airflow.utils.task_group import TaskGroup
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import json
from functools import wraps

sys.path.insert(0, '/opt/airflow')
sys.path.insert(0, '/opt/airflow/cp2_don')
sys.path.insert(0, '/opt/airflow/don_home')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cp2_don.settings')

import django
django.setup()

from don_home.apis import ably, cafe24
from don_home.models import Ably_token, Cafe24, AblySalesInfo, AblyProductInfo
from don_home.models import Cafe24Product, Cafe24Order, NaverProductInfo, NaverSalesPerformance
from django.contrib.auth.models import User
import logging
import numpy as np

class StructuredLogger:
    """구조화된 로깅을 위한 커스텀 로거 클래스"""
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # JSON 형식의 로그 포맷
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
        )
        
        # 핸들러 설정 (중복 방지)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _format_message(self, message, **kwargs):
        """구조화된 메시지 포맷팅"""
        log_data = {
            "message": message,
            "context": kwargs
        }
        return json.dumps(log_data, ensure_ascii=False, default=str)
    
    def debug(self, message, **kwargs):
        self.logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message, **kwargs):
        self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message, **kwargs):
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message, **kwargs):
        self.logger.error(self._format_message(message, **kwargs))
    
    def critical(self, message, **kwargs):
        self.logger.critical(self._format_message(message, **kwargs))

# 로거 인스턴스 생성
logger = StructuredLogger('shopping_mall_etl')

def log_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        logger.debug(f"Function started: {func.__name__}", 
                    function=func.__name__, 
                    module=func.__module__,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys()))
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            logger.info(f"Function completed: {func.__name__}", 
                       function=func.__name__, 
                       duration_seconds=round(duration, 2),
                       status="success")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error(f"Function failed: {func.__name__}", 
                        function=func.__name__, 
                        duration_seconds=round(duration, 2),
                        status="failed",
                        error_message=str(e),
                        error_type=type(e).__name__,
                        traceback=True)
            raise
            
    return wrapper

# 동시 실행 제한
ABLY_SEMAPHORE = threading.Semaphore(10)
CAFE24_SEMAPHORE = threading.Semaphore(20)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 2, 10),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,  
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,  
    'max_retry_delay': timedelta(minutes=30),
    'email': ['admin@admin.com'],
}

dag = DAG(
    'shopping_mall_etl_pipeline_v2',
    default_args=default_args,
    description='쇼핑몰 데이터 수집 ETL 파이프라인 (로깅 강화 버전)',
    schedule_interval='0 8 * * *',
    catchup=False,
    tags=['etl', 'shopping_mall', 'ably', 'cafe24', 'naver', 'v2'],
)

@log_performance
def get_active_tokens():
    """활성화된 토큰 정보 조회"""
    logger.info("Starting token retrieval process")
    
    # Ably 토큰 조회
    ably_tokens = Ably_token.objects.select_related('user').all()
    ably_token_list = []
    
    logger.debug("Processing Ably tokens", count=ably_tokens.count())
    
    for token in ably_tokens:
        ably_token_list.append({
            'ably_user_id': token.user.id,
            'ably_id': token.ably_id,
            'ably_pw': token.ably_pw,
            'username': token.user.username
        })
        
        logger.debug("Ably token processed", 
                    user_id=token.user.id, 
                    username=token.user.username)
    
    # Cafe24 토큰 조회
    cafe24_tokens = Cafe24.objects.select_related('user').all()
    cafe24_token_list = []
    
    logger.debug("Processing Cafe24 tokens", count=cafe24_tokens.count())
    
    for token in cafe24_tokens:
        cafe24_token_list.append({
            'cafe24_user_id': token.user.id,
            'admin_id': token.cafe24_id,
            'admin_pw': token.cafe24_pw,
            'client_id': token.cafe24_clientid,
            'client_secret': token.cafe24_client_secret,
            'mall_id': token.cafe24_mallid,
            'encode_csrf_token': token.cafe24_encode_csrf_token,
            'redirect_uri': token.cafe24_redirect_uri,
            'username': token.user.username
        })
        
        logger.debug("Cafe24 token processed", 
                    user_id=token.user.id, 
                    mall_id=token.cafe24_mallid)
    
    logger.info("Token retrieval completed", 
               ably_count=len(ably_token_list), 
               cafe24_count=len(cafe24_token_list))
    
    return {
        'ably_tokens': ably_token_list,
        'cafe24_tokens': cafe24_token_list
    }

def extract_single_ably(token):
    """단일 Ably 계정 데이터 추출 (세마포어 사용)"""
    with ABLY_SEMAPHORE:
        try:
            logger.info("Starting Ably extraction", 
                       user_id=token['ably_user_id'],
                       username=token['username'])
            
            logger.debug("Waiting before crawling", wait_seconds=2)
            time.sleep(2)
            
            logger.debug("Starting Ably crawling", 
                        user_id=token['ably_user_id'])
            
            sales_df, products_df = ably.AblyDataInfo(
                token['ably_id'], 
                token['ably_pw']
            )
            
            logger.info("Ably extraction completed", 
                       user_id=token['ably_user_id'],
                       username=token['username'],
                       sales_count=len(sales_df),
                       products_count=len(products_df))
            
            return {
                'user_id': token['ably_user_id'],
                'sales_data': sales_df,
                'product_data': products_df,
                'username': token['username']
            }
            
        except Exception as e:
            logger.error("Ably extraction failed", 
                        user_id=token['ably_user_id'],
                        username=token['username'],
                        error=str(e),
                        error_type=type(e).__name__)
            return None

@log_performance
def extract_ably_data(ti, **context):
    """에이블리 데이터 추출 (병렬 처리)"""
    tokens_info = ti.xcom_pull(task_ids='get_tokens')
    ably_tokens = tokens_info['ably_tokens']
    
    if not ably_tokens:
        logger.warning("No Ably tokens found", task_id=context['task'].task_id)
        return []
    
    logger.info("Starting parallel Ably extraction", 
               token_count=len(ably_tokens),
               max_workers=10)
    
    extracted_data = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(extract_single_ably, token): token 
                   for token in ably_tokens}
        
        for future in as_completed(futures):
            token = futures[future]
            
            try:
                result = future.result()
                if result:
                    extracted_data.append(result)
                    logger.debug("Ably future completed", 
                               user_id=token['ably_user_id'],
                               status="success")
                else:
                    logger.warning("Ably future returned None", 
                                 user_id=token['ably_user_id'])
                    
            except Exception as e:
                logger.error("Ably future exception", 
                           user_id=token['ably_user_id'],
                           error=str(e))
    
    logger.info("Ably extraction completed", 
               total_tokens=len(ably_tokens),
               successful_extractions=len(extracted_data))
    
    return extracted_data

def extract_single_cafe24(token):
    """단일 Cafe24 쇼핑몰 데이터 추출 (세마포어 사용)"""
    with CAFE24_SEMAPHORE:
        try:
            logger.info("Starting Cafe24 extraction", 
                       user_id=token['cafe24_user_id'],
                       mall_id=token['mall_id'],
                       username=token['username'])
            
            logger.debug("Waiting before API call", wait_seconds=1)
            time.sleep(1)
            
            logger.debug("Starting Cafe24 API call", 
                        mall_id=token['mall_id'])
            
            category_df, product_df, order_df, coupon_df = cafe24.cafe24_df(
                token['admin_id'],
                token['admin_pw'],
                token['client_id'],
                token['client_secret'],
                token['mall_id'],
                token['encode_csrf_token'],
                token['redirect_uri']
            )
            
            logger.info("Cafe24 extraction completed", 
                       user_id=token['cafe24_user_id'],
                       mall_id=token['mall_id'],
                       categories_count=len(category_df),
                       products_count=len(product_df),
                       orders_count=len(order_df),
                       coupons_count=len(coupon_df))
            
            return {
                'user_id': token['cafe24_user_id'],
                'mall_id': token['mall_id'],
                'category_data': category_df,
                'product_data': product_df,
                'order_data': order_df,
                'coupon_data': coupon_df,
                'username': token['username']
            }
            
        except Exception as e:
            logger.error("Cafe24 extraction failed", 
                        user_id=token['cafe24_user_id'],
                        mall_id=token['mall_id'],
                        error=str(e),
                        error_type=type(e).__name__)
            return None

@log_performance
def extract_cafe24_data(ti, **context):
    """카페24 데이터 추출 (병렬 처리)"""
    tokens_info = ti.xcom_pull(task_ids='get_tokens')
    cafe24_tokens = tokens_info['cafe24_tokens']
    
    if not cafe24_tokens:
        logger.warning("No Cafe24 tokens found", task_id=context['task'].task_id)
        return []
    
    logger.info("Starting parallel Cafe24 extraction", 
               token_count=len(cafe24_tokens),
               max_workers=20)
    
    extracted_data = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(extract_single_cafe24, token): token 
                   for token in cafe24_tokens}
        
        for future in as_completed(futures):
            token = futures[future]
            
            try:
                result = future.result()
                if result:
                    extracted_data.append(result)
                    logger.debug("Cafe24 future completed", 
                               mall_id=token['mall_id'],
                               status="success")
                else:
                    logger.warning("Cafe24 future returned None", 
                                 mall_id=token['mall_id'])
                    
            except Exception as e:
                logger.error("Cafe24 future exception", 
                           mall_id=token['mall_id'],
                           error=str(e))
    
    logger.info("Cafe24 extraction completed", 
               total_tokens=len(cafe24_tokens),
               successful_extractions=len(extracted_data))
    
    return extracted_data

@log_performance
def transform_ably_data(ti, **context):
    """에이블리 데이터 변환"""
    raw_data = ti.xcom_pull(task_ids='extract_ably')
    
    logger.info("Starting Ably data transformation", 
               data_count=len(raw_data))
    
    transformed_data = []
    transform_errors = 0
    
    for idx, item in enumerate(raw_data):
        try:
            logger.debug("Transforming Ably data", 
                        index=idx,
                        user_id=item['user_id'])
            
            sales_df = item['sales_data']
            product_df = item['product_data']
            
            sales_df['user_id'] = item['user_id']
            product_df['user_id'] = item['user_id']
            
            transformed_data.append({
                'user_id': item['user_id'],
                'product_data': product_df,
                'sales_data': sales_df,
                'username': item.get('username', 'Unknown')
            })
            
            logger.debug("Ably data transformed", 
                        user_id=item['user_id'],
                        sales_rows=len(sales_df),
                        product_rows=len(product_df))
            
        except Exception as e:
            transform_errors += 1
            logger.error("Ably transformation error", 
                        index=idx,
                        user_id=item.get('user_id', 'Unknown'),
                        error=str(e))
            continue
    
    logger.info("Ably transformation completed", 
               total_items=len(raw_data),
               successful=len(transformed_data),
               errors=transform_errors)
    
    return transformed_data

@log_performance
def transform_cafe24_data(ti, **context):
    """카페24 데이터 변환"""
    raw_data = ti.xcom_pull(task_ids='extract_cafe24')
    
    logger.info("Starting Cafe24 data transformation", 
               data_count=len(raw_data))
    
    transformed_data = []
    transform_errors = 0
    
    for idx, item in enumerate(raw_data):
        try:
            logger.debug("Transforming Cafe24 data", 
                        index=idx,
                        mall_id=item['mall_id'])
            
            for df_name, df in [
                ('category', item['category_data']),
                ('product', item['product_data']),
                ('order', item['order_data']),
                ('coupon', item['coupon_data'])
            ]:
                df['user_id'] = item['user_id']
                df['mall_id'] = item['mall_id']
                
                logger.debug(f"Cafe24 {df_name} data processed", 
                           mall_id=item['mall_id'],
                           rows=len(df))
            
            transformed_data.append(item)
            
        except Exception as e:
            transform_errors += 1
            logger.error("Cafe24 transformation error", 
                        index=idx,
                        mall_id=item.get('mall_id', 'Unknown'),
                        error=str(e))
            continue
    
    logger.info("Cafe24 transformation completed", 
               total_items=len(raw_data),
               successful=len(transformed_data),
               errors=transform_errors)
    
    return transformed_data

@log_performance
def load_ably_data(ti, **context):
    """에이블리 데이터 로드"""
    transformed_data = ti.xcom_pull(task_ids='transform_ably')
    
    logger.info("Starting Ably data loading", 
               data_count=len(transformed_data))
    
    successful_loads = 0
    failed_loads = 0
    
    for item in transformed_data:
        try:
            user_id = item['user_id']
            username = item.get('username', 'Unknown')
            
            logger.debug("Loading Ably data", 
                        user_id=user_id,
                        username=username)
            
            deleted_products = AblyProductInfo.objects.filter(user_id=user_id).delete()
            deleted_sales = AblySalesInfo.objects.filter(user_id=user_id).delete()
            
            logger.debug("Existing data deleted", 
                        user_id=user_id,
                        deleted_products=deleted_products[0],
                        deleted_sales=deleted_sales[0])
            
            user = User.objects.get(id=user_id)
            
            product_count = 0
            for _, row in item['product_data'].iterrows():
                row_dict = row.to_dict()
                row_dict.pop('user_id', None)
                row_dict.pop('index', None)
                
                AblyProductInfo.objects.create(user=user, **row_dict)
                product_count += 1
            
            sales_count = 0
            for _, row in item['sales_data'].iterrows():
                row_dict = row.to_dict()
                row_dict.pop('user_id', None)
                row_dict.pop('index', None)
                
                if 'paymentDate' in row_dict and hasattr(row_dict['paymentDate'], 'strftime'):
                    row_dict['paymentDate'] = row_dict['paymentDate'].strftime('%Y-%m-%d %H:%M:%S')
                
                AblySalesInfo.objects.create(user=user, **row_dict)
                sales_count += 1
            
            successful_loads += 1
            
            logger.info("Ably data loaded successfully", 
                       user_id=user_id,
                       username=username,
                       products_loaded=product_count,
                       sales_loaded=sales_count)
            
        except Exception as e:
            failed_loads += 1
            logger.error("Ably data loading failed", 
                        user_id=item.get('user_id', 'Unknown'),
                        error=str(e),
                        error_type=type(e).__name__)
            continue
    
    logger.info("Ably loading completed", 
               total_users=len(transformed_data),
               successful=successful_loads,
               failed=failed_loads)

@log_performance
def load_cafe24_data(ti, **context):
    """카페24 데이터 로드"""
    transformed_data = ti.xcom_pull(task_ids='transform_cafe24')
    
    logger.info("Starting Cafe24 data loading", 
               data_count=len(transformed_data))
    
    successful_loads = 0
    failed_loads = 0
    
    for item in transformed_data:
        try:
            user_id = item['user_id']
            mall_id = item['mall_id']
            
            logger.debug("Loading Cafe24 data", 
                        user_id=user_id,
                        mall_id=mall_id)
            
            from don_home.models import Cafe24Category, Cafe24Coupon
            
            deleted_counts = {
                'categories': Cafe24Category.objects.filter(user_id=user_id).delete()[0],
                'products': Cafe24Product.objects.filter(user_id=user_id).delete()[0],
                'orders': Cafe24Order.objects.filter(user_id=user_id).delete()[0],
                'coupons': Cafe24Coupon.objects.filter(user_id=user_id).delete()[0]
            }
            
            logger.debug("Existing Cafe24 data deleted", 
                        user_id=user_id,
                        mall_id=mall_id,
                        **deleted_counts)
            
            user = User.objects.get(id=user_id)
            
            load_counts = {}
            
            for _, row in item['category_data'].iterrows():
                row_dict = row.to_dict()
                row_dict.pop('user_id', None)
                row_dict.pop('mall_id', None)
                Cafe24Category.objects.create(user_id=user_id, mall_id=mall_id, **row_dict)
            load_counts['categories'] = len(item['category_data'])
            
            for _, row in item['product_data'].iterrows():
                row_dict = row.to_dict()
                row_dict.pop('user_id', None)
                row_dict.pop('mall_id', None)
                Cafe24Product.objects.create(user_id=user_id, mall_id=mall_id, **row_dict)
            load_counts['products'] = len(item['product_data'])
            
            for _, row in item['order_data'].iterrows():
                row_dict = row.to_dict()
                row_dict.pop('user_id', None)
                row_dict.pop('mall_id', None)
                Cafe24Order.objects.create(user_id=user_id, mall_id=mall_id, **row_dict)
            load_counts['orders'] = len(item['order_data'])
            
            for _, row in item['coupon_data'].iterrows():
                row_dict = row.to_dict()
                row_dict.pop('user_id', None)
                row_dict.pop('mall_id', None)
                Cafe24Coupon.objects.create(user_id=user_id, mall_id=mall_id, **row_dict)
            load_counts['coupons'] = len(item['coupon_data'])
            
            successful_loads += 1
            
            logger.info("Cafe24 data loaded successfully", 
                       user_id=user_id,
                       mall_id=mall_id,
                       **load_counts)
            
        except Exception as e:
            failed_loads += 1
            logger.error("Cafe24 data loading failed", 
                        user_id=item.get('user_id', 'Unknown'),
                        mall_id=item.get('mall_id', 'Unknown'),
                        error=str(e),
                        error_type=type(e).__name__)
            continue
    
    logger.info("Cafe24 loading completed", 
               total_malls=len(transformed_data),
               successful=successful_loads,
               failed=failed_loads)

@log_performance
def data_quality_check(ti, **context):
    """데이터 품질 검증"""
    logger.info("Starting data quality check")
    
    from don_home.models import Cafe24Category, Cafe24Coupon
    
    counts = {
        'ably_products': AblyProductInfo.objects.count(),
        'ably_sales': AblySalesInfo.objects.count(),
        'cafe24_categories': Cafe24Category.objects.count(),
        'cafe24_products': Cafe24Product.objects.count(),
        'cafe24_orders': Cafe24Order.objects.count(),
        'cafe24_coupons': Cafe24Coupon.objects.count()
    }
    
    logger.info("Data counts retrieved", **counts)
    
    tokens_info = ti.xcom_pull(task_ids='get_tokens')
    
    user_stats = []
    
    for token in tokens_info['ably_tokens']:
        user_id = token['ably_user_id']
        username = token['username']
        
        stats = {
            'platform': 'ably',
            'user_id': user_id,
            'username': username,
            'products': AblyProductInfo.objects.filter(user_id=user_id).count(),
            'sales': AblySalesInfo.objects.filter(user_id=user_id).count()
        }
        
        user_stats.append(stats)
        
        logger.debug("Ably user stats", **stats)
    
    for token in tokens_info['cafe24_tokens']:
        user_id = token['cafe24_user_id']
        username = token['username']
        mall_id = token['mall_id']
        
        stats = {
            'platform': 'cafe24',
            'user_id': user_id,
            'username': username,
            'mall_id': mall_id,
            'products': Cafe24Product.objects.filter(user_id=user_id).count(),
            'orders': Cafe24Order.objects.filter(user_id=user_id).count()
        }
        
        user_stats.append(stats)
        
        logger.debug("Cafe24 user stats", **stats)
    
    # 데이터 품질 검증
    quality_issues = []
    
    if counts['ably_products'] == 0 and counts['cafe24_products'] == 0:
        quality_issues.append("No product data found across all platforms")
        logger.warning("No product data found")
    
    # 사용자별 데이터 누락 체크
    for stat in user_stats:
        if stat['platform'] == 'ably' and stat['products'] == 0:
            quality_issues.append(f"No products for Ably user {stat['username']}")
            logger.warning("No Ably products", user_id=stat['user_id'], username=stat['username'])
        
        if stat['platform'] == 'cafe24' and stat['products'] == 0:
            quality_issues.append(f"No products for Cafe24 mall {stat['mall_id']}")
            logger.warning("No Cafe24 products", user_id=stat['user_id'], mall_id=stat['mall_id'])
    
    result = {
        'total_counts': counts,
        'user_statistics': user_stats,
        'quality_issues': quality_issues,
        'check_passed': len(quality_issues) == 0
    }
    
    if result['check_passed']:
        logger.info("Data quality check passed", 
                   total_issues=0,
                   ably_products=counts['ably_products'],
                   cafe24_products=counts['cafe24_products'])
    else:
        logger.warning("Data quality check completed with issues", 
                      total_issues=len(quality_issues),
                      issues=quality_issues)
    
    return result

# Task 정의
start_task = DummyOperator(
    task_id='start',
    dag=dag,
)

get_tokens_task = PythonOperator(
    task_id='get_tokens',
    python_callable=get_active_tokens,
    retries=3,
    retry_delay=timedelta(minutes=1),
    dag=dag,
)

extract_ably_task = PythonOperator(
    task_id='extract_ably',
    python_callable=extract_ably_data,
    retries=3, 
    retry_delay=timedelta(minutes=5),
    retry_exponential_backoff=True,
    max_retry_delay=timedelta(minutes=30),
    dag=dag,
)

extract_cafe24_task = PythonOperator(
    task_id='extract_cafe24',
    python_callable=extract_cafe24_data,
    retries=3, 
    retry_delay=timedelta(minutes=2),
    retry_exponential_backoff=True,
    max_retry_delay=timedelta(minutes=20),
    dag=dag,
)

transform_ably_task = PythonOperator(
    task_id='transform_ably',
    python_callable=transform_ably_data,
    retries=1,  
    retry_delay=timedelta(minutes=2),
    dag=dag,
)

transform_cafe24_task = PythonOperator(
    task_id='transform_cafe24',
    python_callable=transform_cafe24_data,
    retries=1,  
    retry_delay=timedelta(minutes=2),
    dag=dag,
)

load_ably_task = PythonOperator(
    task_id='load_ably',
    python_callable=load_ably_data,
    retries=2,  
    retry_delay=timedelta(minutes=3),
    dag=dag,
)

load_cafe24_task = PythonOperator(
    task_id='load_cafe24',
    python_callable=load_cafe24_data,
    retries=2,  
    retry_delay=timedelta(minutes=3),
    dag=dag,
)

quality_check_task = PythonOperator(
    task_id='data_quality_check',
    python_callable=data_quality_check,
    retries=1,  
    retry_delay=timedelta(minutes=1),
    dag=dag,
)

end_task = DummyOperator(
    task_id='end',
    dag=dag,
)

start_task >> get_tokens_task

get_tokens_task >> [extract_ably_task, extract_cafe24_task]

extract_ably_task >> transform_ably_task >> load_ably_task
extract_cafe24_task >> transform_cafe24_task >> load_cafe24_task

[load_ably_task, load_cafe24_task] >> quality_check_task >> end_task