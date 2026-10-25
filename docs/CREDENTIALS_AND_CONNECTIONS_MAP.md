# AI-BS Ecosystem — Credentials, Web Host, and Cloudflared Connections Map

> **Security & Privacy Notice:**
> In accordance with repository architectural decisions (`ADR-002`, `ADR-005`) and secret protection guidelines, this document serves as an **authoritative directory and inventory map** of where all credentials, configuration files, tunnel mappings, and host environments reside on this system.
> **Never commit unmasked API keys, private keys, or secret tokens into Git-tracked files or public repositories.**

---

## 1. Cloudflare Tunnel (`cloudflared`) Connections

All public edge routing to your sovereign local services is routed through Cloudflare Zero Trust via `cloudflared`.

### 1.1 Tunnel Core Specifications
- **Tunnel Name:** `ai-bs`
- **Tunnel UUID:** `d1acbd25-06c3-4be0-a7f4-ae3943263aed`
- **Cloudflare Account ID:** Defined in `C:\AI-BS\.env` (`CLOUDFLARE_ACCOUNT_ID`)
- **Cloudflare Zone ID:** Defined in `C:\AI-BS\.env` (`CLOUDFLARE_ZONE_ID`)
- **Cloudflare API Token:** Defined in `C:\AI-BS\.env` (`CLOUDFLARE_API_TOKEN`)

### 1.2 Configuration & Credential Files
| Component | Absolute File Path | Description |
|---|---|---|
| **Tunnel Config** | `C:\Users\footb\.cloudflared\config.yml` | Master ingress rules, DNS hostname mappings, and target localhost ports. |
| **Tunnel Credentials** | `C:\Users\footb\.cloudflared\d1acbd25-06c3-4be0-a7f4-ae3943263aed.json` | Tunnel service account token, secret, and Account Tag. |
| **Origin Certificate** | `C:\Users\footb\.cloudflared\cert.pem` | Cloudflare origin authentication certificate. |
| **Backup Configs** | `C:\Users\footb\.cloudflared\config.yml.bak` | Pre-audit backup of ingress rules. |
| **Root Binary** | `C:\AI-BS\cloudflared.exe` | Standalone Windows executable used by system launch scripts. |
| **Backend Binary** | `C:\AI-BS\backend\cloudflared.exe` | Mirror executable for backend subsystem independence. |

### 1.3 Active Ingress Routing Map (`config.yml`)
| Public Hostname | Path Route | Target Service (Localhost) | Upstream Subsystem |
|---|---|---|---|
| `api.brettstehouwer.live` | `/sse` | `http://127.0.0.1:8099` | Real-time SSE event bus |
| `api.brettstehouwer.live` | `/messages` | `http://127.0.0.1:8099` | Messaging / webhooks |
| `api.brettstehouwer.live` | `/` (root / all) | `http://127.0.0.1:8000` | Sovereign Go Gateway |
| `ai-bs.brettstehouwer.live` | `/` (root / all) | `http://127.0.0.1:8080` | FastAPI Core Backend |
| `stehouwer-publishing.com` | `*` | `http://127.0.0.1:80` | Local Web Server (Publishing) |
| `www.stehouwer-publishing.com`| `*` | `http://127.0.0.1:80` | Local Web Server (Publishing) |
| `stehouwerpublishing.com` | `*` | `http://127.0.0.1:80` | Local Web Server (Publishing) |
| `www.stehouwerpublishing.com` | `*` | `http://127.0.0.1:80` | Local Web Server (Publishing) |
| `recdebut-recruit.org` | `/api/` | `http://127.0.0.1:8080` | RecDebut API proxy |
| `recdebut-recruit.org` | `/r/` | `http://127.0.0.1:8080` | RecDebut Redirect handler |
| `r.recdebut-recruit.org` | `*` | `http://127.0.0.1:8080` | RecDebut Shortlinks |
| `recdebut-recruit.org` | `*` | `http://127.0.0.1:8080` | RecDebut Main Web App |
| `www.recdebut-recruit.org` | `*` | `http://127.0.0.1:8080` | RecDebut Main Web App |

