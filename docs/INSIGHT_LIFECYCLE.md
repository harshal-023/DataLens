# Insight Lifecycle & Collaborative Assessment

## Overview
Phase 6D treats AI business insights as active operational entities that progress through a managed collaborative workflow.

## Insight Lifecycle States

```
┌───────┐      ┌──────────┐      ┌──────────────┐
│  NEW  ├─────►│ REVIEWED ├─────►│ ACKNOWLEDGED │
└───┬───┘      └────┬─────┘      └──────┬───────┘
    │               │                   │
    ▼               ▼                   ▼
┌───────────┐  ┌─────────────┐   ┌────────────┐
│ DISMISSED │  │INVESTIGATING│──►│  RESOLVED  │
└───────────┘  └─────────────┘   └────────────┘
```

| Status | Description | Permitted Next States |
|---|---|---|
| `NEW` | Autonomous insight detected by sweep engine. | `REVIEWED`, `ACKNOWLEDGED`, `DISMISSED` |
| `REVIEWED` | Examined by an analyst or business user. | `ACKNOWLEDGED`, `INVESTIGATING`, `DISMISSED` |
| `ACKNOWLEDGED` | Confirmed by management as a valid finding. | `INVESTIGATING`, `RESOLVED`, `DISMISSED` |
| `INVESTIGATING` | Assigned to a team member with active inquiry. | `RESOLVED`, `DISMISSED` |
| `RESOLVED` | Operational corrective action taken or completed. | Reopen to `INVESTIGATING` |
| `DISMISSED` | Deemed not actionable or expected behavior. | Reopen to `NEW` |

## Assignments & Discussion Threads
- **Assignments (`insight_assignments`)**: Insights can be assigned to workspace users with due dates and role designations (`LEAD`, `REVIEWER`, `STAKEHOLDER`).
- **Comments (`insight_comments`)**: Multi-user threaded discussions supporting notes, hypothesis testing, and operational follow-ups.
- **Audit Assessments (`insight_assessments`)**: Immutable record capturing who reviewed the insight, the status transition, user feedback rating, and justification notes.

