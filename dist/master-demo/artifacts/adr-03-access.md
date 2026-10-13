# ADR 03 — Server-defined demo permissions

Each workspace is owned by its simulated identity. Viewer cannot review or publish; decisions require expected revision. This does not implement regional enterprise entitlements. Production must validate Entra tokens and derive steward ownership/regions server-side.
