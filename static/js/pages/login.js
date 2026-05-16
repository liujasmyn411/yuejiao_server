/**
 * 登录页
 */
const LoginPage = (() => {
  function render() {
    return `
      <div class="login-page">
        <div class="login-card">
          <div class="login-card__header">
            <h1>🎓 粤教服务</h1>
            <p>AI Agent 智能服务平台</p>
          </div>
          <form id="login-form" class="login-form">
            <div class="form-group">
              <label>用户名</label>
              <input type="text" id="login-username" class="input" placeholder="请输入用户名" autocomplete="username">
            </div>
            <div class="form-group">
              <label>密码</label>
              <input type="password" id="login-password" class="input" placeholder="请输入密码" autocomplete="current-password">
            </div>
            <div id="login-error" class="login-error hidden"></div>
            <button type="submit" class="btn btn-primary btn-block btn-lg">登 录</button>
          </form>
          <div class="login-card__hint">
            <p>测试账号</p>
            <small>admin / admin123 | 员工1 / 123456 | 学生4 / 123456</small>
          </div>
        </div>
      </div>
    `;
  }

  function onMount() {
    document.getElementById('login-form').onsubmit = async (e) => {
      e.preventDefault();
      const username = document.getElementById('login-username').value.trim();
      const password = document.getElementById('login-password').value.trim();
      const errorEl = document.getElementById('login-error');

      if (!username || !password) {
        errorEl.textContent = '请输入用户名和密码';
        errorEl.classList.remove('hidden');
        return;
      }

      try {
        const data = await API.post('/api/login', { username, password });
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));

        // 统一 AI 聊天窗口
        ChatWidget.setAgent('unified', data.user.id);

        Sidebar.render();
        Topbar.render('/dashboard');
        Topbar.updateUnread();
        Router.navigate('/dashboard');
      } catch (err) {
        errorEl.textContent = err.message || '登录失败';
        errorEl.classList.remove('hidden');
      }
    };

    // 回车提交
    const inputs = document.querySelectorAll('#login-username, #login-password');
    inputs.forEach(inp => {
      inp.onkeydown = (e) => {
        if (e.key === 'Enter') document.getElementById('login-form').requestSubmit();
      };
    });
  }

  return { render, onMount };
})();
