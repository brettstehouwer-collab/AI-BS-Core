# **The Invisible Hand: A Comprehensive Analysis of Inter-Market Dynamics and the Architecture of Module XXIII**

## **Executive Summary**

This research report presents a rigorous examination of the inter-market relationships governing high-frequency and intraday price action in risk assets, specifically the Nasdaq-100 and Bitcoin. The objective is to define the theoretical and operational parameters for **Module XXIII**, a quantitative trading filter codenamed **"The Invisible Hand."** This module is designed to function as a "Macro Lock-Out" mechanism, disabling long entries during hostile macroeconomic environments to preserve capital and maintain high win-rate probabilities.

The core thesis of this research is that price movements in high-beta assets (Tech and Crypto) are downstream derivatives of global liquidity flows and the cost of capital. These fundamental drivers are observable in real-time through the price mechanics of the U.S. Dollar Index (DXY) and the U.S. 10-Year Treasury Yield (TNX). By analyzing the intraday inverse correlations between these benchmarks and risk assets, this report derives dynamic probability thresholds that define "Risk-Off" regimes.

The analysis draws upon a diverse range of academic studies, institutional market research, and quantitative trading methodologies. Key findings indicate that the post-2020 market structure has synchronized crypto-assets with traditional monetary policy drivers, necessitating a filter that accounts for the "denominator effect" of the U.S. Dollar and the "discount rate shock" of Treasury yields. The report details the construction of dynamic, volatility-adjusted thresholds using Z-Scores and Average True Range (ATR) to prevent false signals, and elaborates on "divergence" logic to identify regime shifts such as fiscal dominance or inflation scares.

## ---

**1\. Introduction: The Macro-Liquidity Nexus**

In the contemporary landscape of algorithmic and high-frequency trading, the isolationist view of asset pricing—analyzing a chart in a vacuum—has become a liability. Assets do not move independently; they float on a sea of global liquidity. The tide of this liquidity is governed by the central banks and the bond markets, the "Invisible Hand" that dictates the terms of risk-taking behavior. For traders operating in the Nasdaq-100 or Bitcoin markets, understanding the real-time interaction between the U.S. Dollar, Treasury Yields, and equity valuations is not merely an edge; it is a survival requirement.

The primary function of Module XXIII is to quantify this interaction. It serves as a pre-trade risk filter, a "gatekeeper" that assesses the macroeconomic weather before permitting a strategy to open the door to exposure. When the macro environment is hostile—characterized by surging yields and a strengthening dollar—the statistical probability of a sustained rally in risk assets diminishes mathematically. By identifying these periods of hostility with precision, the module prevents the execution of low-probability trades, thereby enhancing the overall Expected Value (EV) of the trading system.

### **1.1 The Evolution of Market Correlations**

The necessity for such a module has been underscored by a structural shift in global market correlations. Prior to the COVID-19 pandemic, the correlation between cryptocurrencies and traditional stock indices was negligible, hovering near zero. Bitcoin behaved as an idiosyncratic asset, largely uncorrelated with the S\&P 500 or the Nasdaq. However, the unprecedented monetary and fiscal response to the pandemic in March 2020 fundamentally altered this dynamic.1

The massive injection of liquidity by the Federal Reserve created a synchronized "everything rally," binding digital assets to the same liquidity cycles that drive technology stocks. Institutional investors, entering the crypto space in scale, began treating Bitcoin as a "high-beta" technology stock rather than a non-correlated safe haven. Consequently, the crypto-stock correlation increased strikingly, and Bitcoin became acutely sensitive to monetary policy shocks and volatility spillovers from the equity markets.1 This synchronization validates the premise of using traditional macro indicators—DXY and TNX—as a unified filter for both asset classes.

### **1.2 Research Objectives**

This report addresses four specific research questions critical to the development of Module XXIII:

1. **Intraday Inverse Correlations**: How do the U.S. Dollar Index (DXY) and the 10-Year Treasury Yield (TNX) inversely impact the intraday pricing of the Nasdaq and Bitcoin?  
2. **"Risk-Off" Thresholds**: What are the specific quantitative thresholds—measured in percentage gains or basis points—at which the probability of successful long trades degrades significantly?  
3. **"Divergence" Signals**: How can the system detect broken correlations (e.g., yields rising without a dollar rally) and what do these divergences signal about the market regime?  
4. **Macro Lock-Out Logic**: How can these insights be synthesized into a robust, dynamic rule set that disables long entries without generating "hallucinations" or false positives?

## ---

**2\. Theoretical Foundations of Inter-Market Liquidity**

To construct a robust quantitative filter, one must first establish the theoretical transmission mechanisms that link the independent variables (DXY, TNX) to the dependent variables (Risk Assets). This relationship is causal, rooted in the fundamental valuation models of finance: the Discounted Cash Flow (DCF) model and the Liquidity Preference Theory.

### **2.1 The Denominator Effect: DXY as the Global Numeraire**

The U.S. Dollar Index (DXY) is the standard metric for USD strength against a basket of foreign currencies, heavily weighted toward the Euro (57.6%) and the Japanese Yen (13.6%).2 However, its significance extends far beyond foreign exchange. The U.S. Dollar serves as the global unit of account, the currency in which the vast majority of global debt and assets are denominated.

The "Denominator Effect" posits that since assets are priced in dollars, a rise in the value of the dollar (the denominator) exerts mechanical downward pressure on the nominal price of the asset (the numerator), assuming the asset's intrinsic value remains constant. Furthermore, a rising DXY signals a contraction in global USD liquidity. When the dollar strengthens, it becomes more expensive for emerging markets and corporations to service dollar-denominated debt, leading to a tightening of credit conditions and a withdrawal of liquidity from speculative markets.3

For Bitcoin and the Nasdaq, which function as "long-duration" assets highly sensitive to liquidity conditions, a rising DXY represents a withdrawal of the fuel required for price appreciation. Empirical evidence suggests that Bitcoin acts as a "high-beta" risk asset that exhibits negative sensitivity to USD strength, rather than as a counter-cyclical hedge.4 Thus, the DXY acts as a barometer for the availability of risk capital.

### **2.2 The Cost of Capital: TNX and the Discount Rate**

