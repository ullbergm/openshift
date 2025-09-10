# Application Todo List

This document lists applications that could be considered for addition to the homelab deployment. Applications are categorized by function and include both popular self-hosted applications and infrastructure components commonly used in homelab environments.

## Application Status Legend

- ✅ **Deployed** - Currently running in the cluster
- 🔄 **Planned** - Identified for future deployment
- ⚠️ **Under Review** - Requires further evaluation
- ❌ **Not Suitable** - Determined to be incompatible or unnecessary

## Priority Levels

- **High** - Essential functionality, high impact, should be implemented soon
- **Medium** - Useful functionality, moderate impact, implement when resources allow
- **Low** - Nice to have, low impact, implement if time permits

---

## AI & Machine Learning

| Application                | Status      | Priority | Notes                                                                  |
| -------------------------- | ----------- | -------- | ---------------------------------------------------------------------- |
| **LiteLLM**                | ✅ Deployed | -        | LLM proxy for managing multiple LLM APIs                               |
| **Ollama**                 | ✅ Deployed | -        | Local LLM runtime                                                      |
| **Open-WebUI**             | ✅ Deployed | -        | Web interface for LLMs                                                 |
| **Stable Diffusion WebUI** | 🔄 Planned  | High     | Text-to-image generation interface, requires significant GPU resources |
| **ComfyUI**                | 🔄 Planned  | Medium   | Node-based stable diffusion workflow interface, alternative to WebUI   |
| **Text Generation WebUI**  | 🔄 Planned  | Medium   | Advanced web interface for text generation models                      |
| **Jupyter Notebooks**      | 🔄 Planned  | High     | Interactive development environment for ML/data science                |
| **MLflow**                 | 🔄 Planned  | Low      | ML lifecycle management platform                                       |
| **Weights & Biases**       | 🔄 Planned  | Low      | ML experiment tracking and collaboration                               |

## Media & Entertainment

| Application        | Status      | Priority | Notes                                                                    |
| ------------------ | ----------- | -------- | ------------------------------------------------------------------------ |
| **Bazarr**         | ✅ Deployed | -        | Subtitle management for Radarr/Sonarr                                    |
| **Gaps**           | ✅ Deployed | -        | Media gap detection                                                      |
| **Radarr**         | ✅ Deployed | -        | Movie collection manager                                                 |
| **Sonarr**         | ✅ Deployed | -        | TV series collection manager                                             |
| **Recyclarr**      | 🔄 Planned  | High     | TRaSH guides automation for \*arr apps, essential for quality management |
| **Plex**           | 🔄 Planned  | High     | Media server, industry standard with excellent client support            |
| **Jellyfin**       | 🔄 Planned  | High     | Open-source media server alternative to Plex                             |
| **Overseerr**      | 🔄 Planned  | High     | Request management for Plex/Jellyfin, improves user experience           |
| **Prowlarr**       | 🔄 Planned  | High     | Indexer manager for \*arr applications                                   |
| **Tautulli**       | 🔄 Planned  | Medium   | Plex monitoring and analytics                                            |
| **Lidarr**         | 🔄 Planned  | Medium   | Music collection manager                                                 |
| **PhotoPrism**     | 🔄 Planned  | High     | Photo management and organization with AI features                       |
| **Immich**         | 🔄 Planned  | High     | Modern photo and video backup solution, Google Photos alternative        |
| **Audiobookshelf** | 🔄 Planned  | Medium   | Audiobook and podcast server                                             |
| **Navidrome**      | 🔄 Planned  | Medium   | Music streaming server (subsonic-compatible)                             |
| **Readarr**        | 🔄 Planned  | Low      | Book collection manager                                                  |
| **Komga**          | 🔄 Planned  | Medium   | Comic/manga server                                                       |
| **YouTube-DL**     | 🔄 Planned  | Medium   | Video downloading service                                                |
| **Emby**           | 🔄 Planned  | Medium   | Media server with premium features                                       |
| **LibrePhotos**    | 🔄 Planned  | Medium   | Photo management with facial recognition                                 |

## Communication & Social

