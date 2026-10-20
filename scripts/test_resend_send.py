import requests

api_key = "re_cwXi97Fw_PMQUNSCbpkTcBpU7ecLvybxW"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "from": "Dennis Bell <onboarding@resend.dev>",
    "to": ["brettstehouwer@gmail.com"],
    "reply_to": "dbell002@sbcglobal.net",
    "subject": "AI-BS Resend API Key Test: Connected & Verified!",
    "html": "<h3>🎉 Resend API Key Connected Successfully!</h3><p>Your Resend API key <code>re_cwXi...bxW</code> is active and sending from AI-BS.</p><p><b>Next Step to send to all 5,177 athletes:</b><br>In your Resend dashboard (<a href='https://resend.com/domains'>resend.com/domains</a>), add your domain (e.g. <code>recdebut.com</code>) and copy the 3 DNS records (TXT/DKIM/MX) into your domain DNS host (GoDaddy/Cloudflare/Namecheap) so you can broadcast freely to external recipients.</p>",
    "text": "Resend API Key Connected Successfully! Your Resend API key is active in AI-BS."
}

r = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10)
print("Status:", r.status_code)
print("Response:", r.text)
