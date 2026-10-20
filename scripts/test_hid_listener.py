import hid
import time
import sys

print("Opening HID Interface for RIG 800HS...")
device = hid.device()

# Find and open the vendor-defined or consumer HID interface
opened = False
for d in hid.enumerate():
    if d.get('vendor_id') == 0x047F and d.get('product_id') == 0xC044:
        try:
            device.open_path(d['path'])
            print(f"Successfully opened HID path: {d['path']}")
            print(f"  UsagePage: {hex(d.get('usage_page', 0))}, Usage: {hex(d.get('usage', 0))}")
            opened = True
            break
        except Exception as e:
            print(f"  Could not open path {d['path']}: {e}")

if opened:
    print("\nListening for raw USB packets/button presses for 5 seconds (non-blocking test)...")
    device.set_nonblocking(True)
    start = time.time()
    packet_count = 0
    while time.time() - start < 5.0:
        data = device.read(64)
        if data:
            packet_count += 1
            print(f"[{time.strftime('%H:%M:%S')}] Received Raw Packet ({len(data)} bytes): {[hex(b) for b in data]}")
        time.sleep(0.05)
    
    print(f"\nTest finished. Total packets intercepted: {packet_count}")
    device.close()
else:
    print("Failed to open any HID endpoints.")
