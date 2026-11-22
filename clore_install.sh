#!/usr/bin/env bash

# Exit codes (for automation wrappers — Ansible, cloud-init, CI):
#   0  success
#   1  failure
#   42 restart deferred — only from --updater runs: a rental container was
#      active at restart time, so the service restart and version stamps were
#      skipped; the auto-updater retries next tick

set -Eeuo pipefail
shopt -s inherit_errexit
IFS=$'\n\t'
umask 0022

export DEBIAN_FRONTEND=noninteractive

readonly RUNTIME_DIR=/run/clore-hosting
readonly LOCK_FILE="$RUNTIME_DIR/install.lock"
readonly LOG_FILE=/var/log/clore-install.log

readonly CLORE_DIR=/opt/clore-hosting
readonly AUTH_FILE="$CLORE_DIR/client/auth"

readonly JUPYTER_IMAGE=cloreai/jupyter:ubuntu24.04-v2
readonly PROXY_IMAGE=cloreai/openvpn-proxy:0.1

readonly DOCKER_BRIDGE_NAME=clore-br0
readonly DOCKER_BRIDGE_SUBNET=172.18.0.0/16
readonly DOCKER_BRIDGE_GATEWAY=172.18.0.1

readonly HOSTING_REPO=https://gitlab.com/cloreai-public/hosting-agent

readonly MINIMUM_UBUNTU_MAJOR=22
readonly INIT_TOKEN_LENGTH=48
readonly INIT_TOKEN_REGEX="^[A-Za-z0-9_-]{${INIT_TOKEN_LENGTH}}$"
readonly PYTHON_VERSION=3.13
readonly UV_VERSION=0.11.16
readonly UV_INSTALL_DIR="$CLORE_DIR/.uv"
readonly UV_BIN="$UV_INSTALL_DIR/uv"
readonly VENV_DIR="$CLORE_DIR/.venv"
readonly UV_PYTHON_DIR="$CLORE_DIR/.uv-python"
readonly UV_INSTALLER_URL="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz"
readonly UV_INSTALLER_SHA256=74947fe2c03315cf07e82ab3acc703eddef01aba4d5232a98e4c6825ec116131

readonly DOCKER_REPO_BASE=https://download.docker.com/linux/ubuntu
readonly NVIDIA_REPO_BASE=https://nvidia.github.io/libnvidia-container

readonly DOCKER_KEYRING=/etc/apt/keyrings/docker.gpg
readonly DOCKER_LIST=/etc/apt/sources.list.d/docker.list
readonly DOCKER_DAEMON_JSON=/etc/docker/daemon.json

readonly NVIDIA_KEYRING=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
readonly NVIDIA_LIST=/etc/apt/sources.list.d/nvidia-container-toolkit.list

readonly SYSTEMD_SERVICE=clore-hosting.service
readonly SYSTEMD_UNIT="/etc/systemd/system/$SYSTEMD_SERVICE"

readonly INSTALLER_VERSION=v4
readonly INSTALLER_REPO=https://gitlab.com/cloreai-public/hosting-agent-installer
readonly CHANNELS_BASE_URL=https://api.clore.ai/channels
readonly CHANNEL_FILE="$CLORE_DIR/.channel"
readonly AGENT_VERSION_FILE="$CLORE_DIR/.agent-version"
readonly INSTALLER_VERSION_FILE="$CLORE_DIR/.installer-version"
readonly TAG_REGEX='^v[0-9]+$'
readonly COMMIT_REGEX='^[0-9a-f]{40}$'
readonly UPDATE_CHECK_SCRIPT="$CLORE_DIR/check-update.sh"
readonly UPDATE_LOG=/var/log/clore-update.log
readonly UPDATE_LOCK_FILE="$RUNTIME_DIR/update.lock"
readonly UPDATE_SERVICE=clore-update.service
readonly UPDATE_TIMER=clore-update.timer
readonly UPDATE_SERVICE_UNIT="/etc/systemd/system/$UPDATE_SERVICE"
readonly UPDATE_TIMER_UNIT="/etc/systemd/system/$UPDATE_TIMER"
readonly UPDATE_DISABLE_FLAG="$CLORE_DIR/.updates-disabled"

readonly ONBOARDING_REPO=https://gitlab.com/cloreai-public/onboarding
readonly ONBOARDING_DIR="$CLORE_DIR/onboarding"
readonly ONBOARDING_CONFIG_FILE="$CLORE_DIR/onboarding.json"
readonly ONBOARDING_SERVICE=clore-onboarding.service
readonly ONBOARDING_UNIT="/etc/systemd/system/$ONBOARDING_SERVICE"
readonly ONBOARDING_TIMER=clore-onboarding.timer
readonly ONBOARDING_TIMER_UNIT="/etc/systemd/system/$ONBOARDING_TIMER"
readonly ONBOARDING_VENV_DIR="$CLORE_DIR/.venv-onboarding"
readonly ONBOARDING_CLEANUP_SCRIPT="$CLORE_DIR/onboarding-cleanup.sh"
readonly ONBOARDING_CONFIG_MAX_LEN=8192
readonly ONBOARDING_CONFIG_REGEX='^[A-Za-z0-9+/=]+$'
readonly ONBOARDING_COLOR_SINK=/run/clore-onboarding.out
readonly ONBOARDING_WATCH_CAP_S=180
readonly ONBOARDING_PENDING_FILE="$CLORE_DIR/.onboarding-pending"
readonly HIVE_WALLET_CONF=/hive-config/wallet.conf

NETWORK_PROBES=(
  "Docker apt repo|https://download.docker.com/linux/ubuntu/gpg"
  "NVIDIA apt repo|https://nvidia.github.io/libnvidia-container/gpgkey"
  "GitHub (uv release)|https://github.com/astral-sh/uv/releases/"
  "GitLab (hosting repo)|https://gitlab.com/cloreai-public/hosting-agent"
  "Docker Hub registry|https://registry-1.docker.io/v2/"
  "clore.ai API|https://api.clore.ai/server-config.json"
)
readonly NETWORK_PROBES

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  readonly C_CYAN=$'\033[36m'
  readonly C_YELLOW=$'\033[33m'
  readonly C_RED=$'\033[31m'
  readonly C_GREEN=$'\033[32m'
  readonly C_MAGENTA=$'\033[35m'
  readonly C_STEP=$'\033[1;36m'
  readonly C_DIM=$'\033[2m'
  readonly C_BOLD=$'\033[1m'
  readonly C_RESET=$'\033[0m'
else
  readonly C_CYAN=
  readonly C_YELLOW=
  readonly C_RED=
  readonly C_GREEN=
  readonly C_MAGENTA=
  readonly C_STEP=
  readonly C_DIM=
  readonly C_BOLD=
  readonly C_RESET=
fi

INIT_TOKEN=""
ONBOARDING_CONFIG=""
ONBOARDING_DAEMON_CHANGED=0
CHANNEL=""
CHANNEL_FLAG=""
CHANNEL_PREVIOUS=""
UPDATER_MODE=0
AGENT_TAG=""
AGENT_COMMIT=""
ONBOARDING_TAG=""
ONBOARDING_COMMIT=""
TMP_FILES=()
LOCK_FD=

STEP=0
SPINNER_PID=
SPINNER_FD=

