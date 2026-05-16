/**
 * 画像研判页 — 输入客户画像 → 匹配推荐项目
 */
const ProfileMatchPage = (() => {
  function render() {
    return `
      <div class="profile-match">
        <div class="card">
          <h4 style="margin-bottom:16px">🎯 客户画像研判</h4>
          <p class="text-muted" style="margin-bottom:20px">输入客户基本信息，自动匹配最适合的留学项目</p>
          <div class="form-grid">
            <div class="form-group">
              <label>年龄</label>
              <input id="pm-age" class="input" type="number" placeholder="例如 20">
            </div>
            <div class="form-group">
              <label>学历</label>
              <select id="pm-edu" class="select">
                <option value="">请选择</option>
                <option>初中</option><option>高中</option><option>职高</option>
                <option>中专</option><option>大专</option><option>本科</option>
                <option>硕士</option><option>博士</option>
              </select>
            </div>
            <div class="form-group">
              <label>意向国家</label>
              <select id="pm-country" class="select">
                <option value="">请选择</option>
                <option>新加坡</option><option>德国</option><option>英国</option>
                <option>澳大利亚</option><option>美国</option><option>加拿大</option>
              </select>
            </div>
            <div class="form-group" style="display:flex;align-items:flex-end">
              <button id="btn-match" class="btn btn-primary btn-block">🔍 开始匹配</button>
            </div>
          </div>
        </div>
        <div id="match-results" class="mt-16"></div>
      </div>
    `;
  }

  function onMount() {
    document.getElementById('btn-match').onclick = doMatch;
  }

  async function doMatch() {
    const age = document.getElementById('pm-age').value;
    const education = document.getElementById('pm-edu').value;
    const intended_country = document.getElementById('pm-country').value;
    if (!age && !education && !intended_country) {
      Toast.show('请至少填写一项信息', 'warning'); return;
    }
    const results = document.getElementById('match-results');
    results.innerHTML = '<div class="page-loading">匹配中...</div>';
    try {
      const params = new URLSearchParams();
      if (age) params.set('age', age);
      if (education) params.set('education', education);
      if (intended_country) params.set('intended_country', intended_country);
      const data = await API.post(`/api/customer/profile-match?${params.toString()}`, null);
      const matches = data.matches || [];
      if (!matches.length) {
        results.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">🔍</div><h3>暂无匹配项目</h3><p>尝试调整筛选条件</p></div>';
        return;
      }
      results.innerHTML = `
        <h4 style="margin-bottom:12px">匹配结果（共 ${matches.length} 个）</h4>
        <div class="match-list">
          ${matches.map((m, i) => `
            <div class="card match-card">
              <div class="flex-between mb-16">
                <div class="flex-center gap-12">
                  <span class="match-rank">#${i + 1}</span>
                  <div>
                    <h4>${esc(m.project_name)}</h4>
                    <span class="text-muted">${esc(m.category)} · ${esc(m.country)}</span>
                  </div>
                </div>
                <div class="match-score">${m.match_score} 分</div>
              </div>
              <p class="text-muted mb-16">${esc(m.description || '')}</p>
              <div class="match-reasons">
                ${(m.match_reasons || []).map(r => `<span class="tag tag-blue">${esc(r)}</span>`).join(' ')}
              </div>
            </div>
          `).join('')}
        </div>
      `;
    } catch (e) {
      results.innerHTML = `<div class="page-error">匹配失败: ${e.message}</div>`;
    }
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
