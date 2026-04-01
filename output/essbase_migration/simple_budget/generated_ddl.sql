CREATE TABLE IF NOT EXISTS Fact_Essbase_simple_budget (
    ProductKey STRING,
    TimeKey STRING,
    Value STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Time (
    TimeKey STRING,
    Time STRING,
    TimeParent STRING,
    TimeLevel STRING,
    Gen1_Time STRING,
    Gen2_Time STRING,
    TimeAlias STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Product (
    ProductKey STRING,
    Product STRING,
    ProductParent STRING,
    ProductLevel STRING,
    ProductAlias STRING
)
USING DELTA;
