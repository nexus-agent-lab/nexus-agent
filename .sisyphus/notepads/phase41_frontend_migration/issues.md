
## Memory Management API
- Found that `Memory.embedding` is not needed by the front end, so we intentionally omitted it from `MemoryResponse` to avoid massive payload overheads.

## Tailscale Network Status
- The backend subprocess call `docker exec nexus-agent-ts-nexus-1 tailscale status --json` will often fail in a local isolated dev environment if the host Docker socket isn't mounted, or if running directly on host without the container running. The frontend gracefully falls back to displaying a generic generic placeholder node in this case.
