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

  askResearch: (question, childAge, state) =>
    fetch(`${BASE}/research/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, child_age: childAge, state }),
    }).then(asJson),

  getChildLogs: (childId) =>
    fetch(`${BASE}/sessions/child/${childId}/logs`).then(asJson),
};

export { WS_BASE };
