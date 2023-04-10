# ETL Project  (Airflow)
실제 쇼핑몰 데이터 Airflow를 활용해 Pipeline으로 처리한 프로젝트

## Description
프로젝트 기간 2023.01.18 ~ 2023.02.15 \
본 프로젝트는 실제 운영 되고 있는 쇼핑몰들의 데이터를 가져와 운영자가 한 눈에 볼 수 있게 끔 DashBorad를 보여줍니다.
-   기획 동기 및 의도
    -   데이터 분석 환경 구축의 필요성 → 데이터 분석을 통한 매출 증대 목표
        -   분산되어있는 데이터
        -   주요 지표 파악의 어려움
        -   고객 데이터 수집 불가
    -   데이터 파이프라인 구축
        -   분산되어있는 데이터를 하나의 DB에 적재한 뒤, 한 테이블에 플랫폼 별 주문 데이터 통합

## Service INFO
> 실제 기업의 각 플랫폼 별 데이터를 수집 및 분석하여 사업자가 활용할 수 있는 대시보드 제작 및 배포
- 데이터 
	- H-log 쇼핑몰의 각 플랫폼 별 데이터(cafe24, 스마트스토어, 에이블리)
	- 사용자의 로그분석을 위해 GA를 연동한 데이터
- USE TECH
	- Python, Django, Selenium, AWS, Tableau, Chart.js, Airflow

- 페이지 구현 영상



https://user-images.githubusercontent.com/98085184/230868655-d57ac5aa-4f2f-412e-abd7-accd443fceb0.mp4



## PIPELINE
![donone_pipeling](https://user-images.githubusercontent.com/98085184/230866641-feae6ecb-80ea-4509-8bea-e99c7b0466b2.png)

> Airflow 오케스트라 환경에서 API를 개발해 크롤링 진행 후 데이터 전처리 이후 RDS에 저장 해주었습니다.
## Environment

> Python Version 3.8 \
> Docker Mysql 8.1 \
> Django 3.2.3 \
> Airflow 2.3.1

## Troubleshooting
- 원래는 사이트에 접속해 버튼을 눌러 쇼핑몰 데이터를 최신화 시켜주는 방안으로 잡았는데
User가 20명이 동시 접속 해서 동시에 버튼을 눌러 보니 몇명의 사용자가 크롤링이 튕기는 현상이 발생했다.
- 하나의 토큰 값으로 크롤링으로 동시에 20개가 돌아가다 보니 크롤링 서버에서 오류가 발생한 것 같았다.
	- 차라리 Airflow를 사용해 데이터는 매일 아침 6시에 최신화 시켜주어 안정화가 되었다.


## RETROSPECTIVE
- 네이버 스마트스토어, Cafe24의 경우 API가 굉장히 불친절 하고 API를 사용할 때마다 새로운 토큰을 발급 받아 사용해야 한다. 
그 부분의 코드를 짜는데 시간이 생각보다 오래 걸렸다.
- 그리고 트러블 슈팅을 해결하면서 사용한 Airflow를 활용한 부분이 개인적으로 너무 마음에 들었다.
- 또한 실제 운영중인 쇼핑몰데이터를 활용한 부분도 굉장히 좋았다.