The U.S. 10-Year Treasury Yield (TNX) is the proxy for the risk-free rate (![][image1]) in the Capital Asset Pricing Model (CAPM). It forms the baseline against which all other risk assets are valued. The mathematical relationship is governed by the present value formula:

![][image2]  
Where ![][image3] is the Present Value (stock price), ![][image4] are the expected future cash flows, and ![][image1] is the risk-free rate (yield).

As the yield (TNX) rises, the discount rate in the denominator increases. This disproportionately affects "growth" assets—companies like those in the Nasdaq-100, whose valuations are heavily dependent on earnings projected far into the future. A higher discount rate reduces the present value of these distant cash flows, forcing an immediate repricing of the stock.5

Bitcoin, while lacking cash flows, is often traded as a speculative technology play. It competes for capital against the risk-free rate. When yields are low (near 0%), the opportunity cost of holding non-yielding assets like Bitcoin is negligible. However, as yields rise (e.g., to 4.5% or 5%), the opportunity cost increases significantly. Investors are incentivized to rotate capital out of high-risk, non-yielding assets and into risk-free government bonds.6 This dynamic creates a direct, mechanical inverse correlation between TNX and risk asset prices.

### **2.3 The Feedback Loop of Volatility**

The relationship between these assets is also characterized by volatility spillovers. Research indicates that while crypto shocks have little transmission effect to the stock market, volatility spillovers from the stock market to crypto are significant.1 This implies a hierarchy of causality: Macro shocks (Bond Market) impact Equity Markets (Nasdaq), which in turn transmit volatility to Crypto Markets (Bitcoin). This "waterfall" effect confirms that monitoring the top of the funnel—TNX and DXY—is the most effective way to filter risk for assets at the bottom of the funnel.

## ---

**3\. The Independent Variables: DXY and TNX**

Before establishing correlations, it is crucial to understand the nuances of the independent variables themselves. The "Invisible Hand" module relies on accurate data interpretation of DXY and TNX to generate valid signals.

### **3.1 DXY: Composition and Idiosyncrasies**

The DXY is not a perfect measure of USD strength due to its archaic weighting. With the Euro comprising nearly 58% of the index, DXY movements can sometimes reflect idiosyncratic European weakness rather than genuine USD strength. For example, poor economic data from Germany can cause the Euro to fall, pushing DXY up, even if U.S. liquidity conditions haven't tightened.

This necessitates a confirmation mechanism. The **USD/JPY** pair is often a cleaner proxy for U.S. yields and "pure" dollar strength because the Bank of Japan utilizes Yield Curve Control (YCC), pegging their rates and forcing the currency pair to absorb the entire interest rate differential.2 A rise in DXY accompanied by a rise in USD/JPY is a high-confidence signal of broad USD strength. A rise in DXY while USD/JPY falls (Yen strength) suggests the move is driven by Euro weakness, which may have a lower impact on risk assets.

### **3.2 TNX: The Signal vs. The Noise**

Treasury yields are subject to their own volatility regimes. A 5-basis point move in a low-volatility environment is a shock; the same move in a high-volatility environment is noise. Understanding the "Rate of Change" (ROC) is often more important than the absolute level. The market adapts to high rates over time, but it reacts violently to *rapidly rising* rates.

Furthermore, the yield curve itself provides context. The 10-Year Yield (TNX) is the standard benchmark for mortgages and corporate debt, making it the most relevant for broad economic conditions. However, the 2-Year Yield is more sensitive to immediate Federal Reserve policy expectations. For the purpose of a "Macro Filter" focused on equity valuations (duration risk), the 10-Year Yield (TNX) remains the superior metric.6

## ---

**4\. Intraday Correlation Mechanics (Research Q1)**

The first functional requirement of Module XXIII is to accurately track the intraday relationships between the macro variables and the tradeable assets. The effectiveness of the "Invisible Hand" relies on the persistence and reliability of these inverse correlations.

### **4.1 DXY vs. Risk Assets: Wavelet Coherence and Time-Varying Relationships**

The correlation between Bitcoin and the DXY is not a static number; it breathes and evolves over different time horizons. Advanced statistical methods, such as Wavelet Coherence (WTC), allow researchers to decompose this relationship into time-frequency domains.

| Time Horizon | Correlation Character | WTC Findings | Implication for Module XXIII |
| :---- | :---- | :---- | :---- |
| **Short Term (\<30 Days)** | Ephemeral / Sporadic | Negative coherence is observed but is short-lived. Bitcoin may ignore minor DXY moves. | Filter should ignore low-volatility drift. Only high-velocity moves matter. |
| **Medium Term (30-180 Days)** | Event-Driven | Sporadic negative coherence. Often aligned with "flight to safety" events. | Correlation tightens during macro events (CPI, FOMC). |
| **Long Term (\>180 Days)** | Decoupled | Coherence vanishes in most intervals. Bitcoin follows its own adoption curve. | Long-term trend following should not be permanently disabled by high DXY levels, only by DXY *momentum*. |

This analysis reveals a critical insight: Bitcoin exhibits resilience to the global reserve currency during periods of calm but snaps into inverse alignment during periods of stress. The "ephemeral nature" of the negative correlation in the short term suggests that Bitcoin responds briefly to sudden monetary shifts.8 Therefore, Module XXIII must focus on **volatility expansion** in DXY as the trigger, rather than the absolute price level.

### **4.2 TNX vs. Nasdaq/Bitcoin: The Immediate Repricing Mechanism**

The correlation between the 10-Year Yield and the Nasdaq is more mechanical and immediate than that of the DXY. Because algorithmic trading systems (HFTs) dominate the equity futures market, a spike in yields triggers instant selling in Nasdaq futures (NQ) to adjust valuation models.

* **Granger Causality**: Statistical tests confirm that significant Granger causality runs from the Nasdaq to Bitcoin.4 This implies a transmission mechanism where macro shocks hit the bond market first, cascade to the equity market, and finally impact the crypto market.  
* **The Lead-Lag Advantage**: Because the Treasury market is significantly larger and more liquid than the crypto market, it acts as a leading indicator. An intraday breakout in yields often precedes a breakdown in Bitcoin prices by minutes. This latency provides the "Invisible Hand" with a window of opportunity to engage the lock-out before the price damage occurs in the target asset.7

### **4.3 Asymmetric Correlations: The "Risk-Off" Bias**

