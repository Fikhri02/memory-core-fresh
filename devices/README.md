# Devices

The sync registry: one file per device, `devices/{id}.md`, written only by that device on every sync.
Each file lists what the device follows, its Claude Code plugins and its MCP servers — names, scopes
and transports only, never settings, arguments or tokens.

The device's own identity lives in `device/id.md`, which is never synced. See the `sync-memory` skill.
