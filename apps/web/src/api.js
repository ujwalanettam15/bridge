const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const WS_BASE = import.meta.env.VITE_WS_BASE || BASE.replace(/^http/, "ws");

function asJson(response) {
  if (!response.ok) throw new Error(response.statusText || "Request failed");
  return response.json();
}

export const api = {
  listChildren: () => fetch(`${BASE}/children/`).then(asJson),
  createChild: (data) =>
    fetch(`${BASE}/children/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then(asJson),

  infer: (childId, frameB64, audioB64 = "", context = {}) =>
    fetch(`${BASE}/infer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ child_id: childId, frame_b64: frameB64, audio_b64: audioB64, context }),
    }).then(asJson),

  getJournal: (childId) =>
    fetch(`${BASE}/actions/journal/${childId}`).then(asJson),

  predictSymbols: (childId, context = {}) =>
    fetch(`${BASE}/actions/predict-symbols`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ child_id: childId, context }),
    }).then(asJson),

  speak: (phrase, childId) =>
    fetch(`${BASE}/actions/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phrase, child_id: childId }),
    }).then(asJson),

  confirmIntent: (childId, intentLogId, confirmedLabel) =>
    fetch(`${BASE}/actions/confirm-intent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        child_id: childId,
        intent_log_id: intentLogId,
        confirmed_label: confirmedLabel,
      }),
    }).then(asJson),

  fileIep: (childId, schoolDistrict, grade, disability) =>
    fetch(`${BASE}/actions/iep-request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ child_id: childId, school_district: schoolDistrict, grade, disability }),
    }).then(asJson),

  appealInsurance: (childId, insuranceProvider, denialReason) =>
    fetch(`${BASE}/actions/insurance-appeal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ child_id: childId, insurance_provider: insuranceProvider, denial_reason: denialReason }),
    }).then(asJson),

  searchTherapists: (childId, zipCode, insuranceProvider = "") =>
    fetch(`${BASE}/actions/therapist-search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        child_id: childId,
        zip_code: zipCode,
        insurance_provider: insuranceProvider,
      }),
    }).then(asJson),

  askResearch: (question, childAge, state) =>
    fetch(`${BASE}/research/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, child_age: childAge, state }),
    }).then(asJson),

  getChildLogs: (childId) =>
    fetch(`${BASE}/sessions/child/${childId}/logs`).then(asJson),

  seedDemo: (childId) =>
    fetch(`${BASE}/sessions/child/${childId}/seed-demo`, { method: "POST" }).then(asJson),

  seedMayaDemo: () =>
    fetch(`${BASE}/sessions/seed-maya-demo`, { method: "POST" }).then(asJson),

  runIepAgent: (childId, payload = {}) =>
    fetch(`${BASE}/actions/iep-agent-run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ child_id: childId, ...payload }),
    }).then(asJson),

  approveCareFollowup: (childId, agentRunId, followupType, extra = {}) =>
    fetch(`${BASE}/actions/approve-care-followup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        child_id: childId,
        agent_run_id: agentRunId,
        followup_type: followupType,
        ...extra,
      }),
    }).then(asJson),

  requestTeacherUpdate: (childId, payload = {}) =>
    fetch(`${BASE}/actions/request-teacher-update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ child_id: childId, ...payload }),
    }).then(asJson),

  getTeacherUpdates: (childId) =>
    fetch(`${BASE}/actions/teacher-updates/${childId}`).then(asJson),

  demoConfirmIntent: (childId, confirmedLabel, context = {}, confidence = 0.74) =>
    fetch(`${BASE}/actions/demo-confirm-intent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        child_id: childId,
        confirmed_label: confirmedLabel,
        context,
        confidence,
      }),
    }).then(asJson),

  getAgentEvents: (childId) =>
    fetch(`${BASE}/actions/agent-events/${childId}`).then(asJson),

  getGhostStatus: () =>
    fetch(`${BASE}/ghost/status`).then(asJson),

  getGhostEvents: (limit = 20, queue = "bridge_agent_events") =>
    fetch(`${BASE}/ghost/events?limit=${limit}&queue=${encodeURIComponent(queue)}`).then(asJson),

  generateTherapistSummary: (childId) =>
    fetch(`${BASE}/actions/therapist-summary/${childId}`).then(asJson),

  syncTherapistSummary: (childId, therapistWebhook = "") =>
    fetch(`${BASE}/actions/sync-therapist-summary/${childId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ therapist_webhook: therapistWebhook }),
    }).then(asJson),
};

export { WS_BASE };
