/**
 * UI Component helpers: Toast, Modal, Confirm, Pagination, Tabs
 */

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>\"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[char]));
}

// ─── Toast ──────────────────────────────────────
const Toast = (() => {
  let container;

  function getContainer() {
    if (!container) {
      container = document.getElementById('toast-container');
      if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
      }
    }
    return container;
  }

  const icons = { success: '&#x2713;', error: '&#x2716;', warning: '&#x26A0;', info: '&#x2139;' };
  const titles = { success: 'موفق', error: 'خطا', warning: 'هشدار', info: 'اطلاع' };

  function show(type, message, duration = 4000) {
    const c = getContainer();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || '&#x1F4E2;'}</span>
      <div class="toast-body">
        <div class="toast-title">${escapeHtml(titles[type] || '')}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
      </div>
      <button class="toast-dismiss" onclick="this.closest('.toast').remove()">&#x2715;</button>
    `;
    c.appendChild(toast);
    if (duration > 0) {
      setTimeout(() => toast.remove(), duration);
    }
  }

  return {
    success: (msg, d) => show('success', msg, d),
    error:   (msg, d) => show('error',   msg, d),
    warning: (msg, d) => show('warning', msg, d),
    info:    (msg, d) => show('info',    msg, d),
  };
})();


// ─── Modal ──────────────────────────────────────
const Modal = (() => {
  function open(id) {
    const overlay = document.getElementById(id);
    if (overlay) overlay.classList.add('active');
  }

  function close(id) {
    const overlay = document.getElementById(id);
    if (overlay) overlay.classList.remove('active');
  }

  function closeAll() {
    document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
  }

  // Close on overlay click
  document.addEventListener('click', e => {
    if (e.target.classList.contains('modal-overlay')) {
      e.target.classList.remove('active');
    }
  });

  // Close on Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeAll();
  });

  return { open, close, closeAll };
})();


// ─── Confirm Dialog ─────────────────────────────
function confirmAction(message, onConfirm, title = 'تأیید عملیات') {
  const id = 'confirm-modal-' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.className = 'modal-overlay active';
  div.innerHTML = `
    <div class="modal modal-sm">
      <div class="modal-header">
        <h3 class="modal-title">${escapeHtml(title)}</h3>
        <button class="modal-close" onclick="document.getElementById('${id}').remove()">&#x2715;</button>
      </div>
      <div class="modal-body">
        <p style="font-size:15px; color: var(--text-secondary); line-height:1.7">${escapeHtml(message)}</p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="document.getElementById('${id}').remove()">انصراف</button>
        <button class="btn btn-danger" id="${id}-confirm">تأیید</button>
      </div>
    </div>
  `;
  document.body.appendChild(div);
  document.getElementById(`${id}-confirm`).addEventListener('click', () => {
    div.remove();
    onConfirm();
  });
}


// ─── Pagination ─────────────────────────────────
function renderPagination(containerId, currentPage, totalPages, totalItems, pageSize, onPageChange) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const start = (currentPage - 1) * pageSize + 1;
  const end = Math.min(currentPage * pageSize, totalItems);

  let pages = '';
  const range = getPaginationRange(currentPage, totalPages);
  range.forEach(p => {
    if (p === '...') {
      pages += `<span style="padding:0 4px; color:var(--text-muted)">...</span>`;
    } else {
      pages += `<button class="page-btn ${p === currentPage ? 'active' : ''}" data-page="${p}">${p}</button>`;
    }
  });

  container.innerHTML = `
    <span class="pagination-info">نمایش ${start}–${end} از ${totalItems}</span>
    <div class="pagination-controls">
      <button class="page-btn" data-page="${currentPage - 1}" ${currentPage <= 1 ? 'disabled' : ''}>›</button>
      ${pages}
      <button class="page-btn" data-page="${currentPage + 1}" ${currentPage >= totalPages ? 'disabled' : ''}>‹</button>
    </div>
  `;

  container.querySelectorAll('.page-btn:not([disabled])').forEach(btn => {
    btn.addEventListener('click', () => onPageChange(parseInt(btn.dataset.page)));
  });
}

function getPaginationRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, '...', total];
  if (current >= total - 3) return [1, '...', total-4, total-3, total-2, total-1, total];
  return [1, '...', current-1, current, current+1, '...', total];
}


// ─── Tabs ────────────────────────────────────────
function initTabs(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const buttons = container.querySelectorAll('.tab-btn');
  const contents = container.querySelectorAll('.tab-content');

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      buttons.forEach(b => b.classList.remove('active'));
      contents.forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(target)?.classList.add('active');
    });
  });

  // Activate first tab
  if (buttons.length) buttons[0].click();
}


// ─── Format helpers ──────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = /^\d{4}-\d{2}-\d{2}$/.test(String(dateStr))
    ? new Date(Number(dateStr.slice(0, 4)), Number(dateStr.slice(5, 7)) - 1, Number(dateStr.slice(8, 10)), 12)
    : new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('fa-IR-u-ca-persian-nu-arabext', { calendar: 'persian', numberingSystem: 'arabext', year: 'numeric', month: 'long', day: 'numeric' });
}

function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('fa-IR-u-ca-persian-nu-arabext', { calendar: 'persian', numberingSystem: 'arabext', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}


// ─── Status / Priority Labels ─────────────────────
const STATUS_LABELS = {
  TODO: 'در انتظار',
  IN_PROGRESS: 'در حال انجام',
  SUBMITTED: 'ارسال شده',
  NEEDS_REVISION: 'نیاز به اصلاح',
  APPROVED: 'تأیید شده',
  DONE: 'انجام شده',
};

const PRIORITY_LABELS = {
  LOW: 'کم',
  MEDIUM: 'متوسط',
  HIGH: 'بالا',
  URGENT: 'فوری',
};

const PROJECT_STATUS_LABELS = {
  PLANNED: 'برنامه‌ریزی شده',
  ACTIVE: 'فعال',
  COMPLETED: 'تکمیل شده',
  ARCHIVED: 'بایگانی شده',
};

function statusBadge(status) {
  const label = STATUS_LABELS[status] || escapeHtml(status);
  const cls = `status-${status.toLowerCase()}`;
  return `<span class="badge ${cls}">${label}</span>`;
}

function priorityBadge(priority) {
  const label = PRIORITY_LABELS[priority] || escapeHtml(priority);
  const cls = `priority-${priority.toLowerCase()}`;
  return `<span class="badge ${cls}">${label}</span>`;
}

function projectStatusBadge(status) {
  const label = PROJECT_STATUS_LABELS[status] || escapeHtml(status);
  const map = { PLANNED: 'badge-info', ACTIVE: 'badge-success', COMPLETED: 'badge-primary', ARCHIVED: 'badge-gray' };
  return `<span class="badge ${map[status] || 'badge-gray'}">${label}</span>`;
}

function progressBar(value) {
  const pct = Math.min(100, Math.max(0, value || 0));
  return `
    <div class="progress-bar-wrapper">
      <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
      <span class="progress-text">${pct}%</span>
    </div>
  `;
}


// ─── Loading State ────────────────────────────────
function setLoading(btn, loading) {
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner spinner-sm" style="border-color:rgba(255,255,255,0.3); border-top-color:white"></span>';
  } else {
    btn.disabled = false;
    if (btn.dataset.originalText) btn.innerHTML = btn.dataset.originalText;
  }
}


// ─── Error display ────────────────────────────────
function showFieldError(fieldId, message) {
  const field = document.getElementById(fieldId);
  if (!field) return;
  field.classList.add('error');
  let err = field.parentElement.querySelector('.form-error');
  if (!err) {
    err = document.createElement('div');
    err.className = 'form-error';
    field.parentElement.appendChild(err);
  }
  err.textContent = message;
}

function clearFieldErrors(formId) {
  const form = document.getElementById(formId);
  if (!form) return;
  form.querySelectorAll('.form-control.error').forEach(el => el.classList.remove('error'));
  form.querySelectorAll('.form-error').forEach(el => el.remove());
}

// ─── Jalali display for native date controls ──────
(function initJalaliDateFields() {
  const nativeValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
  if (!nativeValue) return;
  document.querySelectorAll('input[type="date"]').forEach(input => {
    if (input.dataset.jalaliReady === 'true') return;
    input.dataset.jalaliReady = 'true';
    const wrapper = document.createElement('span');
    wrapper.className = 'jalali-date-wrap';
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);
    const display = document.createElement('span');
    display.className = 'jalali-date-display';
    display.setAttribute('aria-hidden', 'true');
    wrapper.appendChild(display);
    const sync = () => {
      const value = nativeValue.get.call(input);
      display.textContent = value ? formatDate(value) : 'انتخاب تاریخ شمسی';
    };
    Object.defineProperty(input, 'value', {
      configurable: true,
      enumerable: true,
      get() { return nativeValue.get.call(this); },
      set(value) { nativeValue.set.call(this, value); sync(); }
    });
    input.addEventListener('change', sync);
    input.addEventListener('input', sync);
    input.setAttribute('aria-label', input.getAttribute('aria-label') || 'تاریخ شمسی');
    sync();
  });
})();

// ─── Shared notification center ──────────────────
(function initNotificationCenter() {
  document.querySelectorAll('[data-admin-only="true"]').forEach(el => { if (Api.getCurrentUser()?.role !== 'ADMIN') el.remove(); });
  const toggle = document.getElementById('notification-toggle');
  const panel = document.getElementById('notification-panel');
  const list = document.getElementById('notification-list');
  const dot = document.getElementById('notification-dot');
  const clear = document.getElementById('notification-clear');
  if (!toggle || !panel || !list || typeof Api === 'undefined' || !Api.getToken()) return;

  let loaded = false;
  const render = async () => {
    try {
      const response = await Api.getNotifications();
      const data = response.data || {};
      const items = data.items || [];
      dot.style.display = data.unread_count > 0 ? 'block' : 'none';
      dot.setAttribute('aria-label', data.unread_count > 0 ? String(data.unread_count) : '');
      if (!items.length) {
        list.className = 'notification-empty';
        list.innerHTML = '<p>اعلانی برای نمایش وجود ندارد.</p>';
        loaded = true;
        return;
      }
      list.className = 'notification-items';
      list.innerHTML = items.map(n => `
        <article class="notification-item ${n.is_read ? '' : 'unread'}" data-notification-id="${Number(n.id)}">
          <div class="notification-item-title">${escapeHtml(n.title)}</div>
          <div class="notification-item-message">${escapeHtml(n.message).replace(/\\n/g, '<br>')}</div>
          <div class="notification-item-meta">${formatDateTime(n.created_at)} · ${n.scope === 'public' ? 'عمومی' : 'خصوصی'} ${n.is_read ? '' : '<button type="button" class="notification-mark-read" data-read-id="' + Number(n.id) + '">خواندم</button>'}</div>
        </article>
      `).join('');
      loaded = true;
    } catch (error) {
      list.className = 'notification-empty';
      list.textContent = error.message || 'بارگذاری اعلان‌ها ناموفق بود.';
    }
  };

  toggle.addEventListener('click', async () => {
    const opening = panel.classList.contains('hidden');
    panel.classList.toggle('hidden', !opening);
    toggle.setAttribute('aria-expanded', String(opening));
    if (opening || !loaded) await render();
  });
  document.addEventListener('click', async event => {
    const markButton = event.target.closest('[data-read-id]');
    if (markButton) {
      try {
        await Api.markNotificationRead(Number(markButton.dataset.readId));
        await render();
      } catch (error) { Toast.error(error.message || 'ثبت وضعیت اعلان ناموفق بود'); }
    } else if (!event.target.closest('.notification-wrap') && !panel.classList.contains('hidden')) {
      panel.classList.add('hidden');
      toggle.setAttribute('aria-expanded', 'false');
    }
  });
  if (clear) clear.addEventListener('click', async () => {
    try {
      await Api.markAllNotificationsRead();
      await render();
    } catch (error) { Toast.error(error.message || 'ثبت وضعیت اعلان‌ها ناموفق بود'); }
  });
  render();
  window.setInterval(render, 60000);
})();
