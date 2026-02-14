# Whistleblower Guide — Using This Tool for False Claims Act Cases

## Overview

This tool is designed to help identify potential Medicaid fraud patterns that may support qui tam (whistleblower) filings under the **False Claims Act (FCA)**. It analyzes the HHS DOGE Medicaid dataset focusing on NYC elderly care and rehabilitation facilities.

> **Disclaimer**: This tool provides statistical analysis only. Always consult with a qualified attorney before filing any legal action.

## Legal Context

### Qui Tam Provisions
- Private parties can file lawsuits on behalf of the government
- Whistleblowers may receive **15–30% of recovery**
- FCA cases can result in treble damages (3× the fraud amount)

### Anti-Kickback Statute
Recent NY cases involved:
- Illegal kickbacks and bribes to Medicaid recipients
- Billing for services never provided
- Laundering proceeds through business entities

## Recent NY Cases for Reference

### Queens — $120M Adult Day Care Fraud (Feb 9, 2026)
- **Pattern**: Billing exceeding facility capacity
- **Detection**: Compare daily billed patients vs licensed capacity
- **Codes**: T2024, T2025 (adult day care services)
- **How this tool helps**: Capacity violation analysis, heatmap visualization

### Brooklyn — $68M Kickback Scheme (Jan 15 & 28, 2026)
- **Pattern**: Sustained high-volume billing (2017–2024), kickbacks to patients
- **Detection**: Enrollment spikes near cash withdrawal patterns, unusual referral networks
- **Codes**: Multiple service categories (adult day care + pharmacy)
- **How this tool helps**: Multi-service facility chart, referral network analysis

### Albany — $1.3M Settlement (Feb 11, 2026)
- **Pattern**: Billing for services not provided
- **Detection**: Statistical outlier analysis, peer comparison

## How to Build a Case

### Step 1: Identify Suspicious Providers
1. Go to **Elderly Care Dashboard** → review outlier providers
2. Filter by Z-score ≥ 3 (statistically significant anomalies)
3. Look for patterns matching recent prosecutions

### Step 2: Gather Evidence
1. Open the provider's detail page → review peer comparison
2. Check fraud patterns detected (high volume, weekend billing, capacity violations)
3. Use the **Evidence Timeline** feature to organize findings chronologically

### Step 3: Create a Case
1. Go to **Cases** → Create New Case
2. Add notes about the specific anomalies observed
3. Build the evidence timeline with dates and descriptions
4. Export the provider report for your records

### Step 4: Export for Attorney Review
1. Use **Export Provider Report** for a structured summary
2. Include:
   - Provider statistics vs peer group
   - Detected anomalies with Z-scores
   - Trend data showing billing patterns over time
   - Confidence indicators for each finding

### Step 5: Contact a Qui Tam Attorney

| Firm | Contact | Phone |
|------|---------|-------|
| Phillips & Cohen | General intake | (212) 220-7110 |
| Constantine Cannon | Whistleblower practice | (212) 350-2700 |
| Kirby McInerney | Thomas Elrod | investigations@kmllp.com |

## Statistical Patterns to Look For

| Pattern | What It Means | Z-Score Threshold |
|---------|---------------|-------------------|
| Sustained high volume | Provider bills far more than peers over multiple months | ≥ 3 |
| Unusual code combinations | Provider bills across too many categories | ≥ 3 |
| Weekend/holiday billing | >30% of claims on weekends | N/A (ratio) |
| Capacity violations | More patients billed than facility can hold | N/A (count) |
| Enrollment spikes | Sudden jump in patient count near cash activity | N/A (trend) |

## Privacy and Security

- All data in this tool is aggregated at the provider level
- No individual patient identifiers are stored or displayed
- Case notes are stored locally in your database
- Use the anonymized reporting option if you prefer not to be identified initially
