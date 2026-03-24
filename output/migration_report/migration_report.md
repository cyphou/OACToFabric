# Migration Report

> **Generated:** 2026-03-24 14:29:36 UTC  
> **Total assets discovered:** 145  
> **Elapsed time:** 0.2s  
> **Output directory:** `output\migration_report`

---

## 1. Discovery Summary

### Assets by Source Platform

| Source | Assets | Types |
|--------|--------|-------|
| **cognos** | 18 | analysis, dataModel, prompt |
| **essbase** | 15 | logicalTable |
| **qlik** | 36 | filter, physicalTable |
| **rpd** | 53 | initBlock, logicalTable, physicalTable, presentationTable, securityRole, subjectArea |
| **tableau** | 23 | analysis, dashboard, logicalTable, prompt |

### Assets by Type

| Asset Type | Count | Sources |
|------------|-------|---------|
| analysis | 15 | cognos, tableau |
| dashboard | 3 | tableau |
| dataModel | 7 | cognos |
| filter | 14 | qlik |
| initBlock | 3 | rpd |
| logicalTable | 30 | essbase, rpd, tableau |
| physicalTable | 36 | qlik, rpd |
| presentationTable | 16 | rpd |
| prompt | 12 | cognos, tableau |
| securityRole | 3 | rpd |
| subjectArea | 6 | rpd |

### Full Inventory

<details>
<summary>Click to expand — all discovered assets</summary>

| # | Name | Type | Source | Path |
|---|------|------|--------|------|
| 1 | RevenueTrend | dataModel | cognos | `/cognos/Executive Performance Dashboard/RevenueTrend` |
| 2 | RegionBreakdown | dataModel | cognos | `/cognos/Executive Performance Dashboard/RegionBreakdown` |
| 3 | ProductPerformance | dataModel | cognos | `/cognos/Executive Performance Dashboard/ProductPerformance` |
| 4 | CustomerSegments | dataModel | cognos | `/cognos/Executive Performance Dashboard/CustomerSegments` |
| 5 | Executive Performance Dashboard — Executive Summary | analysis | cognos | `/cognos/Executive Performance Dashboard/Executive Summary` |
| 6 | Executive Performance Dashboard — Product Analysis | analysis | cognos | `/cognos/Executive Performance Dashboard/Product Analysis` |
| 7 | Executive Performance Dashboard — Customer Insights | analysis | cognos | `/cognos/Executive Performance Dashboard/Customer Insights` |
| 8 | Fiscal Year | prompt | cognos | `/cognos/Executive Performance Dashboard/prompts/pYear` |
| 9 | Region | prompt | cognos | `/cognos/Executive Performance Dashboard/prompts/pRegion` |
| 10 | Customer Segment | prompt | cognos | `/cognos/Executive Performance Dashboard/prompts/pSegment` |
| 11 | As-Of Date | prompt | cognos | `/cognos/Executive Performance Dashboard/prompts/pAsOfDate` |
| 12 | RegionSummary | dataModel | cognos | `/cognos/Regional Sales Analysis/RegionSummary` |
| 13 | TopCustomers | dataModel | cognos | `/cognos/Regional Sales Analysis/TopCustomers` |
| 14 | Regional Sales Analysis — Regional Analysis | analysis | cognos | `/cognos/Regional Sales Analysis/Regional Analysis` |
| 15 | Select Region | prompt | cognos | `/cognos/Regional Sales Analysis/prompts/pRegion` |
| 16 | Start Date | prompt | cognos | `/cognos/Regional Sales Analysis/prompts/pStartDate` |
| 17 | OrderQuery | dataModel | cognos | `/cognos/Customer Order List/OrderQuery` |
| 18 | Customer Order List — Order List | analysis | cognos | `/cognos/Customer Order List/Order List` |
| 19 | Time | logicalTable | essbase | `/essbase/complex_planning/Time` |
| 20 | Accounts | logicalTable | essbase | `/essbase/complex_planning/Accounts` |
| 21 | Entity | logicalTable | essbase | `/essbase/complex_planning/Entity` |
| 22 | Product | logicalTable | essbase | `/essbase/complex_planning/Product` |
| 23 | Channel | logicalTable | essbase | `/essbase/complex_planning/Channel` |
| 24 | Scenario | logicalTable | essbase | `/essbase/complex_planning/Scenario` |
| 25 | Currency | logicalTable | essbase | `/essbase/complex_planning/Currency` |
| 26 | Time | logicalTable | essbase | `/essbase/medium_finance/Time` |
| 27 | Accounts | logicalTable | essbase | `/essbase/medium_finance/Accounts` |
| 28 | Entity | logicalTable | essbase | `/essbase/medium_finance/Entity` |
| 29 | Product | logicalTable | essbase | `/essbase/medium_finance/Product` |
| 30 | Scenario | logicalTable | essbase | `/essbase/medium_finance/Scenario` |
| 31 | Time | logicalTable | essbase | `/essbase/simple_budget/Time` |
| 32 | Accounts | logicalTable | essbase | `/essbase/simple_budget/Accounts` |
| 33 | Product | logicalTable | essbase | `/essbase/simple_budget/Product` |
| 34 | DIM_DATE | physicalTable | rpd | `/physical/DIM_DATE` |
| 35 | DIM_PRODUCT | physicalTable | rpd | `/physical/DIM_PRODUCT` |
| 36 | DIM_CUSTOMER | physicalTable | rpd | `/physical/DIM_CUSTOMER` |
| 37 | DIM_STORE | physicalTable | rpd | `/physical/DIM_STORE` |
| 38 | DIM_CHANNEL | physicalTable | rpd | `/physical/DIM_CHANNEL` |
| 39 | FACT_SALES | physicalTable | rpd | `/physical/FACT_SALES` |
| 40 | FACT_RETURNS | physicalTable | rpd | `/physical/FACT_RETURNS` |
| 41 | FACT_BUDGET | physicalTable | rpd | `/physical/FACT_BUDGET` |
| 42 | Time | logicalTable | rpd | `/logical/Time` |
| 43 | Product | logicalTable | rpd | `/logical/Product` |
| 44 | Customer | logicalTable | rpd | `/logical/Customer` |
| 45 | Sales | logicalTable | rpd | `/logical/Sales` |
| 46 | Returns | logicalTable | rpd | `/logical/Returns` |
| 47 | Budget | logicalTable | rpd | `/logical/Budget` |
| 48 | Executive Sales | subjectArea | rpd | `/presentation/Executive Sales` |
| 49 | Product Performance | subjectArea | rpd | `/presentation/Product Performance` |
| 50 | Returns Analysis | subjectArea | rpd | `/presentation/Returns Analysis` |
| 51 | Time | presentationTable | rpd | `/presentation/Time` |
| 52 | Product | presentationTable | rpd | `/presentation/Product` |
| 53 | Customer | presentationTable | rpd | `/presentation/Customer` |
| 54 | Measures | presentationTable | rpd | `/presentation/Measures` |
| 55 | Product | presentationTable | rpd | `/presentation/Product` |
| 56 | Sales | presentationTable | rpd | `/presentation/Sales` |
| 57 | Time | presentationTable | rpd | `/presentation/Time` |
| 58 | Product | presentationTable | rpd | `/presentation/Product` |
| 59 | Returns | presentationTable | rpd | `/presentation/Returns` |
| 60 | Regional_Manager | securityRole | rpd | `/security/roles/Regional_Manager` |
| 61 | Analyst | securityRole | rpd | `/security/roles/Analyst` |
| 62 | RLS_Region | initBlock | rpd | `/security/initblocks/RLS_Region` |
| 63 | RLS_Segment | initBlock | rpd | `/security/initblocks/RLS_Segment` |
| 64 | EMPLOYEES | physicalTable | rpd | `/physical/EMPLOYEES` |
| 65 | DEPARTMENTS | physicalTable | rpd | `/physical/DEPARTMENTS` |
| 66 | LOCATIONS | physicalTable | rpd | `/physical/LOCATIONS` |
| 67 | PAYROLL | physicalTable | rpd | `/physical/PAYROLL` |
| 68 | DIM_Employee | logicalTable | rpd | `/logical/DIM_Employee` |
| 69 | DIM_Location | logicalTable | rpd | `/logical/DIM_Location` |
| 70 | FACT_Payroll | logicalTable | rpd | `/logical/FACT_Payroll` |
| 71 | HR Analytics | subjectArea | rpd | `/presentation/HR Analytics` |
| 72 | Compensation Review | subjectArea | rpd | `/presentation/Compensation Review` |
| 73 | Employees | presentationTable | rpd | `/presentation/Employees` |
| 74 | Locations | presentationTable | rpd | `/presentation/Locations` |
| 75 | Payroll | presentationTable | rpd | `/presentation/Payroll` |
| 76 | Employees | presentationTable | rpd | `/presentation/Employees` |
| 77 | Compensation | presentationTable | rpd | `/presentation/Compensation` |
| 78 | HR_Manager | securityRole | rpd | `/security/roles/HR_Manager` |
| 79 | RLS_Department | initBlock | rpd | `/security/initblocks/RLS_Department` |
| 80 | CUSTOMERS | physicalTable | rpd | `/physical/CUSTOMERS` |
| 81 | ORDERS | physicalTable | rpd | `/physical/ORDERS` |
| 82 | DIM_Customer | logicalTable | rpd | `/logical/DIM_Customer` |
| 83 | FACT_Orders | logicalTable | rpd | `/logical/FACT_Orders` |
| 84 | Sales Analysis | subjectArea | rpd | `/presentation/Sales Analysis` |
| 85 | Customer | presentationTable | rpd | `/presentation/Customer` |
| 86 | Orders | presentationTable | rpd | `/presentation/Orders` |
| 87 | vToday | filter | qlik | `/qlik/complex_pipeline/variables/vToday` |
| 88 | vThisYear | filter | qlik | `/qlik/complex_pipeline/variables/vThisYear` |
| 89 | vLastYear | filter | qlik | `/qlik/complex_pipeline/variables/vLastYear` |
| 90 | vCurrencyRate | filter | qlik | `/qlik/complex_pipeline/variables/vCurrencyRate` |
| 91 | vRevenueThreshold | filter | qlik | `/qlik/complex_pipeline/variables/vRevenueThreshold` |
| 92 | vQuarter | filter | qlik | `/qlik/complex_pipeline/variables/vQuarter` |
| 93 | vDateFormat | filter | qlik | `/qlik/complex_pipeline/variables/vDateFormat` |
| 94 | vDataPath | filter | qlik | `/qlik/complex_pipeline/variables/vDataPath` |
| 95 | vArchivePath | filter | qlik | `/qlik/complex_pipeline/variables/vArchivePath` |
| 96 | unnamed_load | physicalTable | qlik | `/qlik/complex_pipeline/unnamed_load` |
| 97 | RegionMapping | physicalTable | qlik | `/qlik/complex_pipeline/RegionMapping` |
| 98 | Stores | physicalTable | qlik | `/qlik/complex_pipeline/Stores` |
| 99 | Channels | physicalTable | qlik | `/qlik/complex_pipeline/Channels` |
| 100 | OrderEnriched | physicalTable | qlik | `/qlik/complex_pipeline/OrderEnriched` |
| 101 | CustomerSummary | physicalTable | qlik | `/qlik/complex_pipeline/CustomerSummary` |
| 102 | ProductPerformance | physicalTable | qlik | `/qlik/complex_pipeline/ProductPerformance` |
| 103 | Returns | physicalTable | qlik | `/qlik/complex_pipeline/Returns` |
| 104 | Budget | physicalTable | qlik | `/qlik/complex_pipeline/Budget` |
| 105 | dim_customer | physicalTable | qlik | `/qlik/complex_pipeline/dim_customer` |
| 106 | dim_product | physicalTable | qlik | `/qlik/complex_pipeline/dim_product` |
| 107 | fact_orders | physicalTable | qlik | `/qlik/complex_pipeline/fact_orders` |
| 108 | vToday | filter | qlik | `/qlik/medium_etl/variables/vToday` |
| 109 | vThisYear | filter | qlik | `/qlik/medium_etl/variables/vThisYear` |
| 110 | vThreshold | filter | qlik | `/qlik/medium_etl/variables/vThreshold` |
| 111 | vLastMonth | filter | qlik | `/qlik/medium_etl/variables/vLastMonth` |
| 112 | unnamed_load | physicalTable | qlik | `/qlik/medium_etl/unnamed_load` |
| 113 | Regions | physicalTable | qlik | `/qlik/medium_etl/Regions` |
| 114 | OrderSummary | physicalTable | qlik | `/qlik/medium_etl/OrderSummary` |
| 115 | Products | physicalTable | qlik | `/qlik/medium_etl/Products` |
| 116 | dim_customer | physicalTable | qlik | `/qlik/medium_etl/dim_customer` |
| 117 | fact_orders | physicalTable | qlik | `/qlik/medium_etl/fact_orders` |
| 118 | vToday | filter | qlik | `/qlik/simple_load/variables/vToday` |
| 119 | unnamed_load | physicalTable | qlik | `/qlik/simple_load/unnamed_load` |
| 120 | unnamed_load | physicalTable | qlik | `/qlik/simple_load/unnamed_load` |
| 121 | Orders | physicalTable | qlik | `/qlik/simple_load/Orders` |
| 122 | customers | physicalTable | qlik | `/qlik/simple_load/customers` |
| 123 | Sales Data Warehouse | logicalTable | tableau | `/tableau/complex_enterprise/SalesWarehouse` |
| 124 | Budget & Forecast | logicalTable | tableau | `/tableau/complex_enterprise/BudgetData` |
| 125 | Top N | prompt | tableau | `/tableau/complex_enterprise/parameters/TopNParam` |
| 126 | Start Date | prompt | tableau | `/tableau/complex_enterprise/parameters/DateRangeStart` |
| 127 | End Date | prompt | tableau | `/tableau/complex_enterprise/parameters/DateRangeEnd` |
| 128 | Metric | prompt | tableau | `/tableau/complex_enterprise/parameters/MetricSelector` |
| 129 | Revenue Trend | analysis | tableau | `/tableau/complex_enterprise/worksheets/Revenue Trend` |
| 130 | Category Breakdown | analysis | tableau | `/tableau/complex_enterprise/worksheets/Category Breakdown` |
| 131 | Geographic Analysis | analysis | tableau | `/tableau/complex_enterprise/worksheets/Geographic Analysis` |
| 132 | Customer Segments | analysis | tableau | `/tableau/complex_enterprise/worksheets/Customer Segments` |
| 133 | Top Products | analysis | tableau | `/tableau/complex_enterprise/worksheets/Top Products` |
| 134 | Budget vs Actual | analysis | tableau | `/tableau/complex_enterprise/worksheets/Budget vs Actual` |
| 135 | Executive Summary | dashboard | tableau | `/tableau/complex_enterprise/dashboards/Executive Summary` |
| 136 | Operations Detail | dashboard | tableau | `/tableau/complex_enterprise/dashboards/Operations Detail` |
| 137 | Enterprise Sales | logicalTable | tableau | `/tableau/medium_dashboard/EnterpriseSales` |
| 138 | Top N Customers | prompt | tableau | `/tableau/medium_dashboard/parameters/TopN` |
| 139 | Min Revenue Filter | prompt | tableau | `/tableau/medium_dashboard/parameters/MinRevenue` |
| 140 | Revenue by Category | analysis | tableau | `/tableau/medium_dashboard/worksheets/Revenue by Category` |
| 141 | Regional Profit | analysis | tableau | `/tableau/medium_dashboard/worksheets/Regional Profit` |
| 142 | Top Customers | analysis | tableau | `/tableau/medium_dashboard/worksheets/Top Customers` |
| 143 | Sales Overview | dashboard | tableau | `/tableau/medium_dashboard/dashboards/Sales Overview` |
| 144 | Sales DB | logicalTable | tableau | `/tableau/simple_chart/SalesDatabase` |
| 145 | Revenue by Region | analysis | tableau | `/tableau/simple_chart/worksheets/Revenue by Region` |

