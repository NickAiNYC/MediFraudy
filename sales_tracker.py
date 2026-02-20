#!/usr/bin/env python3
"""
MediFraudy Sales Tracker
Track your path to getting paid!
"""

import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

class SalesTracker:
    def __init__(self):
        self.leads = []
        self.contracts = []
        self.payments = []
        
    def add_lead(self, company: str, contact: str, phone: str, email: str):
        """Add a new lead to track"""
        lead = {
            'company': company,
            'contact': contact,
            'phone': phone,
            'email': email,
            'status': 'New',
            'call_date': None,
            'meeting_date': None,
            'proposal_sent': None,
            'contract_signed': None,
            'payment_received': None,
            'notes': '',
            'created_at': datetime.now().isoformat()
        }
        self.leads.append(lead)
        return lead
    
    def update_lead_status(self, company: str, status: str, notes: str = ''):
        """Update lead status"""
        for lead in self.leads:
            if lead['company'] == company:
                lead['status'] = status
                lead['notes'] = notes
                if status == 'Contacted':
                    lead['call_date'] = datetime.now().isoformat()
                elif status == 'Meeting Scheduled':
                    lead['meeting_date'] = datetime.now().isoformat()
                elif status == 'Proposal Sent':
                    lead['proposal_sent'] = datetime.now().isoformat()
                elif status == 'Contract Signed':
                    lead['contract_signed'] = datetime.now().isoformat()
                return lead
        return None
    
    def add_contract(self, company: str, amount: float, signed_date: str):
        """Add a signed contract"""
        contract = {
            'company': company,
            'amount': amount,
            'signed_date': signed_date,
            'status': 'Active',
            'initial_payment': 0,
            'final_payment': 0,
            'implementation_start': None,
            'go_live_date': None
        }
        self.contracts.append(contract)
        return contract
    
    def add_payment(self, company: str, amount: float, payment_type: str, date: str):
        """Add a payment received"""
        payment = {
            'company': company,
            'amount': amount,
            'type': payment_type,  # 'initial' or 'final'
            'date': date,
            'status': 'Received'
        }
        self.payments.append(payment)
        
        # Update contract payment totals
        for contract in self.contracts:
            if contract['company'] == company:
                if payment_type == 'initial':
                    contract['initial_payment'] += amount
                else:
                    contract['final_payment'] += amount
                break
        return payment
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current sales metrics"""
        total_leads = len(self.leads)
        contacted = len([l for l in self.leads if l['status'] == 'Contacted'])
        meetings = len([l for l in self.leads if l['status'] == 'Meeting Scheduled'])
        proposals = len([l for l in self.leads if l['status'] == 'Proposal Sent'])
        contracts = len([l for l in self.leads if l['status'] == 'Contract Signed'])
        
        total_revenue = sum(p['amount'] for p in self.payments)
        initial_payments = sum(p['amount'] for p in self.payments if p['type'] == 'initial')
        final_payments = sum(p['amount'] for p in self.payments if p['type'] == 'final')
        
        return {
            'total_leads': total_leads,
            'contacted': contacted,
            'meetings_scheduled': meetings,
            'proposals_sent': proposals,
            'contracts_signed': contracts,
            'total_revenue': total_revenue,
            'initial_payments': initial_payments,
            'final_payments': final_payments,
            'conversion_rate': (contracts / total_leads * 100) if total_leads > 0 else 0
        }
    
    def get_pipeline_value(self) -> float:
        """Calculate total pipeline value"""
        pipeline_value = 0
        for lead in self.leads:
            if lead['status'] in ['Meeting Scheduled', 'Proposal Sent']:
                pipeline_value += 90000  # Standard contract value
        return pipeline_value
    
    def export_to_csv(self, filename: str):
        """Export leads to CSV"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['company', 'contact', 'phone', 'email', 'status', 
                         'call_date', 'meeting_date', 'proposal_sent', 
                         'contract_signed', 'payment_received', 'notes']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for lead in self.leads:
                writer.writerow({k: v for k, v in lead.items() if k in fieldnames})
    
    def print_dashboard(self):
        """Print sales dashboard"""
        metrics = self.get_metrics()
        pipeline = self.get_pipeline_value()
        
        print("\n" + "="*60)
        print("🚀 MEDIFRAUDY SALES DASHBOARD")
        print("="*60)
        print(f"📊 Total Leads: {metrics['total_leads']}")
        print(f"📞 Contacted: {metrics['contacted']}")
        print(f"🤝 Meetings: {metrics['meetings_scheduled']}")
        print(f"📋 Proposals: {metrics['proposals_sent']}")
        print(f"✅ Contracts: {metrics['contracts_signed']}")
        print(f"💰 Total Revenue: ${metrics['total_revenue']:,.2f}")
        print(f"📈 Pipeline Value: ${pipeline:,.2f}")
        print(f"🎯 Conversion Rate: {metrics['conversion_rate']:.1f}%")
        print("="*60)
        
        # Recent activity
        print("\n📋 RECENT ACTIVITY:")
        for lead in sorted(self.leads, key=lambda x: x['created_at'], reverse=True)[:5]:
            print(f"  • {lead['company']} - {lead['status']}")
        
        # Upcoming payments
        print("\n💳 EXPECTED PAYMENTS:")
        for contract in self.contracts:
            if contract['final_payment'] < 45000:  # Assuming $90K total contracts
                remaining = 90000 - contract['initial_payment'] - contract['final_payment']
                if remaining > 0:
                    print(f"  • {contract['company']}: ${remaining:,.2f} pending")

# Sample usage
if __name__ == "__main__":
    tracker = SalesTracker()
    
    # Add sample leads
    tracker.add_lead("NYC Medicaid Agency", "John Smith", "555-0101", "john@nycmedicaid.gov")
    tracker.add_lead("State Healthcare Provider", "Jane Doe", "555-0102", "jane@statehealth.org")
    tracker.add_lead("Private Healthcare Network", "Bob Johnson", "555-0103", "bob@privatehealth.net")
    
    # Update some statuses
    tracker.update_lead_status("NYC Medicaid Agency", "Contacted", "Interested in AI solution")
    tracker.update_lead_status("State Healthcare Provider", "Meeting Scheduled", "Meeting Thursday 2PM")
    
    # Add a contract
    tracker.add_contract("NYC Medicaid Agency", 90000, datetime.now().isoformat())
    
    # Add payments
    tracker.add_payment("NYC Medicaid Agency", 45000, "initial", datetime.now().isoformat())
    
    # Print dashboard
    tracker.print_dashboard()
    
    # Export to CSV
    tracker.export_to_csv("sales_leads.csv")
    print(f"\n📁 Leads exported to sales_leads.csv")
