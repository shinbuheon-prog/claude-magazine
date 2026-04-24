const API_BASE = import.meta.env.VITE_EDITOR_API || 'http://127.0.0.1:8080';
const API_TOKEN = import.meta.env.VITE_EDITOR_API_TOKEN || '';

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set('Accept', 'application/json');
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }
  if (API_TOKEN) {
    headers.set('Authorization', `Bearer ${API_TOKEN}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = data?.detail || data || { message: response.statusText };
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data;
}

export function listDrafts() {
  return request('/api/drafts');
}

export function getDraft(articleId) {
  return request(`/api/drafts/${articleId}`);
}

export function getLint(articleId) {
  return request(`/api/drafts/${articleId}/lint`);
}

export function getDiff(articleId) {
  return request(`/api/drafts/${articleId}/diff`);
}

export function approveDraft(articleId, options = {}) {
  return request(`/api/drafts/${articleId}/approve`, {
    method: 'POST',
    body: JSON.stringify(options),
  });
}

export function rejectDraft(articleId, options = {}) {
  return request(`/api/drafts/${articleId}/reject`, {
    method: 'POST',
    body: JSON.stringify(options),
  });
}

export function listPublished() {
  return request('/api/published');
}

export function unpublish(postId) {
  return request(`/api/published/${postId}/unpublish`, {
    method: 'POST',
  });
}

export function getMetrics() {
  return request('/api/metrics');
}
