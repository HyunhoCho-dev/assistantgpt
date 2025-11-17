# Microsoft Playwright 공식 이미지 사용 (Chromium 이미 설치됨)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 작업 디렉토리 설정
WORKDIR /app

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY . .

# 포트 노출
EXPOSE 5000

# Start Command는 Cloudtype 설정에서 지정
# CMD ["python", "server.py"]
