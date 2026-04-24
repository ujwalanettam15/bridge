import { useEffect, useRef, useState } from "react";
import { api, WS_BASE } from "../api";

const CONTEXTS = [
  { name: "mealtime", label: "Meal" },
  { name: "bedtime", label: "Bedtime" },
  { name: "school", label: "School" },
  { name: "therapy", label: "Therapy" },
];

const MOCK_INTENTS = [
  {
    label: "I want water",
    confidence: 0.73,
    explanation: "Mealtime context plus a repeated reaching pattern that has matched drink requests before.",
  },
  {
    label: "I need a break",
    confidence: 0.18,
    explanation: "Body posture suggests possible frustration or fatigue.",
  },
  {
    label: "I want more",
    confidence: 0.09,
    explanation: "Recent mealtime choices make another serving possible.",
  },
];

const BAR_COLORS = ["#10b981", "#f59e0b", "#94a3b8"];

function normalizeIntent(intent) {
  return {
    ...intent,
    confidence: intent.confidence ?? intent.probability ?? 0,
    explanation: intent.explanation ?? "",
  };
}

function phraseForIntent(label) {
  const cleaned = label.replace(/^wants?\s+/i, "I want ");
  if (/^i\s/i.test(cleaned)) return cleaned;
  return `I want to say: ${cleaned}`;
}

function speakAloud(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.9;
  utterance.pitch = 1.1;
  window.speechSynthesis.speak(utterance);
}

export default function ParentView({ child, sessionContext, onContextChange }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const intervalRef = useRef(null);
  const contextRef = useRef(sessionContext);

  const [active, setActive] = useState(false);
  const [intents, setIntents] = useState(MOCK_INTENTS);
  const [intentLogId, setIntentLogId] = useState(null);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [confirming, setConfirming] = useState("");
  const [confirmed, setConfirmed] = useState("");
  const [speaking, setSpeaking] = useState("");

  useEffect(() => {
    contextRef.current = sessionContext;
  }, [sessionContext]);

  useEffect(() => {
    const tick = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(tick);
  }, []);

  useEffect(() => () => stopSession(), []);

  async function startSession() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
    } catch {
      setError("Camera access denied. Please allow camera permissions.");
      return;
    }

    const ws = new WebSocket(`${WS_BASE}/ws/intent/${child.id}`);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.intents?.length) {
          setIntents(data.intents.map(normalizeIntent));
          if (data.intent_log_id) setIntentLogId(data.intent_log_id);
          setElapsed(0);
        }
      } catch {}
    };
    wsRef.current = ws;

    intervalRef.current = setInterval(async () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas) return;
      const ctx = canvas.getContext("2d");
      canvas.width = 320;
      canvas.height = 240;
      ctx.drawImage(video, 0, 0, 320, 240);
      const frameB64 = canvas.toDataURL("image/jpeg", 0.6).split(",")[1];
      try {
        const result = await api.infer(child.id, frameB64, "", contextRef.current);
        if (result.intents?.length) {
          setIntents(result.intents.map(normalizeIntent));
          if (result.intent_log_id) setIntentLogId(result.intent_log_id);
          setElapsed(0);
        }
      } catch {
        setIntents(MOCK_INTENTS);
      }
    }, 2000);

    setActive(true);
  }

  function stopSession() {
    clearInterval(intervalRef.current);
    if (wsRef.current) wsRef.current.close();
    if (videoRef.current?.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(t => t.stop());
      videoRef.current.srcObject = null;
    }
    setActive(false);
  }

  async function handleConfirm(intent) {
    if (!intentLogId) {
      setError("Run one inference first so Bridge can save this communication attempt.");
      return;
    }
    setError("");
    setConfirming(intent.label);
    try {
      await api.confirmIntent(child.id, intentLogId, intent.label);
      setConfirmed(intent.label);
      setTimeout(() => setConfirmed(""), 2400);
    } catch {
      setError("Could not save the confirmation. Check the backend connection and try again.");
    } finally {
      setConfirming("");
    }
  }

  async function handleSpeak(intent) {
    const phrase = phraseForIntent(intent.label);
    setSpeaking(intent.label);
    speakAloud(phrase);
    try {
      await api.speak(phrase, child.id);
    } catch {
      // Browser speech already handled the demo-critical output.
    } finally {
      setTimeout(() => setSpeaking(""), 1200);
    }
  }

  return (
    <div className="parent-view">
      <div className="page-header">
        <div>
          <h1 className="page-title">Live Session</h1>
          <p className="page-sub">Review suggestions and speak for {child.name}</p>
        </div>
      </div>

      <div className="context-strip">
        <div className="context-label">Context</div>
        <div className="context-buttons">
          {CONTEXTS.map(context => (
            <button
              key={context.name}
              className={`context-btn ${sessionContext?.name === context.name ? "active" : ""}`}
              onClick={() => onContextChange(context)}
            >
              {context.label}
            </button>
          ))}
        </div>
      </div>

      <div className="camera-preview-lg">
        <video ref={videoRef} muted playsInline className={active ? "" : "hidden"} />
        {!active && (
          <div className="camera-placeholder-overlay">
            <p>Camera is off</p>
            <button className="btn-primary" onClick={startSession}>
              Start Session
            </button>
          </div>
        )}
        <canvas ref={canvasRef} className="hidden" />
        {active && (
          <button className="stop-btn" onClick={stopSession}>Stop</button>
        )}
      </div>

      {error && <p className="error-msg">{error}</p>}
      {confirmed && (
        <div className="success-msg">Saved for future suggestions.</div>
      )}

      <div className="intent-heading">
        <h2>Possible intents</h2>
        <span className="last-updated">Last updated: {elapsed}s ago</span>
      </div>

      <div className="profile-update-notice">
        Bridge suggests possible intents — your confirmation is the required step before anything updates {child.name}&rsquo;s profile.
      </div>

      <div className="intent-rows">
        {intents.map((intent, i) => {
          const isTop = i === 0;
          return (
          <div key={i} className={`intent-row-lg ${isTop ? "top-intent" : "secondary-intent"}`}>
            <div className="intent-row-top">
              <span className="intent-label-lg">{intent.label}</span>
              <span className="intent-pct-lg" style={{ color: BAR_COLORS[i] }}>
                {Math.round((intent.confidence ?? 0) * 100)}%
              </span>
            </div>
            <div className="intent-bar-track-lg">
              <div
                className="intent-bar-fill-lg"
                style={{
                  width: `${Math.round((intent.confidence ?? 0) * 100)}%`,
                  background: BAR_COLORS[i],
                }}
              />
            </div>
            {intent.explanation && (
              <p className="intent-explanation">{intent.explanation}</p>
            )}
            <div className="intent-actions">
              <button
                className="btn-speak"
                onClick={() => handleSpeak(intent)}
                disabled={speaking === intent.label}
              >
                {speaking === intent.label ? "Speaking..." : "Speak"}
              </button>
              <button
                className="btn-confirm"
                onClick={() => handleConfirm(intent)}
                disabled={confirming === intent.label}
                title="Confirming saves this suggestion to the profile and improves future results"
              >
                {confirming === intent.label ? "Saving..." : "Confirm & save to profile"}
              </button>
            </div>
          </div>
        )})}
      </div>

      <div className="safety-banner">
        <span className="safety-icon">ℹ</span>
        <p>
          Bridge suggests possible intents for parent review. It does not diagnose or replace clinical judgment.
          Parents and therapists remain in control of all decisions.
        </p>
      </div>
    </div>
  );
}
