import { useState, useEffect, useRef } from "react";
import Sidebar from "./components/Sidebar";
import SymbolBoard from "./components/SymbolBoard";
import ParentView from "./components/ParentView";
import SessionLog from "./components/SessionLog";
import ResearchPortal from "./components/ResearchPortal";
import { api } from "./api";
import "./App.css";

const DEMO_DURATION_MS = 90000;

const DEMO_STEPS = [
  { id: "seed", at: 0, label: "Resetting Maya demo", action: "seed" },
  { id: "profile", at: 3000, label: "Live Session: Maya profile", action: "highlight", page: "parent", highlight: "profile" },
  { id: "intent", at: 8000, label: "Suggested intent: I want water", action: "highlight", page: "parent", highlight: "top_intent" },
  { id: "speak", at: 13000, label: "Speaking AAC phrase", action: "parent_command", command: "speak_top_intent", page: "parent", highlight: "top_intent" },
  { id: "confirm", at: 18000, label: "Saving parent-confirmed moment", action: "parent_command", command: "confirm_top_intent", page: "parent", highlight: "top_intent" },
  { id: "memory", at: 24000, label: "Redis event published", action: "highlight", page: "parent", highlight: "memory" },
  { id: "timeline", at: 30000, label: "Evidence Timeline", action: "highlight", page: "sessions", highlight: "timeline_summary" },
  { id: "pattern", at: 36000, label: "Pattern detected", action: "highlight", page: "sessions", highlight: "timeline_pattern" },
  { id: "care", at: 42000, label: "Care Agent sponsor pipeline", action: "highlight", page: "research", highlight: "pipeline_redis" },
  { id: "run-agent", at: 46000, label: "TinyFish source extraction", action: "research_command", command: "run_agent", page: "research", highlight: "pipeline_tinyfish" },
  { id: "ghost", at: 58000, label: "Ghost/Postgres audit saved", action: "highlight", page: "research", highlight: "pipeline_ghost" },
  { id: "trace", at: 63000, label: "Technical trace", action: "highlight", page: "research", highlight: "technical_trace" },
  { id: "packet", at: 69000, label: "Parent-review packet ready", action: "highlight", page: "research", highlight: "packet_full" },
  { id: "nexla", at: 78000, label: "Approving Nexla Express delivery", action: "research_command", command: "approve_nexla", page: "research", highlight: "pipeline_nexla" },
  { id: "vapi", at: 84000, label: "Approving Vapi update", action: "research_command", command: "approve_vapi", page: "research", highlight: "pipeline_vapi" },
  { id: "complete", at: 90000, label: "Sponsor pipeline complete", action: "complete", page: "research", highlight: "sponsors" },
];

