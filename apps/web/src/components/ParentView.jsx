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

function normalizeObjectDetection(item) {
  return {
    label: item.label || "object",
    confidence: item.confidence ?? 0,
    box: item.box || { x: 0, y: 0, w: 0, h: 0 },
    cue: item.cue || "",
  };
}

function phraseForIntent(label) {
  const cleaned = label.replace(/^wants?\s+/i, "I want ");
  if (/^i\s/i.test(cleaned)) return cleaned;
  return `I want to say: ${cleaned}`;
}

function getVideoObjectFitBox(video) {
  const bounds = video?.getBoundingClientRect();
  const videoWidth = video?.videoWidth || 320;
  const videoHeight = video?.videoHeight || 240;
  if (!bounds?.width || !bounds?.height || !videoWidth || !videoHeight) {
    return { x: 0, y: 0, width: 100, height: 100 };
  }

  const scale = Math.min(bounds.width / videoWidth, bounds.height / videoHeight);
  const renderedWidth = videoWidth * scale;
  const renderedHeight = videoHeight * scale;

  return {
    x: ((bounds.width - renderedWidth) / 2 / bounds.width) * 100,
    y: ((bounds.height - renderedHeight) / 2 / bounds.height) * 100,
    width: (renderedWidth / bounds.width) * 100,
    height: (renderedHeight / bounds.height) * 100,
  };
}

function speakAloud(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.9;
  utterance.pitch = 1.1;
  window.speechSynthesis.speak(utterance);
}

