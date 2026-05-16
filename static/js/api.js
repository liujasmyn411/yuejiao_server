/**
 * API 请求封装层 — 自动带 JWT、统一错误处理
 */
const API = (() => {
  const BASE = '';

  function getToken() {
    return localStorage.getItem('access_token');
  }

  function headers(isJson = true) {
    const h = {};
    const token = getToken();
    if (token) h['Authorization'] = `Bearer ${token}`;
    if (isJson) h['Content-Type'] = 'application/json';
    return h;
  }

  async function request(url, options = {}) {
    const { method = 'GET', body, isJson = true } = options;
    const config = { method, headers: headers(isJson) };
    if (body && isJson) config.body = JSON.stringify(body);
    if (body && !isJson) config.body = body;

    try {
      const res = await fetch(BASE + url, config);
      if (res.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        window.location.hash = '#/login';
        return null;
      }
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.message || `请求失败 (${res.status})`);
      }
      return data;
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        Toast.show('网络错误，请检查后端服务是否启动', 'error');
      }
      throw err;
    }
  }

  return {
    get(url) { return request(url); },
    post(url, body, isJson = true) { return request(url, { method: 'POST', body, isJson }); },
    put(url, body) { return request(url, { method: 'PUT', body }); },
    delete(url) { return request(url, { method: 'DELETE' }); },
    upload(url, file, extraFields = {}) {
      const fd = new FormData();
      fd.append('file', file);
      Object.keys(extraFields).forEach(k => fd.append(k, extraFields[k]));
      return request(url, { method: 'POST', body: fd, isJson: false });
    },
  };
})();
