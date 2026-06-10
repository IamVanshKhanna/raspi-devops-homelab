# Architecture Decision Records (ADR) Index

> **Maintained:** Per release
> **Format:** Markdown, numbered sequentially
> **Template:** [ADR Template](https://github.com/joelparkerhenderson/architecture-decision-record)

---

## ADR Catalog

| ID | Title | Status | Date | Supersedes | Related |
|----|-------|--------|------|------------|---------|
| [ADR-001](ADR-001-orchestration.md) | Orchestration Platform Selection | **Accepted** | 2026-06-09 | — | ADR-008 |
| [ADR-002](ADR-002-network-access.md) | Network Access & Zero Trust | **Accepted** | 2026-06-09 | — | ADR-006 |
| [ADR-003](ADR-003-memory.md) | Memory Management & ZRAM | **Accepted** | 2026-06-09 | — | — |
| [ADR-004](ADR-004-secrets.md) | Secrets Management Strategy | **Accepted** | 2026-06-09 | — | ADR-006 |
| [ADR-005](ADR-005-hermes-skills.md) | Hermes Agent Skills Architecture | **Accepted** | 2026-06-09 | — | — |
| [ADR-006](ADR-006-threat-model.md) | Threat Model & Security Posture | **Accepted** | 2026-06-09 | — | ADR-002, ADR-004 |
| [ADR-007](ADR-007-gpu-scheduling.md) | GPU Scheduling for AI/ML Workloads | **Proposed** | 2026-06-10 | — | ADR-001, ADR-008 |
| [ADR-008](ADR-008-v2-migration.md) | v2.0 Breaking Migration: Docker Compose → K3s | **Accepted** | 2026-06-09 | ADR-001 | — |

---

## By Version

### v1.x (Baseline)
- ADR-001: Orchestration Platform Selection
- ADR-002: Network Access & Zero Trust
- ADR-003: Memory Management & ZRAM
- ADR-004: Secrets Management Strategy
- ADR-005: Hermes Agent Skills Architecture
- ADR-006: Threat Model & Security Posture

### v2.0 (Breaking Migration)
- ADR-008: v2.0 Breaking Migration — Docker Compose to K3s

### v3.0 (Planned - AI/ML Platform)
- ADR-007: GPU Scheduling for AI/ML Workloads *(proposed)*

---

## ADR Lifecycle

| Status | Meaning |
|--------|---------|
| **Proposed** | Under discussion, not yet implemented |
| **Accepted** | Approved, implemented or ready to implement |
| **Superseded** | Replaced by newer ADR (see "Supersedes" column) |
| **Deprecated** | No longer relevant, kept for history |

---

## Creating New ADRs

```bash
# 1. Copy template
cp docs/ADR-TEMPLATE.md docs/ADR-XXX-your-title.md

# 2. Fill in:
# - ID: Next sequential number
# - Title: Clear, specific
# - Status: Proposed
# - Context: Problem statement
# - Decision: What was decided
# - Consequences: Trade-offs, risks
# - Related: Link to other ADRs

# 3. Submit PR for review
# 4. On merge: Update this index
```

---

## Template Reference

```markdown
# ADR-XXX: Title

## Status
Proposed / Accepted / Superseded / Deprecated

## Context
What is the problem? What forces are at play?

## Decision
What was decided? Be specific.

## Consequences
### Positive
- Benefit 1
- Benefit 2

### Negative
- Trade-off 1
- Risk 1

### Neutral
- Observation 1

## Related ADRs
- ADR-XXX: Title
```

---

## Governance

- **Owner:** Platform team
- **Review:** Required for Accepted status
- **Merge:** 1 approval minimum
- **Retention:** Never delete - Supersede instead