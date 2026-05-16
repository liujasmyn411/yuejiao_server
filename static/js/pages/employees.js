/**
 * 员工通讯录页
 */
const EmployeesPage = (() => {
  function render() {
    return `
      <div class="page-header"><h3 style="margin:0">👤 员工通讯录</h3></div>
      <div id="employees-grid" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    try {
      const data = await API.get('/api/enterprise/employee');
      const employees = data.employees || [];
      const grid = document.getElementById('employees-grid');
      if (!employees.length) {
        grid.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">👤</div><h3>暂无员工数据</h3></div>';
        return;
      }
      grid.innerHTML = `
        <div class="table-container">
          <table class="table">
            <thead><tr><th>ID</th><th>姓名</th><th>角色</th><th>部门</th><th>电话</th><th>邮箱</th></tr></thead>
            <tbody>
              ${employees.map(e => `
                <tr>
                  <td>${e.id}</td>
                  <td><strong>${esc(e.real_name)}</strong></td>
                  <td><span class="tag tag-blue">${esc(e.employee_role || '-')}</span></td>
                  <td>${esc(e.department || '-')}</td>
                  <td>${esc(e.contact_info || '-')}</td>
                  <td>${esc(e.email || '-')}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    } catch (e) {
      document.getElementById('employees-grid').innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
