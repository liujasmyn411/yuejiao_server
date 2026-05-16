/**
 * 活动讲座页 — 列表 + 报名
 */
const EventsPage = (() => {
  function render() {
    return `
      <div class="page-header flex-between">
        <h3 style="margin:0">📅 活动讲座</h3>
      </div>
      <div id="events-grid" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    try {
      const data = await API.get('/api/customer/events');
      const events = data.events || [];
      const grid = document.getElementById('events-grid');
      if (!events.length) {
        grid.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">📅</div><h3>暂无活动</h3></div>';
        return;
      }
      grid.innerHTML = events.map(e => `
        <div class="event-card card">
          <div class="event-card__header">
            <span class="tag ${e.event_type === '线上' ? 'tag-blue' : 'tag-green'}">${esc(e.event_type)}</span>
            <span class="tag ${e.event_status === '未开始' ? 'tag-orange' : 'tag-green'}">${esc(e.event_status)}</span>
          </div>
          <h4 class="event-card__title">${esc(e.event_name)}</h4>
          <div class="event-card__info">
            <div class="event-info-item">
              <span class="event-info-label">时间</span>
              <span>${(e.start_time || '').slice(0,16).replace('T',' ')}</span>
            </div>
            <div class="event-info-item">
              <span class="event-info-label">地点</span>
              <span>${esc(e.location || '-')}</span>
            </div>
            ${e.speaker ? `<div class="event-info-item"><span class="event-info-label">主讲人</span><span>${esc(e.speaker)}</span></div>` : ''}
            <div class="event-info-item">
              <span class="event-info-label">报名</span>
              <span><strong>${e.current_participants}</strong> / ${e.max_participants || '不限'}</span>
            </div>
          </div>
          <div class="event-card__progress">
            <div class="progress-bar">
              <div class="progress-bar__fill" style="width:${e.max_participants ? Math.min(100, e.current_participants/e.max_participants*100) : 0}%"></div>
            </div>
          </div>
          <button class="btn btn-primary btn-block mt-16 btn-register" data-event='${esc(JSON.stringify(e))}'>
            ${e.max_participants && e.current_participants >= e.max_participants ? '已满' : '立即报名'}
          </button>
        </div>
      `).join('');

      grid.querySelectorAll('.btn-register').forEach(btn => {
        btn.onclick = () => {
          const event = JSON.parse(btn.dataset.event);
          if (event.max_participants && event.current_participants >= event.max_participants) {
            Toast.show('报名已满', 'warning'); return;
          }
          openRegisterModal(event);
        };
      });
    } catch (e) {
      document.getElementById('events-grid').innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function openRegisterModal(event) {
    Modal.show({
      title: `报名 — ${event.event_name}`,
      body: `
        <div class="event-register-info">
          <p><strong>活动：</strong>${esc(event.event_name)}</p>
          <p><strong>时间：</strong>${(event.start_time || '').slice(0,16).replace('T',' ')}</p>
          <p><strong>地点：</strong>${esc(event.location || '-')}</p>
        </div>
        <div class="form-group mt-16">
          <label>姓名 <span class="text-error">*</span></label>
          <input id="reg-name" class="input" placeholder="请输入姓名">
        </div>
        <div class="form-group">
          <label>联系方式</label>
          <input id="reg-contact" class="input" placeholder="手机/微信">
        </div>
      `,
      confirmText: '确认报名',
      onConfirm: async () => {
        const name = document.getElementById('reg-name').value.trim();
        const contact = document.getElementById('reg-contact').value.trim();
        if (!name) { Toast.show('请输入姓名', 'warning'); return; }
        try {
          await API.post('/api/customer/events/register', {
            event_id: event.id,
            customer_id: 1,
            customer_name: name,
            contact: contact,
          });
          Toast.show('报名成功！', 'success');
          EventsPage.onMount(); // 刷新
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
