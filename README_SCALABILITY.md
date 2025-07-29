# 확장성 및 미완성 작업 안내

## 현재 구현 상태

### 동시 실행 제한
- **Ably 크롤링**: 최대 10개 동시 실행
- **Cafe24 API**: 최대 20개 동시 실행

### 예상 처리 시간 (100명 기준)
- **Ably**: 
  - 크롤링 시간: 약 30초/건
  - 총 시간: (100 / 10) * 30초 = 약 5분
- **Cafe24**:
  - API 처리 시간: 약 10초/건  
  - 총 시간: (100 / 20) * 10초 = 약 50초

## 대규모 사용자 대응 방안 (미구현)

### 1. 분산 큐 시스템 도입
```python
# Celery + Redis를 사용한 분산 처리 예시
from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379')

@app.task
def crawl_ably_async(user_token):
    # 개별 크롤링 작업
    pass

# DAG에서 Celery 작업 호출
for token in ably_tokens:
    crawl_ably_async.delay(token)
```

### 2. 사용자별 스케줄링
```python
# 사용자를 시간대별로 분산
def schedule_by_user_group():
    users = User.objects.all()
    groups = {
        '0-6시': users.filter(id__mod=4 == 0),
        '6-12시': users.filter(id__mod=4 == 1),
        '12-18시': users.filter(id__mod=4 == 2),
        '18-24시': users.filter(id__mod=4 == 3),
    }
    return groups
```

### 3. 크롤링 서버 분리
```yaml
# docker-compose에 크롤링 전용 서비스 추가
services:
  crawler-1:
    image: crawler:latest
    environment:
      - WORKER_ID=1
      - MAX_CONCURRENT=20
  
  crawler-2:
    image: crawler:latest
    environment:
      - WORKER_ID=2
      - MAX_CONCURRENT=20
```

### 4. 우선순위 큐
```python
# 유료/무료 사용자 구분
class CrawlingPriority:
    HIGH = 1    # 유료 사용자
    MEDIUM = 2  # 활성 무료 사용자
    LOW = 3     # 비활성 사용자

def get_user_priority(user):
    if user.subscription == 'premium':
        return CrawlingPriority.HIGH
    elif user.last_login > datetime.now() - timedelta(days=7):
        return CrawlingPriority.MEDIUM
    return CrawlingPriority.LOW
```

### 5. 실시간 모니터링
```python
# Prometheus + Grafana 연동
from prometheus_client import Counter, Histogram

crawling_counter = Counter('crawling_total', 'Total crawling attempts')
crawling_duration = Histogram('crawling_duration_seconds', 'Crawling duration')

@crawling_duration.time()
def monitored_crawling(token):
    crawling_counter.inc()
    return extract_single_ably(token)
```

## 권장 아키텍처 (1000+ 사용자)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Airflow   │────▶│    Redis    │────▶│   Celery    │
│  Scheduler  │     │    Queue    │     │  Workers    │
└─────────────┘     └─────────────┘     └─────────────┘
                            │                    │
                            ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Priority   │     │  Crawler    │
                    │   Queue     │     │  Instances  │
                    └─────────────┘     └─────────────┘
```

## 현재 제약사항

1. **서버 리소스**: 단일 서버에서 실행 시 CPU/메모리 한계
2. **Chrome 인스턴스**: 동시에 많은 Chrome 실행 시 불안정
3. **IP 차단**: 동일 IP에서 대량 크롤링 시 차단 위험
4. **데이터베이스 병목**: 동시 쓰기 작업 시 락 발생 가능

## 임시 해결 방안

사용자가 급증할 경우:
1. DAG 실행 주기를 여러 시간대로 분산
2. 동시 실행 수를 서버 상황에 맞게 조절
3. 크롤링 간격을 늘려 안정성 확보
4. 중요 사용자 우선 처리