</details>

---

## 2. Schema Migration (DDL)

**Tables generated:** 36

| # | Table | Source | Platform |
|---|-------|--------|----------|
| 1 | `DIM_DATE` | rpd | Lakehouse (Delta) |
| 2 | `DIM_PRODUCT` | rpd | Lakehouse (Delta) |
| 3 | `DIM_CUSTOMER` | rpd | Lakehouse (Delta) |
| 4 | `DIM_STORE` | rpd | Lakehouse (Delta) |
| 5 | `DIM_CHANNEL` | rpd | Lakehouse (Delta) |
| 6 | `FACT_SALES` | rpd | Lakehouse (Delta) |
| 7 | `FACT_RETURNS` | rpd | Lakehouse (Delta) |
| 8 | `FACT_BUDGET` | rpd | Lakehouse (Delta) |
| 9 | `EMPLOYEES` | rpd | Lakehouse (Delta) |
| 10 | `DEPARTMENTS` | rpd | Lakehouse (Delta) |
| 11 | `LOCATIONS` | rpd | Lakehouse (Delta) |
| 12 | `PAYROLL` | rpd | Lakehouse (Delta) |
| 13 | `CUSTOMERS` | rpd | Lakehouse (Delta) |
| 14 | `ORDERS` | rpd | Lakehouse (Delta) |
| 15 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 16 | `RegionMapping` | qlik | Lakehouse (Delta) |
| 17 | `Stores` | qlik | Lakehouse (Delta) |
| 18 | `Channels` | qlik | Lakehouse (Delta) |
| 19 | `OrderEnriched` | qlik | Lakehouse (Delta) |
| 20 | `CustomerSummary` | qlik | Lakehouse (Delta) |
| 21 | `ProductPerformance` | qlik | Lakehouse (Delta) |
| 22 | `Returns` | qlik | Lakehouse (Delta) |
| 23 | `Budget` | qlik | Lakehouse (Delta) |
| 24 | `dim_customer` | qlik | Lakehouse (Delta) |
| 25 | `dim_product` | qlik | Lakehouse (Delta) |
| 26 | `fact_orders` | qlik | Lakehouse (Delta) |
| 27 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 28 | `Regions` | qlik | Lakehouse (Delta) |
| 29 | `OrderSummary` | qlik | Lakehouse (Delta) |
| 30 | `Products` | qlik | Lakehouse (Delta) |
| 31 | `dim_customer` | qlik | Lakehouse (Delta) |
| 32 | `fact_orders` | qlik | Lakehouse (Delta) |
| 33 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 34 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 35 | `Orders` | qlik | Lakehouse (Delta) |
| 36 | `customers` | qlik | Lakehouse (Delta) |

<details>
<summary>Generated DDL statements</summary>

#### `DIM_DATE`

```sql
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
```

#### `DIM_PRODUCT`

```sql
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
```

#### `DIM_CUSTOMER`

