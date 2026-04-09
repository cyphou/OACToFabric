# Migration Report

> **Generated:** 2026-04-08 11:06:05 UTC  
> **Total assets discovered:** 250  
> **Elapsed time:** 0.7s  
> **Output directory:** `output\migration_report`

---

## 1. Discovery Summary

### Assets by Source Platform

| Source | Assets | Types |
|--------|--------|-------|
| **cognos** | 18 | analysis, dataModel, prompt |
| **essbase** | 15 | logicalTable |
| **oac_api** | 34 | agent, analysis, dashboard, dataModel, dataflow, filter, logicalTable, prompt |
| **qlik** | 36 | filter, physicalTable |
| **rpd** | 124 | initBlock, logicalTable, physicalTable, presentationTable, securityRole, subjectArea |
| **tableau** | 23 | analysis, dashboard, logicalTable, prompt |

### Assets by Type

| Asset Type | Count | Sources |
|------------|-------|---------|
| agent | 5 | oac_api |
| analysis | 19 | cognos, oac_api, tableau |
| dashboard | 6 | oac_api, tableau |
| dataModel | 8 | cognos, oac_api |
| dataflow | 3 | oac_api |
| filter | 20 | oac_api, qlik |
| initBlock | 6 | rpd |
| logicalTable | 51 | essbase, oac_api, rpd, tableau |
| physicalTable | 57 | qlik, rpd |
| presentationTable | 34 | rpd |
| prompt | 19 | cognos, oac_api, tableau |
| securityRole | 9 | rpd |
| subjectArea | 13 | rpd |

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
| 36 | DIM_TERRITORY | physicalTable | rpd | `/physical/DIM_TERRITORY` |
| 37 | FACT_SALES | physicalTable | rpd | `/physical/FACT_SALES` |
| 38 | FACT_FORECAST | physicalTable | rpd | `/physical/FACT_FORECAST` |
| 39 | Time | logicalTable | rpd | `/logical/Time` |
| 40 | Product | logicalTable | rpd | `/logical/Product` |
| 41 | Sales_Analytics | logicalTable | rpd | `/logical/Sales_Analytics` |
| 42 | Sales Analytics | subjectArea | rpd | `/presentation/Sales Analytics` |
| 43 | Statistical Analysis | subjectArea | rpd | `/presentation/Statistical Analysis` |
| 44 | Time Dimension | presentationTable | rpd | `/presentation/Time Dimension` |
| 45 | Product | presentationTable | rpd | `/presentation/Product` |
| 46 | Revenue Metrics | presentationTable | rpd | `/presentation/Revenue Metrics` |
| 47 | Advanced Metrics | presentationTable | rpd | `/presentation/Advanced Metrics` |
| 48 | Low Inventory Alert | agent | oac_api | `/shared/Agents/Low Inventory Alert` |
| 49 | Revenue Drop Alert | agent | oac_api | `/shared/Agents/Revenue Drop Alert` |
| 50 | ETL Failure Monitor | agent | oac_api | `/shared/Agents/ETL Failure Monitor` |
| 51 | New Customer Welcome | agent | oac_api | `/shared/Agents/New Customer Welcome` |
| 52 | Financial Report | analysis | oac_api | `/shared/Finance/Financial Report` |
| 53 | Sales Overview | analysis | oac_api | `/shared/Sales/Sales Overview` |
| 54 | Sales Overview | analysis | oac_api | `/shared/Sales/Sales Overview` |
| 55 | Executive Dashboard | dashboard | oac_api | `/shared/Dashboards/Executive Dashboard` |
| 56 | Sales Data Model | dataModel | oac_api | `/shared/Models/Sales Data Model` |
| 57 | Region Prompt | prompt | oac_api | `/shared/Sales/Region Prompt` |
| 58 | Date Range Prompt | prompt | oac_api | `/shared/Common/Date Range Prompt` |
| 59 | High Revenue Filter | filter | oac_api | `/shared/Filters/High Revenue Filter` |
| 60 | Low Inventory Alert | agent | oac_api | `/shared/Agents/Low Inventory Alert` |
| 61 | Daily Sales ETL | dataflow | oac_api | `/shared/DataFlows/Daily Sales ETL` |
| 62 | Financial Report | analysis | oac_api | `/shared/Finance/Financial Report` |
| 63 | DIM_DATE | physicalTable | rpd | `/physical/DIM_DATE` |
| 64 | DIM_PRODUCT | physicalTable | rpd | `/physical/DIM_PRODUCT` |
| 65 | DIM_CUSTOMER | physicalTable | rpd | `/physical/DIM_CUSTOMER` |
| 66 | DIM_STORE | physicalTable | rpd | `/physical/DIM_STORE` |
| 67 | DIM_CHANNEL | physicalTable | rpd | `/physical/DIM_CHANNEL` |
| 68 | FACT_SALES | physicalTable | rpd | `/physical/FACT_SALES` |
| 69 | FACT_RETURNS | physicalTable | rpd | `/physical/FACT_RETURNS` |
| 70 | FACT_BUDGET | physicalTable | rpd | `/physical/FACT_BUDGET` |
| 71 | Time | logicalTable | rpd | `/logical/Time` |
| 72 | Product | logicalTable | rpd | `/logical/Product` |
| 73 | Customer | logicalTable | rpd | `/logical/Customer` |
| 74 | Sales | logicalTable | rpd | `/logical/Sales` |
| 75 | Returns | logicalTable | rpd | `/logical/Returns` |
| 76 | Budget | logicalTable | rpd | `/logical/Budget` |
| 77 | Executive Sales | subjectArea | rpd | `/presentation/Executive Sales` |
| 78 | Product Performance | subjectArea | rpd | `/presentation/Product Performance` |
| 79 | Returns Analysis | subjectArea | rpd | `/presentation/Returns Analysis` |
| 80 | Time | presentationTable | rpd | `/presentation/Time` |
| 81 | Product | presentationTable | rpd | `/presentation/Product` |
| 82 | Customer | presentationTable | rpd | `/presentation/Customer` |
| 83 | Measures | presentationTable | rpd | `/presentation/Measures` |
| 84 | Product | presentationTable | rpd | `/presentation/Product` |
| 85 | Sales | presentationTable | rpd | `/presentation/Sales` |
| 86 | Time | presentationTable | rpd | `/presentation/Time` |
| 87 | Product | presentationTable | rpd | `/presentation/Product` |
| 88 | Returns | presentationTable | rpd | `/presentation/Returns` |
| 89 | Regional_Manager | securityRole | rpd | `/security/roles/Regional_Manager` |
| 90 | Analyst | securityRole | rpd | `/security/roles/Analyst` |
| 91 | RLS_Region | initBlock | rpd | `/security/initblocks/RLS_Region` |
| 92 | RLS_Segment | initBlock | rpd | `/security/initblocks/RLS_Segment` |
| 93 | Executive Dashboard | dashboard | oac_api | `/shared/Dashboards/Executive Dashboard` |
| 94 | Operations Command Center | dashboard | oac_api | `/shared/Dashboards/Operations Command Center` |
| 95 | Fact Sales | logicalTable | oac_api | `/oac/data_model_star_schema/Fact Sales` |
| 96 | Dim Customer | logicalTable | oac_api | `/oac/data_model_star_schema/Dim Customer` |
| 97 | Dim Product | logicalTable | oac_api | `/oac/data_model_star_schema/Dim Product` |
| 98 | Dim Date | logicalTable | oac_api | `/oac/data_model_star_schema/Dim Date` |
| 99 | Dim Geography | logicalTable | oac_api | `/oac/data_model_star_schema/Dim Geography` |
| 100 | Customer 360 Enrichment | dataflow | oac_api | `/shared/DataFlows/Customer 360 Enrichment` |
| 101 | Daily Sales ETL | dataflow | oac_api | `/shared/DataFlows/Daily Sales ETL` |
| 102 | High Revenue Filter | filter | oac_api | `/shared/Filters/High Revenue Filter` |
| 103 | Active Customers Only | filter | oac_api | `/shared/Filters/Active Customers Only` |
| 104 | Current Fiscal Year | filter | oac_api | `/shared/Filters/Current Fiscal Year` |
| 105 | Top 10 Products by Revenue | filter | oac_api | `/shared/Filters/Top 10 Products` |
| 106 | Exclude Internal Orders | filter | oac_api | `/shared/Filters/Exclude Internal Orders` |
| 107 | DIM_DATE | physicalTable | rpd | `/physical/DIM_DATE` |
| 108 | DIM_EMPLOYEE | physicalTable | rpd | `/physical/DIM_EMPLOYEE` |
| 109 | DIM_ACCOUNT | physicalTable | rpd | `/physical/DIM_ACCOUNT` |
| 110 | FACT_GL | physicalTable | rpd | `/physical/FACT_GL` |
| 111 | FACT_BUDGET | physicalTable | rpd | `/physical/FACT_BUDGET` |
| 112 | REF_EXCHANGE_RATE | physicalTable | rpd | `/physical/REF_EXCHANGE_RATE` |
| 113 | Time | logicalTable | rpd | `/logical/Time` |
| 114 | Employee | logicalTable | rpd | `/logical/Employee` |
| 115 | General_Ledger | logicalTable | rpd | `/logical/General_Ledger` |
| 116 | Employee Analytics | subjectArea | rpd | `/presentation/Employee Analytics` |
| 117 | Financial Reporting | subjectArea | rpd | `/presentation/Financial Reporting` |
| 118 | Employee Info | presentationTable | rpd | `/presentation/Employee Info` |
| 119 | GL Metrics | presentationTable | rpd | `/presentation/GL Metrics` |
| 120 | FinanceAnalyst | securityRole | rpd | `/security/roles/FinanceAnalyst` |
| 121 | HRManager | securityRole | rpd | `/security/roles/HRManager` |
| 122 | FACT_SALES | physicalTable | rpd | `/physical/FACT_SALES` |
| 123 | FACT_INVENTORY | physicalTable | rpd | `/physical/FACT_INVENTORY` |
| 124 | DIM_CUSTOMER | physicalTable | rpd | `/physical/DIM_CUSTOMER` |
| 125 | DIM_PRODUCT | physicalTable | rpd | `/physical/DIM_PRODUCT` |
| 126 | DIM_DATE | physicalTable | rpd | `/physical/DIM_DATE` |
| 127 | DIM_GEOGRAPHY | physicalTable | rpd | `/physical/DIM_GEOGRAPHY` |
| 128 | DIM_CHANNEL | physicalTable | rpd | `/physical/DIM_CHANNEL` |
| 129 | DIM_WAREHOUSE | physicalTable | rpd | `/physical/DIM_WAREHOUSE` |
| 130 | DIM_EMPLOYEE | physicalTable | rpd | `/physical/DIM_EMPLOYEE` |
| 131 | FACT_GL | physicalTable | rpd | `/physical/FACT_GL` |
| 132 | Fact Sales | logicalTable | rpd | `/logical/Fact Sales` |
| 133 | Fact Inventory | logicalTable | rpd | `/logical/Fact Inventory` |
| 134 | Fact GL | logicalTable | rpd | `/logical/Fact GL` |
| 135 | Dim Customer | logicalTable | rpd | `/logical/Dim Customer` |
| 136 | Dim Product | logicalTable | rpd | `/logical/Dim Product` |
| 137 | Dim Date | logicalTable | rpd | `/logical/Dim Date` |
| 138 | Dim Geography | logicalTable | rpd | `/logical/Dim Geography` |
| 139 | Dim Channel | logicalTable | rpd | `/logical/Dim Channel` |
| 140 | Dim Warehouse | logicalTable | rpd | `/logical/Dim Warehouse` |
| 141 | Dim Employee | logicalTable | rpd | `/logical/Dim Employee` |
| 142 | SampleApp | subjectArea | rpd | `/presentation/SampleApp` |
| 143 | Operations Analytics | subjectArea | rpd | `/presentation/Operations Analytics` |
| 144 | Financial Analytics | subjectArea | rpd | `/presentation/Financial Analytics` |
| 145 | Revenue | presentationTable | rpd | `/presentation/Revenue` |
| 146 | Customers | presentationTable | rpd | `/presentation/Customers` |
| 147 | Products | presentationTable | rpd | `/presentation/Products` |
| 148 | Time | presentationTable | rpd | `/presentation/Time` |
| 149 | Geography | presentationTable | rpd | `/presentation/Geography` |
| 150 | Channel | presentationTable | rpd | `/presentation/Channel` |
| 151 | Inventory | presentationTable | rpd | `/presentation/Inventory` |
| 152 | Warehouse | presentationTable | rpd | `/presentation/Warehouse` |
| 153 | Products | presentationTable | rpd | `/presentation/Products` |
| 154 | General Ledger | presentationTable | rpd | `/presentation/General Ledger` |
| 155 | Time | presentationTable | rpd | `/presentation/Time` |
| 156 | HR | presentationTable | rpd | `/presentation/HR` |
| 157 | Admin | securityRole | rpd | `/security/roles/Admin` |
| 158 | SalesAnalyst | securityRole | rpd | `/security/roles/SalesAnalyst` |
| 159 | FinanceManager | securityRole | rpd | `/security/roles/FinanceManager` |
| 160 | OperationsViewer | securityRole | rpd | `/security/roles/OperationsViewer` |
| 161 | Set User Region | initBlock | rpd | `/security/initblocks/Set User Region` |
| 162 | Set User ID | initBlock | rpd | `/security/initblocks/Set User ID` |
| 163 | Set Fiscal Year | initBlock | rpd | `/security/initblocks/Set Fiscal Year` |
| 164 | EMPLOYEES | physicalTable | rpd | `/physical/EMPLOYEES` |
| 165 | DEPARTMENTS | physicalTable | rpd | `/physical/DEPARTMENTS` |
| 166 | LOCATIONS | physicalTable | rpd | `/physical/LOCATIONS` |
| 167 | PAYROLL | physicalTable | rpd | `/physical/PAYROLL` |
| 168 | DIM_Employee | logicalTable | rpd | `/logical/DIM_Employee` |
| 169 | DIM_Location | logicalTable | rpd | `/logical/DIM_Location` |
| 170 | FACT_Payroll | logicalTable | rpd | `/logical/FACT_Payroll` |
| 171 | HR Analytics | subjectArea | rpd | `/presentation/HR Analytics` |
| 172 | Compensation Review | subjectArea | rpd | `/presentation/Compensation Review` |
| 173 | Employees | presentationTable | rpd | `/presentation/Employees` |
| 174 | Locations | presentationTable | rpd | `/presentation/Locations` |
| 175 | Payroll | presentationTable | rpd | `/presentation/Payroll` |
| 176 | Employees | presentationTable | rpd | `/presentation/Employees` |
| 177 | Compensation | presentationTable | rpd | `/presentation/Compensation` |
| 178 | HR_Manager | securityRole | rpd | `/security/roles/HR_Manager` |
| 179 | RLS_Department | initBlock | rpd | `/security/initblocks/RLS_Department` |
| 180 | Region Prompt | prompt | oac_api | `/shared/Sales/Region Prompt` |
| 181 | Date Range Prompt | prompt | oac_api | `/shared/Common/Date Range Prompt` |
| 182 | Cost Center Prompt | prompt | oac_api | `/shared/Finance/Cost Center Prompt` |
| 183 | Product Category Prompt | prompt | oac_api | `/shared/Sales/Product Category Prompt` |
| 184 | Warehouse Prompt | prompt | oac_api | `/shared/Operations/Warehouse Prompt` |
| 185 | CUSTOMERS | physicalTable | rpd | `/physical/CUSTOMERS` |
| 186 | ORDERS | physicalTable | rpd | `/physical/ORDERS` |
| 187 | DIM_Customer | logicalTable | rpd | `/logical/DIM_Customer` |
| 188 | FACT_Orders | logicalTable | rpd | `/logical/FACT_Orders` |
| 189 | Sales Analysis | subjectArea | rpd | `/presentation/Sales Analysis` |
| 190 | Customer | presentationTable | rpd | `/presentation/Customer` |
| 191 | Orders | presentationTable | rpd | `/presentation/Orders` |
| 192 | vToday | filter | qlik | `/qlik/complex_pipeline/variables/vToday` |
| 193 | vThisYear | filter | qlik | `/qlik/complex_pipeline/variables/vThisYear` |
| 194 | vLastYear | filter | qlik | `/qlik/complex_pipeline/variables/vLastYear` |
| 195 | vCurrencyRate | filter | qlik | `/qlik/complex_pipeline/variables/vCurrencyRate` |
| 196 | vRevenueThreshold | filter | qlik | `/qlik/complex_pipeline/variables/vRevenueThreshold` |
| 197 | vQuarter | filter | qlik | `/qlik/complex_pipeline/variables/vQuarter` |
| 198 | vDateFormat | filter | qlik | `/qlik/complex_pipeline/variables/vDateFormat` |
| 199 | vDataPath | filter | qlik | `/qlik/complex_pipeline/variables/vDataPath` |
| 200 | vArchivePath | filter | qlik | `/qlik/complex_pipeline/variables/vArchivePath` |
| 201 | unnamed_load | physicalTable | qlik | `/qlik/complex_pipeline/unnamed_load` |
| 202 | RegionMapping | physicalTable | qlik | `/qlik/complex_pipeline/RegionMapping` |
| 203 | Stores | physicalTable | qlik | `/qlik/complex_pipeline/Stores` |
| 204 | Channels | physicalTable | qlik | `/qlik/complex_pipeline/Channels` |
| 205 | OrderEnriched | physicalTable | qlik | `/qlik/complex_pipeline/OrderEnriched` |
| 206 | CustomerSummary | physicalTable | qlik | `/qlik/complex_pipeline/CustomerSummary` |
| 207 | ProductPerformance | physicalTable | qlik | `/qlik/complex_pipeline/ProductPerformance` |
| 208 | Returns | physicalTable | qlik | `/qlik/complex_pipeline/Returns` |
| 209 | Budget | physicalTable | qlik | `/qlik/complex_pipeline/Budget` |
| 210 | dim_customer | physicalTable | qlik | `/qlik/complex_pipeline/dim_customer` |
| 211 | dim_product | physicalTable | qlik | `/qlik/complex_pipeline/dim_product` |
| 212 | fact_orders | physicalTable | qlik | `/qlik/complex_pipeline/fact_orders` |
| 213 | vToday | filter | qlik | `/qlik/medium_etl/variables/vToday` |
| 214 | vThisYear | filter | qlik | `/qlik/medium_etl/variables/vThisYear` |
| 215 | vThreshold | filter | qlik | `/qlik/medium_etl/variables/vThreshold` |
| 216 | vLastMonth | filter | qlik | `/qlik/medium_etl/variables/vLastMonth` |
| 217 | unnamed_load | physicalTable | qlik | `/qlik/medium_etl/unnamed_load` |
| 218 | Regions | physicalTable | qlik | `/qlik/medium_etl/Regions` |
| 219 | OrderSummary | physicalTable | qlik | `/qlik/medium_etl/OrderSummary` |
| 220 | Products | physicalTable | qlik | `/qlik/medium_etl/Products` |
| 221 | dim_customer | physicalTable | qlik | `/qlik/medium_etl/dim_customer` |
| 222 | fact_orders | physicalTable | qlik | `/qlik/medium_etl/fact_orders` |
| 223 | vToday | filter | qlik | `/qlik/simple_load/variables/vToday` |
| 224 | unnamed_load | physicalTable | qlik | `/qlik/simple_load/unnamed_load` |
| 225 | unnamed_load | physicalTable | qlik | `/qlik/simple_load/unnamed_load` |
| 226 | Orders | physicalTable | qlik | `/qlik/simple_load/Orders` |
| 227 | customers | physicalTable | qlik | `/qlik/simple_load/customers` |
| 228 | Sales Data Warehouse | logicalTable | tableau | `/tableau/complex_enterprise/SalesWarehouse` |
| 229 | Budget & Forecast | logicalTable | tableau | `/tableau/complex_enterprise/BudgetData` |
| 230 | Top N | prompt | tableau | `/tableau/complex_enterprise/parameters/TopNParam` |
| 231 | Start Date | prompt | tableau | `/tableau/complex_enterprise/parameters/DateRangeStart` |
| 232 | End Date | prompt | tableau | `/tableau/complex_enterprise/parameters/DateRangeEnd` |
| 233 | Metric | prompt | tableau | `/tableau/complex_enterprise/parameters/MetricSelector` |
| 234 | Revenue Trend | analysis | tableau | `/tableau/complex_enterprise/worksheets/Revenue Trend` |
| 235 | Category Breakdown | analysis | tableau | `/tableau/complex_enterprise/worksheets/Category Breakdown` |
| 236 | Geographic Analysis | analysis | tableau | `/tableau/complex_enterprise/worksheets/Geographic Analysis` |
| 237 | Customer Segments | analysis | tableau | `/tableau/complex_enterprise/worksheets/Customer Segments` |
| 238 | Top Products | analysis | tableau | `/tableau/complex_enterprise/worksheets/Top Products` |
| 239 | Budget vs Actual | analysis | tableau | `/tableau/complex_enterprise/worksheets/Budget vs Actual` |
| 240 | Executive Summary | dashboard | tableau | `/tableau/complex_enterprise/dashboards/Executive Summary` |
| 241 | Operations Detail | dashboard | tableau | `/tableau/complex_enterprise/dashboards/Operations Detail` |
| 242 | Enterprise Sales | logicalTable | tableau | `/tableau/medium_dashboard/EnterpriseSales` |
| 243 | Top N Customers | prompt | tableau | `/tableau/medium_dashboard/parameters/TopN` |
| 244 | Min Revenue Filter | prompt | tableau | `/tableau/medium_dashboard/parameters/MinRevenue` |
| 245 | Revenue by Category | analysis | tableau | `/tableau/medium_dashboard/worksheets/Revenue by Category` |
| 246 | Regional Profit | analysis | tableau | `/tableau/medium_dashboard/worksheets/Regional Profit` |
| 247 | Top Customers | analysis | tableau | `/tableau/medium_dashboard/worksheets/Top Customers` |
| 248 | Sales Overview | dashboard | tableau | `/tableau/medium_dashboard/dashboards/Sales Overview` |
| 249 | Sales DB | logicalTable | tableau | `/tableau/simple_chart/SalesDatabase` |
| 250 | Revenue by Region | analysis | tableau | `/tableau/simple_chart/worksheets/Revenue by Region` |

