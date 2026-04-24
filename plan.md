# Bridge Care Agent Builder Plan

## Current Goal

Build Bridge as a 3-minute hackathon demo for an autonomous care agent:

> Bridge turns one parent-confirmed AAC communication moment into evidence, a source-grounded AAC/IEP support packet, and parent-approved care-team follow-up.

The demo should not claim the model magically understands a child. The parent confirms the moment. Bridge turns that confirmed moment into documentation and action.

## Demo Flow

1. Load the Maya demo profile.
2. Open Live Session.
3. Confirm `I want water`.
4. Bridge speaks the phrase locally with browser speech synthesis.
5. Live Agent Memory records the confirmed event.
6. Open Evidence Timeline.
7. Show the pattern: 6 confirmed moments, 4 water requests, 2 help requests, common context mealtime.
8. Open Care Agent.
9. Draft an AAC/IEP support packet.
10. Show source cards extracted from seeded school/AAC URLs.
11. Show the parent-review packet.
12. Parent approves Nexla sync.
13. Parent approves Vapi care-team voice update.
14. Show audit/sponsor statuses.

## Sponsor-Accurate Roles

| Sponsor | Real role in Bridge |
|---|---|
| TinyFish | Open-web source extraction from seeded AAC/IEP URLs through `POST https://agent.tinyfish.ai/v1/automation/run` with `X-API-Key` |
| Redis | Live Agent Memory event stream for confirmations and agent stages |
| Nexla Express | Parent-approved packet delivery through an Incoming Webhook source, source Nexset generation, optional transforms/data contracts, and delivery to target |
| Vapi | Parent-approved care-team voice update, not child AAC speech |
| Ghost/TigerData | Managed Postgres story through `DATABASE_URL`; stores agent audit records |
| Chainguard | Secure/minimal backend container deploy story |
| OpenRouter | Existing OpenAI-compatible LLM provider for intent, symbols, journals, and Q&A |

Out of scope for this sprint: WunderGraph, Akash, Guild, InsForge, AWS-specific deployment.

## Product Shape

Primary nav:

- Live Session
- Voice Board
- Care Agent
- Evidence Timeline

Main labels:

- `Suggested Intent`, not AI detection
- `Parent-Confirmed Moment`, not prediction
- `Live Agent Memory`, not cache
- `Care Agent`, not Resources
- `Evidence Timeline`, not History
- `Approve Vapi Care-Team Update`, not child TTS
- `Draft AAC/IEP Support Packet`, not submit IEP

## Implemented Foundation

- Default page is Live Session.
- Maya demo seed creates/updates a deterministic profile.
- Maya demo seed creates exactly six confirmed events.
- Live Session can confirm a demo-safe event without camera inference.
- Browser speech remains the local child AAC voice.
- Redis event helper publishes events and falls back to an in-process buffer if Redis is unavailable.
- Evidence Timeline summarizes the seeded pattern and links into the Care Agent.
- Care Agent runs one primary task: draft an AAC/IEP support packet.
- TinyFish integration uses the documented automation endpoint and honest demo-mode source facts when credentials fail or are missing.
- `AgentRun` audit records store sources, extracted facts, draft, pattern summary, approvals, sponsor statuses, and timestamps.
- Nexla Express and Vapi follow-up run only through explicit approval.
- Ghost is represented by normal Postgres/Ghost usage through `DATABASE_URL`.
- Alembic migration `003_agent_runs.py` adds the audit table.

## Backend API

### Demo seed

`POST /sessions/seed-maya-demo`

Creates or updates:

- Maya, age 6
- Minimally verbal
- Uses gestures, pointing, and picture choices
- Goal: AAC support across school/home routines

Seeds:

- Monday 6:18 PM, mealtime, water
- Tuesday 6:42 PM, mealtime, water
- Wednesday 7:05 PM, homework, help
- Thursday 6:31 PM, mealtime, water
- Friday 5:58 PM, transition, help
- Today 6:22 PM, mealtime, water

### Demo-safe confirmation

`POST /actions/demo-confirm-intent`

