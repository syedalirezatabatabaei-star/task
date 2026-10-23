/**
 * Central API Client
 * Handles all communication with the FastAPI backend.
 */

const API_BASE = window.API_BASE_URL || '/api/v1';

const Api = (() => {
  // ─── Token Management ─────────────────────────
  function getToken() {
    return localStorage.getItem('access_token');
  }

  function setToken(token) {
    localStorage.setItem('access_token', token);
  }

  function clearAuth() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_user');
    localStorage.removeItem('user_permissions');
  }

  function getUser() {
    const u = localStorage.getItem('current_user');
    return u ? JSON.parse(u) : null;
  }

  function setUser(user) {
    localStorage.setItem('current_user', JSON.stringify(user));
  }

  function getPermissions() {
    const p = localStorage.getItem('user_permissions');
    return p ? JSON.parse(p) : [];
  }

  function setPermissions(perms) {
    localStorage.setItem('user_permissions', JSON.stringify(perms));
  }

  function hasPermission(code) {
    const user = getUser();
    if (user && user.role === 'ADMIN') return true;
    return getPermissions().includes(code);
  }

  // ─── HTTP Core ────────────────────────────────
  async function request(method, path, body = null, isFormData = false) {
    const token = getToken();
    const headers = {};

    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (!isFormData && body) headers['Content-Type'] = 'application/json';

    const options = {
      method,
      headers,
    };

    if (body) {
      options.body = isFormData ? body : JSON.stringify(body);
    }

    const url = path.startsWith('http') ? path : `${API_BASE}${path}`;

    let response;
    try {
      response = await fetch(url, options);
    } catch (err) {
      throw { success: false, message: 'خطا در اتصال به سرور. لطفاً اتصال اینترنت خود را بررسی کنید.', code: 'NETWORK_ERROR' };
    }

    if (response.status === 401) {
      clearAuth();
      if (!window.location.pathname.endsWith('login.html')) {
        window.location.href = '/login.html';
      }
      throw { success: false, message: 'نشست شما منقضی شده است. لطفاً دوباره وارد شوید.', code: 'SESSION_EXPIRED' };
    }

    if (response.status === 403) {
      let data = {};
      try { data = await response.json(); } catch {}
      throw { success: false, message: data.detail?.message || 'شما اجازه دسترسی به این بخش را ندارید.', code: 'FORBIDDEN' };
    }

    let data;
    try {
      data = await response.json();
    } catch {
      if (!response.ok) throw { success: false, message: 'خطای سرور', code: 'SERVER_ERROR' };
      return { success: true };
    }

    if (!response.ok) {
      const detail = data.detail || data;
      throw {
        success: false,
        message: detail.message || detail || 'خطا در انجام عملیات',
        code: detail.code || 'ERROR',
      };
    }

    return data;
  }

  // ─── Public Methods ───────────────────────────
  return {
    // Accessors
    getToken, setToken, clearAuth, getCurrentUser: getUser, setUser, getPermissions, setPermissions, hasPermission,

    // HTTP verbs
    get:    (path)              => request('GET',    path),
    post:   (path, body)        => request('POST',   path, body),
    put:    (path, body)        => request('PUT',    path, body),
    patch:  (path, body)        => request('PATCH',  path, body),
    delete: (path)              => request('DELETE', path),
    upload: (path, formData)    => request('POST',   path, formData, true),

    // ─── Auth ──────────────────────────────────
    login: (username, password) => request('POST', '/auth/login', { username, password }),
    logout: async () => {
      try { return await request('POST', '/auth/logout'); }
      finally { clearAuth(); }
    },
    getMe:  () => request('GET', '/auth/me'),

    // ─── Users ─────────────────────────────────
    getUsers:      (params = {}) => request('GET',  '/users?' + new URLSearchParams(params)),
    createUser:    (data)        => request('POST', '/users', data),
    getUser:       (id)          => request('GET',  `/users/${id}`),
    updateUser:    (id, data)    => request('PUT',  `/users/${id}`, data),
    deleteUser:    (id)          => request('DELETE', `/users/${id}`),
    updateStatus:  (id, is_active) => request('PATCH', `/users/${id}/status`, { is_active }),
    resetPassword: (id, new_password) => request('POST', `/users/${id}/reset-password`, { new_password }),

    // ─── Permissions ───────────────────────────
    getAllPermissions:     ()           => request('GET',  '/permissions'),
    getUserPermissions:   (id)          => request('GET',  `/users/${id}/permissions`),
    updateUserPermissions:(id, codes)   => request('PUT',  `/users/${id}/permissions`, { permission_codes: codes }),

    // ─── Projects ──────────────────────────────
    getProjects:   (params = {}) => request('GET',  '/projects?' + new URLSearchParams(params)),
    createProject: (data)        => request('POST', '/projects', data),
    getProject:    (id)          => request('GET',  `/projects/${id}`),
    updateProject: (id, data)    => request('PUT',  `/projects/${id}`, data),
    deleteProject: (id)          => request('DELETE', `/projects/${id}`),

    // ─── Members ───────────────────────────────
    getMembers:   (projectId)          => request('GET',  `/projects/${projectId}/members`),
    addMember:    (projectId, data)    => request('POST', `/projects/${projectId}/members`, data),
    removeMember: (projectId, userId)  => request('DELETE', `/projects/${projectId}/members/${userId}`),

    // ─── Stages ────────────────────────────────
    getStages:    (projectId)     => request('GET',  `/projects/${projectId}/stages`),
    createStage:  (projectId, d)  => request('POST', `/projects/${projectId}/stages`, d),
    updateStage:  (id, data)      => request('PUT',  `/stages/${id}`, data),
    deleteStage:  (id)            => request('DELETE', `/stages/${id}`),
    getRoadmap:   (projectId)     => request('GET',  `/projects/${projectId}/roadmap`),

    // ─── Tasks ─────────────────────────────────
    getTasks:       (params = {}) => request('GET',  '/tasks?' + new URLSearchParams(params)),
    createTask:     (data)        => request('POST', '/tasks', data),
    getTask:        (id)          => request('GET',  `/tasks/${id}`),
    updateTask:     (id, data)    => request('PUT',  `/tasks/${id}`, data),
    deleteTask:     (id)          => request('DELETE', `/tasks/${id}`),
    updateTaskStatus:   (id, status)   => request('PATCH', `/tasks/${id}/status`, { status }),
    updateTaskProgress: (id, progress) => request('PATCH', `/tasks/${id}/progress`, { progress }),
    submitTask:     (id, data)    => request('POST', `/tasks/${id}/submit`, data),

    // ─── Evaluations ───────────────────────────
    getEvaluations:    (taskId)       => request('GET',  `/tasks/${taskId}/evaluations`),
    createEvaluation:  (taskId, data) => request('POST', `/tasks/${taskId}/evaluations`, data),
    updateEvaluation:  (id, data)     => request('PUT',  `/evaluations/${id}`, data),

    // ─── Attachments ───────────────────────────
    getAttachments:   (taskId)        => request('GET',  `/tasks/${taskId}/attachments`),
    uploadAttachment: (taskId, file)  => {
      const fd = new FormData();
      fd.append('file', file);
      return request('POST', `/tasks/${taskId}/attachments`, fd, true);
    },
    deleteAttachment: (id) => request('DELETE', `/attachments/${id}`),

    // ─── Dashboard ─────────────────────────────
    getAdminDashboard: () => request('GET', '/dashboard/admin'),
    getUserDashboard:  () => request('GET', '/dashboard/user'),

    // ─── Reports ───────────────────────────────
    getUserReport:    (id) => request('GET', `/reports/users/${id}`),
    getProjectReport: (id) => request('GET', `/reports/projects/${id}`),

    // ─── Audit Logs ────────────────────────────
    getAuditLogs: (params = {}) => request('GET', '/audit-logs?' + new URLSearchParams(params)),

    // ─── Notifications ─────────────────────────
    getNotifications: () => request('GET', '/notifications'),
    getNotificationRecipients: () => request('GET', '/notifications/recipients'),
    markNotificationRead: (id) => request('PATCH', `/notifications/${id}/read`),
    markAllNotificationsRead: () => request('PATCH', '/notifications/read-all'),
    publishAnnouncement: (data) => request('POST', '/notifications/announcements', data),
  };
})();