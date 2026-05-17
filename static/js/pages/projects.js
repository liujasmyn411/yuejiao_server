/**
 * 课程项目页 — 列表 + 筛选 + 添加/删除
 */
const ProjectsPage = (() => {
  let currentCategory = '';

  function render() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const canManage = user.user_type === 'ADMIN' || user.user_type === 'EMPLOYEE';
    return `
      <div class="page-header flex-between">
        <div class="filter-tabs" id="project-filter">
          <button class="filter-tab filter-tab--active" data-cat="">全部</button>
          <button class="filter-tab" data-cat="新加坡-本科">新加坡本科</button>
          <button class="filter-tab" data-cat="新加坡-大专">新加坡大专</button>
          <button class="filter-tab" data-cat="德国-双元制">德国双元制</button>
        </div>
        ${canManage ? '<button class="btn btn-primary" id="btn-add-project">+ 添加项目</button>' : ''}
      </div>
      <div id="projects-grid" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    document.querySelectorAll('#project-filter .filter-tab').forEach(tab => {
      tab.onclick = () => {
        document.querySelectorAll('#project-filter .filter-tab').forEach(t => t.classList.remove('filter-tab--active'));
        tab.classList.add('filter-tab--active');
        currentCategory = tab.dataset.cat;
        load();
      };
    });

    const addBtn = document.getElementById('btn-add-project');
    if (addBtn) {
      addBtn.onclick = () => openAddModal();
    }

    load();
  }

  async function load() {
    const grid = document.getElementById('projects-grid');
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const canDelete = user.user_type === 'ADMIN';
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
            ${canDelete ? `<button class="btn btn-sm btn-danger project-del-btn" data-id="${p.id}" style="margin-left:auto">🗑️ 删除</button>` : ''}
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

      if (canDelete) {
        document.querySelectorAll('.project-del-btn').forEach(btn => {
          btn.onclick = async (e) => {
            e.stopPropagation();
            const id = parseInt(btn.dataset.id);
            const project = projects.find(p => p.id === id);
            if (!project) return;
            Modal.show({
              title: '确认删除',
              body: `<p>确定要删除项目「<strong>${esc(project.project_name)}</strong>」吗？此操作不可恢复。</p>`,
              confirmText: '确认删除',
              onConfirm: async () => {
                try {
                  await API.delete(`/api/enterprise/project/${id}`);
                  Toast.show('项目已删除', 'success');
                  load();
                } catch (e) { Toast.show(e.message, 'error'); }
              },
            });
          };
        });
      }
    } catch (e) {
      grid.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function openAddModal() {
    Modal.show({
      title: '添加课程项目',
      body: `
        <div class="form-grid">
          <div class="form-group"><label>项目名称 <span class="text-error">*</span></label><input id="pj-name" class="input"></div>
          <div class="form-group"><label>类别</label><input id="pj-cat" class="input" placeholder="如 新加坡-本科"></div>
          <div class="form-group"><label>国家</label><input id="pj-country" class="input" placeholder="如 新加坡"></div>
          <div class="form-group"><label>学费</label><input id="pj-fee" class="input" placeholder="如 约25万人民币"></div>
          <div class="form-group"><label>学制</label><input id="pj-duration" class="input" placeholder="如 2+2年"></div>
          <div class="form-group"><label>适合人群</label><input id="pj-audience" class="input"></div>
          <div class="form-group"><label>申请要求</label><input id="pj-require" class="input"></div>
          <div class="form-group"><label>描述</label><textarea id="pj-desc" class="input" rows="3"></textarea></div>
          <div class="form-group"><label>推荐</label><input id="pj-rec" type="checkbox"></div>
        </div>
      `,
      confirmText: '添加',
      onConfirm: async () => {
        const g = (id) => document.getElementById(id).value;
        const name = g('pj-name').trim();
        if (!name) { Toast.show('请填写项目名称', 'warning'); return; }
        const body = {
          project_name: name,
          category: g('pj-cat') || '',
          country: g('pj-country') || '',
          tuition_fee: g('pj-fee') || '',
          duration: g('pj-duration') || '',
          description: document.getElementById('pj-desc').value || '',
          target_audience: g('pj-audience') || '',
          application_require: g('pj-require') || '',
          is_recommended: document.getElementById('pj-rec').checked ? 1 : 0,
        };
        try {
          await API.post('/api/enterprise/project', body);
          Toast.show('项目添加成功', 'success');
          load();
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
