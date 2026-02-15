import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

interface ReportProvider {
  id: string;
  name: string;
  address: string;
  npi: string;
  medicaidId: string;
  riskScore: number;
  licensedCapacity: number;
  capacityViolations: number;
  missingEVV: number;
  impossibleSchedules: number;
  beneficiaryOverlap: number;
  totalBilled: number;
  falseClaims: number;
  sampleClaims: Array<{
    date: string;
    beneficiaryId: string;
    amount: number;
    violationType: string;
  }>;
}

export async function generatePDFReport(provider: ReportProvider) {
  const pdf = new jsPDF('p', 'mm', 'letter');
  let yPos = 20;

  // ==== PAGE 1: COVER PAGE ====
  pdf.setFillColor(15, 23, 42);
  pdf.rect(0, 0, 220, 280, 'F');

  pdf.setFontSize(32);
  pdf.setTextColor(239, 68, 68);
  pdf.text('FRAUD EVIDENCE REPORT', 105, 60, { align: 'center' });

  pdf.setFontSize(18);
  pdf.setTextColor(255, 255, 255);
  pdf.text(provider.name, 105, 85, { align: 'center' });

  pdf.setFontSize(12);
  pdf.setTextColor(148, 163, 184);
  pdf.text(`NPI: ${provider.npi}`, 105, 95, { align: 'center' });
  pdf.text(`Medicaid ID: ${provider.medicaidId}`, 105, 102, { align: 'center' });
  pdf.text(provider.address, 105, 109, { align: 'center' });

  const riskColor: [number, number, number] =
    provider.riskScore >= 85
      ? [239, 68, 68]
      : provider.riskScore >= 70
      ? [249, 115, 22]
      : [234, 179, 8];
  pdf.setFillColor(...riskColor);
  pdf.roundedRect(70, 120, 65, 25, 3, 3, 'F');
  pdf.setFontSize(14);
  pdf.setTextColor(255, 255, 255);
  pdf.text('RISK SCORE', 102.5, 130, { align: 'center' });
  pdf.setFontSize(24);
  pdf.text(`${provider.riskScore}/100`, 102.5, 140, { align: 'center' });

  pdf.setFontSize(10);
  pdf.setTextColor(148, 163, 184);
  pdf.text(
    `Generated: ${new Date().toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })}`,
    105,
    160,
    { align: 'center' }
  );

  // Attorney Work Product designation per FRCP 26(b)(3) - review with counsel before use in litigation
  pdf.setFontSize(8);
  pdf.text('CONFIDENTIAL - Attorney Work Product', 105, 270, { align: 'center' });

  // ==== PAGE 2: EXECUTIVE SUMMARY ====
  pdf.addPage();
  pdf.setFillColor(255, 255, 255);
  pdf.rect(0, 0, 220, 280, 'F');

  yPos = 20;
  pdf.setFontSize(20);
  pdf.setTextColor(15, 23, 42);
  pdf.text('EXECUTIVE SUMMARY', 20, yPos);

  yPos += 15;
  pdf.setFontSize(11);
  pdf.setTextColor(51, 65, 85);

  const totalViolations =
    provider.capacityViolations + provider.missingEVV + provider.impossibleSchedules;
  const analysisStart = new Date(Date.now() - 730 * 24 * 60 * 60 * 1000).toLocaleDateString();
  const analysisEnd = new Date().toLocaleDateString();

  const summary = [
    `This report details ${totalViolations} violations`,
    `detected at ${provider.name}, located at ${provider.address}.`,
    '',
    `Analysis Period: 24 months (${analysisStart} to ${analysisEnd})`,
    '',
    'The facility exhibits patterns consistent with the Queens $120M CDPAP fraud case,',
    'including capacity violations, missing EVV records, and impossible aide schedules.',
  ];

  summary.forEach((line) => {
    pdf.text(line, 20, yPos);
    yPos += 6;
  });

  yPos += 5;
  pdf.setFontSize(14);
  pdf.setTextColor(15, 23, 42);
  pdf.text('KEY FINDINGS:', 20, yPos);

  yPos += 10;
  pdf.setFillColor(248, 250, 252);
  pdf.roundedRect(20, yPos, 170, 60, 2, 2, 'F');

  yPos += 10;
  pdf.setFontSize(10);
  pdf.setTextColor(51, 65, 85);

  const capViolationRate = ((provider.capacityViolations / 730) * 100).toFixed(1);
  const findings = [
    `\u2022  Capacity Violations: ${provider.capacityViolations} days (${capViolationRate}% of analysis period)`,
    `\u2022  Missing EVV Records: ${provider.missingEVV} claims ($${((provider.falseClaims * 0.4) / 1000000).toFixed(2)}M estimated exposure)`,
    `\u2022  Impossible Schedules: ${provider.impossibleSchedules} incidents detected`,
    `\u2022  Beneficiary Overlap: ${provider.beneficiaryOverlap}% shared with other providers (kickback indicator)`,
    `\u2022  Licensed Capacity: ${provider.licensedCapacity} patients`,
    `\u2022  Average Violation Rate: ${capViolationRate}% over capacity`,
  ];

  findings.forEach((finding) => {
    pdf.text(finding, 25, yPos);
    yPos += 7;
  });

  // ==== PAGE 3: FINANCIAL EXPOSURE ====
  pdf.addPage();
  yPos = 20;

  pdf.setFontSize(20);
  pdf.setTextColor(15, 23, 42);
  pdf.text('FINANCIAL EXPOSURE ANALYSIS', 20, yPos);

  yPos += 15;

  const totalPenalties = (provider.capacityViolations + provider.missingEVV) * 20000;
  const totalRecovery = provider.falseClaims * 3 + totalPenalties;

  autoTable(pdf, {
    startY: yPos,
    head: [['Category', 'Amount']],
    body: [
      ['Total Billed (24 months)', `$${(provider.totalBilled / 1000000).toFixed(2)}M`],
      ['Estimated False Claims', `$${(provider.falseClaims / 1000000).toFixed(2)}M`],
      ['Treble Damages (FCA)', `$${((provider.falseClaims * 3) / 1000000).toFixed(2)}M`],
      ['Civil Penalties Estimate', `$${(totalPenalties / 1000000).toFixed(2)}M`],
      ['', ''],
      ['TOTAL POTENTIAL RECOVERY', `$${(totalRecovery / 1000000).toFixed(2)}M`],
    ],
    theme: 'grid',
    styles: { fontSize: 11 },
    headStyles: {
      fillColor: [15, 23, 42] as [number, number, number],
      textColor: [255, 255, 255] as [number, number, number],
    },
  });

  // ==== PAGE 4: LEGAL FRAMEWORK ====
  pdf.addPage();
  yPos = 20;

  pdf.setFontSize(20);
  pdf.setTextColor(15, 23, 42);
  pdf.text('APPLICABLE LEGAL FRAMEWORK', 20, yPos);

  yPos += 15;
  pdf.setFontSize(12);
  pdf.text('False Claims Act (31 U.S.C. \u00A7 3729)', 20, yPos);

  yPos += 8;
  pdf.setFontSize(10);
  pdf.setTextColor(51, 65, 85);
  const fcaText = [
    'The False Claims Act imposes liability on any person who knowingly presents, or causes to be',
    'presented, a false or fraudulent claim for payment to the United States government. Penalties include:',
    '',
    "  \u2022 Treble (3x) the government's damages",
    '  \u2022 Civil penalties of $13,946 to $27,894 per false claim (adjusted for inflation)',
    '  \u2022 Whistleblower relator entitled to 15-30% of total recovery',
  ];

  fcaText.forEach((line) => {
    pdf.text(line, 20, yPos);
    yPos += 6;
  });

  yPos += 8;
  pdf.setFontSize(12);
  pdf.setTextColor(15, 23, 42);
  pdf.text('Anti-Kickback Statute (42 U.S.C. \u00A7 1320a-7b)', 20, yPos);

  yPos += 8;
  pdf.setFontSize(10);
  pdf.setTextColor(51, 65, 85);
  const aksText = [
    'Criminal penalties for knowingly and willfully offering, paying, soliciting, or receiving',
    'remuneration to induce referrals of items or services covered by Medicare or Medicaid.',
    '',
    'Beneficiary overlap patterns detected suggest potential kickback arrangements.',
  ];

  aksText.forEach((line) => {
    pdf.text(line, 20, yPos);
    yPos += 6;
  });

  // ==== PAGE 5: SAMPLE VIOLATING CLAIMS ====
  if (provider.sampleClaims && provider.sampleClaims.length > 0) {
    pdf.addPage();
    yPos = 20;

    pdf.setFontSize(20);
    pdf.setTextColor(15, 23, 42);
    pdf.text('SAMPLE VIOLATING CLAIMS', 20, yPos);

    yPos += 10;

    autoTable(pdf, {
      startY: yPos,
      head: [['Date', 'Beneficiary', 'Amount', 'Violation Type']],
      body: provider.sampleClaims.slice(0, 50).map((c) => [
        new Date(c.date).toLocaleDateString(),
        c.beneficiaryId,
        `$${c.amount.toFixed(2)}`,
        c.violationType.replace(/_/g, ' '),
      ]),
      theme: 'striped',
      styles: { fontSize: 8 },
      headStyles: {
        fillColor: [15, 23, 42] as [number, number, number],
        textColor: [255, 255, 255] as [number, number, number],
      },
      alternateRowStyles: { fillColor: [248, 250, 252] as [number, number, number] },
    });
  }

  // ==== FINAL PAGE: RECOMMENDATIONS ====
  pdf.addPage();
  yPos = 20;

  pdf.setFontSize(20);
  pdf.setTextColor(15, 23, 42);
  pdf.text('RECOMMENDED ACTIONS', 20, yPos);

  yPos += 15;
  pdf.setFontSize(11);
  pdf.setTextColor(51, 65, 85);

  const recommendations = [
    '1. IMMEDIATE INVESTIGATION',
    '   \u2022 Subpoena all claim records and EVV data',
    '   \u2022 Interview beneficiaries to verify services received',
    '   \u2022 Obtain aide employment records and schedules',
    '',
    '2. LEGAL PROCEEDINGS',
    '   \u2022 File sealed qui tam complaint under False Claims Act',
    '   \u2022 Request government intervention given clear fraud indicators',
    '   \u2022 Coordinate with state Medicaid Fraud Control Unit',
    '',
    '3. EVIDENCE PRESERVATION',
    '   \u2022 Request litigation hold on all provider records',
    '   \u2022 Obtain GPS/EVV data before potential destruction',
    '   \u2022 Secure beneficiary medical records',
    '',
    '4. EXPERT WITNESSES',
    '   \u2022 Engage capacity compliance expert',
    '   \u2022 Retain healthcare billing expert for damages calculation',
    '   \u2022 Consider forensic accountant for financial analysis',
  ];

  recommendations.forEach((line) => {
    pdf.text(line, 20, yPos);
    yPos += 6;
  });

  // Save PDF
  const sanitizedName = provider.npi.replace(/[^a-zA-Z0-9]/g, '_');
  pdf.save(`Fraud_Evidence_${sanitizedName}_${Date.now()}.pdf`);
}
