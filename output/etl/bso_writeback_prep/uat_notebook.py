"""
UAT Validation Notebook — longview_budget_writeback
Phase A — Step 6: Parallel run comparison
Compares Essbase export vs Fabric Warehouse data
"""

from pyspark.sql import functions as F
import logging

logger = logging.getLogger(__name__)
results = []

# ── Config ─────────────────────────────────────────────────
ESSBASE_EXPORT = spark.conf.get("spark.essbase_export", "Files/essbase_export/longview_budget_writeback_baseline.csv")

# ── Load both datasets ────────────────────────────────────
essbase = spark.read.format("csv").option("header", "true").option("inferSchema", "true").load(ESSBASE_EXPORT)
fabric = spark.read.format("delta").load("Tables/Budget_Input")

# ── Test 1: Row count comparison ──────────────────────────
ess_count = essbase.count()
fab_count = fabric.count()
count_match = ess_count == fab_count
results.append({"test": "Row Count", "essbase": ess_count, "fabric": fab_count, "pass": count_match})
logger.info(f"Row count — Essbase: {ess_count}, Fabric: {fab_count}, Match: {count_match}")

# ── Test 2: Grand total comparison ────────────────────────
ess_total = essbase.agg(F.sum("Revenue")).collect()[0][0] or 0
fab_total = fabric.agg(F.sum("Revenue")).collect()[0][0] or 0
tolerance = 0.01
total_match = abs(float(ess_total) - float(fab_total)) <= tolerance
results.append({"test": "Grand Total", "essbase": float(ess_total), "fabric": float(fab_total), "pass": total_match})
logger.info(f"Grand total — Essbase: {ess_total}, Fabric: {fab_total}, Match: {total_match}")

# ── Test 3: Dimension member coverage ─────────────────────
ess_period = set(essbase.select("Period").distinct().rdd.flatMap(lambda x: x).collect())
fab_period = set(fabric.select("Period").distinct().rdd.flatMap(lambda x: x).collect())
missing_period = ess_period - fab_period
results.append({"test": "Dim Period", "essbase": len(ess_period), "fabric": len(fab_period), "pass": len(missing_period) == 0})
ess_entity = set(essbase.select("Entity").distinct().rdd.flatMap(lambda x: x).collect())
fab_entity = set(fabric.select("Entity").distinct().rdd.flatMap(lambda x: x).collect())
missing_entity = ess_entity - fab_entity
results.append({"test": "Dim Entity", "essbase": len(ess_entity), "fabric": len(fab_entity), "pass": len(missing_entity) == 0})
ess_product = set(essbase.select("Product").distinct().rdd.flatMap(lambda x: x).collect())
fab_product = set(fabric.select("Product").distinct().rdd.flatMap(lambda x: x).collect())
missing_product = ess_product - fab_product
results.append({"test": "Dim Product", "essbase": len(ess_product), "fabric": len(fab_product), "pass": len(missing_product) == 0})
ess_scenario = set(essbase.select("Scenario").distinct().rdd.flatMap(lambda x: x).collect())
fab_scenario = set(fabric.select("Scenario").distinct().rdd.flatMap(lambda x: x).collect())
missing_scenario = ess_scenario - fab_scenario
results.append({"test": "Dim Scenario", "essbase": len(ess_scenario), "fabric": len(fab_scenario), "pass": len(missing_scenario) == 0})
ess_currency = set(essbase.select("Currency").distinct().rdd.flatMap(lambda x: x).collect())
fab_currency = set(fabric.select("Currency").distinct().rdd.flatMap(lambda x: x).collect())
missing_currency = ess_currency - fab_currency
results.append({"test": "Dim Currency", "essbase": len(ess_currency), "fabric": len(fab_currency), "pass": len(missing_currency) == 0})

# ── Test 4: Per-scenario totals ───────────────────────────
ess_scenarios = essbase.groupBy("Scenario").agg(F.sum("Revenue").alias("Total")).collect()
fab_scenarios = fabric.groupBy("Scenario").agg(F.sum("Revenue").alias("Total")).collect()
ess_map = {r['Scenario']: float(r['Total'] or 0) for r in ess_scenarios}
fab_map = {r['Scenario']: float(r['Total'] or 0) for r in fab_scenarios}
for scen in ess_map:
    match = abs(ess_map[scen] - fab_map.get(scen, 0)) <= tolerance
    results.append({"test": f"Scenario {scen}", "essbase": ess_map[scen], "fabric": fab_map.get(scen, 0), "pass": match})

# ── Test 5: Writeback round-trip ──────────────────────────
# Insert a test row, read it back, delete it
from delta.tables import DeltaTable

test_vals = {
    "Period": "UAT_TEST",
    "Entity": "UAT_TEST",
    "Product": "UAT_TEST",
    "Scenario": "UAT_TEST",
    "Currency": "UAT_TEST",
    "Revenue": 999.99,
}
test_df = spark.createDataFrame([test_vals])
test_df.write.format("delta").mode("append").save("Tables/Budget_Input")

# Read back
readback = spark.read.format("delta").load("Tables/Budget_Input")
readback = readback.filter(F.col("Period") == "UAT_TEST")
roundtrip_ok = readback.count() == 1
results.append({"test": "Writeback Round-trip", "essbase": "N/A", "fabric": readback.count(), "pass": roundtrip_ok})

# Cleanup test row
dt = DeltaTable.forPath(spark, "Tables/Budget_Input")
dt.delete(F.col("Period") == "UAT_TEST")

# ── UAT Summary ───────────────────────────────────────────
passed = sum(1 for r in results if r['pass'])
total = len(results)

print(f"""
╔══════════════════════════════════════════════════════════╗
║  UAT Results — longview_budget_writeback                ║
╠══════════════════════════════════════════════════════════╣
║  Total tests:  {total:>4}                                   ║
║  Passed:       {passed:>4}                                   ║
║  Failed:       {total - passed:>4}                                   ║
╚══════════════════════════════════════════════════════════╝
""")

for r in results:
    status = "✅" if r["pass"] else "❌"
    print(f"  {status} {r['test']:<25} Essbase: {r['essbase']}  Fabric: {r['fabric']}")

assert passed == total, f"UAT FAILED: {total - passed} tests did not pass"