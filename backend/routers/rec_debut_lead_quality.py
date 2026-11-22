"""
Recreational Debut - Lead Quality Classifier

Separates real human engagement from machine-generated tracking events:
  * internal tests (our own devices / localhost / non-existent athletes)
  * security link scanners (duplicate same-second clicks, datacenter bursts)
  * link-preview fetchers (Google Messages / Gmail "X11; Linux" fetches, python-requests)
  * Apple Mail Privacy Protection auto-opens (bare "Mozilla/5.0" UA via iCloud relay)

Athlete-level tiers (best first):
  verified_click  - tapped a link from a real phone (iPhone / Android UA)
  possible_click  - desktop click that is not an obvious bot; confirm by phone
  real_open       - opened the email in Gmail / Yahoo / a real device
  auto_open       - only Apple Mail auto-loads; cannot confirm they read it
  bot_only        - only scanner / preview / bot activity
  none            - no tracking activity
"""

from collections import defaultdict

# Our own test devices / infrastructure. Events from these never count as leads.
TEST_IPS = {"38.131.234.4", "127.0.0.1", "::1", ""}
TEST_CAMPAIGNS = {"test_blast"}

TIER_ORDER = ["verified_click", "possible_click", "real_open", "auto_open", "bot_only", "none"]
REAL_TIERS = {"verified_click", "possible_click", "real_open"}

TIER_LABELS = {
    "verified_click": "Real - tapped link on phone",
    "possible_click": "Possible - desktop click, confirm",
    "real_open": "Real - opened email",
    "auto_open": "Auto-open only (Apple Mail)",
    "bot_only": "Bot / scanner only",
    "none": "No activity",
}


def _first_ip(ip):
    return (ip or "").split(",")[0].strip()


def _is_mobile(ua):
    return "iPhone" in ua or "Android" in ua or "iPad" in ua


def classify_events(events, valid_athlete_ids=None):
    """
    events: iterable of dicts with keys
        id, athlete_id, campaign_id, event_type, ip_address, user_agent, created_at
    Returns {event_id: label} where label is one of
        test, bot, human_click, possible_click, human_open, proxy_open, auto_open
    """
    events = sorted(events, key=lambda e: (e.get("created_at") or 0))
    labels = {}

    # Duplicate clicks: same athlete, same second -> scanner pre-fetch
    click_seconds = defaultdict(int)
    for e in events:
        if e["event_type"] == "CLICK":
            click_seconds[(e["athlete_id"], int(e.get("created_at") or 0))] += 1

    # Datacenter IPs that click links for 3+ different athletes -> scanner
    ip_click_athletes = defaultdict(set)
    for e in events:
        if e["event_type"] == "CLICK":
            ip_click_athletes[_first_ip(e.get("ip_address"))].add(e["athlete_id"])
    scanner_ips = {ip for ip, ath in ip_click_athletes.items() if len(ath) >= 3}

    for e in events:
        ip = _first_ip(e.get("ip_address"))
        ua = e.get("user_agent") or ""
        aid = e.get("athlete_id")
        etype = e.get("event_type")

        if (
            ip in TEST_IPS
            or e.get("campaign_id") in TEST_CAMPAIGNS
            or (valid_athlete_ids is not None and aid not in valid_athlete_ids)
        ):
            labels[e["id"]] = "test"
            continue

        if "python-requests" in ua or "curl/" in ua or "MSIE " in ua or "bot" in ua.lower():
            labels[e["id"]] = "bot"
            continue

        if etype == "CLICK":
            if (
                "X11; Linux x86_64" in ua
                or click_seconds[(aid, int(e.get("created_at") or 0))] > 1
                or ip in scanner_ips
            ):
                labels[e["id"]] = "bot"
            elif _is_mobile(ua):
                labels[e["id"]] = "human_click"
            else:
                labels[e["id"]] = "possible_click"
        else:  # OPEN
            if ua.strip() == "Mozilla/5.0":
                labels[e["id"]] = "auto_open"
            elif _is_mobile(ua):
                labels[e["id"]] = "human_open"
            elif "YahooMailProxy" in ua or "ggpht" in ua or ip.startswith(("66.249.", "74.125.", "66.102.")):
                labels[e["id"]] = "proxy_open"
            else:
                labels[e["id"]] = "human_open"

    # Opens that happened right before a scanner click (<=120s) were the scanner too
    by_athlete = defaultdict(list)
    for e in events:
        by_athlete[e["athlete_id"]].append(e)
    for aid, evs in by_athlete.items():
        bot_click_times = [e["created_at"] for e in evs if e["event_type"] == "CLICK" and labels.get(e["id"]) == "bot"]
        if not bot_click_times:
            continue
        for e in evs:
            if e["event_type"] == "OPEN" and labels.get(e["id"]) in ("human_open", "proxy_open"):
                if any(0 <= t - e["created_at"] <= 120 for t in bot_click_times):
                    labels[e["id"]] = "bot"
    return labels


def summarize_athletes(events, labels):
    """Returns {athlete_id: {tier, human_clicks, possible_clicks, real_opens, auto_opens, bot_events, last_real_at}}"""
    out = defaultdict(lambda: {
        "human_clicks": 0, "possible_clicks": 0, "real_opens": 0,
        "auto_opens": 0, "bot_events": 0, "last_real_at": None,
    })
    for e in events:
        lab = labels.get(e["id"])
        if lab is None or lab == "test":
            continue
        s = out[e["athlete_id"]]
        ts = e.get("created_at")
        if lab == "human_click":
            s["human_clicks"] += 1
        elif lab == "possible_click":
            s["possible_clicks"] += 1
        elif lab in ("human_open", "proxy_open"):
            s["real_opens"] += 1
        elif lab == "auto_open":
            s["auto_opens"] += 1
        else:
            s["bot_events"] += 1
        if lab in ("human_click", "possible_click", "human_open", "proxy_open") and ts:
            s["last_real_at"] = max(s["last_real_at"] or 0, ts)

    for s in out.values():
        if s["human_clicks"]:
            s["tier"] = "verified_click"
        elif s["possible_clicks"]:
            s["tier"] = "possible_click"
        elif s["real_opens"]:
            s["tier"] = "real_open"
        elif s["auto_opens"]:
            s["tier"] = "auto_open"
        else:
            s["tier"] = "bot_only"
    return dict(out)


def lead_quality_for_db(conn):
    """Convenience: classify everything in an open sqlite3 connection."""
    cur = conn.cursor()
    valid_ids = {r[0] for r in cur.execute("SELECT id FROM rec_debut_athletes")}
    cols = ["id", "athlete_id", "campaign_id", "event_type", "ip_address", "user_agent", "created_at"]
    events = [dict(zip(cols, r)) for r in cur.execute(
        "SELECT id, athlete_id, campaign_id, event_type, ip_address, user_agent, created_at FROM rec_debut_tracking_events"
    )]
    labels = classify_events(events, valid_ids)
    return summarize_athletes(events, labels), labels, events
