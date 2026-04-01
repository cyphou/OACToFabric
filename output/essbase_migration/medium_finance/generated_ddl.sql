CREATE TABLE IF NOT EXISTS Fact_Essbase_medium_finance (
    EntityKey STRING,
    ProductKey STRING,
    ScenarioKey STRING,
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


CREATE TABLE IF NOT EXISTS Entity (
    EntityKey STRING,
    Entity STRING,
    EntityParent STRING,
    EntityLevel STRING,
    UDA_Reporting BOOLEAN,
    EntityAlias STRING
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


CREATE TABLE IF NOT EXISTS Scenario (
    ScenarioKey STRING,
    Scenario STRING,
    ScenarioParent STRING,
    ScenarioLevel STRING,
    ScenarioAlias STRING
)
USING DELTA;
