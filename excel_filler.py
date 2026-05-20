"""
Excel Workbook Filler
Fills the Market Risk Score template with extracted CoStar data
"""

from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from typing import Dict
from datetime import datetime


class MarketScoreFiller:
    def __init__(self, template_path: str):
        self.template_path = template_path
        self.wb = load_workbook(template_path)
        self.ws_scores = self.wb['Market Score Scorecard']
        self.ws_anchors = self.wb['Anchors and Notes']

    def fill_demand_strength_scores(self, metrics: Dict, demand_score: float):
        """Fill in Demand Strength category scores (rows 10-15)"""

        # Row 10: Employment and wage base
        if metrics.get('job_growth') is not None:
            self._score_row(10, metrics['job_growth'], "Job Growth: {:.2f}%")

        # Row 11: Household growth and in-migration
        if metrics.get('population_growth') is not None:
            self._score_row(11, metrics['population_growth'], "Population Growth: {:.2f}%")

        # Row 12: Net absorption and occupancy trend
        if metrics.get('current_vacancy_rate') is not None:
            vr = metrics['current_vacancy_rate']
            # Lower vacancy = better (higher score)
            if vr <= 5:
                score = 5
            elif vr <= 7:
                score = 4
            elif vr <= 10:
                score = 3
            else:
                score = 2
            self.ws_scores[f'E12'] = score
            self.ws_scores[f'F12'] = f"Vacancy Rate: {vr:.2f}%"

    def fill_supply_pressure_scores(self, metrics: Dict, supply_score: float):
        """Fill in Supply Pressure category scores (rows 17-21)"""

        # Row 17: Pipeline volume relative to inventory
        if metrics.get('under_construction_units') is not None:
            uc_units = metrics['under_construction_units']
            # Higher pipeline = lower score
            if uc_units > 500:
                score = 2
            elif uc_units > 200:
                score = 3
            elif uc_units > 0:
                score = 4
            else:
                score = 5
            self.ws_scores['E17'] = score
            self.ws_scores['F17'] = f"Under Construction: {int(uc_units)} units"

        # Row 20: Vacancy and concessions trend
        if metrics.get('current_vacancy_rate') is not None:
            vr = metrics['current_vacancy_rate']
            if vr <= 5:
                score = 5
            elif vr <= 7:
                score = 4
            elif vr <= 10:
                score = 3
            else:
                score = 2
            self.ws_scores['E20'] = score
            self.ws_scores['F20'] = f"Current Vacancy: {vr:.2f}%"

    def fill_competitive_positioning_scores(self, metrics: Dict, comp_score: float):
        """Fill in Competitive Positioning category scores (rows 29-32)"""

        # Row 29: Effective rent comparable grid
        if metrics.get('avg_effective_rent') is not None and metrics.get('avg_asking_rent') is not None:
            eff_rent = metrics['avg_effective_rent']
            ask_rent = metrics['avg_asking_rent']
            ratio = eff_rent / ask_rent if ask_rent > 0 else 0

            if ratio >= 0.95:
                score = 5
            elif ratio >= 0.90:
                score = 4
            elif ratio >= 0.85:
                score = 3
            else:
                score = 2

            self.ws_scores['E29'] = score
            self.ws_scores['F29'] = f"Effective/Asking Rent Ratio: {ratio:.2%}"

    def fill_financing_risk_scores(self, metrics: Dict, financing_score: float):
        """Fill in Capital & Financing Risk category scores (rows 35-36)"""

        # Row 35: Transaction liquidity and buyer depth
        if metrics.get('sales_volume_12m') is not None:
            sv = metrics['sales_volume_12m']
            if sv > 20:
                score = 5
            elif sv > 10:
                score = 4
            elif sv > 5:
                score = 3
            else:
                score = 2
            self.ws_scores['E35'] = score
            self.ws_scores['F35'] = f"12-Month Sales: {int(sv)} transactions"

    def _score_row(self, row: int, metric_value: float, label: str):
        """Helper to score a single row based on metric value"""
        # Default scoring logic - customize as needed
        if metric_value > 0:
            score = min(5, max(1, int(metric_value)))
        else:
            score = 1

        self.ws_scores[f'E{row}'] = score
        self.ws_scores[f'F{row}'] = label.format(metric_value)

    def fill_all_metrics(self, metrics: Dict, category_scores: Dict):
        """Fill the entire workbook with extracted metrics"""

        # Update date
        self.ws_scores['D4'] = datetime.now().date()

        # Fill category scores
        if category_scores.get('demand_strength'):
            self.fill_demand_strength_scores(metrics, category_scores['demand_strength'])

        if category_scores.get('supply_pressure'):
            self.fill_supply_pressure_scores(metrics, category_scores['supply_pressure'])

        if category_scores.get('competitive_positioning'):
            self.fill_competitive_positioning_scores(metrics, category_scores['competitive_positioning'])

        if category_scores.get('financing_risk'):
            self.fill_financing_risk_scores(metrics, category_scores['financing_risk'])

        # Mark reviewed items
        self._mark_reviewed(metrics)

    def _mark_reviewed(self, metrics: Dict):
        """Mark items as 'Yes' for Reviewed if data was extracted"""
        reviewed_mapping = {
            'D10': metrics.get('job_growth'),  # Employment
            'D11': metrics.get('population_growth'),  # Household growth
            'D12': metrics.get('current_vacancy_rate'),  # Absorption
            'D13': None,  # Bad Debts (not available)
            'D14': None,  # Affordability (needs wage data)
            'D17': metrics.get('under_construction_units'),  # Pipeline
            'D20': metrics.get('current_vacancy_rate'),  # Vacancy trend
            'D29': metrics.get('avg_effective_rent'),  # Rent comps
            'D35': metrics.get('sales_volume_12m'),  # Transaction liquidity
        }

        for cell, value in reviewed_mapping.items():
            if value is not None:
                self.ws_scores[cell] = "Yes"

    def save(self, output_path: str):
        """Save the filled workbook"""
        self.wb.save(output_path)
        return output_path
