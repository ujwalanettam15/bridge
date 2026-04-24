import { useState, useEffect } from "react";
import { api } from "../api";

const SYMBOLS = [
  { emoji: "🍎", label: "Snack",    bg: "#fef2f2", color: "#ef4444" },
  { emoji: "💧", label: "Water",    bg: "#eff6ff", color: "#3b82f6" },
  { emoji: "🚽", label: "Bathroom", bg: "#fefce8", color: "#ca8a04" },
  { emoji: "😴", label: "Tired",    bg: "#f5f3ff", color: "#7c3aed" },
  { emoji: "🎮", label: "Play",     bg: "#f0fdf4", color: "#16a34a" },
  { emoji: "🤗", label: "Hug",      bg: "#fdf2f8", color: "#db2777" },
  { emoji: "🤕", label: "Hurt",     bg: "#fff1f2", color: "#e11d48" },
  { emoji: "😊", label: "Happy",    bg: "#fefce8", color: "#d97706" },
  { emoji: "😢", label: "Sad",      bg: "#eff6ff", color: "#4f46e5" },
  { emoji: "🎵", label: "Music",    bg: "#fdf4ff", color: "#9333ea" },
  { emoji: "🌳", label: "Outside",  bg: "#f0fdf4", color: "#15803d" },
  { emoji: "📺", label: "TV",       bg: "#f8fafc", color: "#475569" },
  { emoji: "✋", label: "Stop",     bg: "#fff7ed", color: "#ea580c" },
  { emoji: "➕", label: "More",     bg: "#f0fdf4", color: "#059669" },
  { emoji: "🆘", label: "Help",     bg: "#fef2f2", color: "#dc2626" },
  { emoji: "✅", label: "Yes",      bg: "#f0fdf4", color: "#10b981" },
  { emoji: "❌", label: "No",       bg: "#f8fafc", color: "#475569" },
  { emoji: "⏸", label: "Break",    bg: "#eef2ff", color: "#4f46e5" },
  { emoji: "🏁", label: "All Done", bg: "#ecfdf5", color: "#047857" },
  { emoji: "🔊", label: "Too Loud", bg: "#fff7ed", color: "#c2410c" },
  { emoji: "🔁", label: "Different", bg: "#f0f9ff", color: "#0369a1" },
  { emoji: "🩹", label: "Pain",     bg: "#fff1f2", color: "#be123c" },
];

// Phrases spoken aloud for each symbol
const PHRASES = {
  Snack: "I want a snack please",
  Water: "I want some water",
  Bathroom: "I need to use the bathroom",
  Tired: "I am tired",
  Play: "I want to play",
  Hug: "I want a hug",
  Hurt: "I am hurt",
  Happy: "I am happy",
  Sad: "I am sad",
  Music: "I want to listen to music",
  Outside: "I want to go outside",
  TV: "I want to watch TV",
  Stop: "Stop please",
  More: "I want more",
  Help: "I need help",
  Yes: "Yes",
  No: "No",
  Break: "I need a break",
  "All Done": "I am all done",
  "Too Loud": "It is too loud",
  Different: "I want something different",
  Pain: "Something hurts",
};

function speakAloud(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.9;
  utterance.pitch = 1.1;
  window.speechSynthesis.speak(utterance);
}

export default function SymbolBoard({ child, sessionContext }) {
  const [selected, setSelected] = useState(null);
  const [speaking, setSpeaking] = useState(null);
  const [predictedSymbols, setPredictedSymbols] = useState([]);
  const [predicting, setPredicting] = useState(true);

  useEffect(() => {
    setPredicting(true);
    api.predictSymbols(child.id, sessionContext)
      .then(r => {
        const symbols = r.symbols ?? [];
        setPredictedSymbols(Array.isArray(symbols) ? symbols : []);
      })
      .catch(() => {})
      .finally(() => setPredicting(false));
  }, [child.id, sessionContext]);

  function handleSelect(symbol) {
    setSelected(symbol.label);
    setSpeaking(symbol.label);
    const phrase = PHRASES[symbol.label] || symbol.label;
    speakAloud(phrase);
    // Fire Vapi call in background — this creates a voice call session on their end
    api.speak(phrase, child.id).catch(() => {});
    setTimeout(() => {
      setSelected(null);
      setSpeaking(null);
    }, 1200);
  }

  // Re-order symbols so AI-predicted ones show first with a highlight
  const predictedLabels = predictedSymbols.map(s => typeof s === "string" ? s : s.label);
  const symbolByLabel = Object.fromEntries(SYMBOLS.map(symbol => [symbol.label, symbol]));
  const suggestedSymbols = predictedSymbols
    .map(item => {
      const label = typeof item === "string" ? item : item.label;
      return {
        ...(symbolByLabel[label] || { emoji: "💬", label, bg: "#f8fafc", color: "#475569" }),
        score: typeof item === "string" ? null : item.score,
        reason: typeof item === "string" ? "Suggested for right now." : item.reason,
      };
    })
    .filter(item => item.label);

  const orderedSymbols = predictedLabels.length > 0
    ? [
        ...SYMBOLS.filter(s => predictedLabels.includes(s.label)),
        ...SYMBOLS.filter(s => !predictedLabels.includes(s.label)),
      ]
    : SYMBOLS;

  return (
    <div className="symbol-board-page">
      <div className="camera-indicator-bar">
        <span className="pulse-dot" />
        <span className="camera-status-text">
          {speaking ? `Speaking: "${PHRASES[speaking] || speaking}"` : `Detecting gestures for ${child.name}...`}
        </span>
        <span className="confidence-score">{sessionContext?.label || "Mealtime"} context</span>
        {predicting ? (
          <span className="confidence-score">Loading AI suggestions...</span>
        ) : predictedLabels.length > 0 ? (
          <span className="confidence-score" style={{ background: "#f0fdf4", color: "#15803d", borderColor: "#bbf7d0" }}>
            ✨ {predictedLabels.length} symbols predicted for right now
          </span>
        ) : null}
      </div>

      <div className="page-header">
        <div>
          <h1 className="page-title">Symbol Board</h1>
          <p className="page-sub">
            Tap a symbol to speak it aloud
            {predictedLabels.length > 0 && " · AI-suggested symbols are shown first"}
          </p>
        </div>
      </div>

      {suggestedSymbols.length > 0 && (
        <section className="suggested-symbols">
          <div className="suggested-header">
            <h2>Suggested for right now</h2>
            <span>{sessionContext?.label || "Current"} context</span>
          </div>
          <div className="suggested-row">
            {suggestedSymbols.slice(0, 4).map(symbol => (
              <button
                key={symbol.label}
                className="suggested-card"
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

      <div className="symbol-grid-4x4">
        {orderedSymbols.map((symbol, i) => {
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
    </div>
  );
}
