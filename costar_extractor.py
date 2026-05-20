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
        # More flexible patterns to handle different formatting
        metrics['job_growth'] = self.extract_metric(
            r'(?:JOB\s+GROWTH|Job\s+Growth)[^\n]*?([0-9.]+)\s*%',
            None
        ) or self.extract_metric(r'Job\s+Growth[^\n]*?([0-9.]+)\s*%', None)

        metrics['unemployment_rate'] = self.extract_metric(
            r'(?:Unemployment|UNEMPLOYMENT)[\s\w]*?[Rr]ate[^\n]*?([0-9.]+)\s*%',
            None
        )

        metrics['population_growth'] = self.extract_metric(
            r'(?:POPULATION\s+GROWTH|Population\s+Growth)[^\n]*?([0-9.]+)\s*%',
            None
        ) or self.extract_metric(r'Population[\s\w]*?Growth[^\n]*?([0-9.]+)\s*%', None)

        metrics['household_growth'] = self.extract_metric(
            r'(?:HOUSEHOLD|Household)[\s\w]*?[Gg]rowth[^\n]*?([0-9.]+)\s*%',
            None
        )

        metrics['current_vacancy_rate'] = self.extract_metric(
            r'(?:VACANCY|STABILIZED|Vacancy|Current)[\s\w]*?(?:RATE|VACANCY|Rate)?[^\n]*?([0-9.]+)\s*%',
            None
        )

        metrics['net_absorption'] = self.extract_metric(
            r'(?:NET\s+)?ABSORPTION[^\n]*?([0-9,]+)\s+(?:units?|Units?)',
            None
        ) or self.extract_metric(r'Absorption[^\n]*?([0-9,]+)\s+(?:units?|Units?)', None)

        metrics['avg_asking_rent'] = self.extract_metric(
            r'(?:AVG|Avg|Average)[\s\.]?(?:ASKING\s+)?(?:RENT|Rent)[^\n]*?\$\s*([0-9,]+)',
            None
        ) or self.extract_metric(r'Asking[\s\w]*?Rent[^\n]*?\$\s*([0-9,]+)', None)

        metrics['avg_effective_rent'] = self.extract_metric(
            r'(?:EFFECTIVE|Effective)[\s\w]*?(?:RENT|Rent)[^\n]*?\$\s*([0-9,]+)',
            None
        )

        metrics['rent_per_sf'] = self.extract_metric(
            r'(?:RENT|Rent)[\s\w]*?(?:PER|per)[\s\w]*?(?:SF|SQ|SQFT)[^\n]*?\$\s*([0-9.]+)',
            None
        )

        # Supply Pressure - Search all pages
        metrics['under_construction_units'] = self.extract_metric(
            r'(?:UNDER|Under)[\s\w]*?(?:CONSTRUCTION|Construction)[^\n]*?([0-9,]+)\s+(?:units?|Units?)',
            None
        )

        metrics['deliveries_12_months'] = self.extract_metric(
            r'(?:DELIVERIES|Deliveries)[\s\w]*?(?:PAST|Past)?[\s\w]*?12[\s\w]*?(?:MONTHS?|Mo|months?)[^\n]*?([0-9,]+)\s+(?:units?|Units?)',
            None
        ) or self.extract_metric(r'Deliveries[^\n]*?([0-9,]+)\s+(?:units?|Units?)', None)

        # Sales/Financing - Search all pages
        metrics['sales_volume_12m'] = self.extract_metric(
            r'(?:SALES|Sales)[\s\w]*?12[\s\w]*?(?:MONTHS?|Mo|months?)[^\n]*?([0-9,]+)',
            None
        )

        metrics['cap_rate'] = self.extract_metric(
            r'(?:CAP|Cap)[\s\w]*?(?:RATE|Rate)[^\n]*?([0-9.]+)\s*%',
            None
        )

        metrics['price_per_unit'] = self.extract_metric(
            r'(?:PRICE|Price)[\s\w]*?(?:PER|per)[\s\w]*?(?:UNIT|Unit)[^\n]*?\$\s*([0-9,]+)',
            None
        )

        # Rent Comp Data - Search all pages
        metrics['num_rent_comps'] = self.extract_metric(
            r'(?:NO|No)\.?[\s\w]*?(?:RENT|Rent)[\s\w]*?(?:COMPS?|Comps?)[^\n]*?([0-9]+)',
            None,
            return_type='int'
        )

        metrics['avg_rent_comp_vacancy'] = self.extract_metric(
            r'(?:AVG|Avg)[\s\.]?(?:VACANCY|Vacancy)[^\n]*?([0-9.]+)\s*%',
            None
        )

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

    def get_pdf_text_sample(self, page_num: int = 1, lines: int = 50) -> str:
        """Return sample text from a specific page for debugging."""
        if page_num not in self.pages:
            return f"Page {page_num} not found. PDF has {len(self.pages)} pages."
        text = self.pages[page_num]
        lines_list = text.split('\n')[:lines]
        return '\n'.join(lines_list)

    def get_all_pages_summary(self) -> Dict:
        """Return summary of text content across all pages for debugging."""
        summary = {}
        for page_num, text in self.pages.items():
            summary[f'page_{page_num}'] = {
                'length': len(text),
                'line_count': len(text.split('\n')),
                'first_100_chars': text[:100] if text else ''
            }
        return summary
