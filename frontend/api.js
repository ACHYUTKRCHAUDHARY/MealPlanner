/* Tokens intentionally live in memory: reload requires login, never localStorage. */
const API = (() => {
  let token = null;
  const base = window.PLATEFUL_CONFIG?.apiUrl?.replace(/\/$/, '');
  async function request(path, {method = 'GET', body} = {}) {
    if (!base) throw new Error('API address is missing. Set PUBLIC_API_URL and rebuild.');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 90000);
    try {
      const response = await fetch(base + '/api/v1' + path, {
        method, signal: controller.signal,
        headers: {...(body !== undefined ? {'Content-Type': 'application/json'} : {}),
          ...(token ? {Authorization: `Bearer ${token}`} : {})},
        ...(body !== undefined ? {body: JSON.stringify(body)} : {})
      });
      const data = response.status === 204 ? null : await response.json();
      if (!response.ok) {
        const error = new Error(data?.error?.message || 'Request failed. Please retry.');
        error.status = response.status;
        if (response.status === 401) token = null;
        throw error;
      }
      return data;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('The request took too long. Please retry.');
      if (error instanceof TypeError) throw new Error('Cannot reach the backend. Check your connection and try again.');
      throw error;
    } finally { clearTimeout(timeout); }
  }
  return {request, signedIn: () => !!token, setToken: value => {token = value;}};
})();
