# Homelab Makefile
# Usage: make <target>

.PHONY: help up-core up-network up-monitoring up-apps up-smarthome up-uptime up-all down-core down-network down-monitoring down-apps down-smarthome down-uptime down-all ps logs verify-v1 verify-health verify-loki verify-alertmanager verify-uptime backup restore

# Core stack dependencies
up-core:
	docker compose -f stacks/core/docker-compose.yml up -d

up-network:
	docker compose -f stacks/network/docker-compose.yml up -d

up-monitoring:
	docker compose -f stacks/monitoring/docker-compose.yml up -d

up-apps:
	docker compose -f stacks/apps/docker-compose.yml up -d

up-smarthome:
	docker compose -f stacks/smarthome/docker-compose.yml up -d

up-uptime:
	docker compose -f stacks/uptime-kuma/docker-compose.yml up -d

# Phased deploy per verification plan
up-phase1: up-core up-network
	@echo "Phase 1 done: core + network"

up-phase2: up-monitoring
	@echo "Phase 2 done: monitoring"

up-phase3: up-apps
	@echo "Phase 3 done: apps"

up-phase4: up-smarthome
	@echo "Phase 4 done: smarthome"

up-phase5: up-uptime
	@echo "Phase 5 done: uptime-kuma"

up-all: up-phase1 up-phase2 up-phase3 up-phase4 up-phase5
	@echo "All stacks deployed"

# Down commands
down-core:
	docker compose -f stacks/core/docker-compose.yml down

down-network:
	docker compose -f stacks/network/docker-compose.yml down

down-monitoring:
	docker compose -f stacks/monitoring/docker-compose.yml down

down-apps:
	docker compose -f stacks/apps/docker-compose.yml down

down-smarthome:
	docker compose -f stacks/smarthome/docker-compose.yml down

down-uptime:
	docker compose -f stacks/uptime-kuma/docker-compose.yml down

down-all: down-uptime down-smarthome down-apps down-monitoring down-network down-core

# Status & logs
ps:
	docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

logs:
	docker compose -f stacks/core/docker-compose.yml -f stacks/network/docker-compose.yml \
		-f stacks/monitoring/docker-compose.yml -f stacks/apps/docker-compose.yml \
		-f stacks/smarthome/docker-compose.yml -f stacks/uptime-kuma/docker-compose.yml \
		logs -f --tail=100

# Verification
verify-v1: verify-health verify-loki verify-alertmanager verify-uptime
	@echo "All v1.1 verification checks passed"

verify-health:
	./scripts/health-check.sh --strict

verify-loki:
	@echo "Checking Loki log pipeline..."
	@curl -sf http://localhost:3100/ready >/dev/null || (echo "Loki not ready"; exit 1)
	@LABELS=$$(curl -sf "http://localhost:3100/loki/api/v1/label" | jq -r '.data | length' 2>/dev/null || echo "0"); \
	if [ "$$LABELS" -gt 0 ]; then echo "Loki labels: $$LABELS"; else echo "No labels ingested"; exit 1; fi

verify-alertmanager:
	@echo "Checking Alertmanager..."
	@curl -sf http://localhost:9093/-/ready >/dev/null || (echo "Alertmanager not ready"; exit 1)

verify-uptime:
	@echo "Checking Uptime Kuma..."
	@curl -sf http://localhost:3001 >/dev/null || (echo "Uptime Kuma not responsive"; exit 1)

# Backup & restore
backup:
	./scripts/backup.sh

restore:
	@echo "Usage: make restore SNAPSHOT=<snapshot-id>"
	@restic -r $$RESTIC_REPOSITORY restore $$SNAPSHOT --target /mnt/restore-test

# Config validation
config:
	docker compose -f stacks/core/docker-compose.yml config >/dev/null && \
	docker compose -f stacks/network/docker-compose.yml config >/dev/null && \
	docker compose -f stacks/monitoring/docker-compose.yml config >/dev/null && \
	docker compose -f stacks/apps/docker-compose.yml config >/dev/null && \
	docker compose -f stacks/smarthome/docker-compose.yml config >/dev/null && \
	docker compose -f stacks/uptime-kuma/docker-compose.yml config >/dev/null && \
	echo "All compose files valid"

help:
	@echo "Available targets:"
	@echo "  up-core, up-network, up-monitoring, up-apps, up-smarthome, up-uptime"
	@echo "  up-phase1, up-phase2, up-phase3, up-phase4, up-phase5"
	@echo "  up-all"
	@echo "  down-core, down-network, ... down-all"
	@echo "  ps, logs"
	@echo "  verify-v1, verify-health, verify-loki, verify-alertmanager, verify-uptime"
	@echo "  backup, restore"
	@echo "  config, help"

.DEFAULT_GOAL := help