Recent market analysis has identified an interesting asymmetry in Bitcoin's behavior. While the long-standing positive correlation with the Nasdaq has shown signs of weakening during bullish phases ("decoupling to the upside"), the correlation remains robust during bearish phases ("coupling to the downside").9

Bitcoin appears to ignore Wall Street's optimism at times but reacts swiftly to its pessimism. It continues to respond to Nasdaq sell-offs by trading sharply lower, even if it didn't participate in the prior rally. This asymmetry is highly favorable for a "Lock-Out" module. The goal of the module is risk management (preventing losses), not alpha generation (finding entries). Since the correlation is most reliable during "Risk-Off" events—exactly when the filter is needed—the module's utility is maximized.

### **4.4 The Role of Institutional Investors**

The increased presence of institutional investors in the crypto market has strengthened these correlations. These participants operate cross-asset portfolios and use risk management frameworks that automatically reduce exposure to high-beta assets (Crypto/Tech) when volatility measures (VIX, MOVE Index) or yields rise. This institutional behavior creates a self-fulfilling prophecy where rising macro indicators trigger selling pressure in crypto, reinforcing the validity of the correlation.1

## ---

**5\. Quantitative Threshold Determination (Research Q2)**

To operationalize these theoretical correlations, Module XXIII requires specific, executable numerical thresholds. At what point does a "normal" fluctuation in DXY or TNX become a "hostile" signal that necessitates a trading halt?

### **5.1 Probability Decay and the "Win Rate" Cliff**

The objective of the threshold is to identify the inflection point where the probability (![][image5]) of a successful Long trade drops below a critical acceptance level (e.g., ![][image6]). Professional traders understand that they will be wrong 40-50% of the time 10; the goal is to avoid environments where they are likely to be wrong 70-80% of the time.

### **5.2 DXY Thresholds: The "Pain Point" Analysis**

Analysis of DXY movements highlights several key threshold concepts that define market stress.

#### **5.2.1 The Daily Percentage Gain**

Empirical observation of intraday trading patterns suggests that a daily gain of **\>0.3% to 0.5%** in the DXY is statistically significant enough to suppress risk asset performance. For example, if the DXY base is 100.00, a move to 100.30 represents a notable tightening of liquidity. This magnitude of move is often cited as a "trend day" for the dollar, during which counter-trend trades (Long Risk Assets) have a low probability of success.3

#### **5.2.2 The Psychological Barrier (100.00)**

The **100.00** level in DXY acts as a structural pivot. Trading *above* 100 signals a regime of broad USD strength. Within this zone, the market's sensitivity to dollar moves is heightened. A 0.2% move above 100.00 may have the same psychological impact as a 0.4% move below 100.00 due to the narrative of "Dollar Dominance".11

#### **5.2.3 Intraday Velocity (Rate of Change)**

The *speed* of the move is as critical as the magnitude. A slow drift of \+0.2% over 12 hours allows markets to adjust. A sudden spike of \+0.2% in 30 minutes indicates a shock (e.g., geopolitical news or hot inflation data). Module XXIII must incorporate a velocity threshold, such as a **1-Hour Rate of Change \> 0.15%**.

**Proposed DXY Lock-Out Thresholds:**

* **Standard Lock:** Daily Change \> \+0.35%.  
* **Velocity Lock:** 1-Hour Change \> \+0.15%.  
* **Regime Multiplier:** If DXY \> 100.00, reduce thresholds by 20%.

### **5.3 TNX Thresholds: The Basis Point Barrier**

Yield volatility is measured in basis points (bps). A "standard" day might see a range of 3-5 bps. A "shock" day sees moves significantly larger.

#### **5.3.1 The Volatility Shock**

An intraday move of **\+5 to \+10 basis points** (e.g., from 4.00% to 4.10%) is considered a volatility event for the bond market.12 Such moves force a rapid repricing of equities. The "Invisible Hand" should utilize a **\+6 bps** intraday rise as a primary "Risk-Off" trigger.

#### **5.3.2 Contextual Sensitivity and Convexity**

The impact of yields is non-linear. When yields are already high, the sensitivity of long-duration assets increases (due to bond convexity). Additionally, the speed of the rise matters. A "yield spike" is often the most reliable signal for an immediate Nasdaq sell-off.

**Proposed TNX Lock-Out Thresholds:**

* **Standard Lock:** Intraday Change \> \+6 bps (+0.06% yield).  
* **Velocity Lock:** 15-Minute Change \> \+3 bps.

### **5.4 The "Hostile Environment" Matrix**

By combining these two variables, we can construct a "Macro Heatmap" that categorizes the environment into actionable zones.

| Macro State | DXY Condition | TNX Condition | Long Win Probability | Module Action |
| :---- | :---- | :---- | :---- | :---- |
| **Liquidity Expansion** | Falling (\< \-0.1%) | Stable / Falling | High (\> 60%) | **Enable Longs** |
| **Neutral / Chop** | Range (-0.1% to \+0.1%) | Range (\< 3 bps) | Neutral (50%) | **Standard Filtering** |
| **Yield Shock** | Flat | Spiking (\> \+6 bps) | Low (\< 40%) | **Soft Lock (Tighten)** |
| **Dollar Squeeze** | Rising (\> \+0.3%) | Flat | Low (\< 40%) | **Soft Lock (Tighten)** |
| **"The Wrecking Ball"** | Rising (\> \+0.3%) | Rising (\> \+5 bps) | Very Low (\< 25%) | **HARD LOCK (Disable)** |

This matrix illustrates that the most dangerous environment—"The Wrecking Ball"—occurs when both the cost of capital (Yields) and the scarcity of capital (Dollar) are rising simultaneously.13 In this zone, cash is the only safe asset, and long exposure to high-beta assets is mathematically disadvantageous.

## ---

**6\. Divergence and Regime Identification (Research Q3)**

While correlation provides the baseline, **divergence**—the breakdown of established correlations—provides the most potent alpha signals. Detecting when the market is behaving "irrationally" or shifting regimes is a critical capability of Module XXIII.

### **6.1 The Yield-Dollar Divergence: Fiscal Dominance**

Historically, DXY and TNX move in tandem; higher yields attract foreign capital, boosting the demand for Dollars. However, a dangerous and informative divergence occurs when **TNX Rises** while **DXY Falls**.14

