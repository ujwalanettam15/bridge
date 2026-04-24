import { useState, useRef, useEffect } from "react";
import { api } from "../api";

const IEP_STEPS = [
  "Reading child profile",
  "Drafting request",
  "Searching district portal",
  "Preparing parent review",
];

const APPEAL_STEPS = [
  "Reading child profile",
  "Drafting request",
  "Reviewing insurer requirements",
  "Preparing parent review",
];

const THERAPIST_STEPS = [
  "Reading child profile",
  "Searching therapist directories",
  "Filtering AAC matches",
  "Preparing parent review",
];

const PARENT_REVIEW_COPY =
  "Bridge prepares a parent-review packet only. Nothing is sent automatically.";

const TASKS = [
  { id: "iep", label: "IEP request", description: "Draft school support language" },
  { id: "appeal", label: "Insurance appeal", description: "Prepare a parent-review appeal" },
  { id: "therapist", label: "Find therapist", description: "Search for AAC support nearby" },
];

function AgentActivityLog({ steps, loading, done, footer }) {
  const [visibleCount, setVisibleCount] = useState(loading ? 1 : steps.length);

  useEffect(() => {
    if (!loading) {
      setVisibleCount(steps.length);
      return;
    }
    setVisibleCount(1);
    let current = 1;
    const interval = setInterval(() => {
      current += 1;
      setVisibleCount(current);
      if (current >= steps.length) clearInterval(interval);
    }, 700);
    return () => clearInterval(interval);
  }, [loading, steps.length]);

  return (
    <div className="agent-activity-log">
      <div className="agent-log-header">
        <span className="agent-log-title">Agent activity</span>
        {loading && <span className="pulse-dot" style={{ background: "var(--primary)" }} />}
        {done && <span className="agent-log-done-badge">Done</span>}
      </div>
      <ol className="agent-log-steps">
        {steps.slice(0, visibleCount).map((step, i) => {
          const isDone = done || i < visibleCount - 1;
          return (
            <li key={i} className={`agent-log-step ${isDone ? "done" : "active"}`}>
              <span className="step-icon">{isDone ? "✓" : "→"}</span>
              {step}
            </li>
          );
        })}
      </ol>
      {done && (
        <div className="agent-log-footer">{footer || "TinyFish prepared this review packet."}</div>
      )}
    </div>
  );
}

function ReviewNotice({ copy }) {
  return <div className="review-notice">{copy}</div>;
}

