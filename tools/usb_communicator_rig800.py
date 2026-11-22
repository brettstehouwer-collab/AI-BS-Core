"""
AI-BS Custom Raw USB Communicator & Multi-Channel HID Event Trigger
Target: Plantronics / Nacon RIG 800HS Wireless Dongle (VID: 0x047F, PID: 0xC044)
Features:
  - Simultaneous dual-channel listening (Consumer Controls 0x000C + Vendor Telemetry 0xFF00)
  - Raw Hex Packet Decoding & Event Callback Hooks
  - Continuous Interactive Monitor Mode
"""

import sys
import time
import threading
import hid
import libusb_package
import usb.core
import usb.util

VENDOR_ID = 0x047F
PRODUCT_ID = 0xC044

class DualChannelUSBCommunicator:
    def __init__(self, vendor_id=VENDOR_ID, product_id=PRODUCT_ID):
        self.vid = vendor_id
        self.pid = product_id
        self.handles = []
        self.running = False

    def list_endpoints(self):
        print("==================================================")
        print("   AI-BS RAW USB TOPOLOGY & ENDPOINT MAPPER       ")
        print("==================================================")
        dev = libusb_package.find(idVendor=self.vid, idProduct=self.pid)
        if not dev:
            print("[-] Device not found in LibUSB bus.")
            return
        
        print(f"[+] Device: {dev.product} by {dev.manufacturer} (Bus {dev.bus}, Addr {dev.address})")
        for cfg in dev:
            for intf in cfg:
                intf_name = {0: "Audio Control", 1: "Audio Stream IN", 2: "Audio Stream OUT", 3: "HID Telemetry"}.get(intf.bInterfaceNumber, "Unknown")
                print(f"    Interface {intf.bInterfaceNumber} (Alt {intf.bAlternateSetting}) - {intf_name}:")
                for ep in intf:
                    ep_dir = "IN" if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN else "OUT"
                    ep_type = ["Control", "Isochronous", "Bulk", "Interrupt"][ep.bmAttributes & 3]
                    print(f"      -> Endpoint {hex(ep.bEndpointAddress)} ({ep_dir}): Type={ep_type}, MaxPacketSize={ep.wMaxPacketSize} bytes")

    def open_all_hid_channels(self):
        print("\n[+] Attaching to all exposed HID channels...")
        found = False
        for item in hid.enumerate():
            if item.get('vendor_id') == self.vid and item.get('product_id') == self.pid:
                up = item.get('usage_page', 0)
                usage = item.get('usage', 0)
                path = item['path']
                try:
                    h = hid.device()
                    h.open_path(path)
                    h.set_nonblocking(True)
                    self.handles.append({
                        'handle': h,
                        'usage_page': up,
                        'usage': usage,
                        'name': f"UsagePage: {hex(up)} (Usage {hex(usage)})"
                    })
                    print(f"    [CONNECTED] {hex(up)}:{hex(usage)} on {path.decode() if isinstance(path, bytes) else path}")
                    found = True
                except Exception as e:
                    print(f"    [FAILED] {hex(up)}:{hex(usage)} - {e}")
        return found

    def start_dual_monitor(self, on_event_callback=None):
        if not self.handles:
            print("[-] No HID handles available.")
            return

        print("\n[+] Starting Real-Time Multi-Channel Packet Interceptor...")
        print("[*] Press the physical button on the USB dongle to test signal capture.")
        print("[*] Press Ctrl+C at any time to exit.\n")
        self.running = True

        def channel_worker(channel_info):
            h = channel_info['handle']
            name = channel_info['name']
            while self.running:
                try:
                    data = h.read(64)
                    if data:
                        timestamp = time.strftime("%H:%M:%S")
                        hex_data = " ".join(f"{b:02X}" for b in data)
                        print(f"[{timestamp}] [{name}] RAW RX ({len(data)} bytes): {hex_data}")
                        if on_event_callback:
                            on_event_callback(name, data)
                except Exception as e:
                    break
                time.sleep(0.01)

        threads = []
        for ch in self.handles:
            t = threading.Thread(target=channel_worker, args=(ch,), daemon=True)
            t.start()
            threads.append(t)

        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[*] Interceptor stopped by user.")
        finally:
            self.running = False
            for ch in self.handles:
                ch['handle'].close()
            print("[+] All HID channels closed cleanly.")

def custom_event_action(channel_name, raw_bytes):
    # Example Custom Macro Trigger:
    print(f"  >>> [TRIGGER] Intercepted {len(raw_bytes)} bytes from {channel_name}!")

if __name__ == "__main__":
    comm = DualChannelUSBCommunicator()
    comm.list_endpoints()
    if comm.open_all_hid_channels():
        comm.start_dual_monitor(on_event_callback=custom_event_action)
