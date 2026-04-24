import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";

function topIntent(log) {
  const first = log.ranked_intents?.[0];
  if (!first) return { label: "No suggestion recorded", confidence: 0 };
  return {
    label: first.label,
    confidence: first.confidence ?? first.probability ?? 0,
  };
}

function formatTime(value) {
  if (!value) return "Unknown time";
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function confidenceColor(conf) {
  if (conf >= 0.7) return "var(--primary)";
  if (conf >= 0.45) return "#f59e0b";
  return "var(--muted)";
}

function NexlaSyncStatus({ result }) {
  if (!result) return null;

  const isPrepared = result.status === "demo_mode" || result.status === "prepared";
  const isSynced = result.status === "synced";
  const isError = result.status === "error";

  return (
    <div className={`nexla-sync-status ${isPrepared ? "demo" : isSynced ? "synced" : "error"}`}>
      <div className="nexla-sync-header">
        <span className="nexla-badge">Nexla</span>
        <span className="nexla-sync-label">
          {isSynced ? "Summary synced" : isPrepared ? "Payload ready" : "Sync failed"}
        </span>
      </div>
      <p className="nexla-sync-message">{result.message}</p>
      {isPrepared && result.next_steps?.length > 0 && (
        <details className="nexla-next-steps">
          <summary>How to enable live sync</summary>
          <ol>
            {result.next_steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

function TherapistSummaryCard({ summary, onSync, syncLoading, syncResult, webhookUrl, setWebhookUrl }) {
  const [showWebhook, setShowWebhook] = useState(false);

  const generatedByLlm = summary.generated_by === "llm";

  return (
    <div className="therapist-summary-card">
      <div className="therapist-summary-header">
        <div className="therapist-summary-title-row">
          <h2 className="therapist-summary-title">Therapist Summary</h2>
          <span className="therapist-summary-meta">
            {summary.period} &middot; {summary.total_attempts} attempt{summary.total_attempts !== 1 ? "s" : ""}
            {generatedByLlm && <span className="summary-ai-badge">AI</span>}
          </span>
        </div>
        <p className="therapist-summary-sub">
          Clinical-format overview for {summary.child_name}'s care team.
        </p>
      </div>

      <div className="therapist-summary-body">
        <div className="summary-section">
          <h3 className="summary-section-title">Observed communication attempts</h3>
          <ul className="summary-list">
            {summary.observed_attempts.map((item, i) => (
              <li key={i} className="summary-item">{item}</li>
            ))}
          </ul>
        </div>

        <div className="summary-section">
          <h3 className="summary-section-title">Confirmed intents</h3>
          {summary.confirmed_intents.length === 1 && summary.confirmed_intents[0].count === 0 ? (
            <p className="summary-empty">{summary.confirmed_intents[0].label}</p>
          ) : (
            <ul className="summary-list confirmed-intents-list">
              {summary.confirmed_intents.map((item, i) => (
                <li key={i} className="summary-item confirmed-intent-item">
                  <span className="confirmed-intent-label">{item.label}</span>
                  <span className="confirmed-intent-count">{item.count}×</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="summary-section">
          <h3 className="summary-section-title">Repeated patterns</h3>
          <ul className="summary-list">
            {summary.repeated_patterns.map((item, i) => (
              <li key={i} className="summary-item">{item}</li>
            ))}
          </ul>
        </div>

        <div className="summary-section">
          <h3 className="summary-section-title">Suggested symbol-board changes</h3>
          <ul className="summary-list">
            {summary.suggested_board_changes.map((item, i) => (
              <li key={i} className="summary-item">{item}</li>
            ))}
          </ul>
        </div>

        <div className="summary-section">
          <h3 className="summary-section-title">Questions for next therapy session</h3>
          <ol className="summary-list summary-ordered">
            {summary.questions_for_session.map((q, i) => (
              <li key={i} className="summary-item">{q}</li>
            ))}
          </ol>
        </div>
      </div>

      <div className="therapist-summary-footer">
        {showWebhook && (
          <div className="webhook-row">
            <input
              className="webhook-input"
              type="url"
              placeholder="Therapist webhook URL (optional)"
              value={webhookUrl}
              onChange={e => setWebhookUrl(e.target.value)}
            />
          </div>
        )}
        <div className="summary-actions-row">
          <button
            className="btn-sync-nexla"
            onClick={() => {
              if (!showWebhook && !webhookUrl) {
                setShowWebhook(true);
              } else {
                onSync();
              }
            }}
            disabled={syncLoading}
          >
            {syncLoading ? "Syncing..." : showWebhook ? "Confirm sync" : "Sync to therapist"}
          </button>
          {showWebhook && (
            <button
              className="btn-outline-sm"
              onClick={() => { setShowWebhook(false); onSync(); }}
              disabled={syncLoading}
            >
              Skip URL
            </button>
          )}
        </div>
        <NexlaSyncStatus result={syncResult} />
      </div>
    </div>
  );
}

export default function SessionLog({ child, onNavigate, demoHighlight = "" }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  const [journal, setJournal] = useState(null);
  const [journalLoading, setJournalLoading] = useState(false);
  const journalRequestRef = useRef(null);

  const [therapistSummary, setTherapistSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);

  const [syncResult, setSyncResult] = useState(null);
  const [syncLoading, setSyncLoading] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");

  const fetchLogs = useCallback(() => {
    setLoading(true);
    api.getChildLogs(child.id)
      .then(result => setLogs(Array.isArray(result) ? result : []))
      .catch(() => setLogs([]))
      .finally(() => setLoading(false));
  }, [child.id]);

  const fetchJournal = useCallback(() => {
    if (journalRequestRef.current) return journalRequestRef.current;
    setJournalLoading(true);
    const request = api.getJournal(child.id)
      .then(result => setJournal(result.journal || null))
      .catch(() => setJournal(null))
      .finally(() => {
        journalRequestRef.current = null;
        setJournalLoading(false);
      });
    journalRequestRef.current = request;
    return request;
  }, [child.id]);

  useEffect(() => {
    fetchLogs();
    fetchJournal();
  }, [fetchLogs, fetchJournal]);

  async function handleSeedDemo() {
    setSeeding(true);
    try {
      await api.seedDemo(child.id);
      fetchLogs();
      fetchJournal();
    } catch {
      /* ignore */
    } finally {
      setSeeding(false);
    }
  }

  async function handleGenerateSummary() {
    setSummaryLoading(true);
    setSummaryError(null);
    setSyncResult(null);
    try {
      const result = await api.generateTherapistSummary(child.id);
      setTherapistSummary(result);
    } catch {
      setSummaryError("Could not generate therapist summary. Please try again.");
    } finally {
      setSummaryLoading(false);
    }
  }

  async function handleSync() {
    if (!therapistSummary) return;
    setSyncLoading(true);
    try {
      const result = await api.syncTherapistSummary(child.id, webhookUrl);
      setSyncResult(result);
    } catch {
      setSyncResult({
        status: "error",
        provider: "Nexla",
        message: "Sync request failed. The summary is still available here.",
      });
    } finally {
      setSyncLoading(false);
    }
  }

  const summary = useMemo(() => {
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    const todayLogs = logs.filter(l => new Date(l.timestamp) >= todayStart);
    const confirmed = logs.filter(l => l.confirmed_label);
    const recentConfirmed = confirmed.filter(l => new Date(l.timestamp) >= weekAgo);

    const todayCounts = {};
    todayLogs.forEach(l => {
      const label = topIntent(l).label;
      if (label !== "No suggestion recorded") {
        todayCounts[label] = (todayCounts[label] || 0) + 1;
      }
    });
    const topToday = Object.entries(todayCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "None yet";

    const confirmedCounts = {};
    confirmed.forEach(l => {
      confirmedCounts[l.confirmed_label] = (confirmedCounts[l.confirmed_label] || 0) + 1;
    });
    const mostUsed = Object.entries(confirmedCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "None yet";

    const hat = confirmed.filter(l => /hat/i.test(l.confirmed_label)).length;
    const meal = confirmed.filter(l => {
      const ctx = `${l.context?.label || ""} ${l.context?.name || ""}`;
      return /meal/i.test(ctx);
    }).length;
    const transitionRelated = confirmed.filter(l => {
      const ctx = `${l.context?.label || ""} ${l.context?.name || ""}`;
      return /transition|drop-off/i.test(ctx) || /break|hat/i.test(l.confirmed_label || "");
    }).length;
    const contextCounts = {};
    confirmed.forEach(l => {
      const ctx = l.context?.label || l.context?.name || "Session";
      contextCounts[ctx] = (contextCounts[ctx] || 0) + 1;
    });
    const topContext = Object.entries(contextCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "None yet";
    return { todayCount: todayLogs.length, topToday, mostUsed, recentPatterns: recentConfirmed.length, confirmedCount: confirmed.length, hat, meal, transitionRelated, topContext };
  }, [logs]);

  return (
    <div className="session-log-page history-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Evidence Timeline</h1>
          <p className="page-sub">Parent-confirmed moments that become support-ready documentation for {child.name}</p>
        </div>
      </div>

      <section className={`history-summary history-summary-4 ${demoHighlight === "timeline_summary" ? "demo-highlight" : ""}`}>
        <div>
          <span className="history-kicker">This week</span>
          <strong>{summary.confirmedCount}</strong>
          <span className="history-sub">confirmed moments</span>
        </div>
        <div>
          <span className="history-kicker">Meal moments</span>
          <strong>{summary.meal}</strong>
        </div>
        <div>
          <span className="history-kicker">Comfort item</span>
          <strong>{summary.hat}</strong>
        </div>
        <div>
          <span className="history-kicker">Transitions</span>
          <strong>{summary.transitionRelated}</strong>
        </div>
      </section>

      <section className={`pattern-detected-card ${demoHighlight === "timeline_pattern" ? "demo-highlight" : ""}`}>
        <div>
          <span className="history-kicker">Pattern detected</span>
          <h2>Communication supports reduce frustration during meals, transitions, and work demands.</h2>
          <p>Bridge turns varied parent-confirmed moments into structured evidence for AAC/assistive technology review and shared home-school supports.</p>
        </div>
        <button className="btn-action" onClick={() => onNavigate?.("research")}>
          Draft AAC/IEP Support Packet
        </button>
      </section>

      <section className="journal-card">
        <div className="journal-header">
          <h2 className="card-title" style={{ margin: 0 }}>Today I Felt</h2>
          <button
            className="btn-outline-sm"
            onClick={fetchJournal}
            disabled={journalLoading}
          >
            {journalLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {journalLoading ? (
          <div className="skeleton-lines">
            <div className="skeleton-line" />
            <div className="skeleton-line short" />
          </div>
        ) : journal ? (
          <p className="journal-text">{journal}</p>
        ) : (
          <p className="journal-empty">
            No communication sessions recorded today yet. Start a live session to build today's journal entry.
          </p>
        )}
      </section>

      <section className="sessions-card">
        <h2 className="card-title">Parent-Confirmed Moments</h2>
        {loading ? (
          <div className="skeleton-lines">
            {[1, 2, 3].map(i => <div key={i} className="skeleton-line" />)}
          </div>
        ) : logs.length === 0 ? (
          <div className="empty-history">
            <p>No sessions yet — Bridge refines suggestions based on parent-confirmed interactions.</p>
            <p className="empty-history-hint">Run a live session and confirm a suggestion to build this timeline. Only what you confirm updates the profile.</p>
            <button
              className="btn-seed-demo"
              onClick={handleSeedDemo}
              disabled={seeding}
            >
              {seeding ? "Loading..." : "Load demo data"}
            </button>
          </div>
        ) : (
          <div className="timeline-list">
            {logs.slice(0, 25).map(log => {
              const intent = topIntent(log);
              const dotColor = confidenceColor(intent.confidence);
              return (
                <article key={log.id} className="timeline-item">
                  <div className="timeline-indicator">
                    <span className="timeline-dot" style={{ background: dotColor }} />
                  </div>
                  <div className="timeline-body">
                    <div className="timeline-meta">
                      <span className="timeline-time">{formatTime(log.timestamp)}</span>
                      <span className="timeline-ctx">{log.context?.label || log.context?.name || "Session"}</span>
                    </div>
                    <div className="timeline-chips">
                      <span
                        className="intent-chip top"
                        style={{ borderLeftColor: dotColor }}
                      >
                        {intent.label}
                        <em className="conf-pct">{Math.round(intent.confidence * 100)}%</em>
                      </span>
                      {log.confirmed_label && (
                        <span className="intent-chip confirmed">
                          {log.confirmed_label}
                        </span>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section className="therapist-summary-section">
        <div className="therapist-summary-generate-bar">
          <div>
            <h2 className="card-title" style={{ margin: 0 }}>Therapist Summary</h2>
            <p className="page-sub" style={{ marginTop: 4 }}>
              Clinical-format overview using {child.name}'s last 7 days of session data.
            </p>
          </div>
          <button
            className="btn-generate-summary"
            onClick={handleGenerateSummary}
            disabled={summaryLoading}
          >
            {summaryLoading ? (
              <>
                <span className="pulse-dot" style={{ background: "#fff" }} />
                Generating...
              </>
            ) : therapistSummary ? "Regenerate" : "Generate therapist summary"}
          </button>
        </div>

        {summaryError && (
          <div className="form-error" style={{ marginTop: 12 }}>{summaryError}</div>
        )}

        {summaryLoading && !therapistSummary && (
          <div className="agent-running" style={{ marginTop: 12 }}>
            <span className="pulse-dot" />
            <span>Reviewing {child.name}'s confirmed interactions and building clinical summary for therapist review...</span>
          </div>
        )}

        {therapistSummary && (
          <TherapistSummaryCard
            summary={therapistSummary}
            onSync={handleSync}
            syncLoading={syncLoading}
            syncResult={syncResult}
            webhookUrl={webhookUrl}
            setWebhookUrl={setWebhookUrl}
          />
        )}
      </section>
    </div>
  );
}
