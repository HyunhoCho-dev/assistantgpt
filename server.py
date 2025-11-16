from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from playwright.sync_api import sync_playwright
import json
import traceback
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # 크로스 오리진 요청 허용 (HTML에서 서버로 요청할 때 필요)

@app.route('/api/browse', methods=['POST'])
def browse():
    """
    브라우저 자동화 엔드포인트 - 사용자 지정 작업 수행
    요청: { "goal": "사용자 지시사항" }
    응답: { "success": true/false, "result": "...", "error": "..." }
    """
    try:
        data = request.json
        goal = data.get('goal', '')
        
        if not goal:
            return jsonify({
                'success': False,
                'error': '지시사항이 비어있습니다.'
            }), 400
        
        print(f"[사용자 지시] {goal}")
        
        # Playwright로 자동화 시작
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # 브라우저 창 표시
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 720})
            
            try:
                # 사용자 지시사항 파싱
                goal_lower = goal.lower()
                
                # 1. URL 직접 방문 감지
                if goal_lower.startswith('http://') or goal_lower.startswith('https://'):
                    url = goal.split()[0]  # 첫 번째 단어가 URL
                    print(f"[브라우저] {url} 방문...")
                    page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    page.wait_for_timeout(2000)
                
                # 2. terriotorial (territorial) 사이트 감지
                elif 'territor' in goal_lower and '들어' in goal:
                    print(f"[브라우저] Territorial 사이트 방문...")
                    page.goto('https://www.territorial.io', wait_until='domcontentloaded', timeout=30000)
                    page.wait_for_timeout(3000)
                    
                    # 닉네임 입력 찾기 (다양한 선택자 시도)
                    if '닉네임' in goal or 'nick' in goal_lower:
                        nickname_part = goal.split('닉네임')[-1].split('라고')[-1].split('입력')[0].strip()
                        
                        nickname_selectors = [
                            'input[placeholder*="nickname"]',
                            'input[placeholder*="이름"]',
                            'input[id*="nickname"]',
                            'input[id*="name"]',
                            'input[type="text"]:first-child',
                            'input.nickname-input'
                        ]
                        
                        print(f"[브라우저] 닉네임 입력 필드 찾기: {nickname_part}")
                        
                        for selector in nickname_selectors:
                            try:
                                if page.locator(selector).count() > 0:
                                    print(f"[브라우저] 닉네임 필드 발견: {selector}")
                                    page.fill(selector, nickname_part)
                                    page.wait_for_timeout(500)
                                    break
                            except:
                                continue
                    
                    # 배틀로얄 버튼/링크 찾기
                    if '배틀' in goal or 'battle' in goal_lower:
                        print(f"[브라우저] 배틀로얄 메뉴 찾기...")
                        
                        battle_selectors = [
                            'button:has-text("배틀로얄")',
                            'a:has-text("배틀로얄")',
                            'button:has-text("Battle Royal")',
                            'button:has-text("배틀")',
                            'div[class*="battle"]',
                            'button[class*="battle"]'
                        ]
                        
                        for selector in battle_selectors:
                            try:
                                if page.locator(selector).count() > 0:
                                    print(f"[브라우저] 배틀 옵션 발견: {selector}")
                                    page.locator(selector).first.click()
                                    page.wait_for_timeout(2000)
                                    break
                            except:
                                continue
                
                # 3. 일반 텍스트 입력 지시사항 처리
                else:
                    print(f"[브라우저] 일반 지시사항 처리...")
                    
                    # "입력" 또는 "친" 키워드 찾기
                    if '입력' in goal or '친' in goal or '쓰' in goal:
                        # 입력할 텍스트 추출
                        parts = goal.split('라고')
                        if len(parts) > 1:
                            text_to_input = parts[0].split('친')[-1].split('입력')[-1].strip()
                            
                            # 첫 번째 입력 필드에 텍스트 입력
                            print(f"[브라우저] '{text_to_input}' 입력 시도...")
                            inputs = page.locator('input[type="text"]')
                            if inputs.count() > 0:
                                inputs.first.fill(text_to_input)
                                page.wait_for_timeout(500)
                    
                    # "클릭" 키워드 찾기
                    if '클릭' in goal or '누르' in goal or '들어' in goal:
                        # 버튼 또는 링크 클릭
                        for word in goal.split():
                            try:
                                buttons = page.locator(f'button:has-text("{word}")')
                                if buttons.count() > 0:
                                    print(f"[브라우저] '{word}' 버튼 클릭...")
                                    buttons.first.click()
                                    page.wait_for_timeout(1500)
                                    break
                            except:
                                pass
                
                # 최종 상태 대기
                page.wait_for_timeout(2000)
                
                # 현재 URL과 제목 반환
                current_url = page.url
                title = page.title()
                
                browser.close()
                
                return jsonify({
                    'success': True,
                    'result': f'완료! 현재 페이지: {title}',
                    'url': current_url,
                    'message': '브라우저 자동화 작업이 완료되었습니다.'
                })
            
            except Exception as e:
                browser.close()
                raise e
    
    except Exception as e:
        print(f"[에러] {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'브라우저 자동화 오류: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """서버 상태 확인"""
    return jsonify({'status': 'ok', 'message': 'Assistant GPT 서버가 실행 중입니다.'})


@app.route('/')
def serve_index():
    """HTML 파일 제공"""
    return send_file('index.html')


@app.route('/<path:path>')
def serve_static(path):
    """정적 파일 제공 (CSS, JS, 이미지 등)"""
    return send_from_directory('.', path)


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Assistant GPT Python 서버 시작")
    print("=" * 60)
    print("📍 http://localhost:5000 에서 실행 중...")
    print("💡 Playwright로 브라우저 자동화 준비 완료")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
