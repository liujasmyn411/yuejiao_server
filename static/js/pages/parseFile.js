/**
 * 文件解析页 — 上传 PDF/Excel/TXT → 提取客户画像
 */
const ParseFilePage = (() => {
  function render() {
    return `
      <div class="card" style="max-width:700px">
        <h4 style="margin-bottom:8px">📎 客户文件解析</h4>
        <p class="text-muted" style="margin-bottom:20px">上传客户简历或信息文件（PDF / Excel / TXT），自动提取画像关键字段</p>
        <div class="upload-zone" id="upload-zone">
          <div class="upload-zone__icon">📂</div>
          <p>点击或拖拽文件到此处</p>
          <small class="text-muted">支持 PDF、Excel (.xlsx/.xls)、TXT，最大 10MB</small>
          <input type="file" id="file-input" accept=".pdf,.xlsx,.xls,.txt" style="display:none">
        </div>
        <div id="parse-loading" class="page-loading hidden">正在解析...</div>
        <div id="parse-result" class="mt-16"></div>
      </div>
    `;
  }

  function onMount() {
    const zone = document.getElementById('upload-zone');
    const input = document.getElementById('file-input');

    zone.onclick = () => input.click();
    zone.ondragover = (e) => { e.preventDefault(); zone.classList.add('upload-zone--active'); };
    zone.ondragleave = () => zone.classList.remove('upload-zone--active');
    zone.ondrop = (e) => {
      e.preventDefault();
      zone.classList.remove('upload-zone--active');
      const file = e.dataTransfer.files[0];
      if (file) parseFile(file);
    };
    input.onchange = () => {
      const file = input.files[0];
      if (file) parseFile(file);
    };
  }

  async function parseFile(file) {
    const loading = document.getElementById('parse-loading');
    const result = document.getElementById('parse-result');
    result.innerHTML = '';
    loading.classList.remove('hidden');

    try {
      const data = await API.upload('/api/customer/parse-file', file);
      loading.classList.add('hidden');

      if (!data.success) {
        result.innerHTML = `<div class="page-error">${data.message || '解析失败'}</div>`;
        return;
      }

      const profile = data.extracted_profile || {};
      result.innerHTML = `
        <div class="card">
          <h4 style="margin-bottom:12px">✅ 解析成功 — ${esc(data.filename)}</h4>
          <div class="parse-profile">
            ${renderProfileFields(profile)}
          </div>
          ${data.text ? `
            <details class="mt-16">
              <summary style="cursor:pointer;color:var(--color-text-secondary);font-weight:600">查看原始文本</summary>
              <pre class="parse-text mt-16">${esc(data.text.slice(0, 2000))}${data.text.length > 2000 ? '\n... (内容过长，已截断)' : ''}</pre>
            </details>
          ` : ''}
        </div>
      `;
    } catch (e) {
      loading.classList.add('hidden');
      result.innerHTML = `<div class="page-error">解析失败: ${e.message}</div>`;
    }
  }

  function renderProfileFields(profile) {
    const fields = [
      ['姓名', profile.name || profile.Name || profile.姓名],
      ['年龄', profile.age || profile.Age || profile.年龄],
      ['学历', profile.education || profile.Education || profile.学历],
      ['电话', profile.phone || profile.Phone || profile.电话 || profile.contact],
      ['邮箱', profile.email || profile.Email || profile.邮箱],
      ['意向国家', profile.intended_country || profile.country || profile.意向国家],
      ['意向专业', profile.intended_major || profile.major || profile.意向专业],
    ];
    return fields.filter(([_, v]) => v).map(([label, value]) => `
      <div class="parse-field">
        <span class="parse-field__label">${label}</span>
        <span class="parse-field__value">${esc(String(value))}</span>
      </div>
    `).join('') || '<p class="text-muted">未能提取到关键字段，请查看原始文本</p>';
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
