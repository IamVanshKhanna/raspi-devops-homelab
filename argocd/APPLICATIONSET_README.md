# ArgoCD ApplicationSet

This ApplicationSet automatically generates ArgoCD Applications from the `argocd/applications/` directory.

## Usage

```bash
# Deploy the ApplicationSet
kubectl apply -f argocd/applicationset-homelab.yaml -n argocd
```

## How It Works

1. **Generator**: Scans `argocd/applications/*` directory in the Git repo
2. **Template**: Creates an Application for each subdirectory
3. **Sync Policy**: Automated prune + self-heal + namespace creation
3. **Values**: Uses `helmfile/values/defaults.yaml` for all applications

## Directory Structure

```
argocd/applications/
├── traefik/
│   └── (kustomize/helm files)
├── portainer/
├── infisical/
├── authelia/
├── monitoring/
├── loki/
├── tempo/
├── crowdsec/
├── apps/
│   ├── nextcloud/
│   ├── vaultwarden/
├── smarthome/
├── uptime-kuma/
├── ollama-cluster/
├── longhorn/
├── cert-manager/
├── external-dns/
├── postgres-operator/
├── redis-operator/
└── authelia-db/
```

## Adding New Applications

1. Create a new directory under `argocd/applications/`
2. Add Kustomize/Helm files
2. Commit and push - ApplicationSet will auto-generate the Application