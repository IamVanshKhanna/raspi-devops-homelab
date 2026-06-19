# Cloudflare CDN Integration for Homelab
# Includes optimization rules, caching, compression, and security

## 1. DNS Records (managed via External-DNS)
# All subdomains point to Cloudflare proxy (orange cloud)

## 2. Page Rules (configured via API/Terraform)

### Rule 1: Static Assets - Cache Everything
# Pattern: *.homelab.local/static/*
# Settings:
# - Cache Level: Cache Everything
# - Edge Cache TTL: 1 year
# - Browser Cache TTL: 1 year
# - Compression: Brotli + Gzip

### Rule 2: API Endpoints - Bypass Cache
# Pattern: *.homelab.local/api/*
# Settings:
# - Cache Level: Bypass
# - Security Level: High
# - Rate Limiting: 1000 req/min per IP

### Rule 3: Nextcloud - WebDAV & Sync
# Pattern: *.homelab.local/remote.php/dav/*
# Settings:
# - Cache Level: Bypass
# - Security Level: Medium
# - Rate Limiting: 500 req/min per IP

### Rule 4: Admin Interfaces - High Security
# Pattern: *.homelab.local/admin*, *.homelab.local/dashboard*
# Settings:
# - Cache Level: Bypass
# - Security Level: High
# - WAF: Managed Ruleset + OWASP
# - Bot Fight Mode: On
# - Rate Limiting: 100 req/min per IP

### Rule 5: Monitoring/Observability - Internal Only
# Pattern: grafana.homelab.local/*, prometheus.homelab.local/*
# Settings:
# - Cache Level: Bypass
# - Access: Zero Trust / Cloudflare Access
# - IP Restriction: Tailscale CIDR only

## 3. Workers (Edge Compute)

### Worker 1: Security Headers
# Route: *.homelab.local/*
# Script: Adds security headers to all responses

```
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const response = await fetch(request)
  const headers = new Headers(response.headers)
  
  // Security Headers
  headers.set('X-Content-Type-Options', 'nosniff')
  headers.set('X-Frame-Options', 'DENY')
  headers.set('X-XSS-Protection', '1; mode=block')
  headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
  headers.set('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'")
  
  // Remove server header
  headers.delete('Server')
  
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: headers
  })
}
```

### Worker 2: Cache Optimization for API
# Route: *.homelab.local/api/*, *.homelab.local/graphql*
# Script: Adds conditional caching for GET requests

```
addEventListener('fetch', event => {
  if (event.request.method === 'GET') {
    event.respondWith(cacheFirst(event.request))
  } else {
    event.respondWith(fetch(event.request))
  }
})

async function cacheFirst(request) {
  const cache = caches.default
  const cached = await cache.match(request)
  
  if (cached) {
    // Return cached with stale-while-revalidate
    const fetchPromise = fetch(request).then(response => {
      if (response.ok) cache.put(request, response.clone())
      return response
    })
    return cached
  }
  
  return fetch(request).then(response => {
    if (response.ok) cache.put(request, response.clone())
    return response
  })
}
```

### Worker 3: Request Compression Negotiation
# Route: *.homelab.local/*
# Script: Ensures Brotli/Zstd compression

```
addEventListener('fetch', event => {
  const request = event.request
  
  // Add Accept-Encoding if not present
  if (!request.headers.has('Accept-Encoding')) {
    const newHeaders = new Headers(request.headers)
    newHeaders.set('Accept-Encoding', 'br, gzip, deflate')
    event.respondWith(fetch(new Request(request, { headers: newHeaders })))
  }
})
```

## 4. Cloudflare Rulesets (via API)

### Rate Limiting Rules
```json
[
  {
    "description": "Global rate limit",
    "match": "http.request.full_uri matches \"*.homelab.local*\"",
    "action": "rate_limit",
    "rate_limit": {
      "threshold": 1000,
      "period": 60,
      "key": "ip.src"
    }
  },
  {
    "description": "API strict rate limit",
    "match": "http.request.full_uri matches \"*.homelab.local/api*\"",
    "action": "rate_limit",
    "rate_limit": {
      "threshold": 200,
      "period": 60,
      "key": "ip.src"
    }
  },
  {
    "description": "Login endpoint strict rate limit",
    "match": "http.request.uri.path matches \"*/login*\"",
    "action": "rate_limit",
    "rate_limit": {
      "threshold": 10,
      "period": 300,
      "key": "ip.src"
    }
  }
]
```

### WAF Rules
```json
[
  {
    "description": "Block SQL injection",
    "action": "block",
    "match": "http.request.body contains \"SELECT\" or http.request.body contains \"UNION\" or http.request.body contains \"DROP\""
  },
  {
    "description": "Block XSS attempts",
    "action": "block",
    "match": "http.request.uri.query contains \"<script>\" or http.request.body contains \"<script>\""
  },
  {
    "description": "Block path traversal",
    "action": "block",
    "match": "http.request.uri.path contains \"../\" or http.request.uri.path contains \"..\\\\\""
  }
]
```