This anomaly signals that foreign investors are selling U.S. Treasuries (driving yields up) but are *not* repatriating the proceeds into Dollars; instead, they are moving to other currencies or hard assets. This indicates a loss of confidence in U.S. fiscal credibility, known as "Fiscal Dominance."

* **Signal Implications**: This is not a standard deflationary "Risk-Off" environment; it is potentially an **inflationary** or **stagflationary** regime.  
* **Asset Reaction**: In this specific scenario, **Bitcoin and Gold** may rally despite rising yields, acting as inflation hedges / debasement hedges. The Nasdaq (Tech), however, will likely still suffer due to the discount rate effect.  
* **Module Logic**: If TNX ![][image7] AND DXY ![][image8] ![][image9] **Inflation Hedge Regime**. The module should maintain the Lock-Out for Nasdaq but *disable* the Lock-Out for Bitcoin, allowing it to capture the "digital gold" bid.

### **6.2 The Stock-Bond Correlation Flip**

The correlation between stock prices and bond prices is non-stationary; it flips between positive and negative depending on the inflation regime.7

* **Growth Regime (Negative Correlation)**: Strong economic data drives yields up (bond prices down) and stocks up. Here, rising yields are benign—they signal growth.  
  * *Stocks* ![][image7] \| *Bonds* ![][image8] (Yields ![][image7])  
* **Inflation Regime (Positive Correlation)**: Inflation fears drive yields up (bond prices down) and stocks *down*. Here, rising yields are toxic.  
  * *Stocks* ![][image8] \| *Bonds* ![][image8] (Yields ![][image7])

**Detection Mechanism**: Module XXIII must calculate a rolling correlation coefficient (e.g., 10-day or 20-day) between the S\&P 500 (SPX) and the 10-Year Yield (TNX).

* If Correlation \> 0.5 (Positive Co-movement of Prices / Negative vs. Yields): The market is in an "Inflation Scare." **Action**: Aggressive Lock-Out on *any* Yield spike.  
* If Correlation \< \-0.5 (Negative Co-movement of Prices / Positive vs. Yields): The market is in a "Growth" regime. **Action**: Looser thresholds; rising yields may be ignored if DXY is stable.

### **6.3 The "Decoupling" Signal (Beta Breakdown)**

A "Broken Correlation" can also signal idiosyncratic strength. If the Nasdaq sells off sharply (-1%) due to a macro headline, but Bitcoin remains flat or trades higher, this is a "Decoupling" event.9

* **Interpretation**: This indicates that crypto-native flows (e.g., ETF buying) are overpowering the macro headwinds.  
* **Module Logic**: If Macro \= Hostile (Red Zone) BUT Asset Price \= Bullish trend AND Volume is High ![][image9] **Override Lock-Out**. This exception logic prevents the filter from missing "Black Swan" upside events specific to crypto, though such events are rare.

## ---

**7\. Module XXIII: Architectural Logic and Implementation (Research Q4)**

This section translates the research findings into a concrete architectural blueprint for "The Invisible Hand." The system is designed to act as a "Macro Gatekeeper," permitting or denying entry signals generated by lower-level strategies.

### **7.1 Data Inputs and Normalization**

The module requires real-time data feeds for:

1. **DXY (U.S. Dollar Index)**: Or a synthetic basket if DXY is unavailable (EURUSD inverted \+ USDJPY).  
2. **US10Y (TNX)**: Or the 10-Year Note Futures (ZN1\!) inverted.  
3. **USD/JPY**: For signal confirmation.  
4. **ATR (Average True Range)**: For dynamic threshold normalization.

### **7.2 Dynamic Thresholding Logic (Avoiding Hallucinations)**

Hard-coded numbers (e.g., "+0.3%") are fragile. They fail when volatility regimes change. A 0.3% move in the high-volatility year of 2022 is common noise, whereas in the low-volatility year of 2017, it is a massive shock. To avoid "hallucinations" (false positives/negatives), the module must use **Z-Scores** or **ATR-based** thresholds.17

**The Z-Score Approach**:

The module calculates the Z-Score of the current intraday move relative to the trailing 20-day distribution of intraday moves.

![][image10]  
Where ![][image11] is the current intraday % change, ![][image12] is the rolling mean of daily changes, and ![][image13] is the rolling standard deviation.

* **Rule**: If the current DXY move represents a **\+2\$\\sigma\$ (2 Standard Deviation)** event, the Lock-Out engages. This statistically ensures that the filter only triggers during "abnormal" stress, regardless of the absolute volatility environment.

### **7.3 Detailed Logic Flow (Pseudo-Code Structure)**

The following logic structure outlines the decision tree for Module XXIII.

Python

\# Module XXIII: "The Invisible Hand" Logic Specification

def macro\_filter\_status(dxy\_data, tnx\_data, usdjpy\_data, asset\_class):  
    """  
    Determines the Macro Lock-Out status.  
    Returns: ALLOW\_LONGS (True/False)  
    """  
      
    \# 1\. Calculate Dynamic Volatility Thresholds (20-Day Lookback)  
    \# Using ATR allows the filter to 'breathe' with the market.  
    dxy\_atr \= calculate\_atr(dxy\_data, period=20)  
    tnx\_atr \= calculate\_atr(tnx\_data, period=20)  
      
    \# Define Sensitivity Multiplier (Z-Score proxy)  
    LOCK\_THRESHOLD \= 1.5  \# Trigger at 1.5x average daily range  
      
    \# 2\. Calculate Real-Time Intraday Change  
    dxy\_change \= calculate\_change\_from\_open(dxy\_data)  
    tnx\_change \= calculate\_change\_from\_open(tnx\_data)  
    usdjpy\_change \= calculate\_change\_from\_open(usdjpy\_data)  
      
    \# 3\. CORE LOGIC: The "Wrecking Ball" Check  
    \# If both Dollar and Yields are surging, disable all Longs.  
    if (dxy\_change \> (dxy\_atr \* LOCK\_THRESHOLD)) and (tnx\_change \> (tnx\_atr \* LOCK\_THRESHOLD)):  
        return False  \# HARD LOCK-OUT  
          
    \# 4\. YIELD SHOCK CHECK (Specific to Tech/Growth)  
    \# Yield spikes are fatal to Nasdaq regardless of Dollar.  
    if tnx\_change \> (tnx\_atr \* 1.8):  
        return False  \# YIELD LOCK-OUT  
          
    \# 5\. DIVERGENCE LOGIC (Regime Detection)  
    \# Check for "Fiscal Dominance" (Yields Up, Dollar Down)  
    if (tnx\_change \> tnx\_atr) and (dxy\_change \< \-0.1):  
        if asset\_class \== "CRYPTO":  
            return True   \# ALLOW Longs (Inflation Hedge Play)  
        elif asset\_class \== "NASDAQ":  
            return False  \# BLOCK Longs (Discount Rate Pain)  
              
    \# 6\. FALSE POSITIVE CHECK (Euro-Driven Noise)  
    \# If DXY is up, but USDJPY is DOWN, the dollar move might be weak Euro.  
    if (dxy\_change \> (dxy\_atr \* LOCK\_THRESHOLD)) and (usdjpy\_change \< 0):  
        return True  \# ALLOW Longs (Signal likely noise)  
          
    \# Default State  
    return True

