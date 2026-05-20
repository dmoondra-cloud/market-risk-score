"""
CoStar PDF Data Extractor
Extracts market metrics from CoStar reports
"""

import pdfplumber
import re
from typing import Dict, List, Optional


class CoStarExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pages = {}
        self._load_pdf()

    def _load_pdf(self):
        """Load all pages from PDF"""
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                self.pages[i] = page.extract_text()

    def extract_metric(self, pattern: str, page_range: List[int],
                      return_type: str = "float") -> Optional[float]:
        """
        Extract a numeric metric using regex pattern

        Args:
            pattern: Regex pattern to search for
            page_range: List of page numbers to search
            return_type: 'float', 'int', or 'string'

        Returns:
            Extracted value or None if not found
        """
        for page_num in page_range:
            if page_num not in self.pages:
                continue

            text = self.pages[page_num]
            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                value = match.group(1) if match.groups() else match.group(0)

                # Clean up the value
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

    def extract_all_metrics(self) -> Dict[str, any]:
        """Extract all available metrics from CoStar report"""

        metrics = {}

        # DEMAND STRENGTH METRICS
        metrics['job_growth'] = self.extract_metric(
            r'JOB GROWTH.*?([0-9.]+)%',
            [120, 121]
        )

        metrics['unemployment_rate'] = self.extract_metric(
            r'Unemployment.*?([0-9.]+)%',
            [120, 121, 122]
        )

        metrics['population_growth'] = self.extract_metric(
            r'POPULATION GROWTH.*?([0-9.]+)%',
            [122, 123]
        )

        metrics['household_growth'] = self.extract_metric(
            r'Household.*?([0-9.]+)%',
            [122, 123]
        )

        metrics['current_vacancy_rate'] = self.extract_metric(
            r'(?:OVERALL|STABILIZED)\s+VACANCY.*?([0-9.]+)%',
            [87, 88, 106, 107]
        )

        metrics['net_absorption'] = self.extract_metric(
            r'ABSORPTION.*?([0-9,]+)\s+units?',
            [87, 106]
        )

        metrics['avg_asking_rent'] = self.extract_metric(
            r'Avg\.\s+Rent.*?\$([0-9,]+)',
            [9, 10, 11]
        )

        metrics['avg_effective_rent'] = self.extract_metric(
            r'Effective Rent.*?\$([0-9,]+)',
            [9, 10, 11]
        )

        metrics['rent_per_sf'] = self.extract_metric(
            r'Rent\s+Per\s+SF.*?\$([0-9.]+)',
            [9, 10, 11]
        )

        # SUPPLY PRESSURE METRICS
        metrics['under_construction_units'] = self.extract_metric(
            r'Under\s+Construction.*?([0-9,]+)\s+units?',
            [56, 57, 58, 59, 60, 113, 114]
        )

        metrics['deliveries_12_months'] = self.extract_metric(
            r'Deliveries\s+(?:Past\s+)?12\s+Months.*?([0-9,]+)\s+units?',
            [61, 93]
        )

        # SALES/FINANCING METRICS
        metrics['sales_volume_12m'] = self.extract_metric(
            r'Sales.*?12\s+(?:Months?|Mo).*?([0-9,]+)',
            [72, 96, 117]
        )

        metrics['cap_rate'] = self.extract_metric(
            r'Cap\s+Rate.*?([0-9.]+)%',
            [75, 76]
        )

        metrics['price_per_unit'] = self.extract_metric(
            r'Price\s+Per\s+Unit.*?\$([0-9,]+)',
            [72, 75]
        )

        # RENT COMP DATA
        metrics['num_rent_comps'] = self.extract_metric(
            r'No\.\s+Rent\s+Comps\s*:?\s*([0-9]+)',
            [9, 10, 11],
            return_type='int'
        )

        metrics['avg_rent_comp_vacancy'] = self.extract_metric(
            r'Avg\.\s+Vacancy.*?([0-9.]+)%',
            [9, 10, 11]
        )

        return metrics

    def score_demand_strength(self, metrics: Dict) -> Optional[float]:
        """
        Score demand strength (1-5) based on available metrics

        Uses: job_growth, unemployment_rate, population_growth,
              household_growth, vacancy_rate, net_absorption
        """
        scores = []
        weights = []

        # Job Growth scoring (0.5 weight)
        if metrics.get('job_growth') is not None:
            jg = metrics['job_growth']
            if jg >= 2.0:
                scores.append(5)
            elif jg >= 1.0:
                scores.append(4)
            elif jg >= 0.0:
                scores.append(3)
            elif jg >= -1.0:
                scores.append(2)
            else:
                scores.append(1)
            weights.append(0.5)

        # Unemployment Rate scoring (0.3 weight)
        if metrics.get('unemployment_rate') is not None:
            ur = metrics['unemployment_rate']
            if ur <= 4.0:
                scores.append(5)
            elif ur < 5.0:
                scores.append(4)
            elif ur < 6.0:
                scores.append(3)
            elif ur < 7.0:
                scores.append(2)
            else:
                scores.append(1)
            weights.append(0.3)

        # Population Growth scoring (0.2 weight)
        if metrics.get('population_growth') is not None:
            pg = metrics['population_growth']
            if pg >= 1.5:
                scores.append(5)
            elif pg >= 0.8:
                scores.append(4)
            elif pg >= 0.0:
                scores.append(3)
            elif pg >= -0.5:
                scores.append(2)
            else:
                scores.append(1)
            weights.append(0.2)

        if not scores:
            return None

        # Weighted average
        return sum(s * w for s, w in zip(scores, weights)) / sum(weights)

    def score_supply_pressure(self, metrics: Dict) -> Optional[float]:
        """
        Score supply pressure (1-5) based on pipeline and deliveries
        """
        scores = []

        # Simple heuristic: more pipeline = higher pressure (lower score)
        if metrics.get('under_construction_units') is not None:
            uc = metrics['under_construction_units']
            if uc > 500:
                scores.append(2)  # High pressure
            elif uc > 200:
                scores.append(3)
            elif uc > 0:
                scores.append(4)
            else:
                scores.append(5)  # No pressure

        # Vacancy trend
        if metrics.get('current_vacancy_rate') is not None:
            vr = metrics['current_vacancy_rate']
            if vr > 10:
                scores.append(2)  # High vacancy = pressure
            elif vr > 7:
                scores.append(3)
            elif vr > 5:
                scores.append(4)
            else:
                scores.append(5)

        if not scores:
            return None

        return sum(scores) / len(scores)

    def score_competitive_positioning(self, metrics: Dict) -> Optional[float]:
        """
        Score competitive positioning (1-5) based on rent data
        """
        # Simple scoring: higher effective rents relative to asking = better positioning
        if metrics.get('avg_effective_rent') is not None and metrics.get('avg_asking_rent') is not None:
            eff_rent = metrics['avg_effective_rent']
            ask_rent = metrics['avg_asking_rent']

            if ask_rent > 0:
                ratio = eff_rent / ask_rent
                if ratio >= 0.95:
                    return 5  # Strong pricing
                elif ratio >= 0.90:
                    return 4
                elif ratio >= 0.85:
                    return 3
                else:
                    return 2  # High concessions

        return None

    def score_financing_risk(self, metrics: Dict) -> Optional[float]:
        """
        Score financing/liquidity risk (1-5)
        """
        scores = []

        # Sales volume proxy for liquidity
        if metrics.get('sales_volume_12m') is not None:
            sv = metrics['sales_volume_12m']
            if sv > 20:
                scores.append(5)  # Strong market
            elif sv > 10:
                scores.append(4)
            elif sv > 5:
                scores.append(3)
            else:
                scores.append(2)  # Limited liquidity

        # Cap rates (lower = more buyer interest/liquidity)
        if metrics.get('cap_rate') is not None:
            cr = metrics['cap_rate']
            if cr <= 5:
                scores.append(5)
            elif cr <= 6:
                scores.append(4)
            elif cr <= 7:
                scores.append(3)
            else:
                scores.append(2)

        if not scores:
            return None

        return sum(scores) / len(scores)
