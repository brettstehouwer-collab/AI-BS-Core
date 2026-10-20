import libusb_package
import usb.core
import usb.util
import hid
import sys

print("========================================")
print("  RIG 800HS RAW USB & HID COMMUNICATOR  ")
print("========================================")

# 1. Enumerate HID endpoints
print("\n[1] Querying Native HID Interfaces...")
hid_targets = []
for d in hid.enumerate():
    if d.get("vendor_id") == 0x047F:
        hid_targets.append(d)
        print(f"  - Interface {d.get('interface_number')}: Path={d.get('path')} Product={d.get('product_string')} UsagePage={hex(d.get('usage_page', 0))} Usage={hex(d.get('usage', 0))}")

if not hid_targets:
    print("  No HID endpoints found under VID 0x047F.")

# 2. Enumerate PyUSB / LibUSB endpoints
print("\n[2] Querying LibUSB Device Descriptor...")
try:
    dev = libusb_package.find(idVendor=0x047F, idProduct=0xC044)
    if dev is not None:
        print(f"  Device Found: VID=0x047F PID=0xC044 (Bus {dev.bus} Address {dev.address})")
        print(f"  Manufacturer: {usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else 'Plantronics'}")
        print(f"  Product: {usb.util.get_string(dev, dev.iProduct) if dev.iProduct else 'RIG 800HS'}")
        print(f"  Active Configurations: {dev.bNumConfigurations}")
        
        for cfg in dev:
            print(f"    - Config {cfg.bConfigurationValue}: MaxPower={cfg.bMaxPower * 2}mA")
            for intf in cfg:
                print(f"      * Interface {intf.bInterfaceNumber}, Alt {intf.bAlternateSetting}, Class={intf.bInterfaceClass}, SubClass={intf.bInterfaceSubClass}")
                for ep in intf:
                    print(f"        -> Endpoint {hex(ep.bEndpointAddress)}: Type={ep.bmAttributes & 3} (0=Ctrl, 1=Iso, 2=Bulk, 3=Int), MaxPacket={ep.wMaxPacketSize}")
    else:
        print("  LibUSB could not find VID 0x047F PID 0xC044 directly (may require WinUSB driver binding via Zadig if default Windows audio driver locks it).")
except Exception as e:
    print(f"  LibUSB query exception: {e}")
