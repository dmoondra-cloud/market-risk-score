import pdfplumber
import re
from typing import Dict, Optional


class CoStarExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pages = {}
        self._load_pdf()

    def _load_pdf(self):
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                self.pages[i] = page.extract_text()

    def extract_metric(self, pattern: str, page_range: list = None, return_type: str = "float") -> Optional[float]:
        """Extract metric from PDF. If page_range is None, searches all pages."""

        pages_to_search = page_range if page_range else list(self.pages.keys())

        for page_num in pages_to_search:
            if page_num not in self.pages:
                continue
            text = self.pages[page_num]
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1) if match.groups() else match.group(0)
                value = value.strip().replace('%', '').replace(',', '')
                if return_type == "float":
                    try:
                        return float(value)
                    except ValueError:
                        continue
                elif return_type == "int":
                    try:
                        return int(float(value))
                    except ValueError:
                        continue
                else:
                    return value
        return None

    def extract_all_metrics(self) -> Dict:
        """Extract all metrics from CoStar report - searches all pages dynamically."""
        metrics = {}

        # Demand Strength - Search all pages
        metrics['job_growth'] = self.extract_metric(r'JOB\s+GROWTH[^\n]*?([0-9.]+)\s*%')
        metrics['unemployment_rate'] = self.extract_metric(r'[Uu]nemployment\s+[Rr]ate[^\n]*?([0-9.]+)\s*%')
        metrics['population_growth'] = self.extract_metric(r'POPULATION\s+GROWTH[^\n]*?([0-9.]+)\s*%')
        metrics['household_growth'] = self.extract_metric(r'[Hh]ousehold\s+[Gg]rowth[^\n]*?([0-9.]+)\s*%')
        metrics['current_vacancy_rate'] = self.extract_metric(r'(?:OVERALL|STABILIZED|Current)\s+VACANCY[^\n]*?([0-9.]+)\s*%')
        metrics['net_absorption'] = self.extract_metric(r'ABSORPTION[^\n]*?([0-9,]+)\s+units?')
        metrics['avg_asking_rent'] = self.extract_metric(r'Avg\.?\s+(?:Asking\s+)?Rent[^\n]*?\$\s*([0-9,]+)')
        metrics['avg_effective_rent'] = self.extract_metric(r'Effective\s+Rent[^\n]*?\$\s*([0-9,]+)')
        metrics['rent_per_sf'] = self.extract_metric(r'Rent\s+Per\s+SF[^\n]*?\$\s*([0-9.]+)')

        # Supply Pressure - Search all pages
        metrics['under_construction_units'] = self.extract_metric(r'Under\s+Construction[^\n]*?([0-9,]+)\s+units?')
        metrics['deliveries_12_months'] = self.extract_metric(r'Deliveries.*?(?:Past\s+)?12\s+(?:Months?|Mo)[^\n]*?([0-9,]+)\s+units?')

        # Sales/Financing - Search all pages
        metrics['sales_volume_12m'] = self.extract_metric(r'Sales.*?12\s+(?:Months?|Mo)[^\n]*?([0-9,]+)')
        metrics['cap_rate'] = self.extract_metric(r'Cap\s+Rate[^\n]*?([0-9.]+)\s*%')
        metrics['price_per_unit'] = self.extract_metric(r'Price\s+Per\s+Unit[^\n]*?\$\s*([0-9,]+)')

        # Rent Comp Data - Search all pages
        metrics['num_rent_comps'] = self.extract_metric(r'No\.?\s+Rent\s+Comps\s*:?\s*([0-9]+)', return_type='int')
        metrics['avg_rent_comp_vacancy'] = self.extract_metric(r'Avg\.?\s+Vacancy[^\n]*?([0-9.]+)\s*%')

        return metrics

    def score_demand_strength(self, metrics: Dict) -> Optional[float]:
        scores = []
        weights = []

        if metrics.get('job_growth') is not None:
            jg = metrics['job_growth']
            score = 5 if jg >= 2.0 else (4 if jg >= 1.0 else (3 if jg >= 0.0 else (2 if jg >= -1.0 else 1)))
            scores.append(score)
            weights.append(0.5)

        if metrics.get('unemployment_rate') is not None:
            ur = metrics['unemployment_rate']
            score = 5 if ur <= 4.0 else (4 if ur < 5.0 else (3 if ur < 6.0 else (2 if ur < 7.0 else 1)))
            scores.append(score)
            weights.append(0.3)

        if metrics.get('population_growth') is not None:
            pg = metrics['population_growth']
            score = 5 if pg >= 1.5 else (4 if pg >= 0.8 else (3 if pg >= 0.0 else (2 if pg >= -0.5 else 1)))
            scores.append(score)
            weights.append(0.2)

        if not scores:
            return None

        return sum(s * w for s, w in zip(scores, weights)) / sum(weights)

    def score_supply_pressure(self, metrics: Dict) -> Optional[float]:
        scores = []

        if metrics.get('under_construction_units') is not None:
            uc = metrics['under_construction_units']
            score = 2 if uc > 500 else (3 if uc > 200 else (4 if uc > 0 else 5))
            scores.append(score)

        if metrics.get('current_vacancy_rate') is not None:
            vr = metrics['current_vacancy_rate']
            score = 2 if vr > 10 else (3 if vr > 7 else (4 if vr > 5 else 5))
            scores.append(score)

        if not scores:
            return None

        return sum(scores) / len(scores)

    def score_competitive_positioning(self, metrics: Dict) -> Optional[float]:
        if metrics.get('avg_effective_rent') is not None and metrics.get('avg_asking_rent') is not None:
            eff_rent = metrics['avg_effective_rent']
            ask_rent = metrics['avg_asking_rent']

            if ask_rent > 0:
                ratio = eff_rent / ask_rent
                return 5 if ratio >= 0.95 else (4 if ratio >= 0.90 else (3 if ratio >= 0.85 else 2))

        return None

    def score_financing_risk(self, metrics: Dict) -> Optional[float]:
        scores = []

        if metrics.get('sales_volume_12m') is not None:
            sv = metrics['sales_volume_12m']
            score = 5 if sv > 20 else (4 if sv > 10 else (3 if sv > 5 else 2))
            scores.append(score)

        if metrics.get('cap_rate') is not None:
            cr = metrics['cap_rate']
            score = 5 if cr <= 5 else (4 if cr <= 6 else (3 if cr <= 7 else 2))
            scores.append(score)

        if not scores:
            return None

        return sum(scores) / len(scores)