```sql
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
```

#### `DIM_STORE`

```sql
CREATE TABLE IF NOT EXISTS DIM_STORE (
    STORE_KEY INT,
    STORE_NAME STRING,
    STORE_TYPE STRING,
    REGION STRING
)
USING DELTA;
```

#### `DIM_CHANNEL`

```sql
CREATE TABLE IF NOT EXISTS DIM_CHANNEL (
    CHANNEL_KEY INT,
    CHANNEL_NAME STRING,
    CHANNEL_CLASS STRING
)
USING DELTA;
```

#### `FACT_SALES`

```sql
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
```

#### `FACT_RETURNS`

```sql
CREATE TABLE IF NOT EXISTS FACT_RETURNS (
    RETURN_KEY INT,
    SALES_KEY INT,
    RETURN_DATE_KEY INT,
    RETURN_QUANTITY INT,
    REASON_CODE STRING
)
USING DELTA;
```

#### `FACT_BUDGET`

```sql
CREATE TABLE IF NOT EXISTS FACT_BUDGET (
    BUDGET_KEY INT,
    DATE_KEY INT,
    PRODUCT_KEY INT,
    STORE_KEY INT,
    BUDGET_AMOUNT STRING
)
USING DELTA;
```

#### `EMPLOYEES`

```sql
CREATE TABLE IF NOT EXISTS EMPLOYEES (
    EMP_ID INT,
    FIRST_NAME STRING,
    LAST_NAME STRING,
    DEPT_ID INT,
    HIRE_DATE TIMESTAMP,
    SALARY STRING
)
USING DELTA;
```

#### `DEPARTMENTS`

```sql
CREATE TABLE IF NOT EXISTS DEPARTMENTS (
    DEPT_ID INT,
    DEPT_NAME STRING,
    LOCATION_ID INT
)
USING DELTA;
```

#### `LOCATIONS`

```sql
CREATE TABLE IF NOT EXISTS LOCATIONS (
    LOCATION_ID INT,
    CITY STRING,
    COUNTRY STRING
)
USING DELTA;
```

#### `PAYROLL`

```sql
CREATE TABLE IF NOT EXISTS PAYROLL (
    PAY_ID INT,
    EMP_ID INT,
    PAY_DATE TIMESTAMP,
    GROSS_PAY STRING,
    DEDUCTIONS STRING
)
USING DELTA;
```

#### `CUSTOMERS`

```sql
CREATE TABLE IF NOT EXISTS CUSTOMERS (
    CUST_ID INT,
    CUST_NAME STRING,
    EMAIL STRING,
    REGION STRING
)
USING DELTA;
```

#### `ORDERS`

```sql
CREATE TABLE IF NOT EXISTS ORDERS (
    ORDER_ID INT,
    CUST_ID INT,
    ORDER_DATE TIMESTAMP,
    AMOUNT STRING
)
USING DELTA;
```

#### `unnamed_load`

```sql
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
```

#### `RegionMapping`

```sql
CREATE TABLE IF NOT EXISTS RegionMapping (
    RegionCode STRING,
    RegionName STRING,
    CurrencyCode STRING,
    TimeZone STRING
)
USING DELTA;
```

#### `Stores`

```sql
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
```

#### `Channels`

```sql
CREATE TABLE IF NOT EXISTS Channels (
    channel_code STRING,
    channel_name STRING,
    channel_class STRING,
    commission_pct STRING
)
USING DELTA;
```

#### `OrderEnriched`

```sql
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
```

#### `CustomerSummary`

```sql
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
```

#### `ProductPerformance`

```sql
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
```

#### `Returns`

```sql
CREATE TABLE IF NOT EXISTS Returns (
    return_id STRING,
    order_id STRING,
    return_date STRING,
    return_quantity STRING,
    reason_code STRING,
    refund_amount STRING
)
USING DELTA;
```

#### `Budget`

```sql
CREATE TABLE IF NOT EXISTS Budget (
    budget_month STRING,
    region_code STRING,
    category STRING,
    budget_amount STRING,
    budget_units STRING
)
USING DELTA;
```

#### `dim_customer`

```sql
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
```

#### `dim_product`

```sql
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
```

#### `fact_orders`

```sql
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
```

#### `unnamed_load`

```sql
CREATE TABLE IF NOT EXISTS unnamed_load (
    Script___Medium_ETL____Complexity__Medium____Tables__5 STRING,
    SQL__2 STRING,
    Variables__4____Features_ STRING
)
USING DELTA;
```

#### `Regions`

```sql
CREATE TABLE IF NOT EXISTS Regions (
    RegionID STRING,
    RegionName STRING,
    Manager STRING
)
USING DELTA;
```

#### `OrderSummary`

```sql
CREATE TABLE IF NOT EXISTS OrderSummary (
    customer_id STRING,
    OrderCount STRING,
    TotalRevenue STRING,
    AvgOrderValue STRING
)
USING DELTA;
```

#### `Products`

```sql
CREATE TABLE IF NOT EXISTS Products (
    product_id STRING,
    product_name STRING,
    category STRING,
    subcategory STRING,
    unit_cost STRING
)
USING DELTA;
```

#### `dim_customer`

```sql
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id STRING,
    customer_name STRING,
    email STRING,
    region_id STRING,
    segment STRING,
    signup_date STRING
)
USING DELTA;
```

#### `fact_orders`

```sql
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
```

#### `unnamed_load`

```sql
CREATE TABLE IF NOT EXISTS unnamed_load (
    Script___Simple_Load____Complexity__Simple____Tables__2 STRING,
    SQL__1 STRING,
    Variables__1____Features__Basic_SQL_SELECT STRING,
    QVD_file_load____________________________________________________________________Connection_CONNECT_TO__sales_db_connection_______Variables_SET_vToday___Today________Load_customers STRING
)
USING DELTA;
```

#### `unnamed_load`

```sql
CREATE TABLE IF NOT EXISTS unnamed_load (
    orders STRING
)
USING DELTA;
```

#### `Orders`

```sql
CREATE TABLE IF NOT EXISTS Orders (
    order_id STRING,
    customer_id STRING,
    order_date STRING,
    product_name STRING,
    quantity STRING,
    amount STRING
)
USING DELTA;
```

#### `customers`

```sql
CREATE TABLE IF NOT EXISTS customers (
    customer_id STRING,
    customer_name STRING,
    email STRING,
    region STRING,
    segment STRING
)
USING DELTA;
```

</details>

---

## 3. Semantic Model (TMDL)

**TMDL files generated:** 25  
**Expressions translated:** 76  
**Warnings:** 0  
**Items requiring review:** 61

### Generated Files

| File | Size (chars) |
|------|-------------|
| `.platform` | 304 |
| `definition/expressions.tmdl` | 220 |
| `definition/perspectives.tmdl` | 2,334 |
| `definition/roles.tmdl` | 0 |
| `definition/tables/Accounts.tmdl` | 1,323 |
| `definition/tables/Budget.tmdl` | 478 |
| `definition/tables/Budget_&_Forecast.tmdl` | 1,593 |
| `definition/tables/Channel.tmdl` | 655 |
| `definition/tables/Currency.tmdl` | 803 |
| `definition/tables/Customer.tmdl` | 1,221 |
| `definition/tables/DIM_Customer.tmdl` | 760 |
| `definition/tables/DIM_Employee.tmdl` | 1,159 |
| `definition/tables/DIM_Location.tmdl` | 874 |
| `definition/tables/Enterprise_Sales.tmdl` | 2,648 |
| `definition/tables/Entity.tmdl` | 886 |
| `definition/tables/FACT_Orders.tmdl` | 803 |
| `definition/tables/FACT_Payroll.tmdl` | 987 |
| `definition/tables/Product.tmdl` | 2,218 |
| `definition/tables/Returns.tmdl` | 627 |
| `definition/tables/Sales.tmdl` | 2,336 |
| `definition/tables/Sales_DB.tmdl` | 1,459 |
| `definition/tables/Sales_Data_Warehouse.tmdl` | 5,630 |
| `definition/tables/Scenario.tmdl` | 1,202 |
| `definition/tables/Time.tmdl` | 1,800 |
| `model.tmdl` | 170 |

### Expression Translations

