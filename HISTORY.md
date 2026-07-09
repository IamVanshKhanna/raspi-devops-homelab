# Homelab Evolution — how this repo got here

This repo (`raspi-devops-homelab`) is the **current, live-tested** 24/7 homelab on a
Raspberry Pi 4B 4GB. It absorbed three earlier iterations, preserved here in `archive/`
with their full git history so the progression is verifiable — not just claimed.

## Version timeline

| Version | Repo (archived) | What it added | Why it moved on |
|---------|-----------------|---------------|-----------------|
| v0 | `pi4b-homelab` | Baseline 24/7 Pi stack: Traefik, Nextcloud, Vaultwarden, HA, Pi-hole, WireGuard, Ollama, Prometheus/Grafana on 2TB SSD | Duplicate of this repo's structure; no unique IP beyond 3 CI workflows |
| v1 | `pi4homelab` | **Security + observability leap**: Authelia, CrowdSec, Alertmanager, Loki, Tempo, OTel, Prometheus rules; 6 ADRs (orchestration, network-access, memory, secrets, hermes-skills, threat-model); ENDPOINTS/SECRET_ROTATION/PERFORMANCE docs | Most mature single-node design, but not the one deployed 24/7 |
| v2 | `homelab-prod` | **Production SRE leap**: 14 GitHub Actions (DR failover, incident drill, secrets-rotation, supply-chain scan, cost-allocation, rightsizing, unused-resource detection, Trivy) | CI/ops maturity, but untested against the live box |
| **current** | `raspi-devops-homelab` (this repo) | The deployed, running config — 26-27 containers, live-tested | Chosen as canonical because it is what actually runs |

## What's intentional

- The **live tree** (`stacks/`, `config/`, `docs/`, `scripts/`) is ONLY this repo's verified
  config. No config, ADR, or CI file from the archived versions was copied into the running
  stack — they're kept in `archive/` as reference so the homelab stays deployable.
- To promote a draft's idea (e.g. CrowdSec, an ADR, a DR workflow) into the live homelab,
  cherry-pick it into the tree and test on the Pi first. See `archive/<version>/docs/ADR-*.md`
  for the decision records behind earlier choices.

## Archived repos (GitHub, read-only)

- `pi4b-homelab` · `pi4homelab` · `homelab-prod` — archived 2026-07-10 after this consolidation.
- `homelab-options-lab` — separate tool-comparison repo, archived (distinct purpose).
- `homelab-ops-mesh` — multi-node (Pi + Windows + Tailscale) variant, kept **active** as a
  distinct repo (different scope, not a draft of this one).
