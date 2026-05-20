// 共用工具函数
function getKey() { return localStorage.getItem('qwen2api_key') || '' }
function authHeaders() { return { Authorization: 'Bearer ' + getKey() } }
function jsonHeaders() { return { ...authHeaders(), 'Content-Type': 'application/json' } }

function logout() { localStorage.removeItem('qwen2api_key'); location.href = '/admin/login' }

function showToast(msg, duration) {
  if (!duration) duration = 2500;
  let wrap = document.querySelector('.toast-wrap');
  if (!wrap) { wrap = document.createElement('div'); wrap.className = 'toast-wrap'; document.body.appendChild(wrap) }
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  wrap.appendChild(t);
  setTimeout(() => t.remove(), duration);
}

// 渲染 header
function renderHeader(active) {
  const header = document.getElementById('admin-header');
  if (!header) return;
  header.innerHTML = `
    <div class="admin-header-inner">
      <div><a href="https://github.com/jiujiu532/Qwen2api" target="_blank" style="display:inline-flex;align-items:center;gap:8px;color:inherit;text-decoration:none"><svg height="20" width="20" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg><span class="admin-brand">Qwen2api</span></a></div>
      <nav class="admin-nav">
        <a href="/admin/accounts" class="${active === 'accounts' ? 'active' : ''}">账户管理</a>
        <a href="/admin/config" class="${active === 'config' ? 'active' : ''}">配置管理</a>
        <a href="/admin/cache" class="${active === 'cache' ? 'active' : ''}">缓存管理</a>
        <a href="/admin/register" class="${active === 'register' ? 'active' : ''}">扩容中心</a>
      </nav>
      <div class="admin-header-right">
        <span class="admin-version">v3.0</span>
        <button class="admin-logout" onclick="logout()">登出</button>
      </div>
    </div>
  `;
}

// 鉴权检查
async function checkAuth() {
  const key = getKey();
  if (!key) { location.href = '/admin/login'; return false }
  try {
    const r = await fetch('/api/admin/settings', { headers: authHeaders() });
    if (!r.ok) { location.href = '/admin/login'; return false }
    return true;
  } catch { location.href = '/admin/login'; return false }
}
