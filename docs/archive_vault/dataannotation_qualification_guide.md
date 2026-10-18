# DataAnnotation.tech: Technical Qualification & $35–$45/hr Onboarding Guide

## 1. Overview & Economics

- **Platform:** [DataAnnotation.tech](https://www.dataannotation.tech) (and equivalent [Outlier.ai](https://outlier.ai))
- **Role:** AI Model Evaluator & Code Reviewer (Contractor)
- **Target Revenue:** **`$430.00 / week`**
- **Compensation Rate:** **$35.00 to $45.00 / hour** (Coding / Technical Logic track)
- **Time Commitment:** **12 hours / week** (~1.7 hours / day, or two 50-minute blocks)
- **Client Outreach:** **Zero** (Tasks appear directly in your browser dashboard 24/7; you claim tasks, complete them, and log your time)
- **Payout:** Automated weekly transfers via PayPal or direct ACH to your bank account

---

## 2. The Onboarding Assessment Structure

The evaluation process consists of two primary stages:

1. **The Starter Assessment (General Logic & Reasoning):**
   - Tests reading comprehension, factual verification, and instruction following.
   - Evaluates whether you can spot subtle factual errors, hallucinations, and formatting violations in AI-generated answers.
2. **The Coding Qualification Assessment:**
   - Tests basic-to-intermediate Python (data structures, algorithms, debugging, syntax, and time complexity).
   - Presents two model responses to a programming prompt and requires you to grade correctness, efficiency, and safety, followed by writing a detailed justification.

---

## 3. Four Golden Rules to Pass on the First Attempt

The grading algorithm and human reviewers look for specific behaviors. Failing any of these four rules is the primary cause of applicant rejection:

### Rule 1: Extreme Adherence to Negative Constraints
- Prompt creators intentionally test model obedience with negative constraints (e.g., *"Write a Python function without using the `math` module"*, *"Do not use any loops"*, *"Limit your response to exactly 4 sentences"*).
- **Grading Mandate:** If Model A writes superior code but imports `math` when forbidden, Model A **fails the constraint completely**. You must penalize Model A severely and document the exact violation in your explanation.

### Rule 2: Execute & Verify Every Code Snippet Locally
- Never rely on visual inspection to determine if Python code works.
- **Your Workstation Advantage:** You have a 16-core Ryzen 9 9950X and full local Python environments (`pyppeteer_env`).
- **Workflow:** Copy the code from Model A and Model B into a scratch file (`scratch/test_eval.py`). Run edge cases:
  - Empty lists (`[]`)
  - Negative numbers / zero
  - NoneType inputs
  - Large integer scale
- Document the exact runtime output and any tracebacks in your evaluation.

### Rule 3: Write Deep, Objective Justifications (No Fluff)
- Do not write: *"Model A is better because it is clearer and more helpful."* (Immediate disqualification).
- **Write like a technical editor:**
  > *"Model A correctly implements an O(n) two-pointer approach, properly handling the edge case where the input array contains fewer than two elements by returning `None`. In contrast, Model B uses nested loops with O(n²) complexity and raises an unhandled `IndexError` on empty arrays at line 8 (`arr[i+1]`). Furthermore, Model A strictly follows the prompt constraint to format docstrings in Google style, whereas Model B omitted docstrings entirely."*

### Rule 4: Factual Truthfulness & Hallucination Spotting
- If an answer cites a library, a version number, a historical event, or a mathematical theorem, open a separate tab and verify it via official documentation or Wikipedia.
- If a model invents a nonexistent parameter in `requests.get()` or a fake method in `pandas`, highlight it as a critical factual hallucination.

---

## 4. Step-by-Step Signup & Assessment Execution

1. **Registration:**
   - Go to [DataAnnotation.tech](https://www.dataannotation.tech) and sign up with your primary email and phone number.
   - Select **"I have coding/software experience"** during the profile setup.
2. **Environment Preparation:**
   - Keep your local code editor (VS Code) open side-by-side with your browser.
   - Open a Python terminal ready to paste and test code snippets.
3. **Pacing:**
   - The test is untimed or gives generous multi-hour windows. Do not rush.
   - Spend 20–30 minutes per coding problem verifying every line of code, running edge cases, and polishing your comparative explanation.
4. **Submission & Verification:**
   - Once submitted, reviews typically take 2 to 5 business days. Once approved, your dashboard unlocks with active hourly projects.

---

## 5. Daily Time-Blocking Schedule to Hit $430/Week

| Day | Schedule | Time Spent | Gross Earnings (@ $35/hr) |
| :--- | :--- | :--- | :--- |
| **Monday** | 50m Morning • 50m Evening | 1.7 Hours | **$59.50** |
| **Tuesday** | 50m Morning • 50m Evening | 1.7 Hours | **$59.50** |
| **Wednesday** | 50m Morning • 50m Evening | 1.7 Hours | **$59.50** |
| **Thursday** | 50m Morning • 50m Evening | 1.7 Hours | **$59.50** |
| **Friday** | 50m Morning • 50m Evening | 1.7 Hours | **$59.50** |
| **Saturday** | 100m Weekend Block | 1.7 Hours | **$59.50** |
| **Sunday** | 100m Weekend Block | 1.7 Hours | **$59.50** |
| **Weekly Total** | **~12 Hours Total** | **12.0 Hours** | **`$416.50 – $450.00`** |

Combined with the passive **Vast.ai GPU Host (~$70/week)**, total net weekly cash flow reaches **`$486.50 – $520.00 / week`** directly deposited into SoFi Bank with **zero sales outreach**.
