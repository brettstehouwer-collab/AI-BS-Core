import sys
import os
import time
import argparse
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game_trainer.profiles.btd6_profile import BTD6Trainer
from game_trainer.core.overlay import TrainerOverlay


def main():
    parser = argparse.ArgumentParser(description="AI-BS Standalone Bloons TD 6 Trainer")
    parser.add_argument("--pid", type=int, help="Optional PID of BloonsTD6.exe")
    parser.add_argument("--cash-addr", type=lambda x: int(x, 0), help="Direct hex address of match cash")
    parser.add_argument("--lives-addr", type=lambda x: int(x, 0), help="Direct hex address of match lives")
    parser.add_argument("--no-overlay", action="store_true", help="Disable on-screen transparent HUD overlay")
    parser.add_argument("--daemon", action="store_true", help="Run as headless JSON IPC daemon for Electron UI")
    args = parser.parse_args()

    if args.daemon:
        # Run the JSON IPC Daemon
        from game_trainer.daemon import TrainerDaemon
        daemon = TrainerDaemon(target_pid=args.pid)
        try:
            daemon.start()
        except KeyboardInterrupt:
            daemon.stop()
        return

    print("\n" + "=" * 68)
    print("      AI-BS STANDALONE TRAINER: BLOONS TD 6 (OFFLINE / SINGLE-PLAYER)")
    print("=" * 68)
    print(" [*] Target Executable : BloonsTD6.exe")
    print(" [*] Architecture      : Unity IL2CPP (x86_64, GameAssembly.dll)")
    print(" [*] Operational Scope : Offline Single-Player Maps / Local Sandbox")
    print(" [*] Interactive HUD   : " + ("Disabled" if args.no_overlay else "Enabled (Fully Clickable UI + Tabs)"))
    print("=" * 68)

    trainer = BTD6Trainer(target_pid=args.pid)
    overlay = None

    if not args.no_overlay:
        try:
            overlay = TrainerOverlay(trainer, title="BTD6 TRAINER HUD")
            trainer.set_overlay(overlay)
        except Exception as e:
            print(f"[!] Warning: Could not initialize HUD overlay: {e}")
            overlay = None

    def trainer_logic_thread():
        if not trainer.setup():
            print("\n[!] BloonsTD6.exe is not currently running.")
            print("[*] CONTINUOUS AUTO-DETECTION ACTIVE: Launch Bloons TD 6 from Steam or your Desktop...")
            
            dots = 0
            while not trainer.setup():
                dots = (dots + 1) % 4
                try:
                    sys.stdout.write(f"\r[*] Waiting for BloonsTD6.exe{'.' * dots}{' ' * (3 - dots)}")
                    sys.stdout.flush()
                except Exception:
                    pass
                time.sleep(1.0)
            print("\n")

        print(f"\n[+] Successfully attached to BloonsTD6.exe (PID {trainer.mem.pid})!")
        print(f"[+] GameAssembly.dll Base Address: {hex(trainer.game_assembly_base)}")

        if args.cash_addr:
            trainer.set_cash_address(args.cash_addr)
        if args.lives_addr:
            trainer.set_lives_address(args.lives_addr)

        if not trainer.cash_addresses:
            print("[*] Probing game memory for active match cash...")
            trainer.auto_scan_cash()
        if not trainer.lives_addresses:
            trainer.auto_scan_lives()

        trainer.start()
        trainer.print_dashboard()

        try:
            while trainer.running:
                try:
                    cmd = input("Trainer> ").strip().lower()
                except (EOFError, RuntimeError):
                    # No console available, just sleep and let UI handle things
                    time.sleep(1.0)
                    continue
                    
                if cmd in ("q", "exit"):
                    break
                elif cmd == "scan" or cmd.startswith("scan "):
                    parts = cmd.split()
                    target_val = float(parts[1]) if len(parts) > 1 else None
                    trainer.first_scan_cash(target_val) if target_val is not None else trainer.auto_scan_cash()
                elif cmd.startswith("next ") or cmd == "next":
                    parts = cmd.split()
                    if len(parts) > 1:
                        try:
                            trainer.next_scan_cash(float(parts[1]))
                        except ValueError:
                            print("[!] Usage: next <new_cash_value>")
                    else:
                        print("[!] Usage: next <new_cash_value> (e.g. 'next 435')")
                elif cmd == "coins" or cmd.startswith("coins "):
                    parts = cmd.split()
                    if len(parts) > 1:
                        try:
                            trainer.first_scan_coins(int(parts[1]))
                        except ValueError:
                            pass
                elif cmd.startswith("nextcoins "):
                    parts = cmd.split()
                    if len(parts) > 1:
                        try:
                            trainer.next_scan_coins(int(parts[1]))
                        except ValueError:
                            pass
                elif cmd in ("hud", "overlay"):
                    if overlay:
                        overlay.toggle_visibility()
                elif cmd == "status":
                    trainer.print_dashboard()
                elif cmd in ("help", "?"):
                    print("\nCommands:")
                    print("  scan <cash>       : First scan for current match cash (e.g. 'scan 650')")
                    print("  next <cash>       : Filter candidates after cash changes in-game (e.g. 'next 435')")
                    print("  coins <coins>     : Scan for Monkey Money (e.g. 'coins 5240')")
                    print("  nextcoins <coins> : Filter Monkey Money candidates")
                    print("  hud / overlay     : Toggle on-screen HUD visibility")
                    print("  status            : Print status dashboard")
                    print("  exit / q          : Quit trainer\n")

                if not trainer.mem.is_alive():
                    print("\n[!] BloonsTD6.exe has terminated. Detaching trainer.")
                    break
        except KeyboardInterrupt:
            pass
        finally:
            trainer.stop()
            if overlay:
                overlay.stop()

    # Start the trainer logic in a background daemon thread
    t_thread = threading.Thread(target=trainer_logic_thread, daemon=True)
    t_thread.start()

    # Run the UI on the main thread to satisfy Windows message pump (prevents 'Not Responding')
    if overlay:
        overlay._running = True
        overlay._run_ui()
    else:
        # If no UI, just block on the background thread
        while t_thread.is_alive():
            time.sleep(0.5)

    print("\n[Trainer] Clean shutdown complete.")


if __name__ == "__main__":
    main()
