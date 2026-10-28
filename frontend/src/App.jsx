import { useEffect, useState } from "react";
import { api, session } from "./api.js";
import { AuthPage, ProjectsPage, BoardPage, NotificationsPage } from "./pages.jsx";

// Minimal hash router: #/projects, #/projects/3, #/notifications
function useRoute() {
  const [hash, setHash] = useState(window.location.hash || "#/projects");
  useEffect(() => {
    const on = () => setHash(window.location.hash || "#/projects");
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return hash.replace(/^#\/?/, "").split("/");
}

export default function App() {
  const [user, setUser] = useState(session.get()?.user || null);
  const [unread, setUnread] = useState(0);
  const route = useRoute();

  useEffect(() => {
    if (!user) return;
    const load = () => api.notifications().then((n) => setUnread(n.filter((x) => !x.is_read).length)).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [user, route.join("/")]);

  if (!user) return <AuthPage onAuth={(s) => { session.set(s); setUser(s.user); }} />;

  const logout = () => { session.clear(); setUser(null); window.location.hash = "#/projects"; };

  return (
    <>
      <header className="topbar">
        <a className="brand" href="#/projects">SprintBoard</a>
        <nav>
          <a href="#/projects" aria-current={route[0] === "projects" ? "page" : undefined}>Projects</a>
          <a href="#/notifications" aria-current={route[0] === "notifications" ? "page" : undefined}>
            Reminders{unread > 0 && <span className="badge">{unread}</span>}
          </a>
        </nav>
        <span className="who">{user.name}</span>
        <button className="ghost" onClick={logout}>Log out</button>
      </header>
      <main>
        {route[0] === "notifications" ? <NotificationsPage />
          : route[0] === "projects" && route[1] ? <BoardPage key={route[1]} projectId={Number(route[1])} me={user} />
          : <ProjectsPage />}
      </main>
    </>
  );
}
