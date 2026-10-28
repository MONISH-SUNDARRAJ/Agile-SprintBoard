import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

const STATUS = [["todo", "To do"], ["in_progress", "In progress"], ["done", "Done"]];
const label = (s) => STATUS.find(([k]) => k === s)?.[1] ?? s;
const pct = (x) => `${Math.round((x ?? 0) * 100)}%`;
const today = () => new Date().toISOString().slice(0, 10);

function useAsync(fn, deps) {
  const [state, setState] = useState({ data: null, error: "", loading: true });
  const reload = useCallback(() =>
    fn().then((data) => {
      setState({ data, error: "", loading: false });
      return data;
    }).catch((e) => {
      setState((s) => ({ ...s, error: e.message, loading: false }));
      return null;
    }), deps); // eslint-disable-line
  useEffect(() => { reload(); }, [reload]);
  return { ...state, reload };
}

const Progress = ({ value, text }) => (
  <div className="progress" role="progressbar" aria-valuenow={Math.round(value * 100)} aria-valuemin="0" aria-valuemax="100">
    <div style={{ width: pct(value) }} />
    {text && <span>{text}</span>}
  </div>
);
const Err = ({ msg }) => (msg ? <p className="error" role="alert">{msg}</p> : null);

/* ---------------- Auth ---------------- */
export function AuthPage({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const r = mode === "login" ? await api.login(f.email, f.password) : await api.register(f);
      onAuth({ token: r.access_token, user: r.user });
    } catch (err) { setError(err.message); }
  };

  return (
    <div className="auth">
      <h1>SprintBoard</h1>
      <p className="muted">Plan projects, stories and tasks with your team.</p>
      <form onSubmit={submit}>
        {mode === "register" && <label>Name<input required value={f.name} onChange={set("name")} /></label>}
        <label>Email<input required type="email" value={f.email} onChange={set("email")} /></label>
        <label>Password<input required type="password" minLength={8} maxLength={72} value={f.password} onChange={set("password")} /></label>
        <Err msg={error} />
        <button type="submit">{mode === "login" ? "Log in" : "Create account"}</button>
      </form>
      <button className="link" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
        {mode === "login" ? "New here? Create an account" : "Have an account? Log in"}
      </button>
    </div>
  );
}

