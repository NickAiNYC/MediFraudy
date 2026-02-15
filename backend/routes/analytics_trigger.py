from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
import io
import csv
from sqlalchemy.orm import Session
from typing import List, Dict, Union, Optional
from database import get_db
from analytics.market_basket import ClaimsAprioriAnalyzer
from analytics.peer_grouping import PeerProfiler
from analytics.member_profiling import MemberProfiler
from analytics.sadc_detector import SADCDetector
from analytics.pharmacy_detector import PharmacyDetector
from analytics.cdpap_detector import CDPAPDetector
from analytics.recipient_detector import RecipientDetector
from analytics.nemt_detector import NEMTFraudDetector
from analytics.homecare_detector import HomeCareFraudDetector
from analytics.dashboard_summary import DashboardAggregator
from models import AssociationRule, PeerGroup
import json
from analytics.pattern_of_life import (
    analyze_nyc_elderly_care_facilities,
    detect_kickback_patterns,
    comprehensive_pattern_analysis,
    analyze_behavioral_patterns,
    detect_capacity_violations
)

router = APIRouter(
    prefix="/api/analytics",
    tags=["advanced-analytics"],
    responses={404: {"description": "Not found"}},
)

@router.get("/pattern-of-life/{provider_id}")
def get_full_pattern_of_life_analysis(
    provider_id: int, 
    lookback_days: int = 365, 
    db: Session = Depends(get_db)
):
    """
    Run comprehensive Pattern-of-Life analysis (Behavioral + Capacity + Kickbacks).
    """
    return comprehensive_pattern_analysis(db, provider_id, lookback_days)

