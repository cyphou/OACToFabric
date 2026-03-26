# Migration Report

> **Generated:** 2026-03-24 15:03:06 UTC  
> **Total assets discovered:** 145  
> **Elapsed time:** 0.4s  
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
    "logicalId": "bc4bfc92-9c60-43f3-b4c4-e48a5074481a"
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
    lineageTag: 928a666d-f9c5-4f96-931f-e5b1d9c8dc3e
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
    lineageTag: a4ef0d2d-341c-468f-aecd-192847cbf45b

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
        lineageTag: 15c286dd-7130-49b6-880d-685d3d255f7c

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
    lineageTag: 651e861c-e69f-454a-9d82-48862cf74d38

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
        lineageTag: f678f1d6-5fec-4d25-89cc-247c24c6ecce
```

#### `definition/tables/Budget_&_Forecast.tmdl`

```
table Budget & Forecast
    lineageTag: fdd6eacd-764e-4e3f-bad1-648c72fce4b0

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
        lineageTag: 03c5e983-71ee-4ce3-98be-9eb90b75b3d9
        sourceColumn: BudgetMonth
        summarizeBy: none

    column BudgetRegion
        dataType: string
        lineageTag: 07613485-f793-4dc3-a1d7-407a8248510f
        sourceColumn: BudgetRegion
        summarizeBy: none

    column BudgetCategory
        dataType: string
        lineageTag: 92db38ca-a782-4722-90a5-dc1b59ecc013
        sourceColumn: BudgetCategory
        summarizeBy: none

    column BudgetAmount
        dataType: string
        lineageTag: c021c3b5-e9bc-4b65-806e-62ef6e15b9da
        sourceColumn: BudgetAmount
        summarizeBy: none

    column ForecastAmount
        dataType: string
        lineageTag: 4dc16154-231c-40f1-b597-a616a51d51c5
        sourceColumn: ForecastAmount
        summarizeBy: none

    column 'BudgetVariance' = [ForecastAmount] - [BudgetAmount]
        dataType: string
        lineageTag: d3fbd016-3307-4ca4-9734-c2db6c72ecf2

    column 'VariancePct' = IF [BudgetAmount] > 0 THEN ([ForecastAmount] - [BudgetAmount]) / [BudgetAmount] * 100 ELSE 0 END
        dataType: string
        lineageTag: d058e63e-b62d-4fc2-b618-7a11cfc4e514
```

#### `definition/tables/Channel.tmdl`

```
table Channel
    lineageTag: 43ad66df-f1d2-407a-aedc-669af7adba37

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
    lineageTag: 18c14408-1781-4b79-83ee-bfa8d97874bf

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
        lineageTag: 35577649-13ed-406d-958e-cfb5e9d4a340

    column 'EUR' = @CALCMBR(USD, @XREF(ExchangeRates, EUR_Rate))
        dataType: string
        lineageTag: cb1e262b-3c54-4507-86f5-c8cf5a654849

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
    lineageTag: 43f39742-041c-480e-b0ca-c3c6b3e0f643

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
        lineageTag: 5c8914bc-f6fa-41c1-9b33-d2bf94752d06

    column 'Segment' = "DIM_CUSTOMER"."SEGMENT"
        dataType: string
        lineageTag: f48dca25-35c2-4f73-bd9b-75223d13060e

    column 'Region' = "DIM_CUSTOMER"."REGION"
        dataType: string
        lineageTag: 405833e8-ce80-487e-a268-b23facb0a446

    column 'Country' = "DIM_CUSTOMER"."COUNTRY"
        dataType: string
        lineageTag: 4f6bae13-6860-4e6d-97c1-86791afe96fc

    column 'City' = "DIM_CUSTOMER"."CITY"
        dataType: string
        lineageTag: 76975c5d-881a-40f4-b0b8-aeef38351a6c

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
    lineageTag: aeb177f1-78c8-4d04-b7cb-65b8dbc0d597

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
        lineageTag: 081b6a56-303f-4832-a736-2778c151abd9

    column 'Customer Name' = "CUSTOMERS"."CUST_NAME"
        dataType: string
        lineageTag: bcc36ef1-bd02-4f62-9481-f3eb76a39c81

    column 'Region' = "CUSTOMERS"."REGION"
        dataType: string
        lineageTag: 8befdcf0-0750-49b6-b9bc-4a6ea8152ee7
