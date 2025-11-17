# Selenium + Chrome 공식 이미지
FROM selenium/standalone-chrome:latest

# Python 설치
USER root
RUN apt-get update && apt-get install -y python3 python3-pip
WORKDIR /app

# Python 패키지 설치
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY . .

# 포트 노출
EXPOSE 5000

# 서버 실행
CMD ["python3", "server.py"]
