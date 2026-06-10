# Runbook: Certificate Rotation & Expiry

## Detection
- Prometheus alert: `CertificateExpiringSoon` (< 30 days)
- Prometheus alert: `CertificateExpiringCritical` (< 7 days)
- Prometheus alert: `CertificateNotReady` (Ready condition != True)
- Manual check: `kubectl get certificates -A`

## Diagnosis
```bash
# List all certificates with expiry
kubectl get certificates -A -o custom-columns="NS:.metadata.namespace,NAME:.metadata.name,READY:.status.conditions[?(@.type==\"Ready\")].status,EXPIRY:.status.notAfter,ISSUER:.spec.issuerRef.name"

# Check specific certificate details
kubectl describe certificate <name> -n <namespace>

# Check CertificateRequest status
kubectl get certificaterequest -n <namespace>

# Check Issuer/ClusterIssuer status
kubectl get clusterissuer,issuer -A

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager --tail 100
```

## Common Causes & Fixes

### 1. Issuer Not Configured / ACME Challenge Failing
```bash
# Check Issuer status
kubectl describe clusterissuer letsencrypt-prod

# Check ACME challenge
kubectl get challenge -A

# Common: DNS-01 challenge failing (Cloudflare API)
# Check Cloudflare DNS records exist
kubectl logs -n cert-manager -l app=cert-manager | grep -i challenge
```

### 2. Certificate Stuck in Pending
```bash
# Force renewal via Ansible
cd /home/vansh/homelab-prod
ansible-playbook ansible/playbooks/update-certificates.yml -e "namespace=<ns> cert_name=<name>"

# Or manually trigger
kubectl annotate certificate <name> -n <namespace> cert-manager.io/force-renewal=$(date -u +%Y-%m-%dT%H:%M:%SZ) --overwrite
kubectl delete certificaterequest -l cert-manager.io/certificate-name=<name> -n <namespace>
```

### 3. DNS Propagation Delay
```bash
# Check DNS record
dig TXT _acme-challenge.<domain> +short

# Wait for propagation (up to 5 min for Cloudflare)
# Then re-check certificate
kubectl wait --for=condition=Ready certificate/<name> -n <namespace> --timeout=10m
```

### 4. Rate Limited by Let's Encrypt
```bash
# Check for rate limit errors in logs
kubectl logs -n cert-manager -l app=cert-manager | grep -i "rate limit"

# Solution: Wait (1h-1w), use staging issuer for testing, or request rate limit increase
```

### 5. Private Key Rotation (Security)
```bash
# Rotate private key by deleting secret (cert-manager regenerates)
kubectl delete secret <cert-name>-tls -n <namespace>
# cert-manager will create new private key and request new certificate
```

## Recovery Steps
1. Identify expiring/failed certificate via alerts or `kubectl get certificates -A`
2. Check Issuer/ClusterIssuer status
3. If ACME challenge failing: verify DNS, check Cloudflare API token
4. Force renewal via Ansible playbook or manual annotation
5. Verify: `kubectl get certificate <name> -n <ns> -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'` → "True"
6. Restart dependent ingress controllers: `kubectl rollout restart deployment/traefik -n traefik`

## Prevention
- Automated renewal: cert-manager handles 30 days before expiry
- Monitoring: Prometheus alerts at 30d (warning) and 7d (critical)
- Testing: Monthly `ansible-playbook ansible/playbooks/update-certificates.yml` dry-run
- Staging issuer: Use Let's Encrypt staging for non-prod testing

## Escalation
- Critical expiry (< 24h): Manual DNS challenge + force renewal
- Persistent failures: Check cert-manager GitHub issues, upgrade version
- Rate limited: Switch to backup CA (ZeroSSL, Buypass) or request limit increase

## Related
- Ansible playbook: `ansible/playbooks/update-certificates.yml`
- Cert-manager namespace: `cert-manager`
- ClusterIssuer: `letsencrypt-prod` (Cloudflare DNS-01)
- Dashboard: Grafana → Cert Manager → Certificate Expiry