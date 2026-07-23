const AUTH_TOKEN_KEY = "minerai_token";
const AUTH_USER_KEY = "minerai_user";
const LOGIN_EVENTS_PREFIX = "minerai_login_events_";
const RECENT_LESSONS_PREFIX = "minerai_recent_lessons_";

type AuthStorageKey = typeof AUTH_TOKEN_KEY | typeof AUTH_USER_KEY;

export interface StoredRecentLesson {
  id: string;
  title: string;
  subtitle: string;
  topic: string;
  score: number;
  max_score: number;
  percentage: number;
  grade?: string;
  answered_questions: number;
  total_questions: number;
  created_at: string;
}

export function getAuthItem(key: AuthStorageKey): string | null {
  return localStorage.getItem(key) || sessionStorage.getItem(key);
}

export function hasAuthSession(): boolean {
  return !!getAuthItem(AUTH_TOKEN_KEY);
}

export function saveAuthSession(token: string, user: unknown, rememberLogin: boolean) {
  clearAuthSession();

  const storage = rememberLogin ? localStorage : sessionStorage;
  storage.setItem(AUTH_TOKEN_KEY, token);
  storage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

function getUserStorageId(user: any): string {
  return String(user?.user_id || user?.email || "guest").replace(/[^a-zA-Z0-9@._-]/g, "_");
}

export function recordLoginEvent(user: unknown) {
  try {
    const userId = getUserStorageId(user);
    const key = `${LOGIN_EVENTS_PREFIX}${userId}`;
    const current = JSON.parse(localStorage.getItem(key) || "[]");
    const events = Array.isArray(current) ? current : [];
    events.push(new Date().toISOString());
    localStorage.setItem(key, JSON.stringify(events.slice(-1000)));
  } catch {
    // Best-effort fallback for local activity charts.
  }
}

export function getLocalLoginEvents(): string[] {
  try {
    const rawUser = getAuthItem(AUTH_USER_KEY);
    if (!rawUser) return [];
    const user = JSON.parse(rawUser);
    const key = `${LOGIN_EVENTS_PREFIX}${getUserStorageId(user)}`;
    const events = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(events) ? events.filter((item) => typeof item === "string") : [];
  } catch {
    return [];
  }
}

function getCurrentUserStorageId(): string | null {
  try {
    const rawUser = getAuthItem(AUTH_USER_KEY);
    if (!rawUser) return null;
    return getUserStorageId(JSON.parse(rawUser));
  } catch {
    return null;
  }
}

export function getLocalRecentLessons(): StoredRecentLesson[] {
  try {
    const userId = getCurrentUserStorageId();
    if (!userId) return [];
    const key = `${RECENT_LESSONS_PREFIX}${userId}`;
    const rows = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(rows) ? rows : [];
  } catch {
    return [];
  }
}

export function saveLocalRecentLesson(lesson: StoredRecentLesson) {
  try {
    const userId = getCurrentUserStorageId();
    if (!userId) return;
    const key = `${RECENT_LESSONS_PREFIX}${userId}`;
    const rows = getLocalRecentLessons();
    const deduped = rows.filter((item) => item.id !== lesson.id);
    const nextRows = [lesson, ...deduped]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 12);
    localStorage.setItem(key, JSON.stringify(nextRows));
  } catch {
    // Best-effort fallback for the overview recent lessons panel.
  }
}

export function clearAuthSession() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
  sessionStorage.removeItem(AUTH_TOKEN_KEY);
  sessionStorage.removeItem(AUTH_USER_KEY);
}
