CREATE TABLE IF NOT EXISTS Fact_Essbase_complex_planning (
    EntityKey STRING,
    ProductKey STRING,
    ChannelKey STRING,
    ScenarioKey STRING,
    CurrencyKey STRING,
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
    Gen3_Time STRING,
    TimeAlias STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Entity (
    EntityKey STRING,
    Entity STRING,
    EntityParent STRING,
    EntityLevel STRING,
    UDA_Interco BOOLEAN,
    UDA_Operating BOOLEAN,
    UDA_Reporting BOOLEAN,
    EntityAlias STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Product (
    ProductKey STRING,
    Product STRING,
    ProductParent STRING,
    ProductLevel STRING,
    UDA_HighMargin BOOLEAN,
    UDA_Recurring BOOLEAN,
    ProductAlias STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Channel (
    ChannelKey STRING,
    Channel STRING,
    ChannelParent STRING,
    ChannelLevel STRING,
    ChannelAlias STRING
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


CREATE TABLE IF NOT EXISTS Currency (
    CurrencyKey STRING,
    Currency STRING,
    CurrencyParent STRING,
    CurrencyLevel STRING,
    CurrencyAlias STRING
)
USING DELTA;
