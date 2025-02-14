# price_calculator.py

import json
import os

class PriceCalculator:
    def __init__(self):
        self.pricing_data = self._load_pricing_data()
        self._init_column_indices()
        
    def _load_pricing_data(self):
        """Load the App Store pricing matrix."""
        try:
            with open('appstorepricing.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load pricing data: {e}")
            return None

    def _init_column_indices(self):
        """Initialize column indices for customer prices."""
        self.column_indices = {}
        if not self.pricing_data:
            return
            
        header = self.pricing_data['header']
        for i, col in enumerate(header):
            if "(Customer Price)" in col:
                currency = col.split(" ")[0]
                self.column_indices[currency] = i
                
        # Add special handling for Euro zone countries
        euro_countries = [
            "Germany", "France", "Austria", "Belgium", "Spain", 
            "Italy", "Netherlands", "Ireland", "Finland"
        ]
        for country in euro_countries:
            if f"{country} (EUR)" in header:
                idx = header.index(f"{country} (EUR)")
                self.column_indices[f"{country}_EUR"] = idx

    def _find_tier_by_usd_price(self, usd_price):
        """Find the pricing tier that matches the USD price."""
        if not self.pricing_data:
            return None
            
        usd_index = self.column_indices.get("USD")
        if not usd_index:
            return None

        for row in self.pricing_data['rows']:
            if abs(float(row[usd_index]) - float(usd_price)) < 0.01:
                return row
        return None

    def get_prices_for_country(self, usd_price, country_code):
        """Get both USD and local currency prices."""
        if not country_code:
            return (usd_price, usd_price, 'USD')
            
        # Map country codes to currency columns
        country_mapping = {
            'US': ('USD', 'USD'),
            'GB': ('GBP', 'GBP'),
            'DE': ('Germany_EUR', 'EUR'),
            'FR': ('France_EUR', 'EUR'),
            'IT': ('Italy_EUR', 'EUR'),
            'ES': ('Spain_EUR', 'EUR'),
            'NL': ('Netherlands_EUR', 'EUR'),
            'IE': ('Ireland_EUR', 'EUR'),
            'FI': ('Finland_EUR', 'EUR'),
            'BE': ('Belgium_EUR', 'EUR'),
            'AT': ('Austria_EUR', 'EUR')
        }

        if country_code not in country_mapping:
            return (usd_price, usd_price, 'USD')

        column_key, currency = country_mapping[country_code]
        price_index = self.column_indices.get(column_key)
        
        if not price_index:
            print(f"[ERROR] Price column not found for currency: {currency}")
            return (usd_price, usd_price, currency)

        tier = self._find_tier_by_usd_price(usd_price)
        if not tier:
            return (usd_price, usd_price, currency)

        return (float(usd_price), float(tier[price_index]), currency)

    def calculate_savings(self, base_plan_usd, target_plan_usd, country_code):
        """Calculate savings when upgrading plans."""
        base_prices = self.get_prices_for_country(base_plan_usd, country_code)
        target_prices = self.get_prices_for_country(target_plan_usd, country_code)
        
        if base_plan_usd <= 5.0:  # weekly plan
            base_yearly = base_prices[1] * 52
            target_yearly = target_prices[1]
            usd_base_yearly = base_prices[0] * 52
        else:  # monthly plan
            base_yearly = base_prices[1] * 12
            target_yearly = target_prices[1]
            usd_base_yearly = base_prices[0] * 12
            
        return {
            'usd': {
                'original': base_prices[0],
                'target': target_prices[0],
                'original_yearly': usd_base_yearly,
                'target_yearly': target_prices[0],
                'savings': usd_base_yearly - target_prices[0]
            },
            'local': {
                'original': base_prices[1],
                'target': target_prices[1],
                'original_yearly': base_yearly,
                'target_yearly': target_yearly,
                'savings': base_yearly - target_yearly,
                'currency': base_prices[2]
            }
        }

    def format_price(self, amount, currency):
        """Format price with currency symbol."""
        currency_formats = {
            'USD': '${:.2f}',
            'EUR': '€{:.2f}',
            'GBP': '£{:.2f}'
        }
        format_str = currency_formats.get(currency, '${:.2f}')
        return format_str.format(float(amount))