| # | Source Expression | DAX Output | Confidence |
|---|-----------------|------------|------------|
| 1 | `@PRIOR(Time, 12, @LEVMBRS(Time, 3))` | `@PRIOR(Time, 12, @LEVMBRS(Time, 3))` | 30% |
| 2 | `@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))` | `@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))` | 60% |
| 3 | `Revenue + COGS` | `Revenue + COGS` | 100% |
| 4 | `Gross Profit + OpEx` | `Gross Profit + OpEx` | 100% |
| 5 | `EBITDA + Depreciation` | `EBITDA + Depreciation` | 60% |
| 6 | `@ROUND(Gross Profit % Revenue, 4)` | `@ROUND(Gross Profit % Revenue, 4)` | 60% |
| 7 | `@ROUND(EBITDA % Revenue, 4)` | `@ROUND(EBITDA % Revenue, 4)` | 60% |
| 8 | `@ROUND(Revenue / (Headcount SM + Headcount RD + Headcount GA…` | `@ROUND(Revenue / (Headcount SM + Headcount RD + Headcount GA…` | 60% |
| 9 | `Actual - Budget` | `Actual - Budget` | 100% |
| 10 | `@ROUND((Actual - Budget) % Budget, 4)` | `@ROUND((Actual - Budget) % Budget, 4)` | 60% |
| 11 | `Actual - Forecast` | `Actual - Forecast` | 100% |
| 12 | `@ROUND((Actual - @PRIOR(Actual, 1, @LEVMBRS(Scenario, 0))) %…` | `@ROUND((Actual - @PRIOR(Actual, 1, @LEVMBRS(Scenario, 0))) %…` | 30% |
| 13 | `@CALCMBR(Local, @XREF(ExchangeRates, Rate))` | `@CALCMBR(Local, @XREF(ExchangeRates, Rate))` | 60% |
| 14 | `@CALCMBR(USD, @XREF(ExchangeRates, EUR_Rate))` | `@CALCMBR(USD, @XREF(ExchangeRates, EUR_Rate))` | 60% |
| 15 | `@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))` | `@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))` | 60% |
| 16 | `Revenue - COGS` | `Revenue - COGS` | 100% |
| 17 | `Gross Profit - Operating Expenses` | `Gross Profit - Operating Expenses` | 60% |
| 18 | `@ROUND(Gross Profit % Revenue, 4)` | `@ROUND(Gross Profit % Revenue, 4)` | 60% |
| 19 | `Actual - Budget` | `Actual - Budget` | 100% |
| 20 | `@ROUND((Actual - Budget) % Budget, 4)` | `@ROUND((Actual - Budget) % Budget, 4)` | 60% |
| 21 | `Revenue - COGS` | `Revenue - COGS` | 100% |
| 22 | `"DIM_DATE"."FULL_DATE"` | `"DIM_DATE"."FULL_DATE"` | 60% |
| 23 | `"DIM_DATE"."YEAR"` | `"DIM_DATE"."YEAR"` | 100% |
| 24 | `"DIM_DATE"."QUARTER"` | `"DIM_DATE"."QUARTER"` | 100% |
| 25 | `"DIM_DATE"."MONTH_NAME"` | `"DIM_DATE"."MONTH_NAME"` | 60% |
| 26 | `"DIM_PRODUCT"."PRODUCT_NAME"` | `"DIM_PRODUCT"."PRODUCT_NAME"` | 60% |
| 27 | `"DIM_PRODUCT"."CATEGORY"` | `"DIM_PRODUCT"."CATEGORY"` | 60% |
| 28 | `"DIM_PRODUCT"."SUBCATEGORY"` | `"DIM_PRODUCT"."SUBCATEGORY"` | 60% |
| 29 | `"DIM_PRODUCT"."BRAND"` | `"DIM_PRODUCT"."BRAND"` | 60% |
| 30 | `("DIM_PRODUCT"."UNIT_PRICE" - "DIM_PRODUCT"."UNIT_COST") / "…` | `("DIM_PRODUCT"."UNIT_PRICE" - "DIM_PRODUCT"."UNIT_COST") / "…` | 60% |
| 31 | `"DIM_CUSTOMER"."CUSTOMER_NAME"` | `"DIM_CUSTOMER"."CUSTOMER_NAME"` | 60% |
| 32 | `"DIM_CUSTOMER"."SEGMENT"` | `"DIM_CUSTOMER"."SEGMENT"` | 60% |
| 33 | `"DIM_CUSTOMER"."REGION"` | `"DIM_CUSTOMER"."REGION"` | 60% |
| 34 | `"DIM_CUSTOMER"."COUNTRY"` | `"DIM_CUSTOMER"."COUNTRY"` | 60% |
| 35 | `"DIM_CUSTOMER"."CITY"` | `"DIM_CUSTOMER"."CITY"` | 60% |
| 36 | `"FACT_SALES"."QUANTITY"` | `"FACT_SALES"."QUANTITY"` | 60% |
| 37 | `SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1…` | `SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRI…` | 100% |
| 38 | `SUM("FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST")` | `SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_CO…` | 100% |
| 39 | `SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1…` | `SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRI…` | 100% |
| 40 | `CASE WHEN SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_P…` | `SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY" * "FA…` | 80% |
| 41 | `CASE WHEN SUM("FACT_SALES"."QUANTITY") = 0 THEN 0 ELSE SUM("…` | `SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY"]) = 0…` | 80% |
| 42 | `SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE") - S…` | `SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRI…` | 100% |
| 43 | `"FACT_RETURNS"."RETURN_QUANTITY"` | `"FACT_RETURNS"."RETURN_QUANTITY"` | 60% |
| 44 | `"FACT_RETURNS"."REASON_CODE"` | `"FACT_RETURNS"."REASON_CODE"` | 60% |
| 45 | `"FACT_BUDGET"."BUDGET_AMOUNT"` | `"FACT_BUDGET"."BUDGET_AMOUNT"` | 60% |
| 46 | `"EMPLOYEES"."EMP_ID"` | `"EMPLOYEES"."EMP_ID"` | 100% |
| 47 | `"EMPLOYEES"."FIRST_NAME" || ' ' || "EMPLOYEES"."LAST_NAME"` | `"EMPLOYEES"."FIRST_NAME" & ' ' & "EMPLOYEES"."LAST_NAME"` | 100% |
| 48 | `"EMPLOYEES"."HIRE_DATE"` | `"EMPLOYEES"."HIRE_DATE"` | 60% |
| 49 | `"DEPARTMENTS"."DEPT_NAME"` | `"DEPARTMENTS"."DEPT_NAME"` | 60% |
| 50 | `"LOCATIONS"."LOCATION_ID"` | `"LOCATIONS"."LOCATION_ID"` | 60% |
| 51 | `"LOCATIONS"."CITY"` | `"LOCATIONS"."CITY"` | 100% |
| 52 | `"LOCATIONS"."COUNTRY"` | `"LOCATIONS"."COUNTRY"` | 60% |
| 53 | `"PAYROLL"."PAY_ID"` | `"PAYROLL"."PAY_ID"` | 100% |
| 54 | `"PAYROLL"."GROSS_PAY"` | `"PAYROLL"."GROSS_PAY"` | 60% |
| 55 | `"PAYROLL"."GROSS_PAY" - "PAYROLL"."DEDUCTIONS"` | `"PAYROLL"."GROSS_PAY" - "PAYROLL"."DEDUCTIONS"` | 60% |
| 56 | `AVG("EMPLOYEES"."SALARY")` | `AVERAGE('FACT_Payroll'["EMPLOYEES"."SALARY"])` | 100% |
| 57 | `"CUSTOMERS"."CUST_ID"` | `"CUSTOMERS"."CUST_ID"` | 60% |
| 58 | `"CUSTOMERS"."CUST_NAME"` | `"CUSTOMERS"."CUST_NAME"` | 60% |
| 59 | `"CUSTOMERS"."REGION"` | `"CUSTOMERS"."REGION"` | 100% |
| 60 | `"ORDERS"."ORDER_ID"` | `"ORDERS"."ORDER_ID"` | 100% |
| 61 | `"ORDERS"."AMOUNT"` | `"ORDERS"."AMOUNT"` | 100% |
| 62 | `SUM("ORDERS"."AMOUNT") * 0.2` | `SUM('FACT_Orders'["ORDERS"."AMOUNT"]) * 0.2` | 100% |
| 63 | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | 60% |
| 64 | `[Quantity] * [UnitCost] + [TaxAmount] + [FreightCost]` | `[Quantity] * [UnitCost] + [TaxAmount] + [FreightCost]` | 60% |
| 65 | `[Revenue] - [TotalCost]` | `[Revenue] - [TotalCost]` | 60% |
| 66 | `IF [Revenue] > 0 THEN [Profit] / [Revenue] * 100 ELSE 0 END` | `IF [Revenue] > 0 THEN [Profit] / [Revenue] * 100 ELSE 0 END` | 60% |
| 67 | `[Quantity] * [UnitPrice] * [DiscountPct]` | `[Quantity] * [UnitPrice] * [DiscountPct]` | 60% |
| 68 | `IF [UnitPrice] > 500 THEN 'Premium' ELSEIF [UnitPrice] > 100…` | `IF [UnitPrice] > 500 THEN 'Premium' ELSEIF [UnitPrice] > 100…` | 60% |
| 69 | `IF [Revenue] > 5000 THEN 'Yes' ELSE 'No' END` | `IF [Revenue] > 5000 THEN 'Yes' ELSE 'No' END` | 60% |
| 70 | `SUM([Revenue]) / COUNTD([OrderID])` | `SUM('Sales Data Warehouse'[[Revenue]]) / COUNTD([OrderID])` | 100% |
| 71 | `[ForecastAmount] - [BudgetAmount]` | `[ForecastAmount] - [BudgetAmount]` | 60% |
| 72 | `IF [BudgetAmount] > 0 THEN ([ForecastAmount] - [BudgetAmount…` | `IF [BudgetAmount] > 0 THEN ([ForecastAmount] - [BudgetAmount…` | 60% |
| 73 | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | 60% |
| 74 | `[Revenue] - ([Quantity] * [UnitCost])` | `[Revenue] - ([Quantity] * [UnitCost])` | 60% |
| 75 | `IF [Revenue] > 0 THEN [Profit] / [Revenue] ELSE 0 END` | `IF [Revenue] > 0 THEN [Profit] / [Revenue] ELSE 0 END` | 60% |
| 76 | `[Amount] * [Quantity]` | `[Amount] * [Quantity]` | 60% |

### Items Requiring Review

