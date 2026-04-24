import { useEffect, useState } from "react";
import { api } from "../api";

const DEFAULT_SOURCE_URLS = [
  "https://www.sfusd.edu/sped",
  "https://www.sfusd.edu/employees/teaching/special-education-services-employee-resources/special-education-assistive-technology-accessibility-resources",
  "https://www.cde.ca.gov/sp/se/sr/atexmpl.asp",
];

const DEFAULT_STEPS = [
  "Monitoring confirmed communication history",
  "Opening school and AAC sources with TinyFish",
  "Extracting support requirements",
  "Drafting parent-review packet",
  "Awaiting approval",
];

const TINYFISH_RUN_URL = "https://agent.tinyfish.ai/v1/automation/run";

function compactJson(value) {
  return JSON.stringify(value, null, 2);
}

function StepList({ steps, loading, done }) {
  const [visible, setVisible] = useState(loading ? 1 : steps.length);

  useEffect(() => {
    if (!loading) {
      setVisible(steps.length);
      return;
    }
    setVisible(1);
    let next = 1;
    const timer = setInterval(() => {
      next += 1;
      setVisible(Math.min(next, steps.length));
      if (next >= steps.length) clearInterval(timer);
    }, 650);
    return () => clearInterval(timer);
  }, [loading, steps.length]);

  return (
    <div className="agent-activity-log care-agent-steps">
      <div className="agent-log-header">
        <span className="agent-log-title">Care Agent run</span>
        {loading && <span className="pulse-dot" style={{ background: "var(--primary)" }} />}
        {done && <span className="agent-log-done-badge">Ready for review</span>}
      </div>
      <ol className="agent-log-steps">
        {steps.slice(0, visible).map((step, i) => {
          const checked = done || i < visible - 1;
          return (
            <li key={step} className={`agent-log-step ${checked ? "done" : "active"}`}>
              <span className="step-icon">{checked ? "✓" : "→"}</span>
              {step}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function SourceCards({ sources }) {
  if (!sources?.length) return null;
  return (
    <section className="care-section">
      <h2 className="care-section-title">Source cards</h2>
      <div className="source-card-grid">
        {sources.map((source, i) => (
          <article key={`${source.url}-${i}`} className="source-card">
            <div className="source-card-top">
              <span className="source-index">Source {i + 1}</span>
              <span className="demo-mode-badge">{source.provider || "TinyFish"}</span>
            </div>
            <h3>{source.title}</h3>
            <p>{source.extracted_fact}</p>
            <a href={source.url} target="_blank" rel="noreferrer">{source.url}</a>
          </article>
        ))}
      </div>
    </section>
  );
}

function PacketCard({ draft }) {
  if (!draft) return null;
  return (
    <section className="care-section packet-card">
      <div className="packet-header">
        <div>
          <span className="draft-label">Parent-review packet</span>
          <h2>{draft.subject}</h2>
        </div>
        <span className="demo-mode-badge">Review required</span>
      </div>
      <pre className="packet-body">{draft.body}</pre>
      {draft.rationale && (
        <div className="packet-rationale">
          <strong>Why this packet:</strong> {draft.rationale}
        </div>
      )}
      {draft.parent_next_steps?.length > 0 && (
        <ol className="packet-next-steps">
          {draft.parent_next_steps.map((step, i) => <li key={i}>{step}</li>)}
        </ol>
      )}
    </section>
  );
}

function pipelineStatus(status, fallback = "waiting") {
  if (!status) return fallback;
  return typeof status === "string" ? status : status.status || fallback;
}

function SponsorPipeline({ statuses, approvals, events, result, demoHighlight }) {
  const lastEvent = events?.[0]?.message || "Waiting for agent event";
  const rows = [
    {
      key: "redis",
      name: "Redis",
      action: "Live Agent Memory",
      status: statuses?.redis?.status || (events?.length ? "published" : "waiting"),
      detail: events?.length ? lastEvent : "Publishes confirmed moments and agent stages.",
    },
    {
      key: "tinyfish",
      name: "TinyFish",
      action: "Open-web extraction",
      status: pipelineStatus(statuses?.tinyfish, result?.sources?.length ? "sources extracted" : "waiting"),
      detail: statuses?.tinyfish?.message || "POST automation runs against school/AAC source URLs.",
    },
    {
      key: "ghost",
      name: "Ghost/Postgres",
      action: "Audit DB",
      status: result?.agent_run_id ? "audit saved" : "waiting",
      detail: result?.agent_run_id ? `AgentRun ${result.agent_run_id}` : "Stores sources, draft, approvals, and sponsor results.",
    },
    {
      key: "nexla",
      name: "Nexla Express",
      action: "Incoming Webhook",
      status: approvals?.nexla_sync?.result?.status || pipelineStatus(statuses?.nexla, "awaiting approval"),
      detail: approvals?.nexla_sync?.result?.message || "Parent-approved packet delivery waits here.",
    },
    {
      key: "vapi",
      name: "Vapi",
      action: "Care-team voice update",
      status: approvals?.vapi_update?.result?.status || pipelineStatus(statuses?.vapi, "awaiting approval"),
      detail: approvals?.vapi_update?.result?.message || "Parent-approved phone/voice update waits here.",
    },
  ];

  return (
    <section className="care-section sponsor-pipeline-card">
      <div className="pipeline-header">
        <div>
          <span className="history-kicker">Sponsor pipeline</span>
          <h2>Communication evidence to care-team action</h2>
        </div>
        <span className="pipeline-run-id">{result?.agent_run_id ? "audit saved" : "ready"}</span>
      </div>
      <div className="pipeline-grid">
        {rows.map((row, index) => (
          <article
            key={row.key}
            className={`pipeline-node ${demoHighlight === `pipeline_${row.key}` ? "demo-highlight" : ""}`}
          >
            <div className="pipeline-node-top">
              <span className="pipeline-index">{index + 1}</span>
              <span className="pipeline-status">{row.status}</span>
            </div>
            <h3>{row.name}</h3>
            <strong>{row.action}</strong>
            <p>{row.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function TechnicalTrace({ result, approvals, events, demoHighlight }) {
  const confirmedEvent = events?.find(event => event.type === "parent_confirmed")
    || events?.find(event => /Parent confirmed/i.test(event.message));
  const sources = result?.sources || [];
  const nexlaPayload = result ? {
    type: "aac_iep_support_packet",
    destination_hint: "care team",
    data: {
      child_name: "Maya",
      agent_run_id: result.agent_run_id,
      pattern_summary: result.pattern_summary,
      draft_subject: result.draft?.subject,
      source_count: sources.length,
    },
  } : null;
  const vapiPreview = approvals?.vapi_update?.result?.voice_update || (
    result ? "Hi, this is Bridge with a parent-approved update for Maya. Bridge prepared an AAC and IEP support packet for review." : ""
  );
  const traceRows = [
    {
      service: "Redis",
      action: "event published",
      status: confirmedEvent ? "confirmed" : "waiting",
      summary: confirmedEvent?.message || "Waiting for parent-confirmed moment.",
      payload: confirmedEvent?.payload,
    },
    {
      service: "TinyFish",
      action: "open-web extraction",
      status: sources.length ? `${sources.length} sources` : "waiting",
      summary: `POST ${TINYFISH_RUN_URL}`,
      payload: {
        headers: { "X-API-Key": "configured server-side" },
        body: { url: DEFAULT_SOURCE_URLS[0], goal: "Extract AAC/IEP support fact" },
      },
    },
    {
      service: "TinyFish",
      action: "facts extracted",
      status: sources.length ? "ready" : "waiting",
      summary: sources.length ? sources.map(source => source.title).join(", ") : "Source cards will appear after extraction.",
      payload: sources.map(source => ({
        title: source.title,
        url: source.url,
        extracted_fact: source.extracted_fact,
      })),
    },
    {
      service: "Ghost/Postgres",
      action: "AgentRun saved",
      status: result?.agent_run_id ? "saved" : "waiting",
      summary: result?.agent_run_id ? `Audit ID ${result.agent_run_id}` : "Waiting for packet run.",
      payload: result ? {
        agent_run_id: result.agent_run_id,
        status: result.status,
        source_count: sources.length,
        approvals: Object.keys(approvals || {}),
      } : null,
    },
    {
      service: "Nexla Express",
      action: "POST to Incoming Webhook",
      status: approvals?.nexla_sync?.result?.status || "awaiting approval",
      summary: approvals?.nexla_sync?.result?.message || "Prepared structured packet for approved data delivery.",
      payload: nexlaPayload,
    },
    {
      service: "Vapi",
      action: "care-team voice update",
      status: approvals?.vapi_update?.result?.status || "awaiting approval",
      summary: approvals?.vapi_update?.result?.message || "Prepared parent-approved voice update preview.",
      payload: vapiPreview ? { voice_update: vapiPreview } : null,
    },
  ];

  return (
    <section className={`care-section technical-trace-card ${demoHighlight === "technical_trace" ? "demo-highlight" : ""}`}>
      <div className="trace-header">
        <div>
          <span className="history-kicker">Technical trace</span>
          <h2>What the agent is doing behind the UI</h2>
        </div>
      </div>
      <div className="trace-list">
        {traceRows.map((row, index) => (
          <article key={`${row.service}-${row.action}`} className="trace-row">
            <div className="trace-row-main">
              <span className="trace-service">{row.service}</span>
              <div>
                <strong>{row.action}</strong>
                <p>{row.summary}</p>
              </div>
              <span className="trace-status">{row.status}</span>
            </div>
            {row.payload && (
              <details className="payload-preview">
                <summary>View payload</summary>
                <pre>{compactJson(row.payload)}</pre>
              </details>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function SponsorStatus({ statuses, approvals }) {
  const rows = [
    ["Redis", statuses?.redis?.status || "ready", statuses?.redis?.message || "Live agent memory publishes session and care-agent events."],
    ["TinyFish", statuses?.tinyfish?.status || "ready", statuses?.tinyfish?.message || "Ready to extract source facts."],
    ["Nexla Express", statuses?.nexla?.status || approvals?.nexla_sync?.result?.status || "awaiting approval", statuses?.nexla?.message || approvals?.nexla_sync?.result?.message || "Incoming Webhook delivery waits for parent approval."],
    ["Vapi", statuses?.vapi?.status || approvals?.vapi_update?.result?.status || "awaiting approval", statuses?.vapi?.message || approvals?.vapi_update?.result?.message || "Care-team voice update waits for parent approval."],
    ["Ghost", statuses?.ghost?.status || "audit saved", statuses?.ghost?.message || "Agent audit is stored in the configured DATABASE_URL."],
  ];
  return (
    <section className="care-section">
      <h2 className="care-section-title">Sponsor status</h2>
      <div className="sponsor-status-grid">
        {rows.map(([name, status, message]) => (
          <div key={name} className="sponsor-status-card">
            <div className="sponsor-status-top">
              <strong>{name}</strong>
              <span>{status}</span>
            </div>
            <p>{message}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function LiveMemory({ events }) {
  return (
    <section className="live-memory-panel care-memory">
      <div className="live-memory-header">
        <span>Live Agent Memory</span>
        <small>Redis event stream</small>
      </div>
      <div className="live-memory-list">
        {events.length === 0 ? (
          <div className="live-memory-empty">Run the Care Agent to stream source and approval events.</div>
        ) : (
          events.slice(0, 8).map((event, i) => (
            <div key={`${event.timestamp}-${i}`} className="live-memory-event">
              <span className="memory-dot" />
              <span>{event.message}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

export default function ResearchPortal({ child, demoCommand, demoHighlight = "" }) {
  const [form, setForm] = useState({
    school_district: "San Francisco Unified School District",
    grade: "1st",
    disability: "Autism Spectrum Disorder",
  });
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [events, setEvents] = useState([]);
  const [approvals, setApprovals] = useState({});
  const [approving, setApproving] = useState("");
  const [pendingApprovals, setPendingApprovals] = useState([]);

  function refreshEvents() {
    api.getAgentEvents(child.id)
      .then(res => setEvents(res.events || []))
      .catch(() => {});
  }

  useEffect(() => {
    refreshEvents();
    const timer = setInterval(refreshEvents, 2500);
    return () => clearInterval(timer);
  }, [child.id]);

  useEffect(() => {
    if (!demoCommand) return;
    if (demoCommand.type === "run_agent") {
      runAgent();
    }
    if (demoCommand.type === "approve_nexla") {
      handleDemoApproval("nexla_sync");
    }
    if (demoCommand.type === "approve_vapi") {
      handleDemoApproval("vapi_update");
    }
  }, [demoCommand?.id]);

  useEffect(() => {
    if (!result?.agent_run_id || approving || pendingApprovals.length === 0) return;
    const [next, ...rest] = pendingApprovals;
    setPendingApprovals(rest);
    approve(next);
  }, [result?.agent_run_id, approving, pendingApprovals]);

  useEffect(() => {
    if (!demoHighlight) return;
    const timer = setTimeout(() => {
      document.querySelector(".demo-highlight")?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }, 200);
    return () => clearTimeout(timer);
  }, [demoHighlight, result, approvals]);

  async function runAgent() {
    setRunning(true);
    setError("");
    setApprovals({});
    setPendingApprovals([]);
    try {
      const response = await api.runIepAgent(child.id, {
        ...form,
        source_urls: DEFAULT_SOURCE_URLS,
      });
      setResult(response);
      refreshEvents();
    } catch {
      setError("Care Agent run failed. Check the backend connection and try again.");
    } finally {
      setRunning(false);
    }
  }

  async function approve(type) {
    if (!result?.agent_run_id) return;
    setApproving(type);
    try {
      const response = await api.approveCareFollowup(child.id, result.agent_run_id, type);
      const nextApprovals = response.approvals || {
        ...approvals,
        [type]: { result: response.result },
      };
      setApprovals(nextApprovals);
      setResult(prev => ({
        ...prev,
        sponsor_statuses: response.sponsor_statuses || prev.sponsor_statuses,
      }));
      refreshEvents();
    } catch {
      setError(`Could not approve ${type}. The packet is still saved for review.`);
    } finally {
      setApproving("");
    }
  }

  function handleDemoApproval(type) {
    if (result?.agent_run_id) {
      approve(type);
      return;
    }
    setPendingApprovals(prev => prev.includes(type) ? prev : [...prev, type]);
  }

  const steps = result?.agent_steps || DEFAULT_STEPS;
  const statuses = result?.sponsor_statuses || {};

  return (
    <div className="research-portal care-agent-page">
      <div className="page-header care-agent-header">
        <div>
          <h1 className="page-title">Care Agent</h1>
          <p className="page-sub">
            Turn parent-confirmed moments into source-grounded AAC/IEP support packets.
          </p>
        </div>
      </div>

      <div className="care-agent-layout">
        <div className="care-agent-main">
          <section className={`care-hero-panel ${demoHighlight === "care_hero" ? "demo-highlight" : ""}`}>
            <div className="care-hero-copy">
              <span className="history-kicker">Demo action</span>
              <h2>From one communication moment to an IEP-ready support packet.</h2>
              <p>
                Bridge reviews Maya's confirmed communication pattern, extracts facts from real
                school/AAC sources with TinyFish, and prepares a packet for parent review.
              </p>
            </div>
            <div className="maya-profile-card">
              <div className="avatar" style={{ background: "#0f766e" }}>M</div>
              <div>
                <strong>Maya</strong>
                <span>Age 6 · minimally verbal</span>
                <small>Uses gestures, pointing, and picture choices</small>
                <small>Goal: AAC support across school/home routines</small>
              </div>
            </div>
          </section>

          <SponsorPipeline
            statuses={statuses}
            approvals={approvals}
            events={events}
            result={result}
            demoHighlight={demoHighlight}
          />

          <section className={`care-run-card ${demoHighlight === "care_run" ? "demo-highlight" : ""}`}>
            <div className="care-run-fields">
              <label>
                School district
                <input
                  value={form.school_district}
                  onChange={e => setForm(f => ({ ...f, school_district: e.target.value }))}
                />
              </label>
              <label>
                Grade
                <input
                  value={form.grade}
                  onChange={e => setForm(f => ({ ...f, grade: e.target.value }))}
                />
              </label>
              <label>
                Disability category
                <input
                  value={form.disability}
                  onChange={e => setForm(f => ({ ...f, disability: e.target.value }))}
                />
              </label>
            </div>
            <button className="btn-action btn-care-primary" disabled={running} onClick={runAgent}>
              {running ? "Drafting packet..." : "Draft AAC/IEP Support Packet"}
            </button>
          </section>

          {(running || result) && (
            <StepList steps={steps} loading={running} done={!running && !!result} />
          )}

          <TechnicalTrace
            result={result}
            approvals={approvals}
            events={events}
            demoHighlight={demoHighlight}
          />

          {error && <div className="form-error">{error}</div>}

          {result && (
            <>
              <div className={demoHighlight === "sources" ? "demo-highlight" : ""}>
                <SourceCards sources={result.sources} />
              </div>
              <div className={demoHighlight === "packet_full" ? "demo-highlight" : ""}>
                <PacketCard draft={result.draft} />
              </div>

              <section className={`care-section approval-card ${demoHighlight === "approval" ? "demo-highlight" : ""}`}>
                <div>
                  <span className="history-kicker">Parent approval required</span>
                  <h2>Coordinate follow-up</h2>
                  <p>{result.parent_control_notice || "Nothing is sent or called without parent approval."}</p>
                </div>
                <div className="approval-actions">
                  <button
                    className="btn-sync-nexla"
                    disabled={approving === "nexla_sync"}
                    onClick={() => approve("nexla_sync")}
                  >
                    {approving === "nexla_sync" ? "Delivering..." : "Approve Nexla Express Delivery"}
                  </button>
                  <button
                    className="btn-vapi-update"
                    disabled={approving === "vapi_update"}
                    onClick={() => approve("vapi_update")}
                  >
                    {approving === "vapi_update" ? "Preparing..." : "Approve Vapi Care-Team Update"}
                  </button>
                </div>
              </section>

              <div className={demoHighlight === "sponsors" ? "demo-highlight" : ""}>
                <SponsorStatus statuses={statuses} approvals={approvals} />
              </div>
            </>
          )}
        </div>

        <aside className="care-agent-side">
          <LiveMemory events={events} />
          <section className="care-source-list">
            <h2 className="care-section-title">Seeded open-web sources</h2>
            {DEFAULT_SOURCE_URLS.map(url => (
              <a key={url} href={url} target="_blank" rel="noreferrer">{url}</a>
            ))}
          </section>
        </aside>
      </div>
    </div>
  );
}
