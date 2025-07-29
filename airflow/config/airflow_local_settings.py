"""
Airflow Local Settings
MySQL 연결 설정을 Django settings와 동일하게 구성
"""

from airflow.models import Connection
from airflow import settings
import os
import sys

# Django 설정 가져오기
sys.path.insert(0, '/opt/airflow')
sys.path.insert(0, '/opt/airflow/cp2_don')

from cp2_don import don_settings

def create_mysql_connection():
    """Django 설정과 동일한 MySQL 연결 생성"""
    new_conn = Connection(
        conn_id='donone_mysql',
        conn_type='mysql',
        host=don_settings.DATABASES['default']['HOST'],
        login=don_settings.DATABASES['default']['USER'],
        password=don_settings.DATABASES['default']['PASSWORD'],
        schema=don_settings.DATABASES['default']['NAME'],
        port=int(don_settings.DATABASES['default']['PORT'])
    )
    
    session = settings.Session()
    existing_conn = session.query(Connection).filter(Connection.conn_id == new_conn.conn_id).first()
    
    if existing_conn:
        session.delete(existing_conn)
    
    session.add(new_conn)
    session.commit()
    session.close()
    
    print(f"MySQL connection 'donone_mysql' created successfully")

# Airflow 시작 시 연결 생성
if __name__ == "__main__":
    create_mysql_connection()