import time
import random
import sys
import json
import asyncio

def print_typewriter(text, delay=0.03):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

leads_data = [
    {"industry": "TRADES (Roofing/Plumbing)", "lead": "John Doe (Homeowner) - 'Need emergency roof patch' - Grand Rapids, MI", "action": "Drafting instant SMS quote based on $150/hr base rate."},
    {"industry": "TRADES (Roofing/Plumbing)", "lead": "New commercial building permit filed at 123 Main St.", "action": "Emailing General Contractor offering sub-contract plumbing services."},
    {"industry": "RETAIL", "lead": "Competitor 'Boutique X' just dropped prices on winter coats by 20%.", "action": "Generating dynamic Facebook Ad to match price for local radius."},
    {"industry": "RETAIL", "lead": "Negative review detected on competitor's Google Maps profile regarding slow service.", "action": "Flagging lead for direct outreach offering faster fulfillment."},
    {"industry": "B2B SERVICES", "lead": "Company Y recently hired 50 new employees (Growth Signal).", "action": "Drafting personalized LinkedIn pitch to HR Director for corporate catering/services."},
]

industries = [
    {"name": "TRADES (Roofing/Plumbing)", "targets": ["Nextdoor Scrape", "Local Permit Database", "Yelp New Listings"]},
    {"name": "RETAIL", "targets": ["Competitor Pricing APIs", "Google Maps Sentiment Analysis", "Local Chamber of Commerce"]},
    {"name": "B2B SERVICES", "targets": ["LinkedIn Sales Navigator", "Corporate Event Registries", "Public Tax Filings"]}
]

async def generate_leads_stream():
    """Async generator yielding Server-Sent Events (SSE) for the frontend dashboard"""
    yield f"data: {json.dumps({'type': 'status', 'message': 'Initializing distributed web scrapers...'})}\n\n"
    await asyncio.sleep(1)
    yield f"data: {json.dumps({'type': 'status', 'message': 'Bypassing CAPTCHAs and loading heuristics engine...'})}\n\n"
    await asyncio.sleep(1)
    
    for ind in industries:
        yield f"data: {json.dumps({'type': 'status', 'message': f'[TARGET LOCKED] Initializing {ind['name']} pipelines...'})}\n\n"
        for target in ind['targets']:
            yield f"data: {json.dumps({'type': 'status', 'message': f' [+] Scanning {target}...'})}\n\n"
            await asyncio.sleep(0.4)
            
    yield f"data: {json.dumps({'type': 'status', 'message': 'LEAD EXTRACTION IN PROGRESS'})}\n\n"
    await asyncio.sleep(1)
    
    for lead in leads_data:
        yield f"data: {json.dumps({'type': 'lead', 'data': lead})}\n\n"
        await asyncio.sleep(2)
        
    yield f"data: {json.dumps({'type': 'status', 'message': 'Foraging cycle complete. 5 high-value leads processed, analyzed, and actioned autonomously.'})}\n\n"
    yield "data: [DONE]\n\n"

def simulate_foraging():
    print("================================================================")
    print(" AI-BS: Multi-Industry Autonomous Lead Foraging Engine (Demo) ")
    print("================================================================")
    print_typewriter("[SYSTEM] Initializing distributed web scrapers...")
    time.sleep(1)
    print_typewriter("[SYSTEM] Bypassing CAPTCHAs and loading heuristics engine...")
    time.sleep(1)
    
    for ind in industries:
        print(f"\n---> [TARGET LOCKED] Initializing {ind['name']} pipelines...")
        for target in ind['targets']:
            print(f"     [+] Scanning {target}...")
            time.sleep(0.4)
            
    print("\n================= LEAD EXTRACTION IN PROGRESS =================\n")
    time.sleep(1)
    
    for lead in leads_data:
        print(f"[NEW LEAD FOUND] Sector: {lead['industry']}")
        print(f" | Data: {lead['lead']}")
        print_typewriter(f" | AI-BS Action: {lead['action']}", delay=0.02)
        print("-" * 60)
        time.sleep(1.5)
        
    print("\n[SYSTEM] Foraging cycle complete. 5 high-value leads processed, analyzed, and actioned autonomously.")
    print("================================================================")

if __name__ == "__main__":
    simulate_foraging()
