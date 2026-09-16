import asyncio
import json
import logging
import random
import time
import os
import aiohttp
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] SocialDaemon: %(message)s")

app = FastAPI(title="AI-BS Social & Sidekick Daemon")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_FILE = "C:/AI-BS/backend/twitch_config.json"

class TwitchState:
    def __init__(self):
        self.client_id: str = ""
        self.client_secret: str = ""
        self.channel_name: str = "brettstehouwer"
        self.bot_username: str = "AI-BS_Sidekick"
        self.access_token: str = ""
        self.refresh_token: str = ""
        self.is_connected: bool = False
        self.irc_ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.client_id = data.get("client_id", "")
                    self.client_secret = data.get("client_secret", "")
                    self.channel_name = data.get("channel_name", "brettstehouwer")
                    self.bot_username = data.get("bot_username", "AI-BS_Sidekick")
                    self.access_token = data.get("access_token", "")
                    self.refresh_token = data.get("refresh_token", "")
            except Exception as e:
                logging.warn(f"Failed to load twitch config: {e}")

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "channel_name": self.channel_name,
                    "bot_username": self.bot_username,
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token
                }, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save twitch config: {e}")

twitch_state = TwitchState()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"Client connected to social feed. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logging.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        dead_connections = []
        msg_str = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(msg_str)
            except Exception:
                dead_connections.append(connection)
        
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

# --- Sidekick AI Logic ---
async def ask_sidekick(prompt: str, context_user: str, intent: str = "general") -> str:
    system_prompt = (
        f"You are 'Sidekick', a helpful, witty and highly energetic AI co-host for Brett Stehouwer's livestream. "
        f"Answer the viewer named {context_user}. Keep your answers concise, engaging, and gaming-focused (1-2 sentences maximum)."
    )
    
    if intent == "joke":
        system_prompt += " Tell a hilarious, short gaming or streaming joke."
    elif intent == "hype":
        system_prompt += " ACT AS AN EXTREME HYPE-MAN! USE ALL CAPS, EXCITEMENT, AND TELL EVERYONE TO DROP A FOLLOW AND CLIP THE PLAY!"
    elif intent == "sentiment":
        system_prompt += " Summarize the current mood and energy of the chat room in a fun way."
        
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama3.2",
                "prompt": system_prompt + "\nViewer message: " + prompt,
                "stream": False,
                "options": {"num_ctx": 2048, "temperature": 0.8}
            }
            async with session.post("http://127.0.0.1:11435/api/generate", json=payload, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "").strip()
    except Exception as e:
        logging.debug(f"Sidekick LLM local endpoint check: {e}")
        # Fallback offline Sidekick witty responses if local model is busy
        if intent == "joke":
            return "Why do gamers love elevators? Because they're great on so many levels! 🎮"
        elif intent == "hype":
            return "🔥 CHAT WE ARE GOING CRAZY! DROP THOSE FOLLOWS AND LET'S WIN THIS MATCH! LETS GOOOOO! 🔥"
        elif intent == "sentiment":
            return "The chat energy is at 100% pure hype right now! 🚀"
        return f"Hey @{context_user}, Sidekick co-host active! Ready for high-FPS action!"
    return ""

async def send_twitch_irc_message(channel: str, text: str):
    if twitch_state.irc_ws and not twitch_state.irc_ws.closed:
        try:
            clean_ch = channel.lstrip('#').lower()
            await twitch_state.irc_ws.send_str(f"PRIVMSG #{clean_ch} :{text}\r\n")
            logging.info(f"Sidekick sent to Twitch IRC (#{clean_ch}): {text}")
        except Exception as e:
            logging.error(f"Failed to send message to Twitch IRC: {e}")