export default function ParentView({ child, sessionContext, onContextChange, demoCommand, demoHighlight = "" }) {
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
  const [documentationInsight, setDocumentationInsight] = useState(null);
  const [speaking, setSpeaking] = useState("");
  const [agentEvents, setAgentEvents] = useState([]);
  const [detectedObjects, setDetectedObjects] = useState([]);
  const [visionStatus, setVisionStatus] = useState("idle");
  const [videoFitBox, setVideoFitBox] = useState({ x: 0, y: 0, width: 100, height: 100 });

  useEffect(() => {
    contextRef.current = sessionContext;
  }, [sessionContext]);

  useEffect(() => {
    const tick = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(tick);
  }, []);

  useEffect(() => () => stopSession(), []);

  useEffect(() => {
    let cancelled = false;
    function loadEvents() {
      api.getAgentEvents(child.id)
        .then(result => {
          if (!cancelled) setAgentEvents(result.events || []);
        })
        .catch(() => {});
    }
    loadEvents();
    const timer = setInterval(loadEvents, 2500);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [child.id]);

  useEffect(() => {
    if (!demoCommand) return;
    const topIntent = intents[0] || MOCK_INTENTS[0];
    if (demoCommand.type === "speak_top_intent") {
      handleSpeak(topIntent);
    }
    if (demoCommand.type === "confirm_top_intent") {
      handleConfirm(topIntent);
    }
  }, [demoCommand?.id]);

  useEffect(() => {
    if (!active) return;
    function updateFitBox() {
      setVideoFitBox(getVideoObjectFitBox(videoRef.current));
    }
    updateFitBox();
    window.addEventListener("resize", updateFitBox);
    return () => window.removeEventListener("resize", updateFitBox);
  }, [active]);

  async function startSession() {
    setError("");
    setDetectedObjects([]);
    setVisionStatus("starting camera");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      setVideoFitBox(getVideoObjectFitBox(videoRef.current));
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
          setDetectedObjects((data.detected_objects || []).map(normalizeObjectDetection));
          if (data.intent_log_id) setIntentLogId(data.intent_log_id);
          setElapsed(0);
        }
      } catch {}
    };
    wsRef.current = ws;

    async function runInferenceFrame() {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas) return;
      if (video.readyState < 2) return;
      setVideoFitBox(getVideoObjectFitBox(video));
      const ctx = canvas.getContext("2d");
      canvas.width = 320;
      canvas.height = 240;
      ctx.drawImage(video, 0, 0, 320, 240);
      const frameB64 = canvas.toDataURL("image/jpeg", 0.6).split(",")[1];
      try {
        setVisionStatus("checking frame");
        const result = await api.infer(child.id, frameB64, "", contextRef.current);
        setVisionStatus("frame checked");
        setDetectedObjects((result.detected_objects || []).map(normalizeObjectDetection));
        if (result.intents?.length) {
          setIntents(result.intents.map(normalizeIntent));
          if (result.intent_log_id) setIntentLogId(result.intent_log_id);
          setElapsed(0);
        }
      } catch {
        setVisionStatus("backend not reachable");
        setIntents(MOCK_INTENTS);
      }
    }

    setActive(true);
    setTimeout(runInferenceFrame, 250);
    intervalRef.current = setInterval(runInferenceFrame, 1400);
  }

  function stopSession() {
    clearInterval(intervalRef.current);
    if (wsRef.current) wsRef.current.close();
    if (videoRef.current?.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(t => t.stop());
      videoRef.current.srcObject = null;
    }
    setDetectedObjects([]);
    setVisionStatus("idle");
    setActive(false);
  }

  async function handleConfirm(intent) {
    setError("");
    setConfirming(intent.label);
    try {
      const result = intentLogId
        ? await api.confirmIntent(child.id, intentLogId, intent.label)
        : await api.demoConfirmIntent(child.id, intent.label, contextRef.current, intent.confidence ?? 0.74);
      if (result.intent_log_id) setIntentLogId(result.intent_log_id);
      setConfirmed(intent.label);
      setDocumentationInsight(result.documentation_insight || null);
      setTimeout(() => setConfirmed(""), 2400);
      setTimeout(() => setDocumentationInsight(null), 7200);
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
      <div className={`page-header ${demoHighlight === "profile" ? "demo-highlight" : ""}`}>
        <div>
          <h1 className="page-title">Live Session</h1>
          <p className="page-sub">Review suggestions and speak for {child.name}</p>
        </div>
      </div>

      <div className={`context-strip ${demoHighlight === "context" ? "demo-highlight" : ""}`}>
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
        {active && (
          <div className="object-overlay" aria-hidden="true">
            {detectedObjects.map((object, i) => (
              <div
                key={`${object.label}-${i}`}
                className={`object-box object-${object.label.replace(/\s+/g, "-")}`}
                style={{
                  left: `${videoFitBox.x + object.box.x * videoFitBox.width}%`,
                  top: `${videoFitBox.y + object.box.y * videoFitBox.height}%`,
                  width: `${object.box.w * videoFitBox.width}%`,
                  height: `${object.box.h * videoFitBox.height}%`,
                }}
              >
                <span>{object.label} {Math.round(object.confidence * 100)}%</span>
              </div>
            ))}
          </div>
        )}
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

      <div className="object-detection-strip">
        <span className="object-strip-label">Visual cues</span>
        {active && detectedObjects.length > 0 ? (
          detectedObjects.map((object, i) => (
            <span key={`${object.label}-chip-${i}`} className="object-chip">
              {object.label} · {Math.round(object.confidence * 100)}%
            </span>
          ))
        ) : (
          <span className="object-chip muted">
            {active ? `${visionStatus}; watching for gray bottle or black hat` : "start camera to detect props"}
          </span>
        )}
      </div>

      {error && <p className="error-msg">{error}</p>}
      {confirmed && (
        <div className="success-msg">Added to Maya's evidence timeline.</div>
      )}
      {documentationInsight && (
        <div className="pattern-toast">
          <strong>{documentationInsight.title}</strong>
          <span>{documentationInsight.message}</span>
          <small>{documentationInsight.recommendation}</small>
        </div>
      )}

      <div className="intent-heading">
        <h2>Suggested Intent</h2>
        <span className="last-updated">Last updated: {elapsed}s ago</span>
      </div>

      <div className="profile-update-notice">
        Confirming saves the moment as documentation for {child.name}&rsquo;s evidence timeline and future pattern summaries.
      </div>

      <div className="intent-rows">
        {intents.map((intent, i) => {
          const isTop = i === 0;
          return (
          <div key={i} className={`intent-row-lg ${isTop ? "top-intent" : "secondary-intent"} ${isTop && demoHighlight === "top_intent" ? "demo-highlight" : ""}`}>
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
                title="Confirming documents this moment for future evidence and pattern summaries"
              >
                {confirming === intent.label ? "Saving..." : "Confirm & document"}
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

      <section className={`live-memory-panel ${demoHighlight === "memory" ? "demo-highlight" : ""}`}>
        <div className="live-memory-header">
          <span>Live Agent Memory</span>
          <small>Redis event stream</small>
        </div>
        <div className="live-memory-list">
          {agentEvents.length === 0 ? (
            <div className="live-memory-empty">Confirm a moment to stream evidence events here.</div>
          ) : (
            agentEvents.slice(0, 5).map((event, i) => (
              <div key={`${event.timestamp}-${i}`} className="live-memory-event">
                <span className="memory-dot" />
                <span>{event.message}</span>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