```

#### `definition/tables/DIM_Employee.tmdl`

```
table DIM_Employee
    lineageTag: fb66119b-3a47-4d92-aca8-eab38da1a376

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
        lineageTag: 38314449-b198-46b5-8b74-af30af5fd2f5

    column 'Full Name' = "EMPLOYEES"."FIRST_NAME" & ' ' & "EMPLOYEES"."LAST_NAME"
        dataType: string
        lineageTag: 312b3aa8-588a-4e25-a5e4-4c2f3f89de2f

    column 'Hire Date' = "EMPLOYEES"."HIRE_DATE"
        dataType: string
        lineageTag: 1de4c362-b882-479a-9bf6-169f7dcbf150

    column 'Department' = "DEPARTMENTS"."DEPT_NAME"
        dataType: string
        lineageTag: 5510e6ad-8fb0-4f10-a5ff-3ed151a56743

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
    lineageTag: 26318b4c-e36b-4f4f-966d-4c3e54cdc1ce

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
        lineageTag: e7ad5283-d75d-40ab-8fc9-275d08d3fb18

    column 'City' = "LOCATIONS"."CITY"
        dataType: string
        lineageTag: 6be9ff88-37dd-4c9b-892a-d60ffaf51aaf

    column 'Country' = "LOCATIONS"."COUNTRY"
        dataType: string
        lineageTag: 4a520c42-2df5-4daa-a91c-d19f3eb9bbfd

    hierarchy GeoHierarchy
        level Country
            column: Country
        level City
            column: City
```

#### `definition/tables/Enterprise_Sales.tmdl`

```
table Enterprise Sales
    lineageTag: 050b2a90-f777-49b0-b8a7-83356af7168e

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
        lineageTag: 6f8e034d-f2e5-482a-b0ba-fd94b2202fee
        sourceColumn: CustomerName
        summarizeBy: none

    column Segment
        dataType: string
        lineageTag: efdb081a-43bc-48b0-9f4c-37fdceabfc69
        sourceColumn: Segment
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: d46249ae-f01f-4b8b-ac0a-983a5bc91174
        sourceColumn: Region
        summarizeBy: none

    column Country
        dataType: string
        lineageTag: 63ffb1c0-87dc-499b-a3c1-1ab8246ba675
        sourceColumn: Country
        summarizeBy: none

    column Category
        dataType: string
        lineageTag: a27bec47-fddd-46a0-875f-934e53bc6c47
        sourceColumn: Category
        summarizeBy: none

    column Subcategory
        dataType: string
        lineageTag: d2b59773-b9a1-4c96-8564-54f3047f5c73
        sourceColumn: Subcategory
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: 5d7cc6df-efe1-4f75-ad37-48b6bbd6a70b
        sourceColumn: OrderDate
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: cefe4da7-dbd4-442d-85ca-a7993bdffe53
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column UnitPrice
        dataType: string
        lineageTag: 3b507302-2e39-4f63-b0d4-b14fdd475d4d
        sourceColumn: UnitPrice
        summarizeBy: none

    column UnitCost
        dataType: string
        lineageTag: cecf3e66-8b07-48df-985b-2c4b46b114da
        sourceColumn: UnitCost
        summarizeBy: none

    column DiscountPct
        dataType: string
        lineageTag: f2579d31-feb1-499d-b793-1ff02b3c105d
        sourceColumn: DiscountPct
        summarizeBy: none

    column 'Revenue' = [Quantity] * [UnitPrice] * (1 - [DiscountPct])
        dataType: string
        lineageTag: 4efb7a2e-2dc2-4ceb-9ff9-13f25ee51748

    column 'Profit' = [Revenue] - ([Quantity] * [UnitCost])
        dataType: string
        lineageTag: a35368f8-fedc-4f1d-92e5-d963f4131b73

    column 'ProfitMargin' = IF [Revenue] > 0 THEN [Profit] / [Revenue] ELSE 0 END
        dataType: string
        lineageTag: 6a9c3859-1fd4-4a5a-af63-fb9621a67926