/* ---------------- Projects ---------------- */
export function ProjectsPage() {
  const { data, error, reload } = useAsync(api.projects, []);
  const [form, setForm] = useState({ name: "", description: "" });
  const [err, setErr] = useState("");

  const add = async (e) => {
    e.preventDefault();
    setErr("");
    try { await api.createProject(form); setForm({ name: "", description: "" }); reload(); }
    catch (x) { setErr(x.message); }
  };
  const remove = async (p) => {
    if (!window.confirm(`Delete "${p.name}" and all its stories and tasks?`)) return;
    try { await api.deleteProject(p.id); reload(); } catch (x) { setErr(x.message); }
  };

  return (
    <>
      <h2>Projects</h2>
      <form className="inline" onSubmit={add}>
        <input required maxLength={120} placeholder="Project name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input placeholder="Short description (optional)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <button type="submit">Create project</button>
      </form>
      <Err msg={err || error} />
      {data?.length === 0 && <p className="muted">No projects yet. Create your first one above.</p>}
      <div className="grid">
        {data?.map((p) => (
          <article className="card" key={p.id}>
            <h3><a href={`#/projects/${p.id}`}>{p.name}</a></h3>
            <p className="muted">{p.description || "No description"}</p>
            <Progress value={p.progress} text={`${p.done_tasks}/${p.total_tasks} tasks done`} />
            <div className="row">
              <span className="muted">{p.story_count} {p.story_count === 1 ? "story" : "stories"}</span>
              <button className="ghost danger" onClick={() => remove(p)}>Delete</button>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

/* ---------------- Board ---------------- */
export function BoardPage({ projectId, me }) {
  const project = useAsync(() => api.project(projectId), [projectId]);
  const stories = useAsync(() => api.stories(projectId), [projectId]);
  const users = useAsync(api.users, []);
  const [open, setOpen] = useState(null);
  const [form, setForm] = useState({ title: "", priority: "medium", story_points: "" });
  const [err, setErr] = useState("");
  const [boardTasks, setBoardTasks] = useState([]);
  const [taskBoardError, setTaskBoardError] = useState("");

  const refresh = async () => {
    const results = await Promise.allSettled([
      stories.reload(),
      project.reload(),
    ]);
    const refreshedStories = results[0].status === "fulfilled"
      ? results[0].value
      : stories.data;

    if (refreshedStories) {
      try {
        const groups = await Promise.all(
          refreshedStories.map(async (story) => {
            const tasks = await api.tasks(story.id);
            return tasks.map((task) => ({
              ...task,
              storyTitle: story.title,
              storyId: story.id,
            }));
          })
        );
        setBoardTasks(groups.flat());
        setTaskBoardError("");
      } catch (error) {
        setTaskBoardError(error.message || "Unable to load tasks.");
      }
    }
  };

  useEffect(() => {
    let cancelled = false;

    const loadTasks = async () => {
      if (!stories.data) {
        setBoardTasks([]);
        return;
      }
      try {
        const groups = await Promise.all(
          stories.data.map(async (story) => {
            const tasks = await api.tasks(story.id);
            return tasks.map((task) => ({
              ...task,
              storyTitle: story.title,
              storyId: story.id,
            }));
          })
        );
        if (!cancelled) {
          setBoardTasks(groups.flat());
          setTaskBoardError("");
        }
      } catch (error) {
        if (!cancelled) setTaskBoardError(error.message || "Unable to load tasks.");
      }
    };

    loadTasks();
    return () => { cancelled = true; };
  }, [stories.data]);

  const nameOf = (id) => users.data?.find((u) => u.id === id)?.name ?? "";

  const add = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await api.createStory(projectId, {
        title: form.title, priority: form.priority,
        story_points: form.story_points === "" ? null : Number(form.story_points),
      });
      setForm({ title: "", priority: "medium", story_points: "" });
      refresh();
    } catch (x) { setErr(x.message); }
  };

  const p = project.data;
  return (
    <>
      <p><a href="#/projects">← All projects</a></p>
      <h2>{p?.name}</h2>
      {p && <Progress value={p.progress} text={`${pct(p.progress)} complete · ${p.done_tasks}/${p.total_tasks} tasks`} />}
      <form className="inline" onSubmit={add}>
        <input required maxLength={200} placeholder="As a user, I can…" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <select aria-label="Priority" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
          <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
        </select>
        <input aria-label="Story points" type="number" min="0" max="100" placeholder="Points" value={form.story_points} onChange={(e) => setForm({ ...form, story_points: e.target.value })} />
        <button type="submit">Add story</button>
      </form>
      <Err msg={err || stories.error || project.error} />
      <h3>Stories</h3>
      <div className="columns">
        {STATUS.map(([key, name]) => {
          const items = stories.data?.filter((s) => s.status === key) ?? [];
          return (
            <section className={`column ${key}`} key={key} aria-label={`${name} stories`}>
              <h3>{name} <span className="count">{items.length}</span></h3>
              {items.length === 0 && <p className="muted small">Nothing here</p>}
              {items.map((s) => (
                <button className="story" key={s.id} onClick={() => setOpen(s.id)}>
                  <strong>{s.title}</strong>
                  <span className="meta">
                    <span className={`pill ${s.priority}`}>{s.priority}</span>
                    {s.story_points != null && <span>{s.story_points} pts</span>}
                    {s.assignee_id && <span>{nameOf(s.assignee_id)}</span>}
                  </span>
                  <Progress value={s.progress} text={`${s.done_tasks}/${s.total_tasks}`} />
                </button>
              ))}
            </section>
          );
        })}
      </div>

      <h3>Task board</h3>
      <Err msg={taskBoardError} />
      <div className="columns">
        {STATUS.map(([key, name]) => {
          const items = boardTasks.filter((task) => task.status === key);
          return (
            <section className={`column ${key}`} key={`tasks-${key}`} aria-label={`${name} tasks`}>
              <h3>{name} <span className="count">{items.length}</span></h3>
              {items.length === 0 && <p className="muted small">No tasks here</p>}
              {items.map((task) => (
                <article className="card" key={task.id}>
                  <strong>{task.title}</strong>
                  <p className="muted small">Story: {task.storyTitle}</p>
                  <label className="small">Status
                    <select
                      aria-label={`Status of ${task.title}`}
                      value={task.status}
                      onChange={async (event) => {
                        const status = event.target.value;
                        setTaskBoardError("");
                        try {
                          await api.updateTask(task.id, { status });
                          setBoardTasks((current) => current.map((item) =>
                            item.id === task.id ? { ...item, status } : item
                          ));
                          await refresh();
                        } catch (error) {
                          setTaskBoardError(error.message || "Unable to update task status.");
                        }
                      }}
                    >
                      {STATUS.map(([value, labelText]) => (
                        <option key={value} value={value}>{labelText}</option>
                      ))}
                    </select>
                  </label>
                </article>
              ))}
            </section>
          );
        })}
      </div>
      {open && stories.data?.some((s) => s.id === open) && (
        <StoryPanel story={stories.data.find((s) => s.id === open)} users={users.data || []}
                    onClose={() => setOpen(null)} onChange={refresh} />
      )}
    </>
  );
}

function StoryPanel({ story, users, onClose, onChange }) {
  const tasks = useAsync(() => api.tasks(story.id), [story.id]);
  const [t, setT] = useState({ title: "", assignee_id: "", due_date: "" });
  const [err, setErr] = useState("");

  const run = async (fn) => {
    setErr("");
    try {
      await fn();
      await tasks.reload();
      await onChange();
    } catch (x) {
      setErr(x.message);
    }
  };
  const patchStory = (b) => run(() => api.updateStory(story.id, b));
  const assignee = (v) => (v === "" ? null : Number(v));
  const userSelect = (value, onSel, lbl) => (
    <select aria-label={lbl} value={value ?? ""} onChange={(e) => onSel(e.target.value)}>
      <option value="">Unassigned</option>
      {users.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
    </select>
  );

  return (
    <aside className="panel" aria-label="Story details">
      <div className="row">
        <h3>{story.title}</h3>
        <button className="ghost" onClick={onClose} aria-label="Close panel">Close</button>
      </div>
      <div className="fields">
        <label>Status
          <select value={story.status} onChange={(e) => patchStory({ status: e.target.value })}>
            {STATUS.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label>Priority
          <select value={story.priority} onChange={(e) => patchStory({ priority: e.target.value })}>
            <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
          </select>
        </label>
        <label>Assignee {userSelect(story.assignee_id, (v) => patchStory({ assignee_id: assignee(v) }), "Story assignee")}</label>
      </div>
      <Progress value={story.progress} text={`${story.done_tasks}/${story.total_tasks} tasks done`} />
      <Err msg={err || tasks.error} />

      <h4>Tasks</h4>
      {tasks.data?.length === 0 && <p className="muted small">No tasks yet. Add the first step below.</p>}
      <ul className="tasks">
        {tasks.data?.map((k) => {
          const overdue = k.due_date && k.status !== "done" && k.due_date < today();
          return (
            <li key={k.id} className={k.status}>
              <span className="ttitle">{k.title}</span>
              <select aria-label={`Status of ${k.title}`} value={k.status} onChange={(e) => run(() => api.updateTask(k.id, { status: e.target.value }))}>
                {STATUS.map(([a, b]) => <option key={a} value={a}>{b}</option>)}
              </select>
              {userSelect(k.assignee_id, (v) => run(() => api.updateTask(k.id, { assignee_id: assignee(v) })), `Assignee of ${k.title}`)}
              <input type="date" aria-label={`Due date of ${k.title}`} value={k.due_date || ""}
                     onChange={(e) => run(() => api.updateTask(k.id, { due_date: e.target.value || null }))} />
              {overdue && <span className="pill overdue">Overdue</span>}
              <button className="ghost danger" onClick={() => run(() => api.deleteTask(k.id))} aria-label={`Delete ${k.title}`}>Delete</button>
            </li>
          );
        })}
      </ul>
      <form className="inline" onSubmit={(e) => {
        e.preventDefault();
        run(async () => {
          await api.createTask(story.id, { title: t.title, assignee_id: assignee(t.assignee_id), due_date: t.due_date || null });
          setT({ title: "", assignee_id: "", due_date: "" });
        });
      }}>
        <input required maxLength={200} placeholder="New task" value={t.title} onChange={(e) => setT({ ...t, title: e.target.value })} />
        {userSelect(t.assignee_id, (v) => setT({ ...t, assignee_id: v }), "New task assignee")}
        <input type="date" aria-label="New task due date" value={t.due_date} onChange={(e) => setT({ ...t, due_date: e.target.value })} />
        <button type="submit">Add task</button>
      </form>
      <button className="ghost danger" onClick={() => {
        if (window.confirm("Delete this story and its tasks?")) run(async () => { await api.deleteStory(story.id); onClose(); });
      }}>Delete story</button>
    </aside>
  );
}

/* ---------------- Reminders & background jobs ---------------- */
export function NotificationsPage() {
  const notes = useAsync(api.notifications, []);
  const logs = useAsync(api.jobLogs, []);
  const [msg, setMsg] = useState("");

  const runNow = async () => {
    setMsg("");
    try {
      await api.runOverdueCheck();
      setMsg("Overdue check started in the background. Refreshing in a few seconds…");
      setTimeout(() => { notes.reload(); logs.reload(); setMsg(""); }, 4000);
    } catch (x) { setMsg(x.message); }
  };

  return (
    <>
      <div className="row">
        <h2>Reminders</h2>
        <button onClick={runNow}>Check overdue tasks now</button>
      </div>
      <p className="muted">The server also runs this check automatically on a schedule.</p>
      {msg && <p role="status">{msg}</p>}
      <Err msg={notes.error} />
      {notes.data?.length === 0 && <p className="muted">No reminders. Tasks assigned to you that pass their due date will show up here.</p>}
      <ul className="notes">
        {notes.data?.map((n) => (
          <li key={n.id} className={n.is_read ? "read" : ""}>
            <span>{n.message}</span>
            <time>{new Date(n.created_at + "Z").toLocaleString()}</time>
            {!n.is_read && <button className="ghost" onClick={() => api.markRead(n.id).then(notes.reload)}>Mark read</button>}
          </li>
        ))}
      </ul>

      <h3>Background job log</h3>
      <p className="muted small">Each reminder is tried up to 3 times. Failed jobs are retried on the next scheduled run.</p>
      <div className="scroll">
        <table>
          <thead><tr><th>Job</th><th>Task</th><th>Status</th><th>Attempts</th><th>Error</th><th>Started</th></tr></thead>
          <tbody>
            {logs.data?.map((j) => (
              <tr key={j.id}>
                <td>{j.job_type}</td><td>#{j.task_id ?? "–"}</td>
                <td><span className={`pill ${j.status}`}>{j.status}</span></td>
                <td>{j.attempts}</td><td>{j.error_message || "–"}</td>
                <td>{new Date(j.created_at + "Z").toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
