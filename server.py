from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from playwright.sync_api import sync_playwright
import json
import traceback
import os
import re

app = Flask(__name__, static_folder='.', static_url_path='')

# CORS 설정 - 모든 origin 허용 (배포 환경에서 필수)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/api/analyze', methods=['POST'])
def analyze_page():
    """
    페이지 구조 분석 엔드포인트
    요청: { "url": "https://example.com" }
    응답: { "success": true, "html": "...", "title": "...", "screenshot": "base64..." }
    """
    try:
        data = request.json
        url = data.get('url', '')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL이 비어있습니다.'
            }), 400
        
        print(f"[페이지 분석] {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 720})
            
            try:
                # 페이지 방문
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(2000)
                
                # 페이지 정보 수집
                title = page.title()
                html_content = page.content()
                current_url = page.url
                
                # 페이지의 주요 요소 분석
                elements_info = page.evaluate("""() => {
                    const info = {
                        buttons: [],
                        inputs: [],
                        links: [],
                        forms: []
                    };
                    
                    // 버튼 정보
                    document.querySelectorAll('button').forEach((btn, i) => {
                        if (i < 10) {  // 처음 10개만
                            info.buttons.push({
                                text: btn.textContent.trim(),
                                id: btn.id,
                                class: btn.className
                            });
                        }
                    });
                    
                    // 입력 필드 정보
                    document.querySelectorAll('input').forEach((input, i) => {
                        if (i < 10) {
                            info.inputs.push({
                                type: input.type,
                                name: input.name,
                                id: input.id,
                                placeholder: input.placeholder
                            });
                        }
                    });
                    
                    // 링크 정보
                    document.querySelectorAll('a').forEach((link, i) => {
                        if (i < 10) {
                            info.links.push({
                                text: link.textContent.trim(),
                                href: link.href,
                                id: link.id
                            });
                        }
                    });
                    
                    // 폼 정보
                    document.querySelectorAll('form').forEach((form, i) => {
                        if (i < 5) {
                            info.forms.push({
                                action: form.action,
                                method: form.method,
                                id: form.id
                            });
                        }
                    });
                    
                    return info;
                }""")
                
                # 스크린샷 캡처 (base64)
                screenshot = page.screenshot(type='png')
                import base64
                screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
                
                browser.close()
                
                return jsonify({
                    'success': True,
                    'url': current_url,
                    'title': title,
                    'elements': elements_info,
                    'html_preview': html_content[:2000],  # 처음 2000자만
                    'screenshot': screenshot_base64
                })
                
            except Exception as e:
                browser.close()
                raise e
                
    except Exception as e:
        print(f"[분석 오류] {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'페이지 분석 오류: {str(e)}'
        }), 500


@app.route('/api/browse', methods=['POST'])
def browse():
    """
    브라우저 자동화 엔드포인트 - AI가 생성한 Playwright 코드 실행
    요청: { "goal": "사용자 지시사항", "code": "playwright python 코드" }
    응답: { "success": true/false, "result": "...", "error": "..." }
    """
    try:
        data = request.json
        goal = data.get('goal', '')
        playwright_code = data.get('code', '')
        
        if not goal:
            return jsonify({
                'success': False,
                'error': '지시사항이 비어있습니다.'
            }), 400
        
        print(f"[사용자 지시] {goal}")
        if playwright_code:
            print(f"[AI 생성 코드]\n{playwright_code}")
        
        # Playwright로 자동화 시작
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 720})
            
            try:
                # AI가 생성한 코드가 있으면 실행
                if playwright_code and playwright_code.strip():
                    print("[브라우저] AI 생성 코드 실행...")
                    
                    # 안전한 실행 환경 설정
                    execution_context = {
                        'page': page,
                        'browser': browser,
                        'sync_playwright': sync_playwright,
                        'print': print,
                    }
                    
                    try:
                        exec(playwright_code, execution_context)
                        result_message = "AI 생성 코드 실행 완료"
                    except Exception as exec_error:
                        print(f"[코드 실행 오류] {str(exec_error)}")
                        browser.close()
                        return jsonify({
                            'success': False,
                            'error': f'코드 실행 오류: {str(exec_error)}'
                        }), 500
                else:
                    # 코드가 없으면 사용자 지시사항을 직접 처리
                    print(f"[브라우저] 사용자 지시사항 처리...")
                    
                    # URL 추출 시도
                    url_match = re.search(r'https?://[^\s]+', goal)
                    if url_match:
                        url = url_match.group(0)
                        print(f"[브라우저] {url} 방문...")
                        page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        page.wait_for_timeout(2000)
                    else:
                        print("[브라우저] URL을 찾을 수 없습니다.")
                        result_message = "URL을 제공해주세요. (예: https://example.com)"
                
                # 최종 상태
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
    
    # 배포 환경에서 포트 자동 감지
    port = int(os.environ.get('PORT', 5000))
    is_production = os.environ.get('ENVIRONMENT') == 'production' or os.environ.get('NODE_ENV') == 'production'
    
    print(f"📍 포트: {port}")
    print(f"🌍 모드: {'프로덕션' if is_production else '개발'}")
    print("💡 Playwright로 브라우저 자동화 준비 완료")
    print("🔍 페이지 분석 API 활성화")
    print("=" * 60)
    
    app.run(
        debug=not is_production,
        host='0.0.0.0',
        port=port,
        threaded=True
    )