```

#### `definition/tables/Entity.tmdl`

```
table Entity
    lineageTag: ee59cf5f-0c14-4ad0-9841-8db0a4bd30b7

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
    lineageTag: 3301db6f-c876-4bc8-9234-4676fb908f89

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
        lineageTag: 66d84518-a0ba-41d4-953a-85d8d03a2e38

    column 'Order Amount' = "ORDERS"."AMOUNT"
        dataType: string
        lineageTag: c7170fec-94a6-4f40-a5e6-65b5501c4bfa

    measure 'Profit' = SUM('FACT_Orders'["ORDERS"."AMOUNT"]) * 0.2
        lineageTag: ac84a243-6d60-493c-846c-de05c1d021d6
        formatString: #,0.00
        displayFolder: Measures
```

#### `definition/tables/FACT_Payroll.tmdl`

```
table FACT_Payroll
    lineageTag: 9ad6cea6-fb20-474e-bb5c-634eef2c0ee2

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
        lineageTag: b7b7a177-ce94-498c-ac06-f003a06edb9b

    column 'Gross Pay' = "PAYROLL"."GROSS_PAY"
        dataType: string
        lineageTag: 7150e80b-34ce-4ae0-83d9-400929544f37

    column 'Net Pay' = "PAYROLL"."GROSS_PAY" - "PAYROLL"."DEDUCTIONS"
        dataType: string
        lineageTag: 6f8e7426-fa12-4037-bcc4-04e9e67610a6

    measure 'Avg Salary' = AVERAGE('FACT_Payroll'["EMPLOYEES"."SALARY"])
        lineageTag: d0441844-5eae-4367-9c94-1aa0932f70f5
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures
```

#### `definition/tables/Product.tmdl`

```
table Product
    lineageTag: aacc1b8d-94fc-45df-b0b8-9c86459b903e

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
        lineageTag: a4bc9522-249b-4583-a361-40cc5b4af9f6

    column 'Category' = "DIM_PRODUCT"."CATEGORY"
        dataType: string
        lineageTag: 44bd4a95-4efd-4b9b-8d37-7743ed4957c5

    column 'Subcategory' = "DIM_PRODUCT"."SUBCATEGORY"
        dataType: string
        lineageTag: 982195a2-2a92-4b15-b40a-a6846d44a433

    column 'Brand' = "DIM_PRODUCT"."BRAND"
        dataType: string
        lineageTag: a9a27fed-9812-43ad-8f01-91f938f5a545

    column 'Margin Pct' = ("DIM_PRODUCT"."UNIT_PRICE" - "DIM_PRODUCT"."UNIT_COST") / "DIM_PRODUCT"."UNIT_PRICE" * 100
        dataType: string
        lineageTag: 06c1f147-f5dc-493e-a3fb-776fc6feddfd

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
    lineageTag: 320a978d-a82c-455c-8bda-c24a2337be28

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
        lineageTag: 0bf375e6-c911-40a7-8717-3f22b0b67ac6

    column 'Reason Code' = "FACT_RETURNS"."REASON_CODE"
        dataType: string
        lineageTag: 97387c37-1d6b-42bc-b7cc-802d04382ef3
```

#### `definition/tables/Sales.tmdl`

```
table Sales
    lineageTag: 35890a02-fb54-4d5e-9f88-37d2038d6d87

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
        lineageTag: 53335763-e8d2-478b-9193-879ab5273a5e

    measure 'Revenue' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"]))
        lineageTag: 6e0daf00-e039-43cf-ba88-963da0a80bca
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Cost' = SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])
        lineageTag: 2578ba2f-fca1-49b0-ba2a-3ec97365fe83
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Profit' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"])) - SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])
        lineageTag: f3fab71f-b9bb-438c-aa9b-9a9c8d994d40
        formatString: #,0.00
        displayFolder: Measures

    measure 'Profit Margin' = SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) = 0, 0,
    (SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"])) - SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])) / SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) * 100
)
        lineageTag: cdfaf4ca-6bfa-4b60-990a-1a5fe7fa1a6f
        formatString: #,0.00
        displayFolder: Measures

    measure 'Return Rate' = SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY"]) = 0, 0,
    SUM('Sales'["FACT_RETURNS"."RETURN_QUANTITY"]) / SUM('Sales'["FACT_SALES"."QUANTITY"]) * 100
)
        lineageTag: cf61f7b1-2a8b-407e-ab96-13f3d1d82aed
        formatString: 0.00%
        displayFolder: Measures

    measure 'Budget Variance' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) - SUM('Sales'["FACT_BUDGET"."BUDGET_AMOUNT"])
        lineageTag: 832b00de-55f0-4279-9d5e-83aed783c5b7
        formatString: #,0.00
        displayFolder: Measures