async def process_message_for_sidekick(msg: dict):
    if msg.get("type") != "chat":
        return
        
    text = msg.get("message", "")
    username = msg.get("username", "")
    platform = msg.get("platform", "twitch")
    
    # Toxicity & Spam filter
    toxic_words = ["hate", "spam_link", "idiot", "slur", "scam"]
    if any(word in text.lower() for word in toxic_words):
        alert = {
            "type": "alert",
            "platform": platform,
            "event": "timeout",
            "username": "Sidekick",
            "message": f"🚨 Auto-Mod: {username} was timed out for inappropriate language.",
            "timestamp": int(time.time() * 1000)
        }
        await manager.broadcast(alert)
        return

    # --- Autonomous Lexicon Sentiment & Theatrical Reflex ---
    try:
        from core.lexicon_service import LexiconService
        expansion = LexiconService.bulk_expand(text)
        if expansion:
            agg_keywords = {"angry", "rage", "mad", "furious", "aggressive", "destroy", "kill", "fight", "attack", "brutal"}
            hype_keywords = {"hype", "excited", "awesome", "amazing", "epic", "legendary", "win", "victory", "pog", "poggers", "letsgo"}
            calm_keywords = {"calm", "peace", "quiet", "relax", "chill", "steady", "breathe", "gentle", "lull"}
            analytical_keywords = {"analyze", "data", "metrics", "logic", "reason", "system", "stats", "strat", "strategy"}

            expanded_words = set(expansion.keys())
            for v in expansion.values():
                expanded_words.update(set(v))
            expanded_words_lower = {w.lower() for w in expanded_words}

            theme_reflex = None
            if expanded_words_lower.intersection(hype_keywords):
                theme_reflex = "hype"
            elif expanded_words_lower.intersection(agg_keywords):
                theme_reflex = "aggressive"
            elif expanded_words_lower.intersection(analytical_keywords):
                theme_reflex = "analytical"
            elif expanded_words_lower.intersection(calm_keywords):
                theme_reflex = "calm"

            if theme_reflex:
                logging.info(f"[Social Reflex] Chat sentiment triggered theme '{theme_reflex}' from @{username}: '{text}'")
                async with aiohttp.ClientSession() as session:
                    # 1. Trigger OBS camera/scene cut
                    asyncio.create_task(session.post("http://127.0.0.1:8005/obs/trigger-theme", json={"theme": theme_reflex}, timeout=1.5))
                    # 2. Modulate VST3 audio DSP / synth parameters
                    asyncio.create_task(session.post("http://127.0.0.1:8013/api/vst/trigger-theme", json={"theme": theme_reflex}, timeout=1.5))
                    # 3. Trigger Unreal Engine 5 DMX lighting & camera
                    asyncio.create_task(session.post("http://127.0.0.1:8080/api/unreal/theatrical/stage-trigger", json={"theme": theme_reflex}, timeout=1.5))

                reflex_alert = {
                    "type": "alert",
                    "platform": platform,
                    "event": "theatrical_reflex",
                    "username": "AI-BS Theatrical Matrix",
                    "message": f"🎬 Audience reflex activated '{theme_reflex.upper()}' staging from @{username}!",
                    "timestamp": int(time.time() * 1000)
                }
                await manager.broadcast(reflex_alert)
    except Exception as e:
        logging.debug(f"Lexicon social reflex check: {e}")

    # Intent classification
    intent = "general"
    lower_text = text.lower()
    if "joke" in lower_text or "!joke" in lower_text:
        intent = "joke"
    elif "hype" in lower_text or "!hype" in lower_text:
        intent = "hype"
    elif "sentiment" in lower_text or "how is chat" in lower_text:
        intent = "sentiment"

    is_question = "?" in text and len(text.split()) > 2
    is_mention = "sidekick" in lower_text or "!sidekick" in lower_text or "@sidekick" in lower_text or "!ai" in lower_text
    
    if (is_question and random.random() < 0.4) or is_mention or intent != "general":
        await asyncio.sleep(1)
        response = await ask_sidekick(text, username, intent)
        
        if response:
            reply_msg = {
                "type": "chat",
                "platform": platform,
                "username": "🤖 Sidekick",
                "message": f"@{username} {response}",
                "timestamp": int(time.time() * 1000),
                "color": "#eab308"
            }
            await manager.broadcast(reply_msg)
            
            # If from Twitch, write directly back to the live Twitch room!
            if platform == "twitch" and twitch_state.is_connected:
                await send_twitch_irc_message(twitch_state.channel_name, f"@{username} {response}")

