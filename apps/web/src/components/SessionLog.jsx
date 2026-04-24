import { useState, useEffect } from "react";
import { api } from "../api";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const CHART_DATA = [3, 5, 2, 7, 4, 6, 4];

const MOCK_SESSIONS = [
  { id: "1", date: "Today, Apr 23", duration: "18 min", intents: ["Wants Snack", "Tired", "Play"] },
  { id: "2", date: "Today, Apr 23", duration: "24 min", intents: ["Play", "Music", "Happy"] },
  { id: "3", date: "Yesterday, Apr 22", duration: "31 min", intents: ["Water", "Hurt", "Help"] },
  { id: "4", date: "Yesterday, Apr 22", duration: "12 min", intents: ["Tired", "Hug"] },
  { id: "5", date: "Apr 21", duration: "20 min", intents: ["Snack", "Happy", "Play"] },
  { id: "6", date: "Apr 21", duration: "27 min", intents: ["Outside", "Happy", "Music"] },
];

export default function SessionLog({ child }) {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getChildLogs(child.id)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [child.id]);

  const maxVal = Math.max(...CHART_DATA);

  return (
    <div className="session-log-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Session Log</h1>
          <p className="page-sub">Communication history for {child.name}</p>
        </div>
      </div>

      <div className="stat-row-4">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#ede9fe", color: "#7c3aed" }}>📅</div>
          <div className="stat-content">
            <div className="stat-value">31</div>
            <div className="stat-label">Total Sessions</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#dcfce7", color: "#16a34a" }}>⏱</div>
          <div className="stat-content">
            <div className="stat-value">21 min</div>
            <div className="stat-label">Avg Duration</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#fef3c7", color: "#d97706" }}>🏆</div>
          <div className="stat-content">
            <div className="stat-value">Wants Snack</div>
            <div className="stat-label">Most Used Symbol</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#dbeafe", color: "#1d4ed8" }}>📈</div>
          <div className="stat-content">
            <div className="stat-value">+18%</div>
            <div className="stat-label">Progress This Week</div>
          </div>
        </div>
      </div>

      <div className="chart-card">
        <h2 className="card-title">Sessions This Week</h2>
        <div className="bar-chart">
          {CHART_DATA.map((val, i) => (
            <div key={i} className="bar-col">
              <div className="bar-value">{val}</div>
              <div className="bar" style={{ height: `${(val / maxVal) * 140}px` }} />
              <div className="bar-label">{DAYS[i]}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="sessions-card">
        <h2 className="card-title">Recent Sessions</h2>
        {loading ? (
          <div className="skeleton-lines">
            {[1, 2, 3].map(i => <div key={i} className="skeleton-line" />)}
          </div>
        ) : (
          <div className="session-list">
            {MOCK_SESSIONS.map(session => (
              <div key={session.id} className="session-item">
                <div className="session-item-left">
                  <div className="session-item-date">{session.date}</div>
                  <div className="session-item-duration">⏱ {session.duration}</div>
                </div>
                <div className="session-item-intents">
                  {session.intents.map((intent, i) => (
                    <span key={i} className={`intent-chip ${i === 0 ? "top" : ""}`}>
                      {intent}
                    </span>
                  ))}
                </div>
                <button className="btn-outline-sm">View Details</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