### 1.4 Launch & Control Scripts
- **Launch Tunnel:** `C:\AI-BS\Launch_AI_BS.bat` (Executes: `cloudflared.exe tunnel run ai-bs`)
- **Dev Launch:** `C:\AI-BS\Launch_AI_BS_Dev.bat`
- **Graceful Shutdown:** `C:\AI-BS\Shutdown_AI_BS.bat`

---

## 2. Web Host & Deployment Environments

### 2.1 Firebase Production Hosting
- **Hosting Site:** `ai-bs-dashboard`
- **Project RC:** `C:\AI-BS\frontend\.firebaserc`
- **Hosting Config:** `C:\AI-BS\frontend\firebase.json` (defines public directory `dist`, SPA rewrites to `/index.html`, and caching policies)
- **Firebase CLI Auth:** `C:\Users\footb\.config\configstore\firebase-tools.json` (active OAuth session tokens)
- **Deployment Command:** `cd C:\AI-BS\frontend && npm run build && firebase deploy --only hosting`

### 2.2 Vercel Deployment Configuration
- **Root Vercel Config:** `C:\AI-BS\vercel.json` (build command `npm run build --prefix frontend`, output `frontend/dist`)
- **Frontend Vercel Config:** `C:\AI-BS\frontend\vercel.json`
- **Frontend Local Credentials:** `C:\AI-BS\frontend\.env.local`
  - Variable: `VERCEL_OIDC_TOKEN`

### 2.3 Local Sovereign Host Ports (Zero-Browser Loopback)
- **Go Gateway:** `http://127.0.0.1:8000`
- **FastAPI Core Backend:** `http://127.0.0.1:8080`
- **Vite React Frontend:** `http://127.0.0.1:5173`
- **Ollama Neural Swarm:** `http://127.0.0.1:11434`
- **SSE Event Stream:** `http://127.0.0.1:8099`

---

## 3. Main Ecosystem Feature Credentials (`C:\AI-BS\.env`)

**File Path:** `C:\AI-BS\.env`  
*To view or edit in VS Code: `code C:\AI-BS\.env`*  
*To view in Notepad: `notepad C:\AI-BS\.env`*

### 3.1 AI, LLM & GPU Inference
| Variable Name | Service / Feature Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key for multimodal reasoning & generation |
| `AI_BS_API_KEY` | Internal AI-BS ecosystem inter-service API key |
| `CLORE_API_KEY` | Clore.ai GPU compute marketplace leasing |
| `RAPID_API_KEY` | RapidAPI third-party intelligence services |
| `GENERATION_MODEL` | Default local/remote text generation model |
| `EMBEDDING_MODEL` | Default vector embedding model |
| `OLLAMA_BASE_URL` | Local Ollama endpoint (`http://127.0.0.1:11434`) |

### 3.2 Cloudflare Cloud Infrastructure
| Variable Name | Service / Feature Purpose |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Scoped API token for DNS, Zero Trust, and Tunnel management |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account identifier |
| `CLOUDFLARE_ZONE_ID` | DNS zone identifier for `brettstehouwer.live` |

### 3.3 Communications, Alerts & Bot Integrations
| Variable Name | Service / Feature Purpose |
|---|---|
| `DISCORD_BOT_TOKEN` | Discord bot authentication token for neural notifications |
| `DISCORD_WEBHOOK_URL` | Discord channel webhook for trade/audit alerts |
| `DISCORD_STREAM_INTERVAL_MINUTES` | Frequency of Discord monitoring streams |
| `SLACK_BOT_TOKEN` | Slack app bot token for operations workspace |
| `RESEND_API_KEY` | Resend transactional email API key |
| `RESEND_FROM_EMAIL` | Verified sending domain email |
| `TEXTBEE_API_KEY` | TextBee SMS gateway API key |
| `TEXTBEE_DEVICE_ID` | Android device gateway ID for automated SMS |
| `TEXTBEE_WEBHOOK_SECRET` | Inbound SMS webhook validation secret |
| `OPERATOR_PHONE` | Admin mobile contact number |
| `OPERATOR_EMAIL` | Admin primary email contact |