```

#### `definition/tables/Sales_DB.tmdl`

```
table Sales DB
    lineageTag: cee8660b-8b04-402c-bf43-1066cc5350ab

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
        lineageTag: 99739b50-a10e-4e85-9a42-623e693803d5
        sourceColumn: OrderID
        summarizeBy: none

    column CustomerName
        dataType: string
        lineageTag: 7d86155c-5fec-447c-a490-db4f20372d6a
        sourceColumn: CustomerName
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: 7f55cbe4-6cb7-422c-972c-6c49d16511d3
        sourceColumn: Region
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: fb6500f0-fec1-4e68-986b-175b16eeb984
        sourceColumn: OrderDate
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: 2ddc8131-41c8-43a7-a75f-30f750278805
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column Amount
        dataType: string
        lineageTag: 51f6a262-fe4e-4dfa-8fca-61a5615fa5c3
        sourceColumn: Amount
        summarizeBy: none

    column 'Revenue' = [Amount] * [Quantity]
        dataType: string
        lineageTag: 5d057743-2f8a-438a-bcfc-3bce8b8155e7
```

#### `definition/tables/Sales_Data_Warehouse.tmdl`

```
table Sales Data Warehouse
    lineageTag: de7378ac-e725-4237-a497-5c2cdb7f3ee7

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
        lineageTag: a95004e3-d0b9-4335-a036-6cfb3c2f35f7
        sourceColumn: OrderID
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: d60148f8-eba8-4b7d-a874-8dbc3fa26d86
        sourceColumn: OrderDate
        summarizeBy: none

    column Year
        dataType: int64
        lineageTag: 67481933-22fc-4737-ba91-01418e099b97
        formatString: 0
        sourceColumn: Year
        summarizeBy: none

    column Quarter
        dataType: string
        lineageTag: 58cd5ce2-9770-49d6-b04e-398e556c26a3
        sourceColumn: Quarter
        summarizeBy: none

    column Month
        dataType: string
        lineageTag: a37aa66f-697d-4f52-a0a3-5f26a2a3db75
        sourceColumn: Month
        summarizeBy: none

    column CustomerName
        dataType: string
        lineageTag: 898414ef-e160-4a4e-a7fe-42e16c48a9a9
        sourceColumn: CustomerName
        summarizeBy: none

    column Segment
        dataType: string
        lineageTag: 8e31426f-eee6-43fb-82da-72edb63a49ee
        sourceColumn: Segment
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: f004ac06-cd24-4e5b-914e-e5b422c36c53
        sourceColumn: Region
        summarizeBy: none

    column Country
        dataType: string
        lineageTag: e7fc1f1d-7af5-4a12-ae67-4eabca7a5f99
        sourceColumn: Country
        summarizeBy: none

    column State
        dataType: string
        lineageTag: 6197c3db-81b3-4b22-9e1d-30b8339af7d4
        sourceColumn: State
        summarizeBy: none

    column City
        dataType: string
        lineageTag: 2f08d964-99f2-49fe-be67-d5b351eab3a3
        sourceColumn: City
        summarizeBy: none

    column Category
        dataType: string
        lineageTag: ea474830-b0fc-4565-bcdb-1cd09e326ea6
        sourceColumn: Category
        summarizeBy: none

    column Subcategory
        dataType: string
        lineageTag: 12e53dfa-d5ca-45bd-ab71-d8ed12cb5b01
        sourceColumn: Subcategory
        summarizeBy: none

    column Brand
        dataType: string
        lineageTag: 8df6d8fe-d982-4123-a06c-e35662857708
        sourceColumn: Brand
        summarizeBy: none

    column ProductName
        dataType: string
        lineageTag: 2ad94251-4a01-4dc0-958e-e37a4e6ce744
        sourceColumn: ProductName
        summarizeBy: none

    column StoreName
        dataType: string
        lineageTag: 15ec47da-2f43-4a87-ada6-59dcec926109
        sourceColumn: StoreName
        summarizeBy: none

    column StoreType
        dataType: string
        lineageTag: cc54aab6-6e51-4e26-bf20-23a47dfb1179
        sourceColumn: StoreType
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: ea1749a7-90cf-4628-a7ca-4f792bb9c0d8
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column UnitPrice
        dataType: string
        lineageTag: a835ed34-3a74-4826-869e-0b7bf16050fe
        sourceColumn: UnitPrice
        summarizeBy: none

    column UnitCost
        dataType: string
        lineageTag: dccd0094-0b5f-45fe-adbc-9c1857d1eef5
        sourceColumn: UnitCost
        summarizeBy: none

    column DiscountPct
        dataType: string
        lineageTag: 575b746e-55e6-4a29-8dbf-6614b1a1fddf
        sourceColumn: DiscountPct
        summarizeBy: none

    column TaxAmount
        dataType: string
        lineageTag: 98103f4d-53f3-437d-afb9-51a05e7cd56d
        sourceColumn: TaxAmount
        summarizeBy: none

    column FreightCost
        dataType: string
        lineageTag: bacfe68f-7f0b-4898-bb0d-f434caa23d37
        sourceColumn: FreightCost
        summarizeBy: none

    column 'Revenue' = [Quantity] * [UnitPrice] * (1 - [DiscountPct])
        dataType: string
        lineageTag: 5849551c-d165-4d93-9352-282bd82aa019

    column 'TotalCost' = [Quantity] * [UnitCost] + [TaxAmount] + [FreightCost]
        dataType: string
        lineageTag: a7090dcb-c690-4c8a-8378-c91dcb81fc05

    column 'Profit' = [Revenue] - [TotalCost]
        dataType: string
        lineageTag: 77c1d2de-f238-4488-a116-a102a10e72a1

    column 'ProfitMargin' = IF [Revenue] > 0 THEN [Profit] / [Revenue] * 100 ELSE 0 END
        dataType: string
        lineageTag: ff76f95e-39cb-4cac-8ba4-3d49aa81676a

    column 'DiscountAmount' = [Quantity] * [UnitPrice] * [DiscountPct]
        dataType: string
        lineageTag: 7ccc4be6-05c3-4afc-acf9-6f4230dca62c

    column 'PriceCategory' = IF [UnitPrice] > 500 THEN 'Premium' ELSEIF [UnitPrice] > 100 THEN 'Mid-Range' ELSE 'Budget' END
        dataType: string
        lineageTag: 6f3ce047-fd59-496e-a2f7-050e8cc23fa3

    column 'IsHighValue' = IF [Revenue] > 5000 THEN 'Yes' ELSE 'No' END
        dataType: string
        lineageTag: a5b5f826-936c-4132-8433-6e9968debf59

    measure 'AvgOrderValue' = SUM('Sales Data Warehouse'[[Revenue]]) / COUNTD([OrderID])
        lineageTag: 4ef8a339-8c96-463d-ac1f-9827c2af7764
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
    lineageTag: c77970c3-7e21-4274-aa03-f2605f71354e

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
        lineageTag: 86e14b93-c21a-45e0-b76c-2cc2b23e1bfa

    column 'Variance Pct' = @ROUND((Actual - Budget) % Budget, 4)
        dataType: string
        lineageTag: e3200c2b-220d-429b-86e8-f30e77bb35b5

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
    lineageTag: 92613f67-e7be-4b19-85be-c018b822386c

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
        lineageTag: 1260d606-3cd4-4970-90d6-99c137aa77a0

    column 'Year' = "DIM_DATE"."YEAR"
        dataType: string
        lineageTag: 3cd93b78-76d4-4784-9a49-73b9af96f75c

    column 'Quarter' = "DIM_DATE"."QUARTER"
        dataType: string
        lineageTag: 5cc15fd4-5cf6-4a3f-bfad-33dbbf75352c

    column 'Month' = "DIM_DATE"."MONTH_NAME"
        dataType: string
        lineageTag: 89dddbae-620b-48da-ab86-0ffc7717b32b

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
    lineageTag: eaef51f7-4b7c-4224-9738-cc34f8ea4575
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
| Elapsed time | 0.4s |

---

*Report generated by OAC-to-Fabric Migration Accelerator*