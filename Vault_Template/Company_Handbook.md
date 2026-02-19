# Company Handbook

## Business Context

This vault serves as the operational hub for an AI agent assistant. The agent processes tasks, manages workflows, and executes approved actions on behalf of the business.

---

## Vault Structure

| Folder | Purpose |
|--------|---------|
| `Needs_Action` | Incoming raw tasks and triggers that require processing |
| `In_Progress` | Tasks the agent is currently working on |
| `Approved` | Human-vetted actions awaiting execution |
| `Done` | Completed and archived tasks |
| `Logs` | Daily activity logs and audit trail |

---

## Rules of Engagement

### 1. Task Processing

- **New tasks** arrive in `Needs_Action` folder
- Agent reviews and moves tasks to `In_Progress` when work begins
- Tasks requiring human approval move to `Approved` folder
- Completed tasks are archived to `Done` folder

### 2. Approval Requirements

The following actions **MUST** receive human approval before execution:

- [ ] Financial transactions (payments, transfers, refunds)
- [ ] External communications (emails, messages to clients)
- [ ] Data modifications (database changes, file deletions)
- [ ] Account changes (permissions, access levels)
- [ ] Contractual commitments (agreements, subscriptions)

### 3. Autonomy Levels

| Level | Description | Examples |
|-------|-------------|----------|
| **Full Autonomy** | Agent can execute without approval | Reading data, generating reports, organizing files |
| **Notify** | Execute and inform human | Status updates, routine backups |
| **Approval Required** | Must wait for human sign-off | Payments, external emails, deletions |
| **Human Only** | Agent cannot perform | Legal decisions, hiring, terminations |

### 4. Communication Standards

- Log all significant actions in `Logs` folder
- Use clear, concise language in task notes
- Include timestamps on all updates
- Reference related tasks using `[[wikilinks]]`

### 5. Error Handling

1. If uncertain, **ask** rather than assume
2. Document errors in the task file
3. Move problematic tasks back to `Needs_Action` with notes
4. Never delete task files - archive to `Done` with status

### 6. Priority Framework

| Priority | Response Time | Indicator |
|----------|---------------|-----------|
| Critical | Immediate | `#priority/critical` |
| High | Within 1 hour | `#priority/high` |
| Medium | Within 24 hours | `#priority/medium` |
| Low | As capacity allows | `#priority/low` |

---

## Task File Template

When creating task files, use this structure:

```markdown
# Task Title

## Metadata
- **Created:** YYYY-MM-DD
- **Priority:** #priority/medium
- **Status:** pending | in-progress | approved | done
- **Assigned:** agent | human

## Description
[What needs to be done]

## Context
[Background information]

## Actions Required
- [ ] Step 1
- [ ] Step 2

## Notes
[Updates and progress notes with timestamps]

## Outcome
[Final result and any follow-up needed]
```

---

## Log Entry Template

Daily logs should follow this format:

```markdown
# Log: YYYY-MM-DD

## Summary
[Brief overview of the day's activities]

## Tasks Processed
- [Task 1] - Status
- [Task 2] - Status

## Decisions Made
- [Decision and rationale]

## Issues Encountered
- [Issue and resolution]

## Tomorrow's Focus
- [Planned priorities]
```

---

## Security Guidelines

1. Never store sensitive credentials in task files
2. Redact personal information in logs
3. Use secure channels for sensitive communications
4. Report any security concerns immediately

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-27 | 1.0 | Initial handbook created |

---

*This handbook is a living document. Update as processes evolve.*
