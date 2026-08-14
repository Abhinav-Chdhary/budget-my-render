import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "analyze_accuracy.py"
spec = importlib.util.spec_from_file_location("accuracy_analysis", MODULE_PATH)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class AccuracyAnalysisTests(unittest.TestCase):
    def test_summary_groups_fixtures_and_recommends_a_conservative_range(self):
        records = [
            {"fixture": "glossy", "absolute_percentage_error": 5.0},
            {"fixture": "glossy", "absolute_percentage_error": 10.0},
            {"fixture": "volume", "absolute_percentage_error": 32.0},
        ]
        summary = analysis.summarize(records)
        proposed = analysis.recommendation(summary)
        self.assertEqual(summary["measurement_count"], 3)
        self.assertEqual(summary["by_fixture"]["glossy"]["count"], 2)
        self.assertEqual(summary["absolute_percentage_error"]["p90"], 27.6)
        self.assertEqual(proposed["proposed_non_adaptive_range_percent"], 30)


if __name__ == "__main__":
    unittest.main()