### **7.4 Implementation Nuances and Risk Standards**

To align with professional risk desk standards, the module incorporates several safety features:

1. **Timeframe Alignment**: The macro filter must align with the execution timeframe. For intraday scalping (1-5 min charts), the module monitors 15-minute or 1-hour Rate of Change (ROC). Using daily open-to-close data is too lagging for high-frequency entries.  
2. **Grace Period (Cool Down)**: After a Lock-Out condition clears (e.g., DXY retraces), the system engages a "Cool Down" timer (e.g., 30 minutes) before re-enabling longs. Volatility aftershocks often trigger stop-losses even after the trend has stabilized.17  
3. **Risk-Based Position Sizing**: Instead of a binary On/Off, the module can feed into a position sizing algorithm.  
   * **Green Zone**: 100% Position Size.  
   * **Yellow Zone**: 50% Position Size.  
   * **Red Zone**: 0% (Lock-Out).  
     This graduated approach dampens variance and smooths the equity curve.  
4. **Shorting Corollary**: While the primary goal is to disable Longs, the "Red Zone" inherently identifies high-probability Short environments. The system can optionally toggle to a "Short-Only" mode when the Lock-Out is active.

## ---

**8\. Conclusion**

Module XXIII, "The Invisible Hand," represents a critical evolution in algorithmic risk management. By harnessing the predictive power of DXY and TNX, quantifying "hostile" environments through dynamic thresholds, and respecting the lead-lag mechanics of asset pricing, the module effectively insulates the trading strategy from macro headwinds.

The research confirms that while market correlations fluctuate, the mechanics of liquidity and valuation remain constant. A surging Dollar restricts global liquidity; spiking Treasury Yields crush equity valuations. By systematically avoiding exposure during these high-probability failure zones, "The Invisible Hand" ensures that capital is deployed only when the macroeconomic tide is rising, rather than when the tsunami is crashing. This transition from a purely technical approach to a macro-aware quantitative system is the hallmark of professional institutional trading, moving beyond the question of "Where is the price going?" to the more fundamental question: "Is the environment safe for travel?"

#### **Works cited**

