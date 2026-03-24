CREATE TABLE IF NOT EXISTS DIM_DATE (
    DATE_KEY INT,
    FULL_DATE TIMESTAMP,
    YEAR INT,
    QUARTER STRING,
    MONTH_NUM INT,
    MONTH_NAME STRING,
    WEEK_NUM INT
)
USING DELTA;


CREATE TABLE IF NOT EXISTS DIM_PRODUCT (
    PRODUCT_KEY INT,
    PRODUCT_NAME STRING,
    CATEGORY STRING,
    SUBCATEGORY STRING,
    BRAND STRING,
    UNIT_COST STRING,
    UNIT_PRICE STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS DIM_CUSTOMER (
    CUSTOMER_KEY INT,
    CUSTOMER_NAME STRING,
    SEGMENT STRING,
    REGION STRING,
    COUNTRY STRING,
    STATE STRING,
    CITY STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS DIM_STORE (
    STORE_KEY INT,
    STORE_NAME STRING,
    STORE_TYPE STRING,
    REGION STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS DIM_CHANNEL (
    CHANNEL_KEY INT,
    CHANNEL_NAME STRING,
    CHANNEL_CLASS STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS FACT_SALES (
    SALES_KEY INT,
    DATE_KEY INT,
    PRODUCT_KEY INT,
    CUSTOMER_KEY INT,
    STORE_KEY INT,
    CHANNEL_KEY INT,
    QUANTITY INT,
    UNIT_PRICE STRING,
    DISCOUNT_PCT STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS FACT_RETURNS (
    RETURN_KEY INT,
    SALES_KEY INT,
    RETURN_DATE_KEY INT,
    RETURN_QUANTITY INT,
    REASON_CODE STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS FACT_BUDGET (
    BUDGET_KEY INT,
    DATE_KEY INT,
    PRODUCT_KEY INT,
    STORE_KEY INT,
    BUDGET_AMOUNT STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS EMPLOYEES (
    EMP_ID INT,
    FIRST_NAME STRING,
    LAST_NAME STRING,
    DEPT_ID INT,
    HIRE_DATE TIMESTAMP,
    SALARY STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS DEPARTMENTS (
    DEPT_ID INT,
    DEPT_NAME STRING,
    LOCATION_ID INT
)
USING DELTA;


CREATE TABLE IF NOT EXISTS LOCATIONS (
    LOCATION_ID INT,
    CITY STRING,
    COUNTRY STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS PAYROLL (
    PAY_ID INT,
    EMP_ID INT,
    PAY_DATE TIMESTAMP,
    GROSS_PAY STRING,
    DEDUCTIONS STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS CUSTOMERS (
    CUST_ID INT,
    CUST_NAME STRING,
    EMAIL STRING,
    REGION STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS ORDERS (
    ORDER_ID INT,
    CUST_ID INT,
    ORDER_DATE TIMESTAMP,
    AMOUNT STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS unnamed_load (
    Script___Complex_ETL_Pipeline____Complexity__Complex____Tables__10_ STRING,
    SQL__3 STRING,
    Variables__8_____Features__Multiple_connections STRING,
    NOCONCATENATE STRING,
    calculated_fields STRING,
    _____________conditional_logic STRING,
    nested_expressions STRING,
    multiple_file_formats________________________________________________________________________Connections_____CONNECT_TO__oracle_enterprise_dw___CONNECT_TO__azure_sql_staging___________Variables_____SET_vToday___Today____LET_vThisYear___Year___vToday____LET_vLastYear_____vThisYear____1__SET_vCurrencyRate___1_08__SET_vRevenueThreshold___5000__LET_vQuarter____Q____Ceil_Month___vToday_____3___SET_vDateFormat____YYYY_MM_DD___LET_vDataPath____lib___DataFiles____LET_vArchivePath____lib___Archive___vThisYear_____________Calendar__inline______Calendar__LOAD_____DateValue STRING,
    Year STRING,
    MonthNum STRING,
    MonthName STRING,
    Quarter STRING,
    WeekNum STRING,
    DayOfWeek STRING,
    If_Weekday_DateValue_____5 STRING,
    _Weekend_ STRING,
    DayType STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS RegionMapping (
    RegionCode STRING,
    RegionName STRING,
    CurrencyCode STRING,
    TimeZone STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Stores (
    store_id STRING,
    store_name STRING,
    store_type STRING,
    region_code STRING,
    country STRING,
    city STRING,
    open_date STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Channels (
    channel_code STRING,
    channel_name STRING,
    channel_class STRING,
    commission_pct STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS OrderEnriched (
    order_id STRING,
    customer_id STRING,
    product_id STRING,
    store_id STRING,
    channel_code STRING,
    order_date STRING,
    ship_date STRING,
    quantity STRING,
    sold_price STRING,
    discount_pct STRING,
    tax_amount STRING,
    freight_cost STRING,
    GrossAmount STRING,
    NetRevenue STRING,
    TotalAmount STRING,
    If_discount_pct___0 STRING,
    _Discounted_ STRING,
    PricingFlag STRING,
    If_ship_date___order_date___7 STRING,
    _Delayed_ STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS CustomerSummary (
    customer_id STRING,
    TotalOrders STRING,
    CustomerRevenue STRING,
    FirstOrderDate STRING,
    LastOrderDate STRING,
    AvgOrderRevenue STRING,
    If_Count_DISTINCT_order_id____5 STRING,
    _Loyal_ STRING,
    If_Count_DISTINCT_order_id____1 STRING,
    _Repeat_ STRING,
    CustomerTier STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS ProductPerformance (
    product_id STRING,
    TotalUnitsSold STRING,
    ProductRevenue STRING,
    ProductOrders STRING,
    AvgSellingPrice STRING,
    If_Sum_NetRevenue______vRevenueThreshold_ STRING,
    _High_ STRING,
    If_Sum_NetRevenue____1000 STRING,
    _Medium_ STRING,
    PerformanceTier STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Returns (
    return_id STRING,
    order_id STRING,
    return_date STRING,
    return_quantity STRING,
    reason_code STRING,
    refund_amount STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Budget (
    budget_month STRING,
    region_code STRING,
    category STRING,
    budget_amount STRING,
    budget_units STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id STRING,
    customer_name STRING,
    email STRING,
    segment STRING,
    region_code STRING,
    country STRING,
    city STRING,
    signup_date STRING,
    lifetime_value STRING,
    credit_limit STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS dim_product (
    product_id STRING,
    product_name STRING,
    category STRING,
    subcategory STRING,
    brand STRING,
    unit_cost STRING,
    unit_price STRING,
    weight_kg STRING,
    launch_date STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS fact_orders (
    order_id STRING,
    customer_id STRING,
    product_id STRING,
    store_id STRING,
    channel_code STRING,
    order_date STRING,
    ship_date STRING,
    quantity STRING,
    unit_price_AS_sold_price STRING,
    discount_pct STRING,
    tax_amount STRING,
    freight_cost STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS unnamed_load (
    Script___Medium_ETL____Complexity__Medium____Tables__5 STRING,
    SQL__2 STRING,
    Variables__4____Features_ STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Regions (
    RegionID STRING,
    RegionName STRING,
    Manager STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS OrderSummary (
    customer_id STRING,
    OrderCount STRING,
    TotalRevenue STRING,
    AvgOrderValue STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Products (
    product_id STRING,
    product_name STRING,
    category STRING,
    subcategory STRING,
    unit_cost STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id STRING,
    customer_name STRING,
    email STRING,
    region_id STRING,
    segment STRING,
    signup_date STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS fact_orders (
    order_id STRING,
    customer_id STRING,
    order_date STRING,
    product_id STRING,
    quantity STRING,
    unit_price STRING,
    discount_pct STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS unnamed_load (
    Script___Simple_Load____Complexity__Simple____Tables__2 STRING,
    SQL__1 STRING,
    Variables__1____Features__Basic_SQL_SELECT STRING,
    QVD_file_load____________________________________________________________________Connection_CONNECT_TO__sales_db_connection_______Variables_SET_vToday___Today________Load_customers STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS unnamed_load (
    orders STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS Orders (
    order_id STRING,
    customer_id STRING,
    order_date STRING,
    product_name STRING,
    quantity STRING,
    amount STRING
)
USING DELTA;


CREATE TABLE IF NOT EXISTS customers (
    customer_id STRING,
    customer_name STRING,
    email STRING,
    region STRING,
    segment STRING
)
USING DELTA;
