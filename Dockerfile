FROM python:3.8-slim as base

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Chrome 설치 (Selenium용)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ChromeDriver 설치
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | awk -F. '{print $1}') \
    && wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

# Django 앱용 이미지
FROM base as django

WORKDIR /app

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY . .

# Static 파일 디렉토리 생성
RUN mkdir -p /app/staticfiles /app/media

# entrypoint 스크립트 실행 권한
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "cp2_don.wsgi:application"]

# Airflow용 이미지
FROM apache/airflow:2.3.1 as airflow

USER root

# Chrome과 ChromeDriver 복사
COPY --from=base /usr/bin/google-chrome /usr/bin/google-chrome
COPY --from=base /usr/local/bin/chromedriver /usr/local/bin/chromedriver
COPY --from=base /opt/google/chrome /opt/google/chrome

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Django 프로젝트 복사 (requirements.txt 포함)
COPY --from=django /app /app

# Python 패키지 설치 (Django requirements.txt 사용)
RUN pip install --no-cache-dir -r /app/requirements.txt