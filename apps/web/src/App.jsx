import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import SymbolBoard from "./components/SymbolBoard";
import ParentView from "./components/ParentView";
import SessionLog from "./components/SessionLog";
import ResearchPortal from "./components/ResearchPortal";
import { api } from "./api";
import "./App.css";

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [child, setChild] = useState(null);
  const [children, setChildren] = useState([]);
  const [sessionContext, setSessionContext] = useState({ name: "mealtime", label: "Mealtime" });

  useEffect(() => {
    api.listChildren().then(list => {
      setChildren(list);
      if (list.length > 0 && !child) setChild(list[0]);
    }).catch(() => {});
  }, []);

  async function handleAddChild(name, age) {
    const newChild = await api.createChild({ name, age: parseFloat(age) });
    setChildren(prev => [...prev, newChild]);
    setChild(newChild);
  }

  return (
    <div className="app-layout">
      <Sidebar
        child={child}
        children={children}
        onSelectChild={setChild}
        onAddChild={handleAddChild}
        activePage={page}
        onNavigate={setPage}
      />
      <main className="main-content">
        {!child ? (
          <div className="welcome-state">
            <div className="welcome-card">
              <div className="welcome-icon">🧩</div>
              <h1>Welcome to Bridge</h1>
              <p>Add a child profile using the sidebar to get started.</p>
            </div>
          </div>
        ) : (
          <>
            {page === "dashboard" && <Dashboard child={child} onNavigate={setPage} />}
            {page === "symbols"   && <SymbolBoard child={child} sessionContext={sessionContext} />}
            {page === "parent"    && <ParentView child={child} sessionContext={sessionContext} onContextChange={setSessionContext} />}
            {page === "sessions"  && <SessionLog child={child} />}
            {page === "research"  && <ResearchPortal child={child} />}
          </>
        )}
      </main>
    </div>
  );
}