Creates a real confirmed `IntentLog` when no camera inference log exists. This keeps the judge demo independent from camera/model randomness.

### Care Agent run

`POST /actions/iep-agent-run`

Input:

- `child_id`
- `school_district`
- `grade`
- `disability`
- optional `source_urls`

Output:

- `agent_run_id`
- `status`
- `agent_steps`
- `sources`
- `extracted_facts`
- `draft`
- `pattern_summary`
- `parent_control_notice`
- `sponsor_statuses`

### Parent-approved follow-up

`POST /actions/approve-care-followup`

Supported `followup_type` values:

- `nexla_sync`
- `vapi_update`

No outbound care-team action runs before this approval endpoint is called. For Nexla, `nexla_sync` means Bridge posts the structured packet to `NEXLA_INCOMING_WEBHOOK_URL` if configured, or returns the prepared Nexla Express payload if no webhook has been configured yet.

## Nexla Express Setup

Use the Nexla web UI path the sponsor exposes:

1. Open **Integrate**.
2. Choose **Sources**.
3. Select **Incoming Webhook**.
4. Create a source for Bridge care packets.
5. Let Nexla generate the automatic source Nexset.
6. Optionally add transforms and a data contract.
7. Configure the target/destination.
8. Copy the generated webhook URL into `.env`:

```env
NEXLA_INCOMING_WEBHOOK_URL=https://...
```

The MCP endpoint can still be used from an MCP-capable client for agent-driven flow inspection:

```env
NEXLA_EXPRESS_MCP_URL=https://veda-ai.nexla.io/mcp-express/
NEXLA_AUTH_HEADER=Basic <service-key>
```

But the app's live demo path should use the Incoming Webhook source because that is visible in the Nexla UI and does not require guessing a private REST API.

### Event replay

`GET /actions/agent-events/{child_id}`

Returns recent Live Agent Memory events from Redis or local fallback memory.

## Source URLs

Seeded Care Agent sources:

- `https://www.sfusd.edu/sped`
- `https://www.sfusd.edu/employees/teaching/special-education-services-employee-resources/special-education-assistive-technology-accessibility-resources`
- `https://www.cde.ca.gov/sp/se/sr/atexmpl.asp`

## Demo Script

Opening:

> This is Maya. She is six and minimally verbal. Her parent often understands individual moments, but schools and care teams need documentation. Bridge turns parent-confirmed communication into evidence and care action.

Live Session:

> Bridge suggests possible intents. The parent stays in control and confirms the moment.

Evidence Timeline:

> After a few confirmed moments, Bridge shows patterns. This is where daily caregiving becomes structured evidence.

Care Agent:

> The Care Agent uses TinyFish to research real AAC and IEP sources on the open web, extracts source-grounded facts, and drafts a parent-review packet.

Approval:

> Bridge never submits or contacts anyone automatically. After approval, Nexla syncs the structured packet and Vapi prepares the care-team voice update.

Close:

> Bridge turns communication moments into evidence families can actually use.

## Test Plan

- `npm run build` from repo root passes.
- `python -m compileall apps/backend/app` passes.
- Backend smoke test:
  - `GET /health`
  - `POST /sessions/seed-maya-demo`
  - `POST /actions/demo-confirm-intent`
  - `POST /actions/iep-agent-run`
  - `POST /actions/approve-care-followup` with `nexla_sync`
  - `POST /actions/approve-care-followup` with `vapi_update`
  - `GET /actions/agent-events/{child_id}`
- Manual browser test:
  - Load Maya demo.
  - Confirm `I want water` from Live Session without relying on camera inference.
  - Verify Live Agent Memory updates.
  - Open Evidence Timeline and confirm the cards match the demo pattern.
  - Open Care Agent and draft the packet.
  - Verify source cards, packet, approval buttons, and sponsor statuses render.

## Demo Safety Rules

- Parent confirms every communication moment.
- Parent approves every outbound follow-up.
- Bridge does not diagnose.
- Bridge does not replace therapists or IEP teams.
- Bridge does not auto-submit IEP or insurance forms.
- Browser speech is the child-facing AAC voice.
- Vapi is for care-team voice updates only.
