#!/usr/bin/env python3
"""Unit tests for the Maritime Chokepoints transform. Stdlib only.

Run:  python3 -m unittest discover -s dashboards/maritime/tests
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import transform  # noqa: E402


def load(name, base=HERE):
    with open(os.path.join(base, name)) as f:
        return json.load(f)


META = load("chokepoints_meta.json", base=ROOT)
FIXTURE = load("fixture_arcgis.json")


class ParseFeatures(unittest.TestCase):
    def test_extracts_and_normalises_fields(self):
        recs = transform.parse_features(FIXTURE)
        # 8 Suez + 7 Good Hope + 7 Panama
        self.assertEqual(len(recs), 22)
        suez = [r for r in recs if r["name"] == "Suez Canal"]
        self.assertEqual(len(suez), 8)
        # import+export folded into trade
        self.assertEqual(suez[0]["trade"], 150.0)

    def test_alternate_transit_field(self):
        recs = transform.parse_features(FIXTURE)
        panama = [r for r in recs if r["name"] == "Panama Canal"][0]
        self.assertEqual(panama["transit"], 33.0)   # came from 'portcalls'
        self.assertIsNone(panama["trade"])

    def test_malformed_never_raises(self):
        self.assertEqual(transform.parse_features({}), [])
        self.assertEqual(transform.parse_features(None), [])
        self.assertEqual(transform.parse_features({"features": [{"bad": 1}, 7]}), [])


class FieldVariants(unittest.TestCase):
    """The live PortWatch chokepoints layer uses n_total for the transit count."""

    def _one(self, attrs):
        return transform.parse_features({"features": [{"attributes": attrs}]})[0]

    def test_n_total_is_read(self):
        r = self._one({"portname": "Suez Canal", "date": 1, "n_total": 40})
        self.assertEqual(r["transit"], 40.0)

    def test_n_total_preferred_over_types(self):
        r = self._one({"portname": "Suez Canal", "date": 1, "n_total": 40, "n_container": 10})
        self.assertEqual(r["transit"], 40.0)

    def test_per_type_sum_fallback(self):
        r = self._one({"portname": "Suez Canal", "date": 1,
                       "n_container": 10, "n_tanker": 5, "n_dry_bulk": 3})
        self.assertEqual(r["transit"], 18.0)

    def test_capacity_used_as_trade(self):
        r = self._one({"portname": "Suez Canal", "date": 1, "n_total": 40, "capacity": 1234})
        self.assertEqual(r["trade"], 1234.0)


class Build(unittest.TestCase):
    def setUp(self):
        self.recs = transform.parse_features(FIXTURE)
        self.out = transform.build(self.recs, META, source="test")
        self.by = {c["id"]: c for c in self.out["chokepoints"]}

    def test_suez_constrained(self):
        s = self.by["suez"]
        self.assertEqual(s["transit_7d_avg"], 22.0)   # 8th older record excluded
        self.assertEqual(s["baseline"], 55)
        self.assertEqual(s["deviation_pct"], -60)
        self.assertEqual(s["status"], "constrained")
        self.assertEqual(s["trade_musd_7d_avg"], 150.0)

    def test_goodhope_elevated(self):
        g = self.by["goodhope"]
        self.assertEqual(g["transit_7d_avg"], 80.0)
        self.assertEqual(g["deviation_pct"], 45)
        self.assertEqual(g["status"], "elevated")

    def test_panama_normal(self):
        p = self.by["panama"]
        self.assertEqual(p["deviation_pct"], 0)
        self.assertEqual(p["status"], "normal")

    def test_untouched_chokepoints_are_no_data(self):
        h = self.by["hormuz"]
        self.assertIsNone(h["transit_7d_avg"])
        self.assertIsNone(h["deviation_pct"])
        self.assertEqual(h["status"], "no-data")

    def test_summary(self):
        s = self.out["summary"]
        self.assertEqual(s["tracked"], len(META["chokepoints"]))
        self.assertEqual(s["constrained_count"], 1)
        self.assertEqual(s["transits_below_baseline_per_day"], 33)  # max(0,55-22)
        self.assertEqual(s["most_constrained"], "suez")

    def test_most_constrained_first(self):
        self.assertEqual(self.out["chokepoints"][0]["id"], "suez")

    def test_schema_shape(self):
        for c in self.out["chokepoints"]:
            self.assertEqual(set(c) >= {"id", "name", "lat", "lon", "status",
                                        "deviation_pct", "baseline", "transit_7d_avg"}, True)
        self.assertIn(self.out["source"], ("test", "imf-portwatch", "sample"))


class Degradation(unittest.TestCase):
    def test_empty_records_valid_json(self):
        out = transform.build([], META, source="sample")
        self.assertEqual(out["summary"]["constrained_count"], 0)
        self.assertEqual(out["summary"]["transits_below_baseline_per_day"], 0)
        self.assertIsNone(out["summary"]["most_constrained"])
        self.assertEqual(len(out["chokepoints"]), len(META["chokepoints"]))
        self.assertTrue(all(c["status"] == "no-data" for c in out["chokepoints"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
