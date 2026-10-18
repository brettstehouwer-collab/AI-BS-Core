# Learning Proposal: Unreal Engine 5 Pixel Streaming Integration

Based on our recent debugging session, I propose persisting the critical integration logic for Unreal Engine 5 Pixel Streaming into a new **Skill**. This will ensure that any future work involving custom signaling servers or UE5 WebRTC bindings will instantly implement the correct handshake protocols and command-line flags, avoiding the silent deadlocks and `MaxListenersExceededWarning` frontend errors we encountered.

## Classification
**Type:** Skill 
**Name:** `unreal-pixel-streaming`
**Location:** Workspace (`C:\AI-BS\.agents\skills\unreal-pixel-streaming\SKILL.md`)

## Rationale
- **Handshake Deadlock:** UE 5.x explicitly expects the signaling server to proactively push a `config` ICE payload upon connection. Passively waiting for the streamer to say `{"type": "endpointId"}` causes a silent WebRTC failure.
- **Routing Corruptions:** Indiscriminate broadcasting of WebRTC offers/answers causes orphaned data chunks in the React frontend. Explicit `playerId` mappings are strictly required.
- **Launch Flags:** The shift from older IP/Port bindings to the explicit `-PixelStreamingURL` argument, alongside `-RenderOffScreen` and `-AudioMixer`, are essential for headless deployment.

---

## Proposed `SKILL.md` Content

```markdown
---
name: unreal-pixel-streaming
description: Build and manage custom WebRTC signaling servers and launch configurations for Unreal Engine 5 Pixel Streaming. Use when setting up or debugging Pixel Streaming connections, writing custom signaling logic in Python/Node, or configuring UE5 headless arguments.
---

# Unreal Engine 5 Pixel Streaming Guidelines

When building or debugging a custom WebRTC Signaling Server for UE5 Pixel Streaming, you MUST adhere to the following architecture rules to prevent silent deadlocks and frontend media chunk errors.

## 1. The Proactive "config" Handshake
In UE5, the Streamer acts passively upon establishing its WebSocket connection. The Signaling Server MUST immediately push a `config` message to the socket as soon as the connection opens. If the server waits for the Streamer to identify itself, the connection will deadlock.

**Required Initial Payload:**
```json
{
  "type": "config",
  "peerConnectionOptions": {
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
  }
}
```
Only after receiving this payload will the Streamer respond with `{"type": "endpointId", "endpointId": "Streamer"}`.

## 2. Defaulting to Streamer Connections
Since the Streamer expects the server to speak first, your connection handler should assume any incoming WebSocket on the primary port is a Streamer *until* it explicitly sends `{"type": "player"}`.

## 3. Explicit WebRTC Player Routing
When a player connects, assign them a unique `playerId` and store their socket in a map (`players_map[playerId] = socket`).
When notifying the Streamer of the new player, include the ID:
`{"type": "playerConnected", "playerId": "100", "dataChannel": true, "sfu": false}`

**CRITICAL:** When the Streamer responds with `{"type": "offer"}` or `{"type": "iceCandidate"}`, you MUST extract the `playerId` from the JSON and route the message exclusively to that specific player's socket. Broadcasting offers/answers to all clients will cause `MaxListenersExceededWarning` and orphaned `app-init-liveness` media streams in the frontend.

## 4. Headless Launch Flags
When launching Unreal Engine for Pixel Streaming via CLI, the following flags are required:
```bash
-game 
-AudioMixer 
-PixelStreamingURL=ws://127.0.0.1:8888 
-RenderOffScreen 
-RCWebControlEnable 
-RCWebInterfaceEnable 
-AllowPixelStreamingCommands 
-Windowed -ResX=1280 -ResY=720 
-stdout -FullStdOutLogOutput
```
*Note:* The `-PixelStreamingURL` argument supersedes older `-PixelStreamingIP` flags and is mandatory in UE 5.x.
```

---
**Do you approve creating this skill?** I will generate the directory and write the `SKILL.md` file into your local agents config.
