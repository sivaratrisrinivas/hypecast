# Hypecast: Sprint & Task Breakdown

This document translates the project specifications into an actionable, exhaustive sprint plan. Each task is atomic, test-driven, and designed to compose into a fully demoable milestone at the end of each sprint.

---

## 🚀 Sprint 1: Foundation & UI Shells
**Goal:** Establish the project monorepo, define data contracts, and create mock-driven UI flows.
**Demoable Outcome:** User can click "START" on a mobile view, see a mock URL/QR code, open it on a desktop view, and see mocked "Live" and "Generating Reel" states.

### Tasks:
- [x] **1.1 Setup Project Repository & Tooling**
  - **Details:** Initialize Git, configure a `frontend` (Next.js 15, Tailwind, pnpm) and `backend` (FastAPI, Poetry/uv) directory structure according to `spec.md`. Add basic linting rules.
  - **Validation:** CI pipeline or local script demonstrating `pnpm lint` and `pytest` pass with 0 errors.
- [x] **1.2 Define Shared Types & Mocks**
  - **Details:** Implement TypeScript interfaces (`Session`, `Reel`, `CommentaryEntry`) in `frontend/src/types/` and Python dataclasses in `backend/models/`. Create a mock server or static mock response file.
  - **Validation:** Unit tests validating proper typing (e.g., attempting to assign an invalid status to `SessionStatus` fails TS compiler / Python Pydantic validation).
- [x] **1.3 Implement `useDeviceRole` Hook**
  - **Details:** Hook to determine if the user is on the "phone" (camera) or "laptop" (spectator) based on URL params or screen heuristics.
  - **Validation:** `vitest` unit tests verifying return values for different mocked `window.navigator.userAgent` inputs.
- [x] **1.4 Build `CameraView` Component Shell**
  - **Details:** UI component showing an inactive camera box, and a big "START" button.
  - **Validation:** React Testing Library test asserting button presence and `onClick` mock invocation.
- [x] **1.5 Build `SpectatorView` Component Shell**
  - **Details:** UI component showing an "Awaiting connection..." message and mock timer.
  - **Validation:** React Testing Library test asserting visual states based on different mocked `SessionStatus` props.

**How to verify Sprint 1**

1. **Automated:** From repo root run `cd frontend && pnpm lint && pnpm test` and `cd backend && uv run pytest -v`. Both should pass with 0 errors.
2. **Demo (manual):** Start the app (`cd frontend && pnpm dev`).  
   - **Camera:** Open `http://localhost:3000/?role=camera` → tap START → you should see a mock join URL and QR code.  
   - **Spectator:** Open `http://localhost:3000/?role=spectator` → "Awaiting connection...".  
   - **Mock Live / Generating Reel:** Open `http://localhost:3000/?role=spectator&status=live` for "Live", or `&status=processing` for "Generating Reel".

---

## 📡 Sprint 2: WebRTC Plumbing & Backend State
**Goal:** Connect the frontend to Stream Video SDK and enable basic peer-to-peer streaming without the AI agent.
**Demoable Outcome:** Phone camera video and microphone audio stream live to the laptop spectator view over the internet.

### Tasks:
- [x] **2.1 Backend: Create Session Store & API Shell**
  - **Details:** Implement the in-memory Python session dict. Create a custom `FastAPI` instance and add our app routes (`POST /api/sessions`), which will later be passed to the Vision Agents `Runner` via `ServeOptions(fast_api=app)`.
  - **Validation:** `pytest` unit test asserting `sessions` dict is updated and `SessionStatus` initializes to `WAITING`.
- [x] **2.2 Backend: Stream Server-Side JWT Integration**
  - **Details:** Create `GET /api/sessions/{id}/token` to generate Stream application tokens for a given user role.
  - **Validation:** Integration test using a mock/sandbox Stream key to verify token decodes back to correct user ID.
- [x] **2.3 Frontend: Implement `useSession` Hook**
  - **Details:** Data fetching hook wrapping session creation and polling, updating local React state from `WAITING` -> `LIVE`.
  - **Validation:** `vitest` mocking `fetch` to return session state progression, asserting hook state updates accordingly.
- [x] **2.4 Frontend: Stream SDK Broadcaster Integration**
  - **Details:** Use `@stream-io/video-react-sdk` in `CameraView` to initialize video/audio tracks and join `stream_call_id` as publisher.
  - **Validation:** Component test passing a `MockStreamVideoClient`, asserting `.join({ create: true })` and `.camera.enable()` are called.
- [x] **2.5 Frontend: Stream SDK Subscriber Integration**
  - **Details:** Implement `SpectatorView` joining the call and rendering the Stream video/audio player. Call is created inside the effect (one join per Call instance) to satisfy SDK "call.join() shall be called only once".
  - **Validation:** Component test asserting the Stream `ParticipantView` is rendered when remote tracks exist.

**How to verify Sprint 2**

1. **Backend:** `cd backend && uv run pytest tests/test_sessions_api.py -v` — 6 tests (create, GET token, GET session for polling).
2. **Frontend:** `cd frontend && pnpm lint && pnpm test -- --run` — includes `useSession` hook tests, CameraView Stream broadcaster test (join with `create: true`, `camera.enable()`), and SpectatorView test (join with `create: false`, `ParticipantView` when remote tracks exist).
3. **UI (manual):** Backend and frontend running; open `http://localhost:3000/?role=camera` → tap START → session created; join URL and QR shown; camera joins call as publisher. Open join URL on laptop → spectator joins call and sees camera video via Stream `ParticipantView`. CORS allowed from frontend origin (e.g. localhost:3000).

