"""
Apriori Algorithm for Market Basket Analysis in Healthcare Claims.

Used to detect:
1. Impossible Combinations: Procedure codes that should rarely/never occur together.
2. Unbundling Patterns: Codes that frequently occur together but should be bundled.
3. Fraud Rings: Providers sharing identical, unusual billing patterns.
"""

from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import pandas as pd
from itertools import combinations
from models import Claim, AssociationRule

class ClaimsAprioriAnalyzer:
    def __init__(self, db: Session, min_support: float = 0.01, min_confidence: float = 0.5):
        self.db = db
        self.min_support = min_support
        self.min_confidence = min_confidence

    def fetch_transactions(self, limit: int = 10000) -> List[List[str]]:
        """
        Fetch claims grouped by (provider, beneficiary, date) to form 'baskets'.
        Returns list of transactions (list of billing codes).
        """
        sql = text("""
            SELECT provider_id, beneficiary_id, claim_date, array_agg(billing_code) as basket
            FROM claims
            GROUP BY provider_id, beneficiary_id, claim_date
            HAVING count(*) > 1
            LIMIT :limit
        """)
        
        result = self.db.execute(sql, {"limit": limit})
        transactions = [row.basket for row in result]
        return transactions

    def generate_frequent_itemsets(self, transactions: List[List[str]]) -> Dict[Tuple[str], int]:
        """
        Generate frequent itemsets of size 1 and 2.
        (Simplified implementation for performance - usually we'd use mlxtend).
        """
        item_counts = {}
        pair_counts = {}
        total_transactions = len(transactions)
        
        # Pass 1: Individual items
        for basket in transactions:
            unique_items = set(basket)
            for item in unique_items:
                item_counts[item] = item_counts.get(item, 0) + 1
                
        # Filter by support
        frequent_items = {
            item: count 
            for item, count in item_counts.items() 
            if count / total_transactions >= self.min_support
        }
        
        # Pass 2: Pairs
        for basket in transactions:
            # Only consider items that are frequent
            relevant_items = [item for item in set(basket) if item in frequent_items]
            if len(relevant_items) < 2:
                continue
                
            for pair in combinations(sorted(relevant_items), 2):
                pair_counts[pair] = pair_counts.get(pair, 0) + 1
                
        # Filter pairs by support
        frequent_pairs = {
            pair: count 
            for pair, count in pair_counts.items() 
            if count / total_transactions >= self.min_support
        }
        
        return frequent_items, frequent_pairs, total_transactions

    def generate_rules(self, frequent_items, frequent_pairs, N):
        """Generate association rules from frequent itemsets."""
        rules = []
        
        for pair, pair_count in frequent_pairs.items():
            item_A, item_B = pair
            
            # Rule A -> B
            count_A = frequent_items[item_A]
            conf_A_B = pair_count / count_A
            
            if conf_A_B >= self.min_confidence:
                lift = (pair_count / N) / ((count_A / N) * (frequent_items[item_B] / N))
                rules.append({
                    "antecedents": [item_A],
                    "consequents": [item_B],
                    "support": pair_count / N,
                    "confidence": conf_A_B,
                    "lift": lift
                })
                
            # Rule B -> A
            count_B = frequent_items[item_B]
            conf_B_A = pair_count / count_B
            
            if conf_B_A >= self.min_confidence:
                lift = (pair_count / N) / ((count_B / N) * (frequent_items[item_A] / N))
                rules.append({
                    "antecedents": [item_B],
                    "consequents": [item_A],
                    "support": pair_count / N,
                    "confidence": conf_B_A,
                    "lift": lift
                })
                
        return rules

    def run_analysis(self, limit: int = 50000):
        """Run the full Apriori pipeline and save rules to DB."""
        print(f"Fetching {limit} transactions...")
        transactions = self.fetch_transactions(limit)
        
        if not transactions:
            print("No transactions found.")
            return
            
        print(f"Analyzing {len(transactions)} baskets...")
        freq_items, freq_pairs, N = self.generate_frequent_itemsets(transactions)
        
        print("Generating rules...")
        rules = self.generate_rules(freq_items, freq_pairs, N)
        
        print(f"Saving {len(rules)} rules to database...")
        for r in rules:
            rule_obj = AssociationRule(
                antecedents=r["antecedents"],
                consequents=r["consequents"],
                support=r["support"],
                confidence=r["confidence"],
                lift=r["lift"],
                rule_type="auto_detected",
                description=f"Auto-generated rule: {r['antecedents']} -> {r['consequents']}"
            )
            self.db.add(rule_obj)
        
        self.db.commit()
        return rules