</details>

---

## 2. Schema Migration (DDL)

**Tables generated:** 57

| # | Table | Source | Platform |
|---|-------|--------|----------|
| 1 | `DIM_DATE` | rpd | Lakehouse (Delta) |
| 2 | `DIM_PRODUCT` | rpd | Lakehouse (Delta) |
| 3 | `DIM_TERRITORY` | rpd | Lakehouse (Delta) |
| 4 | `FACT_SALES` | rpd | Lakehouse (Delta) |
| 5 | `FACT_FORECAST` | rpd | Lakehouse (Delta) |
| 6 | `DIM_DATE` | rpd | Lakehouse (Delta) |
| 7 | `DIM_PRODUCT` | rpd | Lakehouse (Delta) |
| 8 | `DIM_CUSTOMER` | rpd | Lakehouse (Delta) |
| 9 | `DIM_STORE` | rpd | Lakehouse (Delta) |
| 10 | `DIM_CHANNEL` | rpd | Lakehouse (Delta) |
| 11 | `FACT_SALES` | rpd | Lakehouse (Delta) |
| 12 | `FACT_RETURNS` | rpd | Lakehouse (Delta) |
| 13 | `FACT_BUDGET` | rpd | Lakehouse (Delta) |
| 14 | `DIM_DATE` | rpd | Lakehouse (Delta) |
| 15 | `DIM_EMPLOYEE` | rpd | Lakehouse (Delta) |
| 16 | `DIM_ACCOUNT` | rpd | Lakehouse (Delta) |
| 17 | `FACT_GL` | rpd | Lakehouse (Delta) |
| 18 | `FACT_BUDGET` | rpd | Lakehouse (Delta) |
| 19 | `REF_EXCHANGE_RATE` | rpd | Lakehouse (Delta) |
| 20 | `FACT_SALES` | rpd | Lakehouse (Delta) |
| 21 | `FACT_INVENTORY` | rpd | Lakehouse (Delta) |
| 22 | `DIM_CUSTOMER` | rpd | Lakehouse (Delta) |
| 23 | `DIM_PRODUCT` | rpd | Lakehouse (Delta) |
| 24 | `DIM_DATE` | rpd | Lakehouse (Delta) |
| 25 | `DIM_GEOGRAPHY` | rpd | Lakehouse (Delta) |
| 26 | `DIM_CHANNEL` | rpd | Lakehouse (Delta) |
| 27 | `DIM_WAREHOUSE` | rpd | Lakehouse (Delta) |
| 28 | `DIM_EMPLOYEE` | rpd | Lakehouse (Delta) |
| 29 | `FACT_GL` | rpd | Lakehouse (Delta) |
| 30 | `EMPLOYEES` | rpd | Lakehouse (Delta) |
| 31 | `DEPARTMENTS` | rpd | Lakehouse (Delta) |
| 32 | `LOCATIONS` | rpd | Lakehouse (Delta) |
| 33 | `PAYROLL` | rpd | Lakehouse (Delta) |
| 34 | `CUSTOMERS` | rpd | Lakehouse (Delta) |
| 35 | `ORDERS` | rpd | Lakehouse (Delta) |
| 36 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 37 | `RegionMapping` | qlik | Lakehouse (Delta) |
| 38 | `Stores` | qlik | Lakehouse (Delta) |
| 39 | `Channels` | qlik | Lakehouse (Delta) |
| 40 | `OrderEnriched` | qlik | Lakehouse (Delta) |
| 41 | `CustomerSummary` | qlik | Lakehouse (Delta) |
| 42 | `ProductPerformance` | qlik | Lakehouse (Delta) |
| 43 | `Returns` | qlik | Lakehouse (Delta) |
| 44 | `Budget` | qlik | Lakehouse (Delta) |
| 45 | `dim_customer` | qlik | Lakehouse (Delta) |
| 46 | `dim_product` | qlik | Lakehouse (Delta) |
| 47 | `fact_orders` | qlik | Lakehouse (Delta) |
| 48 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 49 | `Regions` | qlik | Lakehouse (Delta) |
| 50 | `OrderSummary` | qlik | Lakehouse (Delta) |
| 51 | `Products` | qlik | Lakehouse (Delta) |
| 52 | `dim_customer` | qlik | Lakehouse (Delta) |
| 53 | `fact_orders` | qlik | Lakehouse (Delta) |
| 54 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 55 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 56 | `Orders` | qlik | Lakehouse (Delta) |
| 57 | `customers` | qlik | Lakehouse (Delta) |

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
    WEEK_NUM INT,
    DAY_OF_WEEK INT
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
    UNIT_PRICE STRING
)
USING DELTA;
```

#### `DIM_TERRITORY`

```sql
CREATE TABLE IF NOT EXISTS DIM_TERRITORY (
    TERRITORY_KEY INT,
    TERRITORY_NAME STRING,
    REGION STRING,
    COUNTRY STRING
)
USING DELTA;
```

#### `FACT_SALES`

```sql
CREATE TABLE IF NOT EXISTS FACT_SALES (
    SALES_KEY INT,
    DATE_KEY INT,
    PRODUCT_KEY INT,
    TERRITORY_KEY INT,
    QUANTITY INT,
    REVENUE STRING,
    COST STRING,
    DISCOUNT_AMOUNT STRING
)
USING DELTA;
```

#### `FACT_FORECAST`

```sql
CREATE TABLE IF NOT EXISTS FACT_FORECAST (
    FORECAST_KEY INT,
    DATE_KEY INT,
    PRODUCT_KEY INT,
    FORECAST_AMOUNT STRING
)
USING DELTA;
```

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

#### `DIM_DATE`

```sql
CREATE TABLE IF NOT EXISTS DIM_DATE (
    DATE_KEY INT,
    FULL_DATE TIMESTAMP,
    YEAR INT,
    QUARTER STRING,
    MONTH_NUM INT,
    MONTH_NAME STRING
)
USING DELTA;
```

#### `DIM_EMPLOYEE`

```sql
CREATE TABLE IF NOT EXISTS DIM_EMPLOYEE (
    EMP_KEY INT,
    FIRST_NAME STRING,
    LAST_NAME STRING,
    EMAIL STRING,
    PHONE STRING,
    HIRE_DATE TIMESTAMP,
    SALARY STRING,
    DEPARTMENT STRING,
    STATUS STRING,
    MANAGER_KEY INT,
    JOB_CODE STRING,
    NOTES STRING
)
USING DELTA;
```

#### `DIM_ACCOUNT`

```sql
CREATE TABLE IF NOT EXISTS DIM_ACCOUNT (
    ACCOUNT_KEY INT,
    ACCOUNT_NAME STRING,
    ACCOUNT_TYPE STRING,
    PARENT_ACCOUNT STRING,
    ACCOUNT_NUMBER STRING
)
USING DELTA;
```

#### `FACT_GL`

```sql
CREATE TABLE IF NOT EXISTS FACT_GL (
    GL_KEY INT,
    DATE_KEY INT,
    ACCOUNT_KEY INT,
    DEBIT_AMOUNT STRING,
    CREDIT_AMOUNT STRING,
    CURRENCY_CODE STRING,
    EXCHANGE_RATE STRING,
    DESCRIPTION STRING,
    BATCH_ID STRING
)
USING DELTA;
```

#### `FACT_BUDGET`

```sql
CREATE TABLE IF NOT EXISTS FACT_BUDGET (
    BUDGET_KEY INT,
    DATE_KEY INT,
    ACCOUNT_KEY INT,
    BUDGET_AMOUNT STRING,
    VERSION STRING
)
USING DELTA;
```

#### `REF_EXCHANGE_RATE`

```sql
CREATE TABLE IF NOT EXISTS REF_EXCHANGE_RATE (
    FROM_CURRENCY STRING,
    TO_CURRENCY STRING,
    RATE_DATE TIMESTAMP,
    RATE STRING
)
USING DELTA;
```

#### `FACT_SALES`

```sql
CREATE TABLE IF NOT EXISTS FACT_SALES (
    SALES_ID INT,
    CUSTOMER_KEY INT,
    PRODUCT_KEY INT,
    DATE_KEY INT,
    GEOGRAPHY_KEY INT,
    CHANNEL_KEY INT,
    REVENUE STRING,
    COST_AMOUNT STRING,
    QUANTITY INT,
    DISCOUNT_AMT STRING,
    ORDER_DATE TIMESTAMP
)
USING DELTA;
```

#### `FACT_INVENTORY`

```sql
CREATE TABLE IF NOT EXISTS FACT_INVENTORY (
    INVENTORY_ID INT,
    PRODUCT_KEY INT,
    WAREHOUSE_KEY INT,
    DATE_KEY INT,
    QUANTITY_ON_HAND INT,
    QUANTITY_ON_ORDER INT,
    UNIT_COST STRING
)
USING DELTA;
```

#### `DIM_CUSTOMER`

```sql
CREATE TABLE IF NOT EXISTS DIM_CUSTOMER (
    CUSTOMER_KEY INT,
    CUSTOMER_ID STRING,
    CUSTOMER_NAME STRING,
    CUSTOMER_CLASS STRING,
    INDUSTRY STRING,
    COUNTRY STRING,
    REGION STRING,
    STATUS STRING,
    CREATED_DATE TIMESTAMP
)
USING DELTA;
```

#### `DIM_PRODUCT`

```sql
CREATE TABLE IF NOT EXISTS DIM_PRODUCT (
    PRODUCT_KEY INT,
    PRODUCT_ID STRING,
    PRODUCT_NAME STRING,
    CATEGORY STRING,
    SUB_CATEGORY STRING,
    BRAND STRING,
    UNIT_PRICE STRING,
    ACTIVE_FLAG STRING,
    REORDER_POINT INT
)
USING DELTA;
```

#### `DIM_DATE`

```sql
CREATE TABLE IF NOT EXISTS DIM_DATE (
    DATE_KEY INT,
    CALENDAR_DATE TIMESTAMP,
    YEAR_NUM INT,
    QUARTER_NAME STRING,
    MONTH_NAME STRING,
    MONTH_NUM INT,
    FISCAL_YEAR STRING,
    FISCAL_PERIOD STRING
)
USING DELTA;
```

#### `DIM_GEOGRAPHY`

```sql
CREATE TABLE IF NOT EXISTS DIM_GEOGRAPHY (
    GEOGRAPHY_KEY INT,
    COUNTRY STRING,
    REGION STRING,
    STATE_PROVINCE STRING,
    CITY STRING,
    POSTAL_CODE STRING
)
USING DELTA;
```

#### `DIM_CHANNEL`

```sql
CREATE TABLE IF NOT EXISTS DIM_CHANNEL (
    CHANNEL_KEY INT,
    CHANNEL_NAME STRING,
    CHANNEL_TYPE STRING
)
USING DELTA;
```

#### `DIM_WAREHOUSE`

```sql
CREATE TABLE IF NOT EXISTS DIM_WAREHOUSE (
    WAREHOUSE_KEY INT,
    WAREHOUSE_NAME STRING,
    WAREHOUSE_REGION STRING,
    CAPACITY INT
)
USING DELTA;
```

#### `DIM_EMPLOYEE`

```sql
CREATE TABLE IF NOT EXISTS DIM_EMPLOYEE (
    EMPLOYEE_KEY INT,
    EMPLOYEE_ID STRING,
    FIRST_NAME STRING,
    LAST_NAME STRING,
    DEPARTMENT STRING,
    JOB_TITLE STRING,
    HIRE_DATE TIMESTAMP,
    SALARY STRING,
    MANAGER_KEY INT
)
USING DELTA;
```

#### `FACT_GL`

```sql
CREATE TABLE IF NOT EXISTS FACT_GL (
    GL_LINE_ID INT,
    ACCOUNT_KEY INT,
    DATE_KEY INT,
    COST_CENTER_KEY INT,
    VERSION STRING,
    AMOUNT STRING,
    CURRENCY_CODE STRING
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

**TMDL files generated:** 39  
**Expressions translated:** 134  
**Warnings:** 12  
**Items requiring review:** 16

### Generated Files

| File | Size (chars) |
|------|-------------|
| `.platform` | 304 |
| `definition.pbism` | 192 |
| `definition/database.tmdl` | 35 |
| `definition/expressions.tmdl` | 230 |
| `definition/model.tmdl` | 1,807 |
| `definition/perspectives.tmdl` | 1,416 |
| `definition/relationships.tmdl` | 677 |
| `definition/tables/Accounts.tmdl` | 1,426 |
| `definition/tables/Budget & Forecast.tmdl` | 1,722 |
| `definition/tables/Budget.tmdl` | 570 |
| `definition/tables/Calendar.tmdl` | 3,779 |
| `definition/tables/Currency.tmdl` | 1,004 |
| `definition/tables/Customer.tmdl` | 1,728 |
| `definition/tables/DIM_Customer.tmdl` | 1,019 |
| `definition/tables/DIM_Employee.tmdl` | 1,190 |
| `definition/tables/DIM_Location.tmdl` | 1,297 |
| `definition/tables/Dim Channel.tmdl` | 1,004 |
| `definition/tables/Dim Customer.tmdl` | 3,512 |
| `definition/tables/Dim Date.tmdl` | 3,409 |
| `definition/tables/Dim Employee.tmdl` | 1,927 |
| `definition/tables/Dim Geography.tmdl` | 2,580 |
| `definition/tables/Dim Product.tmdl` | 2,813 |
| `definition/tables/Dim Warehouse.tmdl` | 1,208 |
| `definition/tables/Employee.tmdl` | 8,161 |
| `definition/tables/Enterprise Sales.tmdl` | 2,939 |
| `definition/tables/FACT_Orders.tmdl` | 1,026 |
| `definition/tables/FACT_Payroll.tmdl` | 1,178 |
| `definition/tables/Fact GL.tmdl` | 1,685 |
| `definition/tables/Fact Inventory.tmdl` | 1,392 |
| `definition/tables/Fact Sales.tmdl` | 6,229 |
| `definition/tables/General_Ledger.tmdl` | 1,695 |
| `definition/tables/Product.tmdl` | 1,326 |
| `definition/tables/Returns.tmdl` | 765 |
| `definition/tables/Sales DB.tmdl` | 1,641 |
| `definition/tables/Sales Data Warehouse.tmdl` | 6,387 |
| `definition/tables/Sales.tmdl` | 2,078 |
| `definition/tables/Sales_Analytics.tmdl` | 7,998 |
| `definition/tables/Scenario.tmdl` | 1,355 |
| `definition/tables/Time.tmdl` | 1,940 |

### Expression Translations

| # | Source Expression | DAX Output | Confidence |
|---|-----------------|------------|------------|
| 1 | `@PRIOR(Time, 12, @LEVMBRS(Time, 3))` | `BLANK() /* @PRIOR — no DAX equivalent, requires manual revie…` | 30% |
| 2 | `@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))` | `BLANK() /* @SUMRANGE — no DAX equivalent, requires manual re…` | 100% |
| 3 | `Revenue + COGS` | `Revenue + COGS` | 100% |
| 4 | `Gross Profit + OpEx` | `Gross Profit + OpEx` | 100% |
| 5 | `EBITDA + Depreciation` | `EBITDA + Depreciation` | 60% |
| 6 | `@ROUND(Gross Profit % Revenue, 4)` | `ROUND(DIVIDE(Gross Profit, Revenue), 4)` | 100% |
| 7 | `@ROUND(EBITDA % Revenue, 4)` | `ROUND(DIVIDE(EBITDA, Revenue), 4)` | 100% |
| 8 | `@ROUND(Revenue / (Headcount SM + Headcount RD + Headcount GA…` | `ROUND(Revenue / (Headcount SM + Headcount RD + Headcount GA)…` | 100% |
| 9 | `Gross Profit - Operating Expenses` | `Gross Profit - Operating Expenses` | 60% |
| 10 | `("DIM_PRODUCT"."UNIT_PRICE" - "DIM_PRODUCT"."UNIT_COST") / "…` | `([UNIT_PRICE] - [UNIT_COST]) / [UNIT_PRICE] * 100` | 60% |
| 11 | `Actual - Budget` | `Actual - Budget` | 100% |
| 12 | `@ROUND((Actual - Budget) % Budget, 4)` | `ROUND((Actual - Budget) % Budget, 4)` | 100% |
| 13 | `Actual - Forecast` | `Actual - Forecast` | 100% |
| 14 | `@ROUND((Actual - @PRIOR(Actual, 1, @LEVMBRS(Scenario, 0))) %…` | `ROUND((Actual - BLANK() /* @PRIOR — no DAX equivalent, requi…` | 30% |
| 15 | `Actual - Budget` | `Actual - Budget` | 100% |
| 16 | `@ROUND((Actual - Budget) % Budget, 4)` | `ROUND((Actual - Budget) % Budget, 4)` | 100% |
| 17 | `@CALCMBR(Local, @XREF(ExchangeRates, Rate))` | `BLANK() /* @CALCMBR — no DAX equivalent, requires manual rev…` | 100% |
| 18 | `@CALCMBR(USD, @XREF(ExchangeRates, EUR_Rate))` | `BLANK() /* @CALCMBR — no DAX equivalent, requires manual rev…` | 100% |
| 19 | `NTILE(4)` | `INT(RANKX(ALL('Sales_Analytics'), 1, , ASC) * 4 / COUNTROWS(…` | 100% |
| 20 | `CUME_DIST()` | `DIVIDE(RANKX(ALL('Sales_Analytics'), 1, , ASC), COUNTROWS(AL…` | 100% |
| 21 | `PERCENT_RANK()` | `DIVIDE(RANKX(ALL('Sales_Analytics'), 1, , ASC) - 1, COUNTROW…` | 100% |
| 22 | `MEDIAN("FACT_SALES"."REVENUE")` | `MEDIAN('Sales_Analytics'[REVENUE])` | 100% |
| 23 | `STDDEV("FACT_SALES"."REVENUE")` | `STDEV.S('Sales_Analytics'[REVENUE])` | 100% |
| 24 | `PERCENTILE("FACT_SALES"."REVENUE", 0.9)` | `PERCENTILEX.INC('Sales_Analytics', 'Sales_Analytics'[REVENUE…` | 100% |
| 25 | `COUNTIF("FACT_SALES"."REVENUE", "FACT_SALES"."REVENUE" > 100…` | `CALCULATE(COUNTX('Sales_Analytics', [REVENUE]), [REVENUE] > …` | 100% |
| 26 | `SUMIF("FACT_SALES"."REVENUE", "FACT_SALES"."DISCOUNT_AMOUNT"…` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), [DISCOUNT_AMOU…` | 100% |
| 27 | `SUM("FACT_SALES"."REVENUE")` | `SUMX('Sales_Analytics', [REVENUE])` | 100% |
| 28 | `SUM("FACT_SALES"."COST")` | `SUMX('Sales_Analytics', [COST])` | 100% |
| 29 | `SUM("FACT_SALES"."QUANTITY")` | `SUMX('Sales_Analytics', [QUANTITY])` | 100% |
| 30 | `AGO(SUM("FACT_SALES"."REVENUE"), YEAR, 1)` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATEADD('Date'…` | 85% |
| 31 | `AGO(SUM("FACT_SALES"."REVENUE"), QUARTER, 1)` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATEADD('Date'…` | 85% |
| 32 | `AGO(SUM("FACT_SALES"."REVENUE"), MONTH, 1)` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATEADD('Date'…` | 85% |
| 33 | `TODATE(SUM("FACT_SALES"."REVENUE"), 'YEAR')` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESYTD('Date…` | 85% |
| 34 | `TODATE(SUM("FACT_SALES"."REVENUE"), 'QUARTER')` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESQTD('Date…` | 85% |
| 35 | `TODATE(SUM("FACT_SALES"."REVENUE"), 'MONTH')` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESMTD('Date…` | 85% |
| 36 | `TODATE(SUM("FACT_SALES"."REVENUE"), 'WEEK')` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESINPERIOD(…` | 85% |
| 37 | `PERIODROLLING(SUM("FACT_SALES"."REVENUE"), 30)` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESINPERIOD(…` | 85% |
| 38 | `PERIODROLLING(SUM("FACT_SALES"."REVENUE"), 90)` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESINPERIOD(…` | 85% |
| 39 | `RSUM(SUM("FACT_SALES"."REVENUE"))` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE], FILTER(ALL('Dat…` | 85% |
| 40 | `RCOUNT(SUM("FACT_SALES"."QUANTITY"))` | `CALCULATE(COUNTROWS('Sales_Analytics'), FILTER(ALL('Date'), …` | 85% |
| 41 | `RMAX(SUM("FACT_SALES"."REVENUE"))` | `CALCULATE(MAX(SUMX('Sales_Analytics', [REVENUE]), FILTER(ALL…` | 85% |
| 42 | `RMIN(SUM("FACT_SALES"."REVENUE"))` | `CALCULATE(MIN(SUMX('Sales_Analytics', [REVENUE]), FILTER(ALL…` | 85% |
| 43 | `MAVG(SUM("FACT_SALES"."REVENUE"), 7)` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESINPERIOD(…` | 85% |
| 44 | `MSUM(SUM("FACT_SALES"."REVENUE"), 30)` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESINPERIOD(…` | 85% |
| 45 | `PARALLELPERIOD(SUM("FACT_SALES"."REVENUE"), -1, YEAR)` | `CALCULATE(SUMX('Sales_Analytics', [REVENUE]), PARALLELPERIOD…` | 85% |
| 46 | `OPENINGBALANCEYEAR(SUM("FACT_SALES"."REVENUE"))` | `OPENINGBALANCEYEAR(SUMX('Sales_Analytics', [REVENUE], 'Date'…` | 85% |
| 47 | `CLOSINGBALANCEYEAR(SUM("FACT_SALES"."REVENUE"))` | `CLOSINGBALANCEYEAR(SUMX('Sales_Analytics', [REVENUE], 'Date'…` | 85% |
| 48 | `RANK(SUM("FACT_SALES"."REVENUE"))` | `RANKX(ALL('Sales_Analytics'), SUMX('Sales_Analytics', [REVEN…` | 100% |
| 49 | `DENSE_RANK(SUM("FACT_SALES"."REVENUE"))` | `RANKX(ALL('Sales_Analytics'), SUMX('Sales_Analytics', [REVEN…` | 100% |
| 50 | `RATIO_TO_REPORT(SUM("FACT_SALES"."REVENUE"))` | `DIVIDE(SUM('Sales_Analytics'[REVENUE], CALCULATE(SUM('Sales_…` | 100% |
| 51 | `COUNTDISTINCT("FACT_SALES"."PRODUCT_KEY")` | `DISTINCTCOUNT('Sales_Analytics'[PRODUCT_KEY])` | 100% |
| 52 | `SUM("FACT_SALES"."REVENUE") - SUM("FACT_FORECAST"."FORECAST_…` | `SUMX('Sales_Analytics', [REVENUE]) - SUMX('Sales_Analytics',…` | 100% |
| 53 | `SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1…` | `SUMX('Sales', [QUANTITY] * [UNIT_PRICE] * (1 - [DISCOUNT_PCT…` | 100% |
| 54 | `SUM("FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST")` | `SUMX('Sales', [QUANTITY] * [UNIT_COST])` | 100% |
| 55 | `SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1…` | `SUMX('Sales', [QUANTITY] * [UNIT_PRICE] * (1 - [DISCOUNT_PCT…` | 100% |
| 56 | `CASE WHEN SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_P…` | `SWITCH(TRUE(),
    SUMX('Sales', [QUANTITY] * [UNIT_PRICE]) …` | 80% |
| 57 | `CASE WHEN SUM("FACT_SALES"."QUANTITY") = 0 THEN 0 ELSE SUM("…` | `SWITCH(TRUE(),
    SUMX('Sales', [QUANTITY]) = 0, 0,
    SUM…` | 80% |
| 58 | `SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE") - S…` | `SUMX('Sales', [QUANTITY] * [UNIT_PRICE]) - SUMX('Sales', [BU…` | 100% |
| 59 | `"Revenue" - "Cost"` | `"Revenue" - "Cost"` | 100% |
| 60 | `("Revenue" - "Cost") / NULLIF("Revenue", 0) * 100` | `("Revenue" - "Cost") / IF("Revenue" = 0, BLANK(), "Revenue")…` | 100% |
| 61 | `CONCAT("DIM_EMPLOYEE"."FIRST_NAME", ' ' || "DIM_EMPLOYEE"."L…` | `[FIRST_NAME] & ' ' & [LAST_NAME]` | 100% |
| 62 | `"DIM_EMPLOYEE"."FIRST_NAME" || ' ' || "DIM_EMPLOYEE"."LAST_N…` | `[FIRST_NAME] & ' ' & [LAST_NAME]` | 100% |
| 63 | `INITCAP("DIM_EMPLOYEE"."LAST_NAME")` | `UPPER(LEFT([LAST_NAME], 1)) & LOWER(MID([LAST_NAME], 2, LEN(…` | 100% |
| 64 | `SUBSTRING("DIM_EMPLOYEE"."EMAIL", INSTR("DIM_EMPLOYEE"."EMAI…` | `MID([EMAIL], FIND('@', [EMAIL]) + 1, 50)` | 100% |
| 65 | `LEFT("DIM_EMPLOYEE"."EMAIL", INSTR("DIM_EMPLOYEE"."EMAIL", '…` | `LEFT([EMAIL], FIND('@', [EMAIL]) - 1)` | 100% |
| 66 | `LENGTH("DIM_EMPLOYEE"."LAST_NAME")` | `LEN([LAST_NAME])` | 100% |
| 67 | `UPPER("DIM_EMPLOYEE"."LAST_NAME")` | `UPPER([LAST_NAME])` | 100% |
| 68 | `LOWER("DIM_EMPLOYEE"."FIRST_NAME")` | `LOWER([FIRST_NAME])` | 100% |
| 69 | `TRIM("DIM_EMPLOYEE"."NOTES")` | `TRIM([NOTES])` | 100% |
| 70 | `LTRIM("DIM_EMPLOYEE"."NOTES")` | `TRIM([NOTES])` | 100% |
| 71 | `RTRIM("DIM_EMPLOYEE"."NOTES")` | `TRIM([NOTES])` | 100% |
| 72 | `REPLACE("DIM_EMPLOYEE"."PHONE", '-', '')` | `SUBSTITUTE([PHONE], '-', '')` | 100% |
| 73 | `LPAD("DIM_EMPLOYEE"."JOB_CODE", 8, '0')` | `REPT('0', 8 - LEN([JOB_CODE])) & [JOB_CODE]` | 100% |
| 74 | `RPAD("DIM_EMPLOYEE"."JOB_CODE", 10, ' ')` | `[JOB_CODE] & REPT(' ', 10 - LEN([JOB_CODE]))` | 100% |
| 75 | `ASCII("DIM_EMPLOYEE"."FIRST_NAME")` | `UNICODE([FIRST_NAME])` | 100% |
| 76 | `CHR(65)` | `UNICHAR(65)` | 100% |
| 77 | `TRANSLATE("DIM_EMPLOYEE"."STATUS", 'A', 'Active')` | `SUBSTITUTE([STATUS], 'A', 'Active')` | 100% |
| 78 | `IFNULL("DIM_EMPLOYEE"."DEPARTMENT", 'Unassigned')` | `IF(ISBLANK([DEPARTMENT]), 'Unassigned', [DEPARTMENT])` | 100% |
| 79 | `NVL("DIM_EMPLOYEE"."DEPARTMENT", 'General')` | `IF(ISBLANK([DEPARTMENT]), 'General', [DEPARTMENT])` | 100% |
| 80 | `NVL2("DIM_EMPLOYEE"."DEPARTMENT", "DIM_EMPLOYEE"."DEPARTMENT…` | `IF(ISBLANK([DEPARTMENT]), 'N/A', [DEPARTMENT])` | 100% |
| 81 | `COALESCE("DIM_EMPLOYEE"."DEPARTMENT", "DIM_EMPLOYEE"."JOB_CO…` | `COALESCE([DEPARTMENT], [JOB_CODE], 'None')` | 100% |
| 82 | `NULLIF("DIM_EMPLOYEE"."STATUS", '')` | `IF([STATUS] = '', BLANK(), [STATUS])` | 100% |
| 83 | `GREATEST("DIM_EMPLOYEE"."SALARY", 50000)` | `IF([SALARY] >= 50000, [SALARY], 50000)` | 100% |
| 84 | `LEAST("DIM_EMPLOYEE"."SALARY", 200000)` | `IF([SALARY] <= 200000, [SALARY], 200000)` | 100% |
| 85 | `DECODE("DIM_EMPLOYEE"."STATUS", 'A', 'Active', 'I', 'Inactiv…` | `SWITCH([STATUS],
    'A', 'Active',
    'I', 'Inactive',
   …` | 80% |
| 86 | `CASE WHEN "DIM_EMPLOYEE"."SALARY" > 100000 THEN 'Senior' WHE…` | `SWITCH(TRUE(),
    [SALARY] > 100000, 'Senior',
    [SALARY]…` | 80% |
| 87 | `CAST("DIM_EMPLOYEE"."SALARY" AS INT)` | `INT([SALARY])` | 100% |
| 88 | `CAST("DIM_EMPLOYEE"."EMP_KEY" AS VARCHAR)` | `FORMAT([EMP_KEY], "General")` | 100% |
| 89 | `TO_NUMBER("DIM_EMPLOYEE"."JOB_CODE")` | `VALUE([JOB_CODE])` | 100% |
| 90 | `EXTRACT(YEAR FROM "DIM_EMPLOYEE"."HIRE_DATE")` | `YEAR([HIRE_DATE])` | 100% |
| 91 | `EXTRACT(MONTH FROM "DIM_EMPLOYEE"."HIRE_DATE")` | `MONTH([HIRE_DATE])` | 100% |
| 92 | `EXTRACT(QUARTER FROM "DIM_EMPLOYEE"."HIRE_DATE")` | `QUARTER([HIRE_DATE])` | 100% |
| 93 | `MONTHS_BETWEEN(CURRENT_DATE, "DIM_EMPLOYEE"."HIRE_DATE")` | `DATEDIFF([HIRE_DATE], TODAY(), MONTH)` | 100% |
| 94 | `ADD_MONTHS("DIM_EMPLOYEE"."HIRE_DATE", 12)` | `EDATE([HIRE_DATE], 12)` | 100% |
| 95 | `LAST_DAY("DIM_EMPLOYEE"."HIRE_DATE")` | `EOMONTH([HIRE_DATE], 0)` | 100% |
| 96 | `CURRENT_DATE` | `TODAY()` | 100% |
| 97 | `CURRENT_TIMESTAMP` | `NOW()` | 100% |
| 98 | `SYSDATE` | `NOW()` | 100% |
| 99 | `TO_CHAR("DIM_EMPLOYEE"."HIRE_DATE", 'YYYY-MM-DD')` | `FORMAT([HIRE_DATE], 'YYYY-MM-DD')` | 100% |
| 100 | `ABS("DIM_EMPLOYEE"."SALARY" - 75000)` | `ABS([SALARY] - 75000)` | 100% |
| 101 | `ROUND("DIM_EMPLOYEE"."SALARY", -3)` | `ROUND([SALARY], -3)` | 100% |
| 102 | `CEIL("DIM_EMPLOYEE"."SALARY" / 1000)` | `CEILING([SALARY] / 1000, 1)` | 100% |
| 103 | `FLOOR("DIM_EMPLOYEE"."SALARY" / 1000)` | `FLOOR([SALARY] / 1000, 1)` | 100% |
| 104 | `POWER("DIM_EMPLOYEE"."SALARY", 2)` | `POWER([SALARY], 2)` | 100% |
| 105 | `SQRT("DIM_EMPLOYEE"."SALARY")` | `SQRT([SALARY])` | 100% |
| 106 | `LOG("DIM_EMPLOYEE"."SALARY")` | `LN([SALARY])` | 100% |
| 107 | `EXP(1)` | `EXP(1)` | 100% |
| 108 | `MOD("DIM_EMPLOYEE"."EMP_KEY", 10)` | `MOD([EMP_KEY], 10)` | 100% |
| 109 | `SIGN("DIM_EMPLOYEE"."SALARY" - 75000)` | `SIGN([SALARY] - 75000)` | 100% |
| 110 | `VALUEOF(NQ_SESSION.USER)` | `USERPRINCIPALNAME()` | 100% |
| 111 | `RAND()` | `RAND()` | 100% |
| 112 | `SUM("FACT_GL"."DEBIT_AMOUNT") - SUM("FACT_GL"."CREDIT_AMOUNT…` | `SUMX('General_Ledger', [DEBIT_AMOUNT]) - SUMX('General_Ledge…` | 100% |
| 113 | `SUM("FACT_GL"."DEBIT_AMOUNT" * "FACT_GL"."EXCHANGE_RATE")` | `SUMX('General_Ledger', [DEBIT_AMOUNT] * [EXCHANGE_RATE])` | 100% |
| 114 | `SUM("FACT_GL"."DEBIT_AMOUNT") - SUM("FACT_BUDGET"."BUDGET_AM…` | `SUMX('General_Ledger', [DEBIT_AMOUNT]) - SUMX('General_Ledge…` | 100% |
| 115 | `CASE WHEN SUM("FACT_BUDGET"."BUDGET_AMOUNT") = 0 THEN 0 ELSE…` | `SWITCH(TRUE(),
    SUMX('General_Ledger', [BUDGET_AMOUNT]) =…` | 80% |
| 116 | `TOPN(10, SUM("FACT_GL"."DEBIT_AMOUNT"))` | `TOPN(10, 'General_Ledger', SUMX('General_Ledger', [DEBIT_AMO…` | 100% |
| 117 | `"EMPLOYEES"."FIRST_NAME" || ' ' || "EMPLOYEES"."LAST_NAME"` | `[FIRST_NAME] & ' ' & [LAST_NAME]` | 100% |
| 118 | `"PAYROLL"."GROSS_PAY" - "PAYROLL"."DEDUCTIONS"` | `[GROSS_PAY] - [DEDUCTIONS]` | 60% |
| 119 | `AVG("EMPLOYEES"."SALARY")` | `AVERAGEX('FACT_Payroll', [SALARY])` | 100% |
| 120 | `SUM("ORDERS"."AMOUNT") * 0.2` | `SUMX('FACT_Orders', [AMOUNT]) * 0.2` | 100% |
| 121 | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | 60% |
| 122 | `[Quantity] * [UnitCost] + [TaxAmount] + [FreightCost]` | `[Quantity] * [UnitCost] + [TaxAmount] + [FreightCost]` | 60% |
| 123 | `[Revenue] - [TotalCost]` | `[Revenue] - [TotalCost]` | 60% |
| 124 | `IF [Revenue] > 0 THEN [Profit] / [Revenue] * 100 ELSE 0 END` | `IF([Revenue] > 0, [Profit] / [Revenue] * 100, 0)` | 80% |
| 125 | `[Quantity] * [UnitPrice] * [DiscountPct]` | `[Quantity] * [UnitPrice] * [DiscountPct]` | 60% |
| 126 | `IF [UnitPrice] > 500 THEN 'Premium' ELSEIF [UnitPrice] > 100…` | `IF([UnitPrice] > 500, "Premium", IF([UnitPrice] > 100, "Mid-…` | 80% |
| 127 | `IF [Revenue] > 5000 THEN 'Yes' ELSE 'No' END` | `IF([Revenue] > 5000, "Yes", "No")` | 80% |
| 128 | `SUM([Revenue]) / COUNTD([OrderID])` | `SUMX('Sales Data Warehouse', [Revenue]) / COUNTD([OrderID])` | 100% |
| 129 | `[ForecastAmount] - [BudgetAmount]` | `[ForecastAmount] - [BudgetAmount]` | 60% |
| 130 | `IF [BudgetAmount] > 0 THEN ([ForecastAmount] - [BudgetAmount…` | `IF([BudgetAmount] > 0, ([ForecastAmount] - [BudgetAmount]) /…` | 80% |
| 131 | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | 60% |
| 132 | `[Revenue] - ([Quantity] * [UnitCost])` | `[Revenue] - ([Quantity] * [UnitCost])` | 60% |
| 133 | `IF [Revenue] > 0 THEN [Profit] / [Revenue] ELSE 0 END` | `IF([Revenue] > 0, [Profit] / [Revenue], 0)` | 80% |
| 134 | `[Amount] * [Quantity]` | `[Amount] * [Quantity]` | 60% |

### Items Requiring Review

| Type | Table | Column/Hierarchy | Reason |
|------|-------|------------------|--------|
| hierarchy | Currency | CurrencyHierarchy | Missing column references |
| hierarchy | Customer | GeoHierarchy | Missing column references |
| expression | Time | Prior Year | Fixed unbalanced parentheses; Untranslatable pattern: PRIOR (hierarchical) |
| expression | Accounts | EBIT | No translation rules matched — expression may need manual review |
| expression | Accounts | Operating Income | No translation rules matched — expression may need manual review |
| expression | Product | Margin Pct | No translation rules matched — expression may need manual review |
| expression | Scenario | YoY Growth | Fixed unbalanced parentheses; Untranslatable pattern: PRIOR (hierarchical) |
| expression | FACT_Payroll | Net Pay | No translation rules matched — expression may need manual review |
| expression | Sales Data Warehouse | Revenue | No translation rules matched — expression may need manual review |
| expression | Sales Data Warehouse | TotalCost | No translation rules matched — expression may need manual review |
| expression | Sales Data Warehouse | Profit | No translation rules matched — expression may need manual review |
| expression | Sales Data Warehouse | DiscountAmount | No translation rules matched — expression may need manual review |
| expression | Budget & Forecast | BudgetVariance | No translation rules matched — expression may need manual review |
| expression | Enterprise Sales | Revenue | No translation rules matched — expression may need manual review |
| expression | Enterprise Sales | Profit | No translation rules matched — expression may need manual review |
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
    "logicalId": "1663da5a-85fc-490f-8cda-2448767f5a25"
  }
}
```

#### `definition.pbism`

```
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
  "version": "4.2",
  "settings": {
    "qnaEnabled": true
  }
}
```

#### `definition/database.tmdl`

```
database
	compatibilityLevel: 1604
```

#### `definition/expressions.tmdl`

```
expression ServerName = "localhost" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression DatabaseName = "MigrationLakehouse" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
```

#### `definition/model.tmdl`

```
model Model
	culture: en-US
	defaultPowerBIDataSourceVersion: powerBI_V3
	sourceQueryCulture: en-US
	dataAccessOptions
		legacyRedirects
		returnErrorValuesAsNull

annotation PBI_QueryOrder = ["Time","Accounts","Product","Scenario","Currency","Sales_Analytics","Customer","Sales","Returns","Budget","Fact Sales","Dim Customer","Dim Product","Dim Date","Dim Geography","Employee","General_Ledger","Fact Inventory","Fact GL","Dim Channel","Dim Warehouse","Dim Employee","DIM_Employee","DIM_Location","FACT_Payroll","DIM_Customer","FACT_Orders","Sales Data Warehouse","Budget & Forecast","Enterprise Sales","Sales DB"]

ref table Time
ref table Accounts
ref table Product
ref table Scenario
ref table Currency
ref table Sales_Analytics
ref table Customer
ref table Sales
ref table Returns
ref table Budget
ref table 'Fact Sales'
ref table 'Dim Customer'
ref table 'Dim Product'
ref table 'Dim Date'
ref table 'Dim Geography'
ref table Employee
ref table General_Ledger
ref table 'Fact Inventory'
ref table 'Fact GL'
ref table 'Dim Channel'
ref table 'Dim Warehouse'
ref table 'Dim Employee'
ref table DIM_Employee
ref table DIM_Location
ref table FACT_Payroll
ref table DIM_Customer
ref table FACT_Orders
ref table 'Sales Data Warehouse'
ref table 'Budget & Forecast'
ref table 'Enterprise Sales'
ref table 'Sales DB'

ref relationship rel_Fact_Sales_Dim_Customer
ref relationship rel_Fact_Sales_Dim_Product
ref relationship rel_Fact_Sales_Dim_Date
ref relationship rel_Fact_Sales_Dim_Geography

ref table Calendar

ref expression ServerName
ref expression DatabaseName

ref perspective 'Sales Analytics'
ref perspective 'Executive Sales'
ref perspective 'Product Performance'
ref perspective 'Returns Analysis'
ref perspective SampleApp
ref perspective 'Financial Analytics'
ref perspective 'Sales Analysis'
```

#### `definition/perspectives.tmdl`

```
perspective 'Sales Analytics'
	perspectiveTable Product
		perspectiveColumn 'Product Name'
		perspectiveColumn Category

perspective 'Executive Sales'
	perspectiveTable Time
		perspectiveColumn Date
		perspectiveColumn Year
		perspectiveColumn Quarter
		perspectiveColumn Month
	perspectiveTable Product
		perspectiveColumn 'Product Name'
		perspectiveColumn Category
		perspectiveColumn Brand
	perspectiveTable Customer
		perspectiveColumn 'Customer Name'
		perspectiveColumn Region
		perspectiveColumn Country

perspective 'Product Performance'
	perspectiveTable Product
		perspectiveColumn 'Product Name'
		perspectiveColumn Category
		perspectiveColumn Subcategory
		perspectiveColumn 'Margin Pct'
	perspectiveTable Sales
		perspectiveMeasure Revenue
		perspectiveColumn Quantity
		perspectiveMeasure 'Return Rate'

perspective 'Returns Analysis'
	perspectiveTable Time
		perspectiveColumn Year
		perspectiveColumn Month
	perspectiveTable Product
		perspectiveColumn 'Product Name'
		perspectiveColumn Category
	perspectiveTable Returns
		perspectiveColumn 'Return Quantity'
		perspectiveColumn 'Reason Code'

perspective SampleApp
	perspectiveTable Time
		perspectiveColumn Year
		perspectiveColumn Quarter
		perspectiveColumn Month

perspective 'Financial Analytics'
	perspectiveTable Time

perspective 'Sales Analysis'
	perspectiveTable Customer
		perspectiveColumn 'Customer Name'
		perspectiveColumn Region
```

#### `definition/relationships.tmdl`

```
relationship 92317850-62e5-43dd-bb70-7e368362c3f5
	fromColumn: 'Fact Sales'.'Customer Key'
	toColumn: 'Dim Customer'.'Customer Key'
	crossFilteringBehavior: oneDirection



relationship 1e9b7bc3-8638-4355-bc00-8082a1d06236
	fromColumn: 'Fact Sales'.'Product Key'
	toColumn: 'Dim Product'.'Product Key'
	crossFilteringBehavior: oneDirection



relationship 8cd879b3-aab0-4e78-903b-2e2a51a3b517
	fromColumn: 'Fact Sales'.'Date Key'
	toColumn: 'Dim Date'.'Date Key'
	crossFilteringBehavior: oneDirection



relationship d6e8220a-f44c-4add-891f-9856cc6a3474
	fromColumn: 'Fact Sales'.'Geography Key'
	toColumn: 'Dim Geography'.'Geography Key'
	crossFilteringBehavior: oneDirection
```

#### `definition/tables/Accounts.tmdl`

```
table Accounts
	lineageTag: 5390a0a3-ddb8-4905-9f60-4bb9566a5a3d

	column 'Gross Profit' = Revenue + COGS
		dataType: string
		lineageTag: 8a8ffd42-66bb-4505-95ce-9a6f20ba68b5
		summarizeBy: none

	column EBITDA = Gross Profit + OpEx
		dataType: string
		lineageTag: e4c454db-9f6f-4bcc-8046-c0250ef7dc28
		summarizeBy: none

	column EBIT = EBITDA + Depreciation
		dataType: string
		lineageTag: 75f966f7-2acd-429d-a703-ebbf56bedaa0
		summarizeBy: none

	column 'Gross Margin Pct' = ROUND(DIVIDE(Gross Profit, Revenue), 4)
		dataType: string
		lineageTag: c411acdf-5cd0-4ade-bf48-eeaeab10aa71
		summarizeBy: none

	column 'EBITDA Margin Pct' = ROUND(DIVIDE(EBITDA, Revenue), 4)
		dataType: string
		lineageTag: 7b3dd2e2-517d-4e03-a8e3-bb8474fe4e20
		summarizeBy: none

	column 'Rev per FTE' = ROUND(Revenue / (Headcount SM + Headcount RD + Headcount GA), 0)
		dataType: string
		lineageTag: 3eef673c-625d-4237-a533-ea55ee97ac07
		summarizeBy: none

	column 'Operating Income' = Gross Profit - Operating Expenses
		dataType: string
		lineageTag: ddee9bf6-5a13-4e30-8739-40aed8fb3420
		summarizeBy: none

	partition 'Accounts-26add474-f85e-424f-ac91-6f600e099e3e' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Accounts = Source
				in
				    Accounts

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Accounts
```

#### `definition/tables/Budget & Forecast.tmdl`

```
table 'Budget & Forecast'
	lineageTag: 6d46dd1c-1815-432f-97fa-0febe07928e7

	column BudgetMonth
		dataType: dateTime
		lineageTag: f94f1f51-30c7-4cd0-bd7b-dd7c50eaa486
		summarizeBy: none
		sourceColumn: BudgetMonth

		annotation SummarizationSetBy = Automatic

	column BudgetRegion
		dataType: string
		lineageTag: 446d280e-cbdb-4a3e-a263-296c0a9a6197
		summarizeBy: none
		sourceColumn: BudgetRegion

		annotation SummarizationSetBy = Automatic

	column BudgetCategory
		dataType: string
		lineageTag: f882439a-1d66-4807-b7cd-db9eba99b437
		summarizeBy: none
		sourceColumn: BudgetCategory

		annotation SummarizationSetBy = Automatic

	column BudgetAmount
		dataType: string
		lineageTag: 1a390607-d701-4668-a2c2-c62f18c7ea43
		summarizeBy: none
		sourceColumn: BudgetAmount

		annotation SummarizationSetBy = Automatic

	column ForecastAmount
		dataType: string
		lineageTag: 0092b04e-e55b-4b72-84bf-ad264551980e
		summarizeBy: none
		sourceColumn: ForecastAmount

		annotation SummarizationSetBy = Automatic

	column BudgetVariance = [ForecastAmount] - [BudgetAmount]
		dataType: string
		lineageTag: 9f8adf52-6d6d-401f-8305-8dd8f9dec162
		summarizeBy: none

	column VariancePct = IF([BudgetAmount] > 0, ([ForecastAmount] - [BudgetAmount]) / [BudgetAmount] * 100, 0)
		dataType: string
		lineageTag: 4801eb43-f7e9-4ee3-b3af-0b59784c1a96
		summarizeBy: none

	partition 'Budget & Forecast-9540dc7f-61a1-4937-886d-571b01edf907' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Budget__Forecast = Source
				in
				    Budget__Forecast

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Budget & Forecast
```

#### `definition/tables/Budget.tmdl`

```
table Budget
	lineageTag: 51882b3b-2302-4f01-a013-b303519b60ed

	column 'Budget Amount'
		dataType: string
		lineageTag: 357fb98f-9b3e-485c-a6d3-57a9a2395035
		summarizeBy: none
		sourceColumn: BUDGET_AMOUNT

		annotation SummarizationSetBy = Automatic

	partition 'Budget-8114a848-cfa4-4a32-867f-140301add0b5' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Budget = Source
				in
				    Budget

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Budget
```

#### `definition/tables/Calendar.tmdl`

```
table 'Calendar'
	lineageTag: be9b7802-1c83-4531-9e7f-949cd3f31051
	isHidden

	annotation Copilot_TableDescription = Auto-generated Calendar table for time intelligence
	annotation Copilot_DateTable = YES

	partition 'Calendar' = m
		mode: import
		source =
				let
				    StartDate = Date.StartOfYear(List.Min(#"Time"[Date])),
				    EndDate = Date.EndOfYear(List.Max(#"Time"[Date])),
				    DateList = List.Dates(StartDate, Duration.Days(EndDate - StartDate) + 1, #duration(1,0,0,0)),
				    #"Convert to Table" = Table.FromList(DateList, Splitter.SplitByNothing(), {"Date"}),
				    #"Changed Type" = Table.TransformColumnTypes(#"Convert to Table", {{"Date", type date}}),
				    #"Added Year" = Table.AddColumn(#"Changed Type", "Year", each Date.Year([Date]), Int64.Type),
				    #"Added Quarter" = Table.AddColumn(#"Added Year", "Quarter", each Date.QuarterOfYear([Date]), Int64.Type),
				    #"Added Month" = Table.AddColumn(#"Added Quarter", "Month", each Date.Month([Date]), Int64.Type),
				    #"Added MonthName" = Table.AddColumn(#"Added Month", "MonthName", each Date.MonthName([Date]), type text),
				    #"Added Day" = Table.AddColumn(#"Added MonthName", "Day", each Date.Day([Date]), Int64.Type),
				    #"Added DayOfWeek" = Table.AddColumn(#"Added Day", "DayOfWeek", each Date.DayOfWeek([Date], Day.Monday) + 1, Int64.Type),
				    #"Added DayName" = Table.AddColumn(#"Added DayOfWeek", "DayName", each Date.DayOfWeekName([Date]), type text)
				in
				    #"Added DayName"

	column Date
		dataType: dateTime
		lineageTag: 9436d306-239a-4287-9316-12b85f9a5754
		formatString: yyyy-MM-dd
		sourceColumn: Date
		summarizeBy: none

	column Year
		dataType: int64
		lineageTag: e581f2c1-97e0-4c74-b4aa-8ed7f3696ea3
		formatString: 0
		sourceColumn: Year
		summarizeBy: none

	column Quarter
		dataType: int64
		lineageTag: db2c1ec2-5534-4638-8fc9-b206a83cfc91
		formatString: 0
		sourceColumn: Quarter
		summarizeBy: none

	column Month
		dataType: int64
		lineageTag: 23ff1c63-e129-48b2-ba96-3be93772d3f8
		formatString: 0
		sourceColumn: Month
		summarizeBy: none

	column MonthName
		dataType: string
		lineageTag: 8f3589c3-f3a8-4532-8107-a2dd9f1a8b50
		sourceColumn: MonthName
		sortByColumn: Month
		summarizeBy: none

	column Day
		dataType: int64
		lineageTag: 417e79d5-b1c9-42c3-bae6-d723600d6f2f
		formatString: 0
		sourceColumn: Day
		summarizeBy: none

	column DayOfWeek
		dataType: int64
		lineageTag: 851345e3-9057-46f5-8531-e18ef7441180
		formatString: 0
		sourceColumn: DayOfWeek
		summarizeBy: none

	column DayName
		dataType: string
		lineageTag: c0701c21-7011-4194-a788-db737da2106c
		sourceColumn: DayName
		sortByColumn: DayOfWeek
		summarizeBy: none

	hierarchy 'Date Hierarchy'
		lineageTag: fdfb867c-3cf2-4fee-b21a-cd2ec855dd45
		level Year
			lineageTag: ce8fb48c-55a2-40a8-9d1c-4cacf2847cd2
			column: Year
		level Quarter
			lineageTag: c7843f69-f823-4980-978c-37deab2c761e
			column: Quarter
		level Month
			lineageTag: 1ce32ab1-3705-4a1f-a3fa-d1fe93062d4a
			column: Month
		level Day
			lineageTag: b3c41086-5b82-4c1b-9ee0-871c84f336e7
			column: Day

	measure 'YTD Sales' = TOTALYTD(SUM('Calendar'[Date]), 'Calendar'[Date])
		lineageTag: 40cf7b79-f04a-4f1a-a918-fd5ac44ca24d
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence

	measure 'PY Sales' = CALCULATE([YTD Sales], SAMEPERIODLASTYEAR('Calendar'[Date]))
		lineageTag: 09d343b1-e16f-411f-8362-a328b4cb3bf4
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence

	measure 'YoY %' = DIVIDE([YTD Sales] - [PY Sales], [PY Sales], BLANK())
		lineageTag: 2d4ce314-5007-4254-9a94-ffdca149840c
		formatString: 0.00%
		displayFolder: Time Intelligence

	annotation __migration_note = unreferenced-hidden — consider removing
```

#### `definition/tables/Currency.tmdl`

```
table Currency
	lineageTag: 0f5a00eb-a33f-4484-808f-b01ddaeac369

	column USD = BLANK() /* @CALCMBR — no DAX equivalent, requires manual review */
		dataType: string
		lineageTag: 2a8c3392-f917-40b9-abc5-eaae3d765fc9
		summarizeBy: none

	column EUR = BLANK() /* @CALCMBR — no DAX equivalent, requires manual review */
		dataType: string
		lineageTag: 3bdfc551-f9d3-4458-866e-314947eea074
		summarizeBy: none

	hierarchy CurrencyHierarchy
		lineageTag: f4eeff4e-fb57-428f-bdd5-22c4adf7bf26

		level USD
			ordinal: 0
			column: USD
			lineageTag: 76de9248-9aaf-49b1-bd4d-6430621e8702

		level EUR
			ordinal: 1
			column: EUR
			lineageTag: 12ef6931-b677-49f8-a4f1-73760e4a82e5


	partition 'Currency-6d84a790-0aed-4a69-b77a-c1f30b1c8653' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Currency = Source
				in
				    Currency

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Currency
```

#### `definition/tables/Customer.tmdl`

```
table Customer
	lineageTag: 7ada415e-1df7-49e4-bbfc-8290b26782a0

	column 'Customer Name'
		dataType: string
		lineageTag: f211de52-b3e2-4ed9-a406-bd36d6e50aa6
		summarizeBy: none
		sourceColumn: CUSTOMER_NAME

		annotation SummarizationSetBy = Automatic

	column Segment
		dataType: string
		lineageTag: 9dc082fb-a541-4a38-8775-b27a5458d36a
		summarizeBy: none
		sourceColumn: SEGMENT

		annotation SummarizationSetBy = Automatic

	column Region
		dataType: string
		lineageTag: af1b773b-7f01-491c-a71e-cf4ec7a7e34a
		summarizeBy: none
		sourceColumn: REGION
		dataCategory: StateOrProvince

		annotation SummarizationSetBy = Automatic

	column Country
		dataType: string
		lineageTag: c682b5c6-9441-475c-9cdb-ebb2b3f8e1ac
		summarizeBy: none
		sourceColumn: COUNTRY
		dataCategory: Country

		annotation SummarizationSetBy = Automatic

	column City
		dataType: string
		lineageTag: f699fee2-1535-4e98-a876-5551fb5571c6
		summarizeBy: none
		sourceColumn: CITY
		dataCategory: City

		annotation SummarizationSetBy = Automatic

	hierarchy GeoHierarchy
		lineageTag: d7eaabfb-a762-4767-a133-b07a6aab38cf

		level Region
			ordinal: 0
			column: Region
			lineageTag: de91dd65-4061-4456-ab0f-e08b0a0b9b30

		level Country
			ordinal: 1
			column: Country
			lineageTag: 2b6efc72-ad93-4292-bec2-f3896539afd3

		level City
			ordinal: 2
			column: City
			lineageTag: 55927df3-90e5-4479-96c2-6671861fd6aa


	partition 'Customer-e26781b6-1d85-43f5-9119-50f979a54374' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Customer = Source
				in
				    Customer

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Customer
```

#### `definition/tables/DIM_Customer.tmdl`

```
table DIM_Customer
	lineageTag: 4c21cb3d-8296-4dab-a400-9ff3edb6cfea

	column 'Customer ID'
		dataType: string
		lineageTag: e2caf382-fdf0-4219-9f79-3e5fbbd9aa79
		summarizeBy: none
		sourceColumn: CUST_ID

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Customer Name'
		dataType: string
		lineageTag: af904a19-5d61-4a23-b52e-bf2997349be2
		summarizeBy: none
		sourceColumn: CUST_NAME

		annotation SummarizationSetBy = Automatic

	column Region
		dataType: string
		lineageTag: 18dfebbe-4016-4d38-b3c9-18f91a89307c
		summarizeBy: none
		sourceColumn: REGION
		dataCategory: StateOrProvince

		annotation SummarizationSetBy = Automatic

	partition 'DIM_Customer-31b3dbbb-b421-4ece-9173-96ef23cd73e3' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    DIM_Customer = Source
				in
				    DIM_Customer

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from DIM_Customer
```

#### `definition/tables/DIM_Employee.tmdl`

```
table DIM_Employee
	lineageTag: f370021a-09c0-4260-ad2d-a3466f8a77b3

	column 'Employee ID'
		dataType: string
		lineageTag: bce356f1-e23f-4988-b041-53a0287a1158
		summarizeBy: none
		sourceColumn: EMP_ID

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Hire Date'
		dataType: string
		lineageTag: 12e666cd-98af-4452-adfd-672b06de5c9d
		summarizeBy: none
		sourceColumn: HIRE_DATE

		annotation SummarizationSetBy = Automatic

	column Department
		dataType: string
		lineageTag: 5eeafd0c-e9ca-4885-b4fd-312ff8c07132
		summarizeBy: none
		sourceColumn: DEPT_NAME

		annotation SummarizationSetBy = Automatic

	column 'Full Name' = [FIRST_NAME] & ' ' & [LAST_NAME]
		dataType: string
		lineageTag: 144198ef-2fad-4d2b-8616-3a28cb3e2da0
		summarizeBy: none

	partition 'DIM_Employee-8e411e49-ac15-45f0-b4cb-4429ff02a42c' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    DIM_Employee = Source
				in
				    DIM_Employee

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from DIM_Employee

	annotation __migration_note = broken-ref-auto-hidden
```

#### `definition/tables/DIM_Location.tmdl`

```
table DIM_Location
	lineageTag: 8ab24adb-8bf7-4a28-948f-bbfa6cac8fb1

	column 'Location ID'
		dataType: string
		lineageTag: 699670cb-b73f-43ec-9f21-7b8a19dda274
		summarizeBy: none
		sourceColumn: LOCATION_ID

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column City
		dataType: string
		lineageTag: 5d023172-acf7-46ad-81b2-5e73f5f6613b
		summarizeBy: none
		sourceColumn: CITY
		dataCategory: City

		annotation SummarizationSetBy = Automatic

	column Country
		dataType: string
		lineageTag: fa526050-dad7-4d52-9e79-f2aa040b2b4b
		summarizeBy: none
		sourceColumn: COUNTRY
		dataCategory: Country

		annotation SummarizationSetBy = Automatic

	hierarchy GeoHierarchy
		lineageTag: 4f5f4616-cd80-42f9-9e5c-20014d2064a4

		level Country
			ordinal: 0
			column: Country
			lineageTag: 05b933c3-e27f-461e-97ae-899a87e25ff8

		level City
			ordinal: 1
			column: City
			lineageTag: 77a15030-474d-4d59-af4b-5e769a4d9a28


	partition 'DIM_Location-e8399a91-54de-441a-95bb-ec54685c52c9' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    DIM_Location = Source
				in
				    DIM_Location

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from DIM_Location
```

#### `definition/tables/Dim Channel.tmdl`

```
table 'Dim Channel'
	lineageTag: e70db8bb-f25d-4ea5-a17c-be2e82d0f913

	column 'Channel Key'
		dataType: string
		lineageTag: 1c0f8bf1-98cb-444a-ae7f-0dfa64d4dcb1
		summarizeBy: none
		sourceColumn: Channel Key

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Channel Name'
		dataType: string
		lineageTag: 97e97e65-cea3-4cb9-bbe8-29e8650cc1ec
		summarizeBy: none
		sourceColumn: Channel Name

		annotation SummarizationSetBy = Automatic

	column 'Channel Type'
		dataType: string
		lineageTag: 3dae1cea-4571-498a-8ab4-62c52a4aac67
		summarizeBy: none
		sourceColumn: Channel Type

		annotation SummarizationSetBy = Automatic

	partition 'Dim Channel-cb018cab-04d6-4086-a124-aeddc2c31f2e' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Dim_Channel = Source
				in
				    Dim_Channel

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Dim Channel
```

#### `definition/tables/Dim Customer.tmdl`

```
table 'Dim Customer'
	lineageTag: e9739dc0-0d55-4680-b996-258d37516971

	column 'Customer Key'
		dataType: int64
		formatString: 0
		lineageTag: e58819b9-aba0-46ff-babb-8434fd26be8f
		summarizeBy: sum
		sourceColumn: Customer Key

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Customer ID'
		dataType: string
		lineageTag: 1d7be705-dc88-46b1-8319-e5ad7bef243b
		summarizeBy: none
		sourceColumn: Customer ID

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Customer Name'
		dataType: string
		lineageTag: 6a6edea8-b164-44eb-8d88-fb151e5fe74a
		summarizeBy: none
		sourceColumn: Customer Name

		annotation SummarizationSetBy = Automatic

	column 'Customer Class'
		dataType: string
		lineageTag: 7ceffba6-ed38-4812-abfb-042a111a86f1
		summarizeBy: none
		sourceColumn: Customer Class

		annotation SummarizationSetBy = Automatic

	column Industry
		dataType: string
		lineageTag: b2431509-3c4e-4d26-b314-799b41d93ffb
		summarizeBy: none
		sourceColumn: Industry

		annotation SummarizationSetBy = Automatic

	column 'Account Manager'
		dataType: string
		lineageTag: 5b0d3f95-7eff-4cc1-bc94-d80d9f532c42
		summarizeBy: none
		sourceColumn: Account Manager

		annotation SummarizationSetBy = Automatic

	column Status
		dataType: string
		lineageTag: 90c3c11e-a6bc-40c7-b61c-18c336131ac7
		summarizeBy: none
		sourceColumn: Status

		annotation SummarizationSetBy = Automatic

	column Email
		dataType: string
		lineageTag: f3217c94-ac53-4482-9699-b9555ae90850
		summarizeBy: none
		sourceColumn: Email

		annotation SummarizationSetBy = Automatic

	column 'Created Date'
		dataType: dateTime
		lineageTag: 21b9a57f-a7c1-43b3-8ff1-946f46b2f8fa
		summarizeBy: none
		sourceColumn: Created Date

		annotation SummarizationSetBy = Automatic

	column Region
		dataType: string
		lineageTag: 15d94730-3e31-433c-a52a-b1a7464c8664
		summarizeBy: none
		sourceColumn: Region
		dataCategory: StateOrProvince

		annotation SummarizationSetBy = Automatic

	column 'Full Name Upper'
		dataType: string
		lineageTag: 956c78e8-b35e-477b-a91d-8f29d56525b9
		summarizeBy: none
		sourceColumn: Full Name Upper

		annotation SummarizationSetBy = Automatic

	column 'Name Length'
		dataType: string
		lineageTag: da3ba858-b96f-475f-8e88-356d4ef342b5
		summarizeBy: none
		sourceColumn: Name Length

		annotation SummarizationSetBy = Automatic

	column 'Name Initial'
		dataType: string
		lineageTag: c361daa0-d442-4e7b-aaa5-a8a2bc777a7c
		summarizeBy: none
		sourceColumn: Name Initial

		annotation SummarizationSetBy = Automatic

	column 'Display Name'
		dataType: string
		lineageTag: 26731bf3-e437-4f2c-80d0-f02da3a29e2e
		summarizeBy: none
		sourceColumn: Display Name

		annotation SummarizationSetBy = Automatic

	column 'Customer Since Year'
		dataType: string
		lineageTag: 9ced2b0b-6918-48cb-9b52-854129eb4bc1
		summarizeBy: none
		sourceColumn: Customer Since Year

		annotation SummarizationSetBy = Automatic

	column 'Tenure Days'
		dataType: string
		lineageTag: 45ea8ff7-a1a2-46e7-bf75-9fb38d1d25ab
		summarizeBy: none
		sourceColumn: Tenure Days

		annotation SummarizationSetBy = Automatic

	partition 'Dim Customer-3afb84e9-4488-4a91-9288-7dd2c26c4ef9' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Dim_Customer = Source
				in
				    Dim_Customer

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Dim Customer
```

#### `definition/tables/Dim Date.tmdl`

```
table 'Dim Date'
	lineageTag: 203ced6c-1560-4cd3-bc21-d3cc2983e000

	column 'Date Key'
		dataType: int64
		formatString: 0
		lineageTag: fe503b34-d271-420f-95ff-31824bff4d0d
		summarizeBy: sum
		sourceColumn: Date Key

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Calendar Date'
		dataType: dateTime
		lineageTag: dca93235-056a-4e98-9d1b-cd1f6a6cab83
		summarizeBy: none
		sourceColumn: Calendar Date

		annotation SummarizationSetBy = Automatic

	column Year
		dataType: int64
		formatString: 0
		lineageTag: 2ef765e8-ea11-4ab5-8f7a-22ae3d0105ce
		summarizeBy: sum
		sourceColumn: Year

		annotation SummarizationSetBy = Automatic

	column Quarter
		dataType: string
		lineageTag: 504958b4-c279-4a54-873b-dd80ecc243a1
		summarizeBy: none
		sourceColumn: Quarter

		annotation SummarizationSetBy = Automatic

	column 'Month Name'
		dataType: string
		lineageTag: f285dd87-1eb0-4486-821b-cc0d8b6e7446
		summarizeBy: none
		sourceColumn: Month Name
		sortByColumn: 'Month Number'

		annotation SummarizationSetBy = Automatic

	column 'Month Number'
		dataType: int64
		formatString: 0
		lineageTag: 1fd47f1e-1430-4bd9-9b5a-c27fba49ef86
		summarizeBy: sum
		sourceColumn: Month Number

		annotation SummarizationSetBy = Automatic

	column 'Week Number'
		dataType: int64
		formatString: 0
		lineageTag: 290513fb-a762-4c63-8293-ec47c62f25bb
		summarizeBy: sum
		sourceColumn: Week Number

		annotation SummarizationSetBy = Automatic

	column 'Day of Week'
		dataType: string
		lineageTag: 379fd00e-3d8c-4e91-b3bb-f36601e3e88d
		summarizeBy: none
		sourceColumn: Day of Week

		annotation SummarizationSetBy = Automatic

	column 'Fiscal Year'
		dataType: string
		lineageTag: ff23617e-d0cb-408a-a638-62629d9782eb
		summarizeBy: none
		sourceColumn: Fiscal Year

		annotation SummarizationSetBy = Automatic

	column 'Fiscal Period'
		dataType: string
		lineageTag: 0a1903b8-dbfb-4d53-8955-3e6bd01bc338
		summarizeBy: none
		sourceColumn: Fiscal Period

		annotation SummarizationSetBy = Automatic

	column 'Is Holiday'
		dataType: string
		lineageTag: 19ce2b4b-d338-47fa-8ff3-034b2c807a90
		summarizeBy: none
		sourceColumn: Is Holiday

		annotation SummarizationSetBy = Automatic

	hierarchy 'Calendar Hierarchy'
		lineageTag: e8572816-f12d-412c-bc8e-1e556c688ec8

		level Year
			ordinal: 0
			column: Year
			lineageTag: 090e60b7-599f-44e6-a592-c097eb1ef655

		level Quarter
			ordinal: 1
			column: Quarter
			lineageTag: df3bf2df-c7e1-479e-a530-72836bb87899

		level 'Month Name'
			ordinal: 2
			column: 'Month Name'
			lineageTag: 746bade1-08d0-480e-aee5-93f312ee21b6

		level 'Calendar Date'
			ordinal: 3
			column: 'Calendar Date'
			lineageTag: 8087ef6b-b061-429e-a513-7ca79bf3d7df


	hierarchy 'Fiscal Hierarchy'
		lineageTag: 4ceb5d19-68ad-488a-b299-85500b001a4f

		level 'Fiscal Year'
			ordinal: 0
			column: 'Fiscal Year'
			lineageTag: 82936d44-1fe4-44c1-84d8-52d71602827a

		level 'Fiscal Period'
			ordinal: 1
			column: 'Fiscal Period'
			lineageTag: 96cd2ee2-0347-49d7-a5d7-7e532925975b


	partition 'Dim Date-b5621c6b-ab1a-452d-94c0-aeb660b96d9b' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Dim_Date = Source
				in
				    Dim_Date

	annotation PBI_ResultType = Table
	annotation Copilot_DateTable = true
	annotation Copilot_TableDescription = Data from Dim Date
```

#### `definition/tables/Dim Employee.tmdl`

```
table 'Dim Employee'
	lineageTag: e75ad085-a301-480c-8e94-f89fea3ad09b

	column 'Employee Key'
		dataType: string
		lineageTag: 8e73be20-8578-4be5-89ad-d8ada4cde6b0
		summarizeBy: none
		sourceColumn: Employee Key

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Full Name'
		dataType: string
		lineageTag: 0fe91437-41e0-4dbe-8ec1-ed5c1084beda
		summarizeBy: none
		sourceColumn: Full Name

		annotation SummarizationSetBy = Automatic

	column Department
		dataType: string
		lineageTag: 2b225e69-1a28-4fae-9925-b5e781921130
		summarizeBy: none
		sourceColumn: Department

		annotation SummarizationSetBy = Automatic

	column 'Job Title'
		dataType: string
		lineageTag: bfef6854-6ac6-48e3-bb3f-7e33e3af5fe9
		summarizeBy: none
		sourceColumn: Job Title

		annotation SummarizationSetBy = Automatic

	column Salary
		dataType: string
		lineageTag: 5c927456-a85f-46cb-b536-07a0a5b5fd95
		summarizeBy: none
		sourceColumn: Salary

		annotation SummarizationSetBy = Automatic

	column 'Annual Salary'
		dataType: string
		lineageTag: 5d00302e-7d32-4ac0-9a24-0245e713d32d
		summarizeBy: none
		sourceColumn: Annual Salary

		annotation SummarizationSetBy = Automatic

	column 'Salary Band'
		dataType: string
		lineageTag: 01108c38-dd7d-46ff-b907-dd0c2bdc8d83
		summarizeBy: none
		sourceColumn: Salary Band

		annotation SummarizationSetBy = Automatic

	column 'Years of Service'
		dataType: string
		lineageTag: aba8a95a-15dd-436e-aa31-20687d51aa45
		summarizeBy: none
		sourceColumn: Years of Service

		annotation SummarizationSetBy = Automatic

	partition 'Dim Employee-34f19976-b110-4811-b454-ad0f4f2d7f98' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Dim_Employee = Source
				in
				    Dim_Employee

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Dim Employee
```

#### `definition/tables/Dim Geography.tmdl`

```
table 'Dim Geography'
	lineageTag: 5bbfd8ca-1eaf-46d3-9ca8-4153c8e94f8c

	column 'Geography Key'
		dataType: int64
		formatString: 0
		lineageTag: c9cf68d2-7f14-40c4-83d9-8c468e7c55ab
		summarizeBy: sum
		sourceColumn: Geography Key

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column Country
		dataType: string
		lineageTag: 67b595d7-30e2-4750-9140-e7aa108bfaa7
		summarizeBy: none
		sourceColumn: Country
		dataCategory: Country

		annotation SummarizationSetBy = Automatic

	column Region
		dataType: string
		lineageTag: ef735764-754a-467a-9c29-2382905b387e
		summarizeBy: none
		sourceColumn: Region
		dataCategory: StateOrProvince

		annotation SummarizationSetBy = Automatic

	column State
		dataType: string
		lineageTag: 67978c4e-a96f-405d-bfd0-cbac23145f16
		summarizeBy: none
		sourceColumn: State
		dataCategory: StateOrProvince

		annotation SummarizationSetBy = Automatic

	column City
		dataType: string
		lineageTag: 35c2f35b-48c8-4644-9b9a-77c8cfb95aed
		summarizeBy: none
		sourceColumn: City
		dataCategory: City

		annotation SummarizationSetBy = Automatic

	column 'Postal Code'
		dataType: string
		lineageTag: ac2df8bd-6ae6-4b5a-847c-1f8ae4ee2e7e
		summarizeBy: none
		sourceColumn: Postal Code

		annotation SummarizationSetBy = Automatic

	column Latitude
		dataType: double
		formatString: #,0.00
		lineageTag: cc4399fa-95a4-43b7-9617-76b43e6da1bc
		summarizeBy: sum
		sourceColumn: Latitude
		dataCategory: Latitude

		annotation SummarizationSetBy = Automatic

	column Longitude
		dataType: double
		formatString: #,0.00
		lineageTag: 93a5ccaa-4683-4452-8945-6724a0fd5b33
		summarizeBy: sum
		sourceColumn: Longitude
		dataCategory: Longitude

		annotation SummarizationSetBy = Automatic

	hierarchy 'Geography Hierarchy'
		lineageTag: 14b1b209-bad3-4ca0-a65b-77a75a95644c

		level Country
			ordinal: 0
			column: Country
			lineageTag: 5c95f6f7-ef92-4c1c-82c4-ec826851fed4

		level Region
			ordinal: 1
			column: Region
			lineageTag: 523370d1-4bec-4686-ab98-60421619dae8

		level State
			ordinal: 2
			column: State
			lineageTag: 8fcab994-edb5-4495-bff0-091e5da25008

		level City
			ordinal: 3
			column: City
			lineageTag: f0eb8ea2-eed3-4032-bb43-174257336886


	partition 'Dim Geography-0aa12e0f-3771-4676-a254-4c10364cfe06' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Dim_Geography = Source
				in
				    Dim_Geography

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Dim Geography
```

#### `definition/tables/Dim Product.tmdl`

```
table 'Dim Product'
	lineageTag: cc32f69a-b68e-4434-a904-6a35723d77bf

	column 'Product Key'
		dataType: int64
		formatString: 0
		lineageTag: 96c14ee0-7b3f-454b-b7bc-7101e0321c75
		summarizeBy: sum
		sourceColumn: Product Key

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Product ID'
		dataType: string
		lineageTag: 0f1dd972-8e2e-4c3a-8c64-98c63ebc5b8f
		summarizeBy: none
		sourceColumn: Product ID

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Product Name'
		dataType: string
		lineageTag: 7e5b115d-7b2d-4599-9a26-a71fa839feca
		summarizeBy: none
		sourceColumn: Product Name

		annotation SummarizationSetBy = Automatic

	column Category
		dataType: string
		lineageTag: 13eb2405-b9c3-4227-bd03-96d742495d28
		summarizeBy: none
		sourceColumn: Category

		annotation SummarizationSetBy = Automatic

	column 'Sub-Category'
		dataType: string
		lineageTag: ef4104e6-d167-4eec-a73e-ee89d1cdc42a
		summarizeBy: none
		sourceColumn: Sub-Category

		annotation SummarizationSetBy = Automatic

	column Brand
		dataType: string
		lineageTag: 1ebbf1c5-18a3-445e-b637-9c32dd1f7ed6
		summarizeBy: none
		sourceColumn: Brand

		annotation SummarizationSetBy = Automatic

	column 'Unit Price'
		dataType: double
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		lineageTag: 96f274e7-7633-4ae3-b2ae-b8bd7a20cfc5
		summarizeBy: sum
		sourceColumn: Unit Price

		annotation SummarizationSetBy = Automatic

	column 'Active Flag'
		dataType: string
		lineageTag: 500fbc46-9f9f-40f9-9109-9fe8e5e36ee4
		summarizeBy: none
		sourceColumn: Active Flag

		annotation SummarizationSetBy = Automatic

	column 'Reorder Point'
		dataType: int64
		formatString: 0
		lineageTag: 5f9707f5-067a-44cc-af92-c2aa6d726f93
		summarizeBy: sum
		sourceColumn: Reorder Point

		annotation SummarizationSetBy = Automatic

	column 'Price Tier'
		dataType: string
		lineageTag: d27aef8f-bc58-448a-9edb-ca5848a870ea
		summarizeBy: none
		sourceColumn: Price Tier

		annotation SummarizationSetBy = Automatic

	hierarchy 'Product Hierarchy'
		lineageTag: cb83be03-bd0e-4141-878f-9ff9e6bb30bd

		level Category
			ordinal: 0
			column: Category
			lineageTag: 2a58a49b-fb2e-4adc-952e-730d49bd0e30

		level 'Sub-Category'
			ordinal: 1
			column: 'Sub-Category'
			lineageTag: 14815ad3-f0e5-4006-8b15-6f11b416c14b

		level 'Product Name'
			ordinal: 2
			column: 'Product Name'
			lineageTag: db4716f3-b07d-4327-89b0-21533be6e177


	partition 'Dim Product-e4d3d297-aa5a-4efe-b55c-b0a6518f3d37' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Dim_Product = Source
				in
				    Dim_Product

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Dim Product
```

#### `definition/tables/Dim Warehouse.tmdl`

```
table 'Dim Warehouse'
	lineageTag: 1882f1d3-48ec-4442-b168-69cd4b1a2a7a

	column 'Warehouse Key'
		dataType: string
		lineageTag: a4877846-508f-461d-986e-e852d66d231a
		summarizeBy: none
		sourceColumn: Warehouse Key

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Warehouse Name'
		dataType: string
		lineageTag: da20cab7-01a8-4bf8-8e82-dbf818c07cc0
		summarizeBy: none
		sourceColumn: Warehouse Name

		annotation SummarizationSetBy = Automatic

	column 'Warehouse Region'
		dataType: string
		lineageTag: 3155cf85-b7b8-4133-8caf-0c12e66ceff5
		summarizeBy: none
		sourceColumn: Warehouse Region

		annotation SummarizationSetBy = Automatic

	column Capacity
		dataType: string
		lineageTag: 3a0259a4-a1e6-4470-abfc-1914ca64eafc
		summarizeBy: none
		sourceColumn: Capacity

		annotation SummarizationSetBy = Automatic

	partition 'Dim Warehouse-96150855-53ed-441e-bcad-e907d6f4da1d' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Dim_Warehouse = Source
				in
				    Dim_Warehouse

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Dim Warehouse
```

#### `definition/tables/Employee.tmdl`

```
table Employee
	lineageTag: 38ac063b-3d36-45fd-a3a1-5f66ef3301c1

	column 'Employee Key'
		dataType: string
		lineageTag: 61d52088-327d-473d-a65b-b6b7965a31ae
		summarizeBy: none
		sourceColumn: EMP_KEY

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Full Name' = [FIRST_NAME] & ' ' & [LAST_NAME]
		dataType: string
		lineageTag: 47cd9a5c-6632-406c-9b7a-776c39663f4f
		summarizeBy: none

	column 'Full Name Alt' = [FIRST_NAME] & ' ' & [LAST_NAME]
		dataType: string
		lineageTag: f92a9004-f517-49cf-a9ea-04f89c8fdd2c
		summarizeBy: none

	column 'Display Name' = UPPER(LEFT([LAST_NAME], 1)) & LOWER(MID([LAST_NAME], 2, LEN([LAST_NAME])))
		dataType: string
		lineageTag: 77d32ea7-b62f-4780-88c0-ee4cc350d1c4
		summarizeBy: none

	column 'Email Domain' = MID([EMAIL], FIND('@', [EMAIL]) + 1, 50)
		dataType: string
		lineageTag: 161c0682-5b39-4433-b575-b97cc5348423
		summarizeBy: none

	column 'Email Prefix' = LEFT([EMAIL], FIND('@', [EMAIL]) - 1)
		dataType: string
		lineageTag: ab58ceca-6c8f-4326-a747-d6ba64cc92ac
		summarizeBy: none

	column 'Name Length' = LEN([LAST_NAME])
		dataType: string
		lineageTag: cf036559-db32-4fc3-a2e0-54cc9659844c
		summarizeBy: none

	column 'Upper Name' = UPPER([LAST_NAME])
		dataType: string
		lineageTag: 6f4cbcad-fc00-4211-ab9f-f1a2f430ee40
		summarizeBy: none

	column 'Lower Name' = LOWER([FIRST_NAME])
		dataType: string
		lineageTag: 5dc63a78-bd84-4ef5-92be-6968ff2ece19
		summarizeBy: none

	column 'Trimmed Notes' = TRIM([NOTES])
		dataType: string
		lineageTag: f9529304-ef19-4413-bfca-d022c402f530
		summarizeBy: none

	column 'Left Trimmed' = TRIM([NOTES])
		dataType: string
		lineageTag: dcc79729-89d5-49aa-b128-8e8bf5680794
		summarizeBy: none

	column 'Right Trimmed' = TRIM([NOTES])
		dataType: string
		lineageTag: 74e09c7e-a844-4abf-9ac3-a8869457a2d6
		summarizeBy: none

	column 'Clean Phone' = SUBSTITUTE([PHONE], '-', '')
		dataType: string
		lineageTag: ffcfaeae-351c-4b45-ac8a-70c11c0089be
		summarizeBy: none

	column 'Padded Job Code' = REPT('0', 8 - LEN([JOB_CODE])) & [JOB_CODE]
		dataType: string
		lineageTag: 725aa56b-65a1-44e4-9dd7-4ea67daf2c17
		summarizeBy: none

	column 'Right Padded' = [JOB_CODE] & REPT(' ', 10 - LEN([JOB_CODE]))
		dataType: string
		lineageTag: c6c79800-bcc3-417a-b338-e1675b73447f
		summarizeBy: none

	column 'Name Char Code' = UNICODE([FIRST_NAME])
		dataType: string
		lineageTag: 904946ce-ef31-4328-84bd-14b440b7917a
		summarizeBy: none

	column 'Char From Code' = UNICHAR(65)
		dataType: string
		lineageTag: ea7315b5-a1b2-4c61-a47d-4eb4ed21c596
		summarizeBy: none

	column 'Translated Status' = SUBSTITUTE([STATUS], 'A', 'Active')
		dataType: string
		lineageTag: e5156bdc-a903-4b3f-90d3-fed49494a513
		summarizeBy: none

	column 'Safe Department' = IF(ISBLANK([DEPARTMENT]), 'Unassigned', [DEPARTMENT])
		dataType: string
		lineageTag: 55a73ed6-a87a-4b98-8964-f97379ad752f
		summarizeBy: none

	column 'NVL Department' = IF(ISBLANK([DEPARTMENT]), 'General', [DEPARTMENT])
		dataType: string
		lineageTag: 86112737-a231-43e8-940e-94335a086ef1
		summarizeBy: none

	column 'Department Label' = IF(ISBLANK([DEPARTMENT]), 'N/A', [DEPARTMENT])
		dataType: string
		lineageTag: 7020f2aa-1de9-4556-841f-a7b7461332d2
		summarizeBy: none

	column 'Coalesce Name' = COALESCE([DEPARTMENT], [JOB_CODE], 'None')
		dataType: string
		lineageTag: d5252385-a70e-42be-b1ad-fa27e1aa8536
		summarizeBy: none

	column 'NullIf Blank' = IF([STATUS] = '', BLANK(), [STATUS])
		dataType: string
		lineageTag: 3965c48c-5cf0-43ea-ac15-61dc2fdd2b5d
		summarizeBy: none

	column 'Greater Salary' = IF([SALARY] >= 50000, [SALARY], 50000)
		dataType: string
		lineageTag: 5361d725-484d-4cab-bb08-1ed6db4bec32
		summarizeBy: none

	column 'Lower Bound' = IF([SALARY] <= 200000, [SALARY], 200000)
		dataType: string
		lineageTag: 1b5e51d2-415c-4581-9bb6-554f2899dffe
		summarizeBy: none

	column 'Status Label (DECODE)' = ```
			SWITCH([STATUS],
			    'A', 'Active',
			    'I', 'Inactive',
			    'T', 'Terminated',
			    'Unknown'
			)
			```
		dataType: string
		lineageTag: c678619b-d8cf-4cc3-b280-1ad51f78a661
		summarizeBy: none

	column 'Salary Band' = ```
			SWITCH(TRUE(),
			    [SALARY] > 100000, 'Senior',
			    [SALARY] > 60000, 'Mid',
			    'Junior'
			)
			```
		dataType: string
		lineageTag: e4183d32-a0f5-4f5e-83fd-9c9d929e0332
		summarizeBy: none

	column 'Salary as Int' = INT([SALARY])
		dataType: string
		lineageTag: 2990ff1c-a9c4-4e5b-92f7-a0da5caee98a
		summarizeBy: none

	column 'Key as String' = FORMAT([EMP_KEY], "General")
		dataType: string
		lineageTag: 6bfac904-4d0a-40e7-b547-5962dd62cdb8
		summarizeBy: none

	column 'Numeric Code' = VALUE([JOB_CODE])
		dataType: string
		lineageTag: ef173894-7098-4439-a3e4-05d964094222
		summarizeBy: none

	column 'Hire Year' = YEAR([HIRE_DATE])
		dataType: string
		lineageTag: b39ae179-bff4-4f41-acdf-5ef04d069173
		summarizeBy: none

	column 'Hire Month' = MONTH([HIRE_DATE])
		dataType: string
		lineageTag: 1ba2204e-ef8b-4a93-be65-cd1b52a013da
		summarizeBy: none

	column 'Hire Quarter' = QUARTER([HIRE_DATE])
		dataType: string
		lineageTag: 269dfbcd-24fb-4c3f-8e1c-24b1b4b9ce21
		summarizeBy: none

	column 'Months Employed' = DATEDIFF([HIRE_DATE], TODAY(), MONTH)
		dataType: string
		lineageTag: cd1e326b-cdb5-4cd3-a0c5-6b224cc2667a
		summarizeBy: none

	column 'Next Review Date' = EDATE([HIRE_DATE], 12)
		dataType: string
		lineageTag: d51156ed-6052-4295-9c5f-ed5d0ccab566
		summarizeBy: none

	column 'End of Hire Month' = EOMONTH([HIRE_DATE], 0)
		dataType: string
		lineageTag: beb41367-e205-4b6d-ab07-abdd6b49aa37
		summarizeBy: none

	column Today = TODAY()
		dataType: string
		lineageTag: 1a65b268-fb41-49ca-841e-d2fdcd56be7f
		summarizeBy: none

	column 'Now Timestamp' = NOW()
		dataType: string
		lineageTag: 4cf7382f-f974-472a-95f3-5854e093ad9d
		summarizeBy: none

	column 'System Date' = NOW()
		dataType: string
		lineageTag: 3380e043-7a9d-487f-8f86-9bc26a1d3e8b
		summarizeBy: none

	column 'Hire Date Formatted' = FORMAT([HIRE_DATE], 'YYYY-MM-DD')
		dataType: string
		lineageTag: 0342ed79-42be-45b4-823a-e5938c39f8ac
		summarizeBy: none

	column 'Salary Abs Diff' = ABS([SALARY] - 75000)
		dataType: string
		lineageTag: d88debae-bc7a-4759-95bd-f9d1f051f096
		summarizeBy: none

	column 'Rounded Salary' = ROUND([SALARY], -3)
		dataType: string
		lineageTag: c66f34a3-b553-48c5-a4b4-ca35a9cbdc67
		summarizeBy: none

	column 'Salary Ceiling' = CEILING([SALARY] / 1000, 1)
		dataType: string
		lineageTag: 7fc2245f-7455-46a0-84c9-88c0b6733a20
		summarizeBy: none

	column 'Salary Floor' = FLOOR([SALARY] / 1000, 1)
		dataType: string
		lineageTag: 2f5a8ec6-e16c-42d8-9468-fa0ec06eabca
		summarizeBy: none

	column 'Salary Squared' = POWER([SALARY], 2)
		dataType: string
		lineageTag: 066a92bd-ee97-4898-88d5-a7c2d5e3605c
		summarizeBy: none

	column 'Salary Sqrt' = SQRT([SALARY])
		dataType: string
		lineageTag: 942fc644-5bdf-440f-b775-9a5bb34de77c
		summarizeBy: none

	column 'Salary Log' = LN([SALARY])
		dataType: string
		lineageTag: 828395b3-dbec-4918-b3c9-e2a4c433a54d
		summarizeBy: none

	column 'Salary Exp' = EXP(1)
		dataType: string
		lineageTag: c152f934-c5e6-41d6-ba1e-7279bec40b33
		summarizeBy: none

	column 'Key Modulo' = MOD([EMP_KEY], 10)
		dataType: string
		lineageTag: 7f4fadb0-fd44-4270-b490-8f6672d66c68
		summarizeBy: none

	column 'Salary Sign' = SIGN([SALARY] - 75000)
		dataType: string
		lineageTag: c1d4828a-c573-46b7-83f4-ace232252a2e
		summarizeBy: none

	measure 'Current User' = USERPRINCIPALNAME()
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: da11d494-7e32-45c6-a199-5ab212386e88

	column 'Random Value' = RAND()
		dataType: string
		lineageTag: 790af80b-9150-4f63-a98d-2d5843fee928
		summarizeBy: none

	partition 'Employee-ef8a59f1-df55-41a0-8667-cca1bb4862c5' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Employee = Source
				in
				    Employee

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Employee

	annotation __migration_note = broken-ref-auto-hidden
```

#### `definition/tables/Enterprise Sales.tmdl`

```
table 'Enterprise Sales'
	lineageTag: c62f26a8-17ee-4118-a29d-d11362879971

	column CustomerName
		dataType: string
		lineageTag: 35bff4ed-a782-460b-a042-0ea400beb62d
		summarizeBy: none
		sourceColumn: CustomerName

		annotation SummarizationSetBy = Automatic

	column Segment
		dataType: string
		lineageTag: 526f3e46-ee3f-4924-9191-2b0be14fe505
		summarizeBy: none
		sourceColumn: Segment

		annotation SummarizationSetBy = Automatic

	column Region
		dataType: string
		lineageTag: 4b4a9871-ed93-4664-b672-0fb660ff1093
		summarizeBy: none
		sourceColumn: Region
		dataCategory: StateOrProvince

		annotation SummarizationSetBy = Automatic

	column Country
		dataType: string
		lineageTag: 87b4ff52-0b13-41c7-9dde-166f9d244aab
		summarizeBy: none
		sourceColumn: Country
		dataCategory: Country

		annotation SummarizationSetBy = Automatic

	column Category
		dataType: string
		lineageTag: 82eac89d-0520-4bfe-a2f0-2fced8ac2c53
		summarizeBy: none
		sourceColumn: Category

		annotation SummarizationSetBy = Automatic

	column Subcategory
		dataType: string
		lineageTag: e65a5f87-66ea-4d81-bd83-e19403af08fa
		summarizeBy: none
		sourceColumn: Subcategory

		annotation SummarizationSetBy = Automatic

	column OrderDate
		dataType: dateTime
		lineageTag: e6156fba-d8bd-40ab-9579-84ad63a255ef
		summarizeBy: none
		sourceColumn: OrderDate

		annotation SummarizationSetBy = Automatic

	column Quantity
		dataType: int64
		formatString: 0
		lineageTag: bb326b89-3626-43a5-894f-6b0872512913
		summarizeBy: sum
		sourceColumn: Quantity

		annotation SummarizationSetBy = Automatic

	column UnitPrice
		dataType: string
		lineageTag: 1b8c34fc-5c27-40f8-add9-a4650501fd9c
		summarizeBy: none
		sourceColumn: UnitPrice

		annotation SummarizationSetBy = Automatic

	column UnitCost
		dataType: string
		lineageTag: c2d8293e-cf47-41de-9485-0fadf09e1158
		summarizeBy: none
		sourceColumn: UnitCost

		annotation SummarizationSetBy = Automatic

	column DiscountPct
		dataType: string
		lineageTag: 4a76f60a-3821-4b62-8cbf-36ae09776ce6
		summarizeBy: none
		sourceColumn: DiscountPct

		annotation SummarizationSetBy = Automatic

	column Revenue = [Quantity] * [UnitPrice] * (1 - [DiscountPct])
		dataType: string
		lineageTag: b7b3f33a-7498-4ebd-9fe0-e1ce714aa710
		summarizeBy: none

	column Profit = [Revenue] - ([Quantity] * [UnitCost])
		dataType: string
		lineageTag: 3c78f899-05c8-42b7-bb7f-db885d93ca1b
		summarizeBy: none

	column ProfitMargin = IF([Revenue] > 0, [Profit] / [Revenue], 0)
		dataType: string
		lineageTag: d8516ba5-c015-42ac-821a-93c8986ad36a
		summarizeBy: none

	partition 'Enterprise Sales-ce513f0f-9fa0-44b7-bae3-1031d30224e3' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Enterprise_Sales = Source
				in
				    Enterprise_Sales

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Enterprise Sales
```

#### `definition/tables/FACT_Orders.tmdl`

```
table FACT_Orders
	lineageTag: 34c0aa8e-fcfd-4653-b087-82222d763c27

	measure 'FACT_Orders_Profit' = SUMX('FACT_Orders', [AMOUNT]) * 0.2
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: eca8e25c-4741-4792-a646-a7349e26ec2a

	column 'Order ID'
		dataType: string
		lineageTag: fa867521-e376-4bdd-ad2d-b44edc1c12f1
		summarizeBy: none
		sourceColumn: ORDER_ID

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Order Amount'
		dataType: string
		lineageTag: d44ea09b-60ca-4411-915c-24c09433763e
		summarizeBy: none
		sourceColumn: AMOUNT

		annotation SummarizationSetBy = Automatic

	partition 'FACT_Orders-0b5b0997-e216-4f92-98d8-da18f32e9b53' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    FACT_Orders = Source
				in
				    FACT_Orders

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from FACT_Orders

	annotation __migration_note = broken-ref-auto-hidden
```

#### `definition/tables/FACT_Payroll.tmdl`

```
table FACT_Payroll
	lineageTag: da0a63ad-365a-4c1d-b86e-a4870635f14b

	measure 'Avg Salary' = AVERAGEX('FACT_Payroll', [SALARY])
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: 5e0a6240-7919-4e19-972d-ad32cbe2e962

	column 'Pay ID'
		dataType: string
		lineageTag: 10811eed-27cf-4bb7-9d3f-63073c0e4ffe
		summarizeBy: none
		sourceColumn: PAY_ID

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Gross Pay'
		dataType: string
		lineageTag: aac21e15-cace-43f9-9872-17cddbd581a2
		summarizeBy: none
		sourceColumn: GROSS_PAY

		annotation SummarizationSetBy = Automatic

	column 'Net Pay' = [GROSS_PAY] - [DEDUCTIONS]
		dataType: string
		lineageTag: f6923c96-2ebb-4c68-b648-4222c43ff74f
		summarizeBy: none

	partition 'FACT_Payroll-5897cb89-1feb-4ca1-aad4-7369505d54e6' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    FACT_Payroll = Source
				in
				    FACT_Payroll

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from FACT_Payroll

	annotation __migration_note = broken-ref-auto-hidden
```

#### `definition/tables/Fact GL.tmdl`

```
table 'Fact GL'
	lineageTag: 5371ebeb-7e26-4bcf-8436-4512f5789b05

	column Amount
		dataType: string
		lineageTag: 3de93eda-2be5-4623-974f-ea981e2d8e86
		summarizeBy: none
		sourceColumn: Amount

		annotation SummarizationSetBy = Automatic

	column 'Actual Amount'
		dataType: string
		lineageTag: 0bbc9ccc-f25b-497b-91ff-ea81677b86c2
		summarizeBy: none
		sourceColumn: Actual Amount

		annotation SummarizationSetBy = Automatic

	column 'Budget Amount'
		dataType: string
		lineageTag: ec7bb476-541e-437e-a494-ba29d40c045e
		summarizeBy: none
		sourceColumn: Budget Amount

		annotation SummarizationSetBy = Automatic

	column Variance
		dataType: string
		lineageTag: 23cf1523-5c6f-467c-a2b9-06b80788ef78
		summarizeBy: none
		sourceColumn: Variance

		annotation SummarizationSetBy = Automatic

	column 'Variance %'
		dataType: string
		lineageTag: 65ade486-34e6-480b-a5e7-acbd0d98f14e
		summarizeBy: none
		sourceColumn: Variance %

		annotation SummarizationSetBy = Automatic

	column 'Amount Prior Year'
		dataType: string
		lineageTag: 6ad5f421-6667-4ae5-a4e6-de4063d645af
		summarizeBy: none
		sourceColumn: Amount Prior Year

		annotation SummarizationSetBy = Automatic

	column 'Amount YTD'
		dataType: string
		lineageTag: c2bdfe85-58b6-421c-b14f-df07d53c805c
		summarizeBy: none
		sourceColumn: Amount YTD

		annotation SummarizationSetBy = Automatic

	partition 'Fact GL-2791a61a-330a-4817-9d0d-485c4d6a9cbd' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Fact_GL = Source
				in
				    Fact_GL

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Fact GL
```

#### `definition/tables/Fact Inventory.tmdl`

```
table 'Fact Inventory'
	lineageTag: a9b31bd9-553e-47ae-84a8-8a515d7c71b5

	column 'Quantity On Hand'
		dataType: string
		lineageTag: 9b684124-2b83-46bc-b90f-5dac91b6d01a
		summarizeBy: none
		sourceColumn: Quantity On Hand

		annotation SummarizationSetBy = Automatic

	column 'Quantity On Order'
		dataType: string
		lineageTag: e3f7c045-039a-4c24-b028-52cd8bf86f78
		summarizeBy: none
		sourceColumn: Quantity On Order

		annotation SummarizationSetBy = Automatic

	column 'Inventory Value'
		dataType: string
		lineageTag: 8ab516d2-5f7a-4430-9d39-1712b5eddaf0
		summarizeBy: none
		sourceColumn: Inventory Value

		annotation SummarizationSetBy = Automatic

	column 'Days of Supply'
		dataType: string
		lineageTag: 5dd7294e-546f-4a1f-af47-c1d7a08d8e9d
		summarizeBy: none
		sourceColumn: Days of Supply

		annotation SummarizationSetBy = Automatic

	column 'Below Reorder'
		dataType: string
		lineageTag: 58aaa98e-dd55-4d1f-942e-e8bc6de5db1d
		summarizeBy: none
		sourceColumn: Below Reorder

		annotation SummarizationSetBy = Automatic

	partition 'Fact Inventory-b2ae2598-6b30-4ba3-bb80-bc6b63458894' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Fact_Inventory = Source
				in
				    Fact_Inventory

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Fact Inventory
```

#### `definition/tables/Fact Sales.tmdl`

```
table 'Fact Sales'
	lineageTag: dd0cc1e5-394e-45ef-9d60-740cd73e1005

	column 'Sales ID'
		dataType: int64
		formatString: 0
		lineageTag: 65bb209d-2a3a-4943-9099-4a22f3df8534
		summarizeBy: sum
		sourceColumn: Sales ID

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Customer Key'
		dataType: int64
		formatString: 0
		lineageTag: 78dc822d-451e-4943-bf22-b34d4c11a2ae
		summarizeBy: sum
		sourceColumn: Customer Key

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Product Key'
		dataType: int64
		formatString: 0
		lineageTag: 605ddb2e-088e-4f47-b386-d9bcea0ec809
		summarizeBy: sum
		sourceColumn: Product Key

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Date Key'
		dataType: int64
		formatString: 0
		lineageTag: ef992880-f71d-45fe-a57a-0a05ab100be6
		summarizeBy: sum
		sourceColumn: Date Key

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column 'Geography Key'
		dataType: int64
		formatString: 0
		lineageTag: f1e30be3-4490-4b63-8075-5a9ebe4eda57
		summarizeBy: sum
		sourceColumn: Geography Key

		annotation SummarizationSetBy = Automatic
		annotation Copilot_Hidden = true

	column Revenue
		dataType: double
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		lineageTag: 7cd8ff39-646e-4323-b37e-3cc05a727be9
		summarizeBy: sum
		sourceColumn: Revenue

		annotation SummarizationSetBy = Automatic

	column Cost
		dataType: double
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		lineageTag: ece7c0d5-6475-4d4e-94e0-afc4fa7c895b
		summarizeBy: sum
		sourceColumn: Cost

		annotation SummarizationSetBy = Automatic

	column Quantity
		dataType: int64
		formatString: 0
		lineageTag: 5a217b37-54fe-4c75-aeab-eb8eb7d5fc4e
		summarizeBy: sum
		sourceColumn: Quantity

		annotation SummarizationSetBy = Automatic

	column 'Discount Amount'
		dataType: double
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		lineageTag: 5c4a0a3c-2a7d-45b7-88c1-94a334aae388
		summarizeBy: sum
		sourceColumn: Discount Amount

		annotation SummarizationSetBy = Automatic

	column Discount
		dataType: string
		lineageTag: 77783ccd-7f28-47a9-8a4b-b8889e3257cd
		summarizeBy: none
		sourceColumn: Discount

		annotation SummarizationSetBy = Automatic

	column 'Avg Deal Size'
		dataType: string
		lineageTag: 25c36e58-adc1-4024-bf17-8a6cc43ac605
		summarizeBy: none
		sourceColumn: Avg Deal Size

		annotation SummarizationSetBy = Automatic

	column 'Order Count'
		dataType: string
		lineageTag: e361bfef-4437-4d2e-9bc9-bc3e305b4b8d
		summarizeBy: none
		sourceColumn: Order Count

		annotation SummarizationSetBy = Automatic

	column 'Revenue LY'
		dataType: string
		lineageTag: ee3c5abe-58a8-4b2c-87f4-67b17156269a
		summarizeBy: none
		sourceColumn: Revenue LY

		annotation SummarizationSetBy = Automatic

	column 'Revenue YTD'
		dataType: string
		lineageTag: 24ee9046-6e0e-4010-ac88-165e357aef85
		summarizeBy: none
		sourceColumn: Revenue YTD

		annotation SummarizationSetBy = Automatic

	column 'Revenue QTD'
		dataType: string
		lineageTag: c1f2506c-bc92-449b-bc0c-9b509f9b2ed1
		summarizeBy: none
		sourceColumn: Revenue QTD

		annotation SummarizationSetBy = Automatic

	column 'Revenue Rolling 3M'
		dataType: string
		lineageTag: 25442bf5-9a82-4691-918a-c86edcdcd1b4
		summarizeBy: none
		sourceColumn: Revenue Rolling 3M

		annotation SummarizationSetBy = Automatic

	column 'Revenue Moving Avg 6M'
		dataType: string
		lineageTag: 769a3b3f-3fd2-490c-823a-c057af90e12e
		summarizeBy: none
		sourceColumn: Revenue Moving Avg 6M

		annotation SummarizationSetBy = Automatic

	column 'Revenue Running Sum'
		dataType: string
		lineageTag: 0efbefc3-bfc6-4cf4-b7f2-fa146d3bf813
		summarizeBy: none
		sourceColumn: Revenue Running Sum

		annotation SummarizationSetBy = Automatic

	column 'Revenue Growth %'
		dataType: string
		lineageTag: c01d12cb-6694-43e0-8714-9bb2d2ca7273
		summarizeBy: none
		sourceColumn: Revenue Growth %

		annotation SummarizationSetBy = Automatic

	column 'Revenue Rank'
		dataType: string
		lineageTag: b993f5dd-7854-4137-ae87-ba754992e20a
		summarizeBy: none
		sourceColumn: Revenue Rank

		annotation SummarizationSetBy = Automatic

	column 'Revenue Dense Rank'
		dataType: string
		lineageTag: 08ba3e9d-8c43-46c7-9efd-a8fafd6e19f7
		summarizeBy: none
		sourceColumn: Revenue Dense Rank

		annotation SummarizationSetBy = Automatic

	column 'Revenue Ntile 4'
		dataType: string
		lineageTag: 0a675de2-3fc2-4ef1-a1fb-6f44b92a539e
		summarizeBy: none
		sourceColumn: Revenue Ntile 4

		annotation SummarizationSetBy = Automatic

	column 'Revenue Ratio'
		dataType: string
		lineageTag: 33eb7e07-2ffd-404d-b8e5-fea2682a4266
		summarizeBy: none
		sourceColumn: Revenue Ratio

		annotation SummarizationSetBy = Automatic

	column 'Revenue Percentile'
		dataType: string
		lineageTag: 0b46ee5b-90e0-440e-bdde-c7488c7c78e6
		summarizeBy: none
		sourceColumn: Revenue Percentile

		annotation SummarizationSetBy = Automatic

	column 'Revenue Category'
		dataType: string
		lineageTag: ce82c361-ea07-4b75-b85e-52d39a2ecb41
		summarizeBy: none
		sourceColumn: Revenue Category

		annotation SummarizationSetBy = Automatic

	column 'High Value Orders'
		dataType: string
		lineageTag: 6cc528df-9700-4135-920c-f3b6e3de10fa
		summarizeBy: none
		sourceColumn: High Value Orders

		annotation SummarizationSetBy = Automatic

	column 'Discount Revenue'
		dataType: string
		lineageTag: 9010decb-736e-4a72-8711-e5db038c0062
		summarizeBy: none
		sourceColumn: Discount Revenue

		annotation SummarizationSetBy = Automatic

	column Profit = "Revenue" - "Cost"
		dataType: double
		lineageTag: 987f04f7-ef12-4d08-b2e2-5eed8c54c33e
		summarizeBy: none

	column 'Margin %' = ("Revenue" - "Cost") / IF("Revenue" = 0, BLANK(), "Revenue") * 100
		dataType: double
		lineageTag: fcf5c084-5066-48db-ab2c-46a9ecd8d527
		summarizeBy: none

	partition 'Fact Sales-4a7c337f-49e4-4444-a2af-56c5e2ea264f' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Fact_Sales = Source
				in
				    Fact_Sales

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Fact Sales
```

#### `definition/tables/General_Ledger.tmdl`

```
table General_Ledger
	lineageTag: 0ba99dbc-e7db-439d-9f96-ee3595eb49ae

	measure 'Net Amount' = SUMX('General_Ledger', [DEBIT_AMOUNT]) - SUMX('General_Ledger', [CREDIT_AMOUNT])
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: 0f95e147-7dc0-4ba8-8bef-b0089ac4f6f1

	measure 'Converted Amount' = SUMX('General_Ledger', [DEBIT_AMOUNT] * [EXCHANGE_RATE])
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: 49497cb8-8d4d-467b-93d4-4ba0b2be8ac9

	measure 'General_Ledger_Budget Variance' = SUMX('General_Ledger', [DEBIT_AMOUNT]) - SUMX('General_Ledger', [BUDGET_AMOUNT])
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: bee21df2-1e7a-4805-b650-c36d1ab996a4

	measure 'Budget Variance Pct' = ```
			SWITCH(TRUE(),
			    SUMX('General_Ledger', [BUDGET_AMOUNT]) = 0, 0,
			    (SUMX('General_Ledger', [DEBIT_AMOUNT]) - SUMX('General_Ledger', [BUDGET_AMOUNT])) / SUMX('General_Ledger', [BUDGET_AMOUNT]) * 100
			)
			```
		formatString: 0.00%
		displayFolder: Measures
		lineageTag: 6a6df5ce-5a38-45d5-88d0-a80bceaa8753

	measure 'Top N Accounts' = TOPN(10, 'General_Ledger', SUMX('General_Ledger', [DEBIT_AMOUNT]))
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: 7298a8f9-c8fe-4e21-a9b2-2c68a1022bf7

	partition 'General_Ledger-d4739203-7d07-4973-b6af-6e9abb2ceb20' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    General_Ledger = Source
				in
				    General_Ledger

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from General_Ledger

	annotation __migration_note = broken-ref-auto-hidden
```

#### `definition/tables/Product.tmdl`

```
table Product
	lineageTag: 176df368-fb52-4387-98bb-292567c46b54

	column 'Product Name'
		dataType: string
		lineageTag: 8c33a6c2-1c42-4884-8dfc-848ee1d22df5
		summarizeBy: none
		sourceColumn: PRODUCT_NAME

		annotation SummarizationSetBy = Automatic

	column Category
		dataType: string
		lineageTag: ec7fd4b9-6194-4640-9f47-20ead8d97e99
		summarizeBy: none
		sourceColumn: CATEGORY

		annotation SummarizationSetBy = Automatic

	column Subcategory
		dataType: string
		lineageTag: 0ac8c010-1786-4580-805d-3b1589f51e5a
		summarizeBy: none
		sourceColumn: SUBCATEGORY

		annotation SummarizationSetBy = Automatic

	column Brand
		dataType: string
		lineageTag: 6b303bdc-d3b0-4903-a1e6-7845f64cc57f
		summarizeBy: none
		sourceColumn: BRAND

		annotation SummarizationSetBy = Automatic

	column 'Margin Pct' = ([UNIT_PRICE] - [UNIT_COST]) / [UNIT_PRICE] * 100
		dataType: string
		lineageTag: ac44dc65-928f-46f1-97d8-d938d5a9183d
		summarizeBy: none

	partition 'Product-16120ef8-ac01-48a8-a36e-96e052489deb' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Product = Source
				in
				    Product

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Product

	annotation __migration_note = broken-ref-auto-hidden
```

#### `definition/tables/Returns.tmdl`

```
table Returns
	lineageTag: 55237309-fa44-40e7-8204-ba64f5e6a65b

	column 'Return Quantity'
		dataType: string
		lineageTag: fc400aa2-1075-470d-b7e7-1e50d87c2485
		summarizeBy: none
		sourceColumn: RETURN_QUANTITY

		annotation SummarizationSetBy = Automatic

	column 'Reason Code'
		dataType: string
		lineageTag: 67217074-5aa8-4270-bcf8-7fd10134b901
		summarizeBy: none
		sourceColumn: REASON_CODE

		annotation SummarizationSetBy = Automatic

	partition 'Returns-1a18d94a-0d40-4f1d-8132-2326b5f9b2e1' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Returns = Source
				in
				    Returns

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Returns
```

#### `definition/tables/Sales DB.tmdl`

```
table 'Sales DB'
	lineageTag: 4f984b72-5815-4b6a-bf19-a5a72a00ee0e

	column OrderID
		dataType: string
		lineageTag: fa5ac37d-2711-4f19-9fa0-10a598e1569b
		summarizeBy: none
		sourceColumn: OrderID

		annotation SummarizationSetBy = Automatic

	column CustomerName
		dataType: string
		lineageTag: 63261580-46ac-467c-985b-19f46398496c
		summarizeBy: none
		sourceColumn: CustomerName

		annotation SummarizationSetBy = Automatic

	column Region
		dataType: string
		lineageTag: 886e243a-69df-445b-834a-1557f9bcf24e
		summarizeBy: none
		sourceColumn: Region
		dataCategory: StateOrProvince

		annotation SummarizationSetBy = Automatic

	column OrderDate
		dataType: dateTime
		lineageTag: 284efd02-7b38-4037-b7f1-91b9405d2983
		summarizeBy: none
		sourceColumn: OrderDate

		annotation SummarizationSetBy = Automatic

	column Quantity
		dataType: int64
		formatString: 0
		lineageTag: 26753755-70e0-4767-9613-f65c2523750c
		summarizeBy: sum
		sourceColumn: Quantity

		annotation SummarizationSetBy = Automatic

	column Amount
		dataType: string
		lineageTag: ff857164-5140-4a5a-b48b-efe2820ac855
		summarizeBy: none
		sourceColumn: Amount

		annotation SummarizationSetBy = Automatic

	column Revenue = [Amount] * [Quantity]
		dataType: string
		lineageTag: 38f84771-feee-4b3e-a694-9db0e6b288ba
		summarizeBy: none

	partition 'Sales DB-5f2d042b-5322-4adc-9187-ccba39078d83' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Sales_DB = Source
				in
				    Sales_DB

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Sales DB
```

#### `definition/tables/Sales Data Warehouse.tmdl`

```
table 'Sales Data Warehouse'
	lineageTag: 803e2723-ebe7-4f0d-8744-5bc17db5ec66

	measure AvgOrderValue = SUMX('Sales Data Warehouse', [Revenue]) / COUNTD([OrderID])
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: 6d9acfae-f467-4207-81cc-b6e80fe47c57

	column OrderID
		dataType: string
		lineageTag: 943aff40-f95a-44a7-95e1-a015a0a2b342
		summarizeBy: none
		sourceColumn: OrderID

		annotation SummarizationSetBy = Automatic

	column OrderDate
		dataType: dateTime
		lineageTag: 1aeb34bc-50ba-4437-bd7b-9d603effcf17
		summarizeBy: none
		sourceColumn: OrderDate

		annotation SummarizationSetBy = Automatic

	column Year
		dataType: int64
		formatString: 0
		lineageTag: 09950a7a-559d-4f3a-a57b-284987a76aa8
		summarizeBy: sum
		sourceColumn: Year

		annotation SummarizationSetBy = Automatic

	column Quarter
		dataType: string
		lineageTag: c4c119c4-2bc0-4ef5-b885-311021dc9ee8
		summarizeBy: none
		sourceColumn: Quarter

		annotation SummarizationSetBy = Automatic

	column Month
		dataType: string
		lineageTag: 79e45b67-41fe-4861-834a-9566b6a27101
		summarizeBy: none
		sourceColumn: Month

		annotation SummarizationSetBy = Automatic

	column CustomerName
		dataType: string
		lineageTag: 382020ba-d92a-443b-bbc7-26b8859a5b06
		summarizeBy: none
		sourceColumn: CustomerName

		annotation SummarizationSetBy = Automatic

	column Segment
		dataType: string
		lineageTag: fbdaa73a-18b1-4cae-9022-80a4062426e0
		summarizeBy: none
		sourceColumn: Segment

		annotation SummarizationSetBy = Automatic

	column Region
		dataType: string
		lineageTag: e0ab7897-3488-4d83-8e0b-e3ae1a1a4431
		summarizeBy: none
		sourceColumn: Region
		dataCategory: StateOrProvince

		annotation SummarizationSetBy = Automatic

	column Country
		dataType: string
		lineageTag: dd2f4f9f-1a4e-4dfc-beac-4feb7cbb7016
		summarizeBy: none
		sourceColumn: Country
		dataCategory: Country

		annotation SummarizationSetBy = Automatic

	column State
		dataType: string
		lineageTag: b52a2ca6-03f9-4056-873d-d71a3220c8d5
		summarizeBy: none
		sourceColumn: State
		dataCategory: StateOrProvince

		annotation SummarizationSetBy = Automatic

	column City
		dataType: string
		lineageTag: 58a5180f-3806-4c23-a21c-6711cb7c23fc
		summarizeBy: none
		sourceColumn: City
		dataCategory: City

		annotation SummarizationSetBy = Automatic

	column Category
		dataType: string
		lineageTag: b17f0e11-d685-488e-aa0a-35a92c118e62
		summarizeBy: none
		sourceColumn: Category

		annotation SummarizationSetBy = Automatic

	column Subcategory
		dataType: string
		lineageTag: cdd32c5a-057f-43a1-9e8a-3031745b422e
		summarizeBy: none
		sourceColumn: Subcategory

		annotation SummarizationSetBy = Automatic

	column Brand
		dataType: string
		lineageTag: 410145d3-cfd9-4d03-91d7-f99ef9b9fcc9
		summarizeBy: none
		sourceColumn: Brand

		annotation SummarizationSetBy = Automatic

	column ProductName
		dataType: string
		lineageTag: 4cce60f3-2358-4691-ae97-a03fe6b3f061
		summarizeBy: none
		sourceColumn: ProductName

		annotation SummarizationSetBy = Automatic

	column StoreName
		dataType: string
		lineageTag: 56de1dc1-47e8-459d-9518-891a85fa4155
		summarizeBy: none
		sourceColumn: StoreName

		annotation SummarizationSetBy = Automatic

	column StoreType
		dataType: string
		lineageTag: 004e7c99-aeba-4224-ab27-0455ffbafa48
		summarizeBy: none
		sourceColumn: StoreType

		annotation SummarizationSetBy = Automatic

	column Quantity
		dataType: int64
		formatString: 0
		lineageTag: 857a311e-4ce1-49f9-bb85-640c1cc74ac0
		summarizeBy: sum
		sourceColumn: Quantity

		annotation SummarizationSetBy = Automatic

	column UnitPrice
		dataType: string
		lineageTag: d6f93dfb-786a-4f80-82db-a3c751575f84
		summarizeBy: none
		sourceColumn: UnitPrice

		annotation SummarizationSetBy = Automatic

	column UnitCost
		dataType: string
		lineageTag: db02d538-5a01-44e5-bcd7-ce4cb4a89925
		summarizeBy: none
		sourceColumn: UnitCost

		annotation SummarizationSetBy = Automatic

	column DiscountPct
		dataType: string
		lineageTag: 8c0840b9-3190-4ab5-b6ba-333abaf4d0a4
		summarizeBy: none
		sourceColumn: DiscountPct

		annotation SummarizationSetBy = Automatic

	column TaxAmount
		dataType: string
		lineageTag: 41c10678-4b42-468e-a6ea-afe1ccb4a03b
		summarizeBy: none
		sourceColumn: TaxAmount

		annotation SummarizationSetBy = Automatic

	column FreightCost
		dataType: string
		lineageTag: 691d6c48-d0a3-46fc-96c1-bf461c42ee5d
		summarizeBy: none
		sourceColumn: FreightCost

		annotation SummarizationSetBy = Automatic

	column Revenue = [Quantity] * [UnitPrice] * (1 - [DiscountPct])
		dataType: string
		lineageTag: 63e13a72-ced0-4446-9f45-41f9904be302
		summarizeBy: none

	column TotalCost = [Quantity] * [UnitCost] + [TaxAmount] + [FreightCost]
		dataType: string
		lineageTag: bc24784d-3ea6-461c-ab95-f8f3cfa672fe
		summarizeBy: none

	column Profit = [Revenue] - [TotalCost]
		dataType: string
		lineageTag: ebd63212-00d0-4398-a04d-3065d9d8c277
		summarizeBy: none

	column ProfitMargin = IF([Revenue] > 0, [Profit] / [Revenue] * 100, 0)
		dataType: string
		lineageTag: 1cfbe731-a044-4165-a8ff-6884362326c4
		summarizeBy: none

	column DiscountAmount = [Quantity] * [UnitPrice] * [DiscountPct]
		dataType: string
		lineageTag: b0562109-c6f5-4a84-a36d-17ce3085d1d1
		summarizeBy: none

	column PriceCategory = IF([UnitPrice] > 500, "Premium", IF([UnitPrice] > 100, "Mid-Range", "Budget"))
		dataType: string
		lineageTag: b1cf5776-0ccb-4979-ba31-f08282a2d5df
		summarizeBy: none

	column IsHighValue = IF([Revenue] > 5000, "Yes", "No")
		dataType: string
		lineageTag: b3a65a6d-1f6b-486f-9d70-261b560c811f
		summarizeBy: none

	hierarchy Date
		lineageTag: e7a9d8a2-7d32-48e6-9391-1c974dc65cfa

		level Year
			ordinal: 0
			column: Year
			lineageTag: f42675d1-eb45-400e-86b8-ec649af87cc3

		level Quarter
			ordinal: 1
			column: Quarter
			lineageTag: 5b15a330-f817-409d-b25d-b9ebc962b541

		level Month
			ordinal: 2
			column: Month
			lineageTag: ff928b37-16de-4e56-b531-3f25d43999dd


	partition 'Sales Data Warehouse-74ffb9aa-3680-40c0-ad5a-314484e019c1' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Sales_Data_Warehouse = Source
				in
				    Sales_Data_Warehouse

	annotation PBI_ResultType = Table
	annotation Copilot_DateTable = true
	annotation Copilot_TableDescription = Data from Sales Data Warehouse
```

#### `definition/tables/Sales.tmdl`

```
table Sales
	lineageTag: d9b68c83-187d-46ef-8540-41adc779fbed

	measure Revenue = SUMX('Sales', [QUANTITY] * [UNIT_PRICE] * (1 - [DISCOUNT_PCT]))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: 55d97a02-ff21-4ed8-8e25-548b04eb1a4f

	measure Cost = SUMX('Sales', [QUANTITY] * [UNIT_COST])
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: 04584ad6-000f-4030-9f4b-3eb82f295545

	measure Profit = SUMX('Sales', [QUANTITY] * [UNIT_PRICE] * (1 - [DISCOUNT_PCT])) - SUMX('Sales', [QUANTITY] * [UNIT_COST])
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: efbccc39-8b07-40d3-afbc-dc7429b6f3f5

	measure 'Profit Margin' = ```
			SWITCH(TRUE(),
			    SUMX('Sales', [QUANTITY] * [UNIT_PRICE]) = 0, 0,
			    (SUMX('Sales', [QUANTITY] * [UNIT_PRICE] * (1 - [DISCOUNT_PCT])) - SUMX('Sales', [QUANTITY] * [UNIT_COST])) / SUMX('Sales', [QUANTITY] * [UNIT_PRICE]) * 100
			)
			```
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: c26f7267-db8a-48f0-942f-90729ec820bb

	measure 'Return Rate' = ```
			SWITCH(TRUE(),
			    SUMX('Sales', [QUANTITY]) = 0, 0,
			    SUMX('Sales', [RETURN_QUANTITY]) / SUMX('Sales', [QUANTITY]) * 100
			)
			```
		formatString: 0.00%
		displayFolder: Measures
		lineageTag: 2e801646-1641-452f-b397-0225049516ce

	measure 'Budget Variance' = SUMX('Sales', [QUANTITY] * [UNIT_PRICE]) - SUMX('Sales', [BUDGET_AMOUNT])
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: c7841cfa-5e4b-480e-abe0-d163db4a7b99

	column Quantity
		dataType: string
		lineageTag: 12163947-898a-43de-91a8-04085e545f8d
		summarizeBy: none
		sourceColumn: QUANTITY

		annotation SummarizationSetBy = Automatic

	partition 'Sales-541272b6-d017-4056-ad74-fd7618a5b353' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Sales = Source
				in
				    Sales

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Sales

	annotation __migration_note = broken-ref-auto-hidden
```

#### `definition/tables/Sales_Analytics.tmdl`

```
table Sales_Analytics
	lineageTag: 4c12f96e-ede4-4e47-85fe-ef071f467b23

	measure 'Total Revenue' = SUMX('Sales_Analytics', [REVENUE])
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: 5cffc5a7-a28b-4e4e-84c4-002d2b015b08

	measure 'Total Cost' = SUMX('Sales_Analytics', [COST])
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: 0e990340-2585-40c8-9350-fd24ad719467

	measure 'Total Quantity' = SUMX('Sales_Analytics', [QUANTITY])
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: 67831c1f-2a6d-43a3-ad49-d6b0b174cf49

	measure 'Revenue Prior Year' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATEADD('Date'[Date], -1, YEAR))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence
		lineageTag: 9a87b821-95e1-45c8-a89b-e46a7d1cbe8e

	measure 'Revenue Prior Quarter' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATEADD('Date'[Date], -1, QUARTER))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence
		lineageTag: 6fc194e9-019c-4b18-ad1c-4ae6fe0241db

	measure 'Revenue Prior Month' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATEADD('Date'[Date], -1, MONTH))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence
		lineageTag: 505dcb55-a59e-4269-8835-b7ac9351ec53

	measure 'Revenue YTD' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESYTD('Date'[Date]))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence
		lineageTag: c7450d79-56c1-42e1-a0f3-e0f1d1c52138

	measure 'Revenue QTD' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESQTD('Date'[Date]))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence
		lineageTag: cb1e5546-4cc4-4189-b4dd-f4ae4f17c541

	measure 'Revenue MTD' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESMTD('Date'[Date]))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence
		lineageTag: d01777af-ca5b-41e2-ac83-fe011d3dc8b0

	measure 'Revenue WTD' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -7, DAY))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence
		lineageTag: 0b88178b-2c58-466d-970d-4816b75b79d0

	measure 'Rolling 30 Day Revenue' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESINPERIOD('Date'[Date], MAX('Date'[Date]), 30, DAY))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence
		lineageTag: b351bbe6-afce-4bb3-9c62-d862320d9e19

	measure 'Rolling 90 Day Revenue' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESINPERIOD('Date'[Date], MAX('Date'[Date]), 90, DAY))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence
		lineageTag: 7e865f11-9660-44e1-a7f2-2714e1716a0e

	measure 'Running Total Revenue' = CALCULATE(SUMX('Sales_Analytics', [REVENUE], FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date]))))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Time Intelligence
		lineageTag: 16e0c450-b347-4eb8-9730-4df675be9018

	measure 'Running Count' = CALCULATE(COUNTROWS('Sales_Analytics'), FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date])))
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: 09571961-335d-4e77-a558-7282f3c91fb3

	measure 'Running Max Revenue' = CALCULATE(MAX(SUMX('Sales_Analytics', [REVENUE]), FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date]))))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: 190ee9e9-e6ce-4aa4-a1c6-3219c9654a3d

	measure 'Running Min Revenue' = CALCULATE(MIN(SUMX('Sales_Analytics', [REVENUE]), FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date]))))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: cdcae650-e51c-493c-be07-bf164f547778

	measure '7 Day Moving Avg' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -7, DAY)) / 7
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: 22e86af4-aa85-419d-8594-54ed3c871570

	measure '30 Day Moving Sum' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -30, DAY))
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: 457ed9fb-218c-4e72-b540-c7c4a1837da2

	measure 'Same Period Last Year' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), PARALLELPERIOD('Date'[Date], -1, YEAR))
		formatString: #,0.00
		displayFolder: Time Intelligence
		lineageTag: e2b831ae-ff48-4dd3-9a27-307988dcbeba

	measure 'Opening Balance Year' = OPENINGBALANCEYEAR(SUMX('Sales_Analytics', [REVENUE], 'Date'[Date]))
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: 9600528e-3e3f-4faa-b46b-7f48b7757148

	measure 'Closing Balance Year' = CLOSINGBALANCEYEAR(SUMX('Sales_Analytics', [REVENUE], 'Date'[Date]))
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: d8bac78b-0b68-41d4-ad1f-61ff1bea9e8f

	measure 'Revenue Rank' = RANKX(ALL('Sales_Analytics'), SUMX('Sales_Analytics', [REVENUE]))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: 6ae83570-1ae2-4970-9948-f7eb7c4cf6ae

	measure 'Revenue Dense Rank' = RANKX(ALL('Sales_Analytics'), SUMX('Sales_Analytics', [REVENUE], , ASC, DENSE))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: e6a000a2-5d30-4cc2-8fe8-a990539b2539

	measure 'Revenue Share' = DIVIDE(SUM('Sales_Analytics'[REVENUE], CALCULATE(SUM('Sales_Analytics'[REVENUE], ALL('Sales_Analytics')))))
		formatString: \$#,0.00;(\$#,0.00);\$#,0.00
		displayFolder: Measures
		lineageTag: 16338e1f-f18a-4e05-9ab1-992f3b4dd914

	measure 'Distinct Products Sold' = DISTINCTCOUNT('Sales_Analytics'[PRODUCT_KEY])
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: eaac56a6-d94e-4759-ad09-ef316f54a512

	measure 'Forecast Variance' = SUMX('Sales_Analytics', [REVENUE]) - SUMX('Sales_Analytics', [FORECAST_AMOUNT])
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: 7c611ea0-d79f-4b33-8088-a7a469ba326e

	column 'Revenue Quartile' = INT(RANKX(ALL('Sales_Analytics'), 1, , ASC) * 4 / COUNTROWS(ALL('Sales_Analytics'))) + 1
		dataType: string
		lineageTag: ff229bd0-9571-492d-9983-857ebb63e9dc
		summarizeBy: none

	column 'Cumulative Distribution' = DIVIDE(RANKX(ALL('Sales_Analytics'), 1, , ASC), COUNTROWS(ALL('Sales_Analytics')))
		dataType: string
		lineageTag: 0932314a-87d3-4e7f-b8de-428b92130ed0
		summarizeBy: none

	column 'Percentile Rank' = DIVIDE(RANKX(ALL('Sales_Analytics'), 1, , ASC) - 1, COUNTROWS(ALL('Sales_Analytics')) - 1)
		dataType: string
		lineageTag: 4964bab2-8e3f-4316-b0a1-48ff7939874a
		summarizeBy: none

	column 'Median Revenue' = MEDIAN('Sales_Analytics'[REVENUE])
		dataType: string
		lineageTag: c3e43c4c-fa22-416d-a09f-5009d2c8a0d3
		summarizeBy: none

	column 'Revenue StdDev' = STDEV.S('Sales_Analytics'[REVENUE])
		dataType: string
		lineageTag: 501bcc2d-a1c1-4644-bddb-5ec6ba014a36
		summarizeBy: none

	column 'Revenue 90th Pct' = PERCENTILEX.INC('Sales_Analytics', 'Sales_Analytics'[REVENUE], 0.9)
		dataType: string
		lineageTag: 69bc599f-2920-4069-9343-1408a8005110
		summarizeBy: none

	column 'High Value Sales Count' = CALCULATE(COUNTX('Sales_Analytics', [REVENUE]), [REVENUE] > 10000)
		dataType: string
		lineageTag: 8d5b0142-4b3e-42ad-a96b-a600c7bfeb89
		summarizeBy: none

	column 'Discounted Revenue Sum' = CALCULATE(SUMX('Sales_Analytics', [REVENUE]), [DISCOUNT_AMOUNT] > 0)
		dataType: string
		lineageTag: feb54e88-9e26-4b5d-b5fc-be79fb4d8355
		summarizeBy: none

	partition 'Sales_Analytics-e295bac1-58df-4e0e-b08c-0ccd78162394' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Sales_Analytics = Source
				in
				    Sales_Analytics

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Sales_Analytics

	annotation __migration_note = broken-ref-auto-hidden