### 3.4 Email & Mailbox Sync (IMAP / SMTP)
| Variable Name | Service / Feature Purpose |
|---|---|
| `IMAP_USER` | Primary IMAP monitoring mailbox |
| `IMAP_APP_PASSWORD` | App password for IMAP polling |
| `BRETT_EMAIL` | Personal operational email address |
| `BRETT_APP_PASSWORD` | App-specific password for personal email |
| `NOCO_EMAIL` | Enterprise / NoCo mailbox address |
| `NOCO_APP_PASSWORD` | App-specific password for NoCo mailbox |
| `IONOS_EMAIL` | IONOS domain hosting email |
| `IONOS_PASSWORD` | IONOS domain mailbox password |
| `IONOS_SMTP_HOST` | IONOS SMTP server host |
| `IONOS_SMTP_PORT` | IONOS SMTP port (e.g., 587/465) |

### 3.5 Developer Repositories, IPFS & Web3
| Variable Name | Service / Feature Purpose |
|---|---|
| `GITHUB_TOKEN` | GitHub Personal Access Token for git automation & releases |
| `PINATA_API_KEY` | Pinata IPFS pinning service API key |
| `PINATA_SECRET_API_KEY` | Pinata IPFS secret key |
| `IPFS_GATEWAY_URL` | Public/dedicated IPFS gateway |
| `NFT_ROYALTY_ADDRESS` | On-chain royalty beneficiary address |
| `NFT_ROYALTY_PERCENTAGE` | Royalty fee basis points |

### 3.6 Crypto Exchanges, Trading & Wallets
| Variable Name | Service / Feature Purpose |
|---|---|
| `CRYPTO_COM_API_KEY` | Crypto.com exchange API key |
| `CRYPTO_COM_SECRET_KEY` | Crypto.com secret signing key |
| `CRYPTOCOM_APP_AGENT_KEY` | Crypto.com mobile app agent integration key |
| `KRAKEN_API_KEY` | Kraken spot exchange API key |
| `KRAKEN_SECRET_KEY` | Kraken secret signing key |
| `KRAKEN_PRIVATE_KEY` | Kraken private key for programmatic orders |
| `USDC_DESTINATION_ADDRESS` | Native USDC deposit/payout address |
| `XCH_WALLET` | Chia native wallet address |
| `DOGE_WALLET` | Dogecoin native payout wallet |
| `WATCHER_SYMBOLS` | Trading pairs monitored by SafeTrade algorithm |
| `TRADE_USD_AMOUNT` / `MIN_ORDER_USD` | Position sizing configurations |
| `BUY_DIP_PCT` / `TAKE_PROFIT_PCT` / `STOP_LOSS_PCT` | Quantitative execution thresholds |

### 3.7 Mining & Proof-of-Space Farming
| Variable Name | Service / Feature Purpose |
|---|---|
| `CHIA_FARMER_PUBKEY` | Chia farmer public key |
| `CHIA_POOL_CONTRACT_ADDR` | Chia Plot NFT pool contract address |
| `CHIA_POOL_PUBKEY` | Chia pool public key |
| `CHIA_NFT_FINGERPRINT` | Chia wallet fingerprint |
| `DUAL_MINER_BINARY` | Path to GPU dual-miner executable |
| `POOL_PRIMARY_URL` | Primary Stratum mining pool endpoint |
| `POOL_SECONDARY_URL` | Secondary Stratum mining pool endpoint |
| `POOL_FAILOVER_URL` | Failover Stratum mining pool endpoint |

### 3.8 Live Streaming & Social
| Variable Name | Service / Feature Purpose |
|---|---|
| `KICK_CLIENT_ID` | Kick live-streaming client ID |
| `KICK_CLIENT_SECRET` | Kick client secret |

---

## 4. Backend Web Host, Payment & Security Credentials (`C:\AI-BS\backend\.env`)

**File Path:** `C:\AI-BS\backend\.env`  
*To view or edit in VS Code: `code C:\AI-BS\backend\.env`*  
*To view in Notepad: `notepad C:\AI-BS\backend\.env`*

