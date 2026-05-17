/**
 * 留学进度页 — 7 阶段时间线可视化 + 编辑
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

      const canEdit = user.user_type === 'ADMIN' || user.user_type === 'EMPLOYEE';

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
            const editBtn = canEdit ? `<button class="btn btn-sm" style="margin-top:8px" data-id="${s.id}">✏️ 编辑</button>` : '';
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
                  ${editBtn}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;

      if (canEdit) {
        document.querySelectorAll('.timeline-item__body .btn-sm').forEach(btn => {
          btn.onclick = () => {
            const id = parseInt(btn.dataset.id);
            const stage = stages.find(s => s.id === id);
            if (stage) openEditModal(stage, user);
          };
        });
      }
    } catch (e) {
      document.getElementById('progress-content').innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function openEditModal(stage, user) {
    Modal.show({
      title: '编辑留学进度',
      body: `
        <div class="form-grid">
          <div class="form-group"><label>当前阶段</label><input id="ed-stage" class="input" value="${esc(stage.stage || '')}"></div>
          <div class="form-group"><label>阶段状态</label>
            <select id="ed-status" class="select">
              <option value="待开始" ${stage.stage_status === '待开始' ? 'selected' : ''}>待开始</option>
              <option value="进行中" ${stage.stage_status === '进行中' ? 'selected' : ''}>进行中</option>
              <option value="已完成" ${stage.stage_status === '已完成' ? 'selected' : ''}>已完成</option>
            </select>
          </div>
          <div class="form-group"><label>阶段详情</label><input id="ed-detail" class="input" value="${esc(stage.stage_detail || '')}"></div>
          <div class="form-group"><label>负责人</label><input id="ed-handler" class="input" value="${esc(stage.handler_name || '')}"></div>
          <div class="form-group"><label>负责人联系方式</label><input id="ed-contact" class="input" value="${esc(stage.handler_contact || '')}"></div>
          <div class="form-group"><label>预计完成日期</label><input id="ed-est" class="input" type="date" value="${stage.estimated_complete_date || ''}"></div>
          <div class="form-group"><label>实际完成日期</label><input id="ed-actual" class="input" type="date" value="${stage.actual_complete_date || ''}"></div>
          <div class="form-group"><label>设为当前阶段</label><input id="ed-current" type="checkbox" ${stage.is_current ? 'checked' : ''}></div>
        </div>
      `,
      confirmText: '保存',
      onConfirm: async () => {
        const body = {
          stage: document.getElementById('ed-stage').value || null,
          stage_status: document.getElementById('ed-status').value || null,
          stage_detail: document.getElementById('ed-detail').value || null,
          handler_name: document.getElementById('ed-handler').value || null,
          handler_contact: document.getElementById('ed-contact').value || null,
          estimated_complete_date: document.getElementById('ed-est').value || null,
          actual_complete_date: document.getElementById('ed-actual').value || null,
          is_current: document.getElementById('ed-current').checked ? 1 : null,
        };
        try {
          await API.put(`/api/student/study-abroad/${stage.id}`, body);
          Toast.show('留学进度已更新', 'success');
          onMount();
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
