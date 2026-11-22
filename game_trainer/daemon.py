import sys
import json
import time
import threading
from typing import Dict, Any, Optional
from game_trainer.profiles.btd6_profile import BTD6Trainer

class TrainerDaemon:
    """
    Headless JSON IPC daemon that bridges the BTD6Trainer with an external process (like Electron).
    Reads JSON commands from stdin and broadcasts JSON status updates to stdout.
    """
    def __init__(self, target_pid: Optional[int] = None):
        self.trainer = BTD6Trainer(target_pid=target_pid)
        self.running = False
        self._input_thread = None

    def start(self):
        self.running = True
        
        # Start input polling thread
        self._input_thread = threading.Thread(target=self._read_stdin_loop, daemon=True)
        self._input_thread.start()
        
        # Start setup/attachment loop in background
        threading.Thread(target=self._setup_loop, daemon=True).start()
        
        # Main thread runs the broadcast loop
        self._broadcast_loop()

    def stop(self):
        self.running = False
        self.trainer.stop()

    def _setup_loop(self):
        while self.running:
            if not self.trainer.setup():
                time.sleep(1.0)
            else:
                self.trainer.start()
                
                # Wait until game closes
                while self.running and self.trainer.mem.is_alive():
                    time.sleep(1.0)
                
                if self.running:
                    self.trainer.stop()

    def _read_stdin_loop(self):
        """Continuously read commands from standard input."""
        while self.running:
            try:
                line = sys.stdin.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                
                command = json.loads(line.strip())
                self._handle_command(command)
            except EOFError:
                break
            except json.JSONDecodeError:
                pass # Ignore malformed json
            except Exception as e:
                self._send_event({"type": "error", "message": str(e)})

    def _handle_command(self, cmd: Dict[str, Any]):
        action = cmd.get("action")
        if action == "auto_scan_cash":
            target = cmd.get("target_val")
            self.trainer.auto_scan_cash(target)
        elif action == "auto_scan_lives":
            target = cmd.get("target_val")
            self.trainer.auto_scan_lives(target)
        elif action == "add_cash":
            amount = cmd.get("amount", 50000.0)
            if self.trainer.cash_addresses:
                for addr in self.trainer.cash_addresses:
                    cur = self.trainer.mem.read_double(addr)
                    self.trainer.mem.write_double(addr, cur + amount)
        elif action == "set_coins":
            current = cmd.get("current")
            target = cmd.get("target", 99999)
            if current is not None:
                self.trainer.frozen_coins_val = target
                self.trainer.auto_scan_coins(current)
        elif action == "toggle_feature":
            feat_name = cmd.get("feature")
            for feat in self.trainer.get_unique_features():
                if feat.name == feat_name:
                    feat.toggle()
                    break
        elif action == "set_variable":
            var_key = cmd.get("variable")
            value = cmd.get("value")
            for var in self.trainer.get_variables():
                if var.key == var_key:
                    try:
                        var.set_val(float(value))
                    except ValueError:
                        pass
                    break
        elif action == "quit":
            self.stop()

    def _broadcast_loop(self):
        """Continuously broadcast state to stdout."""
        while self.running:
            try:
                state = self._get_state()
                self._send_event(state)
            except Exception:
                pass
            time.sleep(0.5)

    def _get_state(self) -> Dict[str, Any]:
        attached = self.trainer.mem.is_alive()
        state = {
            "type": "state_update",
            "status": "ATTACHED" if attached else "SEARCHING",
            "features": {},
            "variables": {}
        }
        
        for feat in self.trainer.get_unique_features():
            state["features"][feat.name] = feat.enabled if feat.is_toggle else "READY"
            
        for var in self.trainer.get_variables():
            state["variables"][var.key] = var.get_val()
            
        return state

    def _send_event(self, event: Dict[str, Any]):
        try:
            msg = json.dumps(event)
            sys.stdout.write(msg + "\n")
            sys.stdout.flush()
        except Exception:
            pass

if __name__ == "__main__":
    daemon = TrainerDaemon()
    try:
        daemon.start()
    except KeyboardInterrupt:
        daemon.stop()
