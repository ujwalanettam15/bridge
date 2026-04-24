import { useEffect, useState } from "react";
import { api } from "../api";

const DEFAULT_SOURCE_URLS = [
  "https://www.sfusd.edu/sped",
  "https://atic.sfusd.edu/aac-quick-reference",
  "https://help.sfusd.edu/hc/en-us/articles/360008612753-How-do-I-request-an-assistive-technology-device-for-my-eligible-special-education-student",
  "https://www.cde.ca.gov/sp/se/sr/atexmpl.asp",
];

const DEFAULT_STEPS = [
  "Monitoring confirmed communication history",
  "Opening school and AAC sources with TinyFish",
  "Extracting support requirements",
  "Drafting parent-review packet",
];

const TINYFISH_RUN_URL = "https://agent.tinyfish.ai/v1/automation/run";

function compactJson(value) {
  return JSON.stringify(value, null, 2);
}

function displayStatus(status, fallback = "waiting") {
  const raw = pipelineStatus(status, fallback);
  if (raw === "demo_mode") return "prepared";
  if (raw === "configured_by_database_url") return "configured";
  if (raw === "source_grounded") return "source grounded";
  return raw.replaceAll("_", " ");
}

function StepList({ steps, loading, done }) {
  const [visible, setVisible] = useState(loading ? 1 : steps.length);

  useEffect(() => {
    if (!loading) {
      setVisible(steps.length);
      return;
    }
    setVisible(1);
    let next = 1;
    const timer = setInterval(() => {
      next += 1;
      setVisible(Math.min(next, steps.length));
      if (next >= steps.length) clearInterval(timer);
    }, 650);
    return () => clearInterval(timer);
  }, [loading, steps.length]);

  return (
    <div className="agent-activity-log care-agent-steps">
      <div className="agent-log-header">
        <span className="agent-log-title">{loading ? "Building report from evidence + sources" : "Care Agent report run"}</span>
        {loading && <span className="pulse-dot" style={{ background: "var(--primary)" }} />}
        {done && <span className="agent-log-done-badge">Ready for review</span>}
      </div>
      <ol className="agent-log-steps">
        {steps.slice(0, visible).map((step, i) => {
          const checked = done || i < visible - 1;
          return (
            <li key={step} className={`agent-log-step ${checked ? "done" : "active"}`}>
              <span className="step-icon">{checked ? "✓" : "→"}</span>
              {step}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function SourceCards({ sources }) {
  if (!sources?.length) return null;
  return (
    <section className="care-section">
      <h2 className="care-section-title">How Bridge grounded the packet</h2>
      <div className="source-card-grid">
        {sources.map((source, i) => (
          <article key={`${source.url}-${i}`} className="source-card">
            <div className="source-card-top">
              <span className="source-index">Source {i + 1}</span>
              <span className="source-provider">{source.provider || "TinyFish"}</span>
            </div>
            <h3>{source.title}</h3>
            <p>{source.extracted_fact}</p>
            <div className="source-card-detail">
              <strong>Why Bridge used this</strong>
              <p>{source.why_bridge_used_this || "Bridge used this source to ground the support packet in real AAC/assistive technology guidance."}</p>
            </div>
            <div className="source-card-detail">
              <strong>Packet insertion</strong>
              <p>{source.packet_insertion || "Use this finding as a parent-review discussion point."}</p>
            </div>
            <a href={source.url} target="_blank" rel="noreferrer">{source.url}</a>
          </article>
        ))}
      </div>
    </section>
  );
}

function PacketCard({ draft }) {
  if (!draft) return null;
  return (
    <section className="care-section packet-card report-card">
      <div className="packet-header">
        <div>
          <span className="draft-label">AAC / IEP support packet</span>
          <h2>{draft.subject}</h2>
        </div>
        <span className="review-badge">Parent review required</span>
      </div>

      {draft.pattern_counts && (
        <div className="report-metrics">
          <div>
            <span>Confirmed moments</span>
            <strong>{draft.pattern_counts.confirmed_moments}</strong>
          </div>
          <div>
            <span>Meal moments</span>
            <strong>{draft.pattern_counts.meal_moments}</strong>
          </div>
          <div>
            <span>Comfort item</span>
            <strong>{draft.pattern_counts.comfort_item_requests}</strong>
          </div>
          <div>
            <span>Transitions</span>
            <strong>{draft.pattern_counts.transition_related_moments}</strong>
          </div>
          <div>
            <span>Sound sensitivity</span>
            <strong>{draft.pattern_counts.noise_sensitivity_moments}</strong>
          </div>
          <div>
            <span>Help requests</span>
            <strong>{draft.pattern_counts.help_request_moments}</strong>
          </div>
        </div>
      )}

      {draft.evidence_events?.length > 0 && (
        <div className="report-section">
          <h3>Evidence timeline used in this packet</h3>
          <div className="report-event-list">
            {draft.evidence_events.map((event, i) => (
              <article key={`${event.date}-${i}`} className="report-event">
                <span>{event.date}</span>
                <strong>{event.confirmed_moment}</strong>
                <p>{event.context} · {event.support_note}</p>
              </article>
            ))}
          </div>
        </div>
      )}

      <pre className="packet-body">{draft.body}</pre>

      {draft.requested_supports?.length > 0 && (
        <div className="report-section">
          <h3>Requested supports</h3>
          <div className="requested-supports">
            {draft.requested_supports.map((support, i) => <span key={i}>{support}</span>)}
          </div>
        </div>
      )}

      {draft.care_plan?.length > 0 && (
        <div className="report-section care-plan-section">
          <h3>Home-school care plan draft</h3>
          <div className="care-plan-list">
            {draft.care_plan.map((item, i) => (
              <article key={i} className="care-plan-item">
                <span>{i + 1}</span>
                <p>{item}</p>
              </article>
            ))}
          </div>
        </div>
      )}

      {draft.source_findings?.length > 0 && (
        <div className="report-section">
          <h3>Source-backed findings</h3>
          <div className="source-finding-list">
            {draft.source_findings.map((finding, i) => (
              <div key={`${finding.source}-${i}`} className="source-finding">
                <strong>{finding.source}</strong>
                <p>{finding.finding}</p>
                {finding.why_bridge_used_this && <small><b>Why Bridge used this:</b> {finding.why_bridge_used_this}</small>}
                {finding.packet_insertion && <small><b>Packet insertion:</b> {finding.packet_insertion}</small>}
              </div>
            ))}
          </div>
        </div>
      )}

      {draft.discussion_questions?.length > 0 && (
        <div className="report-section">
          <h3>Suggested IEP/team discussion questions</h3>
          <ol className="discussion-questions">
            {draft.discussion_questions.map((question, i) => <li key={i}>{question}</li>)}
          </ol>
        </div>
      )}

      {draft.rationale && (
        <div className="packet-rationale">
          <strong>Why this packet:</strong> {draft.rationale}
        </div>
      )}
      {draft.parent_next_steps?.length > 0 && (
        <ol className="packet-next-steps">
          {draft.parent_next_steps.map((step, i) => <li key={i}>{step}</li>)}
        </ol>
      )}
    </section>
  );
}

function SourceTracePanel({ trace }) {
  if (!trace?.length) return null;
  return (
    <section className="care-section source-trace-panel">
      <div className="trace-header">
        <div>
          <span className="history-kicker">Open-web work</span>
          <h2>What TinyFish extracted for the packet</h2>
        </div>
      </div>
      <div className="source-trace-grid">
        {trace.map((item, i) => (
          <article key={`${item.url}-${i}`} className="source-trace-card">
            <span>Source {i + 1}</span>
            <strong>{item.status?.replaceAll("_", " ") || "extracted"}</strong>
            <p>{item.returned_fact}</p>
            <details className="payload-preview">
              <summary>TinyFish request and result shape</summary>
              <pre>{compactJson(item.request || { url: item.url })}</pre>
              <pre>{compactJson(item.result || {
                title: `Source ${i + 1}`,
                extracted_fact: item.returned_fact,
                packet_use: item.packet_use,
              })}</pre>
            </details>
          </article>
        ))}
      </div>
    </section>
  );
}

function TeacherUpdateCard({ child, latestUpdate, running, onRequest, onApprove, approving, demoHighlight }) {
  const profile = child?.behavior_profile || {};
  const teacher = profile.teacher_contact || { name: "Ms. Rivera", role: "1st grade teacher" };
  const report = latestUpdate?.mini_report || latestUpdate?.teacher_update?.mini_report;
  const transcript = report?.transcript_excerpt || latestUpdate?.teacher_update?.transcript_messages?.map(item => item.text).join(" ");
  return (
    <section className={`care-section teacher-update-card ${demoHighlight === "teacher_update" || demoHighlight === "teacher_report" ? "demo-highlight" : ""}`}>
      <div className="teacher-update-header">
        <div>
          <span className="history-kicker">Away-from-home pipeline</span>
          <h2>Request teacher daily update</h2>
          <p>Bridge calls the teacher with parent approval, turns the transcript into evidence, and stores the report in the audit trail.</p>
        </div>
        <div className="teacher-contact-card">
          <strong>{teacher.name || "Ms. Rivera"}</strong>
          <span>{teacher.role || "1st grade teacher"}</span>
          <small>Vapi teacher call target</small>
        </div>
      </div>
      <div className="teacher-actions">
        <button className="btn-vapi-update" disabled={running} onClick={onRequest}>
          {running ? "Requesting update..." : "Request Teacher Update"}
        </button>
        {report && (
          <button
            className="btn-sync-nexla"
            disabled={approving === "teacher_update_nexla_sync"}
            onClick={onApprove}
          >
            {approving === "teacher_update_nexla_sync" ? "Delivering..." : "Approve Teacher Update to Nexla"}
          </button>
        )}
      </div>
      {report && (
        <div className="teacher-report-card">
          <div className="teacher-report-title">
            <span>{displayStatus(latestUpdate?.status || report.call_status, "report ready")}</span>
            <h3>{report.title}</h3>
          </div>
          <div className="teacher-report-grid">
            <article className="teacher-report-section teacher-transcript">
              <strong>Transcript excerpt</strong>
              <p>{transcript}</p>
            </article>
            <article className="teacher-report-section">
              <strong>Observed communication</strong>
              <ul>{report.observed_communication_moments?.map((item, i) => <li key={i}>{item}</li>)}</ul>
            </article>
            <article className="teacher-report-section">
              <strong>Supports used at school</strong>
              <ul>{report.supports_used_at_school?.map((item, i) => <li key={i}>{item}</li>)}</ul>
            </article>
            <article className="teacher-report-section">
              <strong>Home follow-up</strong>
              <ul>{report.recommended_home_follow_up?.map((item, i) => <li key={i}>{item}</li>)}</ul>
            </article>
          </div>
          <div className="teacher-evidence-strip">
            {(report.evidence_entries_added || []).map((entry, i) => (
              <span key={`${entry.confirmed_moment}-${i}`}>{entry.context}: {entry.confirmed_moment}</span>
            ))}
          </div>
          <p className="teacher-review-note">{report.parent_review_notice}</p>
        </div>
      )}
    </section>
  );
}

function pipelineStatus(status, fallback = "waiting") {
  if (!status) return fallback;
  return typeof status === "string" ? status : status.status || fallback;
}

function SponsorPipeline({ statuses, approvals, events, result, ghostStatus, teacherUpdate, demoHighlight }) {
  const lastEvent = events?.[0]?.message || "Waiting for agent event";
  const teacherStatus = teacherUpdate?.sponsor_statuses?.vapi_teacher || teacherUpdate?.teacher_update?.call_status;
  const rows = [
    {
      key: "redis",
      name: "Redis",
      action: "Live Agent Memory",
      status: displayStatus(statuses?.redis, events?.length ? "published" : "waiting"),
      detail: events?.length ? lastEvent : "Publishes confirmed moments and agent stages.",
    },
    {
      key: "vapi_teacher",
      name: "Vapi",
      action: "Teacher update call",
      status: displayStatus(teacherStatus, teacherUpdate ? "transcript ready" : "waiting"),
      detail: teacherUpdate
        ? "Teacher/caregiver update captured as transcript and mini-report evidence."
        : "Parent-approved teacher call waits here.",
    },
    {
      key: "tinyfish",
      name: "TinyFish",
      action: "Open-web extraction",
      status: displayStatus(statuses?.tinyfish, result?.sources?.length ? "sources extracted" : "waiting"),
      detail: statuses?.tinyfish?.message || "POST automation runs against school/AAC source URLs.",
    },
    {
      key: "ghost",
      name: "Ghost / TigerData",
      action: "Audit DB + durable queue",
      status: result?.agent_run_id ? "audit saved" : displayStatus(ghostStatus, "waiting"),
      detail: result?.agent_run_id
        ? `AgentRun ${result.agent_run_id} · queue events captured`
        : ghostStatus?.message || "Stores audit records, durable queue events, and optional DB fork metadata.",
    },
    {
      key: "nexla",
      name: "Nexla Express",
      action: "Incoming Webhook",
      status: displayStatus(approvals?.nexla_sync?.result || statuses?.nexla, result?.agent_run_id ? "needs approval" : "waiting"),
      detail: approvals?.nexla_sync?.result?.message || (result?.agent_run_id ? "Use the review controls beside the packet to approve delivery." : "Parent-approved packet delivery waits here."),
    },
    {
      key: "vapi",
      name: "Vapi",
      action: "Care-team voice update",
      status: displayStatus(approvals?.vapi_update?.result || statuses?.vapi, result?.agent_run_id ? "needs approval" : "waiting"),
      detail: approvals?.vapi_update?.result?.message || (result?.agent_run_id ? "Use the review controls beside the packet to approve the voice update." : "Parent-approved phone/voice update waits here."),
    },
  ];

  return (
    <section className="care-section sponsor-pipeline-card">
      <div className="pipeline-header">
        <div>
          <span className="history-kicker">Sponsor pipeline</span>
          <h2>Communication evidence to care-team action</h2>
        </div>
        <span className="pipeline-run-id">{result?.agent_run_id ? "audit saved" : "ready"}</span>
      </div>
      <div className="pipeline-grid">
        {rows.map((row, index) => (
          <article
            key={row.key}
            className={`pipeline-node ${demoHighlight === `pipeline_${row.key}` ? "demo-highlight" : ""}`}
          >
            <div className="pipeline-node-top">
              <span className="pipeline-index">{index + 1}</span>
              <span className="pipeline-status">{row.status}</span>
            </div>
            <h3>{row.name}</h3>
            <strong>{row.action}</strong>
            <p>{row.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function TechnicalTrace({ result, approvals, events, teacherUpdates, demoHighlight }) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const confirmedEvent = events?.find(event => event.type === "parent_confirmed")
    || events?.find(event => /Parent (confirmed|documented)/i.test(event.message));
  const teacherUpdate = teacherUpdates?.[0];
  const teacherReport = teacherUpdate?.mini_report || teacherUpdate?.teacher_update?.mini_report;
  const teacherDraft = teacherUpdate?.teacher_update || {};
  const sources = result?.sources || [];
  const sourceTrace = result?.source_trace || [];
  const nexlaPayload = result ? {
    type: "aac_iep_support_packet",
    destination_hint: "care team",
    data: {
      child_name: "Maya",
      agent_run_id: result.agent_run_id,
      pattern_summary: result.pattern_summary,
      draft_subject: result.draft?.subject,
      source_count: sources.length,
    },
  } : null;
  const vapiPreview = approvals?.vapi_update?.result?.voice_update || (
    result ? "Hi, this is Bridge with a parent-approved update for Maya. Bridge prepared an AAC and IEP support packet for review." : ""
  );
  const traceRows = [
    {
      id: "redis-confirmed",
      service: "Redis",
      action: "event published",
      status: confirmedEvent ? "confirmed" : "waiting",
      summary: confirmedEvent?.message || "Waiting for parent-confirmed moment.",
      payload: confirmedEvent?.payload,
      artifact: confirmedEvent ? "Live Agent Memory updated for parent-confirmed communication." : "",
    },
    {
      id: "vapi-teacher-call",
      service: "Vapi",
      action: "teacher update call",
      status: displayStatus(teacherUpdate?.sponsor_statuses?.vapi_teacher || teacherDraft?.call_status, teacherUpdate ? "requested" : "waiting"),
      summary: teacherUpdate
        ? "Parent-approved teacher/caregiver call requested. Transcript replay keeps the demo reliable when the webhook is not live."
        : "Request Teacher Update queues an outbound Vapi call to Maya's teacher.",
      payload: teacherUpdate?.sponsor_statuses?.vapi_teacher?.call_payload || teacherDraft?.call_payload,
      artifact: teacherDraft?.vapi_call_id ? `Vapi call ID ${teacherDraft.vapi_call_id}` : "Call payload prepared for Vapi.",
    },
    {
      id: "vapi-transcript",
      service: "Vapi",
      action: "transcript captured",
      status: teacherReport ? "received" : "waiting",
      summary: teacherReport?.transcript_excerpt || "Waiting for transcript or reliable replay.",
      payload: teacherDraft?.transcript_messages,
      artifact: teacherReport?.observed_communication_moments,
    },
    {
      id: "ghost-teacher",
      service: "Ghost/Postgres",
      action: "teacher AgentRun saved",
      status: teacherUpdate?.agent_run_id ? "saved" : "waiting",
      summary: teacherUpdate?.agent_run_id ? `Teacher update audit ID ${teacherUpdate.agent_run_id}` : "Teacher call/report audit waits for request.",
      payload: teacherUpdate ? {
        agent_run_id: teacherUpdate.agent_run_id,
        status: teacherUpdate.status,
        evidence_entries_added: teacherReport?.evidence_entries_added,
      } : null,
      artifact: teacherReport?.title,
    },
    {
      id: "tinyfish-source",
      service: "TinyFish",
      action: "open-web extraction",
      status: sources.length ? `${sources.length} sources` : "waiting",
      summary: sourceTrace.length ? `${sourceTrace.length} source requests prepared/executed` : `POST ${TINYFISH_RUN_URL}`,
      payload: sourceTrace.length ? sourceTrace.map(item => ({
        endpoint: TINYFISH_RUN_URL,
        request: item.request,
        status: item.status,
        returned_fact: item.returned_fact,
        packet_use: item.packet_use,
      })) : {
        headers: { "X-API-Key": "configured server-side" },
        body: { url: DEFAULT_SOURCE_URLS[0], goal: "Extract AAC/IEP support fact" },
      },
      artifact: sourceTrace.length ? "School/AAC facts returned to the report builder." : "",
    },
    {
      id: "tinyfish-facts",
      service: "TinyFish",
      action: "facts extracted",
      status: sources.length ? "ready" : "waiting",
      summary: sources.length ? sources.map(source => source.title).join(", ") : "Source cards will appear after extraction.",
      payload: sources.map(source => ({
        title: source.title,
        url: source.url,
        extracted_fact: source.extracted_fact,
        packet_insertion: source.packet_insertion,
      })),
      artifact: sources.map(source => source.extracted_fact),
    },
    {
      id: "ghost-packet",
      service: "Ghost/Postgres",
      action: "AgentRun saved",
      status: result?.agent_run_id ? "saved" : "waiting",
      summary: result?.agent_run_id ? `Audit ID ${result.agent_run_id}` : "Waiting for packet run.",
      payload: result ? {
        agent_run_id: result.agent_run_id,
        status: result.status,
        source_count: sources.length,
        approvals: Object.keys(approvals || {}),
      } : null,
      artifact: result?.agent_run_id ? "Sources, facts, draft, approvals, and sponsor statuses persisted." : "",
    },
    {
      id: "bridge-report",
      service: "Bridge",
      action: "report generated",
      status: result?.draft ? "ready" : "waiting",
      summary: result?.draft ? "Generated request letter, evidence timeline, pattern summary, requested supports, source findings, and team questions." : "Waiting for source-grounded packet.",
      payload: result?.draft ? {
        title: result.draft.subject,
        sections: [
          "Parent request letter",
          "Evidence timeline",
          "Pattern summary",
          "Requested supports",
          "Source-backed findings",
          "IEP/team discussion questions",
          "Parent approval controls",
        ],
        requested_supports: result.draft.requested_supports,
      } : null,
      artifact: result?.draft?.body,
    },
    {
      id: "nexla-packet",
      service: "Nexla Express",
      action: "POST to Incoming Webhook",
      status: displayStatus(approvals?.nexla_sync?.result, result?.agent_run_id ? "needs approval" : "waiting"),
      summary: approvals?.nexla_sync?.result?.message || "Prepared structured packet. Parent approval controls are shown with the packet.",
      payload: approvals?.nexla_sync?.result?.payload || nexlaPayload,
      artifact: approvals?.nexla_sync?.result?.nexla_response || "Packet metadata ready for Nexla Express delivery.",
    },
    {
      id: "nexla-teacher",
      service: "Nexla Express",
      action: "teacher update delivery",
      status: displayStatus(teacherUpdate?.approvals?.teacher_update_nexla_sync?.result, teacherReport ? "needs approval" : "waiting"),
      summary: teacherUpdate?.approvals?.teacher_update_nexla_sync?.result?.message || "Teacher mini-report can be delivered as structured care data after parent approval.",
      payload: teacherUpdate?.approvals?.teacher_update_nexla_sync?.result?.payload || (teacherReport ? {
        type: "teacher_daily_update",
        data: {
          agent_run_id: teacherUpdate?.agent_run_id,
          teacher: teacherReport.teacher,
          observed_communication_moments: teacherReport.observed_communication_moments,
        },
      } : null),
      artifact: teacherReport?.evidence_entries_added,
    },
    {
      id: "vapi-care",
      service: "Vapi",
      action: "care-team voice update",
      status: displayStatus(approvals?.vapi_update?.result, result?.agent_run_id ? "needs approval" : "waiting"),
      summary: approvals?.vapi_update?.result?.message || "Prepared voice update preview. Parent approval controls are shown with the packet.",
      payload: approvals?.vapi_update?.result?.call_payload || (vapiPreview ? { voice_update: vapiPreview } : null),
      artifact: approvals?.vapi_update?.result?.vapi_response || vapiPreview,
    },
  ];

  useEffect(() => {
    if (demoHighlight === "technical_trace") {
      setSelectedIndex(Math.min(2, traceRows.length - 1));
    } else if (demoHighlight === "source_trace") {
      setSelectedIndex(traceRows.findIndex(row => row.service === "TinyFish"));
    } else if (demoHighlight === "approval_controls" || demoHighlight === "nexla_payload") {
      setSelectedIndex(traceRows.findIndex(row => row.service === "Nexla Express" && row.id === "nexla-packet"));
    } else if (demoHighlight === "vapi_payload") {
      setSelectedIndex(traceRows.findIndex(row => row.id === "vapi-care"));
    } else if (demoHighlight === "teacher_update" || demoHighlight === "teacher_report") {
      setSelectedIndex(traceRows.findIndex(row => row.id === "vapi-transcript"));
    } else if (demoHighlight === "report_full") {
      setSelectedIndex(traceRows.findIndex(row => row.id === "bridge-report"));
    }
  }, [demoHighlight, result?.agent_run_id, teacherUpdate?.agent_run_id, approvals]);

  const safeIndex = selectedIndex < 0 ? 0 : Math.min(selectedIndex, traceRows.length - 1);
  const selected = traceRows[safeIndex];

  return (
    <section className={`care-section technical-trace-card ${demoHighlight === "technical_trace" ? "demo-highlight" : ""}`}>
      <div className="trace-header">
        <div>
          <span className="history-kicker">Technical trace</span>
          <h2>What the agent is doing behind the UI</h2>
        </div>
      </div>
      <div className="trace-timeline-layout">
        <div className="trace-timeline-rail">
        {traceRows.map((row, index) => (
          <button
            key={`${row.service}-${row.action}`}
            type="button"
            onClick={() => setSelectedIndex(index)}
            className={`trace-event-card ${safeIndex === index ? "active" : ""} ${
              (demoHighlight === "nexla_payload" && row.service === "Nexla Express")
              || (demoHighlight === "vapi_payload" && row.service === "Vapi")
              || (demoHighlight === "source_trace" && row.service === "TinyFish")
              || (demoHighlight === "report_full" && row.service === "Bridge")
              || (demoHighlight === "teacher_report" && row.id === "vapi-transcript")
                ? "demo-highlight"
                : ""
            }`}
          >
            <span className="trace-index">{index + 1}</span>
            <div>
              <span className="trace-service">{row.service}</span>
              <strong>{row.action}</strong>
            </div>
            <span className="trace-status">{row.status}</span>
          </button>
        ))}
        </div>
        <article className="trace-detail-panel">
          <div className="trace-detail-top">
            <span>{selected.service}</span>
            <strong>{selected.action}</strong>
            <em>{selected.status}</em>
          </div>
          <p>{selected.summary}</p>
          {selected.artifact && (
            <div className="trace-artifact">
              <span>Output artifact</span>
              <pre>{typeof selected.artifact === "string" ? selected.artifact : compactJson(selected.artifact)}</pre>
            </div>
          )}
          {selected.payload && (
            <details className="payload-preview" open>
              <summary>View payload / record</summary>
              <pre>{compactJson(selected.payload)}</pre>
            </details>
          )}
        </article>
      </div>
    </section>
  );
}

function SponsorStatus({ statuses, approvals, ghostStatus, teacherUpdate }) {
  const ghostDetail = statuses?.ghost?.message
    || ghostStatus?.message
    || "Agent audit stored in the configured DATABASE_URL. Durable Ghost queue captures agent and approval events.";
  const rows = [
    ["Redis", statuses?.redis?.status || "ready", statuses?.redis?.message || "Live agent memory publishes session and care-agent events."],
    ["TinyFish", displayStatus(statuses?.tinyfish, "ready"), statuses?.tinyfish?.message || "Ready to extract source facts."],
    ["Vapi Teacher Call", displayStatus(teacherUpdate?.sponsor_statuses?.vapi_teacher, teacherUpdate ? "transcript ready" : "ready"), teacherUpdate ? "Teacher update transcript and mini-report are saved as evidence." : "Teacher call pipeline is ready for parent approval."],
    ["Nexla Express", displayStatus(approvals?.nexla_sync?.result || statuses?.nexla, "needs approval"), approvals?.nexla_sync?.result?.message || statuses?.nexla?.message || "Incoming Webhook delivery waits for parent approval."],
    ["Vapi", displayStatus(approvals?.vapi_update?.result || statuses?.vapi, "needs approval"), approvals?.vapi_update?.result?.message || statuses?.vapi?.message || "Care-team voice update waits for parent approval."],
    ["Ghost / TigerData", displayStatus(statuses?.ghost || ghostStatus, "audit saved"), ghostDetail],
  ];
  return (
    <section className="care-section">
      <h2 className="care-section-title">Sponsor status</h2>
      <div className="sponsor-status-grid">
        {rows.map(([name, status, message]) => (
          <div key={name} className="sponsor-status-card">
            <div className="sponsor-status-top">
              <strong>{name}</strong>
              <span>{status}</span>
            </div>
            <p>{message}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function LiveMemory({ events }) {
  return (
    <section className="live-memory-panel care-memory">
      <div className="live-memory-header">
        <span>Live Agent Memory</span>
        <small>Redis event stream</small>
      </div>
      <div className="live-memory-list">
        {events.length === 0 ? (
          <div className="live-memory-empty">Run the Care Agent to stream source and approval events.</div>
        ) : (
          events.slice(0, 8).map((event, i) => (
            <div key={`${event.timestamp}-${i}`} className="live-memory-event">
              <span className="memory-dot" />
              <span>{event.message}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

export default function ResearchPortal({ child, demoCommand, demoHighlight = "" }) {
  const [form, setForm] = useState({
    school_district: "San Francisco Unified School District",
    grade: "1st",
    disability: "Autism Spectrum Disorder",
  });
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [events, setEvents] = useState([]);
  const [approvals, setApprovals] = useState({});
  const [approving, setApproving] = useState("");
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [ghostStatus, setGhostStatus] = useState(null);
  const [teacherUpdates, setTeacherUpdates] = useState([]);
  const [teacherRunning, setTeacherRunning] = useState(false);

  function refreshEvents() {
    api.getAgentEvents(child.id)
      .then(res => setEvents(res.events || []))
      .catch(() => {});
  }

  function refreshTeacherUpdates() {
    api.getTeacherUpdates(child.id)
      .then(res => setTeacherUpdates(res.updates || []))
      .catch(() => {});
  }

  useEffect(() => {
    api.getGhostStatus().then(setGhostStatus).catch(() => {});
  }, []);

  useEffect(() => {
    refreshEvents();
    refreshTeacherUpdates();
    const timer = setInterval(refreshEvents, 2500);
    return () => clearInterval(timer);
  }, [child.id]);

  useEffect(() => {
    if (!demoCommand) return;
    if (demoCommand.type === "run_agent") {
      runAgent();
    }
    if (demoCommand.type === "request_teacher_update") {
      requestTeacherUpdate();
    }
    if (demoCommand.type === "approve_nexla") {
      handleDemoApproval("nexla_sync");
    }
    if (demoCommand.type === "approve_vapi") {
      handleDemoApproval("vapi_update");
    }
  }, [demoCommand?.id]);

  useEffect(() => {
    if (!result?.agent_run_id || approving || pendingApprovals.length === 0) return;
    const [next, ...rest] = pendingApprovals;
    setPendingApprovals(rest);
    approve(next);
  }, [result?.agent_run_id, approving, pendingApprovals]);

  async function runAgent() {
    setRunning(true);
    setError("");
    setApprovals({});
    setPendingApprovals([]);
    try {
      const response = await api.runIepAgent(child.id, {
        ...form,
        source_urls: DEFAULT_SOURCE_URLS,
      });
      setResult(response);
      refreshEvents();
    } catch {
      setError("Care Agent run failed. Check the backend connection and try again.");
    } finally {
      setRunning(false);
    }
  }

  async function requestTeacherUpdate() {
    if (teacherRunning) return;
    setTeacherRunning(true);
    setError("");
    try {
      const profile = child.behavior_profile || {};
      const response = await api.requestTeacherUpdate(child.id, {
        teacher_contact: profile.teacher_contact || {},
      });
      setTeacherUpdates(prev => [
        {
          agent_run_id: response.agent_run_id,
          status: response.status,
          teacher_update: response.teacher_update,
          mini_report: response.mini_report,
          sponsor_statuses: response.sponsor_statuses,
          approvals: {},
        },
        ...prev.filter(item => item.agent_run_id !== response.agent_run_id),
      ]);
      refreshEvents();
    } catch {
      setError("Teacher update request failed. The packet flow is still available.");
    } finally {
      setTeacherRunning(false);
    }
  }

  async function approve(type) {
    if (!result?.agent_run_id) return;
    setApproving(type);
    try {
      const response = await api.approveCareFollowup(child.id, result.agent_run_id, type);
      const nextApprovals = response.approvals || {
        ...approvals,
        [type]: { result: response.result },
      };
      setApprovals(nextApprovals);
      setResult(prev => ({
        ...prev,
        sponsor_statuses: response.sponsor_statuses || prev.sponsor_statuses,
      }));
      refreshEvents();
    } catch {
      setError(`Could not approve ${type}. The packet is still saved for review.`);
    } finally {
      setApproving("");
    }
  }

  async function approveTeacherUpdate() {
    const update = teacherUpdates[0];
    if (!update?.agent_run_id) return;
    setApproving("teacher_update_nexla_sync");
    try {
      const response = await api.approveCareFollowup(child.id, update.agent_run_id, "teacher_update_nexla_sync");
      setTeacherUpdates(prev => prev.map(item => (
        item.agent_run_id === update.agent_run_id
          ? {
              ...item,
              sponsor_statuses: response.sponsor_statuses || item.sponsor_statuses,
              approvals: response.approvals || item.approvals,
              status: response.status || item.status,
            }
          : item
      )));
      refreshEvents();
    } catch {
      setError("Could not deliver the teacher update through Nexla. The mini-report is still saved.");
    } finally {
      setApproving("");
    }
  }

  function handleDemoApproval(type) {
    if (result?.agent_run_id) {
      approve(type);
      return;
    }
    setPendingApprovals(prev => prev.includes(type) ? prev : [...prev, type]);
  }

  const steps = result?.agent_steps || DEFAULT_STEPS;
  const statuses = result?.sponsor_statuses || {};
  const latestTeacherUpdate = teacherUpdates[0];

  return (
    <div className="research-portal care-agent-page">
      <div className="page-header care-agent-header">
        <div>
          <h1 className="page-title">Care Agent</h1>
          <p className="page-sub">
            Turn parent-confirmed moments into source-grounded AAC/IEP support packets.
          </p>
        </div>
      </div>

      <div className="care-agent-layout">
        <div className="care-agent-main">
          <section className={`care-hero-panel ${demoHighlight === "care_hero" ? "demo-highlight" : ""}`}>
            <div className="care-hero-copy">
              <span className="history-kicker">Agent action</span>
              <h2>From one communication moment to an IEP-ready support packet.</h2>
              <p>
                Bridge reviews Maya's confirmed communication pattern, extracts facts from real
                school/AAC sources with TinyFish, and prepares a packet for parent review.
              </p>
            </div>
            <div className="maya-profile-card">
              <div className="avatar" style={{ background: "#0f766e" }}>M</div>
              <div>
                <strong>Maya</strong>
                <span>Age 6 · minimally verbal</span>
                <small>Uses gestures, pointing, and picture choices</small>
                <small>Goal: AAC support across school/home routines</small>
              </div>
            </div>
          </section>

          <SponsorPipeline
            statuses={statuses}
            approvals={approvals}
            events={events}
            result={result}
            ghostStatus={ghostStatus}
            teacherUpdate={latestTeacherUpdate}
            demoHighlight={demoHighlight}
          />

          <TeacherUpdateCard
            child={child}
            latestUpdate={latestTeacherUpdate}
            running={teacherRunning}
            onRequest={requestTeacherUpdate}
            onApprove={approveTeacherUpdate}
            approving={approving}
            demoHighlight={demoHighlight}
          />

          <section className={`care-run-card ${demoHighlight === "care_run" ? "demo-highlight" : ""}`}>
            <div className="care-run-fields">
              <label>
                School district
                <input
                  value={form.school_district}
                  onChange={e => setForm(f => ({ ...f, school_district: e.target.value }))}
                />
              </label>
              <label>
                Grade
                <input
                  value={form.grade}
                  onChange={e => setForm(f => ({ ...f, grade: e.target.value }))}
                />
              </label>
              <label>
                Disability category
                <input
                  value={form.disability}
                  onChange={e => setForm(f => ({ ...f, disability: e.target.value }))}
                />
              </label>
            </div>
            <button className="btn-action btn-care-primary" disabled={running} onClick={runAgent}>
              {running ? "Building report..." : "Draft AAC/IEP Support Packet"}
            </button>
          </section>

          {(running || result) && (
            <StepList steps={steps} loading={running} done={!running && !!result} />
          )}

          {running && (
            <section className="care-section approval-card approval-card-pending">
              <div>
                <span className="history-kicker">Building report</span>
                <h2>Building report from evidence + sources.</h2>
                <p>Bridge is reading Maya's evidence timeline, extracting source-backed AAC/AT facts, and saving the AgentRun audit before approvals appear.</p>
              </div>
            </section>
          )}

          {error && <div className="form-error">{error}</div>}

          {result && (
            <>
              <div className={demoHighlight === "report_full" || demoHighlight === "packet_full" ? "demo-highlight" : ""}>
                <PacketCard draft={result.draft} />
              </div>

              <div className={demoHighlight === "source_trace" || demoHighlight === "sources" ? "demo-highlight" : ""}>
                <SourceTracePanel trace={result.source_trace} />
                <SourceCards sources={result.sources} />
              </div>

              <section className={`care-section approval-card approval-card-primary ${demoHighlight === "approval_controls" || demoHighlight === "approval" ? "demo-highlight" : ""}`}>
                <div>
                  <span className="history-kicker">Parent review required</span>
                  <h2>Report ready. Choose the follow-up.</h2>
                  <p>{result.parent_control_notice || "Nothing is sent or called without parent approval."}</p>
                </div>
                <div className="approval-actions">
                  <button
                    className="btn-sync-nexla"
                    disabled={approving === "nexla_sync"}
                    onClick={() => approve("nexla_sync")}
                  >
                    {approving === "nexla_sync" ? "Delivering..." : "Approve Nexla Express Delivery"}
                  </button>
                  <button
                    className="btn-vapi-update"
                    disabled={approving === "vapi_update"}
                    onClick={() => approve("vapi_update")}
                  >
                    {approving === "vapi_update" ? "Preparing..." : "Approve Vapi Care-Team Update"}
                  </button>
                </div>
              </section>

              <div className={demoHighlight === "sponsor_complete" || demoHighlight === "sponsors" ? "demo-highlight" : ""}>
                <SponsorStatus statuses={statuses} approvals={approvals} ghostStatus={ghostStatus} teacherUpdate={latestTeacherUpdate} />
              </div>
            </>
          )}

          <TechnicalTrace
            result={result}
            approvals={approvals}
            events={events}
            teacherUpdates={teacherUpdates}
            demoHighlight={demoHighlight}
          />
        </div>

        <aside className="care-agent-side">
          <LiveMemory events={events} />
          <section className="care-source-list">
            <h2 className="care-section-title">Seeded open-web sources</h2>
            {DEFAULT_SOURCE_URLS.map(url => (
              <a key={url} href={url} target="_blank" rel="noreferrer">{url}</a>
            ))}
          </section>
        </aside>
      </div>
    </div>
  );
}
