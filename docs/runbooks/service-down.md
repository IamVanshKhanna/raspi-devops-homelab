# Runbook: Service Down

## Detection
- `make verify-v1` fails
- `make verify-health` reports container not running
- Telegram alert from health check

## Diagnosis
```bash
# Check which container is down
docker ps -a --format "table {{.Names}}\t{{.Status}}"

# Check logs
docker logs <container_name> --tail 50

# Check resource usage
docker stats --no-stream <container_name>

# Check health status
docker inspect --format '{{.State.Health.Status}}' <container_name>
```

## Common Causes & Fixes

### OOM Killed
```bash
# Check memory limit
docker inspect <container_name> | grep -i memory

# Fix: Increase mem_limit in docker-compose.yml
# Then: make up-phaseX (for appropriate phase)
```

### Port Conflict
```bash
# Check what's using the port
ss -tulpn | grep <port>

# Fix: Stop conflicting service or change port
```

### Config Error
```bash
# Validate config
docker compose -f stacks/<stack>.yml config

# Fix: Correct config, then restart
docker compose -f stacks/<stack>.yml restart <service>
```

### Dependency Not Ready
```bash
# Check depends_on health checks
docker ps --format "table {{.Names}}\t{{.Status}}"

# Fix: Wait for dependency, or restart in order
make down-phaseX && make up-phaseX
```

## Recovery Steps
1. Identify root cause from logs
2. Apply fix
3. Restart service: `docker compose -f stacks/<stack>.yml restart <service>`
4. Verify: `make verify-health`
5. If persistent: `make down-phaseX && make up-phaseX`

## Escalation
- If recurring >3 times/day: Create GitHub issue
- If data loss suspected: `make restore-test` then `make restore SNAPSHOT=latest`