const BASE = "http://127.0.0.1:4000";

export const api = {
  listChildren: () => fetch(`${BASE}/children/`).then((r) => r.json()),
  createChild: (data) =>
    fetch(`${BASE}/children/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then((r) => r.json()),

  infer: (childId, frameB64, audioB64 = "") =>
    fetch(`${BASE}/infer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ child_id: childId, frame_b64: frameB64, audio_b64: audioB64 }),
    }).then((r) => r.json()),

  getJournal: (childId) =>
    fetch(`${BASE}/actions/journal/${childId}`).then((r) => r.json()),

  predictSymbols: (childId) =>
    fetch(`${BASE}/actions/predict-symbols`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ child_id: childId }),
    }).then((r) => r.json()),

  speak: (phrase, childId) =>
    fetch(`${BASE}/actions/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phrase, child_id: childId }),
    }).then((r) => r.json()),

  fileIep: (childId, schoolDistrict, grade, disability) =>
    fetch(`${BASE}/actions/iep-request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ child_id: childId, school_district: schoolDistrict }),
    }).then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),

  appealInsurance: (childId, insuranceProvider, denialReason) =>
    fetch(`${BASE}/actions/insurance-appeal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ child_id: childId, insurance_provider: insuranceProvider, denial_reason: denialReason }),
    }).then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),

  askResearch: (question, childAge, state) =>
    fetch(`${BASE}/research/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, child_age: childAge, state }),
    }).then((r) => r.json()),

  getChildLogs: (childId) =>
    fetch(`${BASE}/sessions/child/${childId}/logs`).then((r) => r.json()),
};

export const WS_BASE = "ws://127.0.0.1:4000";
