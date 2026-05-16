/**
 * CRM 意向客户管理页
 */
const LeadsPage = (() => {
  let currentFilter = '';

  function render() {
    return `
      <div class="page-header flex-between">
        <div>
          <div class="filter-tabs" id="lead-filter-tabs">
            <button class="filter-tab filter-tab--active" data-status="">全部</button>
            <button class="filter-tab" data-status="新增意向">新增意向</button>
            <button class="filter-tab" data-status="跟进中">跟进中</button>
            <button class="filter-tab" data-status="已签约">已签约</button>
            <button class="filter-tab" data-status="已流失">已流失</button>
          </div>
        </div>
        <button class="btn btn-primary" id="btn-add-lead">+ 新增客户</button>
      </div>
      <div id="lead-table" class="table-container mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    document.getElementById('btn-add-lead').onclick = openCreateModal;
    document.querySelectorAll('#lead-filter-tabs .filter-tab').forEach(tab => {
      tab.onclick = () => {
        document.querySelectorAll('#lead-filter-tabs .filter-tab').forEach(t => t.classList.remove('filter-tab--active'));
        tab.classList.add('filter-tab--active');
        currentFilter = tab.dataset.status;
        loadLeads();
      };
    });
    loadLeads();
  }

  async function loadLeads() {
    const container = document.getElementById('lead-table');
    try {
      const url = currentFilter ? `/api/enterprise/lead?status=${encodeURIComponent(currentFilter)}` : '/api/enterprise/lead';
      const data = await API.get(url);
      const leads = data.leads || [];
      if (!leads.length) {
        container.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">📭</div><h3>暂无客户数据</h3><p>点击右上角"新增客户"添加</p></div>';
        return;
      }
      container.innerHTML = `
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>客户姓名</th>
              <th>年龄</th>
              <th>学历</th>
              <th>意向国家</th>
              <th>意向专业</th>
              <th>状态</th>
              <th>评分</th>
              <th>下次跟进</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${leads.map(l => `
              <tr>
                <td>${l.id}</td>
                <td><strong>${esc(l.customer_name)}</strong></td>
                <td>${l.age || '-'}</td>
                <td>${l.education || '-'}</td>
                <td>${l.intended_country || '-'}</td>
                <td>${l.intended_major || '-'}</td>
                <td>${statusTag(l.status)}</td>
                <td>${scoreBadge(l.score)}</td>
                <td>${l.next_follow_time ? l.next_follow_time.slice(0,10) : '-'}</td>
                <td>${(l.create_time || '').slice(0,10)}</td>
                <td>
                  <button class="btn btn-sm btn-edit" data-lead='${esc(JSON.stringify(l))}'>编辑</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
      container.querySelectorAll('.btn-edit').forEach(btn => {
        btn.onclick = () => openEditModal(JSON.parse(btn.dataset.lead));
      });
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function openCreateModal() {
    Modal.show({
      title: '新增意向客户',
      body: leadFormHTML({}),
      confirmText: '保存',
      onConfirm: async () => {
        const data = readForm();
        if (!data.customer_name) { Toast.show('请输入客户姓名', 'warning'); return; }
        try {
          await API.post('/api/enterprise/lead', data);
          Toast.show('客户录入成功', 'success');
          loadLeads();
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function openEditModal(lead) {
    Modal.show({
      title: `编辑客户 - ${lead.customer_name}`,
      body: leadFormHTML(lead),
      confirmText: '保存修改',
      onConfirm: async () => {
        const data = readForm();
        try {
          await API.put(`/api/enterprise/lead/${lead.id}`, data);
          Toast.show('客户信息更新成功', 'success');
          loadLeads();
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function readForm() {
    const get = (id) => document.getElementById(id)?.value || '';
    return {
      customer_name: get('lead-name'),
      contact_info: get('lead-contact'),
      age: parseInt(get('lead-age')) || null,
      education: get('lead-edu'),
      intended_country: get('lead-country'),
      intended_major: get('lead-major'),
      family_finance: get('lead-finance'),
      language_level: get('lead-lang'),
      background_info: get('lead-bg'),
      status: get('lead-status'),
      source_channel: get('lead-source'),
      score: parseInt(get('lead-score')) || 0,
    };
  }

  function leadFormHTML(lead) {
    const v = (key, def = '') => esc(lead[key] || def);
    return `
      <div class="form-grid">
        <div class="form-group">
          <label>客户姓名 <span class="text-error">*</span></label>
          <input id="lead-name" class="input" value="${v('customer_name')}" placeholder="必填">
        </div>
        <div class="form-group">
          <label>联系方式</label>
          <input id="lead-contact" class="input" value="${v('contact_info')}" placeholder="手机/微信">
        </div>
        <div class="form-group">
          <label>年龄</label>
          <input id="lead-age" class="input" type="number" value="${v('age')}">
        </div>
        <div class="form-group">
          <label>学历</label>
          <select id="lead-edu" class="select">
            <option value="">请选择</option>
            ${opt('初中', v('education'))}
            ${opt('高中', v('education'))}
            ${opt('职高', v('education'))}
            ${opt('中专', v('education'))}
            ${opt('大专', v('education'))}
            ${opt('本科', v('education'))}
            ${opt('硕士', v('education'))}
            ${opt('博士', v('education'))}
          </select>
        </div>
        <div class="form-group">
          <label>意向国家</label>
          <select id="lead-country" class="select">
            <option value="">请选择</option>
            ${opt('新加坡', v('intended_country'))}
            ${opt('德国', v('intended_country'))}
            ${opt('英国', v('intended_country'))}
            ${opt('澳大利亚', v('intended_country'))}
            ${opt('美国', v('intended_country'))}
            ${opt('加拿大', v('intended_country'))}
          </select>
        </div>
        <div class="form-group">
          <label>意向专业</label>
          <input id="lead-major" class="input" value="${v('intended_major')}">
        </div>
        <div class="form-group">
          <label>家庭经济</label>
          <select id="lead-finance" class="select">
            <option value="">请选择</option>
            ${opt('富裕', v('family_finance'))}
            ${opt('中等', v('family_finance'))}
            ${opt('一般', v('family_finance'))}
          </select>
        </div>
        <div class="form-group">
          <label>语言水平</label>
          <input id="lead-lang" class="input" value="${v('language_level')}" placeholder="如：雅思6.5">
        </div>
        <div class="form-group">
          <label>客户状态</label>
          <select id="lead-status" class="select">
            ${opt('新增意向', v('status', '新增意向'))}
            ${opt('跟进中', v('status'))}
            ${opt('已签约', v('status'))}
            ${opt('已流失', v('status'))}
          </select>
        </div>
        <div class="form-group">
          <label>获客渠道</label>
          <input id="lead-source" class="input" value="${v('source_channel')}" placeholder="如：抖音/公众号/线下活动">
        </div>
        <div class="form-group">
          <label>意向评分</label>
          <input id="lead-score" class="input" type="number" min="0" max="100" value="${v('score', '0')}">
        </div>
        <div class="form-group" style="grid-column: span 2;">
          <label>背景信息</label>
          <textarea id="lead-bg" class="textarea" rows="3" placeholder="客户背景、需求、跟进备注等">${v('background_info')}</textarea>
        </div>
      </div>
    `;
  }

  function opt(label, selected) {
    return `<option value="${label}" ${label === selected ? 'selected' : ''}>${label}</option>`;
  }

  function statusTag(status) {
    const map = { '新增意向': 'tag-blue', '跟进中': 'tag-orange', '已签约': 'tag-green', '已流失': 'tag-red' };
    return `<span class="tag ${map[status] || 'tag-blue'}">${esc(status)}</span>`;
  }

  function scoreBadge(score) {
    if (!score && score !== 0) return '-';
    let cls = 'tag-blue';
    if (score >= 70) cls = 'tag-green';
    else if (score >= 40) cls = 'tag-orange';
    else cls = 'tag-red';
    return `<span class="tag ${cls}">${score}分</span>`;
  }

  function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  return { render, onMount };
})();
