"""
PDF evidence package generator for law offices
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import asyncio
from jinja2 import Template
import pdfkit

logger = logging.getLogger(__name__)

class EvidencePDFGenerator:
    """Generate professional PDF evidence packages"""
    
    def __init__(self):
        self.output_dir = Path("/tmp/evidence_packages")
        self.output_dir.mkdir(exist_ok=True)
    
    async def generate_fca_complaint_pdf(self, evidence_package: Dict[str, Any]) -> str:
        """Generate complete FCA complaint PDF"""
        
        package_id = evidence_package["package_id"]
        provider_data = evidence_package["provider_intelligence"]
        damages = evidence_package["damages"]
        patterns = evidence_package["fraud_patterns"]
        
        # Generate HTML template
        html_content = await self._render_fca_template(
            package_id, provider_data, damages, patterns
        )
        
        # Convert to PDF
        pdf_path = self.output_dir / f"{package_id}_FCA_Complaint.pdf"
        
        try:
            options = {
                'page-size': 'Letter',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None
            }
            
            pdfkit.from_string(html_content, str(pdf_path), options=options)
            
            logger.info(f"✅ Generated FCA complaint PDF: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"❌ PDF generation failed: {e}")
            raise
    
    async def _render_fca_template(self, package_id: str, provider: Dict, damages: Dict, patterns: list) -> str:
        """Render HTML template for FCA complaint"""
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>False Claims Act Complaint - {{ package_id }}</title>
    <style>
        body { font-family: Times, serif; line-height: 1.6; margin: 40px; }
        .header { text-align: center; margin-bottom: 40px; }
        .section { margin-bottom: 30px; }
        .title { font-weight: bold; font-size: 14pt; }
        .content { margin-top: 10px; }
        .damage-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .damage-table th, .damage-table td { border: 1px solid #000; padding: 8px; text-align: left; }
        .damage-table th { background-color: #f0f0f0; }
        .pattern { background-color: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #ccc; }
        .high-risk { border-left-color: #d32f2f; }
        .medium-risk { border-left-color: #f57c00; }
        .signature { margin-top: 100px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>FALSE CLAIMS ACT COMPLAINT</h1>
        <h2>Package ID: {{ package_id }}</h2>
        <p>Generated: {{ generation_date }}</p>
    </div>

    <div class="section">
        <div class="title">UNITED STATES DISTRICT COURT</div>
        <div class="content">
            EASTERN DISTRICT OF NEW YORK<br>
            ----------------------------------------------------<br>
            UNITED STATES OF AMERICA,<br>
            Plaintiff,<br><br>
            v.<br><br>
            {{ provider.provider_info.name }},<br>
            Defendant.<br><br>
            Case No. _______________<br>
            COMPLAINT FOR VIOLATIONS OF THE FALSE CLAIMS ACT<br>
            31 U.S.C. §§ 3729-3733
        </div>
    </div>

    <div class="section">
        <div class="title">PARTIES</div>
        <div class="content">
            <strong>Plaintiff:</strong> United States of America<br>
            <strong>Defendant:</strong> {{ provider.provider_info.name }}<br>
            <strong>Provider NPI:</strong> {{ provider.provider_info.npi }}<br>
            <strong>Location:</strong> {{ provider.provider_info.city }}, {{ provider.provider_info.state }}
        </div>
    </div>

    <div class="section">
        <div class="title">JURISDICTION AND VENUE</div>
        <div class="content">
            This Court has jurisdiction over this action pursuant to 28 U.S.C. § 1331. 
            Venue is proper in this district pursuant to 28 U.S.C. § 1391(b)(2) as a 
            substantial part of the events giving rise to the claim occurred in this district.
        </div>
    </div>

    <div class="section">
        <div class="title">FACTUAL ALLEGATIONS</div>
        <div class="content">
            <p><strong>1.</strong> Defendant {{ provider.provider_info.name }} ("Defendant") is a 
            healthcare provider licensed to provide Medicaid services in the State of New York.</p>
            
            <p><strong>2.</strong> Between {{ provider.claims_statistics.first_claim }} and 
            {{ provider.claims_statistics.last_claim }}, Defendant submitted 
            {{ provider.claims_statistics.total_claims }} claims to Medicaid totaling 
            ${{ "{:,.2f}".format(provider.claims_statistics.total_amount) }}.</p>
            
            <p><strong>3.</strong> Defendant engaged in systematic fraud through the following patterns:</p>
            
            {% for pattern in patterns %}
            <div class="pattern {{ 'high-risk' if pattern.severity == 'high' else 'medium-risk' }}">
                <strong>{{ loop.index }}. {{ pattern.type.replace('_', ' ').title() }}:</strong> 
                {{ pattern.description }}
                <br><em>Legal Theory: {{ pattern.legal_theory }}</em>
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="section">
        <div class="title">DAMAGES</div>
        <div class="content">
            <p>Plaintiff seeks the following damages:</p>
            
            <table class="damage-table">
                <tr>
                    <th>Damage Type</th>
                    <th>Amount</th>
                </tr>
                <tr>
                    <td>Treble Damages (3x)</td>
                    <td>${{ "{:,.2f}".format(damages.treble_damages) }}</td>
                </tr>
                <tr>
                    <td>Civil Penalties (${{ damages.penalty_per_violation }} per violation)</td>
                    <td>${{ "{:,.2f}".format(damages.civil_penalties) }}</td>
                </tr>
                <tr>
                    <td><strong>Total Exposure</strong></td>
                    <td><strong>${{ "{:,.2f}".format(damages.total_exposure) }}</strong></td>
                </tr>
            </table>
            
            <p>Based on {{ damages.violation_count }} violations of the False Claims Act, 
            the total potential exposure exceeds ${{ "{:,.2f}".format(damages.total_exposure) }}.</p>
        </div>
    </div>

    <div class="section">
        <div class="title">PRAYER FOR RELIEF</div>
        <div class="content">
            WHEREFORE, Plaintiff respectfully requests that this Court enter judgment in favor 
            of Plaintiff and against Defendant as follows:
            <ol type="a">
                <li>Treble damages and civil penalties as provided by 31 U.S.C. § 3729(a);</li>
                <li>Interest, costs, and reasonable attorney fees; and</li>
                <li>Such other and further relief as the Court deems just and proper.</li>
            </ol>
        </div>
    </div>

    <div class="signature">
        <div class="title">Respectfully submitted,</div>
        <br><br><br><br>
        ___________________________<br>
        [Attorney Name]<br>
        United States Attorney<br>
        Eastern District of New York
    </div>
</body>
</html>
        """
        
        template = Template(template_content)
        
        return template.render(
            package_id=package_id,
            generation_date=datetime.now().strftime("%B %d, %Y"),
            provider=provider,
            damages=damages,
            patterns=patterns
        )
    
    async def generate_expert_report_pdf(self, evidence_package: Dict[str, Any]) -> str:
        """Generate expert witness report PDF"""
        
        package_id = evidence_package["package_id"]
        expert_basis = evidence_package["expert_basis"]
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Expert Witness Report - {{ package_id }}</title>
    <style>
        body { font-family: Times, serif; line-height: 1.6; margin: 40px; }
        .header { text-align: center; margin-bottom: 40px; }
        .section { margin-bottom: 30px; }
        .title { font-weight: bold; font-size: 14pt; }
        .content { margin-top: 10px; }
        .stats-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .stats-table th, .stats-table td { border: 1px solid #000; padding: 8px; text-align: left; }
        .stats-table th { background-color: #f0f0f0; }
        .signature { margin-top: 100px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>EXPERT WITNESS REPORT</h1>
        <h2>Package ID: {{ package_id }}</h2>
        <p>Date: {{ report_date }}</p>
    </div>

    <div class="section">
        <div class="title">QUALIFICATIONS</div>
        <div class="content">
            <p><strong>Name:</strong> [Expert Name]</p>
            <p><strong>Field:</strong> {{ expert_basis.methodology.field }}</p>
            <p><strong>Experience:</strong> {{ expert_basis.methodology.experience }}</p>
            <p><strong>Certifications:</strong> {{ expert_basis.expert_qualifications.certifications | join(', ') }}</p>
        </div>
    </div>

    <div class="section">
        <div class="title">METHODOLOGY</div>
        <div class="content">
            <p>{{ expert_basis.methodology.description }}</p>
            <p>Statistical analysis performed using {{ expert_basis.methodology.field }} standards 
            and methodologies commonly accepted in healthcare fraud analysis.</p>
        </div>
    </div>

    <div class="section">
        <div class="title">STATISTICAL FINDINGS</div>
        <div class="content">
            <table class="stats-table">
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                    <th>Significance</th>
                </tr>
                <tr>
                    <td>Z-Score</td>
                    <td>{{ expert_basis.statistical_analysis.statistical_significance.z_score }}</td>
                    <td>{{ expert_basis.statistical_analysis.statistical_significance.confidence_level }}</td>
                </tr>
                <tr>
                    <td>P-Value</td>
                    <td>{{ expert_basis.statistical_analysis.statistical_significance.p_value }}</td>
                    <td>{{ expert_basis.statistical_analysis.statistical_significance.statistical_significance }}</td>
                </tr>
            </table>
        </div>
    </div>

    <div class="signature">
        <div class="title">CONCLUSION</div>
        <div class="content">
            <p>Based on my analysis of the Medicaid claims data, I conclude to a reasonable degree of 
            professional certainty that the billing patterns observed are statistically significant 
            and indicative of fraudulent activity rather than normal variation.</p>
        </div>
        
        <br><br><br><br>
        ___________________________<br>
        [Expert Name]<br>
        Certified Fraud Examiner<br>
        Healthcare Data Analyst
    </div>
</body>
</html>
        """
        
        template = Template(template_content)
        
        html_content = template.render(
            package_id=package_id,
            report_date=datetime.now().strftime("%B %d, %Y"),
            expert_basis=expert_basis
        )
        
        pdf_path = self.output_dir / f"{package_id}_Expert_Report.pdf"
        
        try:
            options = {
                'page-size': 'Letter',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None
            }
            
            pdfkit.from_string(html_content, str(pdf_path), options=options)
            
            logger.info(f"✅ Generated expert report PDF: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"❌ Expert report PDF generation failed: {e}")
            raise

# Singleton instance
pdf_generator = EvidencePDFGenerator()
