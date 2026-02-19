"""Export endpoints for attorney-ready case packages."""

import os
import json
import pdfkit
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import Case, Provider, Anomaly, TimelineEvent
from analytics.pattern_of_life import ElitePatternOfLifeAnalyzer

router = APIRouter(prefix="/export", tags=["export"])

# Configuration
EXPORT_DIR = Path("exports")  # Relative path for local/docker compatibility
EXPORT_DIR.mkdir(exist_ok=True, parents=True)

# Try to configure pdfkit (optional - falls back to JSON if not available)
try:
    PDF_CONFIG = pdfkit.configuration()
    PDF_AVAILABLE = True
except:
    PDF_AVAILABLE = False
    print("PDF generation not available - install wkhtmltopdf for PDF support")


class ExportPackage(BaseModel):
    """Schema for export package response."""
    case_id: int
    provider_id: int
    provider_name: str
    risk_score: int
    risk_level: str
    pol_analysis: dict
    anomalies: list
    timeline: list
    generated_at: str
    export_url: Optional[str] = None
    pdf_available: bool = PDF_AVAILABLE


def generate_case_export_package(
    db: Session,
    case_id: int,
    include_pol: bool = True
) -> ExportPackage:
    """Core logic for generating export package."""
    # Get case
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get provider
    provider = db.query(Provider).filter(Provider.id == case.provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Get anomalies
    anomalies = db.query(Anomaly).filter(
        Anomaly.provider_id == provider.id
    ).order_by(Anomaly.detected_at.desc()).all()
    
    # Get timeline events
    timeline = db.query(TimelineEvent).filter(
        TimelineEvent.case_id == case.id
    ).order_by(TimelineEvent.event_date).all()
    
    # Run fresh POL analysis if requested
    pol_result = None
    if include_pol:
        try:
            pol_analyzer = ElitePatternOfLifeAnalyzer(db)
            pol_result = pol_analyzer.analyze_provider(provider.id)
        except Exception as e:
            print(f"POL analysis failed: {e}")
            pol_result = {"error": "POL analysis unavailable"}
    
    # Build export package
    return ExportPackage(
        case_id=case.id,
        provider_id=provider.id,
        provider_name=provider.name,
        risk_score=int(pol_result.get("risk_score", 0)) if pol_result else 0,
        risk_level=str(pol_result.get("risk_level", "UNKNOWN")) if pol_result else "UNKNOWN",
        pol_analysis=pol_result or {},
        anomalies=[_anomaly_dict(a) for a in anomalies],
        timeline=[_timeline_dict(t) for t in timeline],
        generated_at=datetime.utcnow().isoformat(),
        pdf_available=PDF_AVAILABLE
    )

@router.get("/case/{case_id}")
async def export_case_package(
    case_id: int,
    format: str = Query("json", pattern="^(json|pdf)$"),
    include_pol: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Export complete case package including POL analysis.
    """
    package = generate_case_export_package(db, case_id, include_pol)
    
    # Return JSON
    if format == "json":
        return JSONResponse(content=package.dict())
    
    # Generate PDF (if available)
    if format == "pdf":
        if not PDF_AVAILABLE:
            raise HTTPException(
                status_code=501,
                detail="PDF generation not available on this server"
            )
        
        pdf_path = generate_pdf(package, case_id)
        return FileResponse(
            path=pdf_path,
            filename=f"case_{case_id}_export.pdf",
            media_type="application/pdf"
        )


@router.get("/provider/{provider_id}")
async def export_provider_package(
    provider_id: int,
    include_pol: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Quick export for a provider (without creating a case).
    Useful for initial attorney review.
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Get anomalies
    anomalies = db.query(Anomaly).filter(
        Anomaly.provider_id == provider_id
    ).order_by(Anomaly.detected_at.desc()).limit(50).all()
    
    # Run POL analysis
    pol_result = None
    if include_pol:
        try:
            pol_analyzer = ElitePatternOfLifeAnalyzer(db)
            pol_result = pol_analyzer.analyze_provider(provider_id)
        except Exception as e:
            print(f"POL analysis failed: {e}")
    
    return {
        "provider": _provider_dict(provider),
        "risk_score": pol_result.get("risk_score", 0) if pol_result else 0,
        "risk_level": pol_result.get("risk_level", "UNKNOWN") if pol_result else "UNKNOWN",
        "pol_summary": {
            "capacity_violations": pol_result.get("indicators", {}).get("capacity_exceed", {}),
            "kickback_indicators": pol_result.get("indicators", {}).get("referral_concentration", {}),
            "behavioral_anomalies": pol_result.get("indicators", {}).get("timing_anomaly", {}),
        } if pol_result else {},
        "anomalies": [_anomaly_dict(a) for a in anomalies],
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/batch")
async def export_batch_packages(
    case_ids: str = Query(..., description="Comma-separated list of case IDs"),
    db: Session = Depends(get_db)
):
    """
    Export multiple cases as a ZIP file.
    Format: /export/batch?case_ids=1,2,3,4
    """
    import zipfile
    from io import BytesIO
    
    ids = [int(x.strip()) for x in case_ids.split(",")]
    
    # Create ZIP in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for case_id in ids:
            case = db.query(Case).filter(Case.id == case_id).first()
            if not case:
                continue
            
            # Generate JSON for this case
            provider = db.query(Provider).filter(Provider.id == case.provider_id).first()
            pol_analyzer = ElitePatternOfLifeAnalyzer(db)
            pol_result = pol_analyzer.analyze_provider(provider.id)
            
            package = {
                "case_id": case.id,
                "provider": provider.name if provider else "Unknown",
                "risk_score": pol_result.get("risk_score", 0),
                "risk_level": pol_result.get("risk_level", "UNKNOWN"),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Add to ZIP
            zip_file.writestr(
                f"case_{case_id}_summary.json",
                json.dumps(package, indent=2)
            )
    
    zip_buffer.seek(0)
    return FileResponse(
        path=zip_buffer,
        filename=f"case_batch_export_{datetime.now().strftime('%Y%m%d')}.zip",
        media_type="application/zip"
    )


# --- Helper Functions ---

def generate_pdf(package: ExportPackage, case_id: int) -> str:
    """Generate PDF from package data."""
    import pdfkit
    
    # Simple HTML template
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Case Export - {package.provider_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #2c3e50; }}
            .risk-high {{ color: #c0392b; font-weight: bold; }}
            .risk-medium {{ color: #e67e22; font-weight: bold; }}
            .risk-low {{ color: #27ae60; font-weight: bold; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .section {{ margin: 30px 0; }}
        </style>
    </head>
    <body>
        <h1>Medicaid Whistleblower Case Export</h1>
        <p>Generated: {package.generated_at}</p>
        
        <div class="section">
            <h2>Provider Information</h2>
            <table>
                <tr><th>Name</th><td>{package.provider_name}</td></tr>
                <tr><th>Provider ID</th><td>{package.provider_id}</td></tr>
                <tr><th>Case ID</th><td>{package.case_id}</td></tr>
                <tr><th>Risk Score</th>
                    <td class="risk-{package.risk_level.lower()}">{package.risk_score}</td>
                </tr>
                <tr><th>Risk Level</th>
                    <td class="risk-{package.risk_level.lower()}">{package.risk_level}</td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Pattern-of-Life Indicators</h2>
            <table>
    """
    
    # Add POL indicators
    for key, value in package.pol_analysis.get("indicators", {}).items():
        if isinstance(value, dict) and "score" in value:
            html += f"""
                <tr>
                    <th>{key.replace('_', ' ').title()}</th>
                    <td>Score: {value['score']}</td>
                    <td>{value.get('details', '')}</td>
                </tr>
            """
    
    html += """
            </table>
        </div>
        
        <div class="section">
            <h2>Anomalies ({})</h2>
            <table>
                <tr>
                    <th>Code</th>
                    <th>Z-Score</th>
                    <th>Type</th>
                    <th>Detected</th>
                </tr>
    """.format(len(package.anomalies))
    
    for a in package.anomalies[:20]:  # Limit to 20 for PDF
        html += f"""
                <tr>
                    <td>{a.get('billing_code', '')}</td>
                    <td>{a.get('z_score', 0):.2f}</td>
                    <td>{a.get('anomaly_type', '')}</td>
                    <td>{a.get('detected_at', '')}</td>
                </tr>
        """
    
    html += """
            </table>
        </div>
        
        <div class="section">
            <h2>Timeline Events ({})</h2>
            <table>
                <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Evidence Type</th>
                </tr>
    """.format(len(package.timeline))
    
    for t in package.timeline:
        html += f"""
                <tr>
                    <td>{t.get('event_date', '')}</td>
                    <td>{t.get('description', '')}</td>
                    <td>{t.get('evidence_type', '')}</td>
                </tr>
        """
    
    html += """
            </table>
        </div>
        
        <div class="section">
            <h2>Legal Notice</h2>
            <p>This document contains confidential information prepared for potential 
            False Claims Act litigation. Protected by attorney-client privilege.</p>
        </div>
    </body>
    </html>
    """
    
    # Generate PDF
    pdf_path = EXPORT_DIR / f"case_{case_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdfkit.from_string(html, str(pdf_path), configuration=PDF_CONFIG)
    
    return str(pdf_path)


def _provider_dict(p: Provider) -> dict:
    return {
        "id": p.id,
        "npi": p.npi,
        "name": p.name,
        "facility_type": p.facility_type,
        "city": p.city,
        "state": p.state,
        "licensed_capacity": p.licensed_capacity,
    }


def _anomaly_dict(a: Anomaly) -> dict:
    return {
        "id": a.id,
        "billing_code": a.billing_code,
        "z_score": a.z_score,
        "anomaly_type": a.anomaly_type,
        "notes": a.notes,
        "detected_at": str(a.detected_at) if a.detected_at else None,
    }


def _timeline_dict(t: TimelineEvent) -> dict:
    return {
        "id": t.id,
        "event_date": str(t.event_date),
        "description": t.description,
        "evidence_type": t.evidence_type,
    }
