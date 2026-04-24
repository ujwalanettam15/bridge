import { useState, useEffect } from "react";
import { api } from "../api";

const MOCK_INTENTS = [
  { label: "Wants Snack", confidence: 0.73 },
  { label: "Tired", confidence: 0.18 },
  { label: "Play", confidence: 0.09 },
];

const MOCK_JOURNAL =
  "Today was a wonderful communication day! Morning sessions showed strong hunger cues around snack time with consistent gesture patterns. The afternoon brought playful energy — lots of reaching toward the toy shelf. Communication attempts increased by 3 from yesterday. Great progress!";

const MOCK_TIMELINE = [
  { time: "9:15 AM", label: "Morning Session", emoji: "☀️", duration: "18 min" },
  { time: "11:30 AM", label: "Snack Communication", emoji: "🍎", duration: "6 min" },
  { time: "2:00 PM", label: "Play Session", emoji: "🎮", duration: "24 min" },
  { time: "4:45 PM", label: "Evening Wind Down", emoji: "🌙", duration: "12 min" },
];

const EMOTION_TAGS = [
  { emoji: "😊", label: "Happy", color: "#10b981" },
  { emoji: "😴", label: "Tired", color: "#6366f1" },
  { emoji: "🎮", label: "Playful", color: "#f59e0b" },
  { emoji: "🤗", label: "Affectionate", color: "#ec4899" },
];

const BAR_COLORS = ["#10b981", "#f59e0b", "#94a3b8"];

export default function Dashboard({ child, onNavigate }) {
  const [journal, setJournal] = useState(null);
  const [journalLoading, setJournalLoading] = useState(true);

  useEffect(() => {
    setJournalLoading(true);
    api.getJournal(child.id)
      .then(r => setJournal(r.journal))
      .catch(() => setJournal(MOCK_JOURNAL))
      .finally(() => setJournalLoading(false));
  }, [child.id]);

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric",
  });

  return (
    <div className="dashboard">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-sub">Overview for {child.name} · {today}</p>
        </div>
      </div>

      <div className="stat-row">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#ede9fe", color: "#7c3aed" }}>📅</div>
          <div className="stat-content">
            <div className="stat-value">4</div>
            <div className="stat-label">Today's Sessions</div>
            <div className="stat-sub">↑ 1 from yesterday</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#dcfce7", color: "#15803d" }}>🧠</div>
          <div className="stat-content">
            <div className="stat-value">Wants Snack 🍎</div>
            <div className="stat-label">Top Intent Today</div>
            <div className="stat-sub">73% confidence</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "#fef3c7", color: "#d97706" }}>📈</div>
          <div className="stat-content">
            <div className="stat-value">78%</div>
            <div className="stat-label">Communication Score</div>
            <div className="stat-sub">↑ 5% this week</div>
          </div>
        </div>
      </div>

      <div className="feature-row">
        <div className="feature-card">
          <div className="card-header">
            <h2>Live Communication</h2>
            <span className="live-badge">● LIVE</span>
          </div>

          <div className="camera-placeholder-lg">
            <div className="camera-icon-wrap">
              <span className="camera-icon">📷</span>
              <span className="camera-text">Camera Preview</span>
            </div>
          </div>

          <div className="intent-list-dashboard">
            {MOCK_INTENTS.map((intent, i) => (
              <div key={i} className="intent-row-dash">
                <span className="intent-label-dash">{intent.label}</span>
                <div className="intent-bar-track">
                  <div
                    className="intent-bar-fill"
                    style={{ width: `${Math.round(intent.confidence * 100)}%`, background: BAR_COLORS[i] }}
                  />
                </div>
                <span className="intent-pct-dash">{Math.round(intent.confidence * 100)}%</span>
              </div>
            ))}
          </div>

          <button className="btn-primary full-width" onClick={() => onNavigate("parent")}>
            Open Parent View →
          </button>
        </div>

        <div className="feature-card journal-card">
          <div className="card-header">
            <h2>Today I Felt</h2>
            <span className="card-date">
              {new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" })}
            </span>
          </div>
          <div className="journal-icon">📓</div>
          {journalLoading ? (
            <div className="skeleton-lines">
              <div className="skeleton-line" />
              <div className="skeleton-line" />
              <div className="skeleton-line short" />
            </div>
          ) : (
            <p className="journal-text-dash">{journal || MOCK_JOURNAL}</p>
          )}
          <div className="emotion-tags">
            {EMOTION_TAGS.map((tag, i) => (
              <span
                key={i}
                className="emotion-tag"
                style={{ background: tag.color + "20", color: tag.color }}
              >
                {tag.emoji} {tag.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="bottom-row">
        <div className="bottom-card">
          <h2 className="card-title">Session Timeline</h2>
          <div className="timeline">
            {MOCK_TIMELINE.map((s, i) => (
              <div key={i} style={{ position: "relative", display: "flex", gap: 12 }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <div className="timeline-dot">{s.emoji}</div>
                  {i < MOCK_TIMELINE.length - 1 && (
                    <div style={{ width: 2, flex: 1, background: "var(--border)", margin: "4px 0" }} />
                  )}
                </div>
                <div style={{ paddingBottom: i < MOCK_TIMELINE.length - 1 ? 14 : 0, paddingTop: 6 }}>
                  <div className="timeline-label">{s.label}</div>
                  <div className="timeline-meta">{s.time} · {s.duration}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bottom-card">
          <h2 className="card-title">Quick Actions</h2>
          <div className="quick-actions-grid">
            <button className="quick-action-btn blue" onClick={() => onNavigate("research")}>
              <span className="qa-icon">📄</span>
              <span>File IEP Request</span>
            </button>
            <button className="quick-action-btn orange" onClick={() => onNavigate("research")}>
              <span className="qa-icon">🛡</span>
              <span>Appeal Insurance</span>
            </button>
            <button className="quick-action-btn green" onClick={() => onNavigate("research")}>
              <span className="qa-icon">🧑‍⚕️</span>
              <span>Find Therapist</span>
            </button>
            <button className="quick-action-btn purple" onClick={() => onNavigate("research")}>
              <span className="qa-icon">📚</span>
              <span>AAC Research</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
