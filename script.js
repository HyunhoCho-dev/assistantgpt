let apiKeySet = false;

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', function() {
    // API 키가 설정되어 있는지 확인
    checkApiKey();
    
    // textarea 자동 크기 조절
    const goalInput = document.getElementById('goalInput');
    goalInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });
});

// API 키 확인
function checkApiKey() {
    // 세션에 API 키가 있는지 확인하는 요청
    fetch('/api/set-api-key', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ api_key: sessionStorage.getItem('groq_api_key') || '' })
    })
    .then(response => {
        if (response.ok) {
            apiKeySet = true;
            document.getElementById('apiKeyModal').classList.add('hidden');
        } else {
            showApiKeyModal();
        }
    })
    .catch(error => {
        showApiKeyModal();
    });
}

// API 키 모달 표시
function showApiKeyModal() {
    document.getElementById('apiKeyModal').classList.remove('hidden');
}

// API 키 설정
function setApiKey() {
    const apiKey = document.getElementById('apiKeyInput').value.trim();
    
    if (!apiKey) {
        alert('Please enter a valid API key');
        return;
    }
    
    // API 키 저장
    sessionStorage.setItem('groq_api_key', apiKey);
    
    fetch('/api/set-api-key', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ api_key: apiKey })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            apiKeySet = true;
            document.getElementById('apiKeyModal').classList.add('hidden');
            showMessage('Welcome! You can now start giving me tasks.', 'agent');
        } else {
            alert('Failed to set API key');
        }
    })
    .catch(error => {
        alert('Error: ' + error.message);
    });
}

// 예제 프롬프트 사용
function useExample(text) {
    document.getElementById('goalInput').value = text;
    document.getElementById('welcomeScreen').classList.add('hidden');
    submitGoal();
}

// 새 채팅 시작
function newChat() {
    document.getElementById('messagesContainer').innerHTML = '';
    document.getElementById('welcomeScreen').classList.remove('hidden');
    document.getElementById('goalInput').value = '';
}

// 키 입력 처리
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        submitGoal();
    }
}

// 목표 제출
function submitGoal() {
    if (!apiKeySet) {
        showApiKeyModal();
        return;
    }
    
    const goalInput = document.getElementById('goalInput');
    const goal = goalInput.value.trim();
    
    if (!goal) {
        return;
    }
    
    // welcome 화면 숨기기
    document.getElementById('welcomeScreen').classList.add('hidden');
    
    // 사용자 메시지 표시
    showMessage(goal, 'user');
    
    // 입력 필드 초기화
    goalInput.value = '';
    goalInput.style.height = 'auto';
    
    // 전송 버튼 비활성화
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;
    
    // AI 응답 메시지 표시 (로딩 중)
    const agentMessageId = showMessage('Analyzing your request and planning steps...', 'agent', true);
    
    // 서버에 요청
    fetch('/api/execute-task', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ goal: goal })
    })
    .then(response => response.json())
    .then(data => {
        sendBtn.disabled = false;
        
        if (data.error) {
            updateMessage(agentMessageId, `Error: ${data.error}`, 'agent');
            return;
        }
        
        if (data.success) {
            // 계획 단계 표시
            let content = '<div class="message-text">I\'ve completed the task! Here\'s what I did:</div>';
            content += '<div class="execution-steps">';
            
            data.execution_log.forEach(step => {
                const statusClass = step.status;
                content += `
                    <div class="step-item ${statusClass}">
                        <div class="step-header">
                            <span>Step ${step.step}</span>
                            <span class="step-status ${statusClass}">${step.status}</span>
                        </div>
                        <div class="step-description">${step.description}</div>
                        ${step.result ? `<div class="step-result">${step.result}</div>` : ''}
                        ${step.error ? `<div class="step-result" style="color: #ef4444;">${step.error}</div>` : ''}
                    </div>
                `;
            });
            
            content += '</div>';
            updateMessage(agentMessageId, content, 'agent');
        }
    })
    .catch(error => {
        sendBtn.disabled = false;
        updateMessage(agentMessageId, `Error: ${error.message}`, 'agent');
    });
}

// 메시지 표시
function showMessage(content, type, isLoading = false) {
    const messagesContainer = document.getElementById('messagesContainer');
    const messageId = 'msg-' + Date.now();
    
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `message ${type}-message`;
    
    const avatar = type === 'user' ? 'You' : 'AI';
    const avatarBg = type === 'user' ? 'user' : 'agent';
    
    let messageContent = content;
    if (isLoading) {
        messageContent = `
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
    }
    
    messageDiv.innerHTML = `
        <div class="message-avatar ${avatarBg}-message">
            ${avatar.charAt(0)}
        </div>
        <div class="message-content">
            ${messageContent}
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageId;
}

// 메시지 업데이트
function updateMessage(messageId, content, type) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        const contentDiv = messageElement.querySelector('.message-content');
        contentDiv.innerHTML = content;
    }
    
    // 스크롤을 맨 아래로
    const messagesContainer = document.getElementById('messagesContainer');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 브라우저 세션 종료 (페이지를 떠날 때)
window.addEventListener('beforeunload', function() {
    fetch('/api/stop-browser', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    });
});