| Application          | Status     | Priority | Notes                                                     |
| -------------------- | ---------- | -------- | --------------------------------------------------------- |
| **Nextcloud**        | 🔄 Planned | High     | File sync, calendar, contacts, and collaboration platform |
| **Matrix (Synapse)** | 🔄 Planned | Medium   | Decentralized chat server, self-hosted communication      |
| **Element**          | 🔄 Planned | Medium   | Matrix web client                                         |
| **Ghost**            | 🔄 Planned | Medium   | Modern publishing platform                                |
| **Rocket.Chat**      | 🔄 Planned | Low      | Team communication platform                               |
| **Mastodon**         | 🔄 Planned | Low      | Decentralized social network                              |
| **Discourse**        | 🔄 Planned | Low      | Modern forum software                                     |
| **Mailcow**          | 🔄 Planned | Medium   | Complete email server solution                            |

## Development & DevOps

| Application       | Status     | Priority | Notes                                               |
| ----------------- | ---------- | -------- | --------------------------------------------------- |
| **Gitea/Forgejo** | 🔄 Planned | High     | Lightweight Git hosting service, GitHub alternative |
| **Jenkins**       | 🔄 Planned | Medium   | CI/CD automation server                             |
| **SonarQube**     | 🔄 Planned | Medium   | Code quality analysis                               |
| **Harbor**        | 🔄 Planned | Medium   | Container image registry with security scanning     |
| **Vault**         | 🔄 Planned | High     | Secrets management                                  |
| **Code Server**   | 🔄 Planned | High     | VS Code in the browser for remote development       |
| **GitLab CE**     | 🔄 Planned | Medium   | Complete DevOps platform                            |
| **Nexus**         | 🔄 Planned | Low      | Artifact repository manager                         |
| **Portainer**     | 🔄 Planned | Medium   | Container management UI                             |

## Monitoring & Observability

| Application       | Status     | Priority | Notes                                           |
| ----------------- | ---------- | -------- | ----------------------------------------------- |
| **Grafana**       | 🔄 Planned | High     | Metrics visualization and dashboards            |
| **Prometheus**    | 🔄 Planned | High     | Metrics collection and alerting                 |
| **Loki**          | 🔄 Planned | High     | Log aggregation system                          |
| **Uptime Kuma**   | 🔄 Planned | High     | Uptime monitoring tool, simple and effective    |
| **Netdata**       | 🔄 Planned | Medium   | Real-time performance monitoring                |
| **Alertmanager**  | 🔄 Planned | Medium   | Alert handling and routing for Prometheus       |
| **Jaeger**        | 🔄 Planned | Low      | Distributed tracing system                      |
| **ElasticSearch** | 🔄 Planned | Low      | Search and analytics engine, resource intensive |

## Productivity & Organization

| Application       | Status     | Priority | Notes                                          |
| ----------------- | ---------- | -------- | ---------------------------------------------- |
| **Vikunja**       | 🔄 Planned | Medium   | Task management and to-do lists                |
| **Bookstack**     | 🔄 Planned | High     | Wiki and documentation platform                |
| **Outline**       | 🔄 Planned | Medium   | Team knowledge base                            |
| **Focalboard**    | 🔄 Planned | Medium   | Project management (Notion/Trello alternative) |
| **HedgeDoc**      | 🔄 Planned | Medium   | Collaborative markdown editor                  |
| **Joplin Server** | 🔄 Planned | Low      | Note-taking and synchronization                |

## Utilities & Tools

| Application     | Status      | Priority | Notes                                      |
| --------------- | ----------- | -------- | ------------------------------------------ |
| **Excalidraw**  | ✅ Deployed | -        | Virtual whiteboard for sketching           |
| **Homepage**    | 🔄 Planned  | High     | Customizable application dashboard         |
| **Uptime Kuma** | 🔄 Planned  | High     | Service monitoring and status pages        |
| **FreshRSS**    | 🔄 Planned  | Medium   | RSS feed aggregator                        |
| **Linkding**    | 🔄 Planned  | Medium   | Bookmark manager                           |
| **Gotify**      | 🔄 Planned  | Medium   | Push notification server                   |
| **Searx**       | 🔄 Planned  | Medium   | Privacy-respecting metasearch engine       |
| **Wallabag**    | 🔄 Planned  | Low      | Read-it-later service (Pocket alternative) |

## Security & Privacy

| Application               | Status     | Priority | Notes                                     |
| ------------------------- | ---------- | -------- | ----------------------------------------- |
| **Bitwarden/Vaultwarden** | 🔄 Planned | High     | Password manager, essential security tool |
| **Authelia**              | 🔄 Planned | High     | Authentication and authorization server   |
| **Authentik**             | 🔄 Planned | Medium   | Identity provider and SSO                 |
| **WireGuard**             | 🔄 Planned | High     | Modern VPN protocol                       |
| **CrowdSec**              | 🔄 Planned | Medium   | Collaborative security engine             |
| **Pi-hole**               | 🔄 Planned | High     | Network-wide ad blocking                  |

