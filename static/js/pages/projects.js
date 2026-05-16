/**
 * 课程项目页 — 列表 + 按类别/国家筛选
 */
const ProjectsPage = (() => {
  let currentCategory = '';

  function render() {
    return `
      <div class="page-header flex-between">
        <div class="filter-tabs" id="project-filter">
          <button class="filter-tab filter-tab--active" data-cat="">全部</button>
          <button class="filter-tab" data-cat="新加坡-本科">新加坡本科</button>
          <button class="filter-tab" data-cat="新加坡-大专">新加坡大专</button>
          <button class="filter-tab" data-cat="德国-双元制">德国双元制</button>
        </div>
      </div>
      <div id="projects-grid" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    document.querySelectorAll('#project-filter .filter-tab').forEach(tab => {
      tab.onclick = () => {
        document.querySelectorAll('#project-filter .filter-tab').forEach(t => t.classList.remove('filter-tab--active'));
        tab.classList.add('filter-tab--active');
        currentCategory = tab.dataset.cat;
        load();
      };
    });
    load();
  }

  async function load() {
    const grid = document.getElementById('projects-grid');
    try {
      const url = currentCategory ? `/api/customer/projects?category=${encodeURIComponent(currentCategory)}` : '/api/customer/projects';
      const data = await API.get(url);
      const projects = data.projects || [];
      if (!projects.length) {
        grid.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">📚</div><h3>暂无项目</h3></div>';
        return;
      }
      grid.innerHTML = projects.map(p => `
        <div class="project-card card">
          <div class="project-card__header">
            <span class="tag tag-blue">${esc(p.country)}</span>
            <span class="tag tag-green">${esc(p.category)}</span>
            ${p.is_recommended ? '<span class="tag tag-orange">⭐ 推荐</span>' : ''}
          </div>
          <h4 class="project-card__title">${esc(p.project_name)}</h4>
          <p class="project-card__desc">${esc(p.description || '')}</p>
          <div class="project-card__meta">
            ${p.tuition_fee ? `<div><span class="text-muted">学费：</span>${esc(p.tuition_fee)}</div>` : ''}
            ${p.duration ? `<div><span class="text-muted">学制：</span>${esc(p.duration)}</div>` : ''}
          </div>
          ${p.target_audience ? `<div class="project-card__audience">👤 适合：${esc(p.target_audience)}</div>` : ''}
          ${p.application_require ? `<div class="project-card__require mt-16"><strong>申请要求：</strong>${esc(p.application_require)}</div>` : ''}
        </div>
      `).join('');
    } catch (e) {
      grid.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