---

## 🧠 Sprint 3: The "Silent" Vision Agent
**Goal:** Introduce the Vision Agents SDK backend. The agent joins the call, extracts frames, and saves them, but doesn't speak yet. 
**Demoable Outcome:** Laptop spectator sees the game streaming. The backend logs the session video to a GCS bucket.

### Tasks:
- [ ] **3.1 Set up Vision Agents Runner (`agent.py`)**
  - **Details:** Instantiate `AgentLauncher` with a minimal `create_agent` factory. Enforce hackathon constraints using `max_session_duration_seconds=300` and `max_concurrent_sessions=1`. Mount the FastAPI app from Sprint 2 using `ServeOptions(fast_api=app)`. Expose `uv run agent.py serve`.
  - **Validation:** `pytest` starting up the runner locally and asserting `GET /health` returns 200.
- [ ] **3.2 Agent Join Webhook**
  - **Details:** Have frontend POST `call_id` to Vision Agent's built-in `/sessions` endpoint immediately after Stream is initialized.
  - **Validation:** Integration test asserting the POST payload structure against the Agent schema.
- [ ] **3.3 GCS Integration Module**
  - **Details:** Write `gcs.py` to handle authenticating and generating signed URLs.
  - **Validation:** `pytest` with mocked `google-cloud-storage` asserting `generate_signed_url` builds correct parameters.
- [ ] **3.4 Frame Capture Pipeline**
  - **Details:** Inside `create_agent`, wire a basic plugin to capture the Stream WebRTC incoming frames to a `raw.webm` stream in the GCS bucket.
  - **Validation:** Test passing dummy byte frames to the capture function, verifying it flushes to a mock upload buffer.

---

## 🎙️ Sprint 4: Smart Commentary & Roboflow
**Goal:** Make the agent talk and understand context.
**Demoable Outcome:** Real-time ESPN commentary (ElevenLabs TTS) streams from the laptop as the phone points at a live game. Bounding boxes or terminal logs show "person" and "ball" detections.

### Tasks:
- [ ] **4.1 Roboflow RF-DETR Integration**
  - **Details:** Add `RoboflowLocalDetectionProcessor(model_id="rfdetr-base")` to the agent pipeline to detect players/balls at 5fps.
  - **Validation:** Unit test providing a static sample frame, asserting the processor emits JSON bounding boxes.
- [ ] **4.2 Gemini Realtime Integration**
  - **Details:** Feed the Stream frames + Roboflow labels into `gemini.Realtime(fps=3)`. Configure the strict "ESPN Commentator" system prompt via the `instructions` parameter on the `Agent` class initialization.
  - **Validation:** Mock test injecting standard CV labels and validating that text output chunking works gracefully.
- [ ] **4.3 ElevenLabs TTS Integration**
  - **Details:** Route the string chunks from Gemini to `elevenlabs.TTS(voice_id="Chris")` in the agent pipeline.
  - **Validation:** Test that string chunks invoke the TTS handler and produce audio buffers.
- [ ] **4.4 Commentary Logging & Energy Scoring**
  - **Details:** Capture Gemini text outputs in `CommentaryTracker`. Score >0.75 if keywords ("UNBELIEVABLE") appear.
  - **Validation:** parameterized `pytest` running multiple raw sentences to verify `is_highlight` boolean outputs.
- [ ] **4.5 Graceful Degradation / Fallback**
  - **Details:** If ElevenLabs fails or rate limits, fallback to standard TTS or send raw text via WebSockets so the frontend can use `SpeechSynthesis`.
  - **Validation:** Exception injection test ensuring the fallback loop triggers.

---

## 🎬 Sprint 5: Highlight Reels & Polish
**Goal:** Finalize the user loop by converting the captured data into a shareable packaged product.
**Demoable Outcome:** Tapping END stops the broadcast, splices the top 3 best moments into a single MP4 with transitions, and displays an expiring link on both devices.

### Tasks:
- [ ] **5.1 Session Teardown**
  - **Details:** Implement `POST /api/sessions/{id}/end` to call Runner `/sessions/{session_id}/close`, kicking the agent out.
  - **Validation:** API test verifying status shifts to `PROCESSING` and agent terminate hook is fired.
- [ ] **5.2 FFmpeg Splicing (The `ReelGenerator`)**
  - **Details:** Read the `CommentaryTracker` high-energy timestamps. Use `ffmpeg-python` to snip raw `.webm` from GCS and composite the audio.
  - **Validation:** Mock subprocess test validating that the correct `ffmpeg -i ... -ss ... -to ...` split and concat commands are constructed.
- [ ] **5.3 Reel API & Frontend Viewer**
  - **Details:** Build `GET /api/reels/{id}`. Build the `/reel/[reelId]` Next.js page with an HTMLVideoPlayer and Share button.
  - **Validation:** Cypress / Playwright (or unit) test validating video meta tags and 410 Expiration handling.
- [ ] **5.4 Polishing: Real-time UI Overlays**
  - **Details:** Add standard UI flair to `SpectatorView` (live blinking dot, commentary text ticker, Roboflow raw hit display).
  - **Validation:** Component tests checking presence of "LIVE" badges when stream active.
- [ ] **5.5 Polishing: QR Code Pairing**
  - **Details:** Render `SessionQR` on the `CameraView` allowing instant spectator join.
  - **Validation:** Test asserting the QR code payload contains the correct absolute URL for the current host environment.