> 1. Tracing Contagion Risk: From Crypto or Stock? \*, accessed January 29, 2026, [https\://cob.unt.edu/sites/default/files/docs/acct/accounting-conference/program/4.02-Dong%20Fang%20Lin-Tracing%20Contagion%20Risk.pdf](https://cob.unt.edu/sites/default/files/docs/acct/accounting-conference/program/4.02-Dong%20Fang%20Lin-Tracing%20Contagion%20Risk.pdf)  
> 2. USD/JPY: Correlation of DXY vs US10Y \- ACY Securities, accessed January 29, 2026, [https\://acy.com/en/market-news/education/market-education-usdjpy-yield-correlation-guide-j-o-20250805-111847/](https://acy.com/en/market-news/education/market-education-usdjpy-yield-correlation-guide-j-o-20250805-111847/)  
> 3. UNDERSTANDING DXY \- FTUK, accessed January 29, 2026, [https\://ftuk.com/understanding-dxy/](https://ftuk.com/understanding-dxy/)  
> 4. The Relationship between Bitcoin and Nasdaq, U.S. Dollar Index and Commodities, accessed January 29, 2026, [https\://ideas.repec.org/a/eco/journ2/2024-01-29.html](https://ideas.repec.org/a/eco/journ2/2024-01-29.html)  
> 5. How Declining Short-Term U.S. Treasury Yields Impact Bitcoin Price \| Nasdaq, accessed January 29, 2026, [https\://www\.nasdaq.com/articles/how-declining-short-term-us-treasury-yields-impact-bitcoin-price](https://www.nasdaq.com/articles/how-declining-short-term-us-treasury-yields-impact-bitcoin-price)  
> 6. How Does the 10-Year Treasury Yield Affect Bitcoin & Crypto Prices? \- Binance, accessed January 29, 2026, [https\://www\.binance.com/en/square/post/24458358276154](https://www.binance.com/en/square/post/24458358276154)  
> 7. When Do Stocks and Bonds Move Together, and Why Does it Matter? \| Harvard Kennedy School, accessed January 29, 2026, [https\://www\.hks.harvard.edu/centers/mrcbg/programs/growthpolicy/when-do-stocks-and-bonds-move-together-and-why-does-it-matter](https://www.hks.harvard.edu/centers/mrcbg/programs/growthpolicy/when-do-stocks-and-bonds-move-together-and-why-does-it-matter)  
> 8. Bitcoin vs. the US Dollar: Unveiling Resilience Through Wavelet Analysis of Price Dynamics, accessed January 29, 2026, [https\://www\.mdpi.com/1911-8074/18/5/259](https://www.mdpi.com/1911-8074/18/5/259)  
> 9. The Nasdaq-to-Bitcoin Correlation Is Alive and Well (During Risk-Off) \- FOREX.com, accessed January 29, 2026, [https\://www\.forex.com/en-au/news-and-analysis/the-nasdaq-to-bitcoin-correlation-is-alive-and-well-during-risk-off/](https://www.forex.com/en-au/news-and-analysis/the-nasdaq-to-bitcoin-correlation-is-alive-and-well-during-risk-off/)  
> 10. Macro Trading 101: Risk Management, Position Sizing, and Letting Winners Run, accessed January 29, 2026, [https\://www\.investing.com/analysis/macro-trading-101-risk-management-position-sizing-and-letting-winners-run-200665828](https://www.investing.com/analysis/macro-trading-101-risk-management-position-sizing-and-letting-winners-run-200665828)  
> 11. Chart Advisor: What is the Dollar Telling Us? \- Interactive Brokers, accessed January 29, 2026, [https\://www\.interactivebrokers.com/campus/traders-insight/securities/macro/chart-advisor-what-is-the-dollar-telling-us/](https://www.interactivebrokers.com/campus/traders-insight/securities/macro/chart-advisor-what-is-the-dollar-telling-us/)  
> 12. Bitcoin-macro decoupling discussion yet 'premature'; 10Y Treasury yield signals murky outlook: analysts \| The Block, accessed January 29, 2026, [https\://www\.theblock.co/post/350115/bitcoin-macro-decoupling-discussion-yet-premature-10y-treasury-yield-signals-murky-outlook-analysts](https://www.theblock.co/post/350115/bitcoin-macro-decoupling-discussion-yet-premature-10y-treasury-yield-signals-murky-outlook-analysts)  
> 13. How Treasury Yield Spreads Are Influencing Bitcoin Prices in 2025 \- YCharts, accessed January 29, 2026, [https\://get.ycharts.com/resources/blog/how-treasury-yields-are-influencing-crypto-and-what-advisors-need-to-know/](https://get.ycharts.com/resources/blog/how-treasury-yields-are-influencing-crypto-and-what-advisors-need-to-know/)  
> 14. Chart Of the Week \- 10Y Treasury Yield vs. the U.S. Dollar Index \- Waterloo Capital, accessed January 29, 2026, [https\://waterloocap.com/chart-of-the-week-10y-treasury-yield-vs-the-u-s-dollar-index/](https://waterloocap.com/chart-of-the-week-10y-treasury-yield-vs-the-u-s-dollar-index/)  
> 15. Understanding the dynamics of stock/bond correlations \| Vanguard UK Professional, accessed January 29, 2026, [https\://www\.vanguard.co.uk/professional/vanguard-365/investment-knowledge/portfolio-construction/understanding-stock-bond-correlations](https://www.vanguard.co.uk/professional/vanguard-365/investment-knowledge/portfolio-construction/understanding-stock-bond-correlations)  
> 16. When Do Stocks and Bonds Move Together, and Why Does it Matter? \| Econofact, accessed January 29, 2026, [https\://econofact.org/when-do-stocks-and-bonds-move-together-and-why-does-it-matter](https://econofact.org/when-do-stocks-and-bonds-move-together-and-why-does-it-matter)  
> 17. ATR Trading Strategies Guide \- TradersPost Blog, accessed January 29, 2026, [https\://blog.traderspost.io/article/atr-trading-strategies-guide](https://blog.traderspost.io/article/atr-trading-strategies-guide)  
> 18. Atrbands — Indicadores y estrategias \- TradingView, accessed January 29, 2026, [https\://es.tradingview.com/scripts/atrbands/](https://es.tradingview.com/scripts/atrbands/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABSElEQVR4Xu2UzysFcRTFj6SIkigpZUeiJGs7+ScsLcjSSsofYCsrKVnYKVnYi6UtZWOhbG0URflxTnfezDi9N/p6s5JPnXrvnJnbd+69M8A/iXRRw9SIqTY2qc8KHVAT+dVt8IIo6Gwj/HkPUuhAFHnwgKwjskMPUhhAFDnzgBwjshUPUliiPqgF8/sRxa/NT2Yf0Z5RFFu1Rt0jZtBbXJrODPWE2KYGndQ79VbyWjFOLbpZRu1RG7w9Wk/5g+aX0XKcIObUY1nOFaJQt/mN4U6aX0aHm6XmPCjzjOb7f4fwq97qHcS8WlK1//Klvuy/nnQq+62hH1Gv1B61kfk5KjxNrSKK3FJjKIoJ3axM74g4xfc+qy16+l+jQ2hDdMIty4S2rtmT14aW4NzNOnlEm5+Pn7ihhtysg0tqmdpFzKl29MW9cPNv8QUilkSbiRrblgAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAA2CAYAAAB6H8WdAAAE90lEQVR4Xu3dz6ulYxwA8EczaoQYREoNYkr5VaIslGLBggULypSljVKzIDaT5B+YRGkkC6ZYzEI2WJxSZKZk7ceCBQuhZCzIj+frPW/3Od/7nnvuuZ1zT/fM51Pf7nm/z3t+dFffnud5v08pAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcM45r8ZnNf6t8UaNUY2nazzb3BP+Kd09Q/FAcx8AAAsWBde1KXdknM/OjKP1bo1rUg4AgAX5uMahnKwuqvFjTpauiHsi5R4q3f0AACzYHWV4Fi1EAfZyyh0s3f3xN3w5/vvg+C8AAAsWxVfMsG3XiTK5b+3hyWEAABYtiq6jOTl2WU5UZ0tXtPUsgwIAa6Gdkfp+Rvye7o+4oCzP0H603sl0HU+Sxv03pXzv/nEAAOw5d5WN4iteb9czpXvPK3lggUY1Tudk9VHpCrTWVvvdrizde67LAwAAe8WbZaNo25/GthJF0985uUD9518+vt5X4+uyeVbvxhqflq4PWxSdQ0uhf+YEAEB2oMbVTVw6Ofy/KEh6Fzevr2pe55mlRYnCKAq2H/LADFEcPZ6TCxYNcl8tm3uxbVf87z/ISQCALIqu90q3Mb4v2qL7fr+MF4VYNHeN6xfKZEHXL/fdNr5vGS4pG7Nsy/qOVYm9a9Ha4548AACQ/VzjeMq9VSb7hEXB9FxzHZ4vXUG1bI+W7vu/ygN73OEap2rcngcAAFoXlq4Yapc6Q+y7avdkfVe6zfa9x8rOlwJ3on8I4dc8AACw7mIWLT/FGLNr36RcNIptj1x6v3k9TWzKb/fHDcU8+qXR1/MAAMA6i0Lsp9IVQREv1jh/4o5O7F/rC7tYBl3FfrLY69UXbTekMQCAtRXFz1M5OSAOKu8Ltm/bgV32Yel+RzwosRPHSre0u44BAKyhaH0Rxc8VeWDA9aW798my/dmt2FCfTyXIMa9DZf0ePgAAmCoOIc/716bpi7uY4VqVeEDCQwcAwDkjHizo94NFRDE0S9y3ir1rvXhydZXfDwDAFqLJ7HaKynlFj7fdEsVm+4TsPMXntPNUo4ceAMDKxZOs0wqWaeJg9TixYSv5vNFfxrntLhOH2FM3j+h3dybl/qrxUsoNaX/vraVbno6IpW0AgJWJViPzzoJFW5JZRdfNNU7mZOlmvma9tzXKiRmiuHok5X4rXWPiWeKkifZ81LdrHGyuAQB2XZymME+T3Fhi7PfmjSaHNolD1+/MybL8gi1mC9tTJeI0ifi+7ZwnGue+ti1V/mheAwDsuv4oqp1GtCHZSsxq5eO4wrILtv6z4xSI6G0XD1Ic3hieqf1tsbR6qOzOea4AAJv0Jy/sNGaZVpQts2Drz23txWzZa8116/MyvEzavv9AjX3NNQDAWplWlM0q2O4rk4Vhe6xXH7HMOST3vYsl2aHvitnBo2V45m3ofgCAtRRLkTFDlc0q2LJRTmxhVOOT5vpE2fxd0aD4WI17y/Dvy/cDAKytWI6M4ixbZsEWn9s+IRpLnmfHr99p8qMa+5vrXiyp9vcDAKy9u8twW495jXJiTkdqHC+TTXSnFWXR1kPPNQDgnJIb5+7Eop/QjGXQaDkyJBrsAgCcU6IlxjzHQ+2GeBAhjuEaMu9pDwAAa+GLnFihW2qcysmx0zkBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAnvcfraEjNMzOtXwAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAZCAYAAADJ9/UkAAABdElEQVR4Xu2UvytFYRjHH/mRQiglpRgsIgaDycboDgYG/4DZRsrkPzBJySa7xSQWxWKQSSGbZGLz4/vtOefe93y95zp3wXA+9a17nu/zPO97319mJf+EHmhA1J7JyNIh38zVfPZsTn63Qm2BV2UL+qyjF2ijmu1oDrUQ+L3Qhfirgf+NN/MkZdx8ArtQSxDn6jD/LIgpN9CQBmOw0YcGzQe5h26h/iDeZV5DL8YwtKTBGFwmNjpSA8yaT+oc6haPNVwxZQZ60GAek+aN1tUA2+beihpW20/lFFrTYB7cz0doUOIT5s0PJJ4SG3wMmpNYLunJfIL2oJ1Ed+aNF612ZZRXyw7OK3Vo2YNZl2XzBuFVKcq1eW1f8n1l8e3Jhf+WDUbVKMCJeS23qwk6hjrDhJ9IHwNenUbZN6+dgqYTNUTs0BSFrxZrL82XvCG4VCx+VqMg8+b171BFvFzSp1FV9/2NwHPCiY+o8RvwcG1qsKSk5M/5AlsUWlY19PGBAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACIAAAAYCAYAAACfpi8JAAABpklEQVR4Xu2VsStHURTHj1BEiU0pL2WwWIhJGRj9BewWk4GJRVYWUVKSQVlY7CYGymIyi8liJPH9Ovf2u7/z3v3dV/KTep/69N47973zznv3vPtEKv4pC3AXnsO1IL4Ix4PjX2MUXsNPeA/34SVcgq3wCQ75kx0zoueXMckAvHFm9UPf8A0x0aYdcPRK7XruW07how1aekRv8mAHArpF34x9G5550RzcFjEnen2UFrghmoRPHcMXwm0RB6I5RoJYO+xz+8vwKBjLsSOagD3QiDY4bYMBr5LvAebsMrEonDcmiL3ysvhm7Heuw7e6MxKU7uYGsDmZ405qhbA5n8OTUpQthHPNOS9iTDQH+8SzKonmtJQt5ES0Tyxs9kP4IvWNOgkHg2MPp4vrTo53SReSwSkbdKTWDwunq7AfZ+EHXBF9Osux6Ooag0s+HyS2fni24Rm8Fc2XuxcD/MyYjP8WD5dzFrkFO4O4h+vJMLwSvZZfyYSLx+CUFE5LCG/MOWa1LCiTgqp/QAe8cNs/hf+y5L+mGbCX2Kj8r+2ZsabDdSi2FlVURPkC+fRXm1UYLwYAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAZCAYAAADuWXTMAAAAvklEQVR4XmNgGDZAAIglsWCCoBWI/xPANUDMB9OADXxjgCisQpcAgvcMEDkWdAkYAEn+A2IXdAkgeMgAkRdHlwABQQaI5FYg5kCTAwGQoSB5fnQJENBnwO1kRgaE37GCOUD8BIhl0MT1gPg6EK9gwGEryMmngfg1EM8H4llQvJABYhvIv8xw1WggmgGiKAhdghgAsg2kWRNdghgAcjJIMy+6BDEAb0jiA7BoeIsugQ+AEj3MRmRchKxoFIxcAADlATHfoDcDkwAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEwAAAAZCAYAAACb1MhvAAAC+UlEQVR4Xu2XTahNURTH/0KR77xI0bsMFPkYvIGJIaXkI4oBGTBgTBGZvPQGmJKSuhmIIiWkzJhQykeRkXpKGUgiDMjH+ltn37vOsu8999xz6lL7V//u3nvds+/ea6+9zrpAIpH4x5ktWuA0JfeN/5/Nou/Qfe0TrRdNyH1DuS9q+kHLmOhXF30QHW99e/BwPav9oDAiOiUaFS11NvJc9DBrT4Lu7QHagTFfdFj0StTIxrryFTqJZwV0kRegPzQopopuir5AnROYLDov2m7G2OYYbQHu7Zjp03kLTZ97O4f8M13hhD/9IPR6voZ6nqdQB7GrUMQB6Bq9wzZA102HBtj+Ab12AT57xPSfIj8PnfzC9LsyBzrhbW8Q1kEXxBOZ5Wxl4Cb2il6KtjpbETz1o9A85B02jvjN4Jh1APu8JQFex6Gszfmb2WdPMCf4kA2cgdp4wv0yU/RR9EQ00dl6YbdormgT/nYY+50c9sn0mVZsQNBBIdIZXY22qRh6/g3yd5qsgv7wFTfeC7zKZ0XXRcudrQzc2ImsHXMY19fJYXac0XNS9BbqyOAs5jqqZ3gdH4neQRcXJhiH/uAOlI+KxdAcwvmq8lg0L2tXcViABznd9J+JhrM293kNBQGyCzrxNm8oyRJoXjgNvT5VCW8/+4Kow2EBn7e4fx5ygPVYNGfzIU68zBtKQofdRX0OY15h5FvKOiz21g/shNZmAea396Z/T7TW9FtwUZx8hjf0CXPWN2joV+Ei2s6IiXbSa9L38A1qazfmcJZPAc5/0PRbdDqhqoSkfwf68qgD1lE+wi4jvn6ONf1gBqNr2I1xXusw/gOyddsfmB84sQ3FuuGb6bNoDforWC0xh8UKVyZ1X7gGGogXqD7CLon2hw5P34c4FQ3BmuCG9kAL1y3OVgQd5NcariRhcubY1Ux04DRjt/Ct6MsnwqKYTuahUjeQP4SBsRFawNb9v5R/uEdFh0SLnC3AcTomBp3EZ1lW3BKtzJsTiUQikUgkKvMb4mvCyQXjyZEAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAWCAYAAAD5Jg1dAAAAVUlEQVR4XmNgGFRABF0AF0hHF8AGbIH4J5TGCYSAeBYQ10DptajSEOAKxLeBmBuIy6H0fKg4M0yRJjKHAaIQBkDiIHmsAFkhXjCqEC+gvkJ5dAHaAAAAVAyGaWz2QgAAAABJRU5ErkJggg==>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAWCAYAAAD5Jg1dAAAAXElEQVR4XmNgGFRAHl0AFyhHF8AFRhXiBZQr1ARiZiQ+skKQOEgeDMKB+CEQh0H5MIWMUPH3UD4cCAHxLCCugdJrUaVRgS0Q/4TSeAELEK8BYk50CWxAGl2ANgAAou4OIRh11xcAAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAYCAYAAAAYl8YPAAAAX0lEQVR4XmNgGAWjgKpAAV2AEuABxPzoguQCkEFB6IKUgItALI8uSC7gBuLFQCyDLjENiGeRgRcA8S8g7mOgEOB0GTkA5LLt6ILkgisMVIoAFyAWRBckF7SiC4yC4QYA/C8RC4AA67MAAAAASUVORK5CYII=>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAxCAYAAABnGvUlAAACMElEQVR4Xu3dP4sTQRgH4BGxEIvjVBDRQxCx9EDBQrDzGyiIWFoIYiFYiJWI2PoBxE7kPoGVFhYWgpWdjaCHYHV2Fgrn+Q47uUyWmJxmQ5LjeeDH/NkhSfmymd1JCQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAXelI5Fzpr0ROV9e6sDdyqj0JAMDO3C3tychW5EBpj22vmNz7yM1qvFH1AQAY41Bp70Ve1heGeBJ5OiJ7+ksH5ALwcGsMAMA/+hy51J7swHIaLNBWIz+qMQAAY7wtbe/v0GyttF24HvlSjZ9FXqT+9wIAMEYu1K5FNiP7I2cilwdWTCbvX/td+vmz8/61XMRd3F4BALBg3qSmiBqWachPcO4r/bNVvyv5d+d9chdS811ZfioVAGBh5QLnYDU+X+ZOVHOLor1/DQBgV1iq+q8jv6rxorkRudOeBADYLe6n5u7U316VAQDADOVN/7lY28l+svUxedVfCgBAF4btWXte9bv0YA4CALBwtlJTtPXkJyqn8UJbAAD+Qz7e6Wpr7lMavY/t6Jj0jp4CAGBCt1Nzd+1KycMy/lovAgAAAAAAAAAAAAAAmGf5EPePafBg+g8DKwAAmJnjqSnQ8vvhHkXeDV4GAGDWNiMrpb+cmuINAIA5sRrZqMaPI2vVGACAGVuKfKvG+e7aqFMYAACYgVuR75GfSbEGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAdP0Bz/5g+ueIZxkAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAaCAYAAABhJqYYAAAAvklEQVR4XmNgGAUDARygmAPKFwZiNSBmhPLBAMTJAuKLQPwUiF8DcQIQvwXin0A8Ba4SCDKA+CCUDTLtHANEowIDRPNzqBwYgHTCrJIB4idAbAMV+wTEmVA5MOBBYrsA8T8gFkcSwwpYgHgNEP9Hl8AGpIH4ARD/RhID2SoA44CsA5m0B4hboewDMEkGiEdVYByQ4jtAbAXEt4D4CxBfh8qBFAVD2WAA8vEvBkgIBAGxCQMknEH8l1D5UUBHAADTniI11ql4UwAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAYCAYAAADOMhxqAAAAu0lEQVR4XmNgGAWDEXwF4odoYn5A3IsmBgf/gXgPEp8RiOcDcRWSGByIMEA0gEyEARsg/g3ESkhicACSfAvEmkhiRQwQQ7iRxMCABYjXAPEkNPG7DBANGECcASIZhCYOcg7IVpBfhJAlyhkgJpkiiclDxUC2gvy1H0kO7ByQZCUDxDQZqAKQWCsQrwTiGLhqBojVz4FYAIiNgJgVKs4MxGJQGgWATDqALogLgDyMHv54gQMQT2GABO2IAADhgyGfsil5wwAAAABJRU5ErkJggg==>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAYCAYAAADOMhxqAAAAhklEQVR4XmNgGAWDEYQB8Q0g/o8FX0RSBwYSUAlceBVCKQPDLKggK5KYNBB/A2JTJDE4+AvEt9HEBBkghviiiTOIQyU80cRdgPg5ECuhiTPoA/FbINZEE28F4uVAzIImzsDPgGnSBAaIrYxIYigAJFkDZXMC8T8kPk7AAcRGQCyALjEKaA4ATjUf4GBi+ggAAAAASUVORK5CYII=>