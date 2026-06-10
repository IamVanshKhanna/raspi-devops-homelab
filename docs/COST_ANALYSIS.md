# Cost Analysis — homelab-prod

> Cost breakdown for running homelab-prod on Raspberry Pi hardware

---

## Hardware Costs (One-time)

| Component | Specification | Cost (USD) | Notes |
|-----------|---------------|------------|-------|
| **Raspberry Pi 4B (8GB)** | 8GB RAM | $120 | 2 units for HA |
| **Raspberry Pi 5 (8GB)** | 8GB RAM | $140 | Alternative for v1.7+ |
| **DeskPi 3B Pro Case** | Aluminum, fan, SATA bay | $60 | Includes fan controller |
| **2TB SATA SSD** | Samsung 870 EVO | $130 | 2x for RAID-1 or separate |
| **USB 3.0 to SATA Adapter** | For SSD connection | $15 | If not using DeskPi |
| **USB-C Power Supply** | Official 5V/3A | $12 | 2x |
| **MicroSD Card (backup)** | 32GB Class 10 | $8 | Emergency boot |
| **Ethernet Cable** | Cat6, 1m | $5 | 2x |
| **Network Switch** | 5-port Gigabit | $20 | If not using router ports |

**Total Hardware (2-node cluster)**: ~$570-600 USD

---

## Recurring Costs (Monthly/Annual)

| Service | Cost (USD/year) | Purpose |
|---------|-----------------|---------|
| **Domain** | $12 | DuckDNS free, or custom domain |
| **Backblaze B2** | $6-12 | 1TB backup storage |
| **Cloudflare** | Free | DNS, DNS-01 challenge, CDN |
| **Tailscale** | Free (personal) | VPN mesh, MagicDNS |
| **Electricity** | ~$15-25 | 7W × 2 nodes × 24/7 @ $0.12/kWh |
| **Domain SSL (backup)** | $0 | Let's Encrypt free |

**Total Annual Recurring**: ~$35-50 USD

---

## Cost Comparison: Self-Hosted vs Cloud

| Service | Self-Hosted (Annual) | Cloud Equivalent | Savings |
|---------|---------------------|------------------|---------|
| **File Storage (2TB)** | $6 (power) | Google One 2TB: $100 | $94 |
| **Password Manager** | $0 | 1Password Family: $60 | $60 |
| **Monitoring** | $0 | Datadog: $3600+ | $3600 |
| **VPN** | $0 | Tailscale Teams: $60 | $60 |
| **Backup** | $12 | Backblaze Personal: $70 | $58 |
| **AI/LLM** | $0 (local) | OpenAI API: $500+ | $500+ |
| **Smart Home** | $0 | Hubitat/HA Cloud: $30 | $30 |

**Total Annual Savings vs Cloud**: **~$4,300+**

---

## ROI Analysis

| Metric | Value |
|--------|-------|
| **Initial Investment** | $600 |
| **Annual Operating Cost** | $50 |
| **Cloud Equivalent Annual Cost** | $4,350 |
| **Annual Savings** | $4,300 |
| **Payback Period** | **~1.5 months** |
| **5-Year TCO (Self-Hosted)** | $850 |
| **5-Year TCO (Cloud)** | $21,750 |
| **5-Year Savings** | **$20,900** |

---

## Resource Utilization (v1.7, 2-node cluster)

### Node 1 (Control Plane + Worker)
| Resource | Allocated | Used | % |
|----------|-----------|------|---|
| **CPU** | 4 cores | 1.2 cores | 30% |
| **RAM** | 8 GB | 5.2 GB | 65% |
| **Storage (SSD)** | 2 TB | 450 GB | 22% |
| **Network** | 1 Gbps | 50 Mbps | 5% |

### Node 2 (Worker)
| Resource | Allocated | Used | % |
|----------|-----------|------|---|
| **CPU** | 4 cores | 0.8 cores | 20% |
| **RAM** | 8 GB | 3.1 GB | 39% |
| **Storage (SSD)** | 2 TB | 380 GB | 19% |
| **Network** | 1 Gbps | 30 Mbps | 3% |

### Cluster Totals
| Resource | Total | Used | % |
|----------|-------|------|---|
| **CPU** | 8 cores | 2.0 cores | 25% |
| **RAM** | 16 GB | 8.3 GB | 52% |
| **Storage** | 4 TB | 830 GB | 21% |

---

## Power Consumption

| Component | Power (W) | Daily kWh | Monthly kWh | Cost/mo (@$0.12/kWh) |
|-----------|-----------|-----------|-------------|---------------------|
| Pi 4B (idle) | 3.5W | 0.084 | 2.52 | $0.30 |
| Pi 4B (load) | 6.5W | 0.156 | 4.68 | $0.56 |
| SSD (2x) | 4W | 0.096 | 2.88 | $0.35 |
| Switch | 5W | 0.12 | 3.6 | $0.43 |
| **Total (2 nodes)** | **~23W** | **0.552** | **16.56** | **~$2.00** |

**Annual Electricity Cost**: ~$24 USD

---

## Storage Efficiency

| Data Type | Size | Deduplication | Compressed | Saved |
|-----------|------|---------------|------------|-------|
| **Nextcloud Files** | 120 GB | 40% (dedup) | 60% | 48 GB |
| **Vaultwarden DB** | 50 MB | 10% | 30% | 15 MB |
| **Home Assistant** | 2 GB | 5% | 40% | 800 MB |
| **Grafana/Loki** | 15 GB | 30% | 50% | 7.5 GB |
| **Ollama Models** | 25 GB | 0% | 0% | 0 GB |
| **Backups (Restic)** | 200 GB | 60% (dedup) | 40% | 80 GB |

**Total Raw**: 355 GB → **After Optimization**: 198 GB (44% reduction)

---

## Maintenance Cost (Time)

| Task | Frequency | Time | Annual Hours |
|------|-----------|------|--------------|
| OS Updates | Monthly | 30 min | 6 hrs |
| Container Updates | Weekly | 15 min | 13 hrs |
| Backup Verification | Weekly | 10 min | 8.7 hrs |
| Security Scans | Daily | Auto | 0 hrs |
| Log Review | Weekly | 15 min | 13 hrs |
| Certificate Renewal | 60 days | Auto | 0 hrs |
| Hardware Check | Quarterly | 30 min | 2 hrs |
| **Total Annual** | | | **~42.7 hours** |

---

## Cost Optimization Opportunities

| Optimization | Effort | Annual Savings |
|--------------|--------|----------------|
| **Spot/Preemptible nodes** (cloud burst) | Medium | $200+ |
| **ARM64 native images** (smaller) | Low | 20% storage |
| **Aggressive log rotation** | Low | 10% storage |
| **ARM64 native binaries** | None | Faster builds |
| **Spot instance burst** (cloud) | High | Variable |
| **Solar power** (pi) | High | $24/year |

---

## 5-Year Projection

| Year | Hardware | Operating | Total | Cumulative |
|------|----------|-----------|-------|------------|
| Year 1 | $600 | $50 | $650 | $650 |
| Year 2 | $0 | $50 | $50 | $700 |
| Year 3 | $100 (SSD replace) | $50 | $150 | $850 |
| Year 4 | $0 | $50 | $50 | $900 |
| Year 5 | $150 (Pi upgrade) | $50 | $200 | $1,100 |

**5-Year TCO: $1,100** vs Cloud Equivalent: **$21,750**

**Net Value Created: $20,650 over 5 years**

---

*Last Updated: 2026-06-09 | homelab-prod v1.7*