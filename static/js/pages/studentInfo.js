/**
 * 学生信息页 — 按ID查询学生基本信息
 */
const StudentInfoPage = (() => {
  function render() {
    return `
      <div class="page-header">
        <h3 style="margin:0">🎓 学生信息查询</h3>
      </div>
      <div class="card mt-16">
        <div class="form-grid">
          <div class="form-group">
            <label>学生ID</label>
            <input id="si-student-id" class="input" type="number" placeholder="输入学生ID查询">
          </div>
          <div class="form-group" style="display:flex;align-items:flex-end">
            <button class="btn btn-primary" id="btn-query-student">查询</button>
          </div>
        </div>
      </div>
      <div id="student-info-result" class="mt-16"></div>
    `;
  }

  function onMount() {
    document.getElementById('btn-query-student').onclick = () => {
      const studentId = document.getElementById('si-student-id').value;
      if (!studentId) { Toast.show('请输入学生ID', 'warning'); return; }
      load(studentId);
    };
    // 学生登录自动查自己
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.user_type === 'STUDENT') {
      document.getElementById('si-student-id').value = user.id;
      load(user.id);
    } else {
      document.getElementById('student-info-result').innerHTML =
        '<div class="page-placeholder"><div class="placeholder-icon">🎓</div><h3>请输入学生ID查询</h3></div>';
    }
  }

  async function load(studentId) {
    const container = document.getElementById('student-info-result');
    container.innerHTML = '<div class="page-loading">查询中...</div>';
    try {
      const data = await API.get(`/api/student/info?student_id=${studentId}`);
      container.innerHTML = `
        <div class="card">
          <h4 style="margin-bottom:16px">学生信息</h4>
          <div class="info-grid">
            ${infoRow('姓名', data.real_name)}
            ${infoRow('用户名', data.username)}
            ${infoRow('部门/班级', data.department || '-')}
            ${infoRow('联系方式', data.contact_info || '-')}
            ${infoRow('邮箱', data.email || '-')}
            ${infoRow('国家/地区', data.country_region || '-')}
            ${infoRow('状态', data.status === 1 ? '<span class="tag tag-green">正常</span>' : '<span class="tag tag-orange">' + (data.status || '-') + '</span>')}
          </div>
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div class="page-error">查询失败: ${e.message}</div>`;
    }
  }

  function infoRow(label, value) {
    return `
      <div class="info-item">
        <span class="info-item__label">${label}</span>
        <span class="info-item__value">${value}</span>
      </div>
    `;
  }

  return { render, onMount };
})();
