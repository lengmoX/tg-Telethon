/**
 * TGF API Client
 * 
 * HTTP client for communicating with the FastAPI backend.
 * 
 * Features:
 * - JWT token authentication (stored in localStorage)
 * - Automatic token injection in request headers
 * - Automatic redirect to login on 401 responses
 * - Type-safe API functions for all endpoints
 * 
 * API Endpoints:
 * - /api/auth/* - Authentication (login)
 * - /api/rules/* - Rule CRUD operations
 * - /api/watcher/* - Watcher control (start/stop/status)
 * - /api/telegram/* - Telegram account connection
 * - /api/states/* - Sync state information
 * - /api/health - Health check
 */

const API_BASE = '/api';

// ============================================================
// Type Definitions
// ============================================================
export interface Rule {
  id: number;
  name: string;
  source_chat: string;
  target_chat: string;
  mode: string;
  interval_min: number;
  filter_text: string | null;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface RuleCreate {
  name: string;
  source_chat: string;
  target_chat: string;
  mode?: string;
  interval_min?: number;
  filter_text?: string;
  enabled?: boolean;
}

export interface WatcherStatus {
  running: boolean;
  pid: number | null;
  log_file: string | null;
  rules_count: number;
  enabled_rules: number;
}

export interface State {
  rule_id: number;
  rule_name: string;
  namespace: string;
  last_msg_id: number;
  total_forwarded: number;
  last_sync_at: string | null;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

// Auth state
let authToken: string | null = localStorage.getItem('tgf_token');

export function setToken(token: string) {
  authToken = token;
  localStorage.setItem('tgf_token', token);
}

export function clearToken() {
  authToken = null;
  localStorage.removeItem('tgf_token');
}

export function isAuthenticated(): boolean {
  return authToken !== null;
}

// Fetch wrapper
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearToken();
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Auth Status Type
export interface AuthStatus {
  initialized: boolean;
  need_setup: boolean;
}

// Auth API
export async function getAuthStatus(): Promise<AuthStatus> {
  return fetchApi<AuthStatus>('/auth/status');
}

export async function setupAdmin(username: string, password: string): Promise<{ access_token: string }> {
  const response = await fetchApi<{ access_token: string }>('/auth/setup', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  setToken(response.access_token);
  return response;
}

export async function login(password: string, username: string = 'admin'): Promise<{ access_token: string }> {
  const response = await fetchApi<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  setToken(response.access_token);
  return response;
}

// Rules API
export async function getRules(): Promise<Rule[]> {
  return fetchApi<Rule[]>('/rules');
}

export async function createRule(rule: RuleCreate): Promise<Rule> {
  return fetchApi<Rule>('/rules', {
    method: 'POST',
    body: JSON.stringify(rule),
  });
}

export async function updateRule(id: number, updates: Partial<RuleCreate>): Promise<Rule> {
  return fetchApi<Rule>(`/rules/${id}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

export async function deleteRule(id: number): Promise<void> {
  await fetchApi(`/rules/${id}`, { method: 'DELETE' });
}

export async function enableRule(id: number): Promise<Rule> {
  return fetchApi<Rule>(`/rules/${id}/enable`, { method: 'POST' });
}

export async function disableRule(id: number): Promise<Rule> {
  return fetchApi<Rule>(`/rules/${id}/disable`, { method: 'POST' });
}

// Telegram Auth API

export interface TelegramUser {
  id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  is_premium: boolean;
}

export interface TelegramAuthStatus {
  logged_in: boolean;
  state: 'IDLE' | 'QR_READY' | 'WAITING_PASSWORD' | 'SUCCESS' | 'FAILED';
  qr_url: string | null;
  user: TelegramUser | null;
  error: string | null;
}

export async function getTelegramStatus(): Promise<TelegramAuthStatus> {
  return fetchApi<TelegramAuthStatus>('/telegram/status');
}

export async function loginTelegram(): Promise<TelegramAuthStatus> {
  return fetchApi<TelegramAuthStatus>('/telegram/login', { method: 'POST' });
}

export async function submitTelegramPassword(password: string): Promise<TelegramAuthStatus> {
  return fetchApi<TelegramAuthStatus>('/telegram/password', {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

export async function logoutTelegram(): Promise<{ message: string }> {
  return fetchApi('/telegram/logout', { method: 'POST' });
}

// Watcher API
export async function getWatcherStatus(): Promise<WatcherStatus> {
  return fetchApi<WatcherStatus>('/watcher/status');
}

export async function startWatcher(): Promise<{ message: string }> {
  return fetchApi('/watcher/start', { method: 'POST' });
}

export async function stopWatcher(): Promise<{ message: string }> {
  return fetchApi('/watcher/stop', { method: 'POST' });
}

export async function getLogs(lines: number = 100): Promise<{ logs: LogEntry[]; total: number }> {
  return fetchApi(`/watcher/logs?lines=${lines}`);
}

// States API
export async function getStates(): Promise<State[]> {
  return fetchApi<State[]>('/states');
}

// Health API
export async function getHealth(): Promise<{ status: string; version: string }> {
  return fetchApi('/health');
}

// ============================================================
// Chat Types and API
// ============================================================

export interface ChatInfo {
  id: number;
  name: string;
  type: 'user' | 'group' | 'channel' | 'unknown';
  username: string | null;
  unread_count: number;
  last_message_date: string | null;
}

export interface ChatListResponse {
  chats: ChatInfo[];
  total: number;
}

export interface ExportRequest {
  chat: string;
  limit?: number;
  from_id?: number;
  to_id?: number;
  msg_type?: 'all' | 'media' | 'text' | 'photo' | 'video' | 'document';
  with_content?: boolean;
}

export interface ExportResponse {
  success: boolean;
  message_count: number;
  chat_name: string;
  chat_username: string | null;
  chat_id: number;
  links: string[];
}

// Chats API
export async function getChats(
  limit: number = 100,
  chatType: string = 'all'
): Promise<ChatListResponse> {
  return fetchApi<ChatListResponse>(`/chats?limit=${limit}&chat_type=${chatType}`);
}

export async function exportChat(request: ExportRequest): Promise<ExportResponse> {
  return fetchApi<ExportResponse>('/chats/export', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// Forward API
export interface ForwardRequest {
  links: string[];
  dest?: string;
  mode?: 'clone' | 'direct';
  detect_album?: boolean;
}

export interface ForwardResultItem {
  link: string;
  success: boolean;
  error?: string;
  target_msg_id?: number;
}

export interface ForwardResponse {
  success: boolean;
  total: number;
  succeeded: number;
  failed: number;
  results: ForwardResultItem[];
}

export async function forwardMessages(request: ForwardRequest): Promise<ForwardResponse> {
  return fetchApi<ForwardResponse>('/forward', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// Backup API
export interface BackupImportResponse {
  success: boolean;
  message: string;
  details: string[];
}

export const exportBackup = async (): Promise<void> => {
  const token = localStorage.getItem('tgf_token');
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}/backup/export`, {
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Export failed' }));
    throw new Error(errorData.detail || 'Failed to export backup');
  }

  // Trigger download
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;

  // Try to get filename from headers
  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = 'tgf_backup.zip';
  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?(.+?)"?$/);
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1];
    }
  }

  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

export const importBackup = async (file: File): Promise<BackupImportResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  return fetchApi<BackupImportResponse>('/backup/import', {
    method: 'POST',
    body: formData,
  });
};