### 4.1 Payment Gateways & Banking
| Variable Name | Service / Feature Purpose |
|---|---|
| `PAYPAL_CLIENT_ID` | PayPal REST API client ID |
| `PAYPAL_SECRET` | PayPal REST API secret |
| `PAYPAL_WEBHOOK_ID` | PayPal IPN/Webhook validation ID |
| `STRIPE_API_KEY` | Stripe secret API key (`sk_live_...` or `sk_test_...`) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook endpoint signature verifier (`whsec_...`) |
| `SOFI_ROUTING_NUMBER` | SoFi Bank routing number for ACH settlement |
| `SOFI_ACCOUNT_NUMBER` | SoFi Bank account number |
| `SOFI_ACCOUNT_MASKED` | Display-safe masked account number |

### 4.2 Web3 Payouts & Blockchain Nodes
| Variable Name | Service / Feature Purpose |
|---|---|
| `PAYOUT_WALLET_PRIVATE_KEY` | EVM wallet private key for automated USDC payouts |
| `WEB3_PROVIDER_URI` | EVM RPC endpoint (Allnodes, Infura, or Alchemy) |
| `USDC_CONTRACT_ADDRESS` | ERC-20 / Native USDC smart contract address |
| `USDC_DESTINATION_ADDRESS` | Cold storage destination address for swept funds |
| `ALLNODES_API_KEY` | Allnodes dedicated blockchain RPC / staking key |

### 4.3 Cryptographic Security Vault Keys
| Variable Name | Service / Feature Purpose |
|---|---|
| `AIBS_AES_MASTER_PASSPHRASE` | Master encryption passphrase for local SQLite database vault |
| `AIBS_AES_SALT` | Cryptographic salt for PBKDF2/Argon2 key derivation |
| `AIBS_LICENSE_SECRET` | Offline license generation and validation secret |

### 4.4 Broadcast Media & Video Streaming
| Variable Name | Service / Feature Purpose |
|---|---|
| `TWITCH_CLIENT_ID` | Twitch developer application client ID |
| `TWITCH_CLIENT_SECRET` | Twitch application client secret |
| `TWITCH_CHANNEL_NAME` | Target Twitch broadcast channel |
| `AIBS_RTMP_URL` | Local / remote RTMP ingestion server URL |
| `AIBS_SRT_URL` | Low-latency Secure Reliable Transport (SRT) video endpoint |
| `AIBS_STREAM_KEY` | Streaming authentication key |

### 4.5 AI Model Cache Directories
| Variable Name | Service / Feature Purpose |
|---|---|
| `OLLAMA_MODELS` | Local directory for Ollama model weights |
| `HF_HOME` | Hugging Face cache root directory |
| `HUGGINGFACE_HUB_CACHE` | Hugging Face downloaded transformer weights cache |

---

## 5. Codex Desktop App & Developer Environment Credentials

| Tool / Provider | File Location | Purpose |
|---|---|---|
| **Codex Session Auth** | `C:\Users\footb\.codex\auth.json` | ChatGPT OAuth tokens, account credentials, and session state. |
| **Codex App Config** | `C:\Users\footb\.codex\config.toml` | Codex Desktop settings, origin permissions, model defaults, trusted hooks. |
| **Codex Lifecycle Hooks** | `C:\Users\footb\.codex\hooks.json` | Event hooks (`SessionStart`, `PreCompact`, `PostCompact`, `Stop`). |
| **Git Configuration** | `C:\Users\footb\.gitconfig` | Global git author name, email, credentials helper, and safe directories. |
| **SSH Keys** | `C:\Users\footb\.ssh\` | Private/public keys (`id_rsa`, `id_ed25519`) for GitHub/remote server access. |

---

## 6. How to Safely Inspect and Update Credentials

When viewing or updating credentials, open the files locally on your machine:

1. **To edit Root Features (`.env`):**
   ```powershell
   notepad C:\AI-BS\.env
   ```
2. **To edit Backend Payments & Web3 (`backend\.env`):**
   ```powershell
   notepad C:\AI-BS\backend\.env
   ```
3. **To edit Cloudflare Ingress Routing:**
   ```powershell
   notepad C:\Users\footb\.cloudflared\config.yml
   ```
4. **To view Cloudflare Tunnel Credentials:**
   ```powershell
   notepad C:\Users\footb\.cloudflared\d1acbd25-06c3-4be0-a7f4-ae3943263aed.json
   ```

*Always restart corresponding services (`Launch_AI_BS.bat` or individual service tasks) after updating `.env` or `config.yml` files for changes to take effect.*