```

#### `definition/tables/Scenario.tmdl`

```
table Scenario
	lineageTag: 66914318-908d-479f-920f-e63083aaddc8

	column 'Bud Variance' = Actual - Budget
		dataType: string
		lineageTag: efc0679d-b69c-46f1-bfb0-b3c04c4a5b10
		summarizeBy: none

	column 'Bud Var Pct' = ROUND((Actual - Budget) % Budget, 4)
		dataType: string
		lineageTag: 1f7884d8-689f-4247-b6c1-6232e558e5e1
		summarizeBy: none

	column 'Fcst Variance' = Actual - Forecast
		dataType: string
		lineageTag: 4a67f3a7-29ac-48fa-abef-7fefd77e0fab
		summarizeBy: none

	column 'YoY Growth' = ROUND((Actual - BLANK() /* @PRIOR — no DAX equivalent, requires manual review */)) % BLANK() /* @PRIOR — no DAX equivalent, requires manual review */, 4
		dataType: string
		lineageTag: 7d0f4aac-6eaf-4044-9b04-9ce4df5dd22f
		summarizeBy: none

	column Variance = Actual - Budget
		dataType: string
		lineageTag: 49253f32-28e5-4fe1-8988-927d7856b8ea
		summarizeBy: none

	column 'Variance Pct' = ROUND((Actual - Budget) % Budget, 4)
		dataType: string
		lineageTag: 9bdc402a-e9a8-4dfb-8581-1e7b9aa3bb49
		summarizeBy: none

	partition 'Scenario-07917907-7857-4810-aa26-a409732aba5e' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Scenario = Source
				in
				    Scenario

	annotation PBI_ResultType = Table
	annotation Copilot_TableDescription = Data from Scenario
