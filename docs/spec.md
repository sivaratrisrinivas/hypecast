# Hypecast — Technical Specification

> Source of truth for architecture, data models, APIs, and implementation.  
> **Validated against:** [Vision Agents](https://visionagents.ai) docs via **Vision Agents MCP server** (`SearchVisionAgents`).

---

## 1. Project Overview & Core Objectives

**Hypecast** turns any casual sports game into an ESPN broadcast. A phone streams live video; an AI agent watches in real-time, generates continuous play-by-play commentary via an ESPN-style voice. After the game ends, a highlight reel with baked-in commentary is auto-generated and shared via a 48-hour expiring link.

### Hackathon

| Item              | Detail                                           |
| ----------------- | ------------------------------------------------ |
| **Event**         | Vision Possible: Agent Protocol by WeMakeDevs    |
| **Dates**         | Feb 23 – Mar 1, 2026                             |
| **Required SDK**  | Vision Agents SDK by Stream                      |
| **Prizes**        | $4,000+ cash, swag, interviews                   |

### Core Objectives

1. **One-tap start** — user opens the web app, taps START, and commentary begins within 3 seconds.
2. **Two-device model** — phone is the camera, laptop/tablet is the spectator speaker. Same URL, auto-detected role.
3. **Real-time AI commentary** — Gemini Realtime watches sampled frames, generates play-by-play text, ElevenLabs speaks it.
4. **Auto highlight reel** — after the game, AI picks 3–5 best moments, FFmpeg stitches them with commentary audio into a shareable MP4.
5. **Zero configuration** — no accounts, no sport selection, no player names. AI figures it out from video.

### User Flows

```
Phone (Camera)                  System                          Laptop (Spectator)
  │                               │                                │
  │  1. Tap START                 │                                │
  │─────────────────────────────▶ │                                │
  │  2. Session created           │                                │
  │  3. Shows URL / QR            │                                │
  │◀───────────────────────────── │                                │
  │                               │                                │
  │      === User opens URL on laptop ===                          │
  │                               │                                │
  │                               │  4. Laptop joins session       │
  │                               │◀────────────────────────────── │
  │  5. Camera streaming          │  5. Commentary starts (<3s)    │
  │                               │──────────────────────────────▶ │
  │         ... game in progress (up to 5 min) ...                 │
  │  6. Tap END                   │                                │
  │─────────────────────────────▶ │                                │
  │                               │  7. "Generating reel..."       │
  │                               │──────────────────────────────▶ │
  │  8. Shareable link shown      │  8. Shareable link shown       │
  │◀───────────────────────────── │──────────────────────────────▶ │
```

### Session Constraints

| Constraint              | Value                    |
| ----------------------- | ------------------------ |
| Max session duration     | 5 minutes                |
| Highlight reel length    | 30–60 seconds            |
| Highlights per reel      | 3–5 clips                |
| Shareable link expiry    | 48 hours                 |
| Concurrent sessions      | 1 (MVP)                  |
| Video resolution         | 720p                     |
| Vision AI sample rate    | 3 fps                    |
| Object detection rate    | 5 fps                    |
| Target commentary latency| < 3 seconds              |

---

## 2. Tech Stack & Libraries

### Frontend

| Package                        | Version   | Purpose                                           |
| ------------------------------ | --------- | ------------------------------------------------- |
| `next`                         | `15.x`    | React framework, file-based routing, SSR           |
| `react` / `react-dom`          | `19.x`    | UI rendering                                       |
| `@stream-io/video-react-sdk`   | `latest`  | Stream Video SDK — WebRTC call management          |
| `@stream-io/node-sdk`          | `latest`  | Server-side Stream token generation                |
| `tailwindcss`                  | `4.x`     | Utility-first CSS                                  |
| `qrcode.react`                 | `latest`  | QR code for two-device pairing                     |
| `typescript`                   | `5.x`     | Type safety                                        |

**Hosting**: Vercel (Hobby tier, free)

### Backend

| Package                        | Version   | Purpose                                           |
| ------------------------------ | --------- | ------------------------------------------------- |
| `vision-agents`                | `latest`  | Stream's Vision Agents SDK — `Runner`, `AgentLauncher`, `Agent` |
| `fastapi`                      | `0.115.x` | HTTP server (auto-provided by Vision Agents `Runner`) |
| `uvicorn`                      | `0.34.x`  | ASGI server                                        |
| `python-dotenv`                | `1.x`     | Environment variable loading                       |
| `google-cloud-storage`         | `2.x`     | GCS uploads for video clips and reels              |
| `ffmpeg-python`                | `0.2.x`   | Programmatic FFmpeg for highlight reel stitching   |

**Runtime**: Python 3.11+  
**Hosting**: Google Cloud Run (serverless, $100 GCP credits)

### External Services

| Service                | SDK / Integration                                 | Purpose                              | Auth                          |
| ---------------------- | ------------------------------------------------- | ------------------------------------ | ----------------------------- |
| **Stream**             | `getstream.Edge()`                                | WebRTC video/audio transport         | `STREAM_API_KEY` + `STREAM_API_SECRET` |
| **Gemini**             | `gemini.Realtime(fps=3)`                          | Vision AI — frame analysis, commentary generation | `GOOGLE_API_KEY`             |
| **ElevenLabs**         | `elevenlabs.TTS(voice_id="Anr9GtYh2VRXxiPplzxM")`| Text-to-speech — ESPN commentator voice (Chris) | `ELEVENLABS_API_KEY`         |
| **Roboflow**           | `roboflow.RoboflowLocalDetectionProcessor`        | Local object detection (RF-DETR), no API key | None (runs locally)          |
| **Google Cloud Storage** | `google-cloud-storage` Python SDK               | Temporary video + reel storage       | GCP service account            |

### Dev Tools

| Tool       | Purpose                                |
| ---------- | -------------------------------------- |
| `pnpm`     | Frontend package manager               |
| `ffmpeg`   | System dependency for reel generation  |
| `docker`   | Backend containerization for Cloud Run |

---

## 3. Detailed Data Models

### 3.1 Frontend Types (`frontend/src/types/`)

```typescript
// session.ts

type SessionStatus = "waiting" | "live" | "processing" | "completed" | "error";
type DeviceRole = "camera" | "spectator";

interface Session {
  id: string;                  // nanoid, e.g. "abc123"
  streamCallId: string;        // Stream call ID bound to this session
  streamCallType: string;      // "default"
  status: SessionStatus;
  createdAt: string;           // ISO 8601
  endedAt: string | null;
  duration: number;            // seconds elapsed
  reelId: string | null;       // populated after reel generation
  reelUrl: string | null;      // 48h signed GCS URL
}

interface SessionCreateResponse {
  sessionId: string;
  streamCallId: string;
  streamToken: string;         // user-scoped JWT for Stream SDK
  joinUrl: string;             // /game/{sessionId}
}

interface SessionStatusResponse {
  status: SessionStatus;
  reelId: string | null;
  reelUrl: string | null;
}
```

```typescript
// reel.ts

interface Reel {
  id: string;                  // nanoid
  sessionId: string;
  url: string;                 // signed GCS URL
  expiresAt: string;           // ISO 8601, 48h from creation
  durationSeconds: number;     // 30–60s
  highlightCount: number;      // 3–5
  createdAt: string;
}

interface ReelViewerData {
  reel: Reel;
  expired: boolean;
  gameDate: string;            // formatted display date
}
```

```typescript
// commentary.ts — displayed on spectator view

interface CommentaryEntry {
  timestamp: number;           // seconds from session start
  text: string;                // raw commentary text from Gemini
  energyLevel: number;         // 0.0–1.0 heuristic score
  isHighlight: boolean;        // flagged as highlight-worthy
}
```

### 3.2 Backend Models (`backend/models/`)

```python
# session.py

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class SessionStatus(str, Enum):
    WAITING = "waiting"
    LIVE = "live"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class GameSession:
    id: str                                 # nanoid
    stream_call_id: str
    stream_call_type: str = "default"
    status: SessionStatus = SessionStatus.WAITING
    created_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    commentary_log: list["CommentaryEntry"] = field(default_factory=list)
    highlights: list["Highlight"] = field(default_factory=list)
    reel_id: str | None = None
    reel_url: str | None = None
```

```python
# commentary.py

from dataclasses import dataclass


@dataclass
class CommentaryEntry:
    timestamp: float            # seconds from session start
    text: str                   # raw commentary text
    energy_level: float         # 0.0–1.0
    is_highlight: bool          # flagged by energy threshold


HIGHLIGHT_KEYWORDS = [
    "INCREDIBLE", "UNBELIEVABLE", "WHAT A SHOT", "OH MY",
    "ARE YOU KIDDING", "AMAZING", "SPECTACULAR", "WOW",
]

ENERGY_THRESHOLD = 0.75        # entries above this are highlight candidates
```

```python
# highlight.py

from dataclasses import dataclass


@dataclass
class Highlight:
    start_time: float           # seconds from session start
    end_time: float             # start_time + clip duration
    energy_score: float         # peak energy in this window
    commentary_text: str        # commentary during this moment


@dataclass
class ReelJob:
    session_id: str
    highlights: list[Highlight]
    raw_video_gcs_path: str     # gs://bucket/sessions/{id}/raw.webm
    output_gcs_path: str        # gs://bucket/reels/{reel_id}.mp4
    status: str = "pending"     # pending | processing | done | error
```

### 3.3 In-Memory Session Store (MVP)

No database for MVP. Sessions are held in a Python dict keyed by session ID. This is acceptable for single-instance, single-concurrent-session MVP on Cloud Run.

```python
# store.py

from models.session import GameSession

sessions: dict[str, GameSession] = {}
```

---

## 4. Architecture & Directory Structure

### 4.1 System Architecture

```
┌──────────────┐         WebRTC (Stream)         ┌─────────────────────────────┐
│  Phone       │ ──────────────────────────────▶  │  Google Cloud Run           │
│  (Camera)    │                                  │                             │
│  Next.js PWA │                                  │  ┌───────────────────────┐  │
└──────────────┘                                  │  │  Vision Agents Server │  │
                                                  │  │                       │  │
┌──────────────┐         WebRTC Audio (Stream)    │  │  Gemini Realtime ───┐ │  │
│  Laptop      │ ◀──────────────────────────────  │  │  (3fps vision)     │ │  │
│  (Spectator) │                                  │  │       ▼            │ │  │
│  Next.js PWA │                                  │  │  ElevenLabs TTS    │ │  │
└──────────────┘                                  │  │  (Chris voice)     │ │  │
                                                  │  │       ▼            │ │  │
                                                  │  │  Audio → Stream    │ │  │
                                                  │  │                    │ │  │
                                                  │  │  Roboflow RF-DETR  │ │  │
                                                  │  │  (5fps local det.) │ │  │
                                                  │  └───────────────────┘│  │
                                                  │                       │  │
                                                  │  ┌───────────────────┐│  │
                                                  │  │ Highlight Reel Gen ││  │
                                                  │  │ (FFmpeg + GCS)    ││  │
                                                  │  └───────────────────┘│  │
                                                  └───────────────────────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │  GCS Bucket      │
                                                  │  48h lifecycle   │
                                                  └─────────────────┘
```

### 4.2 Directory Structure

```
hypecast/
├── spec.md                          # this file — source of truth
├── .env.example                     # env var template
├── .gitignore
│
├── frontend/                        # Next.js 15 app
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.mjs
│   ├── Dockerfile                   # (optional, Vercel handles deploy)
│   │
│   ├── public/
│   │   └── og-image.png             # social share image
│   │
│   └── src/
│       ├── app/
│       │   ├── layout.tsx           # root layout, fonts, meta
│       │   ├── page.tsx             # landing page (/)
│       │   ├── game/
│       │   │   └── [sessionId]/
│       │   │       └── page.tsx     # camera or spectator view (/game/:id)
│       │   └── reel/
│       │       └── [reelId]/
│       │           └── page.tsx     # shareable reel viewer (/reel/:id)
│       │
│       ├── components/
│       │   ├── landing/
│       │   │   ├── Hero.tsx
│       │   │   └── DemoVideo.tsx
│       │   ├── game/
│       │   │   ├── CameraView.tsx       # phone: camera preview + START/END
│       │   │   ├── SpectatorView.tsx     # laptop: audio viz + timer
│       │   │   ├── SessionQR.tsx        # QR code for pairing
│       │   │   ├── GameTimer.tsx
│       │   │   └── StatusOverlay.tsx    # "Generating reel..." etc.
│       │   ├── reel/
│       │   │   ├── ReelPlayer.tsx
│       │   │   └── ShareButton.tsx
│       │   └── ui/                      # shared primitives
│       │       ├── Button.tsx
│       │       └── LoadingSpinner.tsx
│       │
│       ├── lib/
│       │   ├── stream.ts               # Stream client init, token fetch
│       │   ├── api.ts                   # fetch wrappers for backend
│       │   └── device.ts               # camera detection → role assignment
│       │
│       ├── hooks/
│       │   ├── useSession.ts            # session lifecycle management
│       │   ├── useDeviceRole.ts         # detect camera vs spectator
│       │   └── useReelPolling.ts        # poll for reel completion
│       │
│       ├── types/
│       │   ├── session.ts
│       │   ├── reel.ts
│       │   └── commentary.ts
│       │
│       └── styles/
│           └── globals.css              # Tailwind base + broadcast theme
│
├── backend/                             # Python Vision Agents server
│   ├── pyproject.toml                   # or requirements.txt
│   ├── Dockerfile                       # Cloud Run container
│   ├── .env.example
│   │
│   ├── agent.py                         # entrypoint — create_agent + join_call + Runner
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session.py                   # GameSession, SessionStatus
│   │   ├── commentary.py               # CommentaryEntry, constants
│   │   └── highlight.py                # Highlight, ReelJob
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── store.py                     # in-memory session store
│   │   ├── commentary_tracker.py        # energy scoring, highlight flagging
│   │   ├── reel_generator.py            # FFmpeg stitching + GCS upload
│   │   └── gcs.py                       # GCS client, signed URL generation
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   └── sessions.py                  # REST endpoints (if extending beyond Runner defaults)
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_commentary_tracker.py
│       ├── test_reel_generator.py
│       └── test_models.py
│
└── scripts/
    └── example_prd.txt                  # (taskmaster)
```

### 4.3 Data Flow — Real-Time Commentary

```
Phone Camera (30fps)
     │
     ▼
Stream Edge Network (WebRTC SFU)
     │
     ├──▶ Gemini Realtime (3fps sampled)
     │       │  Receives video frames + Roboflow annotations
     │       │  Maintains game context across frames
     │       │  Outputs commentary text continuously
     │       ▼
     │    ElevenLabs TTS (voice: Chris)
     │       │  Converts text → speech audio chunks
     │       ▼
     │    Stream Edge Network (WebRTC audio track)
     │       │
     │       ▼
     │    Laptop speaker — spectator hears commentary
     │
     └──▶ Roboflow RF-DETR (5fps, local)
            │  Detects: "person", "sports ball"
            │  conf_threshold: 0.5
            │  Annotated frames fed to Gemini for richer context
```

### 4.4 Data Flow — Highlight Reel Generation

```
During game (continuous):
  ├── Raw video frames → GCS (gs://bucket/sessions/{id}/raw.webm)
  ├── CommentaryEntry[] accumulated with timestamps + energy scores
  └── Entries with energy_level > 0.75 flagged as highlights

After END tapped:
  1. Sort highlights by energy_score descending
  2. Pick top 3–5 non-overlapping time windows (5–15s each)
  3. FFmpeg: extract clips from raw video at highlight timestamps
  4. FFmpeg: overlay corresponding commentary audio on each clip
  5. FFmpeg: concatenate clips with brief transitions
  6. Upload final MP4 → GCS (gs://bucket/reels/{reel_id}.mp4)
  7. Generate 48h signed URL
  8. Update session status → "completed", set reel_url
  9. Return shareable link to both devices
```

---

## 5. API Endpoints & Interface Definitions

### 5.0 Vision Agents Runner (built-in API)

The backend runs `uv run agent.py serve`. The Vision Agents **Runner** registers these endpoints by default (see [Running Agents as a Server](https://visionagents.ai/guides/running)):

| Method | Endpoint | Purpose |
| ------ | -------- | -------- |
| POST | `/sessions` | Spawn agent for a call (body: `call_type`, `call_id`) |
| DELETE | `/sessions/{session_id}` | Stop an agent session |
| POST | `/sessions/{session_id}/close` | Stop session (e.g. sendBeacon from frontend) |
| GET | `/sessions/{session_id}` | Session info |
| GET | `/sessions/{session_id}/metrics` | Real-time metrics (LLM/TTS/STT latency, tokens) |
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness |

**POST /sessions** (Runner default):

- **Request:** `{"call_type": "default", "call_id": "<call_id>"}`
- **Response 200:** `{"session_id": "<uuid>", "call_id": "<call_id>", "session_started_at": "<ISO8601>"}`

**Note:** The Runner does **not** issue Stream tokens or return `join_url`. The frontend must obtain a Stream user token from our own backend (see 5.1) before creating/joining a call, then POST to `/sessions` with the same `call_id` so the agent joins.

**Session limits (AgentLauncher):** Use `ServeOptions` / `AgentLauncher` to enforce MVP limits: `max_session_duration_seconds=300`, `max_sessions_per_call=1`, `max_concurrent_sessions=1` (or small N).

### 5.1 App-specific REST API (FastAPI)

Base URL: `https://<cloud-run-url>`. App routes can be mounted on the Runner’s FastAPI app via `runner.fast_api` or a custom `ServeOptions(fast_api=app)`. Implemented: `backend/routes/sessions.py`, store in `backend/services/store.py` (task 2.1).

#### `POST /api/sessions` (create session; token in 2.2)

Creates a logical game session, generates a Stream **call_id** (e.g. `pickup-{nanoid}`), and returns a **Stream user token** so the frontend can create/join the call. Frontend then POSTs `call_type` + `call_id` to Runner’s **POST /sessions** to spawn the agent.

**Response `201`:**
```json
{
  "session_id": "abc123",
  "stream_call_id": "pickup-abc123",
  "stream_token": "eyJ...",
  "join_url": "/game/abc123"
}
```

#### `GET /api/sessions/{session_id}`

Get session status (and reel URL when ready). Used for polling (e.g. frontend `useSession` hook). Implemented in app session store (task 2.3).

**Response `200`:**
```json
{
  "status": "waiting",
  "reel_id": null,
  "reel_url": null
}
```

Status values: `waiting` | `live` | `processing` | `completed` | `error`. Optional fields (e.g. `duration`, `created_at`, `ended_at`) may be added later.

**Response `404`:** `{"detail": "Session not found"}`

#### `POST /api/sessions/{session_id}/end`

Ends the game session and kicks off highlight reel generation. Should call Runner’s **POST /sessions/{session_id}/close** (or DELETE) so the agent leaves the call.

**Response `200`:** `{"session_id": "abc123", "status": "processing"}`

#### `GET /api/sessions/{session_id}/token`

Issue a Stream user token for a participant (camera or spectator) joining the same call. Required because Runner does not provide tokens.

**Query:** `?role=camera|spectator`  
**Response `200`:** `{"stream_token": "eyJ...", "user_id": "camera-abc123", "call_id": "pickup-abc123"}`

#### `GET /api/reels/{reel_id}`

Get reel metadata for the viewer page.

**Response `200`:**
```json
{
  "id": "reel_xyz",
  "session_id": "abc123",
  "url": "https://storage.googleapis.com/...",
  "expires_at": "2026-02-27T14:34:05Z",
  "duration_seconds": 42,
  "highlight_count": 4,
  "created_at": "2026-02-25T14:35:20Z"
}
```

**Response `410`:**
```json
{ "detail": "Reel has expired" }
```

### 5.2 Vision Agents SDK — Agent Interface

The backend agent follows the Vision Agents SDK pattern. These are not REST endpoints but SDK interface functions.

```python
async def create_agent(**kwargs) -> Agent:
    """
    Factory called by AgentLauncher.
    Returns a configured Agent with:
      - getstream.Edge() for video transport
      - gemini.Realtime(fps=3) for vision LLM
      - elevenlabs.TTS(voice_id=CHRIS) for speech
      - roboflow.RoboflowLocalDetectionProcessor for object detection
    """

async def join_call(agent: Agent, call_type: str, call_id: str, **kwargs) -> None:
    """
    Called when the agent should join a Stream call.
    - Joins the call
    - Sends opening commentary
    - Streams continuous play-by-play until session ends
    """
```

### 5.3 Stream Video SDK — Frontend Interface

```typescript
// Creating a call (camera device)
const client = new StreamVideoClient({ apiKey, user, token });
const call = client.call(callType, callId);
await call.join({ create: true });
await call.camera.enable();

// Joining a call (spectator device)
const client = new StreamVideoClient({ apiKey, user, token });
const call = client.call(callType, callId);
await call.join();
// Audio from the agent's TTS is received automatically
```

### 5.4 Frontend → Backend Communication

The backend must allow **CORS** from the frontend origin (e.g. `http://localhost:3000`, `http://127.0.0.1:3000`) so browser requests to the API succeed. The FastAPI app uses `CORSMiddleware` with these origins in development.

| Action                    | Method | Endpoint                          | Trigger                       |
| ------------------------- | ------ | --------------------------------- | ----------------------------- |
| Start new session         | POST   | `/api/sessions`                   | User taps START               |
| Get spectator token       | GET    | `/api/sessions/{id}/token?role=spectator` | Spectator opens game URL |
| End session               | POST   | `/api/sessions/{id}/end`          | User taps END                 |
| Poll for reel             | GET    | `/api/sessions/{id}`              | Every 3s after END            |
| Load reel viewer          | GET    | `/api/reels/{id}`                 | Viewer page mount             |

### 5.5 GCS Object Layout

```
gs://hypecast-media/
├── sessions/
│   └── {session_id}/
│       ├── raw.webm              # full session recording
│       └── commentary.json       # CommentaryEntry[] log
└── reels/
    └── {reel_id}.mp4             # final highlight reel
```

Lifecycle rule: delete objects older than 48 hours.

### 5.6 Issues & caveats (from Vision Agents MCP validation)

- **Runner does not issue Stream tokens.** The spec previously implied a single “create session” response with `stream_token` and `join_url`. In reality, the Runner’s POST `/sessions` only returns `session_id`, `call_id`, `session_started_at`. Our app must expose a separate endpoint (e.g. POST `/api/session` or GET `/api/sessions/{id}/token`) that uses the Stream server-side SDK to create a user token; the frontend uses that token to create/join the call, then POSTs to Runner’s `/sessions` with the same `call_id`.
- **Session end:** Use Runner’s **POST `/sessions/{session_id}/close`** (or DELETE) when the user taps END so the agent leaves the call; our app then runs reel generation and updates app-level session state.
- **Gemini Realtime:** Default model in Vision Agents is `gemini-2.5-flash`; `fps` default is 1 — we use `fps=3`. Docs: [Gemini integration](https://visionagents.ai/integrations/gemini).
- **Roboflow local:** `RoboflowLocalDetectionProcessor` default `model_id` is `"rfdetr-seg-preview"`; we use `"rfdetr-base"`. Options include `rfdetr-nano`, `rfdetr-base`, `rfdetr-large`. No API key. Docs: [Roboflow integration](https://visionagents.ai/integrations/roboflow).
- **ElevenLabs:** Default `voice_id` in docs is `"VR6AewLTigWG4xSOukaG"`; we use Chris (`Anr9GtYh2VRXxiPplzxM`). Docs: [ElevenLabs integration](https://visionagents.ai/integrations/elevenlabs).
- **Realtime + custom TTS:** With `gemini.Realtime(fps=3)` we use ElevenLabs for TTS (custom voice). The Realtime class supports “direct audio” when the model does speech natively; for custom voices we keep the pipeline: Realtime (vision + text) → ElevenLabs TTS → Stream audio.

---

## 6. Testing Strategy

### 6.1 Backend — Python (`pytest`)

| Test Area              | What to Test                                                          | Location                              |
| ---------------------- | --------------------------------------------------------------------- | ------------------------------------- |
| **Models**             | Dataclass instantiation, enum values, defaults                         | `backend/tests/test_models.py`        |
| **Commentary Tracker** | Energy scoring from text, highlight keyword detection, threshold logic | `backend/tests/test_commentary_tracker.py` |
| **Reel Generator**     | Highlight sorting, time window overlap removal, FFmpeg command construction (mocked) | `backend/tests/test_reel_generator.py` |
| **Session Store**      | CRUD operations on in-memory dict, status transitions                 | `backend/tests/test_store.py`         |
| **API Routes**         | Request/response validation, 404/410 handling, status transitions      | `backend/tests/test_routes.py`        |

**Mocking strategy:**
- Mock `google.cloud.storage` — no real GCS calls in tests.
- Mock `ffmpeg` subprocess — validate command construction, not actual video processing.
- Mock Vision Agents SDK calls — `Agent`, `Runner`, `AgentLauncher` are tested via integration only.

**Run:** `cd backend && pytest -v`

### 6.2 Frontend — TypeScript (`vitest` + `@testing-library/react`)

| Test Area            | What to Test                                                        | Location                              |
| -------------------- | ------------------------------------------------------------------- | ------------------------------------- |
| **Device detection** | `useDeviceRole` returns `camera` when camera available, `spectator` otherwise | `frontend/src/hooks/__tests__/`      |
| **Session hook**     | `useSession` state machine: waiting → live → processing → completed | `frontend/src/hooks/__tests__/`      |
| **API client**       | `api.ts` fetch wrappers construct correct URLs and handle errors     | `frontend/src/lib/__tests__/`        |
| **Components**       | CameraView: START button, join/create + camera.enable; SpectatorView: waiting state, join as subscriber, ParticipantView when remote tracks exist | `frontend/src/components/__tests__/` |

**Mocking strategy:**
- Mock `@stream-io/video-react-sdk` — don't create real WebRTC connections.
- Mock `fetch` for API calls.
- Use `@testing-library/react` for component rendering without a browser.

**Run:** `cd frontend && pnpm test`

### 6.3 Integration Testing (Manual — Hackathon Scope)

| Scenario                            | Steps                                                                           | Expected                                    |
| ----------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------- |
| **Full loop — happy path**          | Open on phone → START → open on laptop → hear commentary → END → get reel link | Reel plays with commentary baked in         |
| **Spectator joins mid-game**        | Start game on phone → wait 30s → open on laptop                                | Commentary is already in progress            |
| **Session timeout**                 | Let game run for 5 minutes without tapping END                                  | Auto-ends with "final whistle" commentary   |
| **Camera disconnect / reconnect**   | Start game → toggle airplane mode briefly → reconnect                           | Commentary resumes after reconnection        |
| **No game visible**                 | Point camera at ceiling / wall                                                  | AI commentates whatever it sees, no crash    |
| **Reel link after 48h**             | Open a reel URL after expiry                                                    | Shows "This reel has expired" message        |
| **Unsupported browser**             | Open in Firefox on iOS                                                          | Shows "Please use Chrome or Safari" message  |

### 6.4 Performance Benchmarks

| Metric                         | Target         | How to Measure                                          |
| ------------------------------ | -------------- | ------------------------------------------------------- |
| Time from START to first audio | < 3 seconds    | Stopwatch from tap to first spoken word                  |
| Commentary continuity          | < 5s gaps      | Listen for dead air during active play                   |
| Reel generation time           | < 60 seconds   | Timestamp from END tap to reel URL available             |
| Frontend LCP                   | < 2 seconds    | Lighthouse on landing page                               |

### 6.5 Error Recovery Behavior

| Failure                        | Recovery                                                       |
| ------------------------------ | -------------------------------------------------------------- |
| Gemini API throttled           | Queue commentary, deliver delayed rather than dropping         |
| ElevenLabs API failure         | Fall back to browser `SpeechSynthesis` API                     |
| GCS upload failure             | Retry once, then offer raw video download                      |
| Stream connection dropped      | Auto-reconnect via SDK, commentary resumes on restore          |
| Reel FFmpeg crash              | Retry once, then return error status with raw video link       |

---

## Appendix A: Environment Variables

```bash
# --- Stream ---
STREAM_API_KEY=
STREAM_API_SECRET=

# --- Google ---
GOOGLE_API_KEY=                    # Gemini
GOOGLE_APPLICATION_CREDENTIALS=    # GCS service account JSON path

# --- ElevenLabs ---
ELEVENLABS_API_KEY=

# --- App ---
NEXT_PUBLIC_STREAM_API_KEY=        # exposed to frontend
NEXT_PUBLIC_API_BASE_URL=          # backend URL
```

## Appendix B: AI Commentary System Prompt

```
You are an elite ESPN sports commentator broadcasting a live game. Your job is to provide continuous, exciting play-by-play commentary of whatever game you see.

RULES:
- Be energetic, dramatic, and entertaining at all times
- Describe the action as it happens — play-by-play style
- Build excitement on rallies, close plays, and impressive moments
- Use player descriptions (jersey color, position) instead of names
- React with genuine emotion: surprise, excitement, tension
- Keep commentary flowing — minimal dead air
- When a highlight-worthy moment happens, mark it by being EXTRA enthusiastic
- Vary your energy: calm during setup, explosive during action
- Add color commentary between plays: stakes, momentum, strategy
- Never mention you are an AI. You are a broadcaster.

STYLE REFERENCE: Think Stuart Scott meets Kevin Harlan. High energy. Iconic calls.

IMPORTANT: You are watching a REAL game happening RIGHT NOW. React to what you SEE.
```

## Appendix C: MVP Scope

### Must Have
- One-tap game start from phone browser
- Live video streaming via Stream WebRTC
- Real-time Gemini-powered commentary
- ElevenLabs voice output on spectator device
- Auto-generated highlight reel (MP4 with commentary)
- Shareable 48-hour expiring link
- Clean landing page

### Nice to Have
- QR code pairing
- Roboflow detection overlay on spectator view
- Multiple spectators
- Social sharing deep links

### Out of Scope
- User accounts / login
- Game history / replay library
- Sport-specific models
- Native mobile app
- Manual highlight editing
