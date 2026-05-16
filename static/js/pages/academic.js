/**
 * 教务 DDL 页 — 考试/论文/作业列表
 */
const AcademicPage = (() => {
  let currentType = '';

  function render() {
    return `
      <div class="page-header flex-between">
        <div class="filter-tabs" id="academic-filter">
          <button class="filter-tab filter-tab--active" data-type="">全部</button>
          <button class="filter-tab" data-type="考试">考试</button>
          <button class="filter-tab" data-type="论文">论文</button>
          <button class="filter-tab" data-type="项目">项目</button>
          <button class="filter-tab" data-type="作业">作业</button>
        </div>
        <button class="btn btn-primary" id="btn-upcoming">📅 即将到期</button>
      </div>
      <div id="academic-table" class="table-container mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (!user.id) {
      document.getElementById('academic-table').innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">📋</div><h3>请先登录</h3></div>';
      return;
    }

    document.querySelectorAll('#academic-filter .filter-tab').forEach(tab => {
      tab.onclick = () => {
        document.querySelectorAll('#academic-filter .filter-tab').forEach(t => t.classList.remove('filter-tab--active'));
        tab.classList.add('filter-tab--active');
        currentType = tab.dataset.type;
        load(user.id);
      };
    });
    document.getElementById('btn-upcoming').onclick = () => loadUpcoming(user.id);
    load(user.id);
  }

  async function load(studentId) {
    const container = document.getElementById('academic-table');
    try {
      const url = currentType
        ? `/api/student/academic?student_id=${studentId}&academic_type=${encodeURIComponent(currentType)}`
        : `/api/student/academic?student_id=${studentId}`;
      const data = await API.get(url);
      const items = data.academics || [];
      if (!items.length) {
        container.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">📋</div><h3>暂无教务安排</h3></div>';
        return;
      }
      container.innerHTML = `
        <table class="table">
          <thead>
            <tr><th>课程</th><th>类型</th><th>标题</th><th>截止时间</th><th>地点</th><th>时长</th><th>学期</th><th>状态</th></tr>
          </thead>
          <tbody>
            ${items.map(a => {
              const due = new Date(a.deadline);
              const now = new Date();
              const daysLeft = Math.ceil((due - now) / (1000 * 60 * 60 * 24));
              let rowClass = '';
              if (a.ddl_status === '已完成') rowClass = 'row-done';
              else if (daysLeft <= 1) rowClass = 'row-urgent';
              else if (daysLeft <= 7) rowClass = 'row-warn';
              return `<tr class="${rowClass}">
                <td><strong>${esc(a.course_name)}</strong></td>
                <td>${typeTag(a.academic_type)}</td>
                <td>${esc(a.title)}</td>
                <td>${a.deadline ? a.deadline.slice(0,16).replace('T',' ') : '-'}</td>
                <td>${esc(a.exam_location || '-')}</td>
                <td>${a.duration_minutes ? a.duration_minutes + '分钟' : '-'}</td>
                <td>${esc(a.semester || '-')}</td>
                <td>${statusTag(a.ddl_status, daysLeft)}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      `;
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  async function loadUpcoming(studentId) {
    const container = document.getElementById('academic-table');
    container.innerHTML = '<div class="page-loading">加载中...</div>';
    try {
      const data = await API.get(`/api/student/academic/upcoming?student_id=${studentId}&days=14`);
      const items = data.upcoming || [];
      if (!items.length) {
        container.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">✅</div><h3>14天内暂无DDL</h3><p>继续保持！</p></div>';
        return;
      }
      container.innerHTML = `
        <div class="card mt-16">
          <h4 style="margin-bottom:12px">📅 未来14天内到期的DDL</h4>
        </div>
        <div class="table-container mt-16">
          <table class="table">
            <thead><tr><th>课程</th><th>类型</th><th>标题</th><th>截止时间</th><th>剩余天数</th><th>状态</th></tr></thead>
            <tbody>
              ${items.map(a => {
                const daysLeft = a.days_left;
                let rowClass = daysLeft <= 1 ? 'row-urgent' : daysLeft <= 3 ? 'row-warn' : '';
                return `<tr class="${rowClass}">
                  <td><strong>${esc(a.course_name)}</strong></td>
                  <td>${typeTag(a.academic_type)}</td>
                  <td>${esc(a.title)}</td>
                  <td>${(a.deadline || '').slice(0,16).replace('T',' ')}</td>
                  <td><strong>${daysLeft} 天</strong></td>
                  <td>${statusTag(a.ddl_status, daysLeft)}</td>
                </tr>`;
              }).join('')}
            </tbody>
          </table>
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function typeTag(type) {
    const map = { '考试': 'tag-red', '论文': 'tag-blue', '项目': 'tag-green', '作业': 'tag-orange' };
    return `<span class="tag ${map[type] || 'tag-blue'}">${esc(type)}</span>`;
  }

  function statusTag(status, daysLeft) {
    if (status === '已完成') return '<span class="tag tag-green">已完成</span>';
    if (daysLeft <= 0) return '<span class="tag tag-red">已逾期</span>';
    if (daysLeft <= 1) return '<span class="tag tag-red">即将截止</span>';
    if (daysLeft <= 7) return '<span class="tag tag-orange">进行中</span>';
    return '<span class="tag tag-blue">待完成</span>';
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
