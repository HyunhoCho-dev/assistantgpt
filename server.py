from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import json
import traceback
import os
import re
import time
import base64

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

def get_chrome_driver():
    """Chrome 드라이버 생성"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1280,720')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

@app.route('/api/analyze', methods=['POST'])
def analyze_page():
    """페이지 구조 분석"""
    try:
        data = request.json
        url = data.get('url', '')
        
        if not url:
            return jsonify({'success': False, 'error': 'URL이 비어있습니다.'}), 400
        
        print(f"[페이지 분석] {url}")
        driver = get_chrome_driver()
        
        try:
            driver.get(url)
            time.sleep(2)
            
            title = driver.title
            current_url = driver.current_url
            
            elements_info = {'buttons': [], 'inputs': [], 'links': []}
            
            # 버튼 정보
            buttons = driver.find_elements(By.TAG_NAME, 'button')
            for btn in buttons[:10]:
                try:
                    elements_info['buttons'].append({
                        'text': btn.text.strip(),
                        'id': btn.get_attribute('id'),
                        'class': btn.get_attribute('class')
                    })
                except:
                    pass
            
            # 입력 필드
            inputs = driver.find_elements(By.TAG_NAME, 'input')
            for inp in inputs[:10]:
                try:
                    elements_info['inputs'].append({
                        'type': inp.get_attribute('type'),
                        'name': inp.get_attribute('name'),
                        'id': inp.get_attribute('id'),
                        'placeholder': inp.get_attribute('placeholder')
                    })
                except:
                    pass
            
            # 링크
            links = driver.find_elements(By.TAG_NAME, 'a')
            for link in links[:10]:
                try:
                    elements_info['links'].append({
                        'text': link.text.strip(),
                        'href': link.get_attribute('href'),
                        'id': link.get_attribute('id')
                    })
                except:
                    pass
            
            # 스크린샷
            screenshot = driver.get_screenshot_as_png()
            screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
            
            driver.quit()
            
            return jsonify({
                'success': True,
                'url': current_url,
                'title': title,
                'elements': elements_info,
                'screenshot': screenshot_base64
            })
            
        except Exception as e:
            driver.quit()
            raise e
            
    except Exception as e:
        print(f"[분석 오류] {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'분석 오류: {str(e)}'}), 500


@app.route('/api/browse', methods=['POST'])
def browse():
    """브라우저 자동화"""
    try:
        data = request.json
        goal = data.get('goal', '')
        selenium_code = data.get('code', '')
        
        if not goal:
            return jsonify({'success': False, 'error': '지시사항이 비어있습니다.'}), 400
        
        print(f"[사용자 지시] {goal}")
        if selenium_code:
            print(f"[AI 생성 코드]\n{selenium_code}")
        
        driver = get_chrome_driver()
        
        try:
            if selenium_code and selenium_code.strip():
                print("[브라우저] AI 생성 코드 실행...")
                
                execution_context = {
                    'driver': driver,
                    'By': By,
                    'WebDriverWait': WebDriverWait,
                    'EC': EC,
                    'time': time,
                    'print': print,
                }
                
                try:
                    exec(selenium_code, execution_context)
                except Exception as exec_error:
                    print(f"[코드 실행 오류] {str(exec_error)}")
                    driver.quit()
                    return jsonify({'success': False, 'error': f'코드 실행 오류: {str(exec_error)}'}), 500
            else:
                url_match = re.search(r'https?://[^\s]+', goal)
                if url_match:
                    url = url_match.group(0)
                    print(f"[브라우저] {url} 방문...")
                    driver.get(url)
                    time.sleep(2)
            
            current_url = driver.current_url
            title = driver.title
            
            driver.quit()
            
            return jsonify({
                'success': True,
                'result': f'완료! 현재 페이지: {title}',
                'url': current_url,
                'message': '브라우저 자동화 작업이 완료되었습니다.'
            })
        
        except Exception as e:
            driver.quit()
            raise e
    
    except Exception as e:
        print(f"[에러] {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'브라우저 자동화 오류: {str(e)}'}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Assistant GPT 서버 (Selenium) 실행 중'})


@app.route('/')
def serve_index():
    return send_file('index.html')


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Assistant GPT Python 서버 시작 (Selenium)")
    print("=" * 60)
    
    port = int(os.environ.get('PORT', 5000))
    is_production = os.environ.get('ENVIRONMENT') == 'production'
    
    print(f"📍 포트: {port}")
    print(f"🌍 모드: {'프로덕션' if is_production else '개발'}")
    print("💡 Selenium으로 브라우저 자동화 준비 완료")
    print("=" * 60)
    
    app.run(
        debug=not is_production,
        host='0.0.0.0',
        port=port,
        threaded=True
    )
