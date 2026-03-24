# Migration Report

> **Generated:** 2026-03-24 14:07:15 UTC  
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
    "logicalId": "9c205efd-e67f-4284-94af-d21cf043abd0"
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
    lineageTag: 93b17c6a-043f-443d-b982-d739044bfb05
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
    lineageTag: 1823207c-d9a6-46e7-8704-872e791265f8

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
        lineageTag: 82d6b7f0-531b-41b6-a7ba-87892f95a114

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
    lineageTag: 886296c6-ae7a-4990-922e-23630fe3dd19

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
        lineageTag: 92d924bd-adbf-4d81-8e98-0fb37619e3b0
```

#### `definition/tables/Budget_&_Forecast.tmdl`

```
table Budget & Forecast
    lineageTag: a41f9acb-b109-4268-b922-657fcf4ee031

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
        lineageTag: fa8c715e-a13b-447e-9ba7-34f52a670c93
        sourceColumn: BudgetMonth
        summarizeBy: none

    column BudgetRegion
        dataType: string
        lineageTag: 84cc7946-be9b-49d7-8534-d177a7f8ed7b
        sourceColumn: BudgetRegion
        summarizeBy: none

    column BudgetCategory
        dataType: string
        lineageTag: 5b3dcbd3-d0a2-4053-b4e3-6f4d0580e8ff
        sourceColumn: BudgetCategory
        summarizeBy: none

    column BudgetAmount
        dataType: string
        lineageTag: 388d261e-9c5a-46ed-ab25-7792b8601ed0
        sourceColumn: BudgetAmount
        summarizeBy: none

    column ForecastAmount
        dataType: string
        lineageTag: 754cee71-b919-4eb1-95bc-56819d2363f7
        sourceColumn: ForecastAmount
        summarizeBy: none

    column 'BudgetVariance' = [ForecastAmount] - [BudgetAmount]
        dataType: string
        lineageTag: ac86ca35-e605-48ba-9763-a260c2bff1d1

    column 'VariancePct' = IF [BudgetAmount] > 0 THEN ([ForecastAmount] - [BudgetAmount]) / [BudgetAmount] * 100 ELSE 0 END
        dataType: string
        lineageTag: 7703562e-e553-4c59-b5dc-17939b562219
```

#### `definition/tables/Channel.tmdl`

```
table Channel
    lineageTag: 5e39a835-0cf9-417d-b099-341be5281a24

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
    lineageTag: c365b237-c638-4ffb-ad8c-e7b2c114c9e5

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
        lineageTag: 00d3d329-182b-4135-8bd0-f6d2abb1f64e

    column 'EUR' = @CALCMBR(USD, @XREF(ExchangeRates, EUR_Rate))
        dataType: string
        lineageTag: 52c7a8e5-2629-4f02-b867-e9c02abc0eeb

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
    lineageTag: f0df7461-d57e-4dd8-a3a2-9ecff3c4f474

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
        lineageTag: 700ba8ae-4da8-4f6c-bb82-412e48aa45b8

    column 'Segment' = "DIM_CUSTOMER"."SEGMENT"
        dataType: string
        lineageTag: c4b6a30d-9618-43d8-82bc-ec30393291f6

    column 'Region' = "DIM_CUSTOMER"."REGION"
        dataType: string
        lineageTag: 7ffc76d0-7baf-40e4-a38e-817065f24791

    column 'Country' = "DIM_CUSTOMER"."COUNTRY"
        dataType: string
        lineageTag: 876bdc13-04ce-4a78-a321-d7ed8874ee69

    column 'City' = "DIM_CUSTOMER"."CITY"
        dataType: string
        lineageTag: a187a14f-bd31-480e-a803-eb086d91b934

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
    lineageTag: 88c71d7d-5ed9-4087-bafd-4618d087bb81

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
        lineageTag: a30938cb-3cbc-4410-bc71-40fed9473fbf

    column 'Customer Name' = "CUSTOMERS"."CUST_NAME"
        dataType: string
        lineageTag: 1a97cc2f-4c2a-45e5-b52a-0997c1426bac

    column 'Region' = "CUSTOMERS"."REGION"
        dataType: string
        lineageTag: 0c8a43a3-ebd0-4b40-b32c-8aef4ae97d56
