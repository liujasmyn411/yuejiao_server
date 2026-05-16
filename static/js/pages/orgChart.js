/**
 * 组织架构页 — 树形展示 + 部门员工查询
 */
const OrgChartPage = (() => {
  function render() {
    return `
      <div class="page-header flex-between">
        <h3 style="margin:0">🏢 组织架构</h3>
        <div class="flex-center gap-8">
          <input id="dept-search" class="input" style="width:200px" placeholder="搜索部门...">
          <button class="btn btn-primary" id="btn-search-dept">搜索</button>
        </div>
      </div>
      <div id="org-tree" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
      <div id="dept-members" class="mt-16"></div>
    `;
  }

  async function onMount() {
    document.getElementById('btn-search-dept').onclick = searchDept;
    document.getElementById('dept-search').onkeydown = (e) => { if (e.key === 'Enter') searchDept(); };
    await loadTree();
  }

  async function loadTree() {
    const container = document.getElementById('org-tree');
    try {
      const data = await API.get('/api/enterprise/org-chart');
      const tree = data.org_tree || [];
      if (!tree.length) {
        container.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">🏢</div><h3>暂无组织架构数据</h3></div>';
        return;
      }
      container.innerHTML = `<div class="tree">${renderTree(tree)}</div>`;

      // 点击部门查看成员
      container.querySelectorAll('.tree-node__name').forEach(el => {
        el.onclick = () => searchDeptMembers(el.textContent.trim());
      });
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function renderTree(nodes) {
    if (!nodes || !nodes.length) return '';
    return `<ul>${nodes.map(n => `
      <li>
        <div class="tree-node">
          <div class="tree-node__name" style="cursor:pointer">
            ${n.dept_level > 2 ? '└ ' : ''}${esc(n.dept_name)}
          </div>
          ${n.dept_desc ? `<div class="tree-node__desc">${esc(n.dept_desc)}</div>` : ''}
          ${n.contact_phone || n.contact_email ? `
            <div class="tree-node__contact">
              ${n.contact_phone ? `📞 ${esc(n.contact_phone)}` : ''}
              ${n.contact_email ? `📧 ${esc(n.contact_email)}` : ''}
            </div>
          ` : ''}
        </div>
        ${n.children ? renderTree(n.children) : ''}
      </li>
    `).join('')}</ul>`;
  }

  async function searchDept() {
    const name = document.getElementById('dept-search').value.trim();
    if (name) { searchDeptMembers(name); return; }
    document.getElementById('dept-members').innerHTML = '';
  }

  async function searchDeptMembers(name) {
    const container = document.getElementById('dept-members');
    container.innerHTML = '<div class="page-loading">加载中...</div>';
    try {
      // 先查部门列表
      const deptData = await API.get('/api/enterprise/org-chart/department');
      const depts = deptData.departments || [];
      const dept = depts.find(d => d.name === name);
      if (!dept) {
        // 尝试用名称模糊搜索
        const found = depts.find(d => d.name.includes(name));
        if (!found) {
          container.innerHTML = `<div class="page-placeholder"><div class="placeholder-icon">🔍</div><h3>未找到部门"${esc(name)}"</h3></div>`;
          return;
        }
        await showMembers(found.name);
        return;
      }
      await showMembers(name);
    } catch (e) {
      container.innerHTML = `<div class="page-error">查询失败: ${e.message}</div>`;
    }
  }

  async function showMembers(name) {
    const container = document.getElementById('dept-members');
    try {
      const data = await API.get(`/api/enterprise/org-chart/department?dept_name=${encodeURIComponent(name)}`);
      const members = data.members || [];
      container.innerHTML = `
        <div class="card">
          <h4 style="margin-bottom:12px">👥 ${esc(name)} — 成员 (${members.length})</h4>
          ${members.length ? `
            <table class="table">
              <thead><tr><th>ID</th><th>姓名</th><th>角色</th><th>电话</th><th>邮箱</th></tr></thead>
              <tbody>
                ${members.map(m => `
                  <tr>
                    <td>${m.id}</td>
                    <td><strong>${esc(m.real_name)}</strong></td>
                    <td>${esc(m.role || '-')}</td>
                    <td>${esc(m.contact_info || '-')}</td>
                    <td>${esc(m.email || '-')}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          ` : '<p class="text-muted">该部门暂无成员</p>'}
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
