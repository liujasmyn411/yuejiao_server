/**
 * 聊天浮窗组件 — 支持对话历史
 */
const ChatWidget = (() => {
  let currentUserId = null;
  let currentSessionId = null;   // 本次登录的会话ID，用于区分历史
  let historyVisible = false;

  const STORAGE_KEY = 'chat_history';
  const MAX_SESSIONS = 50;

  function init() {
    const toggle = document.getElementById('chat-toggle');
    const close = document.getElementById('chat-close');
    const minimize = document.getElementById('chat-minimize');
    const send = document.getElementById('chat-send');
    const input = document.getElementById('chat-input');
    const widget = document.getElementById('chat-widget');
    const historyBtn = document.getElementById('chat-history-btn');
    const historyClear = document.getElementById('chat-history-clear');

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
    historyBtn.onclick = toggleHistory;
    historyClear.onclick = clearHistory;
    send.onclick = sendMessage;
    input.onkeydown = (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    };
  }

  function toggleHistory() {
    historyVisible = !historyVisible;
    const panel = document.getElementById('chat-history-panel');
    panel.classList.toggle('hidden', !historyVisible);
    if (historyVisible) renderHistoryList();
  }

  /* ==================== 历史存储 ==================== */

  function loadAllHistory() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch { return []; }
  }

  function saveAllHistory(data) {
    const trimmed = data.slice(-MAX_SESSIONS);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  }

  /** 获取当前用户的会话列表（按时间倒序） */
  function getUserSessions() {
    if (!currentUserId) return [];
    const all = loadAllHistory();
    return all
      .filter(s => s.userId === currentUserId)
      .sort((a, b) => b.startedAt - a.startedAt);
  }

  /** 结束当前会话并存入历史 */
  function saveCurrentSession() {
    const msgsEl = document.getElementById('chat-messages');
    if (!msgsEl || !currentSessionId) return;

    const msgEls = msgsEl.querySelectorAll('.chat-msg');
    if (msgEls.length === 0) return;

    const messages = [];
    msgEls.forEach(el => {
      const role = el.classList.contains('chat-msg--user') ? 'user' : 'assistant';
      const text = el.textContent.trim();
      if (text && text !== '正在思考...') messages.push({ role, text });
    });
    if (messages.length === 0) return;

    // 取第一条用户消息做预览
    const firstUser = messages.find(m => m.role === 'user');
    const preview = firstUser ? firstUser.text.slice(0, 60) : '对话记录';
    const intentTag = detectIntentTag(messages);

    const session = {
      id: currentSessionId,
      userId: currentUserId,
      startedAt: Date.now(),
      preview,
      intentTag,
      messages,
    };

    const all = loadAllHistory();
    // 如果已有同 sessionId 的记录则替换
    const idx = all.findIndex(s => s.id === currentSessionId);
    if (idx >= 0) all[idx] = session; else all.push(session);
    saveAllHistory(all);
  }

  function detectIntentTag(messages) {
    const allText = messages.map(m => m.text).join(' ');
    if (/投诉|反馈|不满/.test(allText)) return 'feedback';
    if (/请假|病假|事假/.test(allText)) return 'leave';
    return '';
  }

  /* ==================== 历史面板渲染 ==================== */

  function renderHistoryList() {
    const list = document.getElementById('chat-history-list');
    if (!list) return;
    const sessions = getUserSessions();

    if (sessions.length === 0) {
      list.innerHTML = '<div class="chat-history-empty">暂无对话历史</div>';
      return;
    }

    list.innerHTML = sessions.map(s => {
      const date = new Date(s.startedAt).toLocaleString('zh-CN', {
        month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit'
      });
      const badgeCls = s.intentTag === 'feedback' ? 'chat-history-item__badge--feedback'
        : s.intentTag === 'leave' ? 'chat-history-item__badge--leave'
        : 'chat-history-item__badge--default';
      const badgeText = s.intentTag === 'feedback' ? '投诉' : s.intentTag === 'leave' ? '请假' : '';
      return `
        <div class="chat-history-item" data-sid="${s.id}">
          <div class="chat-history-item__date">${date}</div>
          <div class="chat-history-item__preview">${escapeHtml(s.preview)}</div>
          ${badgeText ? `<span class="chat-history-item__badge ${badgeCls}">${badgeText}</span>` : ''}
        </div>`;
    }).join('');

    // 点击历史项 → 在主区域展示（只读）
    list.querySelectorAll('.chat-history-item').forEach(el => {
      el.onclick = () => {
        const sid = el.dataset.sid;
        const all = loadAllHistory();
        const session = all.find(s => s.id === sid);
        if (!session) return;
        showHistorySession(session);
      };
    });
  }

  function showHistorySession(session) {
    const msgs = document.getElementById('chat-messages');
    msgs.innerHTML = '';
    // 添加提示条
    const bar = document.createElement('div');
    bar.className = 'chat-history-bar';
    bar.innerHTML = `<span>📜 历史对话 — ${new Date(session.startedAt).toLocaleString('zh-CN')}</span>
      <button class="btn btn-sm" id="chat-back-current">返回当前对话</button>`;
    msgs.appendChild(bar);
    msgs.querySelector('#chat-back-current').onclick = restoreCurrentSession;

    session.messages.forEach(m => appendMessage(m.role, m.text));
    msgs.scrollTop = msgs.scrollHeight;
  }

  function restoreCurrentSession() {
    // 从 localStorage 读取当前会话消息重新渲染
    const msgs = document.getElementById('chat-messages');
    msgs.innerHTML = '';
    const all = loadAllHistory();
    const cur = all.find(s => s.id === currentSessionId);
    if (cur) {
      cur.messages.forEach(m => appendMessage(m.role, m.text));
    }
    msgs.scrollTop = msgs.scrollHeight;
  }

  function clearHistory() {
    if (!currentUserId) return;
    if (!confirm('确定清空所有对话历史吗？')) return;
    const all = loadAllHistory();
    const filtered = all.filter(s => s.userId !== currentUserId);
    saveAllHistory(filtered);
    renderHistoryList();
    Toast.show('对话历史已清空');
  }

  /* ==================== Agent 绑定 ==================== */

  function setAgent(type, userId) {
    if (!userId) {
      // 登出时清空
      currentUserId = null;
      currentSessionId = null;
      const msgs = document.getElementById('chat-messages');
      if (msgs) msgs.innerHTML = '';
      document.getElementById('chat-title').textContent = 'AI 助手';
      return;
    }

    // 切换用户时：保存上一个用户的当前会话，清空显示
    if (currentUserId && currentUserId !== userId) {
      saveCurrentSession();
    }

    // 新用户登录 → 清空当前聊天区域（历史保留在 localStorage）
    const msgs = document.getElementById('chat-messages');
    msgs.innerHTML = '';

    currentUserId = userId;
    currentSessionId = 'session_' + userId + '_' + Date.now();
    document.getElementById('chat-title').textContent = 'AI 助手';

    // 关闭历史面板
    historyVisible = false;
    const panel = document.getElementById('chat-history-panel');
    if (panel) panel.classList.add('hidden');
  }

  /* ==================== 发送消息 ==================== */

  async function sendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;

    appendMessage('user', text);
    input.value = '';
    input.style.height = 'auto';

    appendMessage('assistant', '<span class="typing">正在思考...</span>');

    try {
      const body = { message: text };
      if (currentUserId) body.student_id = currentUserId;
      const data = await API.post('/api/chat', body);
      // 移除 typing
      const msgs = document.getElementById('chat-messages');
      msgs.removeChild(msgs.lastChild);

      // 根据返回的 agent 类型更新标题
      const agentTitles = { customer: '客服助手', enterprise: '企业助手', student: '学生助手' };
      document.getElementById('chat-title').textContent = agentTitles[data.agent] || 'AI 助手';

      // 渲染回复
      const replyText = data.message || data.response || data.reply || '';
      if (replyText) {
        appendMessage('assistant', formatReply(data));
      }
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
    let text = data.message || data.response || data.reply || '';
    if (!text) {
      const str = JSON.stringify(data, null, 2);
      return `<pre class="chat-json">${escapeHtml(str)}</pre>`;
    }
    return markdownToHtml(text);
  }

  /* ==================== Markdown 渲染 ==================== */

  function markdownToHtml(text) {
    let html = escapeHtml(text);

    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
      `<pre class="chat-code"><code>${code.trim()}</code></pre>`);
    html = html.replace(/`([^`]+)`/g, '<code class="chat-inline-code">$1</code>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/^(---|\*\*\*)\s*$/gm, '<hr class="chat-hr">');
    html = html.replace(/^### (.+)$/gm, '<h5 class="chat-h5">$1</h5>');
    html = html.replace(/^## (.+)$/gm, '<h4 class="chat-h4">$1</h4>');
    html = html.replace(/^[•\-]\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul class="chat-list">$1</ul>');
    html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, (match) => {
      if (match.includes('<ul')) return match;
      return `<ol class="chat-list">${match}</ol>`;
    });
    html = html.replace(/^((?:SELECT|UPDATE|INSERT|DELETE|CREATE|ALTER|DROP|SET|WHERE|FROM|JOIN|LIMIT|ORDER BY|GROUP BY)\b.*)$/gim,
      '<code class="chat-sql-line">$1</code>');
    html = html.replace(/\n\n+/g, '</p><p class="chat-p">');
    html = html.replace(/\n/g, '<br>');
    html = '<p class="chat-p">' + html + '</p>';
    html = html.replace(/<p class="chat-p"><\/p>/g, '');
    html = html.replace(/<p class="chat-p">(<(?:pre|ul|ol|h4|h5|hr)[\s\S]*?<\/\1>)<\/p>/g, '$1');
    return html;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  return { init, setAgent, sendMessage, saveCurrentSession };
})();