```

#### `definition/tables/DIM_Employee.tmdl`

```
table DIM_Employee
    lineageTag: dea6a372-4d55-4d16-a0f2-8f32f8926baa

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
        lineageTag: b3c7d455-2432-4ac4-9278-5b095a7a6641

    column 'Full Name' = "EMPLOYEES"."FIRST_NAME" & ' ' & "EMPLOYEES"."LAST_NAME"
        dataType: string
        lineageTag: 59914261-3ca6-488c-bde7-92d98f911864

    column 'Hire Date' = "EMPLOYEES"."HIRE_DATE"
        dataType: string
        lineageTag: df7d4a7f-50da-4fb0-bb22-573d22b24fa0

    column 'Department' = "DEPARTMENTS"."DEPT_NAME"
        dataType: string
        lineageTag: 52854f18-96d7-48c2-90e4-0ba2b145eb2d

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
    lineageTag: 64c1cc32-4f4a-4066-8177-9a1da9bec61e

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
        lineageTag: 16ab0b54-7695-4d9a-b7ce-39cbabb307c4

    column 'City' = "LOCATIONS"."CITY"
        dataType: string
        lineageTag: 945f20b4-699a-4b21-b61f-13b4be50630f

    column 'Country' = "LOCATIONS"."COUNTRY"
        dataType: string
        lineageTag: 08cf4f95-21c6-4224-b17b-427001a1a13d

    hierarchy GeoHierarchy
        level Country
            column: Country
        level City
            column: City
```

#### `definition/tables/Enterprise_Sales.tmdl`

```
table Enterprise Sales
    lineageTag: 2c938af0-63ca-4952-a621-d5629eb8f1f5

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
        lineageTag: c80b6be0-2086-4aee-8d1b-e2ef7f63c6ee
        sourceColumn: CustomerName
        summarizeBy: none

    column Segment
        dataType: string
        lineageTag: 3c3e4b64-e2fe-409f-8bd9-139510ac321e
        sourceColumn: Segment
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: dc169bb1-5da4-4d7b-94b2-8d7c4b46ea07
        sourceColumn: Region
        summarizeBy: none

    column Country
        dataType: string
        lineageTag: de733152-4e58-444f-bd97-2bb6ee2eb767
        sourceColumn: Country
        summarizeBy: none

    column Category
        dataType: string
        lineageTag: 0a7d310e-221d-447b-8953-1a10a9b25507
        sourceColumn: Category
        summarizeBy: none

    column Subcategory
        dataType: string
        lineageTag: 745f34e5-e23c-4294-bc26-2b3e1efa5f6d
        sourceColumn: Subcategory
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: 66594036-513c-4c3b-bbd3-d6a48ef31188
        sourceColumn: OrderDate
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: 417b2bcc-435b-46a4-81b8-f7ee0a0af20e
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column UnitPrice
        dataType: string
        lineageTag: 7e759e0e-73d2-441d-a8a3-dc705d693920
        sourceColumn: UnitPrice
        summarizeBy: none

    column UnitCost
        dataType: string
        lineageTag: f251ca03-2dc5-444d-bec3-e6a2bf972eb2
        sourceColumn: UnitCost
        summarizeBy: none

    column DiscountPct
        dataType: string
        lineageTag: 14f2a4f0-62b5-4bfa-8613-b44dd9b60266
        sourceColumn: DiscountPct
        summarizeBy: none

    column 'Revenue' = [Quantity] * [UnitPrice] * (1 - [DiscountPct])
        dataType: string
        lineageTag: 4c534aa2-7b08-48fc-a98d-caeaef7ddac7

    column 'Profit' = [Revenue] - ([Quantity] * [UnitCost])
        dataType: string
        lineageTag: 0556a56a-9695-4456-858c-2955954f0206

    column 'ProfitMargin' = IF [Revenue] > 0 THEN [Profit] / [Revenue] ELSE 0 END
        dataType: string
        lineageTag: 90a788c3-b6ff-4137-9f39-321a5ed10cfd