# --- Twitch IRC Real-Time WebSocket Task ---
async def twitch_irc_listener():
    while True:
        if not twitch_state.access_token or not twitch_state.channel_name:
            await asyncio.sleep(5)
            continue

        try:
            logging.info(f"Connecting to Twitch IRC WebSocket for #{twitch_state.channel_name}...")
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect("wss://irc-ws.chat.twitch.tv:443") as ws:
                    twitch_state.irc_ws = ws
                    twitch_state.is_connected = True
                    
                    # Authenticate IRC session
                    token = twitch_state.access_token.replace("oauth:", "")
                    await ws.send_str(f"PASS oauth:{token}\r\n")
                    nick = twitch_state.bot_username or "justinfan12345"
                    await ws.send_str(f"NICK {nick}\r\n")
                    clean_ch = twitch_state.channel_name.lstrip('#').lower()
                    await ws.send_str(f"JOIN #{clean_ch}\r\n")
                    
                    logging.info(f"Successfully joined Twitch chat: #{clean_ch}")

                    welcome_alert = {
                        "type": "alert",
                        "platform": "twitch",
                        "event": "connected",
                        "username": "System",
                        "message": f"Connected to Live Twitch Chat: #{clean_ch}",
                        "timestamp": int(time.time() * 1000)
                    }
                    await manager.broadcast(welcome_alert)

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            raw = msg.data.strip()
                            if raw.startswith("PING"):
                                await ws.send_str("PONG :tmi.twitch.tv\r\n")
                                continue
                                
                            if "PRIVMSG" in raw:
                                try:
                                    # Format: :username!username@username.tmi.twitch.tv PRIVMSG #channel :message
                                    user = raw.split("!", 1)[0].lstrip(":")
                                    parts = raw.split(f"PRIVMSG #{clean_ch} :", 1)
                                    if len(parts) > 1:
                                        content = parts[1]
                                        chat_entry = {
                                            "type": "chat",
                                            "platform": "twitch",
                                            "username": user,
                                            "message": content,
                                            "timestamp": int(time.time() * 1000),
                                            "color": f"#{abs(hash(user)) % 0xFFFFFF:06x}"
                                        }
                                        await manager.broadcast(chat_entry)
                                        asyncio.create_task(process_message_for_sidekick(chat_entry))
                                except Exception as parse_e:
                                    logging.debug(f"IRC parse note: {parse_e}")
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
        except Exception as e:
            logging.warn(f"Twitch IRC connection dropped: {e}. Retrying in 5s...")
        finally:
            twitch_state.is_connected = False
            twitch_state.irc_ws = None
            await asyncio.sleep(5)

# --- Fallback Simulation Loop for Standby & Testing ---
async def simulate_chat():
    platforms = ["twitch", "youtube", "kick", "facebook"]
    users = ["Brett", "Sean", "ProGamer_X", "AudioTech99", "LiveViewer", "BeatMaster"]
    messages = [
        "60 FPS looks so clean!",
        "DAW stems sounding fire! 🔥",
        "Hey Sidekick tell me a joke",
        "hype in the chat!",
        "what game is this?",
        "Audio mixing is dialed in",
        "W stream Brett!",
        "Can Sidekick read the chat sentiment?"
    ]
    
    while True:
        await asyncio.sleep(random.uniform(4.0, 10.0))
        # If live Twitch is NOT connected, generate occasional simulated interactions
        if manager.active_connections and not twitch_state.is_connected:
            platform = random.choice(platforms)
            user = random.choice(users)
            text = random.choice(messages)
            
            msg = {
                "type": "chat",
                "platform": platform,
                "username": user,
                "message": text,
                "timestamp": int(time.time() * 1000),
                "color": f"#{abs(hash(user)) % 0xFFFFFF:06x}"
            }
            await manager.broadcast(msg)
            asyncio.create_task(process_message_for_sidekick(msg))

# --- Twitch OAuth Endpoints ---
@app.get("/auth/twitch/login")
async def twitch_login():
    if not twitch_state.client_id:
        return HTMLResponse("<h3>Please configure Twitch Client ID in Broadcast Studio Settings first.</h3>", status_code=400)
    redirect_uri = "http://localhost:8006/auth/twitch/callback"
    scopes = "chat:read+chat:edit+whispers:read+whispers:edit+channel:moderate"
    auth_url = f"https://id.twitch.tv/oauth2/authorize?client_id={twitch_state.client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}"
    return RedirectResponse(auth_url)