function formatDemoTime(ms) {
  const remaining = Math.max(0, Math.ceil((DEMO_DURATION_MS - ms) / 1000));
  const minutes = Math.floor(remaining / 60);
  const seconds = String(remaining % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function DemoController({ demo, onStart, onPause, onResume, onReset }) {
  const pct = Math.min(100, Math.round((demo.elapsedMs / DEMO_DURATION_MS) * 100));
  const running = demo.status === "running";
  const paused = demo.status === "paused";
  const complete = demo.status === "complete";
  return (
    <div className={`demo-controller demo-${demo.status}`}>
      <div className="demo-controller-top">
        <div>
          <span className="demo-kicker">Presentation autopilot</span>
          <strong>{demo.stage || "Ready for demo"}</strong>
        </div>
        <span className="demo-time">{complete ? "Done" : formatDemoTime(demo.elapsedMs)}</span>
      </div>
      <div className="demo-progress-track">
        <div className="demo-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      {demo.error && <div className="demo-error">{demo.error}</div>}
      <div className="demo-actions">
        {demo.status === "idle" || complete || demo.status === "error" ? (
          <button className="btn-primary" onClick={onStart}>Start Demo</button>
        ) : null}
        {running && <button className="btn-outline-sm" onClick={onPause}>Pause</button>}
        {paused && <button className="btn-primary" onClick={onResume}>Resume</button>}
        {demo.status !== "idle" && <button className="btn-ghost demo-reset-btn" onClick={onReset}>Reset</button>}
      </div>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState("parent");
  const [child, setChild] = useState(null);
  const [children, setChildren] = useState([]);
  const [sessionContext, setSessionContext] = useState({ name: "mealtime", label: "Mealtime" });
  const [demo, setDemo] = useState({
    status: "idle",
    elapsedMs: 0,
    stage: "",
    highlight: "",
    error: "",
  });
  const [parentCommand, setParentCommand] = useState(null);
  const [researchCommand, setResearchCommand] = useState(null);
  const firedStepsRef = useRef(new Set());
  const demoBaseRef = useRef(0);
  const demoPausedAtRef = useRef(0);

  useEffect(() => {
    api.listChildren().then(list => {
      setChildren(list);
      if (list.length > 0 && !child) setChild(list[0]);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!demo.highlight) return;
    const timer = setTimeout(() => {
      document.querySelector(".demo-highlight")?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }, 250);
    return () => clearTimeout(timer);
  }, [demo.highlight, page]);

  useEffect(() => {
    if (demo.status !== "running") return;
    const timer = setInterval(() => {
      const elapsed = demoPausedAtRef.current + Date.now() - demoBaseRef.current;
      setDemo(prev => ({ ...prev, elapsedMs: Math.min(elapsed, DEMO_DURATION_MS) }));
      for (const step of DEMO_STEPS) {
        if (elapsed < step.at || firedStepsRef.current.has(step.id)) continue;
        firedStepsRef.current.add(step.id);
        runDemoStep(step);
      }
      if (elapsed >= DEMO_DURATION_MS && !firedStepsRef.current.has("auto-complete")) {
        firedStepsRef.current.add("auto-complete");
        setDemo(prev => ({
          ...prev,
          status: "complete",
          elapsedMs: DEMO_DURATION_MS,
          stage: "Demo complete",
          highlight: "sponsors",
        }));
      }
    }, 300);
    return () => clearInterval(timer);
  }, [demo.status]);

  async function seedMayaForDemo() {
    const result = await api.seedMayaDemo();
    const maya = result.child;
    setChildren(prev => {
      const others = prev.filter(c => c.id !== maya.id);
      return [maya, ...others];
    });
    setChild(maya);
    setSessionContext({ name: "mealtime", label: "Mealtime" });
    setPage("parent");
  }

  function runDemoStep(step) {
    setDemo(prev => ({
      ...prev,
      stage: step.label,
      highlight: step.highlight || prev.highlight,
      error: "",
    }));
    if (step.page) setPage(step.page);
    if (step.action === "seed") {
      seedMayaForDemo().catch(() => {
        setDemo(prev => ({
          ...prev,
          status: "error",
          stage: "Demo stopped",
          error: "Could not load the Maya demo. Check the backend connection.",
        }));
      });
    }
    if (step.action === "parent_command") {
      setParentCommand({ id: `${step.id}-${Date.now()}`, type: step.command });
    }
    if (step.action === "research_command") {
      setResearchCommand({ id: `${step.id}-${Date.now()}`, type: step.command });
    }
    if (step.action === "complete") {
      setDemo(prev => ({
        ...prev,
        status: "complete",
        elapsedMs: DEMO_DURATION_MS,
        stage: step.label,
        highlight: step.highlight,
      }));
    }
  }

  async function handleAddChild(name, age) {
    const newChild = await api.createChild({ name, age: parseFloat(age) });
    setChildren(prev => [...prev, newChild]);
    setChild(newChild);
  }

  async function handleSeedMaya() {
    const result = await api.seedMayaDemo();
    const maya = result.child;
    setChildren(prev => {
      const others = prev.filter(c => c.id !== maya.id);
      return [maya, ...others];
    });
    setChild(maya);
    setPage("parent");
  }

  function startDemo() {
    firedStepsRef.current = new Set();
    demoBaseRef.current = Date.now();
    demoPausedAtRef.current = 0;
    setParentCommand(null);
    setResearchCommand(null);
    setDemo({
      status: "running",
      elapsedMs: 0,
      stage: "Starting demo",
      highlight: "",
      error: "",
    });
  }

  function pauseDemo() {
    demoPausedAtRef.current = demo.elapsedMs;
    setDemo(prev => ({ ...prev, status: "paused", stage: "Demo paused" }));
  }

  function resumeDemo() {
    demoBaseRef.current = Date.now();
    setDemo(prev => ({ ...prev, status: "running", stage: "Demo resumed" }));
  }

  function resetDemo() {
    firedStepsRef.current = new Set();
    demoBaseRef.current = 0;
    demoPausedAtRef.current = 0;
    setParentCommand(null);
    setResearchCommand(null);
    setDemo({
      status: "idle",
      elapsedMs: 0,
      stage: "",
      highlight: "",
      error: "",
    });
    seedMayaForDemo().catch(() => {});
  }

  function handleNavigate(nextPage) {
    if (demo.status === "running") return;
    setPage(nextPage);
  }

  return (
    <div className="app-layout">
      <Sidebar
        child={child}
        children={children}
        onSelectChild={setChild}
        onAddChild={handleAddChild}
        activePage={page}
        onNavigate={handleNavigate}
      />
      <main className="main-content">
        <DemoController
          demo={demo}
          onStart={startDemo}
          onPause={pauseDemo}
          onResume={resumeDemo}
          onReset={resetDemo}
        />
        {!child ? (
          <div className="welcome-state">
            <div className="welcome-card">
              <div className="welcome-mark" aria-hidden="true">B</div>
              <h1>Welcome to Bridge</h1>
              <p>Add a child profile using the sidebar or load the Maya demo.</p>
              <button className="btn-primary" onClick={handleSeedMaya}>Load Maya demo</button>
            </div>
          </div>
        ) : (
          <>
            {page === "symbols"   && <SymbolBoard child={child} sessionContext={sessionContext} onContextChange={setSessionContext} />}
            {page === "parent"    && (
              <ParentView
                child={child}
                sessionContext={sessionContext}
                onContextChange={setSessionContext}
                demoCommand={parentCommand}
                demoHighlight={demo.highlight}
              />
            )}
            {page === "sessions"  && (
              <SessionLog
                child={child}
                onNavigate={setPage}
                demoHighlight={demo.highlight}
              />
            )}
            {page === "research"  && (
              <ResearchPortal
                child={child}
                demoCommand={researchCommand}
                demoHighlight={demo.highlight}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}