```

#### `definition/tables/Time.tmdl`

```
table Time
	lineageTag: 35d37e08-0e2d-40cc-b971-b1a28f19ee18

	measure YTD = BLANK() /* @SUMRANGE — no DAX equivalent, requires manual review */
		formatString: #,0.00
		displayFolder: Measures
		lineageTag: 009996b0-4f12-48b7-a150-76fbcfbe34b1

	column Date
		dataType: string
		lineageTag: 0aaaa81d-6402-4ac3-9efe-b72c72356345
		summarizeBy: none
		sourceColumn: FULL_DATE

		annotation SummarizationSetBy = Automatic

	column Year
		dataType: string
		lineageTag: 0ff1236b-e95c-4063-9034-e7bd6f738ef5
		summarizeBy: none
		sourceColumn: YEAR

		annotation SummarizationSetBy = Automatic

	column Quarter
		dataType: string
		lineageTag: 602bc5ce-ed2a-4ee2-b54b-fe3c2f256e9c
		summarizeBy: none
		sourceColumn: QUARTER

		annotation SummarizationSetBy = Automatic

	column Month
		dataType: string
		lineageTag: 02b8a3ed-6b6c-431b-aadd-4eedcb017605
		summarizeBy: none
		sourceColumn: MONTH_NAME

		annotation SummarizationSetBy = Automatic

	column 'Prior Year' = BLANK() /* @PRIOR — no DAX equivalent, requires manual review */
		dataType: string
		lineageTag: 30baf790-2cfd-4f05-b1a6-321360dad2c5
		summarizeBy: none

	hierarchy 'Date Hierarchy'
		lineageTag: d45cf382-684a-4a88-bd04-b7d1182d9437

		level Year
			ordinal: 0
			column: Year
			lineageTag: f0c5e78d-0a83-4d1b-ba32-4d9d9217cdb8

		level Quarter
			ordinal: 1
			column: Quarter
			lineageTag: 0ab57655-6ca1-4d51-8fbe-fe9ec3f7e16d

		level Month
			ordinal: 2
			column: Month
			lineageTag: a6f35971-d073-4390-a974-f63bd46f0930

		level Day
			ordinal: 4
			column: Date
			lineageTag: faed0cd1-a37a-43c3-b660-b7bfff99c27e


	partition 'Time-93713fc0-1ace-420e-9f22-ccef7fa7dc8d' = m
		mode: import
		source =
				let
				    Source = #table(type table [], {}),
				    // TODO: Configure data source
				    Time = Source
				in
				    Time

	annotation PBI_ResultType = Table
	annotation Copilot_DateTable = true
	annotation Copilot_TableDescription = Data from Time
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
| Total assets discovered | **250** |
| Physical tables | 57 |
| Logical tables / dimensions | 51 |
| Analyses / worksheets | 19 |
| Dashboards | 6 |
| Security roles | 9 |
| Prompts / parameters | 19 |
| DDL statements generated | 57 |
| TMDL files generated | 39 |
| Expressions translated | 134 |
| Elapsed time | 0.7s |

---

*Report generated by OAC-to-Fabric Migration Accelerator*