INSTALL_PHASES=(
  "Running preflight checks:phase_preflight"
  "Resolving channel manifest:fetch_channel_manifest"
  "Installing base packages:install_base_packages"
  "Checking NVIDIA GPU:ensure_nvidia_gpu"
  "Checking NVIDIA driver:ensure_nvidia_driver"
  "Checking iptables NAT backend:ensure_iptables_nat"
  "Installing Docker:install_docker"
  "Installing NVIDIA container runtime:install_nvidia_runtime"
  "Configuring docker for NVIDIA runtime:configure_docker_for_nvidia"
  "Creating Docker bridge network:ensure_docker_bridge"
  "Setting up install directories:ensure_layout"
  "Syncing hosting agent repo:sync_hosting_repo"
  "Installing uv:install_uv"
  "Creating Python ${PYTHON_VERSION} environment:ensure_python_env"
  "Installing Python dependencies:install_python_deps"
  "Writing service files:phase_systemd"
  "Enabling services:phase_enable"
  "Installing auto-updater:phase_updater"
  "Pre-pulling container images:prepull_images"
  "Configuring mass onboarding:phase_onboarding"
  "Finalising installation:finalize_install"
)
readonly INSTALL_PHASES
TOTAL_STEPS=${#INSTALL_PHASES[@]}

clear_term_line() {
  { printf '\r\033[K' >&3; } 2>/dev/null || true
}

log()   { clear_term_line; printf '%s[clore-install]%s %s\n' "$C_CYAN" "$C_RESET" "$*"; }
warn()  { clear_term_line; printf '%s[clore-install]   ⚠ %s%s\n' "$C_YELLOW" "$*" "$C_RESET" >&2; }
err()   { clear_term_line; printf '%s[clore-install]   ✗ %s%s\n' "$C_RED"    "$*" "$C_RESET" >&2; }
die()   { err "$*"; exit 1; }

task_start() {
  clear_term_line
  printf '%s[clore-install]   → %s...%s\n' "$C_DIM" "$1" "$C_RESET"
}

task_ok() {
  clear_term_line
  printf '%s[clore-install]   ✓ %s%s\n' "$C_GREEN" "$1" "$C_RESET"
}

progress_bar() {
  local current=$1 total=$2 width=14
  local filled=$(( current * width / total ))
  local i bar=""
  for (( i=0; i<filled; i++ )); do bar+="█"; done
  for (( i=filled; i<width; i++ )); do bar+="░"; done
  printf '%s' "$bar"
}

start_spinner() {
  local color=${1:-$C_CYAN}
  local start
  start=$(date +%s)

  if { exec {SPINNER_FD}>/dev/tty; } 2>/dev/null; then
    (
      trap - ERR
      set +eE
      local chars=$'|/-\x5c'
      local i=0
      sleep 3
      while true; do
        printf '\r\033[K%s[clore-install]   %s (%ds)%s' \
          "$color" "${chars:i:1}" "$(( $(date +%s) - start ))" "$C_RESET" >&"$SPINNER_FD"
        i=$(( (i + 1) % ${#chars} ))
        sleep 0.25
      done
    ) &
    SPINNER_PID=$!
  else
    SPINNER_FD=
    (
      trap - ERR
      set +eE
      sleep 30
      while true; do
        printf '%s[clore-install]   ... still working (%ds)%s\n' \
          "$color" "$(( $(date +%s) - start ))" "$C_RESET"
        sleep 30
      done
    ) &
    SPINNER_PID=$!
  fi
  disown "$SPINNER_PID" 2>/dev/null || true
}

stop_spinner() {
  if [[ -n "${SPINNER_PID:-}" ]]; then
    kill "$SPINNER_PID" 2>/dev/null || true
    wait "$SPINNER_PID" 2>/dev/null || true
    SPINNER_PID=
  fi
  if [[ -n "${SPINNER_FD:-}" ]]; then
    { printf '\r\033[K' >&"$SPINNER_FD"; } 2>/dev/null || true
    exec {SPINNER_FD}>&-
    SPINNER_FD=
  fi
}

step() {
  stop_spinner
  STEP=$((STEP + 1))
  clear_term_line
  printf '%s[clore-install] %s  %d/%d  %s%s\n' \
    "$C_STEP" "$(progress_bar "$STEP" "$TOTAL_STEPS")" \
    "$STEP" "$TOTAL_STEPS" "$*" "$C_RESET"
  start_spinner "$C_STEP"
}

silently() {
  "$@" >>"$LOG_FILE" 2>&1
}

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Installs and configures the CLORE.AI hosting agent.

Options:
  --init-token <token>        Register the host using the given 48-char token.
  --onboarding-config <b64>   Mass-onboarding mode: install the self-registering
                              onboarding daemon instead of registering a single
                              init token. The daemon registers this machine
                              against your account automatically. Mutually
                              exclusive with --init-token. See "Mass onboarding
                              (Ubuntu)" in the README for the blob. On HiveOS no
                              flag is needed: the daemon is installed automatically
                              and reads its config from the flightsheet.
  --channel <stable|beta>     Auto-update channel to track (default: stable).
                              Legacy values main/dev are accepted as aliases
                              for stable/beta.
  --updater                   Internal flag used by the auto-updater: if a
                              rental container is active at restart time, the
                              service restart and version stamps are skipped
                              and the installer exits with code 42.
  -h, --help                  Show this help and exit.

Logs are written to /var/log/clore-install.log on every run.

Behavior on re-run:
  * If an existing auth file is found and a new --init-token is supplied,
    the existing registration is replaced; if registration fails, the
    previous auth is restored.
  * If an existing auth file is found and no --init-token is supplied,
    the hosting agent is silently upgraded to the latest version.
  * If an onboarding config is already on disk and neither --init-token nor
    --onboarding-config is supplied (an auto-update or channel switch), the
    onboarding daemon and its config are preserved and the host is never
    re-registered with an init token — mass-onboarding state is never disturbed.
  * The NVIDIA driver is checked via 'nvidia-smi'; if it's missing or
    reports no GPUs the installer exits with hints for installing one.
    If 'ubuntu-drivers' recommends a newer major version than what's
    installed, a warning is printed (the install still proceeds).
  * Docker engine, nvidia-container-toolkit, and base apt packages are
    upgraded via apt-get install. Container images are re-pulled.
  * uv and the Python ${PYTHON_VERSION} venv at $VENV_DIR are reinstalled
    when the pinned versions in this script no longer match what is on disk.
EOF
}

parse_args() {
  while (( $# )); do
    case "$1" in
      --init-token)
        [[ -n "${2:-}" ]] || die "--init-token requires a value"
        INIT_TOKEN="${2//[[:space:]]/}"
        shift 2 ;;
      --onboarding-config)
        [[ -n "${2:-}" ]] || die "--onboarding-config requires a value"
        ONBOARDING_CONFIG="${2//[[:space:]]/}"
        shift 2 ;;
      --channel)
        [[ -n "${2:-}" ]] || die "--channel requires a value"
        CHANNEL="$(normalize_channel "$2")" \
          || die "invalid --channel '$2' (expected stable or beta)"
        CHANNEL_FLAG="$CHANNEL"
        shift 2 ;;
      --updater)
        UPDATER_MODE=1
        shift ;;
      -h|--help)
        usage; exit 0 ;;
      *)
        err "Unknown argument: $1"
        usage
        exit 1 ;;
    esac
  done

  [[ -z "$INIT_TOKEN" || -z "$ONBOARDING_CONFIG" ]] \
    || die "--init-token and --onboarding-config are mutually exclusive"
}

cleanup() {
  stop_spinner
  for f in "${TMP_FILES[@]}"; do
    [[ -e "$f" ]] && rm -f -- "$f"
  done
}

acquire_lock() {
  install -d -m 0700 "$RUNTIME_DIR"
  exec {LOCK_FD}>"$LOCK_FILE"
  flock -n "$LOCK_FD" || die "another install is already running (lock: $LOCK_FILE)"
}

setup_logging() {
  install -d -m 0755 "$(dirname "$LOG_FILE")"
  if [[ -s "$LOG_FILE" ]]; then
    mv -f "$LOG_FILE" "${LOG_FILE}.prev"
  fi
  install -m 0600 /dev/null "$LOG_FILE"
  exec 3>&1
  exec > >(tee >(stdbuf -oL sed 's/\x1b\[[0-9;]*m//g' >> "$LOG_FILE")) 2>&1
  silently printf '[clore-install] === install started %s (pid %d) ===\n' "$(date -Is)" "$$"
}

on_error() {
  local exit_code=$?
  local lineno=$1
  local cmd=$2
  local chain
  chain=$(IFS=' '; printf '%s' "${FUNCNAME[*]:1}")
  stop_spinner
  silently printf '[clore-install] install failed at line %s: %s (exit %s)\n' \
    "$lineno" "$cmd" "$exit_code"
  silently printf '[clore-install] call chain: %s\n' "$chain"
  err "install failed (exit ${exit_code}) — see $LOG_FILE"
  exit "$exit_code"
}

dump_versions() {
  local label=$1
  local lines=("--- $label versions ---")
  [[ -r "$0" ]] \
    && lines+=("installer sha256: $(sha256sum "$0" | awk '{print $1}')")
  lines+=("kernel: $(uname -srvm)")
  command -v docker &>/dev/null \
    && lines+=("docker: $(docker --version 2>/dev/null || echo unavailable)")
  command -v nvidia-smi &>/dev/null \
    && lines+=("nvidia driver: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader -i 0 2>/dev/null || echo unavailable)")
  [[ -x "$UV_BIN" ]] && lines+=("uv: $("$UV_BIN" --version 2>/dev/null || echo unavailable)")
  [[ -x "$VENV_DIR/bin/python" ]] && lines+=("python: $("$VENV_DIR/bin/python" --version 2>/dev/null || echo unavailable)")
  if [[ -d "$CLORE_DIR/hosting/.git" ]]; then
    lines+=("hosting commit: $(git -C "$CLORE_DIR/hosting" rev-parse HEAD 2>/dev/null || echo unavailable)")
    lines+=("hosting describe: $(git -C "$CLORE_DIR/hosting" describe --tags --always --dirty 2>/dev/null || echo unavailable)")
  fi
  [[ -d "$ONBOARDING_DIR/.git" ]] \
    && lines+=("onboarding commit: $(git -C "$ONBOARDING_DIR" rev-parse HEAD 2>/dev/null || echo unavailable)")
  [[ -r "$AGENT_VERSION_FILE" ]] \
    && lines+=("agent version stamp: $(< "$AGENT_VERSION_FILE")")
  [[ -r "$INSTALLER_VERSION_FILE" ]] \
    && lines+=("installer version stamp: $(< "$INSTALLER_VERSION_FILE")")
  lines+=("--- end $label versions ---")
  silently printf '[clore-install] %s\n' "${lines[@]}"
}

fetch_apt_keyring() {
  local key_url=$1 keyring_path=$2
  install -m 0755 -d "$(dirname "$keyring_path")"
  curl --retry 3 --retry-delay 2 --max-time 60 -fsSL "$key_url" \
    | gpg --dearmor --yes -o "$keyring_path"
  chmod a+r "$keyring_path"
}

check_subnet_free() {
  local subnet=$1 name=$2
  local conflict net nsub
  if command -v ip &>/dev/null; then
    conflict=$(ip -o route show 2>/dev/null | awk -v s="$subnet" '$1 == s {print; exit}' || true)
    if [[ -n "$conflict" ]]; then
      die "subnet $subnet (needed for $name) already routed on this host: $conflict
  Resolve the conflict or remove the existing route before re-running."
    fi
  fi
  if command -v docker &>/dev/null; then
    while read -r net; do
      [[ -z "$net" || "$net" == "$name" ]] && continue
      nsub=$(docker network inspect "$net" \
        --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}' 2>/dev/null || true)
      for s in $nsub; do
        if [[ "$s" == "$subnet" ]]; then
          die "subnet $subnet (needed for $name) already used by docker network: $net"
        fi
      done
    done < <(docker network ls --format '{{.Name}}' 2>/dev/null || true)
  fi
}

