/**
 * Authentication utilities.
 * Guard pages, handle login/logout state.
 */

const Auth = (() => {
  function isLoggedIn() {
    return !!Api.getToken();
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
    watchDynamicPermissions();
    return true;
  }

  function renderUserInfo() {
    const user = Api.getCurrentUser();
    if (!user) return;

    // Header user
    const nameEl = document.getElementById('header-user-name');
    const roleEl = document.getElementById('header-user-role');
    const avatarEl = document.getElementById('header-user-avatar');

    if (nameEl) nameEl.textContent = user.full_name || user.username;
    if (roleEl) roleEl.textContent = user.role === 'ADMIN' ? 'پنل مدیریت' : 'پرسنل';
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

    // Notification dropdown behavior is handled by ui.js.
    const notificationPanel = document.getElementById('notification-panel');
    const notificationToggle = document.getElementById('notification-toggle');
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && notificationPanel) {
        notificationPanel.classList.add('hidden');
        notificationToggle?.setAttribute('aria-expanded', 'false');
      }
    });
    sidebar.querySelectorAll('a.nav-item').forEach(link => link.addEventListener('click', () => {
      if (window.innerWidth <= 768) {
        sidebar.classList.remove('mobile-open');
        overlay?.classList.remove('active');
      }
    }));

    // Mark active nav item
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-item').forEach(item => {
      const href = item.getAttribute('href') || '';
      if (href.endsWith(currentPage)) item.classList.add('active');
    });
  }

  function hideUnauthorizedNavItems(root = document) {
    const user = Api.getCurrentUser();
    if (!user) return;
    const elements = [];
    if (root.matches?.('[data-permission]')) elements.push(root);
    elements.push(...(root.querySelectorAll?.('[data-permission]') || []));
    elements.forEach(el => {
      const allowed = user.role === 'ADMIN' || Api.hasPermission(el.dataset.permission);
      if (!allowed) {
        el.dataset.permissionHidden = 'true';
        el.style.display = 'none';
        el.setAttribute('aria-hidden', 'true');
      } else if (el.dataset.permissionHidden === 'true') {
        delete el.dataset.permissionHidden;
        el.style.removeProperty('display');
        el.removeAttribute('aria-hidden');
      }
    });
  }

  let permissionObserver = null;
  function watchDynamicPermissions() {
    if (permissionObserver || !document.body || !window.MutationObserver) return;
    permissionObserver = new MutationObserver(records => {
      records.forEach(record => record.addedNodes.forEach(node => {
        if (node.nodeType === Node.ELEMENT_NODE) hideUnauthorizedNavItems(node);
      }));
    });
    permissionObserver.observe(document.body, { childList: true, subtree: true });
  }

  async function logout() {
    try { await Api.logout(); } catch {}
    Api.clearAuth();
    window.location.href = '/login.html';
  }

  return { isLoggedIn, requireAuth, requireGuest, initPage, renderUserInfo, setupSidebar, hideUnauthorizedNavItems, logout };
})();