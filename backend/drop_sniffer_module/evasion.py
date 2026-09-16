"""
AI-BS Drop Sniffer Module - Evasion & Anti-Ban Subsystem
Provides dynamic residential IP spoofing, realistic User-Agent cycling, and headers generator.
"""

import random

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6; rv:130.0) Gecko/20100101 Firefox/130.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15'
]

RESIDENTIAL_SUBNETS = [
    (24, 0, 0, 0),      # Comcast Cable US
    (73, 0, 0, 0),      # Comcast Cable US
    (98, 160, 0, 0),    # Spectrum / Charter US
    (172, 56, 0, 0),    # T-Mobile US
    (174, 192, 0, 0),   # Verizon Wireless US
    (68, 0, 0, 0),      # AT&T Internet US
    (76, 16, 0, 0)      # Cox Communications US
]

class EvasionEngine:
    @staticmethod
    def generate_spoofed_ip():
        subnet = random.choice(RESIDENTIAL_SUBNETS)
        return f"{subnet[0]}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"

    @staticmethod
    def get_spoofed_headers():
        ip = EvasionEngine.generate_spoofed_ip()
        ua = random.choice(USER_AGENTS)
        return {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Connection': 'keep-alive',
            'X-Forwarded-For': ip,
            'X-Real-IP': ip,
            'CF-Connecting-IP': ip,
            'True-Client-IP': ip,
            'X-Client-IP': ip,
            'Forwarded': f'for={ip};proto=https',
            'Sec-Ch-Ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
