import { useState, useEffect } from "react";
import { api } from "../api";

const CONTEXTS = [
  { name: "mealtime", label: "Mealtime" },
  { name: "bedtime",  label: "Bedtime"  },
  { name: "school",   label: "School"   },
  { name: "therapy",  label: "Therapy"  },
];

const SYMBOLS = [
  { emoji: "🍎",  label: "Snack",     bg: "#fef2f2", color: "#ef4444" },
  { emoji: "💧",  label: "Water",     bg: "#eff6ff", color: "#3b82f6" },
  { emoji: "🚽",  label: "Bathroom",  bg: "#fefce8", color: "#ca8a04" },
  { emoji: "😴",  label: "Tired",     bg: "#eff6ff", color: "#1d4ed8" },
  { emoji: "🎮",  label: "Play",      bg: "#f0fdf4", color: "#16a34a" },
  { emoji: "🤗",  label: "Hug",       bg: "#fdf2f8", color: "#db2777" },
  { emoji: "🤕",  label: "Hurt",      bg: "#fff1f2", color: "#e11d48" },
  { emoji: "😊",  label: "Happy",     bg: "#fefce8", color: "#d97706" },
  { emoji: "😢",  label: "Sad",       bg: "#eff6ff", color: "#1d4ed8" },
  { emoji: "🎵",  label: "Music",     bg: "#fdf4ff", color: "#9333ea" },
  { emoji: "🌳",  label: "Outside",   bg: "#f0fdf4", color: "#15803d" },
  { emoji: "📺",  label: "TV",        bg: "#f8fafc", color: "#475569" },
  { emoji: "✋",  label: "Stop",      bg: "#fff7ed", color: "#ea580c" },
  { emoji: "➕",  label: "More",      bg: "#f0fdf4", color: "#059669" },
  { emoji: "🆘",  label: "Help",      bg: "#fef2f2", color: "#dc2626" },
  { emoji: "✅",  label: "Yes",       bg: "#f0fdf4", color: "#10b981" },
  { emoji: "❌",  label: "No",        bg: "#f8fafc", color: "#475569" },
  { emoji: "⏸",  label: "Break",     bg: "#eff6ff", color: "#1d4ed8" },
  { emoji: "🏁",  label: "All Done",  bg: "#ecfdf5", color: "#047857" },
  { emoji: "🔊",  label: "Too Loud",  bg: "#fff7ed", color: "#c2410c" },
  { emoji: "🔁",  label: "Different", bg: "#f0f9ff", color: "#0369a1" },
  { emoji: "🩹",  label: "Pain",      bg: "#fff1f2", color: "#be123c" },
  { emoji: "📖",  label: "Story",     bg: "#fdf4ff", color: "#9333ea" },
  { emoji: "🌙",  label: "Light Off", bg: "#f1f5f9", color: "#475569" },
  { emoji: "😨",  label: "Scared",    bg: "#fff7ed", color: "#ea580c" },
  { emoji: "👩‍🏫", label: "Teacher",   bg: "#eff6ff", color: "#3b82f6" },
];

const CORE_SYMBOLS = [
  "Water", "Snack", "More", "All Done",
  "Help",  "Break", "Bathroom", "Pain",
  "Too Loud", "Stop", "Yes", "No",
];

const PHRASES = {
  Snack:      "I want a snack please",
  Water:      "I want some water",
  Bathroom:   "I need to use the bathroom",
  Tired:      "I am tired",
  Play:       "I want to play",
  Hug:        "I want a hug",
  Hurt:       "I am hurt",
  Happy:      "I am happy",
  Sad:        "I am sad",
  Music:      "I want to listen to music",
  Outside:    "I want to go outside",
  TV:         "I want to watch TV",
  Stop:       "Stop please",
  More:       "I want more",
  Help:       "I need help",
  Yes:        "Yes",
  No:         "No",
  Break:      "I need a break",
  "All Done": "I am all done",
  "Too Loud": "It is too loud",
  Different:  "I want something different",
  Pain:       "Something hurts",
  Story:      "I want a story",
  "Light Off":"Please turn off the light",
  Scared:     "I am scared",
  Teacher:    "I need the teacher",
};

function speakAloud(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.9;
  utterance.pitch = 1.1;
  window.speechSynthesis.speak(utterance);
}