| Type | Table | Column/Hierarchy | Reason |
|------|-------|------------------|--------|
| hierarchy | Time | TimeHierarchy | Missing column references |
| hierarchy | Accounts | AccountsHierarchy | Missing column references |
| hierarchy | Scenario | ScenarioHierarchy | Missing column references |
| hierarchy | Currency | CurrencyHierarchy | Missing column references |
| hierarchy | Time | TimeHierarchy | Missing column references |
| hierarchy | Accounts | AccountsHierarchy | Missing column references |
| hierarchy | Scenario | ScenarioHierarchy | Missing column references |
| hierarchy | Accounts | AccountsHierarchy | Missing column references |
| hierarchy | Customer | GeoHierarchy | Missing column references |
| hierarchy | DIM_Employee | OrgHierarchy | Missing column references |
| expression | Time | Prior Year | Untranslatable pattern: PRIOR (hierarchical); No translation rules matched — expression may need manual review |
| expression | Time | YTD | No translation rules matched — expression may need manual review |
| expression | Accounts | EBIT | No translation rules matched — expression may need manual review |
| expression | Accounts | Gross Margin Pct | No translation rules matched — expression may need manual review |
| expression | Accounts | EBITDA Margin Pct | No translation rules matched — expression may need manual review |
| expression | Accounts | Rev per FTE | No translation rules matched — expression may need manual review |
| expression | Scenario | Bud Var Pct | No translation rules matched — expression may need manual review |
| expression | Scenario | YoY Growth | Untranslatable pattern: PRIOR (hierarchical); No translation rules matched — expression may need manual review |
| expression | Currency | USD | No translation rules matched — expression may need manual review |
| expression | Currency | EUR | No translation rules matched — expression may need manual review |
| expression | Time | YTD | No translation rules matched — expression may need manual review |
| expression | Accounts | Operating Income | No translation rules matched — expression may need manual review |
| expression | Accounts | Gross Margin Pct | No translation rules matched — expression may need manual review |
| expression | Scenario | Variance Pct | No translation rules matched — expression may need manual review |
| expression | Time | Date | No translation rules matched — expression may need manual review |
| expression | Time | Month | No translation rules matched — expression may need manual review |
| expression | Product | Product Name | No translation rules matched — expression may need manual review |
| expression | Product | Category | No translation rules matched — expression may need manual review |
| expression | Product | Subcategory | No translation rules matched — expression may need manual review |
| expression | Product | Brand | No translation rules matched — expression may need manual review |
| expression | Product | Margin Pct | No translation rules matched — expression may need manual review |
| expression | Customer | Customer Name | No translation rules matched — expression may need manual review |
| expression | Customer | Segment | No translation rules matched — expression may need manual review |
| expression | Customer | Region | No translation rules matched — expression may need manual review |
| expression | Customer | Country | No translation rules matched — expression may need manual review |
| expression | Customer | City | No translation rules matched — expression may need manual review |
| expression | Sales | Quantity | No translation rules matched — expression may need manual review |
| expression | Returns | Return Quantity | No translation rules matched — expression may need manual review |
| expression | Returns | Reason Code | No translation rules matched — expression may need manual review |
| expression | Budget | Budget Amount | No translation rules matched — expression may need manual review |
| expression | DIM_Employee | Hire Date | No translation rules matched — expression may need manual review |
| expression | DIM_Employee | Department | No translation rules matched — expression may need manual review |
| expression | DIM_Location | Location ID | No translation rules matched — expression may need manual review |
| expression | DIM_Location | Country | No translation rules matched — expression may need manual review |
| expression | FACT_Payroll | Gross Pay | No translation rules matched — expression may need manual review |
| expression | FACT_Payroll | Net Pay | No translation rules matched — expression may need manual review |
| expression | DIM_Customer | Customer ID | No translation rules matched — expression may need manual review |
| expression | DIM_Customer | Customer Name | No translation rules matched — expression may need manual review |
| expression | Sales Data Warehouse | Revenue | No translation rules matched — expression may need manual review |
| expression | Sales Data Warehouse | TotalCost | No translation rules matched — expression may need manual review |
| expression | Sales Data Warehouse | Profit | No translation rules matched — expression may need manual review |
| expression | Sales Data Warehouse | ProfitMargin | No translation rules matched — expression may need manual review |
| expression | Sales Data Warehouse | DiscountAmount | No translation rules matched — expression may need manual review |
| expression | Sales Data Warehouse | PriceCategory | No translation rules matched — expression may need manual review |
| expression | Sales Data Warehouse | IsHighValue | No translation rules matched — expression may need manual review |
| expression | Budget & Forecast | BudgetVariance | No translation rules matched — expression may need manual review |
| expression | Budget & Forecast | VariancePct | No translation rules matched — expression may need manual review |
| expression | Enterprise Sales | Revenue | No translation rules matched — expression may need manual review |
| expression | Enterprise Sales | Profit | No translation rules matched — expression may need manual review |
| expression | Enterprise Sales | ProfitMargin | No translation rules matched — expression may need manual review |
| expression | Sales DB | Revenue | No translation rules matched — expression may need manual review |

<details>
<summary>TMDL file contents</summary>

#### `.platform`

```
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {
    "type": "SemanticModel",
    "displayName": "SemanticModel"
  },
  "config": {
    "version": "2.0",
    "logicalId": "9a1349b3-10aa-4168-ac40-54c9d34ccbfd"
  }
}
```

#### `definition/expressions.tmdl`

```
expression 'Lakehouse' =
    let
        Source = Sql.Database("{lakehouse_sql_endpoint}", "MigrationLakehouse"),
    in
        Source
    lineageTag: dd629522-62c6-4e05-ae99-f06b439931bc
    queryGroup: 'Data Sources'
```

#### `definition/perspectives.tmdl`

```
perspective 'Executive Sales'
    perspectiveTable 'Time'
        perspectiveColumn Date
        perspectiveColumn Year
        perspectiveColumn Quarter
        perspectiveColumn Month
    perspectiveTable 'Product'
        perspectiveColumn Product Name
        perspectiveColumn Category
        perspectiveColumn Brand
    perspectiveTable 'Customer'
        perspectiveColumn Customer Name
        perspectiveColumn Region
        perspectiveColumn Country
    perspectiveTable 'Measures'
        perspectiveColumn Revenue
        perspectiveColumn Profit
        perspectiveColumn Profit Margin
        perspectiveColumn Budget Variance

perspective 'Product Performance'
    perspectiveTable 'Product'
        perspectiveColumn Product Name
        perspectiveColumn Category
        perspectiveColumn Subcategory
        perspectiveColumn Margin Pct
    perspectiveTable 'Sales'
        perspectiveColumn Revenue
        perspectiveColumn Quantity
        perspectiveColumn Return Rate

perspective 'Returns Analysis'
    perspectiveTable 'Time'
        perspectiveColumn Year
        perspectiveColumn Month
    perspectiveTable 'Product'
        perspectiveColumn Product Name
        perspectiveColumn Category
    perspectiveTable 'Returns'
        perspectiveColumn Return Quantity
        perspectiveColumn Reason Code

perspective 'HR Analytics'
    perspectiveTable 'Employees'
        perspectiveColumn Employee ID
        perspectiveColumn Full Name
        perspectiveColumn Hire Date
        perspectiveColumn Department
    perspectiveTable 'Locations'
        perspectiveColumn City
        perspectiveColumn Country
    perspectiveTable 'Payroll'
        perspectiveColumn Gross Pay
        perspectiveColumn Net Pay
        perspectiveColumn Avg Salary

perspective 'Compensation Review'
    perspectiveTable 'Employees'
        perspectiveColumn Full Name
        perspectiveColumn Department
    perspectiveTable 'Compensation'
        perspectiveColumn Gross Pay
        perspectiveColumn Net Pay

perspective 'Sales Analysis'
    perspectiveTable 'Customer'
        perspectiveColumn Customer ID
        perspectiveColumn Customer Name
        perspectiveColumn Region
    perspectiveTable 'Orders'
        perspectiveColumn Order ID
        perspectiveColumn Order Amount
        perspectiveColumn Profit
```

#### `definition/roles.tmdl`

```

```

#### `definition/tables/Accounts.tmdl`

```
table Accounts
    lineageTag: fdddaf45-8fcd-4b00-9af0-e77a57c1b751

    partition Accounts = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Accounts = Source{[Schema="dbo", Item="Accounts"]}[Data]
            in
                Accounts

    column 'Gross Profit' = Revenue - COGS
        dataType: string
        lineageTag: c4b00a0b-4478-4eb9-82f1-92048eca23b0

    hierarchy AccountsHierarchy
        level Income Statement
            column: Income Statement
        level Revenue
            column: Revenue
        level Product Sales
            column: Product Sales
        level Service Revenue
            column: Service Revenue
        level Subscription Rev
            column: Subscription Rev

    hierarchy AccountsHierarchy
        level Revenue
            column: Revenue
        level Product Sales
            column: Product Sales
        level Service Revenue
            column: Service Revenue
        level COGS
            column: COGS
        level Material Cost
            column: Material Cost

    hierarchy AccountsHierarchy
        level Revenue
            column: Revenue
        level COGS
            column: COGS
        level Gross Profit
            column: Gross Profit
```

#### `definition/tables/Budget.tmdl`

```
table Budget
    lineageTag: dcc216db-c564-480b-a480-6dc7fa3f42d1

    partition Budget = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Budget = Source{[Schema="dbo", Item="Budget"]}[Data]
            in
                Budget

    column 'Budget Amount' = "FACT_BUDGET"."BUDGET_AMOUNT"
        dataType: string
        lineageTag: 0e3ec246-78aa-4d2b-a660-b0ee297dfe4d
```

#### `definition/tables/Budget_&_Forecast.tmdl`

