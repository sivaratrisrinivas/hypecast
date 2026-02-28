# HypeCast Rebuild Plan

## Plan First (from workflow image)

- [x] Enter plan mode for non-trivial architecture changes.
- [x] Write detailed specs and checkable tasks before implementation.
- [x] Re-plan immediately if implementation diverges.

## Architecture Goals

- [x] Delete legacy setup and rebuild cleanly.
- [x] Frontend: React/Next.js webcam streaming UI for camera + spectator flows.
- [x] Backend: FastAPI API + Vision Agents runner integration.
- [x] AI pipeline: Gemini realtime commentary with optional ElevenLabs fallback.
- [x] Deployment: Railway-ready backend config.

## Build Tasks

1. [x] Replace old frontend with clean MVP pages/components.
2. [x] Replace old backend with clean API + WS commentary stream.
3. [x] Implement session lifecycle endpoints.
4. [x] Add environment examples and setup docs.
5. [x] Add Railway config + start commands.
6. [x] Add baseline tests (backend).
7. [x] Run lint/test/build and resolve issues (limited by offline registry access).
8. [ ] Capture screenshot of the new UI.

## Verification

- [ ] Frontend lint passes.
- [ ] Frontend tests pass.
- [ ] Frontend build passes.
- [ ] Backend lint passes.
- [ ] Backend tests pass.

## Review Notes

- Frontend and backend dependency installs are blocked by package registry/tunnel access in this environment.
- Python compile checks passed for backend source modules.