function DraftCard({ draft, label, status = "draft ready" }) {
  const [copied, setCopied] = useState(false);

  function copyToClipboard() {
    const text = `Subject: ${draft.subject}\n\n${draft.body}`;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="draft-card">
      <div className="draft-card-header">
        <span className="draft-label">{label}</span>
        <span className="demo-mode-badge">{status}</span>
      </div>

      <div className="draft-subject-row">
        <span className="draft-subject-label">Subject line</span>
        <span className="draft-subject">{draft.subject}</span>
      </div>

      <div className="draft-section">
        <div className="draft-section-title">Request body</div>
        <div className="draft-body-wrap">
          <pre className="draft-body">{draft.body}</pre>
        </div>
      </div>

      {draft.rationale && (
        <div className="draft-section">
          <div className="draft-section-title">Supporting rationale</div>
          <p className="draft-rationale">{draft.rationale}</p>
        </div>
      )}

      {draft.parent_next_steps?.length > 0 && (
        <div className="draft-section draft-next-steps">
          <div className="draft-section-title">Parent next steps</div>
          <ol className="draft-next-steps-list">
            {draft.parent_next_steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </div>
      )}

      <div className="draft-card-footer">
        <button className="btn-copy-draft" onClick={copyToClipboard}>
          {copied ? "Copied!" : "Copy draft"}
        </button>
      </div>
    </div>
  );
}

function TherapistResultCard({ result, zipCode, insuranceProvider }) {
  const resources = result?.resources || [];
  const isDemoMode = result?.status === "demo_mode";
  const note =
    result?.resource_note ||
    `Review these provider options yourself before outreach${
      insuranceProvider ? ` and confirm they still accept ${insuranceProvider}.` : "."
    }`;
  return (
    <div className="therapist-demo-result">
      <div className="therapist-demo-header">
        <span>AAC therapists near {zipCode}</span>
        <span className="demo-mode-badge">{isDemoMode ? "Demo results" : "Agent results"}</span>
      </div>
      {result?.message && <div className="resource-result-message">{result.message}</div>}
      <div className="therapist-demo-list">
        {resources.length > 0 ? (
          resources.map((r, i) => (
            <div key={i} className="therapist-demo-item">
              <div className="therapist-demo-name">{r.name}</div>
              <div className="therapist-demo-specialty">{r.specialty}</div>
              <div className="therapist-demo-meta">
                <span className="therapist-demo-distance">{r.distance}</span>
                <span className="therapist-demo-insurance">{r.insurance.join(" · ")}</span>
              </div>
            </div>
          ))
        ) : (
          <div className="therapist-demo-item">
            <div className="therapist-demo-specialty">
              Structured provider matches will appear here when the agent returns them.
            </div>
          </div>
        )}
      </div>
      <p className="therapist-demo-note">{note}</p>
    </div>
  );
}

function TinyfishResult({ result }) {
  if (!result) return null;
  const status = result.status ?? "unknown";
  const resultSteps = result.agent_steps ?? result.steps ?? [];
  const detail =
    typeof result.result === "string"
      ? result.result
      : result.message ?? result.detail ?? JSON.stringify(result);
  const isSuccess = status === "completed" || status === "success";
  const isRunning = status === "running" || status === "pending";
  const statusLabel = isSuccess ? "Completed" : isRunning ? "Agent running" : status;

  return (
    <div className={`tinyfish-result ${isSuccess ? "success" : isRunning ? "running" : "error"}`}>
      <div className="tf-status">
        <span className="tf-status-dot" />
        {statusLabel}
      </div>
      {detail && <div className="tf-detail">{String(detail)}</div>}
      {result.parent_control_notice && (
        <div className="tf-parent-control">{result.parent_control_notice}</div>
      )}
      {result.task_id && <div className="tf-meta">Task ID: {result.task_id}</div>}
      {resultSteps.length > 0 && (
        <details className="tf-steps">
          <summary>Agent steps ({resultSteps.length})</summary>
          <ol>
            {resultSteps.map((step, i) => (
              <li key={i}>
                {typeof step === "string" ? step : step.description ?? JSON.stringify(step)}
              </li>
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
    childName: child.name,
    district: "",
    grade: "",
    disability: "",
  });
  const [iepLoading, setIepLoading] = useState(false);
  const [iepResult, setIepResult] = useState(null);
  const [iepError, setIepError] = useState(null);

  const [appealForm, setAppealForm] = useState({ provider: "", reason: "" });
  const [appealLoading, setAppealLoading] = useState(false);
  const [appealResult, setAppealResult] = useState(null);
  const [appealError, setAppealError] = useState(null);

  const [therapistForm, setTherapistForm] = useState({ zipCode: "", insuranceProvider: "" });
  const [therapistLoading, setTherapistLoading] = useState(false);
  const [therapistResult, setTherapistResult] = useState(null);
  const [therapistError, setTherapistError] = useState(null);

  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    setMessages([
      {
        role: "assistant",
        text: `Hi! I'm here to help you navigate insurance, IEPs, school systems, and therapy options for ${child.name}. What would you like to know?`,
      },
    ]);
    setIepForm(form => ({ ...form, childName: child.name }));
  }, [child.name]);

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
      setMessages(m => [
        ...m,
        { role: "assistant", text: "Sorry, something went wrong. Please try again." },
      ]);
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
      const result = await api.fileIep(
        child.id,
        iepForm.district,
        iepForm.grade,
        iepForm.disability
      );
      setIepResult(result);
    } catch {
      setIepError(
        "The agent request failed. Check that your Tinyfish API key is valid and the school district name is correct."
      );
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
      const result = await api.appealInsurance(
        child.id,
        appealForm.provider,
        appealForm.reason
      );
      setAppealResult(result);
    } catch {
      setAppealError("The appeal request failed. Check that your Tinyfish API key is valid.");
    } finally {
      setAppealLoading(false);
    }
  }

  async function handleTherapistSearch(e) {
    e.preventDefault();
    setTherapistLoading(true);
    setTherapistResult(null);
    setTherapistError(null);
    try {
      const result = await api.searchTherapists(
        child.id,
        therapistForm.zipCode,
        therapistForm.insuranceProvider
      );
      setTherapistResult(result);
    } catch {
      setTherapistError(
        "The therapist search request failed. Check that your TinyFish API key is valid or use demo mode."
      );
    } finally {
      setTherapistLoading(false);
    }
  }

  function renderActiveTask() {
    if (activeTask === "iep") {
      const isDraftResult = Boolean(iepResult?.draft);
      const reviewNotice = iepResult?.parent_control_notice || PARENT_REVIEW_COPY;
      return (
        <div className="action-form-card">
          <div className="action-form-header blue">
            <h3>IEP request</h3>
            <p>Draft a school-ready request while keeping the parent in control before submission.</p>
          </div>
          <form onSubmit={handleIep}>
            <ReviewNotice copy={PARENT_REVIEW_COPY} />
            <div className="form-field">
              <label>Child Name</label>
              <input
                value={iepForm.childName}
                readOnly
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
                  placeholder="e.g. Autism Spectrum Disorder"
                  value={iepForm.disability}
                  onChange={e => setIepForm(f => ({ ...f, disability: e.target.value }))}
                />
              </div>
            </div>
            <button type="submit" disabled={iepLoading} className="btn-action">
              {iepLoading ? "Drafting..." : "Draft IEP Request"}
            </button>
          </form>

          {(iepLoading || iepResult) && (
            <div className="agent-workflow">
              <AgentActivityLog
                steps={iepResult?.agent_steps || IEP_STEPS}
                loading={iepLoading}
                done={!iepLoading && !!iepResult}
                footer={reviewNotice}
              />
              {isDraftResult && (
                <DraftCard
                  draft={iepResult.draft}
                  label="IEP request draft"
                  status={iepResult?.status === "demo_mode" ? "Demo mode" : "Ready for parent review"}
                />
              )}
              {iepResult && !isDraftResult && <TinyfishResult result={iepResult} />}
            </div>
          )}
          {iepError && (
            <div className="form-error" style={{ margin: "0 18px 18px" }}>
              {iepError}
            </div>
          )}
        </div>
      );
    }

    if (activeTask === "appeal") {
      const isDraftResult = Boolean(appealResult?.draft);
      const reviewNotice = appealResult?.parent_control_notice || PARENT_REVIEW_COPY;
      return (
        <div className="action-form-card">
          <div className="action-form-header orange">
            <h3>Insurance appeal</h3>
            <p>Prepare appeal language for parent review before anything is sent to the insurer.</p>
          </div>
          <form onSubmit={handleAppeal}>
            <ReviewNotice copy={PARENT_REVIEW_COPY} />
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
            <button type="submit" disabled={appealLoading} className="btn-action">
              {appealLoading ? "Drafting..." : "Draft Appeal"}
            </button>
          </form>

          {(appealLoading || appealResult) && (
            <div className="agent-workflow">
              <AgentActivityLog
                steps={appealResult?.agent_steps || APPEAL_STEPS}
                loading={appealLoading}
                done={!appealLoading && !!appealResult}
                footer={reviewNotice}
              />
              {isDraftResult && (
                <DraftCard
                  draft={appealResult.draft}
                  label="Insurance appeal draft"
                  status={
                    appealResult?.status === "demo_mode" ? "Demo mode" : "Ready for parent review"
                  }
                />
              )}
              {appealResult && !isDraftResult && <TinyfishResult result={appealResult} />}
            </div>
          )}
          {appealError && (
            <div className="form-error" style={{ margin: "0 18px 18px" }}>
              {appealError}
            </div>
          )}
        </div>
      );
    }

    return (
      <div className="action-form-card">
        <div className="action-form-header green">
          <h3>Find therapist</h3>
          <p>Compile therapist options for parent review with transparent demo labeling when needed.</p>
        </div>
        <form onSubmit={handleTherapistSearch}>
          <ReviewNotice copy="Bridge can gather options, but parents stay in control of outreach and scheduling." />
          <div className="form-field">
            <label>ZIP Code</label>
            <input
              placeholder="e.g. 78701"
              value={therapistForm.zipCode}
              onChange={e =>
                setTherapistForm(form => ({ ...form, zipCode: e.target.value }))
              }
              required
            />
          </div>
          <div className="form-field">
            <label>Insurance Plan (optional)</label>
            <input
              placeholder="e.g. Aetna"
              value={therapistForm.insuranceProvider}
              onChange={e =>
                setTherapistForm(form => ({ ...form, insuranceProvider: e.target.value }))
              }
            />
          </div>
          <button type="submit" className="btn-action" disabled={therapistLoading}>
            {therapistLoading ? "Searching..." : "Search Therapists"}
          </button>
        </form>

        {(therapistLoading || therapistResult) && (
          <div className="agent-workflow">
            <AgentActivityLog
              steps={therapistResult?.agent_steps || THERAPIST_STEPS}
              loading={therapistLoading}
              done={!therapistLoading && !!therapistResult}
              footer={
                therapistResult?.parent_control_notice ||
                "TinyFish gathered options, and parent review is still required before outreach."
              }
            />
            {therapistResult && !therapistLoading && (
              <TherapistResultCard
                result={therapistResult}
                zipCode={therapistForm.zipCode}
                insuranceProvider={therapistForm.insuranceProvider}
              />
            )}
          </div>
        )}
        {therapistError && (
          <div className="form-error" style={{ margin: "0 18px 18px" }}>
            {therapistError}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="research-portal">
      <div className="page-header">
        <div>
          <h1 className="page-title">Family Resources</h1>
          <p className="page-sub">
            Ask questions, draft support requests, and keep parents in control.
          </p>
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