```
table Budget & Forecast
    lineageTag: 02fa9a1c-c8b2-49d3-a261-0d7ca0c2694c

    partition Budget & Forecast = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Budget_&_Forecast = Source{[Schema="dbo", Item="Budget_&_Forecast"]}[Data]
            in
                Budget_&_Forecast

    column BudgetMonth
        dataType: dateTime
        lineageTag: 57802dc9-a776-4e2c-b872-f79e59042c3f
        sourceColumn: BudgetMonth
        summarizeBy: none

    column BudgetRegion
        dataType: string
        lineageTag: 18b255f7-32a4-4bb1-bff6-93226b2d8369
        sourceColumn: BudgetRegion
        summarizeBy: none

    column BudgetCategory
        dataType: string
        lineageTag: 83c5bcd6-f3aa-45c9-bff4-d660d0c0ece8
        sourceColumn: BudgetCategory
        summarizeBy: none

    column BudgetAmount
        dataType: string
        lineageTag: a5066f93-6187-46f3-97f3-c7c24c86a0de
        sourceColumn: BudgetAmount
        summarizeBy: none

    column ForecastAmount
        dataType: string
        lineageTag: ed8fc172-3f50-43bb-a4bd-632753555008
        sourceColumn: ForecastAmount
        summarizeBy: none

    column 'BudgetVariance' = [ForecastAmount] - [BudgetAmount]
        dataType: string
        lineageTag: 11e8db44-eadb-4dcf-af4a-0cd1fb3227c3

    column 'VariancePct' = IF [BudgetAmount] > 0 THEN ([ForecastAmount] - [BudgetAmount]) / [BudgetAmount] * 100 ELSE 0 END
        dataType: string
        lineageTag: d4f5896a-b758-40c4-8d77-dbeefc8acac5
```

#### `definition/tables/Channel.tmdl`

```
table Channel
    lineageTag: 8296f79c-aaa3-4e79-bd3f-c8868c73ba08

    partition Channel = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Channel = Source{[Schema="dbo", Item="Channel"]}[Data]
            in
                Channel

    hierarchy ChannelHierarchy
        level All Channels
            column: All Channels
        level Direct
            column: Direct
        level Field Sales
            column: Field Sales
        level Inside Sales
            column: Inside Sales
        level E-Commerce
            column: E-Commerce
```

#### `definition/tables/Currency.tmdl`

```
table Currency
    lineageTag: 2dba00cb-90c4-4dc3-b276-ffbd72b1dfe1

    partition Currency = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Currency = Source{[Schema="dbo", Item="Currency"]}[Data]
            in
                Currency

    column 'USD' = @CALCMBR(Local, @XREF(ExchangeRates, Rate))
        dataType: string
        lineageTag: 2a26d58c-44d3-42f0-9add-23c1c56e74ea

    column 'EUR' = @CALCMBR(USD, @XREF(ExchangeRates, EUR_Rate))
        dataType: string
        lineageTag: 602bd1b0-2ceb-442a-b974-9f3ff9260a70

    hierarchy CurrencyHierarchy
        level Local
            column: Local
        level USD
            column: USD
        level EUR
            column: EUR
```

#### `definition/tables/Customer.tmdl`

```
table Customer
    lineageTag: 04ec26a9-30f9-40b1-b446-a2bae1c3dca3

    partition Customer = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Customer = Source{[Schema="dbo", Item="Customer"]}[Data]
            in
                Customer

    column 'Customer Name' = "DIM_CUSTOMER"."CUSTOMER_NAME"
        dataType: string
        lineageTag: 20ab9754-6a6e-4c5c-95f3-e43af8455d37

    column 'Segment' = "DIM_CUSTOMER"."SEGMENT"
        dataType: string
        lineageTag: ff418aaf-0503-4ce3-aeb3-3a5da937e8f3

    column 'Region' = "DIM_CUSTOMER"."REGION"
        dataType: string
        lineageTag: 1a529554-744b-44ac-96fb-229c1502ee5b

    column 'Country' = "DIM_CUSTOMER"."COUNTRY"
        dataType: string
        lineageTag: e74d4525-a550-4734-8c08-b4ca4c466499

    column 'City' = "DIM_CUSTOMER"."CITY"
        dataType: string
        lineageTag: 2341fb88-f4e1-4147-92aa-e6891cc8ea96

    hierarchy GeoHierarchy
        level Region
            column: Region
        level Country
            column: Country
        level State
            column: State
        level City
            column: City
```

#### `definition/tables/DIM_Customer.tmdl`

```
table DIM_Customer
    lineageTag: b3eb5e26-4995-40f4-9283-4cc108555b4d

    partition DIM_Customer = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                DIM_Customer = Source{[Schema="dbo", Item="DIM_Customer"]}[Data]
            in
                DIM_Customer

    column 'Customer ID' = "CUSTOMERS"."CUST_ID"
        dataType: string
        lineageTag: 62081cca-238d-4778-b66b-a51ee774ccf2

    column 'Customer Name' = "CUSTOMERS"."CUST_NAME"
        dataType: string
        lineageTag: 7df276ee-753b-4cd3-9589-d2c816fa112c

    column 'Region' = "CUSTOMERS"."REGION"
        dataType: string
        lineageTag: 17a44f7b-c051-4d81-9c12-a5a1adf58818
```

#### `definition/tables/DIM_Employee.tmdl`

```
table DIM_Employee
    lineageTag: a57ee2c4-8be9-4a81-be99-b9932d416fd3

    partition DIM_Employee = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                DIM_Employee = Source{[Schema="dbo", Item="DIM_Employee"]}[Data]
            in
                DIM_Employee

    column 'Employee ID' = "EMPLOYEES"."EMP_ID"
        dataType: string
        lineageTag: 2093d843-d984-4e14-beef-6d3d24b1d314

    column 'Full Name' = "EMPLOYEES"."FIRST_NAME" & ' ' & "EMPLOYEES"."LAST_NAME"
        dataType: string
        lineageTag: 497fb53f-57b8-425e-8413-c7fb4f88adbf

    column 'Hire Date' = "EMPLOYEES"."HIRE_DATE"
        dataType: string
        lineageTag: 39d2b8be-bfd1-448d-89ee-6ad9235cbff4

    column 'Department' = "DEPARTMENTS"."DEPT_NAME"
        dataType: string
        lineageTag: a728baf8-5e57-4180-b85f-7466d88cdc9d

    hierarchy OrgHierarchy
        level Country
            column: Country
        level City
            column: City
        level Department
            column: Department
        level Employee
            column: Employee
```

#### `definition/tables/DIM_Location.tmdl`

```
table DIM_Location
    lineageTag: 60281d3e-8892-46d2-a152-98d8c6a73d98

    partition DIM_Location = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                DIM_Location = Source{[Schema="dbo", Item="DIM_Location"]}[Data]
            in
                DIM_Location

    column 'Location ID' = "LOCATIONS"."LOCATION_ID"
        dataType: string
        lineageTag: 635d51af-ab83-4323-9808-48e530fae4c0

    column 'City' = "LOCATIONS"."CITY"
        dataType: string
        lineageTag: e133ae2e-4483-40a2-89eb-330dc81490a1

    column 'Country' = "LOCATIONS"."COUNTRY"
        dataType: string
        lineageTag: 1add4f32-6d3d-4215-b60a-5661694f7fad

    hierarchy GeoHierarchy
        level Country
            column: Country
        level City
            column: City
```

#### `definition/tables/Enterprise_Sales.tmdl`

```
table Enterprise Sales
    lineageTag: 86ca946b-0362-4eba-a0f4-31fbb02cdd9c

    partition Enterprise Sales = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Enterprise_Sales = Source{[Schema="dbo", Item="Enterprise_Sales"]}[Data]
            in
                Enterprise_Sales

    column CustomerName
        dataType: string
        lineageTag: 0422ea57-12e3-412a-82c2-8836dee0f032
        sourceColumn: CustomerName
        summarizeBy: none

    column Segment
        dataType: string
        lineageTag: 21abe0b2-cecb-4c1f-bab4-9d0901652cfd
        sourceColumn: Segment
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: ee7ee25c-e2b8-4c35-89b8-326a31c5bfe8
        sourceColumn: Region
        summarizeBy: none

    column Country
        dataType: string
        lineageTag: 0ddd61a0-46bd-4444-9db3-144fb5ce92c6
        sourceColumn: Country
        summarizeBy: none

    column Category
        dataType: string
        lineageTag: 5a028414-f0f2-4c30-bd37-dd107b231244
        sourceColumn: Category
        summarizeBy: none

    column Subcategory
        dataType: string
        lineageTag: 34770067-c89c-4642-8782-eaaa54687e98
        sourceColumn: Subcategory
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: 9599b881-e2a5-4cfb-a2af-26b8830aea9f
        sourceColumn: OrderDate
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: d4ee5ab6-4c71-459a-be03-8bc7f8c42bd1
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column UnitPrice
        dataType: string
        lineageTag: cd65fce9-c5b0-4b03-b8c1-e6c409166f40
        sourceColumn: UnitPrice
        summarizeBy: none

    column UnitCost
        dataType: string
        lineageTag: c104d5c5-ef5c-4cb6-aa51-988676428472
        sourceColumn: UnitCost
        summarizeBy: none

    column DiscountPct
        dataType: string
        lineageTag: bb02bd3f-40dd-42f0-8a14-09626457c119
        sourceColumn: DiscountPct
        summarizeBy: none

    column 'Revenue' = [Quantity] * [UnitPrice] * (1 - [DiscountPct])
        dataType: string
        lineageTag: ff20a03d-ca60-46a5-bc75-cc389ee21478

    column 'Profit' = [Revenue] - ([Quantity] * [UnitCost])
        dataType: string
        lineageTag: db254a92-c1d9-4561-ab56-cac48181ee6d

    column 'ProfitMargin' = IF [Revenue] > 0 THEN [Profit] / [Revenue] ELSE 0 END
        dataType: string
        lineageTag: 842d06de-9560-48ba-8cf6-01be16e70de6
```

