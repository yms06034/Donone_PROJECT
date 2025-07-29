#!/bin/bash

echo "================================"
echo "Donone 프로젝트 통합 실행 스크립트"
echo "================================"
echo ""
echo "단일 Dockerfile과 docker-compose.yml로 통합 실행"
echo ""

# 환경 변수 설정
export AIRFLOW_UID=$(id -u)

# 기존 컨테이너 정리 (선택사항)
echo "기존 컨테이너 정리 중..."
docker-compose down

# 이미지 빌드
echo "Docker 이미지 빌드 중..."
docker-compose build

# Airflow 초기화
echo "Airflow 초기화 중..."
docker-compose up airflow-init

# 전체 서비스 실행
echo "전체 서비스 시작 중..."
docker-compose up -d

# 잠시 대기
echo "서비스가 시작되는 동안 잠시 기다려주세요..."
sleep 10

# 서비스 상태 확인
echo ""
echo "서비스 상태:"
docker-compose ps

echo ""
echo "================================"
echo "서비스 접속 정보:"
echo "================================"
echo "Django 웹 애플리케이션: http://localhost (Nginx를 통한 접속)"
echo "Django 직접 접속: http://localhost:8000"
echo "Airflow 웹 UI: http://localhost:8080"
echo "  - Username: airflow"
echo "  - Password: airflow"
echo ""
echo "로그 확인:"
echo "  - 전체 로그: docker-compose logs -f"
echo "  - Django 로그: docker-compose logs -f django"
echo "  - Airflow 로그: docker-compose logs -f airflow-scheduler"
echo ""
echo "서비스 중지:"
echo "  - docker-compose down"
echo "================================"