## Database & Storage

| Application    | Status     | Priority | Notes                                                   |
| -------------- | ---------- | -------- | ------------------------------------------------------- |
| **PostgreSQL** | 🔄 Planned | High     | Advanced relational database, used by many applications |
| **Redis**      | 🔄 Planned | High     | In-memory data structure store, caching                 |
| **MinIO**      | 🔄 Planned | Medium   | S3-compatible object storage                            |
| **PgAdmin**    | 🔄 Planned | Medium   | PostgreSQL administration tool                          |
| **InfluxDB**   | 🔄 Planned | Medium   | Time-series database for metrics                        |

## Gaming

| Application          | Status     | Priority | Notes                        |
| -------------------- | ---------- | -------- | ---------------------------- |
| **Minecraft Server** | 🔄 Planned | Medium   | Minecraft game server        |
| **Pterodactyl**      | 🔄 Planned | Low      | Game server management panel |
| **Satisfactory**     | 🔄 Planned | Low      | Dedicated game server        |

## Home Automation & IoT

| Application     | Status     | Priority | Notes                           |
| --------------- | ---------- | -------- | ------------------------------- |
| **Node-Red**    | 🔄 Planned | High     | Home automation workflow engine |
| **Zigbee2MQTT** | 🔄 Planned | High     | Zigbee to MQTT bridge           |
| **ESPHome**     | 🔄 Planned | Medium   | ESP8266/ESP32 firmware platform |
| **EMQX**        | 🔄 Planned | Medium   | MQTT broker for IoT             |
| **Frigate**     | 🔄 Planned | Medium   | NVR with AI object detection    |

## Finance & ERP

| Application      | Status     | Priority | Notes                          |
| ---------------- | ---------- | -------- | ------------------------------ |
| **Firefly III**  | 🔄 Planned | Medium   | Personal finance management    |
| **InvoiceNinja** | 🔄 Planned | Low      | Invoicing and billing platform |
| **Kimai**        | 🔄 Planned | Low      | Time tracking application      |

## Network Services

| Application             | Status     | Priority | Notes                                                  |
| ----------------------- | ---------- | -------- | ------------------------------------------------------ |
| **Pi-hole**             | 🔄 Planned | High     | Network-wide ad blocking                               |
| **Unbound**             | 🔄 Planned | Medium   | Validating DNS resolver                                |
| **Traefik**             | 🔄 Planned | Medium   | Modern reverse proxy (alternative to OpenShift routes) |
| **Nginx Proxy Manager** | 🔄 Planned | Low      | Easy Nginx proxy management                            |

## Infrastructure Services

| Application      | Status     | Priority | Notes                           |
| ---------------- | ---------- | -------- | ------------------------------- |
| **MetalLB**      | 🔄 Planned | Medium   | Bare metal load balancer        |
| **Velero**       | 🔄 Planned | High     | Kubernetes backup and migration |
| **Longhorn**     | 🔄 Planned | Medium   | Distributed block storage       |
| **External DNS** | 🔄 Planned | Medium   | DNS record management           |
| **Cert Manager** | 🔄 Planned | High     | TLS certificate management      |

---

## Implementation Notes

### Resource Requirements

- **High GPU Applications**: Stable Diffusion, ComfyUI require significant GPU resources
- **Database Heavy**: PostgreSQL, Redis should be implemented early as dependencies
- **Storage Intensive**: Media applications, photo management require substantial storage

### Dependencies

- **Authentication**: Implement Authelia or Authentik early for SSO across applications
- **Monitoring Stack**: Prometheus + Grafana + Loki should be deployed together
- **Media Stack**: Prowlarr → Sonarr/Radarr → Plex/Jellyfin → Overseerr workflow

### Security Considerations

- All applications should integrate with central authentication (SSO)
- Network policies should be implemented for inter-pod communication
- Regular security updates and vulnerability scanning
- Backup strategies for all persistent data

### Deployment Strategy

1. **Phase 1 (Core Infrastructure)**: PostgreSQL, Redis, Vault, Cert Manager
2. **Phase 2 (Monitoring)**: Prometheus, Grafana, Uptime Kuma
3. **Phase 3 (Authentication)**: Authelia/Authentik, SSO integration
4. **Phase 4 (Applications)**: Deploy based on priority and dependencies

---

_Last updated: September 10, 2025_
