# Nexus Agent: Project Focus and Near-Term Direction

> Status: Working strategy draft
> Date: 2026-03-14

## 1. Project Positioning

Nexus Agent should no longer be described as a generic "do-everything AI OS".
Its clearer and more durable positioning is:

**A self-hosted, low-cost, governable Agent control plane for home and enterprise environments.**

This project serves two closely related scenarios:

1. **Home AI Center**
   - A private AI center for family communication, device control, memory, reminders, and automation.
   - Runs with low-cost local or hybrid models whenever possible.

2. **Enterprise Agent Control Plane**
   - A private deployment layer for connecting internal MCP servers and business systems.
   - Adds identity, permissions, audit, and controlled workflow interactions for multiple users.

These are not two unrelated products. They share the same platform foundation:

- people
- context
- memory
- permissions
- actions
- audit

---

## 2. Core Vision

The long-term vision of Nexus is:

**Let AI safely connect to real-world systems, understand context, pass information between people and systems, and take actions inside a private environment.**

In the home, this means:

- understanding family members and routines
- controlling devices with permission boundaries
- remembering things that matter in daily life
- turning natural language into reminders and automations

In enterprises, this means:

- connecting internal MCP services and tools
- enforcing account, role, and approval boundaries
- translating chat-like requests into workflow actions
- passing status, tasks, and approvals across people and systems

---

## 3. Strategic Direction

Nexus should develop as **platform foundation first, scenario validation second**.

### 3.0 Deployment Model

Nexus should assume the following default deployment model:

**one deployment per home or team, with many users accessing the same Nexus service**

This means:

- a family deploys Nexus once on a shared always-on machine
- a company or team deploys Nexus once in its private environment
- end users do not need their own server or their own desktop machine
- most users primarily interact through mobile-first channels such as messaging apps or lightweight web entry points

Nexus should therefore be designed as:

- centralized deployment
- multi-user access
- mobile-first interaction
- admin-managed governance

### 3.1 Foundation Layer

These are the long-term platform capabilities worth investing in:

- MCP and plugin integration standards
- identity and multi-user account system
- permission model for tools, domains, and risk levels
- audit and governance
- sandbox and execution isolation
- low-cost local model support
- secrets and credential scoping

### 3.2 Scenario Layer

Instead of expanding everywhere, Nexus should validate the platform through two practical scenarios:

1. **Home scenario**
   - validates usability, frequency, and real daily value
   - helps shape memory, reminders, automation, and messaging UX

2. **Enterprise scenario**
   - validates permissions, audit, MCP onboarding, and deployment value
   - creates future opportunities for paid implementation and customization

---

## 4. Near-Term Priorities

The short-term goal is not breadth. It is to make Nexus genuinely useful for the author and a small circle of real users.

### P0: Entry Experience and Access

Nexus must become easier to use for non-technical users.

Priority items:

- improve login and permission flows
- reduce Telegram setup friction
- add a more natural messaging entry point
- make account binding simple and reliable
- prioritize family-usable access over technically ideal but high-friction setup

Current intent:

- Telegram can remain a technical channel
- Web chat should be usable as a fallback
- WeChat or another easier family-facing channel should be explored as a higher-priority user entry

Binding is a core product capability, not a setup detail.
Nexus needs a clear identity binding layer that maps external messaging identities to Nexus users and then to a family or enterprise permission model.

### P0: Home AI Center Core Loop

The first strong user experience should be:

**message Nexus -> understand intent -> safely control home devices or answer home context -> record audit**

Priority items:

- integrate Home Assistant reliably
- define family-member permissions
- support common device control and status lookup
- ensure actions are logged and reviewable

### P1: Family Memory and Reminder Layer

Do not start with a heavy "knowledge base" product.
Start with a lightweight **family memory hub**.

Initial memory types:

- reminder memory
- arrival-triggered reminders
- preference memory
- household task memory

Example outcomes:

- "Remind mom next time she comes over to take the medicine."
- "When I get home, remind me the laundry is still outside."
- "Dad does not like the room temperature too low."

The goal is to turn natural family communication into structured, usable memory and automation.

### P1: Enterprise Direction Through Standards, Not Overbuilding

The enterprise path should begin with standards and real onboarding experience, not with a huge platform surface area.

Priority items:

- define how internal systems or MCP servers should integrate into Nexus
- define permission declarations
- define execution contracts
- define audit event formats
- test the product with trusted colleagues and gather real workflow needs

In the early phase, enterprise adoption may depend on hands-on integration by the project author.
That is acceptable and may become a future paid service advantage.

### P2: Explicitly Delayed

The following should not be near-term priorities:

- full community skill marketplace integration
- unrestricted third-party skill execution
- overly broad AI OS narrative
- heavy browser automation expansion
- premature platform complexity for every enterprise feature

---

## 5. Interaction Model

Nexus should default to a **mobile-first, messaging-first interaction model**.

For most users:

- messaging is the primary interface
- web is a fallback interface and admin console
- desktop-heavy workflows should not be assumed

This applies to both major scenarios:

1. **Home**
   - family members primarily use chat or voice-like entry points
   - configuration is handled by one technical owner

2. **Enterprise**
   - employees primarily interact through IM or mobile-friendly pages
   - administrators handle integration, policy, approval, and audit setup

As a result, Nexus should optimize for:

- short conversational workflows
- approvals and confirmations in chat where possible
- low-friction onboarding
- reliable identity recognition
- strong admin controls behind the scenes

---

## 6. Product Differentiation

Nexus should not try to compete with large companies on general assistant breadth.

Its differentiation should come from the combination of:

- self-hosted deployment
- low-cost local or hybrid models
- multi-user permission governance
- MCP and internal system integration
- auditability
- controllable execution
- customization for real environments

Large companies may build broad assistant platforms, but they often do not prioritize:

- deeply customizable private deployment
- long-tail internal system integration
- open governance patterns for tools and MCP
- home and enterprise unified under the same control foundation

This is the area where Nexus can remain distinctive.

---

## 7. Business and Open Source Outlook

Nexus does not need to optimize first for fundraising or scale.
It can grow from genuine usage and exploration.

The practical path is:

1. build something the author personally relies on
2. let family and trusted colleagues use it for free
3. observe real recurring needs
4. turn repeated enterprise integration pain into service and product opportunities

Potential long-term model:

- **Open source core**
  - self-hosting
  - identity
  - permissions
  - basic audit
  - MCP integration framework

- **Paid value**
  - enterprise implementation
  - custom internal system integration
  - deployment support
- advanced governance and approval flows
- hardened sandbox or policy features

---

## 8. The Next 90 Days

Nexus should focus on three concrete outcomes:

1. Build a version that the author and family can comfortably use.
2. Deliver a real home loop with device control, permissions, and memory/reminders.
3. Validate enterprise demand with a small number of trusted colleagues and real internal integration conversations.

If these three things become true, the project direction will be much clearer:

- whether family/home is the strongest daily-use driver
- whether enterprise workflow integration is the strongest paid opportunity
- which platform capabilities are truly foundational

---

## 9. One-Sentence Summary

**Nexus is a self-hosted Agent control foundation for homes and organizations, enabling AI to safely connect systems, understand context, pass information, and take actions under permission and audit controls.**