export default function SymbolBoard({ child, sessionContext, onContextChange }) {
  const [selected, setSelected]          = useState(null);
  const [speaking, setSpeaking]          = useState(null);
  const [predictedSymbols, setPredicted] = useState([]);
  const [predicting, setPredicting]      = useState(true);
  const [showMore, setShowMore]          = useState(false);

  useEffect(() => {
    setPredicting(true);
    api.predictSymbols(child.id, sessionContext)
      .then(r => {
        const symbols = r.symbols ?? [];
        setPredicted(Array.isArray(symbols) ? symbols : []);
      })
      .catch(() => {})
      .finally(() => setPredicting(false));
  }, [child.id, sessionContext]);

  function handleSelect(symbol) {
    setSelected(symbol.label);
    setSpeaking(symbol.label);
    const phrase = PHRASES[symbol.label] || symbol.label;
    // Browser speech fires first — Vapi failure cannot block it
    speakAloud(phrase);
    api.speak(phrase, child.id).catch(() => {});
    setTimeout(() => { setSelected(null); setSpeaking(null); }, 1200);
  }

  const symbolByLabel   = Object.fromEntries(SYMBOLS.map(s => [s.label, s]));
  const predictedLabels = predictedSymbols.map(s => (typeof s === "string" ? s : s.label));

  const suggestedSymbols = predictedSymbols
    .map(item => {
      const label  = typeof item === "string" ? item : item.label;
      const reason = typeof item === "string"
        ? `${sessionContext?.label || "Current"} context`
        : item.reason;
      return {
        ...(symbolByLabel[label] || { emoji: "💬", label, bg: "#f8fafc", color: "#475569" }),
        score: typeof item === "string" ? null : item.score,
        reason,
      };
    })
    .filter(s => s.label)
    .slice(0, 4);

  const coreSymbols = CORE_SYMBOLS.map(label => symbolByLabel[label]).filter(Boolean);
  const moreSymbols = SYMBOLS.filter(symbol => !CORE_SYMBOLS.includes(symbol.label));

  return (
    <div className="symbol-board-page">

      {/* ── Context switcher + live status ── */}
      <div className="sb-topbar">
        <div className="sb-context-strip">
          <span className="sb-context-label">Context</span>
          <div className="sb-context-buttons">
            {CONTEXTS.map(ctx => (
              <button
                key={ctx.name}
                className={`sb-context-btn ${sessionContext?.name === ctx.name ? "active" : ""}`}
                onClick={() => onContextChange?.(ctx)}
              >
                {ctx.label}
              </button>
            ))}
          </div>
        </div>
        <div className="sb-status-row">
          <span className="pulse-dot" />
          <span className="camera-status-text">
            {speaking
              ? `Speaking: "${PHRASES[speaking] || speaking}"`
              : `Ready for ${child.name}`}
          </span>
          {predicting ? (
            <span className="confidence-score">Loading suggestions…</span>
          ) : predictedLabels.length > 0 ? (
            <span className="confidence-score" style={{ background: "#f0fdf4", color: "#15803d", borderColor: "#bbf7d0" }}>
              ✨ {predictedLabels.length} suggested for {sessionContext?.label || "now"}
            </span>
          ) : null}
        </div>
      </div>

      <div className="page-header">
        <div>
          <h1 className="page-title">Symbol Board</h1>
          <p className="page-sub">Tap a symbol to speak it aloud.</p>
        </div>
      </div>

      {/* ── Suggested row — changes with context ── */}
      {suggestedSymbols.length > 0 && (
        <section className="suggested-symbols">
          <div className="suggested-header">
            <h2>Suggested for right now</h2>
            <span>{sessionContext?.label || "Current"} context</span>
          </div>
          <div className="suggested-row">
            {suggestedSymbols.map(symbol => (
              <button
                key={symbol.label}
                className={`suggested-card ${selected === symbol.label ? "selected" : ""}`}
                style={{ background: symbol.bg }}
                onClick={() => handleSelect(symbol)}
              >
                <span className="symbol-emoji">{symbol.emoji}</span>
                <span className="symbol-label" style={{ color: symbol.color }}>{symbol.label}</span>
                <span className="suggested-reason">{symbol.reason}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* ── Stable core grid — order never changes ── */}
      <div className="symbol-grid-4x4">
        {coreSymbols.map(symbol => {
          const isPredicted = predictedLabels.includes(symbol.label);
          return (
            <button
              key={symbol.label}
              className={`symbol-card ${selected === symbol.label ? "selected" : ""} ${isPredicted ? "predicted" : ""}`}
              style={{ background: symbol.bg }}
              onClick={() => handleSelect(symbol)}
            >
              {isPredicted && <span className="predicted-badge">✨</span>}
              <span className="symbol-emoji">{symbol.emoji}</span>
              <span className="symbol-label" style={{ color: symbol.color }}>{symbol.label}</span>
            </button>
          );
        })}
      </div>

      {/* ── More symbols (expandable) ── */}
      <div className="sb-safety-note">
        <span className="safety-icon">ℹ</span>
        Bridge suggests symbols based on context. Parents and therapists stay in control of the board.
      </div>

      <div className="more-symbols">
        <button className="btn-outline more-symbols-toggle" onClick={() => setShowMore(v => !v)}>
          {showMore ? "Hide more symbols" : "More symbols"}
        </button>
        {showMore && (
          <div className="more-symbol-grid">
            {moreSymbols.map(symbol => {
              const isPredicted = predictedLabels.includes(symbol.label);
              return (
                <button
                  key={symbol.label}
                  className={`more-symbol-chip ${selected === symbol.label ? "selected" : ""} ${isPredicted ? "predicted" : ""}`}
                  onClick={() => handleSelect(symbol)}
                >
                  <span>{symbol.emoji}</span>
                  <span>{symbol.label}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