@router.get("/nyc-elderly-care-sweep")
def get_nyc_elderly_care_sweep(
    min_risk_score: int = 50,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Run a forensic sweep of NYC elderly care facilities.
    """
    results = analyze_nyc_elderly_care_facilities(db, min_risk_score=min_risk_score, limit=limit)
    return results

@router.get("/provider/{provider_id}/behavioral")
def get_provider_behavioral(
    provider_id: int, 
    lookback_days: int = 365, 
    db: Session = Depends(get_db)
):
    """
    Analyze specific provider for behavioral anomalies (weekend billing, robotic patterns).
    """
    return analyze_behavioral_patterns(db, provider_id, lookback_days)

@router.get("/provider/{provider_id}/capacity")
def get_provider_capacity(
    provider_id: int, 
    lookback_days: int = 365, 
    db: Session = Depends(get_db)
):
    """
    Check if a provider is billing for more patients than their licensed capacity.
    """
    return detect_capacity_violations(db, provider_id, lookback_days)

@router.get("/provider/{provider_id}/kickbacks")
def get_provider_kickbacks(
    provider_id: int, 
    lookback_days: int = 365, 
    db: Session = Depends(get_db)
):
    """
    Analyze provider for kickback indicators (beneficiary concentration, referral anomalies).
    """
    return detect_kickback_patterns(db, provider_id, lookback_days)

def export_to_csv(data: List[Dict], filename: str = "export.csv"):
    if not data:
        # Return empty CSV
        return StreamingResponse(
            iter([""]), 
            media_type="text/csv", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/run-apriori")
def run_apriori_analysis(
    limit: int = 50000,
    min_support: float = 0.01,
    min_confidence: float = 0.5,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Trigger Apriori algorithm to find association rules.
    Runs in background as it can be slow.
    """
    # Create the analyzer instance
    analyzer = ClaimsAprioriAnalyzer(db, min_support, min_confidence)
    
    # Define a wrapper function for the background task
    def run_analysis_task(limit: int):
        # We need a new session for the background task because the dependency session might be closed
        # However, for simplicity in this synchronous example, we are using the passed db session.
        # In a real production app with async endpoints, you'd use a fresh session.
        # Given the current setup is synchronous, we'll just run it.
        # BUT, BackgroundTasks run AFTER the response is sent, so the 'db' session from Depends might be closed.
        # We need to instantiate a new session inside the task.
        from database import SessionLocal
        with SessionLocal() as session:
            task_analyzer = ClaimsAprioriAnalyzer(session, min_support, min_confidence)
            task_analyzer.run_analysis(limit)

    if background_tasks:
        background_tasks.add_task(run_analysis_task, limit)
        return {"message": "Apriori analysis started in background", "limit": limit}
    
    # Sync run (for testing if no background task provided, though FastAPI always provides it)
    rules = analyzer.run_analysis(limit)
    return {"message": "Analysis complete", "rules_found": len(rules) if rules else 0}

@router.get("/association-rules")
def get_association_rules(db: Session = Depends(get_db)):
    """Get discovered association rules."""
    return db.query(AssociationRule).order_by(AssociationRule.confidence.desc()).all()

@router.post("/run-peer-profiling")
def run_peer_profiling(
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Trigger Peer Group Profiling.
    1. Creates peer groups.
    2. Calculates baselines.
    """
    from database import SessionLocal
    
    def run_profiling_job():
        with SessionLocal() as session:
            profiler = PeerProfiler(session)
            profiler.create_peer_groups()
            profiler.calculate_baselines()
    
    if background_tasks:
        background_tasks.add_task(run_profiling_job)
        return {"message": "Peer profiling started in background"}
        
    run_profiling_job()
    return {"message": "Peer profiling complete"}

@router.get("/peer-groups")
def get_peer_groups(db: Session = Depends(get_db)):
    """Get peer group baselines."""
    return db.query(PeerGroup).all()

@router.get("/peer-outliers")
def get_peer_outliers(threshold: float = 3.0, db: Session = Depends(get_db)):
    """Get providers flagged as outliers within their peer group."""
    profiler = PeerProfiler(db)
    return profiler.identify_outliers(threshold)

@router.get("/member-analysis/high-cost", response_model=List[Dict])
def get_high_cost_members(
    threshold: float = 3.0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Identify members with statistically extreme spending."""
    profiler = MemberProfiler(db)
    return profiler.identify_high_risk_members(threshold, limit)

@router.get("/member-analysis/doctor-shoppers", response_model=List[Dict])
def get_doctor_shoppers(
    threshold: float = 3.0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Identify members visiting unusually many providers."""
    profiler = MemberProfiler(db)
    return profiler.identify_doctor_shoppers(threshold, limit)

@router.get("/member-analysis/stats")
def get_member_statistics(db: Session = Depends(get_db)):
    """Get population statistics for member behavior."""
    profiler = MemberProfiler(db)
    return profiler.get_member_stats()

@router.get("/member-analysis/pill-mills", response_model=List[Dict])
def get_pill_mill_suspects(
    drug_codes: List[str] = Query(None, description="List of drug codes (e.g. J2270). Defaults to common opioids if empty."),
    threshold: float = 3.0,
    db: Session = Depends(get_db)
):
    """
    Identify patients receiving extreme quantities of controlled substances (Pill Mill Detection).
    """
    profiler = MemberProfiler(db)
    return profiler.identify_pill_mill_patients(drug_codes, threshold)

@router.get("/recipient/card-sharing")
def get_card_sharing_suspects(min_distance: float = 50.0, format: str = "json", db: Session = Depends(get_db)):
    detector = RecipientDetector(db)
    results = detector.detect_card_sharing(min_distance)
    
    if format == "csv":
        return export_to_csv(results, "recipient_card_sharing.csv")
    return results

@router.get("/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Get aggregated risk statistics for the main dashboard.
    """
    aggregator = DashboardAggregator(db)
    return aggregator.get_summary_stats()

# --- SADC Fraud Routes ---

@router.get("/sadc/attendance-heatmap")
def get_sadc_heatmap(limit: int = 1000, db: Session = Depends(get_db)):
    """
    Get daily attendance data for heatmap visualization.
    """
    detector = SADCDetector(db)
    return detector.get_daily_attendance_heatmap(limit)

@router.get("/sadc/attendance-spikes")
def get_sadc_attendance_spikes(threshold: float = 2.5, format: str = "json", db: Session = Depends(get_db)):
    """
    Detect Social Adult Day Care (SADC) centers with suspicious daily attendance spikes.
    """
    detector = SADCDetector(db)
    results = detector.detect_attendance_spikes(threshold)
    
    if format == "csv":
        return export_to_csv(results, "sadc_attendance_spikes.csv")
    return results

@router.get("/sadc/impossible-attendance")
def get_sadc_impossible_attendance(db: Session = Depends(get_db)):
    """
    Identify beneficiaries attending SADC programs daily (impossible for frail elderly).
    """
    detector = SADCDetector(db)
    return detector.detect_impossible_attendance()

@router.get("/sadc/ghost-patients")
def get_sadc_ghost_patients(format: str = "json", db: Session = Depends(get_db)):
    """
    Identify 'Ghost' patients: High SADC attendance but ZERO other medical claims.
    """
    detector = SADCDetector(db)
    results = detector.detect_ghost_patients()
    
    if format == "csv":
        return export_to_csv(results, "sadc_ghost_patients.csv")
    return results

# --- Pharmacy Fraud Routes ---

@router.get("/pharmacy/lidocaine-dumping")
def get_lidocaine_dumping(threshold: float = 5000.0, format: str = "json", db: Session = Depends(get_db)):
    """
    Detect providers prescribing excessive Lidocaine patches (phantom pain kickbacks).
    """
    detector = PharmacyDetector(db)
    results = detector.detect_lidocaine_dumping(threshold)
    
    if format == "csv":
        return export_to_csv(results, "pharmacy_lidocaine_dumping.csv")
    return results

# --- CDPAP Fraud Routes ---

@router.get("/cdpap/suspicious-caregivers")
def get_cdpap_suspicious_caregivers(max_patients: int = 2, min_hours: float = 8.0, format: str = "json", db: Session = Depends(get_db)):
    """
    Identify caregivers with few patients billing high hours (likely relatives).
    """
    detector = CDPAPDetector(db)
    results = detector.detect_suspicious_caregivers(max_patients, min_hours)
    
    if format == "csv":
        return export_to_csv(results, "cdpap_suspicious_caregivers.csv")
    return results

@router.get("/cdpap/network")
def get_cdpap_network(limit: int = 100, db: Session = Depends(get_db)):
    """
    Get graph data for CDPAP caregiver-patient relationships.
    """
    detector = CDPAPDetector(db)
    return detector.get_caregiver_network(limit)

@router.get("/cdpap/impossible-hours")
def get_cdpap_impossible_hours(db: Session = Depends(get_db)):
    """
    Identify caregivers billing > 24 hours in a single day across all patients.
    """
    detector = CDPAPDetector(db)
    return detector.detect_overlapping_hours()

import zipfile
from datetime import datetime

# ... existing code ...

@router.get("/recipient/reselling-meds")
def get_medication_reselling_suspects(min_pharmacies: int = 3, format: str = "json", db: Session = Depends(get_db)):
    """
    Identify beneficiaries engaging in medication reselling or doctor shopping.
    """
    detector = RecipientDetector(db)
    results = detector.detect_medication_resale(min_pharmacies)
    
    if format == "csv":
        return export_to_csv(results, "recipient_medication_reselling.csv")
    return results

# --- NEMT Fraud Routes ---

@router.get("/nemt/ghost-rides")
def get_nemt_ghost_rides(limit: int = 50, format: str = "json", db: Session = Depends(get_db)):
    """
    Detect Ghost Rides (Transport without medical service).
    """
    detector = NEMTFraudDetector(db)
    results = detector.detect_ghost_rides_systemwide(limit)
    
    if format == "csv":
        return export_to_csv(results, "nemt_ghost_rides.csv")
    return results

@router.get("/nemt/impossible-trips")
def get_nemt_impossible_trips(limit: int = 50, format: str = "json", db: Session = Depends(get_db)):
    """
    Detect Impossible Trips (Mileage Inflation).
    """
    detector = NEMTFraudDetector(db)
    results = detector.detect_impossible_trips_systemwide(limit)
    
    if format == "csv":
        return export_to_csv(results, "nemt_impossible_trips.csv")
    return results

@router.get("/export/doj-package")
def export_doj_referral_package(db: Session = Depends(get_db)):
    """
    Generate a comprehensive 'DOJ Referral Package' containing:
    1. SADC Attendance Spikes (CSV)
    2. CDPAP Suspicious Caregivers (CSV)
    3. Pharmacy Lidocaine Dumping (CSV)
    4. Recipient Card Sharing (CSV)
    5. Recipient Medication Reselling (CSV)
    6. NEMT Ghost Rides (CSV)
    7. SUMMARY.txt with high-level statistics
    
    Returns a ZIP file.
    """
    # 1. Gather Data
    sadc_detector = SADCDetector(db)
    sadc_spikes = sadc_detector.detect_attendance_spikes(threshold_z=2.5)
    
    cdpap_detector = CDPAPDetector(db)
    cdpap_suspicious = cdpap_detector.detect_suspicious_caregivers(max_patients=2, min_hours_daily=8.0)
    
    pharmacy_detector = PharmacyDetector(db)
    lidocaine_dumpers = pharmacy_detector.detect_lidocaine_dumping(threshold_amount=5000.0)
    
    recipient_detector = RecipientDetector(db)
    card_sharers = recipient_detector.detect_card_sharing(min_distance_miles=50.0)
    med_resellers = recipient_detector.detect_medication_resale(min_pharmacies=3)

    nemt_detector = NEMTFraudDetector(db)
    ghost_rides = nemt_detector.detect_ghost_rides_systemwide(limit=100)
    impossible_trips = nemt_detector.detect_impossible_trips_systemwide(limit=100)

    # Home Care Fraud (EVV, Ghost Visits)
    homecare_detector = HomeCareFraudDetector(db)
    homecare_risks = homecare_detector.scan_for_high_risk_agencies(limit=50, min_risk_score=40)

    # NYC Elderly Care Sweep (Pattern of Life)
    nyc_sweep = analyze_nyc_elderly_care_facilities(db, min_risk_score=40, limit=500)
    nyc_high_risk = nyc_sweep.get("results", [])
    
    # 2. Create Zip in Memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        
        # Helper to add CSV to zip
        def add_csv(data, filename):
            if not data:
                zip_file.writestr(filename, "")
                return
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            zip_file.writestr(filename, output.getvalue())

        add_csv(sadc_spikes, "1_SADC_Attendance_Spikes.csv")
        add_csv(cdpap_suspicious, "2_CDPAP_Suspicious_Caregivers.csv")
        add_csv(lidocaine_dumpers, "3_Pharmacy_Lidocaine_Dumping.csv")
        add_csv(card_sharers, "4_Recipient_Card_Sharing.csv")
        add_csv(med_resellers, "5_Recipient_Medication_Reselling.csv")
        add_csv(ghost_rides, "6_NEMT_Ghost_Rides.csv")
    
        # 7. Add Full Pattern of Life Reports for High Risk Providers (JSON)
        # We create a folder "Forensic_Reports" in the zip
        # Actually, let's fetch full reports for the top 5 highest risk facilities
        top_5_risky = sorted(nyc_high_risk, key=lambda x: x.get('risk_score', 0), reverse=True)[:5]
        for p in top_5_risky:
            pid = p.get('provider_id')
            if pid:
                # Direct call to analysis function instead of route handler
                full_report = comprehensive_pattern_analysis(db, pid, lookback_days=365)
                report_json = json.dumps(full_report, indent=2, default=str)
                zip_file.writestr(f"Forensic_Reports/Provider_{pid}_POL_Report.json", report_json)

        add_csv(nyc_high_risk, "7_NYC_Elderly_Care_High_Risk.csv")

        # 8. Home Care Fraud Reports (EVV, Ghost Visits)
        add_csv(homecare_risks, "8_Home_Care_Fraud_Risks.csv")
        
        # Add detailed home care analysis for top 5 risky agencies
        top_5_homecare = sorted(homecare_risks, key=lambda x: x.get('risk_score', 0), reverse=True)[:5]
        for p in top_5_homecare:
            pid = p.get('provider_id')
            if pid:
                full_analysis = homecare_detector.generate_homecare_risk_score(pid)
                report_json = json.dumps(full_analysis, indent=2, default=str)
                zip_file.writestr(f"Forensic_Reports/HomeCare_Provider_{pid}_Detailed_Analysis.json", report_json)
    
        # 3. Create Summary Text
        summary = f"""
DOJ MEDICAID FRAUD REFERRAL PACKAGE
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
================================================================

SUMMARY OF FINDINGS
-------------------
1. SADC Fraud (Attendance Spikes): {len(sadc_spikes)} targets identified.
   - Potential kickback schemes timed with 'paydays'.
   
2. CDPAP Fraud (Relative Rackets): {len(cdpap_suspicious)} targets identified.
   - Caregivers billing high hours for single patients (likely relatives).
   
3. Pharmacy Fraud (Lidocaine Dumping): {len(lidocaine_dumpers)} targets identified.
   - Excessive dispensing of high-margin patches.

4. Recipient Fraud:
   - Card Sharing: {len(card_sharers)} beneficiaries.
   - Medication Reselling: {len(med_resellers)} beneficiaries.

5. NEMT Fraud (Ghost Rides): {len(ghost_rides)} providers identified.
   - Billing for transport without corresponding medical claims.

6. NYC Elderly Care Sweep (Pattern of Life): {len(nyc_high_risk)} facilities identified.
   - Comprehensive forensic analysis of Nursing Homes, Adult Day Care, and Home Health Agencies in NYC.
   - Flagged for Capacity Violations, Kickback Patterns, and Behavioral Anomalies.

7. Home Care Fraud (EVV & Ghost Visits): {len(homecare_risks)} agencies identified.
   - Missing EVV records ($14.5B statewide issue).
   - Short visits (< 8 mins) and Ghost Visits (during hospitalization).

================================================================
Generated by MediFraudy Evidence Hub
    """
        zip_file.writestr("SUMMARY_REPORT.txt", summary)

    zip_buffer.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=DOJ_Referral_Package_{timestamp}.zip"}
    )
