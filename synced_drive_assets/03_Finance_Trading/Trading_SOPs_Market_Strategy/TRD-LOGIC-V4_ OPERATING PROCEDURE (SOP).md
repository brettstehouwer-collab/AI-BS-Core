### **TRD-LOGIC-V4: STANDARD OPERATING PROCEDURE (SOP)**

**Clearance:** Level 1 (Owner) \| **Protocol:** 10/7 (Adam Stehouwer Memorial) **System Status:** OPERATIONAL

This guide outlines the mandatory workflow for operating the TRD-LOGIC-V4 application. Deviating from this sequence compromises the integrity of the "Hard Law" logic.

---

### **PHASE 1: SYSTEM INITIALIZATION (08:00 AM)**

**Objective:** Ensure the environment is clean and connected.

1. **Launch Opal:** Open the application via your desktop shortcut.  
2. **Refresh (F5):** Always refresh the page upon opening to clear any cached variables from the previous session.  
3. **Visual Check:** Verify that the **"Advisory Insight"** (Gray Box) and **"Master Verdict"** (Card) are visible on the dashboard.

---

### **PHASE 2: MACRO SCAN (The Gatekeeper)**

**Objective:** Determine if the market environment is safe for engagement.

1. **Locate the Input Node:** Find the node labeled **"User Input (Ticker/Balance/Mode)"**.  
2. **Enter Daily Parameters:**  
   * **Ticker:** Enter the asset you are watching (e.g., `SPY`, `SOL`, `NVDA`).  
   * **Balance:** Enter your *current settled cash* (e.g., `10000`).  
   * **Session Mode:**  
     * Type `SIM` for practice/testing.  
     * Type `LIVE` for real execution.  
3. **Execute:** Click the **Play Button** on the dashboard node.  
4. **Analyze the "Master Verdict":**  
   * 🔴 **RED (VETO):** **STOP.** The Macro Environment (DXY/TNX) is hostile. Do not proceed. Walk away.  
   * 🟢 **GREEN (AUTHORIZE):** **PROCEED.** The environment is safe. Move to Phase 3\.

---

### **PHASE 3: TACTICAL PLANNING (Soft Counsel)**

**Objective:** Optimize the entry using the Advisory Layer.

1. **Read the "Advisory Insight" Box:**  
   * Look at the gray box below the Green Verdict card.  
   * **Crypto (e.g., SOL):** Does it mention Tokenomics or FDV? Check the inflation schedule.  
   * **Stocks (e.g., NVDA):** Does it mention Relative Volume? Check if volume is \>5x average.  
   * **General:** Note the specific Fibonacci levels or "Golden Pocket" advice.  
2. **Chart Verification:** Go to your charting platform (TradingView) and confirm the levels mentioned by the Advisory Insight.

---

### **PHASE 4: AUDIT EXECUTION (The Math Gate)**

**Objective:** Validate the specific trade risk before pulling the trigger.

1. **Locate the Audit Node:** Find the node labeled **"Input Auto Buy Variables"** (or similar prompt).

**Input Trade Data:** Copy the template below, update the numbers based on your chart, and paste it into the box:  
Plaintext  
Ticker: \[ASSET\]  
Entry\_Price: \[PRICE\]  
Stop\_Loss: \[PRICE\]  
Take\_Profit: \[PRICE\]  
Risk\_Amount: \[CASH\_RISK\]  
Liquidity\_Grade: \[A/B/C\]

2.   
   * *Critical:* Ensure `Risk_Amount` reflects your actual intended loss limit (e.g., `50` or `1000`).  
3. **Execute:** Click the **Blue Arrow / Send Button**.  
4. **Review the Audit Report:**  
   * Wait for the webpage to generate.  
   * **Check R-Multiple:** Is it \> 3.0?  
   * **Check Position Size:** Note the exact share/token count calculated. **This is your order size.**  
   * **Devil's Advocate:** Read the counter-arguments. If they sting, hesitate.

---

### **PHASE 5: EXECUTION & SHUTDOWN**

1. **Place Order:** If the Audit Report is clean, enter the **Position Size** into your broker.  
2. **Hard Stop (11:00 AM):**  
   * The Python script enforces a time lock.  
   * At 11:01 AM, the system will automatically issue **VETO** on all new requests.  
   * **Close the App.** Trading session is over.

