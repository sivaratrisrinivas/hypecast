# Debug: Camera join timeout & commentary WebSocket

## What you’re seeing

- **Camera tab:** `AxiosError: timeout of 5000ms exceeded` on `POST …/call/default/pickup_…/join` (Stream coordinator). Then `[Call]: Failed to join call`.
- **Spectator tab:** “Awaiting connection…” (sometimes with video anyway), “Waiting for commentary…”, and `WebSocket connection to 'ws://localhost:8000/api/ws/sessions/…/commentary' failed: WebSocket is closed before the connection is established.`
- **Backend:** Session created and polled (200), but in some runs you never see `[join_call] Session … set to LIVE` or the later SFU/track logs — i.e. the agent path doesn’t complete or is slow.

---

## 5–7 possible causes (by angle)

1. **Race: client joins before the call exists on Stream**  
   We return 201 from `POST /api/sessions` with `stream_call_id` immediately. The frontend then (a) fire-and-forget POSTs to the Runner’s `/sessions` and (b) sets state so `CameraView` runs `call.join({ create: true })`. The **call on Stream is created by the Runner** inside `join_call` when it runs `agent.create_call()`. That happens asynchronously after the Runner receives POST `/sessions`. So the client can hit “join” before the call exists → Stream coordinator can hang or timeout (e.g. 5s).

2. **Session ID / call_id mismatch**  
   If the frontend used a different `session_id` or `stream_call_id` than the backend (e.g. one with/without a leading `_`), then the client would join a different call or the commentary WS would hit a non-existent session. `secrets.token_urlsafe(9)` can produce IDs that start with `_` (e.g. `_k8-iMqwvLV3`), and the same value is used in the URL and API; so a pure encoding mismatch is less likely but possible if something normalizes the ID.

3. **Stream coordinator / network**  
   The 5s timeout is in the Stream SDK when calling the coordinator. So Stream’s backend might be slow, unreachable, or the call might not exist yet (back to race).

4. **Commentary WebSocket closed by server**  
   “Closed before the connection is established” often means the server closed the connection before the first frame. That could be an exception in our WS handler (e.g. in `commentary_hub.subscribe`) or the route not being mounted correctly.

5. **Frontend never gets a valid token or wrong API base**  
   If `NEXT_PUBLIC_API_URL` is wrong or the token request fails, the client would join with bad auth or the WS would point to the wrong host. Your logs show 200 for token and session, so this is less likely.

6. **Turbopack / workspace root**  
   Next.js warning about multiple lockfiles and inferred root could affect env or build in theory, but it doesn’t directly explain a 5s coordinator timeout or WS close.

7. **CORS / proxy**  
   OPTIONS 200 suggests CORS is fine for REST. The join request goes to Stream’s servers, not our backend, so CORS on our side is less relevant for the timeout. Could still affect WS if the browser blocks the preflight or connection.

---

## Most likely causes (narrowed down)

1. **Race: client joins before the Runner has created the call (most likely)**  
   The call is created only when `join_call` runs and calls `agent.create_call()`. The frontend gets `stream_call_id` and joins almost immediately. If the Runner hasn’t finished `create_user()` and `create_call()` yet, the call doesn’t exist on Stream and the client’s join can hang until the SDK’s 5s timeout.

2. **Commentary WS: server-side error or timing**  
   Either our handler throws (e.g. in `subscribe`) and FastAPI closes the WS, or the client connects before the backend is ready. Logs will tell.

---

## Why this matches what you see

- **Backend:** You see `[join_call] Joining call_id=pickup-…` but in some runs you never see “Session … set to LIVE” or SFU/track logs. So `join_call` starts, but either it’s slow (create_user/create_call taking time) or something fails later. Meanwhile the frontend has already tried to join and hit the 5s limit.
- **Frontend:** The timeout is on the **coordinator** request (Stream’s join), not on our backend. So the client is waiting for Stream to accept the join; if the call doesn’t exist yet, Stream can timeout.
- **Commentary:** “WebSocket is closed before the connection is established” means the TCP/WS handshake or first frame failed. That’s consistent with the server closing the connection (e.g. after an error in our code) or a proxy/env issue.

---

## What was added (logs + fix)

### 1. Diagnostic logs

- **`routes/sessions.py`**  
  - After creating the session: log `[sessions] POST /sessions → 201 session_id=… stream_call_id=…` so you know when the app returns and what ID the client will use.

