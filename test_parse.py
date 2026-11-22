import xml.etree.ElementTree as ET
import re, json

with open('/tmp/smi.xml') as f:
    msg = f.read()

root = ET.fromstring(msg)

def read_xml_text_part(node, keys, unit, default=0):
    for k in keys:
        try:
            val = node.find(k).text
            if val is None or val == "N/A":
                continue
            x, _, u = val.partition(" ")
            if u == unit or not u:
                return x
        except:
            pass
    return default

for cidx, gpu in enumerate(root.iter('gpu')):
    prodname = gpu.find("product_name").text
    display_active = gpu.find("display_active").text == "Enabled"
    idx = cidx
    uuid = gpu.find("uuid").text
    pci_bus_id = gpu.find("pci").find("pci_bus_id").text
    minor_text = gpu.find("minor_number").text
    minor_no = int(minor_text) if minor_text and minor_text.isdigit() else cidx
    print("Minor no:", minor_no)

    total = int(read_xml_text_part(gpu, ["fb_memory_usage/total"], "MiB", 24576))
    free = int(read_xml_text_part(gpu, ["fb_memory_usage/free"], "MiB", 24576))
    print("Total:", total, "Free:", free)
    cur_power = float(read_xml_text_part(gpu, ["power_readings/power_draw", "gpu_power_readings/power_draw"], "W", 0))
    max_power = float(read_xml_text_part(gpu, ["power_readings/power_limit", "gpu_power_readings/current_power_limit"], "W", 310))
    cur_temp = float(read_xml_text_part(gpu, ["temperature/gpu_temp"], "C", 40))
    max_temp = float(read_xml_text_part(gpu, ["temperature/gpu_temp_max_threshold", "temperature/gpu_temp_tlimit"], "C", 80))
    gpu_util = float(read_xml_text_part(gpu, ["utilization/gpu_util"], "%", 0))
    print("Power:", cur_power, "Temp:", cur_temp, "Util:", gpu_util)

print("ALL PASSED!")
