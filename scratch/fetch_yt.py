import urllib.request
import xml.etree.ElementTree as ET
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Fetch the video transcript from the caption URL
url = "https://www.youtube.com/api/timedtext?v=zc-dsSauYGM&ei=_TigarKAG-iw2_gPu5H6-AM&caps=asr&opi=112496729&exp=xpe&xoaf=5&xowf=1&xospf=1&hl=en&ip=0.0.0.0&ipbits=0&expire=1788910445&sparams=ip,ipbits,expire,v,ei,caps,opi,exp,xoaf&signature=C4CE5F1D391788879FB93F79193C71B97EC98290.77582A8204A47FC404713C4AFD0D2372DE175CE6&key=yt8&lang=en"

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    xml_data = urllib.request.urlopen(req).read().decode('utf-8', 'ignore')
    root = ET.fromstring(xml_data)
    text_pieces = []
    for text in root.findall('.//text'):
        start = text.get('start')
        dur = text.get('dur')
        content = text.text or ''
        # Clean HTML entities
        content = content.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
        text_pieces.append(f"[{start}s]: {content}")
    print("\n".join(text_pieces[:100]))
    print(f"\n... Total lines: {len(text_pieces)}")
    # Also dump all to a file for full reading
    with open(r"C:\AI-BS\scratch\yt_transcript.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(text_pieces))
    print("Full transcript saved to scratch/yt_transcript.txt")
except Exception as e:
    print("Error fetching captions:", e)
