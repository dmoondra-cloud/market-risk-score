from openpyxl import load_workbook
from typing import Dict
from datetime import datetime


class MarketScoreFiller:
    def __init__(self, template_path: str):
        self.template_path = template_path
        self.wb = load_workbook(template_path)
        self.ws_scores = self.wb['Market Score Scorecard']

    def fill_demand_strength_scores(self, metrics: Dict, demand_score: float):
        if metrics.get('job_growth') is not None:
            self.ws_scores['E10'] = min(5, max(1, int(metrics['job_growth'])))
            self.ws_scores['F10'] = f"Job Growth: {metrics['job_growth']:.2f}%"

        if metrics.get('population_growth') is not None:
            self.ws_scores['E11'] = min(5, max(1, int(metrics['population_growth'])))
            self.ws_scores['F11'] = f"Population Growth: {metrics['population_growth']:.2f}%"

        if metrics.get('current_vacancy_rate') is not None:
            vr = metrics['current_vacancy_rate']
            score = 5 if vr <= 5 else (4 if vr <= 7 else (3 if vr <= 10 else 2))
            self.ws_scores['E12'] = score
            self.ws_scores['F12'] = f"Vacancy Rate: {vr:.2f}%"

    def fill_supply_pressure_scores(self, metrics: Dict, supply_score: float):
        if metrics.get('under_construction_units') is not None:
            uc_units = metrics['under_construction_units']
            score = 2 if uc_units > 500 else (3 if uc_units > 200 else (4 if uc_units > 0 else 5))
            self.ws_scores['E17'] = score
            self.ws_scores['F17'] = f"Under Construction: {int(uc_units)} units"

        if metrics.get('current_vacancy_rate') is not None:
            vr = metrics['current_vacancy_rate']
            score = 5 if vr <= 5 else (4 if vr <= 7 else (3 if vr <= 10 else 2))
            self.ws_scores['E20'] = score
            self.ws_scores['F20'] = f"Current Vacancy: {vr:.2f}%"

    def fill_competitive_positioning_scores(self, metrics: Dict, comp_score: float):
        if metrics.get('avg_effective_rent') is not None and metrics.get('avg_asking_rent') is not None:
            eff_rent = metrics['avg_effective_rent']
            ask_rent = metrics['avg_asking_rent']
            ratio = eff_rent / ask_rent if ask_rent > 0 else 0

            score = 5 if ratio >= 0.95 else (4 if ratio >= 0.90 else (3 if ratio >= 0.85 else 2))
            self.ws_scores['E29'] = score
            self.ws_scores['F29'] = f"Effective/Asking Rent Ratio: {ratio:.2%}"

    def fill_financing_risk_scores(self, metrics: Dict, financing_score: float):
        if metrics.get('sales_volume_12m') is not None:
            sv = metrics['sales_volume_12m']
            score = 5 if sv > 20 else (4 if sv > 10 else (3 if sv > 5 else 2))
            self.ws_scores['E35'] = score
            self.ws_scores['F35'] = f"12-Month Sales: {int(sv)} transactions"

    def fill_all_metrics(self, metrics: Dict, category_scores: Dict):
        self.ws_scores['D4'] = datetime.now().date()

        if category_scores.get('demand_strength'):
            self.fill_demand_strength_scores(metrics, category_scores['demand_strength'])

        if category_scores.get('supply_pressure'):
            self.fill_supply_pressure_scores(metrics, category_scores['supply_pressure'])

        if category_scores.get('competitive_positioning'):
            self.fill_competitive_positioning_scores(metrics, category_scores['competitive_positioning'])

        if category_scores.get('financing_risk'):
            self.fill_financing_risk_scores(metrics, category_scores['financing_risk'])

        self._mark_reviewed(metrics)

    def _mark_reviewed(self, metrics: Dict):
        reviewed_mapping = {
            'D10': metrics.get('job_growth'),
            'D11': metrics.get('population_growth'),
            'D12': metrics.get('current_vacancy_rate'),
            'D17': metrics.get('under_construction_units'),
            'D20': metrics.get('current_vacancy_rate'),
            'D29': metrics.get('avg_effective_rent'),
            'D35': metrics.get('sales_volume_12m'),
        }

        for cell, value in reviewed_mapping.items():
            if value is not None:
                self.ws_scores[cell] = "Yes"

    def save(self, output_path: str):
        self.wb.save(output_path)
        return output_path
