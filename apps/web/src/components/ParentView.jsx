import { useEffect, useRef, useState } from "react";
import { api, WS_BASE } from "../api";

const MOCK_INTENTS = [
  {
    label: "Wants Snack",
    confidence: 0.73,
    explanation: "Repeated pointing gesture toward kitchen area with vocalizations",
  },
  {
    label: "Tired",
    confidence: 0.18,
    explanation: "Head drooping, reduced eye contact, slow movement patterns",
  },
  {
    label: "Wants to Play",
    confidence: 0.09,
    explanation: "Arm reaching toward toy shelf with excited vocalizations",
  },
];

const BAR_COLORS = ["#10b981", "#f59e0b", "#94a3b8"];

export default function ParentView({ child }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const intervalRef = useRef(null);

  const [active, setActive] = useState(false);
  const [intents, setIntents] = useState(MOCK_INTENTS);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);

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
          setIntents(data.intents.map(i => ({ ...i, explanation: "" })));
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
        const result = await api.infer(child.id, frameB64);
        if (result.intents?.length) {
          setIntents(result.intents.map(i => ({ ...i, explanation: "" })));
          setElapsed(0);
        }
      } catch {}
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

  return (
    <div className="parent-view">
      <div className="page-header">
        <div>
          <h1 className="page-title">Parent View</h1>
          <p className="page-sub">Real-time intent readout for {child.name}</p>
        </div>
      </div>

      <div className="camera-preview-lg">
        <video ref={videoRef} muted playsInline className={active ? "" : "hidden"} />
        {!active && (
          <div className="camera-placeholder-overlay">
            <span style={{ fontSize: 48 }}>📷</span>
            <p>Camera off — start a session to detect gestures</p>
            <button className="btn-primary" onClick={startSession}>
              Start Camera
            </button>
          </div>
        )}
        <canvas ref={canvasRef} className="hidden" />
        {active && (
          <button className="stop-btn" onClick={stopSession}>■ Stop</button>
        )}
      </div>

      {error && <p className="error-msg">{error}</p>}

      <div className="intent-heading">
        <h2>What they're saying right now:</h2>
        <span className="last-updated">Last updated: {elapsed}s ago</span>
      </div>

      <div className="intent-rows">
        {intents.map((intent, i) => (
          <div key={i} className="intent-row-lg">
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
          </div>
        ))}
      </div>
    </div>
  );
}
