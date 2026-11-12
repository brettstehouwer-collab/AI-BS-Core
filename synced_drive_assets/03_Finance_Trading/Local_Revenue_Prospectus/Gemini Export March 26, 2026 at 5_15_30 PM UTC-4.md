![][image1]

![][image2]

The **Localized Revenue Maximization Prospectus** outlines a strategic framework for capturing localized capital through integrated digital systems and algorithmic optimization. Based on the operational segments provided, here are the key takeaways:

### **Key Takeaways**

> * **Strategic Geographic Monopolization**: The primary objective is to establish a dominant presence within the West Michigan corridor, specifically targeting the Holland, Zeeland, and Jenison areas. This strategy aims to mitigate "capital attrition" by redirecting localized consumer search volume toward the Target Enterprise using superior digital architectures.  
> * **Stratified Financial Architecture**: The prospectus defines a bifurcated fiscal structure designed to scale from initial visibility to total sector monopolization.  
  * **Tier I (\$495)**: Functions as an organic primer to establish a baseline.  
  * **Tier II (\$995)**: Combines a \$495 retainer with \$500 in distribution capital, which is the absolute minimum required to exit algorithmic learning phases and ensure accurate lead aggregation.  
  * **Tier III (\$1,495)**: A \$745 retainer plus \$750 in distribution capital for full market saturation.  
> * **Temporal Incentivization for Stability**: To ensure long-term capital stability, a mandatory 90-day engagement is required. The incentive structure rewards commitment with increasing fee reductions: 10% reduction at 180 days and 15% at 365 days.

### **Empirical Validation**

