# Design

## The Lenny Growth Assistant

### Design Principles

1. **Simplicity** — Prefer simple, maintainable solutions over clever abstractions
2. **Incremental Delivery** — Build in phases; each phase should produce a working system
3. **Security by Default** — Never commit secrets; treat generated HTML as untrusted
4. **Observability** — Structured logging and health checks from the start
5. **Reproducibility** — Docker Compose workflow for consistent environments

### Frontend Design

*To be defined in Phase 3.*

The frontend will include:
- Conversational chat interface
- Artifact viewer with safe rendering
- Session management

### API Design

*To be expanded in Phase 2.*

Current endpoints:
- `GET /` — Application root
- `GET /health` — Liveness check
- `GET /health/ready` — Readiness check *(planned)*

### Status

This document will be expanded as the design evolves across phases.

*Phase 1: Foundation design decisions documented.*