#### `definition/tables/Entity.tmdl`

```
table Entity
    lineageTag: 42101461-9df0-45ad-96cd-692ca1b3a37f

    partition Entity = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Entity = Source{[Schema="dbo", Item="Entity"]}[Data]
            in
                Entity

    hierarchy EntityHierarchy
        level Worldwide
            column: Worldwide
        level Americas
            column: Americas
        level US
            column: US
        level US-East
            column: US-East
        level US-West
            column: US-West

    hierarchy EntityHierarchy
        level Global
            column: Global
        level North America
            column: North America
        level US
            column: US
        level Canada
            column: Canada
        level EMEA
            column: EMEA
```

#### `definition/tables/FACT_Orders.tmdl`

```
table FACT_Orders
    lineageTag: 6e067a41-03ac-4582-8327-077174f99230

    partition FACT_Orders = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                FACT_Orders = Source{[Schema="dbo", Item="FACT_Orders"]}[Data]
            in
                FACT_Orders

    column 'Order ID' = "ORDERS"."ORDER_ID"
        dataType: string
        lineageTag: 274d67aa-e63e-446d-9b58-afd297a98123

    column 'Order Amount' = "ORDERS"."AMOUNT"
        dataType: string
        lineageTag: 8e21ec6a-29c7-4b16-af48-98fc0fa8ce69

    measure 'Profit' = SUM('FACT_Orders'["ORDERS"."AMOUNT"]) * 0.2
        lineageTag: 774ec189-3994-483b-b436-2467f3a39832
        formatString: #,0.00
        displayFolder: Measures
```

#### `definition/tables/FACT_Payroll.tmdl`

```
table FACT_Payroll
    lineageTag: a1d7b508-9a45-4564-9fb7-0e0922148fe8

    partition FACT_Payroll = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                FACT_Payroll = Source{[Schema="dbo", Item="FACT_Payroll"]}[Data]
            in
                FACT_Payroll

    column 'Pay ID' = "PAYROLL"."PAY_ID"
        dataType: string
        lineageTag: 5865e327-ad1e-47f4-86ee-e063bd98b211

    column 'Gross Pay' = "PAYROLL"."GROSS_PAY"
        dataType: string
        lineageTag: dc03fc36-d040-40c5-9f78-28e6dccc7ee9

    column 'Net Pay' = "PAYROLL"."GROSS_PAY" - "PAYROLL"."DEDUCTIONS"
        dataType: string
        lineageTag: 6f7877e8-430b-468a-a080-be96caf99f35

    measure 'Avg Salary' = AVERAGE('FACT_Payroll'["EMPLOYEES"."SALARY"])
        lineageTag: ad256b47-7084-46f1-92fb-a861ee7a25fe
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures
```

#### `definition/tables/Product.tmdl`

```
table Product
    lineageTag: 1e6eccd7-3cbf-453e-b1c9-c7151f04a610

    partition Product = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Product = Source{[Schema="dbo", Item="Product"]}[Data]
            in
                Product

    column 'Product Name' = "DIM_PRODUCT"."PRODUCT_NAME"
        dataType: string
        lineageTag: 78e0e2ae-82b2-4349-891b-09324780c94f

    column 'Category' = "DIM_PRODUCT"."CATEGORY"
        dataType: string
        lineageTag: ece3fc7c-1987-4dce-8c7b-a78c2ffd9f70

    column 'Subcategory' = "DIM_PRODUCT"."SUBCATEGORY"
        dataType: string
        lineageTag: 2aec5c51-5d37-4bf1-b3db-419cd640d909

    column 'Brand' = "DIM_PRODUCT"."BRAND"
        dataType: string
        lineageTag: d4b4e06f-fa5f-4313-a837-8d4919227dd1

    column 'Margin Pct' = ("DIM_PRODUCT"."UNIT_PRICE" - "DIM_PRODUCT"."UNIT_COST") / "DIM_PRODUCT"."UNIT_PRICE" * 100
        dataType: string
        lineageTag: 906ead34-e81a-48aa-bc0e-8ac4264b02e3

    hierarchy ProductHierarchy
        level Total Products
            column: Total Products
        level Hardware
            column: Hardware
        level Servers
            column: Servers
        level Storage
            column: Storage
        level Networking
            column: Networking

    hierarchy ProductHierarchy
        level All Products
            column: All Products
        level Hardware
            column: Hardware
        level Servers
            column: Servers
        level Storage
            column: Storage
        level Networking
            column: Networking

    hierarchy ProductHierarchy
        level Electronics
            column: Electronics
        level Laptops
            column: Laptops
        level Phones
            column: Phones
        level Furniture
            column: Furniture
        level Desks
            column: Desks

    hierarchy ProductHierarchy
        level Category
            column: Category
        level Subcategory
            column: Subcategory
        level Brand
            column: Brand
        level Product Name
            column: Product Name
```

#### `definition/tables/Returns.tmdl`

```
table Returns
    lineageTag: 0363ffdb-3bbb-45d9-980d-bc33311bc413

    partition Returns = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Returns = Source{[Schema="dbo", Item="Returns"]}[Data]
            in
                Returns

    column 'Return Quantity' = "FACT_RETURNS"."RETURN_QUANTITY"
        dataType: string
        lineageTag: 6ebbca08-9e6b-481f-bae8-46a395782e07

    column 'Reason Code' = "FACT_RETURNS"."REASON_CODE"
        dataType: string
        lineageTag: d782479c-2304-439f-a3a3-0539d1a55921
```

#### `definition/tables/Sales.tmdl`

```
table Sales
    lineageTag: 377ca517-9c18-4d54-8e31-671c2a794995

    partition Sales = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Sales = Source{[Schema="dbo", Item="Sales"]}[Data]
            in
                Sales

    column 'Quantity' = "FACT_SALES"."QUANTITY"
        dataType: string
        lineageTag: ecbc40b8-6c52-4554-bbad-b394289222cb

    measure 'Revenue' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"]))
        lineageTag: 363c0d0d-27ea-46f0-a365-13bfd790e7b5
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Cost' = SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])
        lineageTag: b6c3e516-93c3-4658-a673-e0aafb3cdd06
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Profit' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"])) - SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])
        lineageTag: 5940261c-495d-4f83-bb79-4456fe985a6e
        formatString: #,0.00
        displayFolder: Measures

    measure 'Profit Margin' = SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) = 0, 0,
    (SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"])) - SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])) / SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) * 100
)
        lineageTag: 2f9c5df6-f030-446e-85e0-dc15c06ab52e
        formatString: #,0.00
        displayFolder: Measures

    measure 'Return Rate' = SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY"]) = 0, 0,
    SUM('Sales'["FACT_RETURNS"."RETURN_QUANTITY"]) / SUM('Sales'["FACT_SALES"."QUANTITY"]) * 100
)
        lineageTag: 73a56167-8aed-4587-a214-8ebdbb71988f
        formatString: 0.00%
        displayFolder: Measures

    measure 'Budget Variance' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) - SUM('Sales'["FACT_BUDGET"."BUDGET_AMOUNT"])
        lineageTag: 1b15b50a-e694-43e5-8d4f-1f37a19609f9
        formatString: #,0.00
        displayFolder: Measures
```

#### `definition/tables/Sales_DB.tmdl`

```
table Sales DB
    lineageTag: 62154abd-34b4-4bcf-8765-7cb142c696e5

    partition Sales DB = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Sales_DB = Source{[Schema="dbo", Item="Sales_DB"]}[Data]
            in
                Sales_DB

    column OrderID
        dataType: string
        lineageTag: 1a41d5f8-0f40-4bbe-98cf-33cc78aeda5a
        sourceColumn: OrderID
        summarizeBy: none

    column CustomerName
        dataType: string
        lineageTag: 4cebbf47-5986-4faf-b74d-fd9182a9a2db
        sourceColumn: CustomerName
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: 61326b6d-eb44-4247-8222-bd4adebb453d
        sourceColumn: Region
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: e625e247-6aba-4573-ba2b-21c46f25a2a0
        sourceColumn: OrderDate
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: a3250a3b-8a0e-4e0f-a918-80429da607c4
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column Amount
        dataType: string
        lineageTag: 2e725f75-1736-4eec-8d2a-a50f239bc5e4
        sourceColumn: Amount
        summarizeBy: none

    column 'Revenue' = [Amount] * [Quantity]
        dataType: string
        lineageTag: a12c8807-a7c5-4f31-b20e-3c59ca485a08
```

#### `definition/tables/Sales_Data_Warehouse.tmdl`