### Transform Rules (Compression & Caching)
```json
[
  {
    "description": "Force Brotli compression",
    "action": "modify_response_header",
    "match": "true",
    "modify_response_header": {
      "action": "set",
      "header": "Content-Encoding",
      "value": "br"
    }
  },
  {
    "description": "Set cache tags for purging",
    "action": "modify_response_header",
    "match": "cf.cache_status in {\"HIT\" \"MISS\" \"EXPIRED\"}",
    "modify_response_header": {
      "action": "set",
      "header": "Cache-Tag",
      "value": "homelab,{{http.host}}"
    }
  }
]
```

## 5. Terraform Configuration

```hcl
# cloudflare.tf

resource "cloudflare_zone_settings" "homelab" {
  zone_id = var.zone_id
  settings {
    # Performance
    brotli = "on"
    automatic_https_rewrites = "on"
    http2 = "on"
    http3 = "on"
    min_tls_version = "1.2"
    tls_1_3 = "on"
    
    # Caching
    browser_cache_ttl = 31536000
    cache_level = "aggressive"
    edge_cache_ttl = 31536000
    
    # Compression
    compression = "on"
    
    # Security
    waf = "on"
    security_level = "medium"
    bot_fight_mode = "on"
    challenge_ttl = 1800
    
    # Performance
    rocket_loader = "off"  # Can break some apps
    mirage = "off"
    polish = "lossless"
    early_hints = "on"
  }
}

resource "cloudflare_page_rule" "static_assets" {
  zone_id = var.zone_id
  target  = "*.homelab.local/static*"
  priority = 1
  actions {
    cache_level       = "cache_everything"
    edge_cache_ttl    = 31536000
    browser_cache_ttl = 31536000
  }
}

resource "cloudflare_page_rule" "api_bypass" {
  zone_id = var.zone_id
  target  = "*.homelab.local/api*"
  priority = 2
  actions {
    cache_level = "bypass"
    security_level = "high"
  }
}

resource "cloudflare_worker_script" "security_headers" {
  account_id = var.account_id
  name       = "security-headers"
  content    = file("workers/security-headers.js")
}

resource "cloudflare_worker_route" "security_headers" {
  zone_id = var.zone_id
  pattern = "*.homelab.local/*"
  script_name = "security-headers"
}

resource "cloudflare_rate_limit" "global" {
  zone_id = var.zone_id
  threshold = 1000
  period    = 60
  match {
    request {
      url_pattern = "*.homelab.local*"
    }
  }
  action {
    mode = "simulate"
    timeout = 300
    response {
      content_type = "application/json"
      body = "{\"error\": \"Rate limit exceeded\"}"
    }
  }
}

resource "cloudflare_waf_rule" "sql_injection" {
  zone_id = var.zone_id
  filter = "http.request.body contains \"SELECT\" or http.request.body contains \"UNION\" or http.request.body contains \"DROP\""
  action = "block"
  description = "Block SQL injection attempts"
}

resource "cloudflare_waf_rule" "xss" {
  zone_id = var.zone_id
  filter = "http.request.uri.query contains \"<script>\" or http.request.body contains \"<script>\""
  action = "block"
  description = "Block XSS attempts"
}
```

## 6. External-DNS Configuration for Cloudflare

```yaml
# External-DNS with Cloudflare provider
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-credentials
  namespace: external-dns
stringData:
  api-token: ${CLOUDFLARE_API_TOKEN}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: external-dns
  namespace: external-dns
spec:
  template:
    spec:
      containers:
      - name: external-dns
        image: registry.k8s.io/external-dns/external-dns:v0.14.0
        args:
        - --source=service
        - --source=ingress
        - --domain-filter=homelab.local
        - --provider=cloudflare
        - --cloudflare-proxied=true
        - --policy=upsert-only
        - --txt-owner-id=homelab
        env:
        - name: CF_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: cloudflare-credentials
              key: api-token
```

## 7. Traefik Middleware for Cloudflare Integration

```yaml
# Traefik Middleware for Cloudflare
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: cloudflare-headers
  namespace: traefik
spec:
  headers:
    customRequestHeaders:
      # Pass Cloudflare headers to backend
      CF-Connecting-IP: ""
      CF-Ray: ""
      CF-Visitor: ""
      CF-IPCountry: ""
    customResponseHeaders:
      # Security headers (backup if Worker fails)
      X-Content-Type-Options: "nosniff"
      X-Frame-Options: "DENY"
      X-XSS-Protection: "1; mode=block"
      Referrer-Policy: "strict-origin-when-cross-origin"
    stsSeconds: 31536000
    stsIncludeSubdomains: true
    stsPreload: true
    forceSTSHeader: true
---
# Rate limiting middleware
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: ratelimit
  namespace: traefik
spec:
  rateLimit:
    average: 1000
    burst: 2000
    period: 1m
---
# Compression middleware
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: compress
  namespace: traefik
spec:
  compress:
    includedContentTypes:
      - "text/html"
      - "text/css"
      - "text/javascript"
      - "application/javascript"
      - "application/json"
      - "application/xml"
      - "application/rss+xml"
      - "font/woff"
      - "font/woff2"
    excludedContentTypes:
      - "image/*"
      - "video/*"
      - "audio/*"
```