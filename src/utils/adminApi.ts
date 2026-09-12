/**
 * DrishtiAI — Intelligence Control Plane Admin API Client
 * Centralized authenticated fetch client with token management and resilient error handling.
 */

let cachedAdminToken: string | null = null;

export function getStoredAdminToken(): string | null {
  if (cachedAdminToken) return cachedAdminToken;
  try {
    if (typeof window !== 'undefined') {
      cachedAdminToken = localStorage.getItem('drishti_admin_token');
    }
  } catch {
    // Ignore localStorage errors
  }
  return cachedAdminToken;
}

export function setStoredAdminToken(token: string): void {
  cachedAdminToken = token;
  try {
    if (typeof window !== 'undefined') {
      localStorage.setItem('drishti_admin_token', token);
    }
  } catch {
    // Ignore localStorage errors
  }
}

export async function loginAdmin(role: string = 'SUPER_ADMIN', secret: string = 'drishti-admin-secret-2026'): Promise<string | null> {
  try {
    const res = await fetch('/api/admin/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, secret, user_id: 'admin_user' }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.token) {
        setStoredAdminToken(data.token);
        return data.token;
      }
    }
  } catch (err) {
    console.warn('[AdminAPI] Auto-login attempt failed:', err);
  }
  return null;
}

export async function adminFetch<T = any>(
  url: string,
  options: RequestInit = {}
): Promise<{ ok: boolean; status: number; data: T | null; error?: string }> {
  let token = getStoredAdminToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    let res = await fetch(url, { ...options, headers });

    // If 401 Unauthorized, attempt auto-login once and retry
    if (res.status === 401) {
      const newToken = await loginAdmin();
      if (newToken) {
        headers['Authorization'] = `Bearer ${newToken}`;
        res = await fetch(url, { ...options, headers });
      }
    }

    if (!res.ok) {
      let errorMsg = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        errorMsg = errJson.error || errorMsg;
      } catch {
        // Fallback to status text
      }
      return { ok: false, status: res.status, data: null, error: errorMsg };
    }

    const data = await res.json();
    return { ok: true, status: res.status, data };
  } catch (err: any) {
    console.error(`[AdminAPI] Request to ${url} failed:`, err);
    return {
      ok: false,
      status: 0,
      data: null,
      error: err.message || 'Network request failed',
    };
  }
}
