import { useEffect, useMemo, useState } from "react";
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

export default function SessionLog({ child }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getChildLogs(child.id)
      .then(result => setLogs(Array.isArray(result) ? result : []))
      .catch(() => setLogs([]))
      .finally(() => setLoading(false));
  }, [child.id]);

  const summary = useMemo(() => {
    const confirmed = logs.filter(log => log.confirmed_label);
    const latest = logs[0] ? topIntent(logs[0]).label : "None yet";
    return {
      attempts: logs.length,
      confirmed: confirmed.length,
      latest,
    };
  }, [logs]);

  return (
    <div className="session-log-page history-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">History</h1>
          <p className="page-sub">Confirmed communication moments for {child.name}</p>
        </div>
      </div>

      <section className="history-summary">
        <div>
          <span className="history-kicker">Attempts</span>
          <strong>{summary.attempts}</strong>
        </div>
        <div>
          <span className="history-kicker">Confirmed</span>
          <strong>{summary.confirmed}</strong>
        </div>
        <div>
          <span className="history-kicker">Latest</span>
          <strong>{summary.latest}</strong>
        </div>
      </section>

      <section className="sessions-card">
        <h2 className="card-title">Recent moments</h2>
        {loading ? (
          <div className="skeleton-lines">
            {[1, 2, 3].map(i => <div key={i} className="skeleton-line" />)}
          </div>
        ) : logs.length === 0 ? (
          <div className="empty-history">
            Start a live session and confirm a suggestion to build this history.
          </div>
        ) : (
          <div className="session-list">
            {logs.slice(0, 20).map(log => {
              const intent = topIntent(log);
              return (
                <article key={log.id} className="session-item">
                  <div className="session-item-left">
                    <div className="session-item-date">{formatTime(log.timestamp)}</div>
                    <div className="session-item-duration">
                      {log.context?.label || log.context?.name || "Session"}
                    </div>
                  </div>
                  <div className="session-item-intents">
                    <span className="intent-chip top">
                      {intent.label} · {Math.round(intent.confidence * 100)}%
                    </span>
                    {log.confirmed_label && (
                      <span className="intent-chip confirmed">Confirmed: {log.confirmed_label}</span>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
