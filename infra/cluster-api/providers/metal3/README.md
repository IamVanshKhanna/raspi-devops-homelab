# Metal3 Provider Configuration for Bare Metal Provisioning

## Overview
Metal3 provides bare metal host management for Cluster API.
This enables provisioning of Pi 4/5 clusters from the management cluster.

## Components
1. **BareMetalHost** - Represents physical hardware
2. **Metal3Machine** - CAPI machine backed by BareMetalHost
3. **Provisioning** - Network boot and OS installation

## Prerequisites
- Management cluster with CAPI controllers
- DHCP/TFTP/HTTP servers for network boot
- IPMI/Redfish access to Pi BMCs (or virtual BMC)
- Ironic inspector for hardware discovery

## Installation

### 1. Install Metal3 Operators
```bash
# Add Metal3 helm repo
helm repo add metal3 https://metal3-io.github.io/metal3-charts
helm repo update

# Install Metal3 controllers
helm install metal3 metal3/metal3 \
  --namespace metal3-system --create-namespace \
  --version v1.11.0

# Verify
kubectl get pods -n metal3-system
```

### 2. Configure Provisioning Network
```yaml
# Metal3 provisioning network
apiVersion: metal3.io/v1alpha1
kind: Provisioning
metadata:
  name: provisioning-configuration
spec:
  provisioningNetwork: "Managed"
  provisioningIP: "192.168.111.1/24"
  provisioningDHCPRange: "192.168.111.100,192.168.111.200"
  provisioningInterface: "eth1"
  watchAllNamespaces: true
```

## BareMetalHost Configuration

### Pi 4B Host
```yaml
apiVersion: metal3.io/v1alpha1
kind: BareMetalHost
metadata:
  name: pi4-node-0
  namespace: homelab-clusters
  labels:
    homelab.io/hardware: pi4
    homelab.io/role: worker
spec:
  online: true
  bootMACAddress: "aa:bb:cc:dd:ee:01"
  bootMode: "uefi"
  hardwareProfile: "default"
  externallyProvisioned: false
  bmc:
    address: ipmi://192.168.1.101:6230
    credentialsName: pi4-node-0-bmc-secret
    disableCertificateVerification: true
  rootDeviceHints:
    deviceName: "/dev/nvme0n1"
    minSizeGigabytes: 100
  preprovisioningNetworkDataName: "pi4-node-0-network"
---
apiVersion: v1
kind: Secret
metadata:
  name: pi4-node-0-bmc-secret
  namespace: homelab-clusters
type: Opaque
stringData:
  username: "admin"
  password: "changeme"
---
apiVersion: metal3.io/v1alpha1
kind: NetworkData
metadata:
  name: pi4-node-0-network
  namespace: homelab-clusters
spec:
  interfaces:
    - name: "eth0"
      type: "ethernet"
      macAddress: "aa:bb:cc:dd:ee:01"
      ipv4:
        address: "192.168.1.50/24"
        gateway: "192.168.1.1"
      ipv6: {}
      bond: {}
  dns:
    - "1.1.1.1"
    - "8.8.8.8"
```

### Pi 5 Host
```yaml
apiVersion: metal3.io/v1alpha1
kind: BareMetalHost
metadata:
  name: pi5-node-0
  namespace: homelab-clusters
  labels:
    homelab.io/hardware: pi5
    homelab.io/role: control-plane
spec:
  online: true
  bootMACAddress: "aa:bb:cc:dd:ee:02"
  bootMode: "uefi"
  hardwareProfile: "pi5"
  externallyProvisioned: false
  bmc:
    address: redfish-virtualmedia://192.168.1.102/redfish/v1/Systems/1
    credentialsName: pi5-node-0-bmc-secret
    disableCertificateVerification: true
  rootDeviceHints:
    deviceName: "/dev/nvme0n1"
    minSizeGigabytes: 200
  preprovisioningNetworkDataName: "pi5-node-0-network"
---
apiVersion: v1
kind: Secret
metadata:
  name: pi5-node-0-bmc-secret
  namespace: homelab-clusters
type: Opaque
stringData:
  username: "admin"
  password: "changeme"
---
apiVersion: metal3.io/v1alpha1
kind: NetworkData
metadata:
  name: pi5-node-0-network
  namespace: homelab-clusters
spec:
  interfaces:
    - name: "eth0"
      type: "ethernet"
      macAddress: "aa:bb:cc:dd:ee:02"
      ipv4:
        address: "192.168.1.51/24"
        gateway: "192.168.1.1"
      ipv6: {}
      bond: {}
  dns:
    - "1.1.1.1"
    - "8.8.8.8"
```

## Images

### Custom Pi OS Image
```yaml
apiVersion: metal3.io/v1alpha1
kind: Image
metadata:
  name: pi-os-image
  namespace: metal3-system
spec:
  url: "https://images.homelab.local/pi-os-bookworm-64-lite.qcow2"
  checksum: "sha256:abc123..."
  format: "qcow2"
  osFamily: "linux"
  operatingSystem: "raspbian"
  architecture: "arm64"
  diskFormat: "qcow2"
```