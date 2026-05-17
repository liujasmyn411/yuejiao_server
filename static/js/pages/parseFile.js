/**
 * 文件解析页 — 上传 PDF/Excel/TXT → 提取画像 → 意向研判
 */
const ParseFilePage = (() => {
  function render() {
    return `
      <div class="card" style="max-width:700px">
        <h4 style="margin-bottom:8px">📎 客户文件解析 & 意向研判</h4>
        <p class="text-muted" style="margin-bottom:20px">上传客户简历或信息文件（PDF / Excel / TXT），自动提取画像并研判是否为意向客户</p>
        <div class="upload-zone" id="upload-zone">
          <div class="upload-zone__icon">📂</div>
          <p>点击或拖拽文件到此处</p>
          <small class="text-muted">支持 PDF、Excel (.xlsx/.xls)、TXT，最大 10MB</small>
          <input type="file" id="file-input" accept=".pdf,.xlsx,.xls,.txt" style="display:none">
        </div>
        <div id="parse-loading" class="page-loading hidden">正在解析并研判...</div>
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
      const assessment = data.assessment || {};
      const isIntended = assessment.is_intended;

      result.innerHTML = `
        <div class="card">
          <h4 style="margin-bottom:12px">✅ 解析成功 — ${esc(data.filename)}</h4>
          <div class="parse-profile">
            ${renderProfileFields(profile)}
          </div>

          ${renderAssessment(assessment)}

          ${data.text ? `
            <details class="mt-16">
              <summary style="cursor:pointer;color:var(--color-text-secondary);font-weight:600">查看原始文本</summary>
              <pre class="parse-text mt-16">${esc(data.text.slice(0, 2000))}${data.text.length > 2000 ? '\n... (内容过长，已截断)' : ''}</pre>
            </details>
          ` : ''}
        </div>
      `;
      Toast.show('文件解析成功', 'success');
    } catch (e) {
      loading.classList.add('hidden');
      result.innerHTML = `<div class="page-error">解析失败: ${e.message}</div>`;
    }
  }

  function renderAssessment(assessment) {
    if (!assessment || assessment.score === undefined) return '';
    const isIntended = assessment.is_intended;
    const icon = isIntended ? '✅' : '❌';
    const label = isIntended ? '符合意向客户条件' : '暂不符合意向客户条件';
    const color = isIntended ? '#16a34a' : '#dc2626';
    return `
      <div class="card mt-16" style="border-left: 4px solid ${color}; background: ${isIntended ? '#f0fdf4' : '#fef2f2'}">
        <h4 style="margin-bottom:8px">🔍 ${icon} 意向研判结果</h4>
        <div style="margin-bottom:4px"><strong>判定：</strong><span style="color:${color};font-weight:700">${label}</span></div>
        <div style="margin-bottom:4px"><strong>综合评分：</strong><span style="font-weight:700">${assessment.score}/100</span></div>
        ${assessment.matched_program ? `<div style="margin-bottom:4px"><strong>匹配项目：</strong>${esc(assessment.matched_program)}</div>` : ''}
        ${assessment.reasons && assessment.reasons.length ? `
          <div style="margin-top:8px"><strong>研判依据：</strong>
            <ul style="margin:4px 0;padding-left:20px">${assessment.reasons.map(r => `<li>${esc(r)}</li>`).join('')}</ul>
          </div>
        ` : ''}
        ${assessment.lead_created ? `<div style="margin-top:8px" class="text-success">✅ 已自动录入意向客户表（ID: ${assessment.lead_id}）</div>` : ''}
        ${!isIntended ? '<div style="margin-top:8px" class="text-muted">💡 该文件内容暂未达到意向客户判定标准，建议持续关注</div>' : ''}
      </div>
    `;
  }

  function renderProfileFields(profile) {
    const fields = [
      ['姓名', profile.name || profile.Name || profile.姓名],
      ['性别', profile.gender || profile.Gender || profile.性别],
      ['年龄', profile.age || profile.Age || profile.年龄],
      ['学历', profile.education || profile.Education || profile.学历],
      ['电话', profile.phone || profile.Phone || profile.电话 || profile.contact],
      ['邮箱', profile.email || profile.Email || profile.邮箱],
      ['微信', profile.wechat || profile.Wechat || profile.微信],
      ['意向国家', profile.intended_country || profile.country || profile.意向国家],
      ['意向专业', profile.intended_major || profile.major || profile.意向专业],
      ['语言水平', profile.language_level || profile.语言水平],
      ['家庭经济', profile.family_finance || profile.家庭经济],
      ['学校', profile.school || profile.School || profile.学校],
      ['地址', profile.address || profile.Address || profile.地址],
      ['备注', profile.remark || profile.Remark || profile.备注],
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
