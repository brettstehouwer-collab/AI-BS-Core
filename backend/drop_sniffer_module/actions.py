"""
AI-BS Drop Sniffer Module - Actions & Notification Subsystem
Handles headless auto-carting, dual-path browser launches, audio sirens, and Windows desktop toasts.
"""

import time
import os
import json
import webbrowser
import subprocess
import threading
from datetime import datetime

LOG_FILE = r"C:\AI-BS\saved_data\cymatics_drop_log.json"
EMERGENCY_QUEUE_FILE = r"C:\AI-BS\saved_data\unclaimed_emergency_queue.txt"
CART_ADD_URL = "https://cymatics.fm/cart/add.js"

class ActionDispatcher:
    def __init__(self, session):
        self.session = session
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    def auto_add_to_cart(self, variant_id, max_retries=3):
        """Instant headless POST to Shopify cart/add.js with exponential backoff."""
        for attempt in range(max_retries):
            try:
                r = self.session.post(
                    CART_ADD_URL,
                    data={'id': variant_id, 'quantity': 1},
                    headers={'X-Requested-With': 'XMLHttpRequest'},
                    timeout=3.0
                )
                if r.status_code == 200:
                    res = r.json()
                    print(f"\n[⚡ AUTO-CART SUCCESS]: Added Variant ID {variant_id} ({res.get('title', 'Item')})", flush=True)
                    return res
                else:
                    time.sleep(0.2 * (attempt + 1))
            except Exception:
                time.sleep(0.2 * (attempt + 1))
        return None

    def play_siren(self):
        """Redundant audio alert: dual frequency pulses + Windows system chime."""
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            for _ in range(8):
                winsound.Beep(1800, 100)
                time.sleep(0.02)
                winsound.Beep(2600, 150)
                time.sleep(0.02)
        except Exception:
            pass

    def send_windows_toast(self, title, url):
        """Fires a non-blocking Windows Desktop Notification."""
        try:
            safe_t = title.replace("'", "").replace('"', "")
            safe_u = url.replace("'", "").replace('"', "")
            ps_cmd = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);
            $textNodes = $template.GetElementsByTagName('text');
            $textNodes.Item(0).AppendChild($template.CreateTextNode('⚡ NEW CYMATICS DROP UNLOCKED!')) > $null;
            $textNodes.Item(1).AppendChild($template.CreateTextNode('{safe_t} - Click or check browser!')) > $null;
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template);
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('AI-BS Sniper').Show($toast);
            """
            subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def launch_checkout(self, url):
        """Launches checkout URL in browser with OS-native fallback without shell string interpolation."""
        try:
            webbrowser.open(url)
        except Exception:
            try:
                if os.name == "nt":
                    os.startfile(url)  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def log_drop(self, title, variant_id, checkout_url, price='0.00'):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry = {
            "timestamp": ts,
            "title": title,
            "variant_id": variant_id,
            "url": checkout_url,
            "price": price
        }
        
        # Update JSON log
        try:
            history = []
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            history.append(entry)
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass

        # Update emergency text queue
        try:
            with open(EMERGENCY_QUEUE_FILE, 'a', encoding='utf-8') as f:
                f.write(f"[{ts}] {title} (${price}) | ID: {variant_id} | {checkout_url}\n")
        except Exception:
            pass

    def execute_claim_sequence(self, title, variant_id=None, direct_url=None, price='0.00'):
        """Executes full multi-modal claim sequence."""
        if price and str(price) not in ['0.00', '0', '0.0']:
            return

        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n=======================================================", flush=True)
        print(f"  🚨🚨 NEW $0.00 FREE DROP DETECTED: {title}! [{ts}] 🚨🚨", flush=True)
        print(f"=======================================================", flush=True)

        checkout_url = f"https://cymatics.fm/cart/{variant_id}:1?checkout" if variant_id else (
            direct_url if direct_url and direct_url.startswith('http') else f"https://cymatics.fm{direct_url}"
        )

        if variant_id:
            threading.Thread(target=self.auto_add_to_cart, args=(variant_id,), daemon=True).start()

        if checkout_url:
            self.launch_checkout(checkout_url)

        self.log_drop(title, variant_id, checkout_url, price=price)
        threading.Thread(target=self.play_siren, daemon=True).start()
        threading.Thread(target=self.send_windows_toast, args=(title, checkout_url or "https://cymatics.fm"), daemon=True).start()
