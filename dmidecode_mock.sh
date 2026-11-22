#!/bin/bash
if [ "$1" = "-s" ]; then
    echo "ProArt X670E-CREATOR WIFI"
    exit 0
fi

cat << 'EOF'
# dmidecode 3.5
Getting SMBIOS data from sysfs.
SMBIOS 3.5.0 present.

Handle 0x0000, DMI type 0, 26 bytes
BIOS Information
	Vendor: American Megatrends Inc.
	Version: 1.00
	Release Date: 08/01/2026

Handle 0x0001, DMI type 1, 27 bytes
System Information
	Manufacturer: ASUSTeK COMPUTER INC.
	Product Name: ProArt X670E-CREATOR WIFI
	Version: 1.00

Handle 0x0002, DMI type 2, 15 bytes
Base Board Information
	Manufacturer: ASUSTeK COMPUTER INC.
	Product Name: ProArt X670E-CREATOR WIFI
	Version: Rev 1.xx

Handle 0x0004, DMI type 4, 48 bytes
Processor Information
	Socket Designation: AM5
	Type: Central Processor
	Family: Zen
	Manufacturer: Advanced Micro Devices
	Version: AMD Ryzen 9 9950X 16-Core Processor
	Max Speed: 5700 MHz
	Current Speed: 4300 MHz
	Status: Populated, Enabled
	Core Count: 16
	Core Enabled: 16
	Thread Count: 32

Handle 0x0011, DMI type 17, 92 bytes
Memory Device
	Array Handle: 0x0010
	Error Information Handle: Not Provided
	Total Width: 64 bits
	Data Width: 64 bits
	Size: 32 GB
	Form Factor: DIMM
	Set: None
	Locator: DIMM 0
	Bank Locator: P0 CHANNEL A
	Type: DDR5
	Type Detail: Synchronous Unbuffered (Unregistered)
	Speed: 6000 MT/s
	Manufacturer: Corsair
	Part Number: CMK64GX5M2B6000C30

Handle 0x0012, DMI type 17, 92 bytes
Memory Device
	Array Handle: 0x0010
	Error Information Handle: Not Provided
	Total Width: 64 bits
	Data Width: 64 bits
	Size: 32 GB
	Form Factor: DIMM
	Set: None
	Locator: DIMM 1
	Bank Locator: P0 CHANNEL B
	Type: DDR5
	Type Detail: Synchronous Unbuffered (Unregistered)
	Speed: 6000 MT/s
	Manufacturer: Corsair
	Part Number: CMK64GX5M2B6000C30
EOF
exit 0
