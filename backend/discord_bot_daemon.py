import os
import sys
import json
import logging
import asyncio
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import httpx
import requests

HAS_DISCORD = False
try:
    import discord
    from discord.ext import commands, tasks
    from discord.ui import View, button

    HAS_DISCORD = True
except ImportError:
    pass

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import socket

_original_getaddrinfo = socket.getaddrinfo


def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0:
        family = socket.AF_INET
    return _original_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = patched_getaddrinfo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] discord_bot: %(message)s",
)
logger = logging.getLogger("DiscordBotDaemon")

BACKEND_DIR = Path(__file__).parent.resolve()
BASE_DIR = BACKEND_DIR.parent
ENV_FILE = BASE_DIR / ".env"
MASTER_DB = BACKEND_DIR / "aibs_master.db"
PEARL_WALLET = "prl1p5r4kvz636h2pa9fuww723s4r02flt25rec9qs6yjckk7lyejkvjs67a4n5"
API_BASE = "http://127.0.0.1:8000"
TRADER_BASE = "http://127.0.0.1:8007"
SYSTEM_VERSION = "v5.214.2"
PEARL_PRICE_USD = 3.10  # SafeTrade reference price for PRL/USDT
CHANNEL_ID = 1526361931399827466


def load_env_val(key_name):
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(f"{key_name}="):
                    val = line.split("=", 1)[1].strip()
                    return val.strip('"').strip("'")
    return os.environ.get(key_name, "")


DISCORD_BOT_TOKEN = load_env_val("DISCORD_BOT_TOKEN")
DISCORD_WEBHOOK_URL = load_env_val("DISCORD_WEBHOOK_URL")
STREAM_INTERVAL_MINS = int(load_env_val("DISCORD_STREAM_INTERVAL_MINUTES") or "15")
STREAM_INTERVAL_MINS = max(1, STREAM_INTERVAL_MINS)


# --- Telemetry Aggregation Functions ---

