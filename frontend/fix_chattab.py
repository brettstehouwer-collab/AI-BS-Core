import os

path = "C:/AI-BS/frontend/components/ChatTab.jsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update text
content = content.replace("⚡ 12 Quick Action Presets", "⚡ 18 Quick Action Presets")
content = content.replace("⚡ 12 Quick Starters", "⚡ 18 Quick Starters")

# 2. Add the 6 new cards to starterCards
new_cards = """    {
      category: "🏠 Automation",
      title: "🏠 Activate Command Center Protocol",
      desc: "Dim studio lights, initialize security dashboard, and boot primary workstation monitors.",
      prompt: "Run the command center boot sequence: activate smart lighting, wake local dashboard, and initialize proxy network."
    },
    {
      category: "🏠 Automation",
      title: "🕸️ Test Go-Matrix Proxy Multiplex",
      desc: "Stress-test Port 8000 reverse-proxy socket multiplexing to prevent starvation.",
      prompt: "Ping the Go API Gateway at Port 8000 to verify reverse-proxy socket multiplexing and memory mapping integrity."
    },
    {
      category: "💻 Developer",
      title: "🚀 Trigger Vercel Edge Deploy",
      desc: "Run Vite build pipeline, execute ESLint, and deploy to Vercel/Firebase edge network.",
      prompt: "Initialize the production build pipeline, verify React boundary state, and deploy the latest artifact to Firebase Hosting."
    },
    {
      category: "💻 Developer",
      title: "🕷️ Deep Cyber-Scrape Analysis",
      desc: "Launch headless Chromium to scrape top cybersecurity architectures and parse with Lexicon.",
      prompt: "Use your web scraping tools to pull the latest front-end architecture trends and cross-reference them with our Lexicon Vault."
    },
    {
      category: "🎙️ Studio",
      title: "🎙️ Generate TTS Podcast Host Track",
      desc: "Synthesize a 30-second intro using Kokoro TTS and load into the local buffer.",
      prompt: "Generate a dynamic AI podcast host introduction script and synthesize it into the local audio buffer."
    },
    {
      category: "📈 Finance",
      title: "📈 Quantitative Market Ledger",
      desc: "Query financial intelligence DB and compute standard deviation on the latest asset vectors.",
      prompt: "Query the financial intelligence database for historical asset vectors and run a quantitative market analysis."
    }
  ];"""
content = content.replace("  ];", new_cards, 1)

# 3. Update the ReactMarkdown blockquote renderer
old_bq = """          blockquote({ children }) {
            return (
              <blockquote style={{
                borderLeft: '4px solid #60a5fa',
                background: 'rgba(59, 130, 246, 0.08)',
                margin: '12px 0',
                padding: '8px 16px',
                borderRadius: '0 8px 8px 0',
                color: '#cbd5e1',
                fontSize: '0.88rem'
              }}>
                {children}
              </blockquote>
            );
          },"""

new_bq = """          blockquote({ node, children }) {
            const isThoughtTrace = node?.children?.[0]?.children?.[0]?.value?.includes('THOUGHT:') || 
                                   node?.children?.[0]?.children?.[0]?.value?.includes('💭') ||
                                   node?.children?.[0]?.children?.[0]?.value?.includes('SWARM PASS');
            return (
              <blockquote style={{
                borderLeft: isThoughtTrace ? '4px solid #c084fc' : '4px solid #60a5fa',
                background: isThoughtTrace ? 'rgba(192, 132, 252, 0.08)' : 'rgba(59, 130, 246, 0.08)',
                margin: '12px 0',
                padding: '10px 16px',
                borderRadius: '0 8px 8px 0',
                color: isThoughtTrace ? '#e879f9' : '#cbd5e1',
                fontSize: isThoughtTrace ? '0.82rem' : '0.88rem',
                fontFamily: isThoughtTrace ? "'JetBrains Mono', 'Fira Code', monospace" : "inherit",
                boxShadow: isThoughtTrace ? 'inset 0 0 10px rgba(192, 132, 252, 0.05)' : 'none'
              }}>
                {children}
              </blockquote>
            );
          },"""

if old_bq in content:
    content = content.replace(old_bq, new_bq)
else:
    print("Could not find blockquote renderer to replace.")

with open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("Updated components/ChatTab.jsx")
import shutil
shutil.copy2(path, "C:/AI-BS/frontend/src/components/ChatTab.jsx")
print("Synced to src/components/ChatTab.jsx")
