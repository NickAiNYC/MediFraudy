@router.get("/export/case/{case_id}")
async def export_case_package(case_id: int, db: Session = Depends(get_db)):
    """Export complete case package including POL analysis"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404)
    
    # Get POL analysis
    pol_analyzer = ElitePatternOfLifeAnalyzer(db)
    pol_result = pol_analyzer.analyze_provider(case.provider_id)
    
    # Generate PDF with POL included
    # ... existing export logic ...
    
    return {
        "case": case.to_dict(),
        "pol_analysis": pol_result,
        "export_url": f"/exports/case_{case_id}.pdf"
    }
