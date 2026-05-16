/**
 * Hash 路由 — 极简 SPA 导航
 * 页面只需注册一个渲染函数，路由切换时自动调用
 */
const Router = (() => {
  const pages = {};
  let currentPage = null;

  function register(path, renderFn, meta = {}) {
    pages[path] = { render: renderFn, meta };
  }

  async function navigate(path) {
    const page = pages[path];
    if (!page) {
      navigate('/login');
      return;
    }
    // 需要登录的页面
    if (page.meta.requireAuth && !API.getToken()) {
      navigate('/login');
      return;
    }
    currentPage = path;
    const content = document.getElementById('content');
    content.innerHTML = '<div class="page-loading">加载中...</div>';
    try {
      const html = await page.render();
      content.innerHTML = html;
      // 触发页面初始化钩子
      if (typeof page.meta.onMount === 'function') {
        page.meta.onMount();
      }
    } catch (err) {
      content.innerHTML = `<div class="page-error">页面加载失败: ${err.message}</div>`;
      console.error(err);
    }
    Sidebar.setActive(path);
  }

  function init() {
    window.addEventListener('hashchange', () => {
      const path = location.hash.slice(1) || '/login';
      navigate(path);
    });
    const path = location.hash.slice(1) || '/login';
    navigate(path);
  }

  return { register, navigate, init, pages };
})();
