// Tiny fetch wrapper. Token lives in sessionStorage (cleared when the tab closes).
const KEY = "sb_session";

export const session = {
  get: () => { try { return JSON.parse(sessionStorage.getItem(KEY)); } catch { return null; } },
  set: (v) => sessionStorage.setItem(KEY, JSON.stringify(v)),
  clear: () => sessionStorage.removeItem(KEY),
};

async function request(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const s = session.get();
  if (s?.token) headers.Authorization = `Bearer ${s.token}`;
  let payload;
  if (form) payload = new URLSearchParams(form);
  else if (body) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }

  const res = await fetch(`/api${path}`, { method, headers, body: payload });
  if (res.status === 401 && s) { session.clear(); window.location.reload(); }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(Array.isArray(d) ? d.map((e) => `${e.loc.slice(-1)[0]}: ${e.msg}`).join(", ") : d || "Request failed");
  }
  return data;
}

export const api = {
  register: (b) => request("/auth/register", { method: "POST", body: b }),
  login: (email, password) => request("/auth/login", { method: "POST", form: { username: email, password } }),
  users: () => request("/users"),
  projects: () => request("/projects"),
  project: (id) => request(`/projects/${id}`),
  createProject: (b) => request("/projects", { method: "POST", body: b }),
  deleteProject: (id) => request(`/projects/${id}`, { method: "DELETE" }),
  stories: (pid) => request(`/projects/${pid}/stories`),
  createStory: (pid, b) => request(`/projects/${pid}/stories`, { method: "POST", body: b }),
  updateStory: (id, b) => request(`/stories/${id}`, { method: "PATCH", body: b }),
  deleteStory: (id) => request(`/stories/${id}`, { method: "DELETE" }),
  tasks: (sid) => request(`/stories/${sid}/tasks`),
  createTask: (sid, b) => request(`/stories/${sid}/tasks`, { method: "POST", body: b }),
  updateTask: (id, b) => request(`/tasks/${id}`, { method: "PATCH", body: b }),
  deleteTask: (id) => request(`/tasks/${id}`, { method: "DELETE" }),
  notifications: () => request("/notifications"),
  markRead: (id) => request(`/notifications/${id}/read`, { method: "POST" }),
  runOverdueCheck: () => request("/jobs/overdue-check", { method: "POST" }),
  jobLogs: () => request("/jobs/logs"),
};
