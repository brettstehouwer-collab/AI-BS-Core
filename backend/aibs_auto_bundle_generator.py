"""
AI-BS Cymatics 1-Click Mega-Bundle Claim Dashboard Generator
Builds a local interactive HTML portal with direct 1-click checkout URLs for all drops.
"""

import json
import os
import requests

OUTPUT_HTML = r"C:\AI-BS\saved_data\CLAIM_DASHBOARD.html"

def generate_dashboard():
    # Load discovered drops
    drops = []
    if os.path.exists(r"C:\AI-BS\saved_data\cymatics_discovered_free_drops.json"):
        with open(r"C:\AI-BS\saved_data\cymatics_discovered_free_drops.json", "r", encoding="utf-8") as f:
            drops = json.load(f)

    # Collect variant IDs for mega-cart
    free_variants = [str(d['variant_id']) for d in drops if d.get('variant_id')]
    mega_cart_url = f"https://cymatics.fm/cart/{':1,'.join(free_variants)}:1?checkout" if free_variants else "https://cymatics.fm/cart"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI-BS Cymatics 1-Click Claim Dashboard</title>
    <style>
        body {{
            background-color: #0b0f19;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 30px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        h1 {{
            color: #00f0ff;
            font-size: 28px;
            margin-bottom: 8px;
            letter-spacing: 1px;
        }}
        .mega-btn {{
            display: block;
            max-width: 600px;
            margin: 0 auto 35px auto;
            background: linear-gradient(135deg, #10b981, #059669);
            color: #ffffff;
            font-size: 20px;
            font-weight: 900;
            text-decoration: none;
            padding: 18px 24px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 0 30px rgba(16, 185, 129, 0.4);
            border: 2px solid #34d399;
            transition: transform 0.1s ease;
        }}
        .mega-btn:hover {{
            transform: scale(1.02);
            box-shadow: 0 0 45px rgba(16, 185, 129, 0.7);
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .card:hover {{
            border-color: #00f0ff;
        }}
        .title {{
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 8px;
            color: #f1f5f9;
        }}
        .price {{
            font-size: 12px;
            color: #10b981;
            font-weight: bold;
            margin-bottom: 12px;
        }}
        .claim-btn {{
            display: inline-block;
            background: #00f0ff;
            color: #000000;
            font-weight: bold;
            font-size: 12px;
            text-decoration: none;
            padding: 8px 12px;
            border-radius: 6px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI-BS CYMATICS 1-CLICK CLAIM PORTAL</h1>
        <p style="color: #94a3b8;">Fail-Safe Instant Direct-to-Checkout Dashboard</p>
    </div>

    <a href="{mega_cart_url}" target="_blank" class="mega-btn">
        🔥 CLAIM ALL {len(free_variants)} FREE ASSETS (1-CLICK MEGA BUNDLE)
    </a>

    <div class="grid">
"""
    for d in drops:
        html_content += f"""
        <div class="card">
            <div>
                <div class="title">{d['title']}</div>
                <div class="price">Price: ${d.get('price', '0.00')} (FREE)</div>
            </div>
            <a href="{d['direct_checkout']}" target="_blank" class="claim-btn">
                1-CLICK CLAIM
            </a>
        </div>
"""

    html_content += """
    </div>
</body>
</html>
"""
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated {OUTPUT_HTML} with {len(drops)} items.")

if __name__ == "__main__":
    generate_dashboard()
