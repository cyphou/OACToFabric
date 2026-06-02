"""
Fabric Notebook: Initial Data Migration — longview_budget_writeback/longview_budget_writeback
Source: Essbase flat export (CSV/TSV)
Target: Fabric Lakehouse (Delta) + Warehouse
Phase A — Step 3: Data Migration
"""

from pyspark.sql import functions as F
from pyspark.sql.types import (StructType, StructField, StringType,
                                DecimalType, IntegerType)
import logging

logger = logging.getLogger(__name__)

# ── Parameters ────────────────────────────────────────────────
APP_NAME = "longview_budget_writeback"
DB_NAME = "longview_budget_writeback"
EXPORT_PATH = spark.conf.get("spark.export_path", "Files/essbase_export/longview_budget_writeback_longview_budget_writeback.csv")

# ── Step 1: Read Essbase flat export ─────────────────────────
# Essbase exports via MaxL or flat file extract:
#   EXPORT DATABASE "App"."Db" ALL DATA TO DATA_FILE "export.csv"
#   USING COLUMN_FORMAT DELIMITER ','

schema = StructType([
    StructField("Period", StringType(), False),
    StructField("Entity", StringType(), False),
    StructField("Product", StringType(), False),
    StructField("Scenario", StringType(), False),
    StructField("Currency", StringType(), False),
    StructField("Revenue", DecimalType(18, 2), True),
])

raw = (
    spark.read.format("csv")
    .option("header", "true")
    .schema(schema)
    .load(EXPORT_PATH)
)
logger.info(f"Read {raw.count()} rows from Essbase export")

# ── Step 2: Data quality checks ──────────────────────────────
null_count = raw.filter(
    F.col("Period").isNull() | F.col("Entity").isNull() | F.col("Product").isNull() | F.col("Scenario").isNull() | F.col("Currency").isNull()
).count()
logger.info(f"Rows with null dimension keys: {null_count}")
assert null_count == 0, f"Found {null_count} rows with null dimensions"

# ── Step 3: Write fact data to Delta tables ──────────────────
# Budget_Input — primary writeback target
(
    raw.write.format("delta")
    .mode("overwrite")
    .option("mergeSchema", "true")
    .save("Tables/Budget_Input")
)
logger.info(f"Wrote {raw.count()} rows to Budget_Input")

# ── Step 4: Extract and write dimension tables ───────────────
# Dim_Period
dim_period = (
    raw.select("Period").distinct()
    .withColumn("ParentMember", F.lit(None).cast("string"))
    .withColumn("Level", F.lit(0))
    .withColumn("IsLeaf", F.lit(True))
)
(
    dim_period.write.format("delta")
    .mode("overwrite")
    .save("Tables/Dim_Period")
)
logger.info(f"Dim_Period: {dim_period.count()} members")

# Dim_Entity
dim_entity = (
    raw.select("Entity").distinct()
    .withColumn("ParentMember", F.lit(None).cast("string"))
    .withColumn("Level", F.lit(0))
    .withColumn("IsLeaf", F.lit(True))
)
(
    dim_entity.write.format("delta")
    .mode("overwrite")
    .save("Tables/Dim_Entity")
)
logger.info(f"Dim_Entity: {dim_entity.count()} members")

# Dim_Product
dim_product = (
    raw.select("Product").distinct()
    .withColumn("ParentMember", F.lit(None).cast("string"))
    .withColumn("Level", F.lit(0))
    .withColumn("IsLeaf", F.lit(True))
)
(
    dim_product.write.format("delta")
    .mode("overwrite")
    .save("Tables/Dim_Product")
)
logger.info(f"Dim_Product: {dim_product.count()} members")

# Dim_Scenario
dim_scenario = (
    raw.select("Scenario").distinct()
    .withColumn("ParentMember", F.lit(None).cast("string"))
    .withColumn("Level", F.lit(0))
    .withColumn("IsLeaf", F.lit(True))
)
(
    dim_scenario.write.format("delta")
    .mode("overwrite")
    .save("Tables/Dim_Scenario")
)
logger.info(f"Dim_Scenario: {dim_scenario.count()} members")

# Dim_Currency
dim_currency = (
    raw.select("Currency").distinct()
    .withColumn("ParentMember", F.lit(None).cast("string"))
    .withColumn("Level", F.lit(0))
    .withColumn("IsLeaf", F.lit(True))
)
(
    dim_currency.write.format("delta")
    .mode("overwrite")
    .save("Tables/Dim_Currency")
)
logger.info(f"Dim_Currency: {dim_currency.count()} members")

# ── Step 5: Validation ───────────────────────────────────────
loaded = spark.read.format("delta").load("Tables/Budget_Input").count()
assert loaded == raw.count(), f"Row count mismatch: {loaded} vs {raw.count()}"
logger.info(f"✅ Data migration complete: {loaded} rows in Budget_Input")

# Summary
print(f"""
╔══════════════════════════════════════════════╗
║  Data Migration Complete — longview_budget_writeback ║
╠══════════════════════════════════════════════╣
║  Fact rows:      {loaded:>10,}              ║
║  Dim_Period      : {dim_period.count():>10,}              ║
║  Dim_Entity      : {dim_entity.count():>10,}              ║
║  Dim_Product     : {dim_product.count():>10,}              ║
║  Dim_Scenario    : {dim_scenario.count():>10,}              ║
║  Dim_Currency    : {dim_currency.count():>10,}              ║
╚══════════════════════════════════════════════╝
""")