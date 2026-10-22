/**
 * Authentication utilities.
 * Guard pages, handle login/logout state.
 */

const Auth = (() => {
  function isLocalDemoMode() {
    return ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)
      && localStorage.getItem('task_demo_mode') === 'true';
  }

  function isLoggedIn() {
    return isLocalDemoMode() || !!Api.getToken();
  }

  function requireAuth() {
    if (!isLoggedIn()) {
      window.location.href = '/login.html';
      return false;
    }
    return true;
  }

  function requireGuest() {
    if (isLoggedIn()) {
      window.location.href = '/dashboard.html';
      return false;
    }
    return true;
  }

  async function initPage() {
    if (!requireAuth()) return false;

    // Local-only demo mode lets the frontend be tested before the backend is ready.
    if (isLocalDemoMode()) {
      if (!Api.getUser()) {
        Api.setUser({ id: 0, username: 'admin', full_name: 'مدیر آزمایشی', role: 'ADMIN', permissions: [] });
      }
      Api.setPermissions([]);
      renderUserInfo();
      setupSidebar();
      hideUnauthorizedNavItems();
      return true;
    }

    // Refresh user info
    try {
      const resp = await Api.getMe();
      if (resp && resp.data) {
        Api.setUser(resp.data);
        Api.setPermissions(resp.data.permissions || []);
      }
    } catch (e) {
      // Token is invalid — clearAuth already handles redirect
      return false;
    }

    renderUserInfo();
    setupSidebar();
    hideUnauthorizedNavItems();
    return true;
  }

  function renderUserInfo() {
    const user = Api.getUser();
    if (!user) return;

    // Header user
    const nameEl = document.getElementById('header-user-name');
    const roleEl = document.getElementById('header-user-role');
    const avatarEl = document.getElementById('header-user-avatar');

    if (nameEl) nameEl.textContent = user.full_name || user.username;
    if (roleEl) roleEl.textContent = user.role === 'ADMIN' ? 'مدیر سیستم' : 'کاربر';
    if (avatarEl) {
      const name = user.full_name || user.username;
      avatarEl.textContent = name.charAt(0);
    }
  }

  function setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    const overlay = document.getElementById('sidebar-overlay');
    const mainContent = document.getElementById('main-content');
    const header = document.getElementById('header');

    if (!sidebar) return;

    // Restore collapsed state
    const collapsed = localStorage.getItem('sidebar_collapsed') === 'true';
    if (collapsed) {
      sidebar.classList.add('collapsed');
      mainContent?.classList.add('sidebar-collapsed');
      header?.classList.add('sidebar-collapsed');
    }

    toggleBtn?.addEventListener('click', () => {
      const isMobile = window.innerWidth <= 768;
      if (isMobile) {
        sidebar.classList.toggle('mobile-open');
        overlay?.classList.toggle('active');
      } else {
        const isCollapsed = sidebar.classList.toggle('collapsed');
        mainContent?.classList.toggle('sidebar-collapsed', isCollapsed);
        header?.classList.toggle('sidebar-collapsed', isCollapsed);
        localStorage.setItem('sidebar_collapsed', isCollapsed);
      }
    });

    overlay?.addEventListener('click', () => {
      sidebar.classList.remove('mobile-open');
      overlay.classList.remove('active');
    });

    // Mark active nav item
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-item').forEach(item => {
      const href = item.getAttribute('href') || '';
      if (href.endsWith(currentPage)) item.classList.add('active');
    });
  }

  function hideUnauthorizedNavItems() {
    const user = Api.getUser();
    if (!user) return;
    if (user.role === 'ADMIN') return; // Admin sees everything

    document.querySelectorAll('[data-permission]').forEach(el => {
      const perm = el.dataset.permission;
      if (!Api.hasPermission(perm)) {
        el.style.display = 'none';
      }
    });
  }

  async function logout() {
    try { await Api.logout(); } catch {}
    Api.clearAuth();
    window.location.href = '/login.html';
  }

  return { isLoggedIn, requireAuth, requireGuest, initPage, renderUserInfo, setupSidebar, hideUnauthorizedNavItems, logout };
})();