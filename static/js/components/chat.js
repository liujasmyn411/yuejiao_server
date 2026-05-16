/**
 * 聊天浮窗组件
 */
const ChatWidget = (() => {
  let agentType = 'customer'; // customer | enterprise | student
  let currentUserId = null;

  function init() {
    const toggle = document.getElementById('chat-toggle');
    const close = document.getElementById('chat-close');
    const minimize = document.getElementById('chat-minimize');
    const send = document.getElementById('chat-send');
    const input = document.getElementById('chat-input');
    const widget = document.getElementById('chat-widget');

    toggle.onclick = () => {
      widget.classList.remove('hidden');
      toggle.classList.add('hidden');
    };
    close.onclick = () => {
      widget.classList.add('hidden');
      toggle.classList.remove('hidden');
    };
    minimize.onclick = () => {
      widget.classList.toggle('chat-widget--minimized');
    };
    send.onclick = sendMessage;
    input.onkeydown = (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    };
  }

  function setAgent(type, userId) {
    agentType = type;
    currentUserId = userId;
    const titles = { customer: '客服助手', enterprise: '企业助手', student: '学生助手' };
    document.getElementById('chat-title').textContent = titles[type] || 'AI 助手';
  }

  async function sendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;

    appendMessage('user', text);
    input.value = '';
    input.style.height = 'auto';

    appendMessage('assistant', '<span class="typing">正在思考...</span>');

    try {
      let endpoint = '';
      let body = { message: text };

      if (agentType === 'enterprise') {
        endpoint = '/api/enterprise/chat';
      } else if (agentType === 'student') {
        endpoint = '/api/student/chat';
        body.student_id = currentUserId;
      } else {
        endpoint = '/api/customer/chat';
      }

      const data = await API.post(endpoint, body);
      // 移除 typing
      const msgs = document.getElementById('chat-messages');
      msgs.removeChild(msgs.lastChild);

      // 渲染回复
      appendMessage('assistant', formatReply(data));
    } catch (err) {
      const msgs = document.getElementById('chat-messages');
      msgs.removeChild(msgs.lastChild);
      appendMessage('assistant', `<span class="text-error">请求失败: ${err.message}</span>`);
    }
  }

  function appendMessage(role, html) {
    const msgs = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `chat-msg chat-msg--${role}`;
    div.innerHTML = html;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function formatReply(data) {
    if (data.message) return escapeHtml(data.message);
    if (data.response) return escapeHtml(data.response);
    if (data.reply) return escapeHtml(data.reply);
    // JSON 美化
    const str = JSON.stringify(data, null, 2);
    return `<pre class="chat-json">${escapeHtml(str)}</pre>`;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  return { init, setAgent, sendMessage };
})();
