# Bridge Devpost Draft

## Project Name

Bridge

## Tagline

An evidence-to-action care agent for AAC families.

## Short Description

Bridge helps parents, teachers, and caregivers turn confirmed communication moments into shared evidence, source-grounded AAC/IEP support packets, and parent-approved care-team follow-up.

## Inspiration

My mom runs a preschool and afterschool program, so I have spent a lot of time around children with different support needs. One thing I have seen is that the hard part is not always understanding a single moment. A parent or teacher may know that a child wants water, needs help, wants a comfort item, or is overwhelmed by noise.

The hard part is what happens after that moment. The context often gets lost before it can help the child get better support across home, school, and care teams.

Bridge was built around that gap: turning everyday communication moments into evidence families can actually use.

## What It Does

Bridge is a care agent for AAC families. In the demo, Maya is a six-year-old minimally verbal child who uses gestures, pointing, picture choices, and comfort items.

Bridge:

- Suggests possible intents during a Live Session.
- Lets the parent confirm the child's actual communication.
- Speaks the confirmed phrase locally as AAC.
- Streams the event into Live Agent Memory.
- Builds an Evidence Timeline of repeated communication patterns.
- Calls a teacher or caregiver through Vapi after parent approval.
- Turns the teacher call transcript into a parent-review mini-report.
- Uses TinyFish to extract facts from real SFUSD and California AAC/assistive technology sources.
- Drafts a source-grounded AAC/IEP support packet.
- Stores the audit trail in Ghost/Postgres.
- Sends structured data through Nexla Express only after parent approval.
- Can trigger a Vapi care-team voice update only after parent approval.

The product is intentionally not framed as "AI understands the child." Bridge keeps the adult in control. It suggests and organizes, but the parent confirms moments and approves every outbound action.

## How We Built It

The app has a React/Vite frontend and a FastAPI backend.

The Live Session uses browser webcam frames, MediaPipe landmarks, and OpenCV object detection for demo props like a gray water bottle and a dark hat. Those visual cues help push the suggested intent list toward phrases like "I want water" or "I want my hat."

Confirmed moments are saved as structured `IntentLog` records. Bridge then uses those logs to build pattern summaries and evidence timelines.

The Care Agent uses `AgentRun` records to track durable work:

- confirmed evidence loaded
- teacher update requested
- Vapi transcript received or replayed
- teacher mini-report generated
- TinyFish source extraction completed
- AAC/IEP packet drafted
- approvals recorded
- Nexla/Vapi follow-up results stored

The frontend includes a Presentation Autopilot mode that automatically drives the  demo while the presenter explains the story.

## Sponsor Tech Used

### Vapi

Vapi powers parent-approved voice actions:

- outbound teacher/caregiver daily update calls
- transcript/end-of-call webhook flow
- parent-approved care-team voice update

### Redis

Redis is used as Live Agent Memory: a real-time event stream for parent confirmations, teacher update progress, source extraction steps, and follow-up statuses.

### TinyFish

TinyFish handles open-web source extraction for the AAC/IEP packet. Bridge uses seeded real sources such as SFUSD special education resources, SFUSD AAC guidance, and California assistive technology references.

### Nexla Express

Nexla receives parent-approved structured care data through an Incoming Webhook flow. Bridge prepares and delivers packet metadata or teacher update reports only after approval.

### Ghost / TigerData

Ghost/Postgres stores the audit trail: children, confirmed moments, agent runs, teacher transcripts, generated reports, source facts, approvals, and sponsor statuses.

### Chainguard

Bridge includes a hardened backend container story using Chainguard-style minimal images in the infrastructure setup.

## What Makes It Agentic

Bridge does more than respond to a prompt. It runs a multi-step workflow:

1. Monitors parent-confirmed communication evidence.
2. Detects patterns across home and school routines.
3. Calls the teacher/caregiver for away-from-home context.
4. Converts transcript evidence into structured report entries.
5. Opens real web sources through TinyFish.
6. Extracts relevant AAC/IEP facts.
7. Drafts a support packet from evidence plus sources.
8. Waits for parent approval.
9. Routes approved follow-up through Nexla and Vapi.
10. Stores the audit trail in Ghost/Postgres.

## Challenges

The biggest challenge was making the demo technically real without making it fragile. Live camera inference, phone calls, web automation, webhooks, and external services can all fail in a hackathon environment.

We solved this by building a hybrid reliable mode:

- real services are called when configured
- transcript/source fallbacks are available for a reliable judge demo
- the UI labels prepared/replayed states cleanly without pretending they are live
- the parent-review and approval gates always remain visible

Another challenge was deciding how to position the product ethically. We did not want to pitch "AI reads nonverbal children." The safer and more honest framing is that Bridge supports parent-confirmed communication and turns it into useful documentation.

## Accomplishments

- Built a full-stack demo with React, FastAPI, Postgres, Redis, and multiple sponsor integrations.
- Added a teacher/caregiver Vapi call pipeline with webhook handling.
- Built a parent-facing teacher mini-report from transcript content.
- Created a source-grounded AAC/IEP packet flow.
- Added a technical trace timeline that shows payloads, records, source facts, reports, and sponsor outputs.
- Added Presentation Autopilot so the demo can run smoothly while the presenter tells the story.
- Kept parent approval as a first-class safety boundary.

## What We Learned

We learned that the most compelling agent demo is not the one with the most model magic. It is the one that makes the problem, workflow, and human control clear.

For this use case, the valuable work is not just predicting "water." It is preserving the context around that moment, combining it with school updates and real source material, and helping the family take the next step.

## What's Next

Next steps for Bridge:

- More robust vision/object detection for AAC-relevant objects and gestures.
- Better teacher/caregiver contact management.
- Real care-team destination setup through Nexla data contracts.
- More district-specific source packs.
- Parent-editable report sections before delivery.
- Stronger privacy controls and consent/audit review.
- Mobile-first caregiver flow.

## Demo Script Summary

Bridge turns daily communication into evidence and action.

In the demo, Maya confirms a communication moment. Bridge speaks it, stores it, shows the pattern in an Evidence Timeline, calls the teacher for a daily update, generates a mini-report, researches real AAC/IEP sources, drafts a support packet, and routes approved follow-up through sponsor infrastructure.

The core line:

> Parents and teachers often understand the moment. Bridge turns that moment into evidence families can actually use.