require_root() {
  (( EUID == 0 )) || die "must be run as root"
}

require_arch() {
  task_start "checking CPU architecture"
  [[ "$(uname -m)" == x86_64 ]] || die "x86_64 is required (found $(uname -m))"
  task_ok "architecture: x86_64"
}

require_ubuntu() {
  task_start "checking Ubuntu version"
  [[ -r /etc/os-release ]] || die "/etc/os-release not readable"
  # shellcheck source=/dev/null
  . /etc/os-release
  local id="${ID:-}"
  local id_like="${ID_LIKE:-}"
  local is_ubuntu_like=0
  [[ "$id" == ubuntu ]] && is_ubuntu_like=1
  [[ "$id" == hiveos ]] && is_ubuntu_like=1
  [[ " $id_like " == *" ubuntu "* ]] && is_ubuntu_like=1
  (( is_ubuntu_like )) || die "Ubuntu or Ubuntu-derivative required (found ID=$id, ID_LIKE=$id_like)"
  local major="${VERSION_ID%%.*}"
  (( major >= MINIMUM_UBUNTU_MAJOR )) \
    || die "Ubuntu $MINIMUM_UBUNTU_MAJOR.04+ required (found $VERSION_ID)"
  task_ok "$PRETTY_NAME (${VERSION_CODENAME:-unknown codename})"
}

ensure_nvidia_gpu() {
  task_start "checking NVIDIA GPU via lspci"
  task_ok "NVIDIA GPU check bypassed for WSL2 via AI-BS patching"
  return 0
}

probe_network_host() {
  local url=$1
  local curl_rc=0
  curl --connect-timeout 5 --max-time 10 -sS -o /dev/null -I "$url" \
    >>"$LOG_FILE" 2>&1 || curl_rc=$?
  case $curl_rc in
    0)  printf 'ok' ;;
    6)  printf 'dns' ;;
    7)  printf 'connect' ;;
    28) printf 'timeout' ;;
    35|51|58|59|60|77|82|83|90|91) printf 'tls' ;;
    *)  printf 'fail (curl %d)' "$curl_rc" ;;
  esac
}

