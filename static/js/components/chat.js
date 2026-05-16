/**
 * 聊天浮窗组件
 */
const ChatWidget = (() => {
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
    currentUserId = userId;
    document.getElementById('chat-title').textContent = 'AI 助手';
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
    let text = data.message || data.response || data.reply || '';
    if (!text) {
      const str = JSON.stringify(data, null, 2);
      return `<pre class="chat-json">${escapeHtml(str)}</pre>`;
    }
    return markdownToHtml(text);
  }

  function markdownToHtml(text) {
    let html = escapeHtml(text);

    // 代码块 ```...``` → <pre><code>
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
      `<pre class="chat-code"><code>${code.trim()}</code></pre>`);

    // 行内代码 `...`
    html = html.replace(/`([^`]+)`/g, '<code class="chat-inline-code">$1</code>');

    // 粗体 **text**
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // 水平线 --- 或 ***
    html = html.replace(/^(---|\*\*\*)\s*$/gm, '<hr class="chat-hr">');

    // 标题 ## text
    html = html.replace(/^### (.+)$/gm, '<h5 class="chat-h5">$1</h5>');
    html = html.replace(/^## (.+)$/gm, '<h4 class="chat-h4">$1</h4>');

    // 无序列表 - item 或 • item
    html = html.replace(/^[•\-]\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul class="chat-list">$1</ul>');

    // 带序号列表 1. item
    html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
    // 把未被 ul 包裹的 li 用 ol 包裹
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, (match) => {
      if (match.includes('<ul')) return match; // 已被 ul 处理过
      return `<ol class="chat-list">${match}</ol>`;
    });

    // SQL 高亮行（以 SELECT/UPDATE/INSERT/DELETE 等开头）
    html = html.replace(/^((?:SELECT|UPDATE|INSERT|DELETE|CREATE|ALTER|DROP|SET|WHERE|FROM|JOIN|LIMIT|ORDER BY|GROUP BY)\b.*)$/gim,
      '<code class="chat-sql-line">$1</code>');

    // 段落：连续两个换行 → 新段落
    html = html.replace(/\n\n+/g, '</p><p class="chat-p">');
    // 单个换行 → <br>
    html = html.replace(/\n/g, '<br>');
    // 包裹在段落中
    html = '<p class="chat-p">' + html + '</p>';

    // 清理空段落
    html = html.replace(/<p class="chat-p"><\/p>/g, '');
    // 把 pre/ul/ol 从段落中提取出来（避免被 p 包裹）
    html = html.replace(/<p class="chat-p">(<(?:pre|ul|ol|h4|h5|hr)[\s\S]*?<\/\1>)<\/p>/g, '$1');

    return html;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  return { init, setAgent, sendMessage };
})();
