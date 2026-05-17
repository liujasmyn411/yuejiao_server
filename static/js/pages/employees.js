/**
 * 员工通讯录页 — 查看 + 编辑
 */
const EmployeesPage = (() => {
  let employees = [];

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
      employees = data.employees || [];
      renderTable();
    } catch (e) {
      document.getElementById('employees-grid').innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function renderTable() {
    const grid = document.getElementById('employees-grid');
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const canEdit = user.user_type === 'ADMIN' || user.user_type === 'EMPLOYEE';

    if (!employees.length) {
      grid.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">👤</div><h3>暂无员工数据</h3></div>';
      return;
    }
    grid.innerHTML = `
      <div class="table-container">
        <table class="table">
          <thead><tr><th>ID</th><th>姓名</th><th>角色</th><th>部门</th><th>电话</th><th>邮箱</th>${canEdit ? '<th>操作</th>' : ''}</tr></thead>
          <tbody>
            ${employees.map(e => `
              <tr>
                <td>${e.id}</td>
                <td><strong>${esc(e.real_name)}</strong></td>
                <td><span class="tag tag-blue">${esc(e.employee_role || '-')}</span></td>
                <td>${esc(e.department || '-')}</td>
                <td>${esc(e.contact_info || '-')}</td>
                <td>${esc(e.email || '-')}</td>
                ${canEdit ? `<td><button class="btn btn-sm btn-edit-emp" data-id="${e.id}">✏️ 编辑</button></td>` : ''}
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    if (canEdit) {
      document.querySelectorAll('.btn-edit-emp').forEach(btn => {
        btn.onclick = () => {
          const id = parseInt(btn.dataset.id);
          const emp = employees.find(e => e.id === id);
          if (emp) openEditModal(emp);
        };
      });
    }
  }

  function openEditModal(emp) {
    Modal.show({
      title: `编辑员工: ${esc(emp.real_name)}`,
      body: `
        <div class="form-grid">
          <div class="form-group"><label>姓名</label><input id="ed-name" class="input" value="${esc(emp.real_name || '')}"></div>
          <div class="form-group"><label>角色</label><input id="ed-role" class="input" value="${esc(emp.employee_role || '')}"></div>
          <div class="form-group"><label>部门</label><input id="ed-dept" class="input" value="${esc(emp.department || '')}"></div>
          <div class="form-group"><label>电话</label><input id="ed-contact" class="input" value="${esc(emp.contact_info || '')}"></div>
          <div class="form-group"><label>邮箱</label><input id="ed-email" class="input" type="email" value="${esc(emp.email || '')}"></div>
        </div>
      `,
      confirmText: '保存',
      onConfirm: async () => {
        const body = {
          real_name: document.getElementById('ed-name').value || null,
          employee_role: document.getElementById('ed-role').value || null,
          department: document.getElementById('ed-dept').value || null,
          contact_info: document.getElementById('ed-contact').value || null,
          email: document.getElementById('ed-email').value || null,
        };
        try {
          await API.put(`/api/enterprise/employee/${emp.id}`, body);
          Toast.show('员工信息已更新', 'success');
          onMount();
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
