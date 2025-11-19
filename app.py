from flask import Flask, render_template, request, jsonify, session
from groq import Groq
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import time
import os
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)

# 활성화된 브라우저 인스턴스를 저장
active_browsers = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/set-api-key', methods=['POST'])
def set_api_key():
    """Groq API 키 설정"""
    data = request.get_json()
    api_key = data.get('api_key')
    
    if not api_key:
        return jsonify({'error': 'API key is required'}), 400
    
    # 세션에 API 키 저장
    session['groq_api_key'] = api_key
    session['session_id'] = str(uuid.uuid4())
    
    return jsonify({'message': 'API key set successfully', 'session_id': session['session_id']})

@app.route('/api/execute-task', methods=['POST'])
def execute_task():
    """사용자 목표를 받아 AI 에이전트가 실행"""
    data = request.get_json()
    user_goal = data.get('goal')
    
    if not user_goal:
        return jsonify({'error': 'Goal is required'}), 400
    
    # API 키 확인
    api_key = session.get('groq_api_key')
    if not api_key:
        return jsonify({'error': 'API key not set'}), 401
    
    session_id = session.get('session_id')
    
    try:
        # Groq 클라이언트 초기화
        client = Groq(api_key=api_key)
        
        # 1단계: 목표를 단계별로 분해
        planning_response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """You are an AI agent that breaks down user goals into specific, actionable steps for browser automation.
                    
                    Return ONLY a JSON object in this exact format:
                    {
                        "steps": [
                            {
                                "step_number": 1,
                                "description": "step description",
                                "action_type": "navigate|click|input|extract|wait",
                                "details": "specific details for this action"
                            }
                        ]
                    }
                    
                    Action types:
                    - navigate: Go to a URL
                    - click: Click on an element
                    - input: Type text into a field
                    - extract: Get information from the page
                    - wait: Wait for an element or condition
                    
                    Make the steps simple, clear, and executable."""
                },
                {
                    "role": "user",
                    "content": f"Break down this goal into browser automation steps: {user_goal}"
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=2000
        )
        
        # 응답에서 JSON 추출
        plan_text = planning_response.choices[0].message.content
        
        # JSON 추출 (마크다운 코드 블록 제거)
        if "```json" in plan_text:
            plan_text = plan_text.split("```json")[1].split("```")[0].strip()
        elif "```" in plan_text:
            plan_text = plan_text.split("```")[1].split("```")[0].strip()
        
        plan = json.loads(plan_text)
        steps = plan.get('steps', [])
        
        # 브라우저 초기화
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(options=chrome_options)
        active_browsers[session_id] = driver
        
        execution_log = []
        
        # 각 단계 실행
        for step in steps:
            step_num = step.get('step_number')
            description = step.get('description')
            action_type = step.get('action_type')
            details = step.get('details')
            
            execution_log.append({
                'step': step_num,
                'description': description,
                'status': 'executing'
            })
            
            try:
                if action_type == 'navigate':
                    # URL로 이동
                    url = details
                    driver.get(url)
                    time.sleep(2)
                    execution_log[-1]['status'] = 'completed'
                    execution_log[-1]['result'] = f'Navigated to {url}'
                
                elif action_type == 'click':
                    # AI에게 셀렉터 요청
                    selector_response = client.chat.completions.create(
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert at finding CSS selectors. Return ONLY the CSS selector string, nothing else."
                            },
                            {
                                "role": "user",
                                "content": f"What CSS selector should I use to find: {details}? Return only the selector."
                            }
                        ],
                        model="llama-3.3-70b-versatile",
                        temperature=0.1,
                        max_tokens=100
                    )
                    selector = selector_response.choices[0].message.content.strip()
                    
                    element = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    element.click()
                    time.sleep(1)
                    execution_log[-1]['status'] = 'completed'
                    execution_log[-1]['result'] = f'Clicked element: {selector}'
                
                elif action_type == 'input':
                    # 입력 필드와 텍스트 분리
                    parts = details.split('|')
                    if len(parts) == 2:
                        field_desc, text = parts
                        
                        selector_response = client.chat.completions.create(
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are an expert at finding CSS selectors. Return ONLY the CSS selector string, nothing else."
                                },
                                {
                                    "role": "user",
                                    "content": f"What CSS selector should I use to find: {field_desc}? Return only the selector."
                                }
                            ],
                            model="llama-3.3-70b-versatile",
                            temperature=0.1,
                            max_tokens=100
                        )
                        selector = selector_response.choices[0].message.content.strip()
                        
                        element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        element.clear()
                        element.send_keys(text)
                        time.sleep(1)
                        execution_log[-1]['status'] = 'completed'
                        execution_log[-1]['result'] = f'Entered text into {selector}'
                
                elif action_type == 'extract':
                    # 페이지에서 정보 추출
                    page_content = driver.page_source
                    
                    extract_response = client.chat.completions.create(
                        messages=[
                            {
                                "role": "system",
                                "content": "Extract the requested information from the HTML content. Be concise."
                            },
                            {
                                "role": "user",
                                "content": f"From this HTML, extract: {details}\n\nHTML: {page_content[:5000]}"
                            }
                        ],
                        model="llama-3.3-70b-versatile",
                        temperature=0.1,
                        max_tokens=500
                    )
                    extracted = extract_response.choices[0].message.content
                    execution_log[-1]['status'] = 'completed'
                    execution_log[-1]['result'] = extracted
                
                elif action_type == 'wait':
                    time.sleep(int(details))
                    execution_log[-1]['status'] = 'completed'
                    execution_log[-1]['result'] = f'Waited {details} seconds'
                
            except Exception as e:
                execution_log[-1]['status'] = 'failed'
                execution_log[-1]['error'] = str(e)
        
        # 최종 스크린샷
        screenshot_path = f'/tmp/screenshot_{session_id}.png'
        driver.save_screenshot(screenshot_path)
        
        return jsonify({
            'success': True,
            'plan': steps,
            'execution_log': execution_log,
            'message': 'Task execution completed'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop-browser', methods=['POST'])
def stop_browser():
    """브라우저 세션 종료"""
    session_id = session.get('session_id')
    
    if session_id and session_id in active_browsers:
        driver = active_browsers[session_id]
        driver.quit()
        del active_browsers[session_id]
        return jsonify({'message': 'Browser session stopped'})
    
    return jsonify({'message': 'No active browser session'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