```

#### `definition/tables/Entity.tmdl`

```
table Entity
    lineageTag: aad69846-e923-4664-9972-22db5bb54f13

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
    lineageTag: 9a143a85-6e81-4047-8e7f-49844235e42a

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
        lineageTag: fd54aa87-64ce-42a1-9351-368306bb7e9e

    column 'Order Amount' = "ORDERS"."AMOUNT"
        dataType: string
        lineageTag: 02bc1008-4650-431e-a68c-160c07b5298a

    measure 'Profit' = SUM('FACT_Orders'["ORDERS"."AMOUNT"]) * 0.2
        lineageTag: a121d35c-c501-4b80-8cbd-37e28dfcb25a
        formatString: #,0.00
        displayFolder: Measures
```

#### `definition/tables/FACT_Payroll.tmdl`

```
table FACT_Payroll
    lineageTag: 9065b9c9-6603-4c33-b675-f47399d5f743

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
        lineageTag: a439e680-96d8-40bf-8bfe-f1ece89402b2

    column 'Gross Pay' = "PAYROLL"."GROSS_PAY"
        dataType: string
        lineageTag: 659e6e93-cb0b-4a29-b626-8a85adf20840

    column 'Net Pay' = "PAYROLL"."GROSS_PAY" - "PAYROLL"."DEDUCTIONS"
        dataType: string
        lineageTag: f94deae8-5ba9-4d63-8cc6-b9ea79b11a02

    measure 'Avg Salary' = AVERAGE('FACT_Payroll'["EMPLOYEES"."SALARY"])
        lineageTag: 81fc9e58-fe2b-40d3-9523-0e2027e8c1cf
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures
```

#### `definition/tables/Product.tmdl`

```
table Product
    lineageTag: d1b638a0-d22f-4be3-a0dc-781e02c92d06

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
        lineageTag: 990f3c13-6896-4dd2-8763-a33469417030

    column 'Category' = "DIM_PRODUCT"."CATEGORY"
        dataType: string
        lineageTag: 1b39dd39-1f47-4cc0-bed4-83134bb9bef0

    column 'Subcategory' = "DIM_PRODUCT"."SUBCATEGORY"
        dataType: string
        lineageTag: 56d872c6-ac40-49d2-9296-30c6e9c6daac

    column 'Brand' = "DIM_PRODUCT"."BRAND"
        dataType: string
        lineageTag: 4010fe8d-ee53-41e4-befd-8d2b487af89a

    column 'Margin Pct' = ("DIM_PRODUCT"."UNIT_PRICE" - "DIM_PRODUCT"."UNIT_COST") / "DIM_PRODUCT"."UNIT_PRICE" * 100
        dataType: string
        lineageTag: 00e5b4af-a5aa-40ac-961d-c31a47a20318

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
    lineageTag: e1ce3956-74a1-4ab3-a88c-9640c6fa3627

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
        lineageTag: 1e6a9f8c-e693-4376-93f1-63d379db2e13

    column 'Reason Code' = "FACT_RETURNS"."REASON_CODE"
        dataType: string
        lineageTag: b3822b64-256c-4ac3-8e6c-bf18ab83bab2
```

#### `definition/tables/Sales.tmdl`

```
table Sales
    lineageTag: db27fbb1-1659-4f22-8a55-30a44c241f33

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
        lineageTag: d333713c-b1d3-4ae4-9d36-e54d0c0ac0ad

    measure 'Revenue' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"]))
        lineageTag: eeb02e30-bc6c-44d1-9276-9556ff9a1b2b
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Cost' = SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])
        lineageTag: 980c5e1a-890c-4ffd-9a93-ac8ef7c91c9d
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Profit' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"])) - SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])
        lineageTag: 6387ffe2-351c-4f1e-b387-f57559651fbe
        formatString: #,0.00
        displayFolder: Measures

    measure 'Profit Margin' = SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) = 0, 0,
    (SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"])) - SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])) / SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) * 100
)
        lineageTag: 4e877ba4-1073-4b47-9ece-f00b2950f567
        formatString: #,0.00
        displayFolder: Measures

    measure 'Return Rate' = SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY"]) = 0, 0,
    SUM('Sales'["FACT_RETURNS"."RETURN_QUANTITY"]) / SUM('Sales'["FACT_SALES"."QUANTITY"]) * 100
)
        lineageTag: 7021524a-89a8-46a8-859c-277af623f8ce
        formatString: 0.00%
        displayFolder: Measures

    measure 'Budget Variance' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) - SUM('Sales'["FACT_BUDGET"."BUDGET_AMOUNT"])
        lineageTag: 322579e9-da98-4bce-9494-a8127b9bf7d5
        formatString: #,0.00
        displayFolder: Measures