- **`agent.py`**  
  - At start of `join_call`: log “Joining call_id=… (client may be waiting to join)” and record `t0`.
  - After `create_user()`: log “create_user() done in X.XXs”.
  - After `create_call()`: log “create_call() done in X.XXs — call now exists on Stream”.  
  So you can see the gap between “201 + client join” and “call exists on Stream”.

- **`routes/commentary_ws.py`**  
  - On connection: log “Client connecting for session_id=…”.
  - After accept and subscribe: log “Subscribed session_id=…”.
  - On accept/subscribe failure: log warning with exception.  
  So you can see if the WS is reached and where it fails.

### 2. Fix for the join timeout (race)

- **`frontend/src/components/game/CameraView.tsx`**  
  - Added a **2.5s delay** after `ensureDeviceListPopulated()` and before `call.join({ create: true })`.  
  - So the Runner has time to run `create_user()` and `create_call()` before the client joins.  
  - “Connecting…” will show for ~2.5s then the actual join runs; if the backend is slow, you can increase `JOIN_DELAY_MS` (e.g. to 4000).

### 3. Commentary WebSocket

- No change to the protocol. If the new logs show “Client connecting” but “subscribe() failed” or no “Subscribed”, the next step is to fix the failing part (e.g. `commentary_hub` or session lookup). If the client never reaches the backend, the issue is URL, CORS, or proxy.

---

## How to verify

1. Restart backend and frontend.
2. Open camera tab, tap START.
3. In the backend log you should see (order may vary):
   - `[sessions] POST /sessions → 201 session_id=… stream_call_id=…`
   - `[join_call] Joining call_id=…`
   - `[join_call] create_user() done in X.XXs`
   - `[join_call] create_call() done in X.XXs — call now exists on Stream`
   - Then SFU/track logs and “Session … set to LIVE”.
4. On the frontend, “Connecting…” should last ~2.5s then switch to “Streaming” (no coordinator timeout).
5. Open the spectator URL; in the backend you should see `[commentary_ws] Client connecting for session_id=…` and “Subscribed …”. If you see “subscribe() failed” or no “Subscribed”, use that to fix the commentary path.

---

## Session ID 0/O confusion (commentary WS "closed before connection established")

If the spectator URL or QR code has a wrong character (e.g. **0** instead of **O** in `ObetJvVC01ss`), the frontend will open `/game/0betJvVC01ss` and connect the commentary WebSocket to `.../sessions/0betJvVC01ss/commentary`. The backend only has a session `ObetJvVC01ss`, so that WS might fail or connect to an empty channel. **Fix:** Session IDs are now generated from an alphabet that excludes ambiguous characters (`0`, `O`, `1`, `I`, `l`) so QR codes and copy-paste are reliable (`routes.sessions._generate_session_id`).

## No commentary (agent leaves before spectator joins)

If the agent logs "Waiting for other participants to join" and then "Stopping the agent" within a few seconds, it has left the call before the spectator (or sometimes the camera) is fully registered. The spectator then connects to an empty call and the commentary WebSocket has no one publishing. **Fix:** We wait 5 seconds after joining before calling `simple_response(...)` so the camera (and optionally the spectator) can register as participants; then we start the LLM. Also open the spectator URL soon after START so the agent sees two participants and is less likely to exit.

## Stream "Health check failed" / agent stopping

Logs may show `WARNING: Health check failed, closing connection` and then the agent leaving the call. That is the Stream SFU closing the connection (e.g. timeout or network). Once the agent has left, the session is no longer LIVE and the spectator will see "Awaiting connection" and get no commentary. **Mitigation:** Have the spectator join soon after the camera; if the agent has already left, start a new session. The cascade of errors (`RuntimeError: cannot join current thread`, `AttributeError: localDescription`, `InvalidStateError: RTCIceTransport is closed`) are cleanup artifacts after the connection is torn down.

---

## Longer-term improvement

The delay is a workaround. A cleaner approach is to **create the call on Stream from our backend** when we create the session (e.g. in `POST /api/sessions`), before returning 201, using the Stream server-side SDK (e.g. `client.video.call(...).get_or_create(...)`). Then the call already exists when the client joins and the Runner’s `join_call` only joins that call. That removes the race without a frontend delay.
