/**
 * NL2SQL 自然语言查询页 — 查询/更新两种模式
 */
const Nl2sqlPage = (() => {
  let mode = 'query'; // 'query' | 'update'

  function render() {
    return `
      <div class="page-header">
        <h3 style="margin:0">🔍 自然语言数据库查询</h3>
      </div>
      <div class="card mt-16">
        <div class="flex-between mb-16">
          <div class="filter-tabs" id="nl2sql-mode-tabs">
            <button class="filter-tab filter-tab--active" data-mode="query">数据查询</button>
            <button class="filter-tab" data-mode="update">数据更新</button>
          </div>
        </div>
        <div class="form-group">
          <label>用自然语言描述你想做什么</label>
          <textarea id="nl2sql-input" class="textarea" rows="3" placeholder="例如：查询所有意向国家为新加坡的客户  或  把学生ID为1的客户状态改为已签约"></textarea>
        </div>
        <button class="btn btn-primary" id="btn-nl2sql-run">执行</button>
      </div>
      <div id="nl2sql-result" class="mt-16"></div>
    `;
  }

  function onMount() {
    document.getElementById('btn-nl2sql-run').onclick = runQuery;
    document.getElementById('nl2sql-input').onkeydown = (e) => {
      if (e.key === 'Enter' && e.ctrlKey) runQuery();
    };
    document.querySelectorAll('#nl2sql-mode-tabs .filter-tab').forEach(tab => {
      tab.onclick = () => {
        document.querySelectorAll('#nl2sql-mode-tabs .filter-tab').forEach(t => t.classList.remove('filter-tab--active'));
        tab.classList.add('filter-tab--active');
        mode = tab.dataset.mode;
        document.getElementById('nl2sql-result').innerHTML = '';
      };
    });
    document.getElementById('nl2sql-result').innerHTML =
      '<div class="page-placeholder"><div class="placeholder-icon">🔍</div><h3>输入自然语言开始查询</h3><p>支持的数据表：意向客户、反馈工单、请假申请、教务信息</p></div>';
  }

  async function runQuery() {
    const input = document.getElementById('nl2sql-input').value.trim();
    if (!input) { Toast.show('请输入查询内容', 'warning'); return; }

    const container = document.getElementById('nl2sql-result');
    container.innerHTML = '<div class="page-loading">执行中...</div>';

    try {
      const endpoint = mode === 'query' ? '/api/enterprise/nl2sql' : '/api/enterprise/nl2sql/update';
      const data = await API.post(endpoint, { message: input });

      // 构建结果展示
      let resultHtml = '<div class="card"><h4 style="margin-bottom:12px">执行结果</h4>';

      // 显示生成的 SQL（如果有）
      if (data.sql || data.generated_sql) {
        resultHtml += `
          <div class="form-group">
            <label>生成的 SQL</label>
            <pre style="background:var(--color-bg);padding:12px;border-radius:6px;font-size:12px;overflow-x:auto;white-space:pre-wrap">${esc(data.sql || data.generated_sql)}</pre>
          </div>
        `;
      }

      // 显示解释
      if (data.explanation) {
        resultHtml += `<p class="text-muted mb-16">${esc(data.explanation)}</p>`;
      }

      // 显示查询结果表格
      const rows = data.data || data.results;
      if (rows && Array.isArray(rows) && rows.length) {
        resultHtml += `<p class="text-muted mb-8">共 ${data.count || rows.length} 条记录</p>`;
        const columns = Object.keys(rows[0]);
        resultHtml += `
          <div class="table-container">
            <table class="table">
              <thead><tr>${columns.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>
              <tbody>
                ${rows.map(row => `
                  <tr>${columns.map(c => `<td>${esc(String(row[c] ?? '-'))}</td>`).join('')}</tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      } else if (rows && Array.isArray(rows) && !rows.length) {
        resultHtml += '<div class="page-placeholder"><div class="placeholder-icon">📭</div><h3>查询无结果</h3></div>';
      }

      // 显示更新/操作结果
      if (data.type === 'UPDATE' && data.data && data.data.length) {
        const upd = data.data[0];
        resultHtml += `<div class="mt-16"><span class="tag tag-green">操作成功</span> ${esc(upd.message || '更新完成')}（影响行数: ${upd.affected_rows || 0}）</div>`;
      }
      if (data.success) {
        resultHtml += `<div class="mt-16"><span class="tag tag-green">操作成功</span> ${esc(data.message || '')}</div>`;
      }

      // 显示其他返回信息
      if (data.response) {
        resultHtml += `<p class="mt-16">${esc(data.response)}</p>`;
      }

      resultHtml += '</div>';
      container.innerHTML = resultHtml;
      Toast.show(mode === 'query' ? '查询完成' : '更新完成', 'success');
    } catch (e) {
      container.innerHTML = `<div class="page-error">执行失败: ${e.message}</div>`;
    }
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
