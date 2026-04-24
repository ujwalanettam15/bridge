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
};

function speakAloud(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.9;
  utterance.pitch = 1.1;
  window.speechSynthesis.speak(utterance);
}

export default function SymbolBoard({ child }) {
  const [selected, setSelected] = useState(null);
  const [speaking, setSpeaking] = useState(null);
  const [predictedSymbols, setPredictedSymbols] = useState([]);
  const [predicting, setPredicting] = useState(true);

  useEffect(() => {
    api.predictSymbols(child.id)
      .then(r => {
        const symbols = r.symbols ?? [];
        setPredictedSymbols(Array.isArray(symbols) ? symbols : []);
      })
      .catch(() => {})
      .finally(() => setPredicting(false));
  }, [child.id]);

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
  const orderedSymbols = predictedSymbols.length > 0
    ? [
        ...SYMBOLS.filter(s => predictedSymbols.includes(s.label)),
        ...SYMBOLS.filter(s => !predictedSymbols.includes(s.label)),
      ]
    : SYMBOLS;

  return (
    <div className="symbol-board-page">
      <div className="camera-indicator-bar">
        <span className="pulse-dot" />
        <span className="camera-status-text">
          {speaking ? `Speaking: "${PHRASES[speaking] || speaking}"` : `Detecting gestures for ${child.name}...`}
        </span>
        {predicting ? (
          <span className="confidence-score">Loading AI suggestions...</span>
        ) : predictedSymbols.length > 0 ? (
          <span className="confidence-score" style={{ background: "#f0fdf4", color: "#15803d", borderColor: "#bbf7d0" }}>
            ✨ {predictedSymbols.length} symbols predicted for right now
          </span>
        ) : null}
      </div>

      <div className="page-header">
        <div>
          <h1 className="page-title">Symbol Board</h1>
          <p className="page-sub">
            Tap a symbol to speak it aloud
            {predictedSymbols.length > 0 && " · AI-suggested symbols are shown first"}
          </p>
        </div>
      </div>

      <div className="symbol-grid-4x4">
        {orderedSymbols.map((symbol, i) => {
          const isPredicted = predictedSymbols.includes(symbol.label);
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
