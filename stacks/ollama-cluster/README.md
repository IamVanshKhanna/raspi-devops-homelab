# STACK: OLLAMA-CLUSTER — Distributed Ollama LLM Inference
# Multi-node Ollama cluster for scaled LLM inference
# Uses K3s + shared storage (Longhorn) + load balancing

version: "3.8"

# This docker-compose is for REFERENCE - actual deployment via K3s/Helm
# For single-node v1.x, use stacks/apps/docker-compose.yml ollama service

# K3s Deployment for Ollama Cluster:
#
# apiVersion: apps/v1
# kind: Deployment
# metadata:
#   name: ollama
#   namespace: ai
#   labels:
#     app: ollama
# spec:
#   replicas: 3  # Scale based on nodes
#   selector:
#     matchLabels:
#       app: ollama
#   template:
#     metadata:
#       labels:
#         app: ollama
#     spec:
#       affinity:
#         podAntiAffinity:
#           preferredDuringSchedulingIgnoredDuringExecution:
#           - weight: 100
#             podAffinityTerm:
#               labelSelector:
#                 matchExpressions:
#                 - key: app
#                   operator: In
#                   values: [ollama]
#               topologyKey: kubernetes.io/hostname
#       containers:
#       - name: ollama
#         image: ollama/ollama:0.3.14
#         ports:
#         - containerPort: 11434
#         volumeMounts:
#         - name: ollama-models
#           mountPath: /root/.ollama
#         resources:
#           requests:
#             memory: "2Gi"
#             cpu: "1000m"
#             nvidia.com/gpu: 1  # If GPU available
#           limits:
#             memory: "4Gi"
#             cpu: "2000m"
#             nvidia.com/gpu: 1
#         env:
#         - name: OLLAMA_NUM_PARALLEL
#           value: "2"
#         - name: OLLAMA_MAX_LOADED_MODELS
#           value: "3"
#         - name: OLLAMA_FLASH_ATTENTION
#           value: "1"
#       volumes:
#       - name: ollama-models
#         persistentVolumeClaim:
#           claimName: ollama-models-pvc
#
# ---
# apiVersion: v1
# kind: Service
# metadata:
#   name: ollama
#   namespace: ai
# spec:
#   type: ClusterIP
#   ports:
#   - port: 11434
#     targetPort: 11434
#   selector:
#     app: ollama
#
# ---
# apiVersion: v1
# kind: PersistentVolumeClaim
# metadata:
#   name: ollama-models-pvc
#   namespace: ai
# spec:
#   accessModes:
#   - ReadWriteMany
#   storageClassName: longhorn
#   resources:
#     requests:
#       storage: 50Gi

# Load Balancer Service (for external access via Traefik):
#
# apiVersion: networking.k8s.io/v1
# kind: Ingress
# metadata:
#   name: ollama-ingress
#   namespace: ai
#   annotations:
#     traefik.ingress.kubernetes.io/router.entrypoints: websecure
#     traefik.ingress.kubernetes.io/router.tls: "true"
#     traefik.ingress.kubernetes.io/router.middlewares: authelia-forwardauth@kubernetescrd
# spec:
#   rules:
#   - host: ollama.homelab.local
#     http:
#       paths:
#       - path: /
#         pathType: Prefix
#         backend:
#           service:
#             name: ollama
#             port:
#               number: 11434
#   tls:
#   - hosts:
#     - ollama.homelab.local
#     secretName: ollama-tls

# GPU Offload Configuration (for Pi 5 with GPU or Jetson):
#
# For Pi 5 with VideoCore VI GPU:
# - Install: vulkan-tools vulkan-validationlayers libvulkan-dev
# - Ollama will auto-detect via llama.cpp Vulkan backend
# - For CUDA (Jetson/NVIDIA): nvidia-container-toolkit required
#
# GPU Resource Configuration:
# resources:
#   limits:
#     nvidia.com/gpu: 1
#     memory: "4Gi"
#   requests:
#     nvidia.com/gpu: 1
#     memory: "2Gi"
#
# Node Labels for GPU Scheduling:
# kubectl label node node-1 accelerator=nvidia-gpu
# kubectl label node node-2 accelerator=videocore-gpu

# Ollama Model Distribution:
# Models stored on Longhorn PVC (ReadWriteMany) so all pods share
# First pod pulls model -> stored on Longhorn -> all other pods can access
# Use initContainer to pre-pull models:
#
# initContainers:
# - name: model-puller
#   image: ollama/ollama:0.3.14
#   command: ["ollama", "pull"]
#   args: ["gemma:2b", "llama3:8b", "codellama:7b"]
#   volumeMounts:
#   - name: ollama-models
#     mountPath: /root/.ollama

# Load Balancing Strategy:
# - Kubernetes Service (ClusterIP) provides round-robin
# - For sticky sessions (long generations): use sessionAffinity: ClientIP
# - For better distribution: use headless service + client-side load balancing

# Auto-scaling (HPA):
#
# apiVersion: autoscaling/v2
# kind: HorizontalPodAutoscaler
# metadata:
#   name: ollama-hpa
#   namespace: ai
# spec:
#   scaleTargetRef:
#     apiVersion: apps/v1
#     kind: Deployment
#     name: ollama
#   minReplicas: 2
#   maxReplicas: 6
#   metrics:
#   - type: Resource
#     resource:
#       name: cpu
#       target:
#         type: Utilization
#         averageUtilization: 70
#   - type: Resource
#     resource:
#       name: memory
#       target:
#         type: Utilization
#         averageUtilization: 80
#   behavior:
#     scaleDown:
#       stabilizationWindowSeconds: 300
#     scaleUp:
#       stabilizationWindowSeconds: 60

# Monitoring (Prometheus):
# - Scrape ollama metrics endpoint: http://ollama:11434/metrics
# - Key metrics: ollama_loaded_models, ollama_request_duration_seconds, ollama_gpu_memory_used

# Logs (Loki):
# - Promtail scrapes pod logs
# - Labels: app=ollama, namespace=ai

# Tracing (Tempo):
# - OTEL Collector receives traces from Ollama (if instrumented)
# - Or use Tempo's Zipkin receiver for Ollama HTTP traces