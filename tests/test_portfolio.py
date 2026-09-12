import unittest

from app.portfolio import PortfolioEntry, calculate_portfolio_totals


class PortfolioTotalsTests(unittest.TestCase):
    def test_mixed_currencies_are_converted_before_sum(self):
        rates = {("USD", "CNY"): 7.0, ("HKD", "CNY"): 0.9}
        entries = [
            PortfolioEntry(1000, "USD", 1200, "USD"),
            PortfolioEntry(10000, "HKD", 11000, "HKD"),
            PortfolioEntry(5000, "CNY", 5500, "CNY"),
        ]

        totals = calculate_portfolio_totals(entries, "CNY", lambda source, target: rates.get((source, target)))

        self.assertTrue(totals.complete)
        self.assertAlmostEqual(totals.total_cost, 21000)
        self.assertAlmostEqual(totals.total_value, 23800)
        self.assertAlmostEqual(totals.total_pnl, 2800)
        self.assertAlmostEqual(totals.total_return_percent, 2800 / 21000 * 100)

    def test_missing_quote_or_rate_disables_summary(self):
        entries = [PortfolioEntry(1000, "USD", None, "USD")]
        totals = calculate_portfolio_totals(entries, "CNY", lambda *_: None)
        self.assertFalse(totals.complete)
        self.assertIsNone(totals.total_value)
        self.assertIn("USD", totals.missing_currencies)
        self.assertIn("USD行情", totals.missing_currencies)
        self.assertIsNone(totals.total_return_percent)

    def test_zero_cost_has_no_return_percent(self):
        totals = calculate_portfolio_totals(
            [PortfolioEntry(0, "USD", 100, "USD")],
            "USD",
            lambda *_: None,
        )
        self.assertTrue(totals.complete)
        self.assertIsNone(totals.total_return_percent)

    def test_summary_can_switch_to_usd(self):
        rates = {("CNY", "USD"): 0.14, ("HKD", "USD"): 0.128}
        entries = [
            PortfolioEntry(7000, "CNY", 7700, "CNY"),
            PortfolioEntry(10000, "HKD", 11000, "HKD"),
            PortfolioEntry(1000, "USD", 1200, "USD"),
        ]
        totals = calculate_portfolio_totals(entries, "USD", lambda source, target: rates.get((source, target)))
        self.assertTrue(totals.complete)
        self.assertAlmostEqual(totals.total_cost, 3260)
        self.assertAlmostEqual(totals.total_value, 3686)


if __name__ == "__main__":
    unittest.main()