@app.get("/auth/twitch/callback")
async def twitch_callback(code: str = Query(None), error: str = Query(None)):
    if error or not code:
        return HTMLResponse(f"<h3>Twitch Authorization Failed: {error or 'No code provided'}</h3>", status_code=400)
        
    redirect_uri = "http://localhost:8006/auth/twitch/callback"
    token_url = "https://id.twitch.tv/oauth2/token"
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "client_id": twitch_state.client_id,
                "client_secret": twitch_state.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
            async with session.post(token_url, data=payload) as resp:
                data = await resp.json()
                if "access_token" in data:
                    twitch_state.access_token = data["access_token"]
                    twitch_state.refresh_token = data.get("refresh_token", "")
                    twitch_state.save_config()
                    return HTMLResponse("""
                        <html>
                        <body style="background:#090d16;color:#38bdf8;font-family:sans-serif;text-align:center;padding:50px;">
                            <h2>✅ Twitch Connected Successfully!</h2>
                            <p style="color:#94a3b8;">AI-BS Sidekick is now connected to your live Twitch chat room.</p>
                            <script>setTimeout(() => window.close(), 2500);</script>
                        </body>
                        </html>
                    """)
                else:
                    return JSONResponse(data, status_code=400)
    except Exception as e:
        return HTMLResponse(f"<h3>OAuth exchange error: {e}</h3>", status_code=500)

@app.post("/config/twitch")
async def update_twitch_config(req: Request):
    body = await req.json()
    twitch_state.client_id = body.get("client_id", twitch_state.client_id)
    twitch_state.client_secret = body.get("client_secret", twitch_state.client_secret)
    twitch_state.channel_name = body.get("channel_name", twitch_state.channel_name)
    twitch_state.bot_username = body.get("bot_username", twitch_state.bot_username)
    if "access_token" in body:
        twitch_state.access_token = body["access_token"]
    twitch_state.save_config()
    return {"status": "ok", "channel": twitch_state.channel_name, "connected": twitch_state.is_connected}

@app.get("/config/twitch")
async def get_twitch_config():
    return {
        "client_id": twitch_state.client_id,
        "channel_name": twitch_state.channel_name,
        "bot_username": twitch_state.bot_username,
        "has_token": bool(twitch_state.access_token),
        "is_connected": twitch_state.is_connected
    }

@app.get("/api/social/status")
@app.get("/status")
async def get_social_status():
    return {
        "status": "online",
        "service": "AI-BS Social & Sidekick Daemon",
        "channel": twitch_state.channel_name,
        "bot_username": twitch_state.bot_username,
        "is_connected": twitch_state.is_connected,
        "has_token": bool(twitch_state.access_token),
        "active_clients": len(manager.active_connections)
    }

@app.get("/stream/verify/twitch")
async def verify_twitch_stream():
    if not twitch_state.client_id or not twitch_state.access_token:
        return {
            "live": False,
            "channel": twitch_state.channel_name,
            "verified": False,
            "message": "Twitch OAuth not connected. Connect in Stream Settings to enable Helix API verification."
        }
    try:
        url = f"https://api.twitch.tv/helix/streams?user_login={twitch_state.channel_name}"
        headers = {
            "Client-Id": twitch_state.client_id,
            "Authorization": f"Bearer {twitch_state.access_token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stream_list = data.get("data", [])
                    if stream_list:
                        s = stream_list[0]
                        return {
                            "live": True,
                            "verified": True,
                            "channel": twitch_state.channel_name,
                            "title": s.get("title", ""),
                            "game_name": s.get("game_name", ""),
                            "viewer_count": s.get("viewer_count", 0),
                            "started_at": s.get("started_at", "")
                        }
                    else:
                        return {
                            "live": False,
                            "verified": True,
                            "channel": twitch_state.channel_name,
                            "message": f"Twitch reports channel '{twitch_state.channel_name}' is currently offline or synchronizing."
                        }
                else:
                    err = await resp.text()
                    return {"live": False, "verified": False, "channel": twitch_state.channel_name, "message": f"Helix API HTTP {resp.status}"}
    except Exception as e:
        return {"live": False, "verified": False, "channel": twitch_state.channel_name, "message": str(e)}

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(twitch_irc_listener())
    asyncio.create_task(simulate_chat())
    logging.info("Social Daemon Started. Twitch IRC & Sidekick Co-Host ready.")

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                if data.get("action") == "send_chat":
                    msg_text = data.get("message", "")
                    # Broadcast to local UI
                    local_msg = {
                        "type": "chat",
                        "platform": data.get("platform", "broadcast"),
                        "username": data.get("username", "Admin (You)"),
                        "message": msg_text,
                        "timestamp": int(time.time() * 1000),
                        "color": "#38bdf8"
                    }
                    await manager.broadcast(local_msg)
                    # Forward to live Twitch IRC
                    if twitch_state.is_connected:
                        await send_twitch_irc_message(twitch_state.channel_name, msg_text)
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    logging.info("Starting AI-BS Social Daemon on port 8006...")
    uvicorn.run(app, host="127.0.0.1", port=8006)