The strategy is supported by historical hospitality sector metrics (Noto's hospitality dataset), which documented **3,238,906 verified impressions** generated through organic structural indexing. This volume serves as the baseline that scales exponentially when targeted distribution capital is applied.

The following charts illustrate the capital allocation tiers and the temporal fee reduction structure described in the prospectus.

**Stratified Financial Architecture: Capital Allocation Matrices**

This chart breaks down the total investment for each tier into retainer and distribution capital.

**Temporal Accumulation Matrix: Structural Incentivization**

This chart shows the increasing fee reduction percentage over the course of a 365-day engagement.

The user wants me to analyze the provided data and context, specifically focusing on the "Localized Revenue Maximization" segments (I through VII) mentioned in the prompt.

> Looking at the prompt:

> * It defines 7 "Operational Segments" (I through VII).  
> * Each segment has a "Visual/Data Anchor", "Conceptual Header", "Oratorical Directive", and "Source".  
> * It mentions specific data points:  
  * West Michigan corridor (Holland, Zeeland, Jenison).  
  * Noto's hospitality dataset: 3,238,906 verified impressions.  
  * Financial Architecture:  
    * Tier I: \$495 (organic primer).  
    * Tier II: \$495 retainer \+ \$500 distribution.  
    * Tier III: \$745 retainer \+ \$750 distribution.  
  * \$500 Tier II distribution capital is the "absolute minimum required to exit algorithmic learning phases".  
  * 90-day trajectory graph: 0% reduction for 90 days, 10% for 180 days, 15% for 365 days.  
> * It provides source references \[1\] through \[7\].

> Looking at the files:

> * Localized Revenue Maximization Prospectus-Sheet2-A1:E5-20260326211442.csv: Contains product info (Knitted blanket, Table cloth, Coasters) and AI ad copy.  
> * Localized Revenue Maximization Prospectus-Table 1-A1:F8-20260326211443.csv: This seems to be the main table described in the prompt. It has columns: "Operational Segment (I through VII)", "Visual/Data Anchor", "Conceptual Header", "Oratorical Directive", "Source", "Column 1".  
> * Localized Revenue Maximization Prospectus-Sheet1-A1:G6-20260326211443.csv: Customer opportunity data (Opportunity, Name, Stage, Est. value, Probability, etc.).  
> * Localized Revenue Maximization Prospectus-Source References-A1:B8-20260326211443.csv: Index and Reference names.  
> * user\_selected\_range-Sheet2-A1-20260326211444.csv: Just "Product".

The user's prompt itself contains the text for these segments. It looks like a request to process or visualize this data.

The prompt ends with: "The final syntactical demarcation has been applied to the expanded manuscript... Active Sheet Name: Sheet2". This looks like a continuation of a larger text or a specific formatting request.

However, the user's *input* is actually just the description of the segments. It doesn't explicitly ask for a chart or a specific summary, but the instructions say: "Specific Guidance for Open-Ended Insights and Trend Analysis: This guidance applies only to user queries that request open-ended insights, analysis, trends, or similar... Structure your response around 1 to 3 key takeaways... Prioritize creating visualizations...".

Wait, the user's prompt is a structured list of segments. It looks like they might want me to summarize or visualize this "Prospectus".

Actually, looking at the instruction "Specific Guidance for Simple Responses: Always Provide Evidence... Handle High Volume... Strict Relevance...", and "Specific Guidance for Generate Chart...".

The prompt looks like a document structure.

Segment IV mentions "3,238,906 verified impressions".

Segment V mentions "Tier I (\$495)", "Tier II (\$495 \+ \$500)", "Tier III (\$745 \+ \$750)".

Segment VII mentions "0% reduction for 90 days, 10% for 180 days, and 15% for 365 days".

> I should probably:

> 1. Inspect the tables to confirm the data.  
> 2. Provide a summary of the "Localized Revenue Maximization Prospectus" based on the segments.  
> 3. Create a visualization for the financial tiers or the temporal reduction brackets.

Let's start by inspecting the tables.  
Show code  
Python  
`import pandas as pd`

`# Load the tables to inspect their content`  
`table1 = pd.read_csv('Localized Revenue Maximization Prospectus-Table 1-A1:F8-20260326211443.csv', header=None)`  
`sheet1 = pd.read_csv('Localized Revenue Maximization Prospectus-Sheet1-A1:G6-20260326211443.csv', header=None)`  
`sheet2 = pd.read_csv('Localized Revenue Maximization Prospectus-Sheet2-A1:E5-20260326211442.csv', header=None)`  
`sources = pd.read_csv('Localized Revenue Maximization Prospectus-Source References-A1:B8-20260326211443.csv', header=None)`

`print("Table 1 (Segments):")`  
`print(table1.head())`  
`print("\nSheet 1 (Opportunities):")`  
`print(sheet1.head())`  
`print("\nSheet 2 (Ad Creation):")`  
`print(sheet2.head())`  
`print("\nSources:")`  
`print(sources.head())`

Code output  
`Table 1 (Segments):`  
                                     `0                                                                                                             1                                                          2                                                                                                                                                                                                                                                                                                              3       4         5`  
`0  Operational Segment (I through VII)                                                                                            Visual/Data Anchor                                          Conceptual Header                                                                                                                                                                                                                                                                                           Oratorical Directive  Source  Column 1`  
`1                            Segment I                                                     Minimalist corporate insignia of Stehouwer Publishing LLC  Nomenclatural Designation: Localized Revenue Maximization                                                    Establish strict geographic monopolization parameters within the West Michigan corridor, specifically targeting Holland, Zeeland, and Jenison. Articulate the strategic objective to capture escaping localized capital through integrated digital systems.     1-3       NaN`  
`2                           Segment II  Display Matrix illustrating the disparity between localized search volume and sub-optimal digital visibility   The Diagnostic Axiom: Quantifying the Visibility Deficit                                                             Clinically diagnose the Target Enterprise's current revenue hemorrhage and capital attrition. Explain that algorithmic latency inherently redirects localized consumer capital to non-local competitors possessing superior digital architectures.     1-4       NaN`  
`3                          Segment III                        Abstract geometric progression representing data aggregation and audience segmentation     The Asymmetrical Solution: Proprietary Data Extraction                        Introduce the existence of proprietary mechanisms for the systematic extraction of high-probability consumer data within a precise geographical radius. Adhere to the Asymmetry Protocol; emphasize conceptual capabilities while strictly obfuscating all internal software mechanics.  1-3, 5       NaN`  
`4                           Segment IV                          Display Matrix featuring 3,238,906 verified impressions (Noto's hospitality dataset)    Empirical Validation: Documented Algorithmic Saturation  Present incontrovertible proof of concept via historical hospitality sector metrics. Demonstrate that this volume of 3,238,906 verified impressions was generated through organic structural indexing, serving as a baseline that scales exponentially upon the application of targeted distribution capital.       4       NaN`

`Sheet 1 (Opportunities):`  
             `0     1              2           3                   4            5      6`  
`0  Opportunity  Name          Stage  Est. value  Relationship owner  Probability  Notes`  
`1          NaN   NaN       Prospect         NaN                 NaN          NaN    NaN`  
`2          NaN   NaN       Pitching         NaN                 NaN          NaN    NaN`  
`3          NaN   NaN   Secured lead         NaN                 NaN          NaN    NaN`  
`4          NaN   NaN  Proposal sent         NaN                 NaN          NaN    NaN`

`Sheet 2 (Ad Creation):`  
                 `0                1                                                          2                                                                                                                                                                                                                                                                                                                                                                                                                                       3                                                                                                                                                                         4`  
`0          Product        Objective                                            Audience target                                                                                                                                                                                                                                                                                                                                                                                                                            AI ad copy 1                                                                                                                                                              AI ad copy 2`  
`1  Knitted blanket        Awareness        Adults 30-60, interested in gifts, holidays, winter                                           Experience the timeless comfort of our meticulously crafted knitted blankets, designed to bring warmth and elegance to your home this season. Whether you are seeking the perfect thoughtful gift or a cozy addition to your winter evenings, our collection offers unparalleled quality for those who appreciate the finer details of holiday comfort. Discover the art of relaxation today.    Stay cozy this season with our handcrafted knitted blankets. They make the perfect gift for loved ones or a warm treat for yourself during those chilly winter nights.`  
`2      Table cloth            Leads                     Adults 25-45, interested in home decor  Elevate your dining experience with our premium collection of table cloths, where sophisticated design meets exceptional quality. Perfectly curated for those who take pride in a refined home aesthetic, our linens provide a distinguished foundation for every gathering. Discover how our timeless pieces can transform your interior space and reflect your unique sense of style. Visit us today to explore our exclusive range.  Elevate your next dinner party with a fresh look. Our stylish table cloths are the perfect finishing touch for your home decor. Click to find your favorite style today!`  
`3         Coasters            Sales  Adults 18-35, interested in home decor, DIY, unique gifts                                         Elevate your living space with our premium collection of handcrafted coasters, where sophisticated design meets everyday utility. Perfect for the discerning individual looking to enhance their home decor or find a truly unique gift, these pieces offer a refined touch to any surface. Secure your set today and experience the perfect blend of artisanal craftsmanship and modern style.   Level up your coffee table game with these unique handcrafted coasters. Perfect for home decor lovers or as a one-of-a-kind gift for someone special. Grab yours today!`  
`4              NaN  Website traffic                                                        NaN                                                                                                                                                                                                                                                                                                                                                                                                                                     NaN                                                                                                                                                                       NaN`

`Sources:`  
       `0                                                                   1`  
`0  Index                                                           Reference`  
`1      1  Algorithmic Growth Strategies for West Michigan Commercial Sectors`  
`2      2                                                         Pasted Text`  
`3      3                                                         Pasted Text`  
`4      4  The Stehouwer Publishing Localized Revenue Maximization Prospectus`

> Okay, I have the data.

> * **Table 1** (Segments) contains the 7 segments mentioned in the prompt.  
> * **Sheet 1** (Opportunities) seems mostly empty or just template.  
> * **Sheet 2** (Ad Creation) has some product data.  
> * **Source References** contains the index and reference names.

The user's request is quite abstract. It's a "Localized Revenue Maximization Prospectus" with segments I-VII.

The prompt text provided by the user is exactly what's in Table 1\.

The user's final sentence is: "The final syntactical demarcation has been applied to the expanded manuscript... What's worse? Throwing on a smile...". This sounds like a personal reflection or a continuation of a creative writing piece.

Wait, I should check the segments in Table 1 again.

Segment V: "Tier I (\$495) serves as an organic primer. Tier II (\$495 retainer \+ \$500 distribution) establishes the target baseline. Tier III (\$745 retainer \+ \$750 distribution) enables total sector monopolization."

Segment VII: "0% reduction for 90 days, 10% for 180 days, and 15% for 365 days to secure long-term capital stability."

> I can create two charts:

> 1. A bar chart showing the total cost of each Tier.  
> 2. A line chart (or bar chart) showing the reduction percentage over time.

Also, I should summarize the key takeaways from this "Prospectus".

> Key Takeaways:

> 1. **Geographic Monopolization**: Targeting Holland, Zeeland, and Jenison in West Michigan.  
> 2. **Stratified Financial Architecture**: Three tiers of investment (\$495, \$995, \$1495 total) to scale from organic priming to total sector monopolization.  
> 3. **Temporal Incentivization**: A 90-day mandatory engagement with increasing fee reductions (up to 15% at 365 days) to ensure stability.

Let's refine the data for the charts.

> Tiers:

> * Tier I: \$495 (Retainer only)  
> * Tier II: \$495 (Retainer) \+ \$500 (Distribution) \= \$995  
> * Tier III: \$745 (Retainer) \+ \$750 (Distribution) \= \$1495

> Temporal Reductions:

> * 90 days: 0%  
> * 180 days: 10%  
> * 365 days: 15%

Wait, the prompt says: "Present the incentive structure: 0% reduction for 90 days, 10% for 180 days, and 15% for 365 days".

I will create these charts.  
Show code  
Python  
`import pandas as pd`  
`import altair as alt`

`# Data for Financial Tiers`  
`tiers_data = pd.DataFrame({`  
    `'Tier': ['Tier I', 'Tier II', 'Tier III'],`  
    `'Retainer': [495, 495, 745],`  
    `'Distribution': [0, 500, 750]`  
`})`  
`tiers_data['Total'] = tiers_data['Retainer'] + tiers_data['Distribution']`

`# Melt for stacked bar chart`  
`tiers_melted = tiers_data.melt(id_vars='Tier', value_vars=['Retainer', 'Distribution'], var_name='Category', value_name='Amount')`

`# Create Financial Tiers Chart`  
`tier_chart = alt.Chart(tiers_melted).mark_bar().encode(`  
    `x=alt.X('Tier:N', title='Investment Tier'),`  
    `y=alt.Y('Amount:Q', title='Capital Allocation ($)'),`  
    `color=alt.Color('Category:N', title='Allocation Type'),`  
    `tooltip=['Tier', 'Category', 'Amount']`  
`).properties(`  
    `title='Stratified Financial Architecture: Capital Allocation Matrices',`  
    `width=400,`  
    `height=300`  
`)`

`# Data for Temporal Reductions`  
`reduction_data = pd.DataFrame({`  
    `'Days': [90, 180, 365],`  
    `'Reduction (%)': [0, 10, 15]`  
`})`

`# Create Temporal Reduction Chart`  
`reduction_chart = alt.Chart(reduction_data).mark_line(point=True).encode(`  
    `x=alt.X('Days:Q', title='Continuous Engagement (Days)', scale=alt.Scale(domain=[0, 400])),`  
    `y=alt.Y('Reduction (%):Q', title='Fee Reduction (%)', scale=alt.Scale(domain=[0, 20])),`  
    `tooltip=['Days', 'Reduction (%)']`  
`).properties(`  
    `title='Temporal Accumulation Matrix: Structural Incentivization',`  
    `width=400,`  
    `height=300`  
`)`

`# Save charts`  
`tier_chart.save('financial_tiers.json')`  
`reduction_chart.save('temporal_reductions.json')`

`print("Charts created and saved.")`

Code output  
`Charts created and saved.`

The charts are created. Now I'll provide a summary of the "Localized Revenue Maximization Prospectus" based on the segments.

> Key Takeaways:

> 1. **Strategic Geographic Focus**: The primary objective is to establish strict geographic monopolization within the West Michigan corridor, specifically targeting Holland, Zeeland, and Jenison. This is achieved by capturing escaping localized capital through integrated digital systems.  
> 2. **Stratified Financial Architecture**: The prospectus details a bifurcated fiscal structure with three tiers of investment:  
   * **Tier I (\$495)**: An organic primer for initial visibility.  
   * **Tier II (\$995)**: A \$495 retainer plus \$500 distribution capital, which is the absolute minimum required to exit algorithmic learning phases.  
   * **Tier III (\$1495)**: A \$745 retainer plus \$750 distribution capital, designed for total sector monopolization.  
> 3. **Temporal Incentivization and Stability**: A mandatory 90-day continuous engagement is enforced to secure long-term capital stability. To incentivize this, a fee reduction structure is offered: 0% reduction for the first 90 days, 10% for 180 days, and 15% for 365 days.

I will also mention the "Empirical Validation" from Segment IV: 3,238,906 verified impressions from Noto's hospitality dataset, which serves as a baseline for scaling.

The user's final sentence about "throwing on a smile" and "hiding everything behind a face" seems to be a personal reflection or a continuation of a narrative. I'll acknowledge the prospectus data first and then provide the insights.

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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AHCCoJwhd6VGUALACYJyhtyVGkEJACcIyhlyV2oEJQCcIChnyF2pEZQAcIKgnCF3pUZQAsAJgnKG3JUaQQkAJwjKGXJXagQlAJwgKGfIXakRlABwgqCcIXelRlACwAmCcobclRpBCQAnCMoZcldqBCUAnCAoZ8hdqRGUAHCCoJwhd6VGUALACYJyhtyVGkEJACcIyhlyV2oEJQCcIChnyF2pEZQAcIKgnCF3pUZQAsAJgnKG3JUaQQkAJwjKGXJXagQlAJwgKGfIXakRlABwgqCcIXelRlACwAmCcobclRpBCQAnCMoZcldqBCUAnCAoZ8hdqRGUAHCCoJwhd6XmYYPyo48/+dLj0/Oj4wDwoQjKGXJXasYE5V/9zd8BwN3947d/9o04oZ/cdYPvf/rDN3rrfRkTlEAv//mDf/7sP/7+uzSWm27hTyhnyF2pedigBGbLmzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldqBCVwiby501PuuoGgnCF3pUZQApfImzs95a4bCMoZcldq7h6UX/v6N76Qx4Hd8uZOT7nrBoJy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lAhKgPC1r3/jjWMvqV6frwG6EZQA4XngZezl6zz29Pzo2Gte5zmADgQlQHgp8I5eH12f1+V7br3OcwAdCEqAcBR4t45lAOb1ef5IXpOvAR6doAQAoERQAgBQIigBACgRlAAAlAhKAABKBCUAACWCEgCAEkEJAECJoAQAoERQAgBQIigBACgRlAAAlAhKAABKBCUAACWCEgCAEkEJPKx/+81f/ZJ///3ffeOaR/Abf/qTL/njv/6fN64BmExQAg/re9/6+huen//o40++kO+75cy1r/W3P/jfz775nR+94fk1T7/Oe3x9gEcgKIGHlTF5FJT5nqfjT+eeX/P82NHxo+e3vsaT1wbl0fOj13n86ddw6zqARyAogYeVMfmhg/I13ldQ3jp+6zXAIxGUwMPKmDwKygytjMmMuXz9/DGPv8bZoHz++tav8+hcngd4JIISeFif/uLPfcm//MpjRtUv/PaPv+TX/uQnb1wDMJmgBACgRFACAFAiKAEAKBGUAACUCEoAAEoEJQAAJYISAIASQQkAQImgBACgRFACAFAiKAEAKBGUAACUCEoAAEoEJQAAJYISAIASQQkAQImgBACgRFACAFAiKAEAKBGUAACUCEoAAEoEJQAAJf8PyCaS3dT1cDIAAAAASUVORK5CYII=>