```

#### `definition/tables/Sales_DB.tmdl`

```
table Sales DB
    lineageTag: c0ffc797-ee68-487f-96d5-46fe10610d1b

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
        lineageTag: 34ff0230-cd5f-44ba-a126-608ecd48b498
        sourceColumn: OrderID
        summarizeBy: none

    column CustomerName
        dataType: string
        lineageTag: 527bb750-9457-4fa8-af9c-69e8ccd44384
        sourceColumn: CustomerName
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: a3a0ab1e-4d3a-44cf-beed-f0ce1e62c075
        sourceColumn: Region
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: 02c9dddd-899c-4133-8ed5-d5ae94eccbc6
        sourceColumn: OrderDate
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: 9b54b649-ee6a-4af1-a001-8a82a9e07b62
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column Amount
        dataType: string
        lineageTag: f0ebff62-0d7c-4d02-9408-fe842665254c
        sourceColumn: Amount
        summarizeBy: none

    column 'Revenue' = [Amount] * [Quantity]
        dataType: string
        lineageTag: 6631b27f-3d48-476a-a5da-b0042388f452
```

#### `definition/tables/Sales_Data_Warehouse.tmdl`

```
table Sales Data Warehouse
    lineageTag: 1d63976f-5866-405c-8674-5c2bd56f10f1

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
        lineageTag: 02285f4b-09fa-4577-b50a-5c585faa8705
        sourceColumn: OrderID
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: ba393743-22f8-46ff-ab3a-642df2e981c4
        sourceColumn: OrderDate
        summarizeBy: none

    column Year
        dataType: int64
        lineageTag: c36e3d5a-9300-4e0f-b537-0408107c76d7
        formatString: 0
        sourceColumn: Year
        summarizeBy: none

    column Quarter
        dataType: string
        lineageTag: 99f5bcc9-ddbd-4b3e-8d04-28ff7ed67006
        sourceColumn: Quarter
        summarizeBy: none

    column Month
        dataType: string
        lineageTag: a3d9c96c-1952-4576-b96d-64ba0a2136ca
        sourceColumn: Month
        summarizeBy: none

    column CustomerName
        dataType: string
        lineageTag: 7fbccdfc-5c6d-40d2-b39d-d65e08a6eb51
        sourceColumn: CustomerName
        summarizeBy: none

    column Segment
        dataType: string
        lineageTag: 3deb6a26-f26b-4126-bf56-20407a1ba216
        sourceColumn: Segment
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: d54b1577-b719-4bac-8e36-bf4d17e7c065
        sourceColumn: Region
        summarizeBy: none

    column Country
        dataType: string
        lineageTag: 9cd9b38e-29a3-49ac-88bd-64305d95632b
        sourceColumn: Country
        summarizeBy: none

    column State
        dataType: string
        lineageTag: 311a95dd-c7ba-463d-b2da-94e57fddfcb5
        sourceColumn: State
        summarizeBy: none

    column City
        dataType: string
        lineageTag: 8867a08b-86d9-4f1b-9ebd-f98f1cc09bb0
        sourceColumn: City
        summarizeBy: none

    column Category
        dataType: string
        lineageTag: 7640f7b4-ede5-4dc0-bbb9-93a3efd85add
        sourceColumn: Category
        summarizeBy: none

    column Subcategory
        dataType: string
        lineageTag: 34967d37-b957-4562-95a7-866079209ae4
        sourceColumn: Subcategory
        summarizeBy: none

    column Brand
        dataType: string
        lineageTag: d37089b6-e0ab-4e42-9c58-d5cdd686f934
        sourceColumn: Brand
        summarizeBy: none

    column ProductName
        dataType: string
        lineageTag: bda1eae9-c2fb-4f88-818b-13cd96ce2eee
        sourceColumn: ProductName
        summarizeBy: none

    column StoreName
        dataType: string
        lineageTag: 102132e2-23c0-4939-996e-7b0f5f24545f
        sourceColumn: StoreName
        summarizeBy: none

    column StoreType
        dataType: string
        lineageTag: 356036df-fa4a-4e16-b510-5489603ce268
        sourceColumn: StoreType
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: 8bac327e-83e6-4acc-90ea-293191ed07f7
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column UnitPrice
        dataType: string
        lineageTag: dbcb5def-c4b1-462a-922b-2f137634c682
        sourceColumn: UnitPrice
        summarizeBy: none

    column UnitCost
        dataType: string
        lineageTag: 0be6b138-8743-4d37-ad20-1280ae433f51
        sourceColumn: UnitCost
        summarizeBy: none

    column DiscountPct
        dataType: string
        lineageTag: b7e114ff-b977-405c-96e4-905f8e9aa69c
        sourceColumn: DiscountPct
        summarizeBy: none

    column TaxAmount
        dataType: string
        lineageTag: 2026ce79-2e30-4886-ac00-34861f7d86bf
        sourceColumn: TaxAmount
        summarizeBy: none

    column FreightCost
        dataType: string
        lineageTag: f7520ce1-14c1-4768-a816-91a0008fcb5b
        sourceColumn: FreightCost
        summarizeBy: none

    column 'Revenue' = [Quantity] * [UnitPrice] * (1 - [DiscountPct])
        dataType: string
        lineageTag: 1c61a753-e154-4dac-8dec-02640b5cc596

    column 'TotalCost' = [Quantity] * [UnitCost] + [TaxAmount] + [FreightCost]
        dataType: string
        lineageTag: 3533f1d3-3fec-47e1-84f5-129d13be049e

    column 'Profit' = [Revenue] - [TotalCost]
        dataType: string
        lineageTag: d9d5c611-3ded-4ec8-bea6-9e595c158dd6

    column 'ProfitMargin' = IF [Revenue] > 0 THEN [Profit] / [Revenue] * 100 ELSE 0 END
        dataType: string
        lineageTag: 9bc39d06-6661-4337-be14-1affd32faa6d

    column 'DiscountAmount' = [Quantity] * [UnitPrice] * [DiscountPct]
        dataType: string
        lineageTag: 833a52a3-5d66-448d-b2e6-3d2fe5f59b7e

    column 'PriceCategory' = IF [UnitPrice] > 500 THEN 'Premium' ELSEIF [UnitPrice] > 100 THEN 'Mid-Range' ELSE 'Budget' END
        dataType: string
        lineageTag: 1e1fa608-5834-4fd3-9733-b45700708e15

    column 'IsHighValue' = IF [Revenue] > 5000 THEN 'Yes' ELSE 'No' END
        dataType: string
        lineageTag: e1edb6ee-c95f-4717-bade-bfe8fc17e69d

    measure 'AvgOrderValue' = SUM('Sales Data Warehouse'[[Revenue]]) / COUNTD([OrderID])
        lineageTag: 860fc0b0-8610-4f91-be80-a33cde76d72f
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
    lineageTag: 093fcd6e-4844-4270-97a5-71248e1dff06

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
        lineageTag: 763698c4-5e95-4825-9b9f-9fd1e8cf890d

    column 'Variance Pct' = @ROUND((Actual - Budget) % Budget, 4)
        dataType: string
        lineageTag: 4dec4256-ea9d-4527-854e-53da7f7197a4

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
    lineageTag: 135c37b8-3d1e-4f26-9a3c-cbb6a64d25fe

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
        lineageTag: 9986d0f4-4591-4def-ac35-88fca20518d3

    column 'Year' = "DIM_DATE"."YEAR"
        dataType: string
        lineageTag: 372a6b9f-c507-40eb-99df-72e812060472

    column 'Quarter' = "DIM_DATE"."QUARTER"
        dataType: string
        lineageTag: c7415d6a-9aa5-46c1-ad88-65baea28d7d1

    column 'Month' = "DIM_DATE"."MONTH_NAME"
        dataType: string
        lineageTag: 06cb4145-c826-47bc-94c8-5988f3bc5aa3

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
    lineageTag: 6816e837-57fb-4359-81b8-a31c17ea561a
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