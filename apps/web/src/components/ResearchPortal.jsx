import { useState, useRef, useEffect } from "react";
import { api } from "../api";

const TASKS = [
  { id: "iep", label: "IEP request", description: "Draft school support language" },
  { id: "appeal", label: "Insurance appeal", description: "Prepare a parent-review appeal" },
  { id: "therapist", label: "Find therapist", description: "Search for AAC support nearby" },
];

function TinyfishResult({ result }) {
  if (!result) return null;
  // Tinyfish returns { status, task_id, result, steps, ... }
  const status = result.status ?? "unknown";
  const detail = result.result ?? result.message ?? result.detail ?? JSON.stringify(result);
  const isSuccess = status === "completed" || status === "success";
  const isRunning = status === "running" || status === "pending";
  const statusLabel = isSuccess ? "Completed" : isRunning ? "Agent running" : status;

  return (
    <div className={`tinyfish-result ${isSuccess ? "success" : isRunning ? "running" : "error"}`}>
      <div className="tf-status">
        <span className="tf-status-dot" aria-hidden="true" />
        {statusLabel}
      </div>
      {detail && <div className="tf-detail">{String(detail)}</div>}
      {result.task_id && (
        <div className="tf-meta">Task ID: {result.task_id}</div>
      )}
      {result.steps?.length > 0 && (
        <details className="tf-steps">
          <summary>Agent steps ({result.steps.length})</summary>
          <ol>
            {result.steps.map((step, i) => (
              <li key={i}>{typeof step === "string" ? step : step.description ?? JSON.stringify(step)}</li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

export default function ResearchPortal({ child }) {
  const [activeTask, setActiveTask] = useState("iep");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: `Hi! I'm here to help you navigate insurance, IEPs, school systems, and therapy options for ${child.name}. What would you like to know?`,
    },
  ]);
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  const [iepForm, setIepForm] = useState({
    childName: child.name, district: "", grade: "", disability: "",
  });
  const [iepLoading, setIepLoading] = useState(false);
  const [iepResult, setIepResult] = useState(null);
  const [iepError, setIepError] = useState(null);

  const [appealForm, setAppealForm] = useState({ provider: "", reason: "" });
  const [appealLoading, setAppealLoading] = useState(false);
  const [appealResult, setAppealResult] = useState(null);
  const [appealError, setAppealError] = useState(null);

  const [zipCode, setZipCode] = useState("");
  const [therapistResult, setTherapistResult] = useState(null);

  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(e) {
    e.preventDefault();
    if (!input.trim()) return;
    const question = input.trim();
    setInput("");
    setMessages(m => [...m, { role: "user", text: question }]);
    setChatLoading(true);
    try {
      const res = await api.askResearch(question, child.age);
      setMessages(m => [...m, { role: "assistant", text: res.answer }]);
    } catch {
      setMessages(m => [...m, { role: "assistant", text: "Sorry, something went wrong. Please try again." }]);
    } finally {
      setChatLoading(false);
    }
  }

  async function handleIep(e) {
    e.preventDefault();
    setIepLoading(true);
    setIepResult(null);
    setIepError(null);
    try {
      // Tinyfish can take up to 2 minutes — the 120s timeout in the backend handles it
      const result = await api.fileIep(child.id, iepForm.district, iepForm.grade, iepForm.disability);
      setIepResult(result);
    } catch (err) {
      setIepError("The agent request failed. Check that your Tinyfish API key is valid and the school district name is correct.");
    } finally {
      setIepLoading(false);
    }
  }

  async function handleAppeal(e) {
    e.preventDefault();
    setAppealLoading(true);
    setAppealResult(null);
    setAppealError(null);
    try {
      const result = await api.appealInsurance(child.id, appealForm.provider, appealForm.reason);
      setAppealResult(result);
    } catch (err) {
      setAppealError("The appeal request failed. Check that your Tinyfish API key is valid.");
    } finally {
      setAppealLoading(false);
    }
  }

  function handleTherapistSearch(e) {
    e.preventDefault();
    setTherapistResult("searching");
    setTimeout(() => {
      setTherapistResult(`Found results near ${zipCode}. In a full integration this would query a therapist directory API filtered by AAC certification and your insurance network.`);
    }, 1200);
  }

  function renderActiveTask() {
    if (activeTask === "iep") {
      return (
        <div className="action-form-card">
          <div className="action-form-header">
            <h3>IEP request</h3>
            <p>Draft language for parent review before anything is submitted.</p>
          </div>
          <form onSubmit={handleIep}>
            <div className="form-field">
              <label>Child Name</label>
              <input
                value={iepForm.childName}
                onChange={e => setIepForm(f => ({ ...f, childName: e.target.value }))}
                required
              />
            </div>
            <div className="form-field">
              <label>School District</label>
              <input
                placeholder="e.g. Austin ISD"
                value={iepForm.district}
                onChange={e => setIepForm(f => ({ ...f, district: e.target.value }))}
                required
              />
            </div>
            <div className="form-row">
              <div className="form-field">
                <label>Grade</label>
                <input
                  placeholder="e.g. 2nd"
                  value={iepForm.grade}
                  onChange={e => setIepForm(f => ({ ...f, grade: e.target.value }))}
                />
              </div>
              <div className="form-field">
                <label>Disability Category</label>
                <input
                  placeholder="e.g. Autism"
                  value={iepForm.disability}
                  onChange={e => setIepForm(f => ({ ...f, disability: e.target.value }))}
                />
              </div>
            </div>

            {iepLoading && (
              <div className="agent-running">
                <span className="pulse-dot" />
                <span>Drafting request and checking next steps.</span>
              </div>
            )}
            {iepResult && <TinyfishResult result={iepResult} />}
            {iepError && <div className="form-error">{iepError}</div>}

            <button type="submit" disabled={iepLoading} className="btn-action">
              {iepLoading ? "Drafting..." : "Draft IEP Request"}
            </button>
          </form>
        </div>
      );
    }

    if (activeTask === "appeal") {
      return (
        <div className="action-form-card">
          <div className="action-form-header">
            <h3>Insurance appeal</h3>
            <p>Prepare a parent-review appeal draft for AAC support.</p>
          </div>
          <form onSubmit={handleAppeal}>
            <div className="form-field">
              <label>Insurance Provider</label>
              <input
                placeholder="e.g. Blue Cross Blue Shield"
                value={appealForm.provider}
                onChange={e => setAppealForm(f => ({ ...f, provider: e.target.value }))}
                required
              />
            </div>
            <div className="form-field">
              <label>Denial Reason</label>
              <input
                placeholder="e.g. Not medically necessary"
                value={appealForm.reason}
                onChange={e => setAppealForm(f => ({ ...f, reason: e.target.value }))}
                required
              />
            </div>

            {appealLoading && (
              <div className="agent-running">
                <span className="pulse-dot" />
                <span>Drafting appeal language for parent review.</span>
              </div>
            )}
            {appealResult && <TinyfishResult result={appealResult} />}
            {appealError && <div className="form-error">{appealError}</div>}

            <button type="submit" disabled={appealLoading} className="btn-action">
              {appealLoading ? "Drafting..." : "Draft Appeal"}
            </button>
          </form>
        </div>
      );
    }

    return (
      <div className="action-form-card">
        <div className="action-form-header">
          <h3>Find therapist</h3>
          <p>Look for AAC-informed therapy support near the family.</p>
        </div>
        <form onSubmit={handleTherapistSearch}>
          <div className="form-field">
            <label>ZIP Code</label>
            <input
              placeholder="e.g. 78701"
              value={zipCode}
              onChange={e => setZipCode(e.target.value)}
              required
            />
          </div>
          {therapistResult && therapistResult !== "searching" && (
            <div className="form-success">{therapistResult}</div>
          )}
          {therapistResult === "searching" && (
            <div className="agent-running">
              <span className="pulse-dot" />
              <span>Searching for AAC-certified therapists.</span>
            </div>
          )}
          <button type="submit" className="btn-action">
            Search Therapists
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="research-portal">
      <div className="page-header">
        <div>
          <h1 className="page-title">Family Resources</h1>
          <p className="page-sub">Ask questions, draft support requests, and keep parents in control.</p>
        </div>
      </div>

      <div className="research-columns">
        <div className="research-chat-col">
          <div className="chat-card">
            <h2 className="card-title">Ask a question</h2>
            <div className="chat-messages-area">
              {messages.map((m, i) => (
                <div key={i} className={`chat-bubble ${m.role}`}>
                  {m.text}
                </div>
              ))}
              {chatLoading && (
                <div className="chat-bubble assistant typing">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </div>
              )}
              <div ref={bottomRef} />
            </div>
            <form className="chat-input-row" onSubmit={send}>
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask anything about AAC, IEP rights, insurance appeals..."
                disabled={chatLoading}
              />
              <button
                type="submit"
                disabled={chatLoading || !input.trim()}
                className="btn-primary"
              >
                Send
              </button>
            </form>
          </div>
        </div>

        <div className="research-actions-col">
          <div className="task-picker">
            {TASKS.map(task => (
              <button
                key={task.id}
                className={`task-tile ${activeTask === task.id ? "active" : ""}`}
                onClick={() => setActiveTask(task.id)}
              >
                <span>{task.label}</span>
                <small>{task.description}</small>
              </button>
            ))}
          </div>
          {renderActiveTask()}
        </div>
      </div>
    </div>
  );
}