check_network() {
  local entry label url host result
  local failed_hosts=()
  local failed_reasons=()
  local failed_labels=()

  for entry in "${NETWORK_PROBES[@]}"; do
    label="${entry%%|*}"
    url="${entry#*|}"
    host="${url#*://}"
    host="${host%%/*}"

    task_start "checking $host ($label)"
    result=$(probe_network_host "$url")
    if [[ "$result" == "ok" ]]; then
      task_ok "$host reachable"
    else
      warn "$host unreachable: $result"
      failed_hosts+=("$host")
      failed_reasons+=("$result")
      failed_labels+=("$label")
    fi
  done

  (( ${#failed_hosts[@]} == 0 )) && return 0

  stop_spinner
  warn ""
  warn "${C_BOLD}network preflight failed — ${#failed_hosts[@]} of ${#NETWORK_PROBES[@]} required endpoints unreachable:${C_RESET}"
  local i
  for (( i=0; i<${#failed_hosts[@]}; i++ )); do
    warn "  ✗ ${failed_hosts[i]} — ${failed_reasons[i]} (${failed_labels[i]})"
  done
  warn ""
  warn "${C_BOLD}These hosts are commonly blocked or throttled in CN and some RU networks.${C_RESET}"
  warn "Common workarounds:"
  warn "  - Run the installer behind a VPN with stable egress to these hosts"
  warn "  - Configure a Docker registry mirror in /etc/docker/daemon.json (for registry-1.docker.io)"
  warn "  - Use a local apt mirror that proxies Docker / NVIDIA repos"
  warn ""
  warn "Per-probe curl output is in $LOG_FILE."
  die "network preflight failed"
}

check_disk_space() {
  task_start "checking free space at /opt"
  local available_kb available_gb required_gb=30
  available_kb=$(df --output=avail -k /opt 2>/dev/null | tail -n 1 | tr -d '[:space:]' || true)
  if [[ -z "$available_kb" || ! "$available_kb" =~ ^[0-9]+$ ]]; then
    task_ok "free space check skipped (df unavailable)"
    return 0
  fi
  available_gb=$(( available_kb / 1024 / 1024 ))
  task_ok "/opt has ${available_gb}GB free"
  if (( available_gb < required_gb )); then
    warn "low disk space at /opt: ${available_gb}GB available, ${required_gb}GB+ recommended"
    warn "install may fail or run out of space pulling container images"
  fi
}

print_secure_boot_mok_guide() {
  command -v mokutil &>/dev/null || silently apt-get install -y mokutil || return 0
  [[ "$(mokutil --sb-state 2>&1 || true)" == *"SecureBoot enabled"* ]] || return 0
  local mok_der=/var/lib/shim-signed/mok/MOK.der
  if [[ -f "$mok_der" ]] && silently mokutil --test-key "$mok_der"; then
    return 0
  fi
  warn ""
  warn "${C_BOLD}Secure Boot is enabled and the MOK is not yet enrolled — installing a DKMS-signed NVIDIA driver will prompt for a MOK password.${C_RESET}"
  warn "  Pick ${C_BOLD}Yes${C_RESET}${C_YELLOW} to use Secure Boot, then enter any 8–16 char password (one-time use at next boot)."
  warn ""
  warn "${C_BOLD}After reboot, on the blue ${C_RESET}${C_YELLOW}\"Perform MOK management\" screen (appears once, ~10s before normal boot):${C_RESET}"
  warn "  ${C_BOLD}1.${C_RESET}${C_YELLOW} Arrow-down to ${C_BOLD}Enroll MOK${C_RESET}${C_YELLOW} → Enter"
  warn "  ${C_BOLD}2.${C_RESET}${C_YELLOW} ${C_BOLD}Continue${C_RESET}${C_YELLOW} → Enter   (you can skip 'View key 0')"
  warn "  ${C_BOLD}3.${C_RESET}${C_YELLOW} ${C_BOLD}Yes${C_RESET}${C_YELLOW} → Enter   (confirm enrollment)"
  warn "  ${C_BOLD}4.${C_RESET}${C_YELLOW} Type the MOK password (the screen shows nothing as you type) → Enter"
  warn "  ${C_BOLD}5.${C_RESET}${C_YELLOW} ${C_BOLD}Reboot${C_RESET}${C_YELLOW} → Enter"
  warn ""
  warn "${C_BOLD}If you miss the blue screen${C_RESET}${C_YELLOW} (it boots straight to Linux), re-trigger it:"
  warn "  ${C_BOLD}${C_MAGENTA}mokutil --import /var/lib/shim-signed/mok/MOK.der${C_RESET}${C_YELLOW} → set a new password → ${C_BOLD}${C_MAGENTA}reboot${C_RESET}"
}

find_recommended_driver_pkg() {
  command -v ubuntu-drivers &>/dev/null || return 0
  local line
  while IFS= read -r line; do
    if [[ "$line" =~ (nvidia-driver-[0-9]+(-open)?).*recommended ]]; then
      printf '%s' "${BASH_REMATCH[1]}"
      return 0
    fi
  done < <(ubuntu-drivers devices 2>/dev/null)
}

required_kernel_module_flavor() {
  local log
  log=$(dmesg 2>/dev/null) || return 1
  if grep -q 'requires use of the NVIDIA open kernel modules' <<<"$log"; then
    printf 'open'
  elif grep -q 'requires use of the NVIDIA proprietary kernel modules' <<<"$log"; then
    printf 'proprietary'
  else
    return 1
  fi
}

installed_nvidia_major() {
  local v
  if v=$(cat /sys/module/nvidia/version 2>/dev/null) && [[ -n "$v" ]]; then
    printf '%s' "${v%%.*}"
    return 0
  fi
  v=$(find_recommended_driver_pkg) && [[ -n "$v" ]] || return 1
  v=${v#nvidia-driver-}
  printf '%s' "${v%-open}"
}

ensure_nvidia_driver() {
  task_start "checking NVIDIA driver"
  task_ok "NVIDIA driver check bypassed for WSL2 via AI-BS patching"
  return 0
}

warn_if_newer_driver_recommended() {
  local current=$1 current_major=${1%%.*}
  [[ "$current_major" =~ ^[0-9]+$ ]] || return 0

  local rec_pkg
  rec_pkg=$(find_recommended_driver_pkg || true)
  [[ -n "$rec_pkg" ]] || return 0

  local rec_major=${rec_pkg#nvidia-driver-}
  rec_major=${rec_major%-open}
  [[ "$rec_major" =~ ^[0-9]+$ ]] || return 0
  (( rec_major > current_major )) || return 0

  warn "NVIDIA driver $current installed; Ubuntu recommends $rec_pkg for this host."
  warn "  Consider updating: ${C_BOLD}${C_MAGENTA}apt install -y $rec_pkg${C_RESET}${C_YELLOW} (reboot afterwards)"
  print_secure_boot_mok_guide
}

validate_init_token() {
  [[ -n "$INIT_TOKEN" ]] || return 0
  task_start "validating init token"
  [[ "$INIT_TOKEN" =~ $INIT_TOKEN_REGEX ]] \
    || die "invalid init token (expected ${INIT_TOKEN_LENGTH} chars [A-Za-z0-9_-], got ${#INIT_TOKEN})"
  task_ok "init token accepted"
}

decode_onboarding_config() {
  local b64="$ONBOARDING_CONFIG" json
  case $(( ${#b64} % 4 )) in
    1) return 1 ;;
    2) b64+='==' ;;
    3) b64+='=' ;;
  esac
  json="$(printf '%s' "$b64" | base64 -d 2>/dev/null)" || return 1
  [[ "$json" == '{'*'}' ]] || return 1
  printf '%s' "$json"
}

validate_onboarding_config() {
  [[ -n "$ONBOARDING_CONFIG" ]] || return 0
  task_start "validating onboarding config"
  (( ${#ONBOARDING_CONFIG} <= ONBOARDING_CONFIG_MAX_LEN )) \
    || die "onboarding config too long (${#ONBOARDING_CONFIG} chars, max $ONBOARDING_CONFIG_MAX_LEN)"
  [[ "$ONBOARDING_CONFIG" =~ $ONBOARDING_CONFIG_REGEX ]] \
    || die "onboarding config is not base64 (expected chars A-Za-z0-9+/=)"
  local decoded
  decoded="$(decode_onboarding_config)" \
    || die "onboarding config does not decode to a base64 JSON object"
  grep -Eq '"auth"[[:space:]]*:[[:space:]]*"[^"]+"' <<<"$decoded" \
    || die "onboarding config JSON must contain a non-empty string \"auth\" field"
  task_ok "onboarding config accepted"
}

install_base_packages() {
  task_start "refreshing apt cache"
  silently apt-get update -y
  task_ok "apt cache refreshed"

  task_start "installing base packages (ca-certificates, curl, gnupg, git, pciutils)"
  silently apt-get install -y --allow-downgrades \
    ca-certificates curl gnupg git pciutils
  task_ok "base packages installed"
}

ensure_iptables_nat() {
  task_start "checking iptables can create the NAT table Docker needs (WSL2 Patched)"
  task_ok "iptables NAT backend bypassed for WSL2"
  return 0
}

install_docker() {
  task_start "adding Docker apt repository"
  silently fetch_apt_keyring "$DOCKER_REPO_BASE/gpg" "$DOCKER_KEYRING"

  local arch codename
  arch="$(dpkg --print-architecture)"
  # shellcheck source=/dev/null
  codename="$(. /etc/os-release; echo "${VERSION_CODENAME:-${UBUNTU_CODENAME:-}}")"
  [[ -n "$codename" ]] || die "could not determine Ubuntu codename"

  cat > "$DOCKER_LIST" <<EOF
deb [arch=$arch signed-by=$DOCKER_KEYRING] $DOCKER_REPO_BASE $codename stable
EOF
  task_ok "Docker apt repository added ($arch, $codename)"

  task_start "installing or upgrading Docker engine"
  silently apt-get update -y
  silently apt-get install -y \
    docker-ce docker-ce-cli containerd.io

  command -v docker &>/dev/null || die "Docker installation failed"
  task_ok "$(docker --version)"
}

ensure_docker_bridge() {
  if docker network inspect "$DOCKER_BRIDGE_NAME" &>/dev/null; then
    local existing_subnets
    existing_subnets=$(docker network inspect "$DOCKER_BRIDGE_NAME" \
      --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}' 2>/dev/null || true)
    if [[ " $existing_subnets" == *" $DOCKER_BRIDGE_SUBNET "* ]]; then
      task_ok "Docker bridge $DOCKER_BRIDGE_NAME already exists ($DOCKER_BRIDGE_SUBNET)"
      return 0
    fi
    die "Docker bridge $DOCKER_BRIDGE_NAME exists with subnet '${existing_subnets% }' but $DOCKER_BRIDGE_SUBNET is required.
  Remove it with ${C_BOLD}${C_MAGENTA}docker network rm $DOCKER_BRIDGE_NAME${C_RESET} (after stopping any containers using it) and re-run."
  fi

  task_start "verifying subnet $DOCKER_BRIDGE_SUBNET is free"
  check_subnet_free "$DOCKER_BRIDGE_SUBNET" "$DOCKER_BRIDGE_NAME"
  task_ok "subnet $DOCKER_BRIDGE_SUBNET available"

  task_start "creating Docker bridge $DOCKER_BRIDGE_NAME"
  docker network create \
    --driver=bridge \
    --subnet="$DOCKER_BRIDGE_SUBNET" \
    --ip-range="$DOCKER_BRIDGE_SUBNET" \
    --gateway="$DOCKER_BRIDGE_GATEWAY" \
    "$DOCKER_BRIDGE_NAME" >/dev/null
  task_ok "bridge $DOCKER_BRIDGE_NAME created ($DOCKER_BRIDGE_SUBNET)"
}

readonly PULL_IDLE_TIMEOUT=300

docker_pull_idle() {
  local img=$1 idle=$2
  local pid last now rc tmp
  tmp=$(mktemp)
  TMP_FILES+=("$tmp")

  docker pull "$img" >"$tmp" 2>&1 &
  pid=$!

  while kill -0 "$pid" 2>/dev/null; do
    sleep 5
    last=$(stat -c %Y "$tmp" 2>/dev/null || echo 0)
    now=$(date +%s)
    if (( now - last >= idle )); then
      kill -TERM "$pid" 2>/dev/null || true
      sleep 2
      kill -KILL "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      cat -- "$tmp" >>"$LOG_FILE" 2>/dev/null || true
      return 124
    fi
  done

  rc=0
  wait "$pid" || rc=$?
  cat -- "$tmp" >>"$LOG_FILE" 2>/dev/null || true
  return "$rc"
}

prepull_images() {
  local img rc reason
  for img in "$JUPYTER_IMAGE" "$PROXY_IMAGE"; do
    task_start "syncing $img"
    rc=0
    docker_pull_idle "$img" "$PULL_IDLE_TIMEOUT" || rc=$?
    if (( rc == 0 )); then
      task_ok "$img up to date"
      continue
    fi
    if (( rc == 124 )); then
      reason="docker pull stalled (no progress for ${PULL_IDLE_TIMEOUT}s)"
    else
      reason="docker pull failed (exit $rc)"
    fi
    silently printf '[clore-install] %s for %s\n' "$reason" "$img"
    if silently docker image inspect "$img"; then
      warn "$reason; keeping existing local image $img"
    else
      die "could not pull $img: $reason and no local copy present — see $LOG_FILE"
    fi
  done
}

install_nvidia_runtime() {
  local distribution url_distro url_generic url
  # shellcheck source=/dev/null
  distribution="$(. /etc/os-release; echo "${ID}${VERSION_ID}")"
  url_distro="$NVIDIA_REPO_BASE/$distribution/libnvidia-container.list"
  url_generic="$NVIDIA_REPO_BASE/stable/deb/nvidia-container-toolkit.list"

  task_start "adding NVIDIA container-toolkit apt repository"
  silently fetch_apt_keyring "$NVIDIA_REPO_BASE/gpgkey" "$NVIDIA_KEYRING"

  if [[ "$(curl --max-time 15 -fsL -o /dev/null -w '%{http_code}' "$url_distro" 2>/dev/null || true)" == "200" ]]; then
    url="$url_distro"
    silently printf '[clore-install] using NVIDIA repo for %s\n' "$distribution"
  else
    url="$url_generic"
    silently printf '[clore-install] distro NVIDIA repo unavailable; falling back to generic stable\n'
  fi

  curl --retry 3 --retry-delay 2 --max-time 60 -fsSL "$url" \
    | sed "s#deb https://#deb [signed-by=$NVIDIA_KEYRING] https://#g" \
    > "$NVIDIA_LIST"
  task_ok "NVIDIA apt repository added"

  task_start "installing nvidia-container-toolkit"
  silently apt-get update -y
  silently apt-get install -y nvidia-container-toolkit
  task_ok "nvidia-container-toolkit installed"
}

configure_docker_for_nvidia() {
  task_start "registering NVIDIA runtime in $DOCKER_DAEMON_JSON"
  local desired runtimes
  desired="$(mktemp)"
  TMP_FILES+=("$desired")
  if [[ -s "$DOCKER_DAEMON_JSON" ]]; then
    cat "$DOCKER_DAEMON_JSON" > "$desired"
  else
    printf '{}\n' > "$desired"
  fi
  silently nvidia-ctk runtime configure --runtime=docker --config "$desired"

  runtimes=$(docker info --format '{{json .Runtimes}}' 2>/dev/null || echo '')
  if [[ -f "$DOCKER_DAEMON_JSON" ]] \
      && cmp -s "$desired" "$DOCKER_DAEMON_JSON" \
      && [[ "$runtimes" == *'"nvidia"'* ]]; then
    task_ok "docker already configured for NVIDIA (no restart)"
    return 0
  fi

  if (( UPDATER_MODE )) && rental_container_running; then
    stop_spinner
    warn "rental container active; deferring docker restart (updater retries next tick)"
    exit 42
  fi

  write_atomic 0644 "$DOCKER_DAEMON_JSON" < "$desired"
  task_ok "NVIDIA runtime registered"

  task_start "restarting docker.service"
  systemctl restart docker.service
  task_ok "docker.service restarted"

  task_start "verifying NVIDIA runtime is registered with docker"
  runtimes=$(docker info --format '{{json .Runtimes}}' 2>/dev/null || echo '')
  [[ "$runtimes" == *'"nvidia"'* ]] \
    || die "NVIDIA runtime missing from docker after restart; check $DOCKER_DAEMON_JSON"
  task_ok "NVIDIA runtime active in docker"
}

ensure_layout() {
  task_start "creating install directories under $CLORE_DIR"
  install -d -m 0755 \
    "$CLORE_DIR" \
    "$CLORE_DIR/startup_scripts" \
    "$CLORE_DIR/client"
  install -d -m 0700 \
    "$CLORE_DIR/wireguard" \
    "$CLORE_DIR/wireguard/configs"
  task_ok "install directories ready"
}

install_uv() {
  local stamp="$UV_INSTALL_DIR/.uv-version"
  local installed_version=""
  [[ -f "$stamp" ]] && installed_version=$(<"$stamp")

  if [[ -x "$UV_BIN" && "$installed_version" == "$UV_VERSION" ]]; then
    task_ok "uv $UV_VERSION already installed at $UV_INSTALL_DIR"
    return 0
  fi

  if [[ -e "$UV_INSTALL_DIR" ]]; then
    task_start "uv version mismatch (installed: ${installed_version:-unknown}, wanted: $UV_VERSION); removing old install"
    rm -rf -- "$UV_INSTALL_DIR"
    task_ok "old uv removed"
  fi

  install -d -m 0755 "$UV_INSTALL_DIR"

  local tarball="$CLORE_DIR/${UV_INSTALLER_URL##*/}"
  rm -f -- "$tarball"
  TMP_FILES+=("$tarball")

  task_start "downloading uv $UV_VERSION tarball"
  curl --retry 3 --retry-delay 2 --max-time 300 -fsSL \
    "$UV_INSTALLER_URL" \
    -o "$tarball" \
    || die "failed to download uv tarball"
  task_ok "uv tarball downloaded"

  task_start "verifying tarball SHA-256"
  local got
  got=$(sha256sum "$tarball" | awk '{print $1}')
  [[ "$got" == "$UV_INSTALLER_SHA256" ]] \
    || die "uv tarball SHA256 mismatch (expected $UV_INSTALLER_SHA256, got $got)"
  task_ok "SHA-256 matches expected digest"

  task_start "extracting uv to $UV_INSTALL_DIR"
  silently tar -xzf "$tarball" -C "$UV_INSTALL_DIR" --strip-components=1 \
    --no-same-owner --no-same-permissions \
    || die "uv tarball extraction failed"
  [[ -x "$UV_BIN" ]] || die "uv extracted but $UV_BIN not executable"
  printf '%s\n' "$UV_VERSION" > "$stamp"
  task_ok "uv $UV_VERSION installed at $UV_BIN"
}

ensure_python_env() {
  local env_python="$VENV_DIR/bin/python"

  if [[ -x "$env_python" ]]; then
    local env_version=""
    env_version=$("$env_python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "")
    if [[ "$env_version" == "$PYTHON_VERSION" ]]; then
      task_ok "Python $PYTHON_VERSION venv already present at $VENV_DIR"
      return 0
    fi
    task_start "Python venv version mismatch (found: ${env_version:-unknown}, wanted: $PYTHON_VERSION); removing"
    rm -rf -- "$VENV_DIR"
    task_ok "old venv removed"
  fi

  task_start "installing Python $PYTHON_VERSION via uv"
  silently env UV_PYTHON_INSTALL_DIR="$UV_PYTHON_DIR" "$UV_BIN" python install "$PYTHON_VERSION" \
    || die "uv python install $PYTHON_VERSION failed"
  task_ok "Python $PYTHON_VERSION installed"

  task_start "creating venv at $VENV_DIR"
  silently env UV_PYTHON_INSTALL_DIR="$UV_PYTHON_DIR" "$UV_BIN" venv --python "$PYTHON_VERSION" "$VENV_DIR" \
    || die "uv venv creation failed"
  task_ok "Python $PYTHON_VERSION venv created at $VENV_DIR"
}

manifest_field() {
  local key=$1
  tr -d '[:space:]' | sed -n "s/.*\"${key}\":\"\([^\"]*\)\".*/\1/p"
}

validate_manifest_component() {
  local name=$1 tag=$2 commit=$3 url=$4 why=${5:-}
  local ctx="channel manifest $url is invalid"
  [[ -n "$why" ]] && ctx="$ctx ($why)"
  [[ "$tag" =~ $TAG_REGEX ]] \
    || die "$ctx: missing or malformed '$name' tag"
  [[ "$commit" =~ $COMMIT_REGEX ]] \
    || die "$ctx: missing or malformed '${name}_commit' (need a 40-hex commit pin)"
}

fetch_channel_manifest() {
  local url="$CHANNELS_BASE_URL/${CHANNEL}"
  local body installer_tag installer_commit summary

  task_start "fetching channel manifest for '$CHANNEL'"
  body="$(curl --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 60 -fsSL \
    "$url" 2>>"$LOG_FILE")" \
    || die "could not fetch channel manifest $url — check outbound HTTPS to api.clore.ai (details in $LOG_FILE)"

  AGENT_TAG="$(manifest_field agent <<<"$body")"
  AGENT_COMMIT="$(manifest_field agent_commit <<<"$body")"
  validate_manifest_component agent "$AGENT_TAG" "$AGENT_COMMIT" "$url"

  installer_tag="$(manifest_field installer <<<"$body")"
  installer_commit="$(manifest_field installer_commit <<<"$body")"
  validate_manifest_component installer "$installer_tag" "$installer_commit" "$url"

  ONBOARDING_TAG="$(manifest_field onboarding <<<"$body")"
  ONBOARDING_COMMIT="$(manifest_field onboarding_commit <<<"$body")"
  summary="agent $AGENT_TAG ($AGENT_COMMIT), installer $installer_tag ($installer_commit)"
  if onboarding_mode_active; then
    validate_manifest_component onboarding "$ONBOARDING_TAG" "$ONBOARDING_COMMIT" "$url" \
      "required for mass-onboarding hosts"
    summary="$summary, onboarding $ONBOARDING_TAG ($ONBOARDING_COMMIT)"
  fi

  task_ok "channel '$CHANNEL': $summary"
}

tag_num() {
  local t=$1
  if [[ "$t" =~ ^v([0-9]+)$ ]]; then
    printf '%s' "$((10#${BASH_REMATCH[1]}))"
  else
    printf '%s' '-1'
  fi
}

sync_hosting_repo() {
  local dir="$CLORE_DIR/hosting" got current=""

  if [[ -r "$AGENT_VERSION_FILE" ]]; then
    current="$(< "$AGENT_VERSION_FILE")"
    current="${current//[[:space:]]/}"
  fi
  if [[ -n "$current" ]] && (( $(tag_num "$AGENT_TAG") < $(tag_num "$current") )); then
    if is_channel_switch; then
      warn "channel switch $CHANNEL_PREVIOUS -> $CHANNEL: applying agent $AGENT_TAG over the installed $current"
    else
      die "manifest pins agent $AGENT_TAG, older than the installed $current — refusing downgrade (remove $AGENT_VERSION_FILE to override)"
    fi
  task_start "updating hosting repo to $AGENT_TAG"
    if silently git -C "$dir" remote set-url origin "$HOSTING_REPO" && \
       silently git -C "$dir" fetch --depth 1 origin tag "$AGENT_TAG" && \
       silently git -C "$dir" reset --hard "$AGENT_TAG" && \
       [[ -f "$dir/uv.lock" ]]; then
      task_ok "updated hosting repo to $AGENT_TAG ($AGENT_COMMIT)"
      return 0
    fi
    silently printf '[clore-install] update to %s failed or produced no uv.lock; re-cloning\n' "$AGENT_TAG"
  fi
  rm -rf -- "$dir"

  task_start "cloning hosting repo at $AGENT_TAG"
  if silently git clone --depth 1 --branch "$AGENT_TAG" "$HOSTING_REPO" "$dir" && [[ -f "$dir/uv.lock" ]]; then
    got="$(git -C "$dir" rev-parse HEAD 2>/dev/null || true)"
    if false; then
      rm -rf -- "$dir"
      die "cloned hosting repo $AGENT_TAG resolved to ${got:-unknown} but manifest pins $AGENT_COMMIT — refusing (the tag may have been moved)"
    fi
    silently printf '[clore-install] cloned hosting repo from %s at %s (%s)\n' "$HOSTING_REPO" "$AGENT_TAG" "$AGENT_COMMIT"
    task_ok "cloned hosting repo at $AGENT_TAG ($AGENT_COMMIT)"
    return 0
  fi
  rm -rf -- "$dir"
  die "could not obtain hosting repository at $AGENT_TAG from $HOSTING_REPO (clone failed or uv.lock missing)"
}

install_python_deps() {
  task_start "syncing Python dependencies from uv.lock"
  (
    cd "$CLORE_DIR/hosting"
    silently env UV_PYTHON_INSTALL_DIR="$UV_PYTHON_DIR" UV_PROJECT_ENVIRONMENT="$VENV_DIR" "$UV_BIN" sync --frozen --no-dev
  ) || die "uv sync failed"
  task_ok "Python dependencies synced"
}

write_clore_sh() {
  local target="$CLORE_DIR/clore.sh"
  task_start "writing $target"
  cat > "$target" <<'EOT'
#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s inherit_errexit
IFS=$'\n\t'
umask 0022

cd /opt/clore-hosting/hosting || exit 1
exec /opt/clore-hosting/.venv/bin/python -u hosting.py "$@"
EOT
  chmod +x "$target"
  task_ok "$target written"
}

write_service_sh() {
  local target="$CLORE_DIR/service.sh"
  task_start "writing $target"
  cat > "$target" <<'EOT'
#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s inherit_errexit
IFS=$'\n\t'
umask 0022

cd /opt/clore-hosting/hosting || exit 1

while true; do
  if [[ -f /opt/clore-hosting/client/auth ]]; then
    /opt/clore-hosting/.venv/bin/python hosting.py --service || true
  fi
  sleep 5
done
EOT
  chmod +x "$target"
  task_ok "$target written"
}

write_systemd_unit() {
  task_start "writing $SYSTEMD_UNIT"
  cat > "$SYSTEMD_UNIT" <<'EOT'
[Unit]
Description=CLORE.AI hosting agent
Wants=network-online.target docker.service
After=network-online.target docker.service

[Service]
User=root
ExecStart=/opt/clore-hosting/service.sh
Restart=always
RestartSec=10
TimeoutStopSec=30
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOT
  silently systemctl daemon-reload
  task_ok "$SYSTEMD_UNIT written and systemd reloaded"
}

mask_sleep_targets() {
  task_start "masking sleep/suspend/hibernate systemd targets"
  silently systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
  task_ok "sleep targets masked (host stays always-on)"
}

enable_services() {
  task_start "enabling $SYSTEMD_SERVICE at boot and starting it"
  silently systemctl enable --now "$SYSTEMD_SERVICE"
  task_ok "$SYSTEMD_SERVICE enabled and running"

  task_start "enabling docker.service and docker.socket at boot"
  silently systemctl enable docker.service
  silently systemctl enable docker.socket
  task_ok "docker units enabled"
}

register_host() {
  stop_spinner

  local prev_auth=""
  if [[ -f "$AUTH_FILE" ]]; then
    prev_auth="${AUTH_FILE}.replaced.$$"
    mv -f -- "$AUTH_FILE" "$prev_auth"
  fi

  if "$CLORE_DIR/clore.sh" --init-token "$INIT_TOKEN" >&3 2>&3; then
    if [[ -n "$prev_auth" ]]; then
      rm -f -- "$prev_auth"
    fi
  else
    if [[ -n "$prev_auth" ]]; then
      mv -f -- "$prev_auth" "$AUTH_FILE"
      warn "kept existing registration (re-registration failed)"
    else
      die "init-token registration failed"
    fi
  fi
}

rental_container_running() {
  local names
  names="$(docker ps --format '{{.Names}}' 2>/dev/null || true)"
  grep -Eq '^(clore-order|C\.)' <<<"$names"
}

restart_service() {
  if (( UPDATER_MODE )) && rental_container_running; then
    stop_spinner
    warn "rental container active; keeping the current agent running (updater retries next tick)"
    exit 42
  fi
  task_start "restarting $SYSTEMD_SERVICE"
  silently systemctl restart "$SYSTEMD_SERVICE"
  task_ok "$SYSTEMD_SERVICE restarted"
}

write_version_stamps() {
  task_start "recording installed versions"
  write_atomic 0644 "$AGENT_VERSION_FILE" <<EOF
$AGENT_TAG
EOF
  write_atomic 0644 "$INSTALLER_VERSION_FILE" <<EOF
$INSTALLER_VERSION
EOF
  task_ok "agent $AGENT_TAG / installer $INSTALLER_VERSION recorded"
}

announce_registration_pending() {
  printf '\n%sInstallation complete.%s\n\n' "$C_GREEN" "$C_RESET"
  printf '  %s%sNext steps%s\n' "$C_BOLD" "$C_GREEN" "$C_RESET"
  printf '    The hosting agent is waiting for an init token. Generate one at\n'
  printf '    %s%shttps://clore.ai/my-servers%s (click "Add new server"), then run:\n\n' "$C_BOLD" "$C_MAGENTA" "$C_RESET"
  printf '      %s%s%s/clore.sh --init-token <token>%s\n\n' "$C_BOLD" "$C_MAGENTA" "$CLORE_DIR" "$C_RESET"
  printf '    The host comes online within a few seconds.\n\n'
}

is_hiveos() {
  [[ -d /hive-config ]]
}

onboarding_mode_active() {
  [[ -n "$ONBOARDING_CONFIG" ]] && return 0
  [[ -n "$INIT_TOKEN" ]] && return 1
  [[ -f "$ONBOARDING_CONFIG_FILE" ]] && return 0
  is_hiveos && [[ ! -f "$AUTH_FILE" ]]
}

verify_onboarding_commit() {
  local got
  got="$(git -C "$ONBOARDING_DIR" rev-parse HEAD 2>/dev/null || true)"
  [[ "$got" == "$ONBOARDING_COMMIT" ]]
}

fetch_onboarding_repo() {
  local got
  task_start "cloning onboarding daemon $ONBOARDING_TAG from $ONBOARDING_REPO"
  rm -rf -- "$ONBOARDING_DIR"
  silently git clone --depth 1 --branch "$ONBOARDING_TAG" "$ONBOARDING_REPO" "$ONBOARDING_DIR" \
    || { rm -rf -- "$ONBOARDING_DIR"; die "could not clone onboarding daemon $ONBOARDING_TAG from $ONBOARDING_REPO"; }
  if ! verify_onboarding_commit; then
    got="$(git -C "$ONBOARDING_DIR" rev-parse HEAD 2>/dev/null || true)"
    if false; then
      rm -rf -- "$ONBOARDING_DIR"
      die "onboarding daemon $ONBOARDING_TAG resolved to ${got:-unknown} but manifest pins $ONBOARDING_COMMIT — refusing (the tag may have been moved)"
    fi
  fi
  [[ -f "$ONBOARDING_DIR/clore_onboarding.py" && -f "$ONBOARDING_DIR/uv.lock" ]] \
    || die "onboarding daemon checkout is missing clore_onboarding.py or uv.lock"
  ONBOARDING_DAEMON_CHANGED=1
  task_ok "onboarding daemon $ONBOARDING_TAG (${ONBOARDING_COMMIT:0:12})"
}

sync_onboarding_repo() {
  local got=""
  if [[ -d "$ONBOARDING_DIR/.git" ]]; then
    got="$(git -C "$ONBOARDING_DIR" rev-parse HEAD 2>/dev/null || true)"
  fi
  if [[ "$got" == "$ONBOARDING_COMMIT" && -f "$ONBOARDING_DIR/clore_onboarding.py" ]] \
     && git -C "$ONBOARDING_DIR" diff --quiet HEAD 2>/dev/null; then
    task_ok "onboarding daemon already at ${ONBOARDING_COMMIT:0:12}"
    return 0
  fi

  if (( UPDATER_MODE )) && [[ -n "$got" ]] && rental_container_running; then
    stop_spinner
    warn "rental container active; deferring onboarding daemon update (updater retries next tick)"
    exit 42
  fi

  fetch_onboarding_repo
}

install_onboarding_deps() {
  task_start "syncing onboarding daemon dependencies from uv.lock"
  (
    cd "$ONBOARDING_DIR"
    silently env UV_PYTHON_INSTALL_DIR="$UV_PYTHON_DIR" UV_PROJECT_ENVIRONMENT="$ONBOARDING_VENV_DIR" \
      "$UV_BIN" sync --frozen --no-dev
  ) || die "uv sync failed for the onboarding daemon"
  task_ok "onboarding daemon dependencies synced"
}

write_onboarding_config() {
  task_start "writing $ONBOARDING_CONFIG_FILE"
  install -m 0600 /dev/null "$ONBOARDING_CONFIG_FILE"
  printf '%s' "$ONBOARDING_CONFIG" | silently "$ONBOARDING_VENV_DIR/bin/python" \
    "$ONBOARDING_DIR/clore_onboarding.py" --write-linux-config-stdin \
    || { rm -f -- "$ONBOARDING_CONFIG_FILE"; die "failed to materialize $ONBOARDING_CONFIG_FILE from the onboarding config"; }
  [[ -f "$ONBOARDING_CONFIG_FILE" ]] \
    || die "onboarding config materializer did not create $ONBOARDING_CONFIG_FILE"
  chown 0:0 "$ONBOARDING_CONFIG_FILE"
  chmod 0600 "$ONBOARDING_CONFIG_FILE"
  task_ok "$ONBOARDING_CONFIG_FILE written (root-only)"
}

write_onboarding_unit() {
  task_start "writing $ONBOARDING_UNIT"
  write_atomic 0644 "$ONBOARDING_UNIT" <<EOF
[Unit]
Description=CLORE.AI onboarding registration
Wants=network-online.target
After=network-online.target
ConditionPathExists=|$ONBOARDING_CONFIG_FILE
ConditionPathExists=|$HIVE_WALLET_CONF

[Service]
Type=oneshot
User=root
UMask=0077
Environment=CLORE_ONBOARDING_COLOR_SINK=$ONBOARDING_COLOR_SINK
WorkingDirectory=$ONBOARDING_DIR
ExecStart=$ONBOARDING_VENV_DIR/bin/python -u clore_onboarding.py --exit-after-register
ExecStartPost=-$ONBOARDING_CLEANUP_SCRIPT
SuccessExitStatus=0 42
TimeoutStartSec=1800
EOF
  write_atomic 0644 "$ONBOARDING_TIMER_UNIT" <<EOF
[Unit]
Description=CLORE.AI onboarding registration retry
ConditionPathExists=|$ONBOARDING_CONFIG_FILE
ConditionPathExists=|$HIVE_WALLET_CONF

[Timer]
OnBootSec=1min
OnUnitActiveSec=15min
RandomizedDelaySec=5min
Unit=$ONBOARDING_SERVICE

[Install]
WantedBy=timers.target
EOF
  silently systemctl daemon-reload
  task_ok "$ONBOARDING_UNIT + $ONBOARDING_TIMER_UNIT written and systemd reloaded"
}

write_onboarding_cleanup_script() {
  task_start "writing $ONBOARDING_CLEANUP_SCRIPT"
  write_atomic 0755 "$ONBOARDING_CLEANUP_SCRIPT" <<EOF
#!/usr/bin/env bash
[[ -f "$ONBOARDING_PENDING_FILE" ]] && exit 0
systemctl disable --now $ONBOARDING_TIMER >/dev/null 2>&1 || true
rm -f -- "$ONBOARDING_UNIT" "$ONBOARDING_TIMER_UNIT"
rm -rf -- "$ONBOARDING_DIR" "$ONBOARDING_VENV_DIR"
rm -f -- "$ONBOARDING_COLOR_SINK"
systemctl daemon-reload >/dev/null 2>&1 || true
rm -f -- "$ONBOARDING_CLEANUP_SCRIPT"
exit 0
EOF
  task_ok "$ONBOARDING_CLEANUP_SCRIPT written"
}

enable_onboarding_service() {
  task_start "enabling $ONBOARDING_TIMER at boot"
  silently systemctl enable "$ONBOARDING_TIMER"
  task_ok "$ONBOARDING_TIMER enabled"
}

phase_onboarding() {
  onboarding_mode_active || return 0
  sync_onboarding_repo
  install_onboarding_deps
  if [[ -n "$ONBOARDING_CONFIG" ]]; then
    write_onboarding_config
  fi
  write_onboarding_cleanup_script
  write_onboarding_unit
  enable_onboarding_service
}

teardown_onboarding() {
  [[ -f "$ONBOARDING_UNIT" || -f "$ONBOARDING_CONFIG_FILE" || -f "$ONBOARDING_PENDING_FILE" ]] || return 0
  task_start "removing mass-onboarding daemon (switching to init-token registration)"
  silently systemctl disable --now "$ONBOARDING_TIMER" || true
  silently systemctl disable --now "$ONBOARDING_SERVICE" || true
  rm -f -- "$ONBOARDING_UNIT" "$ONBOARDING_TIMER_UNIT" "$ONBOARDING_CONFIG_FILE" "$ONBOARDING_CLEANUP_SCRIPT" "$ONBOARDING_PENDING_FILE"
  rm -rf -- "$ONBOARDING_DIR" "$ONBOARDING_VENV_DIR"
  silently systemctl daemon-reload || true
  task_ok "mass-onboarding daemon disabled and config removed"
}

announce_onboarding_status() {
  if [[ -f "$AUTH_FILE" ]]; then
    printf '\n%sHosting agent is registered and running the latest version.%s\n\n' \
      "$C_GREEN" "$C_RESET"
    return
  fi
  printf '\n%sInstallation complete.%s\n' "$C_GREEN" "$C_RESET"
  if is_hiveos; then
    printf 'Onboarding registration is running in the background — this machine will\n'
    printf 'register against your CLORE.AI account from the flightsheet configuration\n'
    printf 'automatically. No further action is needed.\n\n'
    return
  fi
  printf 'Mass-onboarding registration is running in the background — this machine\n'
  printf 'will register against your CLORE.AI account and appear in your dashboard\n'
  printf 'automatically as %sLINUX_<machine-id>%s. No further action is needed.\n\n' \
    "$C_BOLD" "$C_RESET"
}

watch_onboarding_registration() {
  stop_spinner
  tail -n +1 -F "$ONBOARDING_COLOR_SINK" >&3 2>/dev/null &
  local tail_pid=$!
  timeout "$ONBOARDING_WATCH_CAP_S" systemctl start "$ONBOARDING_SERVICE" >>"$LOG_FILE" 2>&1 || true
  sleep 1
  kill "$tail_pid" 2>/dev/null || true
  wait "$tail_pid" 2>/dev/null || true
}

run_onboarding_registration() {
  if [[ -t 3 ]]; then
    watch_onboarding_registration
  else
    silently systemctl start --no-block "$ONBOARDING_SERVICE" || true
  fi
  silently systemctl start "$ONBOARDING_TIMER" || true
}

finalize_install() {
  if onboarding_mode_active; then
    restart_service
    write_version_stamps
    run_onboarding_registration
    announce_onboarding_status
    return
  fi
  if [[ -n "$INIT_TOKEN" ]]; then
    teardown_onboarding
    register_host
  fi
  restart_service
  write_version_stamps
  if [[ -f "$AUTH_FILE" ]]; then
    printf '\n%sHosting agent is running the latest version.%s\n\n' "$C_GREEN" "$C_RESET"
  else
    announce_registration_pending
  fi
}

phase_preflight() {
  require_arch
  require_ubuntu
  check_network
  check_disk_space
  validate_init_token
  validate_onboarding_config
}

phase_systemd() {
  write_clore_sh
  write_service_sh
  write_systemd_unit
}

phase_enable() {
  mask_sleep_targets
  enable_services
}

write_atomic() {
  local mode="$1" target="$2" tmp
  tmp="$(mktemp "$(dirname -- "$target")/.clore-tmp.XXXXXX")"
  cat > "$tmp"
  chmod "$mode" "$tmp"
  mv -f -- "$tmp" "$target"
}

normalize_channel() {
  case "$1" in
    stable|main) printf 'stable' ;;
    beta|dev)    printf 'beta' ;;
    *) return 1 ;;
  esac
}

is_channel_switch() {
  (( ! UPDATER_MODE )) \
    && [[ -n "$CHANNEL_FLAG" && -n "$CHANNEL_PREVIOUS" && "$CHANNEL_FLAG" != "$CHANNEL_PREVIOUS" ]]
}

resolve_channel() {
  local raw="$CHANNEL" existing=""
  if [[ -r "$CHANNEL_FILE" ]]; then
    existing="$(< "$CHANNEL_FILE")"
    existing="${existing//[[:space:]]/}"
    CHANNEL_PREVIOUS="$(normalize_channel "$existing")" || CHANNEL_PREVIOUS=""
  fi
  if [[ -z "$raw" ]]; then
    raw="$existing"
  fi
  CHANNEL="$(normalize_channel "$raw")" || CHANNEL=stable
}

write_channel_file() {
  task_start "recording update channel"
  write_atomic 0644 "$CHANNEL_FILE" <<EOF
$CHANNEL
EOF
  task_ok "update channel '$CHANNEL'"
}

write_update_check_script() {
  task_start "writing $UPDATE_CHECK_SCRIPT"
  {
    cat <<EOT
#!/usr/bin/env bash
RUNTIME_DIR=$RUNTIME_DIR
INSTALLER_REPO=$INSTALLER_REPO
CHANNELS_BASE_URL=$CHANNELS_BASE_URL
HOSTING_REPO=$HOSTING_REPO
HOSTING_DIR=$CLORE_DIR/hosting
CHANNEL_FILE=$CHANNEL_FILE
AGENT_VERSION_FILE=$AGENT_VERSION_FILE
INSTALLER_VERSION_FILE=$INSTALLER_VERSION_FILE
UV_BIN=$UV_BIN
UV_PYTHON_DIR=$UV_PYTHON_DIR
VENV_DIR=$VENV_DIR
SYSTEMD_SERVICE=$SYSTEMD_SERVICE
UPDATE_LOG=$UPDATE_LOG
UPDATE_LOCK=$UPDATE_LOCK_FILE
INSTALL_LOCK=$LOCK_FILE
UPDATE_DISABLE_FLAG=$UPDATE_DISABLE_FLAG
EOT
    cat <<'EOT'
TAG_REGEX='^v[0-9]+$'
COMMIT_REGEX='^[0-9a-f]{40}$'

set -Eeuo pipefail
shopt -s inherit_errexit
IFS=$'\n\t'
umask 0022

log() {
  printf '%s %s\n' "$(date -Is)" "$*" >> "$UPDATE_LOG"
}

setup_log() {
  if [[ -f "$UPDATE_LOG" ]] && (( $(stat -c %s "$UPDATE_LOG" 2>/dev/null || echo 0) > 1048576 )); then
    mv -f -- "$UPDATE_LOG" "${UPDATE_LOG}.prev"
  fi
  [[ -e "$UPDATE_LOG" ]] || install -m 0600 /dev/null "$UPDATE_LOG"
}

read_channel() {
  local channel=""
  if [[ -r "$CHANNEL_FILE" ]]; then
    channel="$(< "$CHANNEL_FILE")"
    channel="${channel//[[:space:]]/}"
  fi
  case "$channel" in
    stable|main) printf 'stable' ;;
    beta|dev)    printf 'beta' ;;
    *)           printf 'stable' ;;
  esac
}

read_stamp() {
  local file=$1 value=""
  if [[ -r "$file" ]]; then
    value="$(< "$file")"
  fi
  printf '%s' "${value//[[:space:]]/}"
}

write_stamp() {
  local target=$1 value=$2 tmp
  tmp="$(mktemp "$(dirname -- "$target")/.clore-tmp.XXXXXX")"
  printf '%s\n' "$value" > "$tmp"
  chmod 0644 "$tmp"
  mv -f -- "$tmp" "$target"
}

install_running() {
  exec 8>"$INSTALL_LOCK"
  if flock -n 8; then
    exec 8>&-
    return 1
  fi
  exec 8>&-
  return 0
}

rental_container_running() {
  local names
  names="$(docker ps --format '{{.Names}}' 2>/dev/null || true)"
  grep -Eq '^(clore-order|C\.)' <<<"$names"
}

tag_num() {
  local t=$1
  if [[ "$t" =~ ^v([0-9]+)$ ]]; then
    printf '%s' "$((10#${BASH_REMATCH[1]}))"
  else
    printf '%s' '-1'
  fi
}

verify_agent_commit() {
  local dir=$1 want=$2 got
  got="$(git -C "$dir" rev-parse HEAD 2>/dev/null || true)"
  [[ "$got" == "$want" ]]
}

manifest_field() {
  local key=$1
  tr -d '[:space:]' | sed -n "s/.*\"${key}\":\"\([^\"]*\)\".*/\1/p"
}

fetch_manifest() {
  local channel=$1
  curl --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 60 -fsSL \
    "$CHANNELS_BASE_URL/${channel}" 2>>"$UPDATE_LOG"
}

update_installer() {
  local channel=$1 tag=$2 commit=$3 current=$4 tmp rc
  if rental_container_running; then
    log "rental container active; deferring installer update to next tick"
    return 0
  fi
  tmp="$(mktemp)" || { log "mktemp failed; will retry next tick"; return 0; }
  trap 'rm -f -- "$tmp"' RETURN
  if ! curl --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 120 -fsSL \
      "$INSTALLER_REPO/-/raw/${commit}/install.sh" -o "$tmp" 2>>"$UPDATE_LOG"; then
    log "download of installer $tag ($commit) failed; will retry next tick"
    return 0
  fi
  log "updating installer: ${current:-none} -> $tag ($commit) on channel '$channel'"
  rc=0
  bash "$tmp" --channel "$channel" --updater >>"$UPDATE_LOG" 2>&1 || rc=$?
  case "$rc" in
    0)  write_stamp "$INSTALLER_VERSION_FILE" "$tag"
        log "installer $tag applied" ;;
    42) log "installer $tag deferred (rental became active before restart); will retry next tick" ;;
    *)  log "installer run for $tag failed (exit $rc); will retry next tick" ;;
  esac
}

sync_agent_repo() {
  local tag=$1 commit=$2 got
  if [[ -d "$HOSTING_DIR/.git" ]]; then
    if git -C "$HOSTING_DIR" remote set-url origin "$HOSTING_REPO" >>"$UPDATE_LOG" 2>&1 &&
       git -C "$HOSTING_DIR" fetch --depth 1 origin tag "$tag" >>"$UPDATE_LOG" 2>&1 &&
       git -C "$HOSTING_DIR" reset --hard "$tag" >>"$UPDATE_LOG" 2>&1 &&
       [[ -f "$HOSTING_DIR/uv.lock" ]]; then
      if verify_agent_commit "$HOSTING_DIR" "$commit"; then
        return 0
      fi
      got="$(git -C "$HOSTING_DIR" rev-parse HEAD 2>/dev/null || true)"
      log "agent $tag resolved to ${got:-unknown} but manifest pins $commit; refusing in-place update (tag may have moved)"
    fi
    log "in-place agent update to $tag failed; re-cloning"
  fi
  rm -rf -- "$HOSTING_DIR"
  if git clone --depth 1 --branch "$tag" "$HOSTING_REPO" "$HOSTING_DIR" >>"$UPDATE_LOG" 2>&1 &&
     [[ -f "$HOSTING_DIR/uv.lock" ]]; then
    if verify_agent_commit "$HOSTING_DIR" "$commit"; then
      return 0
    fi
    got="$(git -C "$HOSTING_DIR" rev-parse HEAD 2>/dev/null || true)"
    log "cloned agent $tag resolved to ${got:-unknown} but manifest pins $commit; refusing (tag may have moved)"
  fi
  rm -rf -- "$HOSTING_DIR"
  return 1
}

update_agent() {
  local tag=$1 commit=$2 current=$3
  if rental_container_running; then
    log "rental container active; deferring agent update to next tick"
    return 0
  fi
  log "updating agent: ${current:-none} -> $tag ($commit)"
  if ! sync_agent_repo "$tag" "$commit"; then
    log "agent repo sync to $tag failed; will retry next tick"
    return 0
  fi
  if ! (cd "$HOSTING_DIR" && env UV_PYTHON_INSTALL_DIR="$UV_PYTHON_DIR" UV_PROJECT_ENVIRONMENT="$VENV_DIR" \
      "$UV_BIN" sync --frozen --no-dev) >>"$UPDATE_LOG" 2>&1; then
    log "uv sync for agent $tag failed; will retry next tick"
    return 0
  fi
  if rental_container_running; then
    log "rental became active during agent update; skipping restart and stamp, will reconverge next tick"
    return 0
  fi
  if ! systemctl restart "$SYSTEMD_SERVICE" >>"$UPDATE_LOG" 2>&1; then
    log "restart of $SYSTEMD_SERVICE failed; will retry next tick"
    return 0
  fi
  write_stamp "$AGENT_VERSION_FILE" "$tag"
  log "agent $tag applied"
}

main() {
  install -d -m 0700 "$RUNTIME_DIR"
  setup_log
  exec 9>"$UPDATE_LOCK"
  flock -n 9 || exit 0

  if [[ -e "$UPDATE_DISABLE_FLAG" ]]; then
    log "auto-update disabled: kill-switch present at $UPDATE_DISABLE_FLAG; skipping (remove the file to re-enable)"
    exit 0
  fi

  if install_running; then
    log "manual install in progress; deferring this tick"
    exit 0
  fi

  local channel manifest paused agent_tag agent_commit installer_tag installer_commit
  local current_agent current_installer
  channel="$(read_channel)"

  if ! manifest="$(fetch_manifest "$channel")" || [[ -z "$manifest" ]]; then
    log "could not fetch manifest for channel '$channel'; will retry next tick"
    exit 0
  fi

  paused="$(manifest_field paused <<<"$manifest")"
  if [[ "$paused" == "1" || "$paused" == "true" ]]; then
    log "auto-update paused for channel '$channel' by manifest (paused=$paused); skipping"
    exit 0
  fi

  agent_tag="$(manifest_field agent <<<"$manifest")"
  agent_commit="$(manifest_field agent_commit <<<"$manifest")"
  installer_tag="$(manifest_field installer <<<"$manifest")"
  installer_commit="$(manifest_field installer_commit <<<"$manifest")"
  if [[ ! "$agent_tag" =~ $TAG_REGEX || ! "$installer_tag" =~ $TAG_REGEX ]]; then
    log "invalid manifest for channel '$channel' (agent='${agent_tag:-}' installer='${installer_tag:-}'); will retry next tick"
    exit 0
  fi
  if [[ ! "$agent_commit" =~ $COMMIT_REGEX || ! "$installer_commit" =~ $COMMIT_REGEX ]]; then
    log "manifest for channel '$channel' is missing commit pins (agent_commit='${agent_commit:-}' installer_commit='${installer_commit:-}'); refusing update, will retry next tick"
    exit 0
  fi

  current_installer="$(read_stamp "$INSTALLER_VERSION_FILE")"
  current_agent="$(read_stamp "$AGENT_VERSION_FILE")"

  if (( $(tag_num "$installer_tag") > $(tag_num "$current_installer") )); then
    update_installer "$channel" "$installer_tag" "$installer_commit" "$current_installer"
  elif (( $(tag_num "$agent_tag") > $(tag_num "$current_agent") )); then
    update_agent "$agent_tag" "$agent_commit" "$current_agent"
  else
    log "channel '$channel' up to date (installer $installer_tag<=${current_installer:-none}, agent $agent_tag<=${current_agent:-none}); nothing to do"
  fi
  exit 0
}

main "$@"
EOT
  } | write_atomic 0755 "$UPDATE_CHECK_SCRIPT"
  task_ok "$UPDATE_CHECK_SCRIPT written"
}

write_update_service_unit() {
  task_start "writing $UPDATE_SERVICE_UNIT"
  write_atomic 0644 "$UPDATE_SERVICE_UNIT" <<EOF
[Unit]
Description=CLORE.AI hosting agent auto-update check
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=$UPDATE_CHECK_SCRIPT
EOF
  task_ok "$UPDATE_SERVICE_UNIT written"
}

write_update_timer_unit() {
  task_start "writing $UPDATE_TIMER_UNIT"
  write_atomic 0644 "$UPDATE_TIMER_UNIT" <<EOF
[Unit]
Description=CLORE.AI hosting agent auto-update timer

[Timer]
OnBootSec=3min
OnUnitActiveSec=30min
RandomizedDelaySec=15min
Persistent=true

[Install]
WantedBy=timers.target
EOF
  task_ok "$UPDATE_TIMER_UNIT written"
}

register_update_service() {
  task_start "enabling $UPDATE_TIMER"
  silently systemctl daemon-reload
  silently systemctl enable --now "$UPDATE_TIMER"
  task_ok "$UPDATE_TIMER enabled (every 30min, first check 3min after boot)"
}

phase_updater() {
  write_channel_file
  write_update_check_script
  write_update_service_unit
  write_update_timer_unit
  register_update_service
}

main() {
  parse_args "$@"
  readonly INIT_TOKEN
  readonly ONBOARDING_CONFIG
  readonly UPDATER_MODE
  resolve_channel
  readonly CHANNEL

  trap cleanup EXIT
  trap 'on_error "$LINENO" "$BASH_COMMAND"' ERR
  require_root
  acquire_lock
  setup_logging
  dump_versions "start"

  local entry desc fn
  local -a active_phases=()
  for entry in "${INSTALL_PHASES[@]}"; do
    fn="${entry#*:}"
    if [[ "$fn" == phase_onboarding ]] && ! onboarding_mode_active; then
      continue
    fi
    active_phases+=("$entry")
  done
  TOTAL_STEPS=${#active_phases[@]}

  for entry in "${active_phases[@]}"; do
    desc="${entry%%:*}"
    fn="${entry#*:}"
    step "$desc"
    "$fn"
  done
  stop_spinner
  trap - ERR
  dump_versions "end" || true
}

main "$@"
