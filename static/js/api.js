/**
 * Module Client API REST.
 * Fournit une interface unifiée pour communiquer avec le backend local ou un serveur distant.
 */

let customApiBase = localStorage.getItem('todolist_remote_server') || '';
let customApiToken = localStorage.getItem('todolist_remote_token') || '';

export function getApiBase() {
  return customApiBase;
}

export function setApiBase(url) {
  customApiBase = (url || '').trim().replace(/\/+$/, '');
  if (customApiBase) {
    localStorage.setItem('todolist_remote_server', customApiBase);
  } else {
    localStorage.removeItem('todolist_remote_server');
  }
}

export function getApiToken() {
  return customApiToken;
}

export function setApiToken(token) {
  customApiToken = (token || '').trim();
  if (customApiToken) {
    localStorage.setItem('todolist_remote_token', customApiToken);
  } else {
    localStorage.removeItem('todolist_remote_token');
  }
}

export async function testServerConnection(url, token = null) {
  const cleanUrl = (url || '').trim().replace(/\/+$/, '');
  if (!cleanUrl) return { success: false, message: 'URL manquante' };
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);
    const headers = { 'Content-Type': 'application/json' };
    const effectiveToken = (token !== null ? token : getApiToken()).trim();
    if (effectiveToken) {
      headers['Authorization'] = `Bearer ${effectiveToken}`;
    }

    const res = await fetch(`${cleanUrl}/api/data`, {
      method: 'GET',
      headers,
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.status === 401) {
      return { success: false, message: 'Non autorisé : jeton d\'accès requis ou invalide.' };
    }
    if (!res.ok) throw new Error(`Code HTTP ${res.status}`);
    const data = await res.json();
    return {
      success: true,
      foldersCount: data.folders?.length || 0,
      tasksCount: data.tasks?.length || 0
    };
  } catch (err) {
    return { success: false, message: err.name === 'AbortError' ? 'Délai d\'attente dépassé (timeout 6s)' : err.message };
  }
}

export async function fetchNetworkInfo() {
  return await api('/api/network/info');
}

export async function api(endpoint, method = 'GET', data = null) {
  try {
    const base = getApiBase();
    let targetUrl = endpoint;
    if (base && endpoint.startsWith('/api')) {
      targetUrl = `${base}${endpoint}`;
    }

    const headers = { 'Content-Type': 'application/json' };
    const token = getApiToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const options = {
      method,
      headers
    };
    if (data) options.body = JSON.stringify(data);
    const res = await fetch(targetUrl, options);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`[API Error] ${method} ${endpoint}:`, err);
    return null;
  }
}

export async function fetchInitialData() {
  return await api('/api/data');
}