```
table Sales Data Warehouse
    lineageTag: e52fd08d-20ee-4730-ac26-18636b8becaf

    partition Sales Data Warehouse = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Sales_Data_Warehouse = Source{[Schema="dbo", Item="Sales_Data_Warehouse"]}[Data]
            in
                Sales_Data_Warehouse

    column OrderID
        dataType: string
        lineageTag: 204dabe2-5f1d-4fb5-bde5-0aed5462ed48
        sourceColumn: OrderID
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: 7d974088-f54e-45c3-ae9c-ca29cb4383ed
        sourceColumn: OrderDate
        summarizeBy: none

    column Year
        dataType: int64
        lineageTag: 3d052db6-8c7d-40f6-a90c-82b8ef3e3abb
        formatString: 0
        sourceColumn: Year
        summarizeBy: none

    column Quarter
        dataType: string
        lineageTag: 9e7302e6-4d3f-421e-9456-3747f0f5bfdd
        sourceColumn: Quarter
        summarizeBy: none

    column Month
        dataType: string
        lineageTag: 17bd8c79-a6e7-4c1d-8218-663dc30ba77b
        sourceColumn: Month
        summarizeBy: none

    column CustomerName
        dataType: string
        lineageTag: 83f4c419-878f-4003-87e5-b6d04495a3dc
        sourceColumn: CustomerName
        summarizeBy: none

    column Segment
        dataType: string
        lineageTag: 01eb510d-4bde-4470-a979-065ebba6818f
        sourceColumn: Segment
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: d69e2261-fcb6-48c1-a9d9-27e9ce72a029
        sourceColumn: Region
        summarizeBy: none

    column Country
        dataType: string
        lineageTag: bb8ce4ce-38bb-42f8-bebe-fa279430c22b
        sourceColumn: Country
        summarizeBy: none

    column State
        dataType: string
        lineageTag: 2d5a01a2-5ef9-43c2-be64-8bfb8e26413c
        sourceColumn: State
        summarizeBy: none

    column City
        dataType: string
        lineageTag: cf70a757-4d22-4e25-8b9f-a534293b8c74
        sourceColumn: City
        summarizeBy: none

    column Category
        dataType: string
        lineageTag: 8325327e-aad2-4284-93d6-3c32a607843f
        sourceColumn: Category
        summarizeBy: none

    column Subcategory
        dataType: string
        lineageTag: 233888af-56cf-4763-8d4a-e7e766e9433c
        sourceColumn: Subcategory
        summarizeBy: none

    column Brand
        dataType: string
        lineageTag: eafa3c52-f645-467a-8ea4-9e08a7786e0e
        sourceColumn: Brand
        summarizeBy: none

    column ProductName
        dataType: string
        lineageTag: 5dae2a87-71cb-4f21-8096-544b6246759d
        sourceColumn: ProductName
        summarizeBy: none

    column StoreName
        dataType: string
        lineageTag: 44fd32c7-c9a9-4c6e-8b9f-d23db81661e5
        sourceColumn: StoreName
        summarizeBy: none

    column StoreType
        dataType: string
        lineageTag: 801c8905-a58a-44dc-b0dd-1c7461ed1237
        sourceColumn: StoreType
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: a6240706-2922-48ce-852d-468752daefdf
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column UnitPrice
        dataType: string
        lineageTag: 749f4790-a4c1-4c4a-b2c6-022710f091fb
        sourceColumn: UnitPrice
        summarizeBy: none

    column UnitCost
        dataType: string
        lineageTag: 1c60c624-9e62-470a-93b2-e15b97cd5061
        sourceColumn: UnitCost
        summarizeBy: none

    column DiscountPct
        dataType: string
        lineageTag: 3ad6d666-e531-421c-9994-5f5f1ecc837e
        sourceColumn: DiscountPct
        summarizeBy: none

    column TaxAmount
        dataType: string
        lineageTag: 7bc825a9-1b44-4b7e-b2a8-e91689d03c80
        sourceColumn: TaxAmount
        summarizeBy: none

    column FreightCost
        dataType: string
        lineageTag: 6ce05fb9-2bc3-4887-9c1f-b5996c0e0d57
        sourceColumn: FreightCost
        summarizeBy: none

    column 'Revenue' = [Quantity] * [UnitPrice] * (1 - [DiscountPct])
        dataType: string
        lineageTag: fc95ff58-9d39-4cb7-afb2-761b807dba1e

    column 'TotalCost' = [Quantity] * [UnitCost] + [TaxAmount] + [FreightCost]
        dataType: string
        lineageTag: 9949a26f-4152-4e70-8278-848d6a46b532

    column 'Profit' = [Revenue] - [TotalCost]
        dataType: string
        lineageTag: 18f9b385-b651-4f74-b110-5225ba10e3b2

    column 'ProfitMargin' = IF [Revenue] > 0 THEN [Profit] / [Revenue] * 100 ELSE 0 END
        dataType: string
        lineageTag: 52f6b0c1-9459-47a4-97d5-4eaddee80553

    column 'DiscountAmount' = [Quantity] * [UnitPrice] * [DiscountPct]
        dataType: string
        lineageTag: 04500d72-ba03-4451-9cf9-f67757f97fbf

    column 'PriceCategory' = IF [UnitPrice] > 500 THEN 'Premium' ELSEIF [UnitPrice] > 100 THEN 'Mid-Range' ELSE 'Budget' END
        dataType: string
        lineageTag: 7a48b167-4e38-4b31-acc9-faae88a048c2

    column 'IsHighValue' = IF [Revenue] > 5000 THEN 'Yes' ELSE 'No' END
        dataType: string
        lineageTag: 5dfd3510-c82f-45c0-8cb2-bdd0aa5a7dda

    measure 'AvgOrderValue' = SUM('Sales Data Warehouse'[[Revenue]]) / COUNTD([OrderID])
        lineageTag: 611dcb06-5464-4b49-a9ff-43226c2d230c
        formatString: #,0.00
        displayFolder: Measures

    hierarchy Date
        level Year
            column: Year
        level Quarter
            column: Quarter
        level Month
            column: Month
```

#### `definition/tables/Scenario.tmdl`

```
table Scenario
    lineageTag: 5566feed-f9e4-474a-af0f-49fef844b814

    partition Scenario = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Scenario = Source{[Schema="dbo", Item="Scenario"]}[Data]
            in
                Scenario

    column 'Variance' = Actual - Budget
        dataType: string
        lineageTag: f5f7e69f-8086-42fd-bfbc-baf1e7781a6d

    column 'Variance Pct' = @ROUND((Actual - Budget) % Budget, 4)
        dataType: string
        lineageTag: 0e48dd48-1174-4222-b3b5-40679bc2669d

    hierarchy ScenarioHierarchy
        level Actual
            column: Actual
        level Budget
            column: Budget
        level Forecast
            column: Forecast
        level Best Case
            column: Best Case
        level Worst Case
            column: Worst Case

    hierarchy ScenarioHierarchy
        level Actual
            column: Actual
        level Budget
            column: Budget
        level Forecast
            column: Forecast
        level Variance
            column: Variance
        level Variance Pct
            column: Variance Pct
```

#### `definition/tables/Time.tmdl`

```
table Time
    lineageTag: faf87e0b-6ea7-4003-9b9c-a12fcfec7054

    partition Time = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MigrationLakehouse"),
                Time = Source{[Schema="dbo", Item="Time"]}[Data]
            in
                Time

    column 'Date' = "DIM_DATE"."FULL_DATE"
        dataType: string
        lineageTag: 9304543c-8e21-4c90-a52f-2f820996ff82

    column 'Year' = "DIM_DATE"."YEAR"
        dataType: string
        lineageTag: 6c96b377-ebb2-4547-98b7-833deacd0e15

    column 'Quarter' = "DIM_DATE"."QUARTER"
        dataType: string
        lineageTag: 17f0e33b-786a-4ca9-acc4-91d40af13122

    column 'Month' = "DIM_DATE"."MONTH_NAME"
        dataType: string
        lineageTag: da228047-ca13-439b-9dfa-0066e65a3167

    hierarchy TimeHierarchy
        level FY2023
            column: FY2023
        level H1-2023
            column: H1-2023
        level Q1-2023
            column: Q1-2023
        level Jan-23
            column: Jan-23
        level Feb-23
            column: Feb-23

    hierarchy TimeHierarchy
        level FY2024
            column: FY2024
        level Q1
            column: Q1
        level Jan
            column: Jan
        level Feb
            column: Feb
        level Mar
            column: Mar

    hierarchy TimeHierarchy
        level FY2024
            column: FY2024
        level Q1
            column: Q1
        level Jan
            column: Jan
        level Feb
            column: Feb
        level Mar
            column: Mar

    hierarchy TimeHierarchy
        level Year
            column: Year
        level Quarter
            column: Quarter
        level Month
            column: Month
        level Date
            column: Date
```

#### `model.tmdl`

```
model SemanticModel
    culture: en-US
    defaultPowerBIDataSourceVersion: powerBI_V3
    sourceQueryCulture: en-US
    lineageTag: af47c80b-8ab2-4e05-bea7-5af225e316f8
```

</details>

---

## 4. Validation

**Layers validated:** 4/4  
**Errors:** 0

Detailed reports written to:

- `data_reconciliation_report.md`
- `semantic_validation_report.md`
- `report_validation_report.md`
- `security_validation_report.md`
- `validation_summary.md`
- `reconciliation_queries.sql`

---

## 5. Migration Summary

| Metric | Value |
|--------|-------|
| Total assets discovered | **145** |
| Physical tables | 36 |
| Logical tables / dimensions | 30 |
| Analyses / worksheets | 15 |
| Dashboards | 3 |
| Security roles | 3 |
| Prompts / parameters | 12 |
| DDL statements generated | 36 |
| TMDL files generated | 25 |
| Expressions translated | 76 |
| Elapsed time | 0.2s |

---

*Report generated by OAC-to-Fabric Migration Accelerator*