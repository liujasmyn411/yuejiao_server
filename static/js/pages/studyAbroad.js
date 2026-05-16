/**
 * 留学进度页 — 7 阶段时间线可视化
 */
const StudyAbroadPage = (() => {
  function render() {
    return `
      <div class="page-header"><h3 style="margin:0">🎓 留学进度</h3></div>
      <div id="progress-content" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    try {
      const data = await API.get(`/api/student/study-abroad?student_id=${user.id}`);
      const stages = data.progress || [];
      const container = document.getElementById('progress-content');

      if (!stages.length) {
        container.innerHTML = `<div class="page-placeholder"><div class="placeholder-icon">🎓</div><h3>暂无留学进度数据</h3><p>${data.message || ''}</p></div>`;
        return;
      }

      const target = stages[0];
      container.innerHTML = `
        <div class="card mb-16">
          <h4>🎯 ${esc(target.target_country)} · ${esc(target.target_school)}</h4>
          <p class="text-muted">${esc(target.target_major)} · ${esc(target.degree_level)}</p>
        </div>
        <div class="timeline">
          ${stages.map((s, i) => {
            const isActive = s.is_current === 1;
            const isDone = s.stage_status === '已完成';
            const cls = isActive ? 'timeline-item--active' : isDone ? 'timeline-item--done' : '';
            return `
              <div class="timeline-item ${cls}">
                <div class="timeline-item__marker">
                  <div class="timeline-dot">${isDone ? '✓' : isActive ? '●' : s.stage_order}</div>
                  ${i < stages.length - 1 ? '<div class="timeline-line"></div>' : ''}
                </div>
                <div class="timeline-item__body">
                  <div class="flex-between">
                    <h4>${esc(s.stage)}</h4>
                    <span class="tag ${isDone ? 'tag-green' : isActive ? 'tag-orange' : ''}">${esc(s.stage_status)}</span>
                  </div>
                  <p class="text-muted">${esc(s.stage_detail || '')}</p>
                  <div class="timeline-item__meta">
                    <span>👤 ${esc(s.handler_name)} · ${esc(s.handler_contact)}</span>
                    <span>📅 预计 ${s.estimated_complete_date || '-'}</span>
                    ${s.actual_complete_date ? `<span>✅ 实际 ${s.actual_complete_date}</span>` : ''}
                  </div>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    } catch (e) {
      document.getElementById('progress-content').innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
