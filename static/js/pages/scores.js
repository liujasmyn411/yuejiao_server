/**
 * 成绩管理页 — 录入 + 按学生查询
 */
const ScoresPage = (() => {
  function render() {
    return `
      <div class="page-header flex-between">
        <h3 style="margin:0">📈 成绩管理</h3>
        <button class="btn btn-primary" id="btn-add-score">+ 录入成绩</button>
      </div>
      <div class="card mt-16">
        <div class="form-grid">
          <div class="form-group">
            <label>学生ID</label>
            <input id="score-student-id" class="input" type="number" placeholder="输入学生ID查询">
          </div>
          <div class="form-group" style="display:flex;align-items:flex-end">
            <button class="btn btn-primary" id="btn-query-score">查询</button>
          </div>
        </div>
      </div>
      <div id="scores-table" class="table-container mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  function onMount() {
    document.getElementById('btn-add-score').onclick = openCreateModal;
    document.getElementById('btn-query-score').onclick = () => {
      const studentId = document.getElementById('score-student-id').value;
      if (!studentId) { Toast.show('请输入学生ID', 'warning'); return; }
      load(studentId);
    };
    // 如果是学生登录，自动查自己
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.user_type === 'STUDENT') {
      document.getElementById('score-student-id').value = user.id;
      load(user.id);
    } else {
      document.getElementById('scores-table').innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">📈</div><h3>请输入学生ID查询成绩</h3></div>';
    }
  }

  async function load(studentId) {
    const container = document.getElementById('scores-table');
    container.innerHTML = '<div class="page-loading">加载中...</div>';
    try {
      const data = await API.get(`/api/enterprise/score?student_id=${studentId}`);
      const scores = data.scores || [];
      if (!scores.length) {
        container.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">📈</div><h3>暂无成绩记录</h3></div>';
        return;
      }
      container.innerHTML = `
        <table class="table">
          <thead><tr><th>课程</th><th>得分</th><th>总分</th><th>及格线</th><th>考试类型</th><th>学期</th><th>考试时间</th></tr></thead>
          <tbody>
            ${scores.map(s => {
              const passed = s.total_score ? s.score >= (s.pass_score || 60) : true;
              return `<tr>
                <td><strong>${esc(s.course_name)}</strong></td>
                <td><span class="${passed ? 'text-success' : 'text-error'}" style="font-weight:700">${s.score}</span></td>
                <td>${s.total_score || '-'}</td>
                <td>${s.pass_score || 60}</td>
                <td>${esc(s.exam_type || '-')}</td>
                <td>${esc(s.semester || '-')}</td>
                <td>${s.exam_time ? s.exam_time.slice(0,10) : '-'}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      `;
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function openCreateModal() {
    Modal.show({
      title: '录入成绩',
      body: `
        <div class="form-grid">
          <div class="form-group"><label>学生ID <span class="text-error">*</span></label><input id="sc-student" class="input" type="number"></div>
          <div class="form-group"><label>课程名称 <span class="text-error">*</span></label><input id="sc-course" class="input"></div>
          <div class="form-group"><label>得分 <span class="text-error">*</span></label><input id="sc-score" class="input" type="number" step="0.5"></div>
          <div class="form-group"><label>总分</label><input id="sc-total" class="input" type="number" step="0.5" value="100"></div>
          <div class="form-group"><label>及格线</label><input id="sc-pass" class="input" type="number" value="60"></div>
          <div class="form-group"><label>考试类型</label><select id="sc-type" class="select"><option value="">请选择</option><option>期中</option><option>期末</option><option>语言考试</option><option>其他</option></select></div>
          <div class="form-group"><label>学期</label><input id="sc-semester" class="input" placeholder="如 2025-2026第二学期"></div>
          <div class="form-group"><label>考试时间</label><input id="sc-time" class="input" type="date"></div>
        </div>
      `,
      confirmText: '保存',
      onConfirm: async () => {
        const g = (id) => document.getElementById(id).value;
        const studentId = parseInt(g('sc-student'));
        const course = g('sc-course').trim();
        const score = parseFloat(g('sc-score'));
        if (!studentId || !course || isNaN(score)) { Toast.show('请填写必填字段', 'warning'); return; }
        const body = {
          student_id: studentId, course_name: course, score,
          total_score: parseFloat(g('sc-total')) || 100,
          pass_score: parseFloat(g('sc-pass')) || 60,
          exam_type: g('sc-type') || null,
          semester: g('sc-semester') || null,
          exam_time: g('sc-time') ? new Date(g('sc-time')).toISOString() : null,
        };
        try {
          await API.post('/api/enterprise/score', body);
          Toast.show('成绩录入成功', 'success');
          document.getElementById('score-student-id').value = studentId;
          load(studentId);
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