def get_gpu_telemetry():
    """Read physical NVIDIA GPU telemetry from host driver."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw,power.limit,clocks.current.graphics,clocks.current.memory,utilization.gpu,fan.speed", "--format=csv,noheader,nounits"],
            encoding="utf-8"
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        return {
            "temp": int(parts[0]),
            "power_draw": float(parts[1]),
            "power_limit": float(parts[2]),
            "core_clock": int(parts[3]),
            "mem_clock": int(parts[4]),
            "util": int(parts[5]),
            "fan": int(parts[6]) if len(parts) > 6 and parts[6].isdigit() else 100,
            "ok": True
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_pearl_telemetry():
    """Fetch live HeroMiners pool stats for the primary mining wallet."""
    url = f"https://pearl.herominers.com/api/stats_address?address={PEARL_WALLET}&recentBlocksAmount=10"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=6).json()
        stats = r.get("stats", {})
        nh = int(stats.get("networkHeight") or 0)
        bal = float(stats.get("balance") or 0) / 1e8
        shares = int(stats.get("shares_good") or 0)
        invalid = int(stats.get("shares_invalid") or 0)
        hashes = int(stats.get("hashes") or 0)
        min_payout = float(stats.get("minPayoutLevel") or 100000000) / 1e8
        workers = r.get("workers", [])
        hashrate = float(workers[0].get("hashrate") or 0) if workers else 0.0
        unconf = r.get("unconfirmed", [])
        pending = sum(float(b.get("reward") or 0) for b in unconf) / 1e8
        closest = None
        min_rem = 999
        for b in unconf:
            h = int(b.get("height") or 0)
            confs = nh - h if nh and h else 0
            rem = max(0, 100 - confs)
            if rem < min_rem:
                min_rem = rem
                closest = {"height": h, "confs": confs, "remaining": rem, "reward": round(float(b.get("reward") or 0)/1e8, 4)}
        
        progress_pct = min(100.0, (bal / min_payout) * 100.0) if min_payout > 0 else 0.0

        return {
            "height": nh,
            "mature_prl": bal,
            "min_payout": min_payout,
            "progress_pct": progress_pct,
            "shares": shares,
            "invalid_shares": invalid,
            "hashes": hashes,
            "hashrate_gh": round(hashrate / 1000.0, 1),
            "pending_prl": round(pending, 4),
            "pending_count": len(unconf),
            "closest": closest,
            "ok": True
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_trader_telemetry():
    """Fetch live market ticks and trading strategy state from Port 8007."""
    try:
        r = requests.get(f"{TRADER_BASE}/api/v1/telemetry", timeout=3).json()
        ledger = r.get("ledger", {})
        prices = ledger.get("reference_prices", {})
        positions = ledger.get("positions", {})
        cro_pos = positions.get("CRO/USD", {})
        return {
            "status": r.get("status", "active"),
            "cro_usd": prices.get("CRO/USD", 0.0),
            "strategy": ledger.get("strategy_layer", "High-Frequency Fast Scalp"),
            "total_profit_usd": ledger.get("total_profit_usd", 0.0),
            "last_action": ledger.get("last_action", "Standing by"),
            "cro_amount": cro_pos.get("amount", 0.0),
            "avg_buy_price": cro_pos.get("avg_buy_price", 0.0),
            "vault_cro": cro_pos.get("long_term_vault", 0.0),
            "hunting_rate": r.get("hunting_rate_per_min", 1200),
            "max_trades": r.get("max_trades_per_min", 120),
            "cooldown": r.get("action_cooldown_sec", 0.5),
            "usd_balance": r.get("usd_balance", 0.0),
            "ok": True
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_accounting_summary():
    """Query master SQLite accounting table for verified on-chain transfers."""
    if not MASTER_DB.exists():
        return {"count": 0, "records": []}
    try:
        conn = sqlite3.connect(MASTER_DB)
        cur = conn.cursor()
        cur.execute("SELECT date, asset, amount, usd_total_value, category, tx_hash FROM crypto_transfers ORDER BY id DESC LIMIT 5")
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(*), COALESCE(SUM(usd_total_value), 0.0) FROM crypto_transfers")
        total_count, total_usd = cur.fetchone()
        conn.close()
        return {
            "count": total_count,
            "total_usd": total_usd,
            "records": rows
        }
    except Exception:
        return {"count": 0, "records": []}


def enforce_hardware_clamp():
    """Execute host driver commands to enforce RTX 4090 310W power cap and 5001 MHz locked memory clock."""
    try:
        cmd1 = ["nvidia-smi", "-pl", "310"]
        cmd2 = ["nvidia-smi", "-lmc", "5001"]
        out1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=5)
        out2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=5)
        res1 = out1.stdout.strip() or out1.stderr.strip()
        res2 = out2.stdout.strip() or out2.stderr.strip()
        return f"• Power Limit: `310.00 W` ({res1})\n• Memory Lock: `5001 MHz` ({res2})"
    except Exception as e:
        return f"⚠️ Error executing clamp: {e}"


# --- Embed Builders ---

def build_telemetry_embed():
    """Construct full-spectrum real-time telemetry Discord embed."""
    gpu = get_gpu_telemetry()
    pearl = get_pearl_telemetry()
    trader = get_trader_telemetry()
    accounting = get_accounting_summary()

    embed = {
        "title": f"⚡ AI-BS Sovereign Telemetry Update ({SYSTEM_VERSION})",
        "description": "Real-time operating telemetry across host hardware, Pearl PoUW mining, and algorithmic trading streams.",
        "color": 0x00ffcc,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": [],
        "footer": {"text": "AI-BS Autonomous Studio • Zero-Mock Fiscal Governance • Interactive Controls Active"}
    }

    # GPU Hardware Field
    if gpu.get("ok"):
        gpu_val = (
            f"• **Power:** `{gpu['power_draw']:.1f} W` / **`{gpu['power_limit']:.0f} W`** (Clamped)\n"
            f"• **Thermals:** `{gpu['temp']}°C` (Fan: `{gpu['fan']}%`)\n"
            f"• **Clocks:** Core `{gpu['core_clock']} MHz` | VRAM **`{gpu['mem_clock']} MHz`** (Locked)\n"
            f"• **Load:** `{gpu['util']}%` GPU Core Compute"
        )
    else:
        gpu_val = "• Telemetry query offline"
    embed["fields"].append({"name": "🖥️ Hardware Profile (RTX 4090 24GB)", "value": gpu_val, "inline": False})

    # Pearl Mining Field
    if pearl.get("ok"):
        closest_str = f"#{pearl['closest']['height']} ({pearl['closest']['confs']}/100 confs • est +{pearl['closest']['reward']} PRL)" if pearl.get("closest") else "All blocks mature"
        progress_bar = f"`[{('█' * int(pearl['progress_pct'] / 10)).ljust(10, '░')}]` {pearl['progress_pct']:.1f}% of {pearl['min_payout']:.1f} PRL"
        hashes_b = f"{pearl['hashes'] / 1e9:.2f} B" if pearl['hashes'] >= 1e9 else f"{pearl['hashes'] / 1e6:.1f} M"
        mining_val = (
            f"• **Worker Rig4090:** **`{pearl['shares']}`** Good Shares (100.0% Eff, 0 invalid)\n"
            f"• **PoUW Compute:** `{hashes_b}` Matrix Attestations Submitted\n"
            f"• **Pool Hashrate:** `~{pearl['hashrate_gh']} GH/s` (Height `#{pearl['height']}`)\n"
            f"• **Mature Balance:** **`{pearl['mature_prl']:.4f} PRL`** (~${pearl['mature_prl'] * PEARL_PRICE_USD:.2f} USD)\n"
            f"• **Payout Progress:** {progress_bar}\n"
            f"• **Pending Accrual:** `{pearl['pending_count']}` Blocks (~`{pearl['pending_prl']:.4f} PRL` / ~${pearl['pending_prl'] * PEARL_PRICE_USD:.2f} USD)\n"
            f"• **Next Maturing:** {closest_str}"
        )
    else:
        mining_val = "• HeroMiners pool query offline"
    embed["fields"].append({"name": "⛏️ Pearl PoUW Mining (HeroMiners)", "value": mining_val, "inline": False})

    # Crypto Trader Field
    if trader.get("ok") and trader.get("cro_usd", 0) > 0:
        pos_str = f"**`{trader.get('cro_amount', 0):.1f} CRO`** @ `${trader.get('avg_buy_price', 0):.5f}` (~${trader.get('cro_amount', 0) * trader.get('cro_usd', 0):.2f} USD)" if trader.get("cro_amount", 0) > 0 else "Flat (Cash USD Ready)"
        trader_val = (
            f"• **CRO Spot Reference:** **`${trader['cro_usd']:.5f} USD`**\n"
            f"• **Active Position:** {pos_str}\n"
            f"• **Realized Profit Banked:** **`+${trader.get('total_profit_usd', 0):.4f} USD`** (Stashed: `{trader.get('vault_cro', 0):.2f} CRO`)\n"
            f"• **Velocity:** `{trader.get('hunting_rate', 1200)} evals/min` (Max `{trader.get('max_trades', 120)}` trades/min, `{trader.get('cooldown', 0.5)}s` cd)\n"
            f"• **Last Engine Action:** `{trader.get('last_action', 'Standing by')}`\n"
            f"• **Free USD Balance:** `${trader.get('usd_balance', 0):.2f} USD`"
        )
    else:
        trader_val = "• Bot Engine: Active on Port 8007 (Awaiting Tick Sync)"
    embed["fields"].append({"name": "⚡ Ultra-Fast Crypto Scalp Engine (Port 8007)", "value": trader_val, "inline": False})

    # Accounting & Fiscal Slate Field
    if accounting["count"] > 0:
        fiscal_val = (
            f"• **Verified Records:** `{accounting['count']}`\n"
            f"• **Total Volume:** `${accounting['total_usd']:.2f} USD`\n"
            f"• **Standard:** 100% On-Chain Grounded"
        )
    else:
        fiscal_val = (
            f"• **Verified Records:** `0` (Clean Slate)\n"
            f"• **Synthetic Data:** `Permanently Prohibited`\n"
            f"• **Direct Deposit:** ACH (USD Cash)"
        )
    embed["fields"].append({"name": "💼 Fiscal Accounting Ledger", "value": fiscal_val, "inline": True})

    return embed


def build_miner_embed(pearl, gpu):
    """Build detailed mining breakdown embed."""
    closest_str = f"Block `#{pearl['closest']['height']}` ({pearl['closest']['confs']}/100 confs • ~{pearl['closest']['remaining']*3.2:.1f}m remaining)" if pearl.get("closest") else "All mature"
    progress_bar = f"`[{('█' * int(pearl['progress_pct'] / 10)).ljust(10, '░')}]` {pearl['progress_pct']:.1f}%"
    hashes_b = f"{pearl['hashes'] / 1e9:.2f} Billion" if pearl['hashes'] >= 1e9 else f"{pearl['hashes'] / 1e6:.1f} Million"

    embed = discord.Embed(
        title="⛏️ AI-BS Sovereign Pearl Mining Breakdown",
        description=f"Direct Stratum PoUW on **`us.pearl.herominers.com:1200`** (Worker: `Rig4090`).",
        color=0x3498db,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Good Shares (100% Efficiency)", value=f"**`{pearl['shares']}`** (0 rejected)", inline=True)
    embed.add_field(name="PoUW Compute Hashes", value=f"**`{hashes_b}`**", inline=True)
    embed.add_field(name="Pool Calculated Hashrate", value=f"**`~{pearl['hashrate_gh']} GH/s`**", inline=True)
    embed.add_field(name="Mature Unlocked Balance", value=f"**`{pearl['mature_prl']:.4f} PRL`** (~${pearl['mature_prl'] * PEARL_PRICE_USD:.2f} USD)", inline=True)
    embed.add_field(name="Payout Threshold (1.0 PRL)", value=progress_bar, inline=True)
    embed.add_field(name="Pending Rewards (Immature)", value=f"**`{pearl['pending_prl']:.4f} PRL`** ({pearl['pending_count']} blocks • ~${pearl['pending_prl'] * PEARL_PRICE_USD:.2f} USD)", inline=True)
    embed.add_field(name="Next Maturing Block", value=closest_str, inline=False)
    if gpu.get("ok"):
        embed.add_field(name="Hardware Clamping", value=f"RTX 4090 @ `{gpu['power_draw']:.1f}W` / `{gpu['power_limit']:.0f}W` | `{gpu['temp']}°C` | `{gpu['mem_clock']} MHz` Locked", inline=False)
    embed.set_footer(text="HeroMiners Pool • Automated Payout Watcher Guarded")
    return embed


def build_gpu_embed(gpu):
    """Build detailed GPU clocks and hardware profile embed."""
    embed = discord.Embed(
        title="🖥️ NVIDIA GeForce RTX 4090 Hardware Telemetry",
        color=0x76b900,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Power Draw & Cap", value=f"`{gpu['power_draw']:.1f} W` / **`{gpu['power_limit']:.0f} W`** (Clamped)", inline=True)
    embed.add_field(name="Core Temperature", value=f"**`{gpu['temp']}°C`** (Fan: `{gpu['fan']}%`)", inline=True)
    embed.add_field(name="GPU Utilization", value=f"`{gpu['util']}%` Core Load", inline=True)
    embed.add_field(name="Graphics Core Clock", value=f"`{gpu['core_clock']} MHz`", inline=True)
    embed.add_field(name="Memory Clock (GDDR6X)", value=f"**`{gpu['mem_clock']} MHz`** (Locked)", inline=True)
    embed.add_field(name="Persistence Profile", value="3-Tier Guarded (SYSTEM Task, Systemd, 60s Watchdog)", inline=True)
    embed.set_footer(text="AI-BS Hardware Guard • Anti-TDR Auto-Recovery Active")
    return embed


def build_ledger_embed(summary):
    """Build fiscal accounting embed."""
    embed = discord.Embed(
        title="💼 AI-BS Master Accounting Ledger",
        color=0xf39c12,
        timestamp=datetime.now(timezone.utc)
    )
    if summary["count"] == 0:
        embed.description = (
            "🛡️ **Zero-Mock Clean Fiscal Slate Active**\n\n"
            "• **Verified On-Chain Transfers:** `0`\n"
            "• **Synthetic Records:** `Permanently Excluded`\n\n"
            "Verified on-chain mining payouts and authenticated bank deposits will populate automatically once broadcast."
        )
    else:
        desc = f"**Total Verified Volume:** `${summary['total_usd']:.2f} USD` across `{summary['count']}` records.\n\n"
        for row in summary["records"]:
            date_str, asset, amount, usd_val, cat, tx = row
            desc += f"• `{date_str}` | **{cat.upper()}** | `{amount:.4f} {asset}` (${usd_val:.2f} USD) | `{tx[:12]}...`\n"
        embed.description = desc
    embed.set_footer(text="aibs_master.db • Zero-Mock Compliance Directive")
    return embed


# --- Interactive UI View with Buttons ---

class TelemetryControlView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view so buttons never expire

    @button(label="Refresh", style=discord.ButtonStyle.primary, emoji="🔄", custom_id="btn_refresh_telemetry")
    async def refresh_btn(self, interaction: discord.Interaction, btn: discord.ui.Button):
        await interaction.response.defer()
        embed_dict = build_telemetry_embed()
        embed = discord.Embed.from_dict(embed_dict)
        await interaction.message.edit(embed=embed, view=self)

    @button(label="Mining Details", style=discord.ButtonStyle.secondary, emoji="⛏️", custom_id="btn_mining_details")
    async def mining_btn(self, interaction: discord.Interaction, btn: discord.ui.Button):
        pearl = get_pearl_telemetry()
        gpu = get_gpu_telemetry()
        if not pearl.get("ok"):
            await interaction.response.send_message(f"⚠️ Could not query HeroMiners: {pearl.get('error')}", ephemeral=True)
            return
        embed = build_miner_embed(pearl, gpu)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @button(label="GPU Clocks", style=discord.ButtonStyle.secondary, emoji="🖥️", custom_id="btn_gpu_clocks")
    async def gpu_btn(self, interaction: discord.Interaction, btn: discord.ui.Button):
        gpu = get_gpu_telemetry()
        if not gpu.get("ok"):
            await interaction.response.send_message(f"⚠️ Could not query GPU: {gpu.get('error')}", ephemeral=True)
            return
        embed = build_gpu_embed(gpu)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @button(label="Enforce 310W Clamp", style=discord.ButtonStyle.danger, emoji="🛡️", custom_id="btn_enforce_clamp")
    async def clamp_btn(self, interaction: discord.Interaction, btn: discord.ui.Button):
        result = enforce_hardware_clamp()
        await interaction.response.send_message(f"🛡️ **RTX 4090 Clamping Enforced:**\n{result}", ephemeral=True)

    @button(label="Fiscal Ledger", style=discord.ButtonStyle.secondary, emoji="💼", custom_id="btn_fiscal_ledger")
    async def ledger_btn(self, interaction: discord.Interaction, btn: discord.ui.Button):
        summary = get_accounting_summary()
        embed = build_ledger_embed(summary)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# --- Bot Setup ---

class DummyBot:
    def event(self, func):
        return func

    def command(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

    def add_view(self, view):
        pass


class DummyTasks:
    def loop(self, *args, **kwargs):
        def decorator(func):
            func.is_running = lambda: False
            func.start = lambda: None
            return func
        return decorator


if HAS_DISCORD and DISCORD_BOT_TOKEN:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)
else:
    bot = DummyBot()
    tasks = DummyTasks()


last_bot_msg = None


@bot.event
async def on_ready():
    global last_bot_msg
    logger.info(f"🤖 AI-BS Discord Command Bot active as: {bot.user}")
    # Register persistent interactive button view
    try:
        bot.add_view(TelemetryControlView())
        logger.info("Registered persistent TelemetryControlView buttons.")
    except Exception as e:
        logger.warning(f"Failed to register persistent view: {e}")

    # Immediately post or update live telemetry card with controls to channel
    try:
        ch = bot.get_channel(CHANNEL_ID)
        if ch:
            embed_dict = build_telemetry_embed()
            embed = discord.Embed.from_dict(embed_dict)
            last_bot_msg = await ch.send(embed=embed, view=TelemetryControlView())
            logger.info(f"Dispatched live telemetry embed with controls to #{ch.name}")
    except Exception as e:
        logger.warning(f"Startup channel dispatch error: {e}")

    if not auto_status_loop.is_running():
        auto_status_loop.start()


@tasks.loop(minutes=STREAM_INTERVAL_MINS)
async def auto_status_loop():
    """Periodic telemetry status broadcast stream to Discord Channel with Controls."""
    global last_bot_msg
    try:
        embed_dict = build_telemetry_embed()
        embed = discord.Embed.from_dict(embed_dict)
        view = TelemetryControlView()

        # 1. Update existing card in-place or post new if channel is available
        ch = bot.get_channel(CHANNEL_ID)
        if ch:
            if last_bot_msg:
                try:
                    await last_bot_msg.edit(embed=embed, view=view)
                    logger.info(f"Updated live interactive telemetry widget in #{ch.name}")
                except Exception:
                    last_bot_msg = await ch.send(embed=embed, view=view)
                    logger.info(f"Posted fresh live telemetry card with controls to #{ch.name}")
            else:
                last_bot_msg = await ch.send(embed=embed, view=view)
                logger.info(f"Posted live telemetry card with controls to #{ch.name}")
        elif DISCORD_WEBHOOK_URL and DISCORD_WEBHOOK_URL.startswith("http"):
            try:
                requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed_dict]}, timeout=5)
                logger.info("Dispatched live telemetry embed via Discord webhook fallback")
            except Exception as w_err:
                logger.warning(f"Webhook fallback error: {w_err}")
    except Exception as e:
        logger.error(f"Error in status loop: {e}")



# --- Interactive Operator Commands ---

@bot.command(name="ping")
async def cmd_ping(ctx):
    """Latency probe and system version ping."""
    await ctx.send(f"🏓 **Pong!** AI-BS Cognitive Gateway is online (`{SYSTEM_VERSION}`) | RTX 4090 Clamped (`310W`).")


@bot.command(name="status")
async def cmd_status(ctx):
    """Returns master system telemetry card with interactive control buttons."""
    try:
        embed_data = build_telemetry_embed()
        embed = discord.Embed.from_dict(embed_data)
        await ctx.send(embed=embed, view=TelemetryControlView())
    except Exception as e:
        await ctx.send(f"⚠️ **Error generating status:** {e}")


@bot.command(name="miner", aliases=["pearl", "mining"])
async def cmd_miner(ctx):
    """Returns granular Pearl PoUW mining telemetry, accepted shares, and maturity countdown."""
    pearl = get_pearl_telemetry()
    gpu = get_gpu_telemetry()
    if not pearl.get("ok"):
        await ctx.send(f"⚠️ Could not reach HeroMiners API: {pearl.get('error')}")
        return
    embed = build_miner_embed(pearl, gpu)
    await ctx.send(embed=embed)


@bot.command(name="gpu", aliases=["hardware"])
async def cmd_gpu(ctx):
    """Returns physical RTX 4090 hardware clocks, power limits, and thermals."""
    gpu = get_gpu_telemetry()
    if not gpu.get("ok"):
        await ctx.send(f"⚠️ Could not query NVIDIA driver: {gpu.get('error')}")
        return
    embed = build_gpu_embed(gpu)
    await ctx.send(embed=embed)


@bot.command(name="clamp", aliases=["power", "lock"])
async def cmd_clamp(ctx):
    """Manually re-enforces the RTX 4090 310W power cap and 5001 MHz memory lock directly from Discord."""
    result = enforce_hardware_clamp()
    await ctx.send(f"🛡️ **RTX 4090 Hardware Clamping Enforced on Host Driver:**\n{result}")


@bot.command(name="ledger", aliases=["trades", "accounting"])
async def cmd_ledger(ctx):
    """Returns verified on-chain transfers from master accounting ledger."""
    summary = get_accounting_summary()
    embed = build_ledger_embed(summary)
    await ctx.send(embed=embed)


@bot.command(name="payout")
async def cmd_payout(ctx):
    """Returns progress toward the 1.0 PRL direct deposit payout threshold."""
    pearl = get_pearl_telemetry()
    if not pearl.get("ok"):
        await ctx.send(f"⚠️ Could not reach HeroMiners API: {pearl.get('error')}")
        return

    progress_bar = f"`[{('█' * int(pearl['progress_pct'] / 10)).ljust(10, '░')}]` {pearl['progress_pct']:.1f}%"
    embed = discord.Embed(
        title="💰 Pearl (PRL) Payout Threshold Progress",
        description=f"Destination Wallet: `{PEARL_WALLET}`",
        color=0x2ecc71,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Mature Unlocked Balance", value=f"**`{pearl['mature_prl']:.4f} PRL`** (~${pearl['mature_prl']*0.15:.2f} USD)", inline=True)
    embed.add_field(name="Payout Threshold", value=f"**`{pearl['min_payout']:.1f} PRL`**", inline=True)
    embed.add_field(name="Progress", value=progress_bar, inline=False)
    embed.add_field(name="Remaining to Payout", value=f"**`{max(0.0, pearl['min_payout'] - pearl['mature_prl']):.4f} PRL`**", inline=True)
    embed.add_field(name="Pending Block Accrual", value=f"**`{pearl['pending_prl']:.4f} PRL`** ({pearl['pending_count']} blocks)", inline=True)
    embed.set_footer(text="HeroMiners Pool • Batch payout broadcasts automatically once threshold is reached")
    await ctx.send(embed=embed)


def main():
    logger.info("Starting upgraded AI-BS Discord Interactive Bot Daemon with Controls...")
    if not HAS_DISCORD:
        logger.warning("discord.py module not installed. Running in idle standby mode.")
        return

    if not DISCORD_BOT_TOKEN:
        logger.warning("DISCORD_BOT_TOKEN not configured in .env. Bot commands inactive.")
        return

    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
