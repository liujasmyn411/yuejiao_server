/**
 * 组织架构页 — 部门卡片 + 成员列表
 */
const OrgChartPage = (() => {
  let orgTree = null;

  function render() {
    return `
      <div class="page-header">
        <h3 style="margin:0">🏢 组织架构</h3>
      </div>
      <div id="org-content" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    try {
      const data = await API.get('/api/enterprise/org-chart');
      const tree = data.org_tree || [];
      if (!tree.length) {
        document.getElementById('org-content').innerHTML =
          '<div class="page-placeholder"><div class="placeholder-icon">🏢</div><h3>暂无组织架构数据</h3></div>';
        return;
      }
      orgTree = tree[0];
      renderOrg(orgTree);
    } catch (e) {
      document.getElementById('org-content').innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function findDeptChildren(deptName) {
    // 在树中查找部门并返回其子部门
    function search(node) {
      if (!node) return null;
      if (node.name === deptName) return node.children || [];
      if (node.children) {
        for (const c of node.children) {
          const found = search(c);
          if (found) return found;
        }
      }
      return null;
    }
    return search(orgTree) || [];
  }

  function renderOrg(root) {
    const children = root.children || [];
    const container = document.getElementById('org-content');
    container.innerHTML = `
      <div class="org-company card">
        <div class="org-company__header">
          <span class="org-company__icon">🏛</span>
          <div>
            <h3>${esc(root.name)}</h3>
            ${root.desc ? `<p class="text-muted">${esc(root.desc)}</p>` : ''}
          </div>
          ${root.contact_phone ? `<div class="org-company__contact">
            <span>📞 ${esc(root.contact_phone)}</span>
            ${root.contact_email ? `<span>📧 ${esc(root.contact_email)}</span>` : ''}
          </div>` : ''}
        </div>
      </div>

      <h4 class="section-title mt-16">部门一览（共 ${children.length} 个部门）</h4>
      <div class="org-dept-grid" id="org-dept-grid">
        ${children.map(dept => renderDeptCard(dept)).join('')}
      </div>
      <div id="org-dept-detail" class="mt-16"></div>
    `;

    // 点击部门卡片查看详情
    container.querySelectorAll('.org-dept-card').forEach(card => {
      card.onclick = () => {
        container.querySelectorAll('.org-dept-card--selected').forEach(c => c.classList.remove('org-dept-card--selected'));
        card.classList.add('org-dept-card--selected');
        showDeptDetail(card.dataset.deptName);
      };
    });
  }

  function renderDeptCard(dept) {
    const children = dept.children || [];
    return `
      <div class="org-dept-card card" data-dept-name="${esc(dept.name)}">
        <div class="org-dept-card__icon">${deptIcon(dept.name)}</div>
        <h4 class="org-dept-card__name">${esc(dept.name)}</h4>
        ${dept.desc ? `<p class="org-dept-card__desc">${esc(dept.desc)}</p>` : ''}
        <div class="org-dept-card__meta">
          ${children.length ? `<span class="tag tag-blue">${children.length} 个小组</span>` : ''}
        </div>
      </div>
    `;
  }

  function deptIcon(name) {
    const map = {
      '市场部': '📢', '销售部': '💼', '教务部': '📋',
      '留学服务部': '🎓', '客服部': '🎧',
    };
    return map[name] || '📂';
  }

  async function showDeptDetail(name) {
    const container = document.getElementById('org-dept-detail');
    container.innerHTML = '<div class="page-loading">加载中...</div>';

    try {
      const memberData = await API.get(`/api/enterprise/org-chart/department?dept_name=${encodeURIComponent(name)}`);
      const members = memberData.members || [];
      const subTeams = findDeptChildren(name);

      let html = `<div class="card"><h4 style="margin-bottom:16px">👥 ${esc(name)}</h4>`;

      // 子小组
      if (subTeams.length) {
        html += `<div class="org-sub-teams mb-16">`;
        html += `<span class="text-muted" style="font-size:12px;margin-right:8px">下属小组：</span>`;
        subTeams.forEach(t => {
          html += `<span class="tag tag-blue" style="padding:6px 12px;font-size:13px">📁 ${esc(t.name)}</span>`;
        });
        html += `</div>`;
      }

      // 成员列表
      html += `<h5 style="margin-bottom:8px;color:var(--color-text-secondary)">部门成员 (${members.length}人)</h5>`;
      if (members.length) {
        html += `
          <div class="org-member-grid">
            ${members.map(m => `
              <div class="org-member-card">
                <div class="org-member-card__avatar">${(m.real_name || '?')[0]}</div>
                <div class="org-member-card__info">
                  <strong>${esc(m.real_name)}</strong>
                  <span class="text-muted">${esc(m.role || '成员')}</span>
                </div>
                ${m.contact_info ? `<small class="text-muted">📞 ${esc(m.contact_info)}</small>` : ''}
                ${m.email ? `<small class="text-muted">📧 ${esc(m.email)}</small>` : ''}
              </div>
            `).join('')}
          </div>
        `;
      } else {
        html += '<p class="text-muted">该部门暂无成员，或成员未分配到该部门名称</p>';
      }

      html += '</div>';
      container.innerHTML = html;
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
