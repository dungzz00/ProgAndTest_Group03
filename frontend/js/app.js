const API = 'http://localhost:5000/api';

// ── Token storage ─────────────────────────────────────────────────────────────
const Token = {
  get:    ()      => localStorage.getItem('edums_token'),
  set:    (t)     => localStorage.setItem('edums_token', t),
  clear:  ()      => localStorage.removeItem('edums_token'),
};

// ── HTTP helpers ──────────────────────────────────────────────────────────────
async function apiCall(path, opts = {}) {
  const token = Token.get();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  try {
    const res = await fetch(API + path, { headers, ...opts });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  } catch (e) {
    return { ok: false, status: 0, data: { message: 'Không thể kết nối server. Hãy đảm bảo backend đang chạy.' } };
  }
}

const get  = p       => apiCall(p, { method: 'GET' });
const post = (p, b)  => apiCall(p, { method: 'POST',   body: JSON.stringify(b) });
const put  = (p, b)  => apiCall(p, { method: 'PUT',    body: JSON.stringify(b) });
const del  = p       => apiCall(p, { method: 'DELETE' });

// ── State ─────────────────────────────────────────────────────────────────────
let currentUser = null;

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, type = 'ok') {
  const c = document.getElementById('toast-container');
  if (!c) return;
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.innerHTML = `<span>${type === 'ok' ? '✓' : '✕'}</span><span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 3200);
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) e.target.classList.remove('open');
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
});

// ── Auth ──────────────────────────────────────────────────────────────────────
async function checkAuth() {
  if (!Token.get()) return false;
  const r = await get('/me');
  if (r.ok && r.data.user) { currentUser = r.data.user; return true; }
  Token.clear();
  return false;
}

function redirectToDashboard() {
  const map = { admin: 'pages/admin.html', teacher: 'pages/teacher.html', student: 'pages/student.html' };
  const isInPages = window.location.pathname.includes('/pages/');
  const base = isInPages ? '../' : '';
  // Detect if served from file:// or http://
  const prefix = window.location.protocol === 'file:' ? '' : '/';
  window.location.href = base + map[currentUser.role];
}

function loadUserUI() {
  const nm = document.getElementById('sidebar-user-name');
  const rl = document.getElementById('sidebar-user-role');
  const av = document.getElementById('sidebar-avatar');
  const labels = { admin: 'Quản trị viên', teacher: 'Giảng viên', student: 'Sinh viên' };
  if (nm) nm.textContent = currentUser.full_name;
  if (rl) rl.textContent = labels[currentUser.role] || currentUser.role;
  if (av) av.textContent = currentUser.full_name.charAt(0).toUpperCase();
}

async function logout() {
  Token.clear();
  currentUser = null;
  const isInPages = window.location.pathname.includes('/pages/');
  window.location.href = isInPages ? '../index.html' : 'index.html';
}

// ── Grade helpers ─────────────────────────────────────────────────────────────
function gradeClass(g) {
  if (g === null || g === undefined || g === '') return '';
  const n = parseFloat(g);
  if (isNaN(n)) return '';

  return n >= 8.5 ? 'gA'
       : n >= 8.0 ? 'gBplus'
       : n >= 7.0 ? 'gB'
       : n >= 6.5 ? 'gCplus'
       : n >= 5.5 ? 'gC'
       : n >= 5.0 ? 'gDplus'
       : n >= 4.0 ? 'gD'
       : 'gF';
}

function gradeLabel(l) {
  if (!l) return '<span class="badge bg_">Chưa có</span>';
  const m = {
    'A': 'bt',
    'B+': 'bplus',
    'B': 'bi',
    'C+': 'cplus',
    'C': 'ba',
    'D+': 'dplus',
    'D': 'br',
    'F': 'bf'
  };
  return `<span class="badge ${m[l] || 'bg_'}">${l}</span>`;
}

function calcGPA(grades) {
  const valid = (grades || []).filter(g => g.grade !== null && g.grade !== undefined && g.grade !== '');
  if (!valid.length) return '0.00';
  const tc = valid.reduce((s, g) => s + (parseInt(g.credits) || 3), 0);
  const w  = valid.reduce((s, g) => s + parseFloat(g.grade) * (parseInt(g.credits) || 3), 0);
  return tc ? (w / tc).toFixed(2) : '0.00';
}

// ── Expose ────────────────────────────────────────────────────────────────────
window.closeModal = closeModal;
window.openModal  = openModal;
window.logout     = logout;
