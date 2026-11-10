/**
 * Module Client API REST.
 * Fournit une interface unifiée pour communiquer avec le backend Python.
 */

export async function api(endpoint, method = 'GET', data = null) {
  try {
    const options = {
      method,
      headers: { 'Content-Type': 'application/json' }
    };
    if (data) options.body = JSON.stringify(data);
    const res = await fetch(endpoint, options);
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
