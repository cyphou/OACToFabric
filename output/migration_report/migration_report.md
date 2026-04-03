# Migration Report

> **Generated:** 2026-04-03 10:12:56 UTC  
> **Total assets discovered:** 250  
> **Elapsed time:** 0.3s  
> **Output directory:** `output\migration_report`

---

## 1. Discovery Summary

### Assets by Source Platform

| Source | Assets | Types |
|--------|--------|-------|
| **cognos** | 18 | analysis, dataModel, prompt |
| **essbase** | 15 | logicalTable |
| **oac_api** | 34 | agent, analysis, dashboard, dataModel, dataflow, filter, logicalTable, physicalTable, prompt |
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
| logicalTable | 50 | essbase, oac_api, rpd, tableau |
| physicalTable | 58 | oac_api, qlik, rpd |
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
| 95 | Fact Sales | physicalTable | oac_api | `/oac/data_model_star_schema/Fact Sales` |
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

**Tables generated:** 58

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
| 14 | `Fact Sales` | oac_api | Lakehouse (Delta) |
| 15 | `DIM_DATE` | rpd | Lakehouse (Delta) |
| 16 | `DIM_EMPLOYEE` | rpd | Lakehouse (Delta) |
| 17 | `DIM_ACCOUNT` | rpd | Lakehouse (Delta) |
| 18 | `FACT_GL` | rpd | Lakehouse (Delta) |
| 19 | `FACT_BUDGET` | rpd | Lakehouse (Delta) |
| 20 | `REF_EXCHANGE_RATE` | rpd | Lakehouse (Delta) |
| 21 | `FACT_SALES` | rpd | Lakehouse (Delta) |
| 22 | `FACT_INVENTORY` | rpd | Lakehouse (Delta) |
| 23 | `DIM_CUSTOMER` | rpd | Lakehouse (Delta) |
| 24 | `DIM_PRODUCT` | rpd | Lakehouse (Delta) |
| 25 | `DIM_DATE` | rpd | Lakehouse (Delta) |
| 26 | `DIM_GEOGRAPHY` | rpd | Lakehouse (Delta) |
| 27 | `DIM_CHANNEL` | rpd | Lakehouse (Delta) |
| 28 | `DIM_WAREHOUSE` | rpd | Lakehouse (Delta) |
| 29 | `DIM_EMPLOYEE` | rpd | Lakehouse (Delta) |
| 30 | `FACT_GL` | rpd | Lakehouse (Delta) |
| 31 | `EMPLOYEES` | rpd | Lakehouse (Delta) |
| 32 | `DEPARTMENTS` | rpd | Lakehouse (Delta) |
| 33 | `LOCATIONS` | rpd | Lakehouse (Delta) |
| 34 | `PAYROLL` | rpd | Lakehouse (Delta) |
| 35 | `CUSTOMERS` | rpd | Lakehouse (Delta) |
| 36 | `ORDERS` | rpd | Lakehouse (Delta) |
| 37 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 38 | `RegionMapping` | qlik | Lakehouse (Delta) |
| 39 | `Stores` | qlik | Lakehouse (Delta) |
| 40 | `Channels` | qlik | Lakehouse (Delta) |
| 41 | `OrderEnriched` | qlik | Lakehouse (Delta) |
| 42 | `CustomerSummary` | qlik | Lakehouse (Delta) |
| 43 | `ProductPerformance` | qlik | Lakehouse (Delta) |
| 44 | `Returns` | qlik | Lakehouse (Delta) |
| 45 | `Budget` | qlik | Lakehouse (Delta) |
| 46 | `dim_customer` | qlik | Lakehouse (Delta) |
| 47 | `dim_product` | qlik | Lakehouse (Delta) |
| 48 | `fact_orders` | qlik | Lakehouse (Delta) |
| 49 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 50 | `Regions` | qlik | Lakehouse (Delta) |
| 51 | `OrderSummary` | qlik | Lakehouse (Delta) |
| 52 | `Products` | qlik | Lakehouse (Delta) |
| 53 | `dim_customer` | qlik | Lakehouse (Delta) |
| 54 | `fact_orders` | qlik | Lakehouse (Delta) |
| 55 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 56 | `unnamed_load` | qlik | Lakehouse (Delta) |
| 57 | `Orders` | qlik | Lakehouse (Delta) |
| 58 | `customers` | qlik | Lakehouse (Delta) |

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

#### `Fact Sales`

```sql
CREATE TABLE IF NOT EXISTS Fact_Sales (
    Sales_ID INT,
    Customer_Key INT,
    Product_Key INT,
    Date_Key INT,
    Geography_Key INT,
    Revenue STRING,
    Cost STRING,
    Quantity INT,
    Discount_Amount STRING,
    Profit STRING,
    Margin__ STRING
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

**TMDL files generated:** 40  
**Expressions translated:** 175  
**Warnings:** 71  
**Items requiring review:** 64

### Generated Files

| File | Size (chars) |
|------|-------------|
| `.platform` | 304 |
| `definition/database.tmdl` | 101 |
| `definition/expressions.tmdl` | 220 |
| `definition/perspectives.tmdl` | 6,785 |
| `definition/roles.tmdl` | 0 |
| `definition/tables/Accounts.tmdl` | 1,374 |
| `definition/tables/Budget.tmdl` | 529 |
| `definition/tables/Budget_&_Forecast.tmdl` | 1,644 |
| `definition/tables/Calendar.tmdl` | 4,608 |
| `definition/tables/Channel.tmdl` | 706 |
| `definition/tables/Currency.tmdl` | 854 |
| `definition/tables/Customer.tmdl` | 1,272 |
| `definition/tables/DIM_Customer.tmdl` | 811 |
| `definition/tables/DIM_Employee.tmdl` | 1,210 |
| `definition/tables/DIM_Location.tmdl` | 925 |
| `definition/tables/Dim_Channel.tmdl` | 914 |
| `definition/tables/Dim_Customer.tmdl` | 2,423 |
| `definition/tables/Dim_Date.tmdl` | 2,303 |
| `definition/tables/Dim_Employee.tmdl` | 1,878 |
| `definition/tables/Dim_Geography.tmdl` | 1,658 |
| `definition/tables/Dim_Product.tmdl` | 1,956 |
| `definition/tables/Dim_Warehouse.tmdl` | 1,100 |
| `definition/tables/Employee.tmdl` | 8,612 |
| `definition/tables/Enterprise_Sales.tmdl` | 2,699 |
| `definition/tables/Entity.tmdl` | 937 |
| `definition/tables/FACT_Orders.tmdl` | 866 |
| `definition/tables/FACT_Payroll.tmdl` | 1,038 |
| `definition/tables/Fact_GL.tmdl` | 1,554 |
| `definition/tables/Fact_Inventory.tmdl` | 1,297 |
| `definition/tables/Fact_Sales.tmdl` | 4,311 |
| `definition/tables/General_Ledger.tmdl` | 1,845 |
| `definition/tables/Product.tmdl` | 2,269 |
| `definition/tables/Returns.tmdl` | 678 |
| `definition/tables/Sales.tmdl` | 2,387 |
| `definition/tables/Sales_Analytics.tmdl` | 8,881 |
| `definition/tables/Sales_DB.tmdl` | 1,510 |
| `definition/tables/Sales_Data_Warehouse.tmdl` | 5,681 |
| `definition/tables/Scenario.tmdl` | 1,253 |
| `definition/tables/Time.tmdl` | 1,596 |
| `model.tmdl` | 170 |

### Expression Translations

| # | Source Expression | DAX Output | Confidence |
|---|-----------------|------------|------------|
| 1 | `@PRIOR(Time, 12, @LEVMBRS(Time, 3))` | `@PRIOR(Time, 12, @LEVMBRS(Time, 3))` | 30% |
| 2 | `@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))` | `@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))` | 60% |
| 3 | `Revenue + COGS` | `Revenue + COGS` | 100% |
| 4 | `Gross Profit + OpEx` | `Gross Profit + OpEx` | 100% |
| 5 | `EBITDA + Depreciation` | `EBITDA + Depreciation` | 60% |
| 6 | `@ROUND(Gross Profit % Revenue, 4)` | `@ROUND(Gross Profit % Revenue, 4)` | 100% |
| 7 | `@ROUND(EBITDA % Revenue, 4)` | `@ROUND(EBITDA % Revenue, 4)` | 100% |
| 8 | `@ROUND(Revenue / (Headcount SM + Headcount RD + Headcount GA…` | `@ROUND(Revenue / (Headcount SM + Headcount RD + Headcount GA…` | 100% |
| 9 | `Actual - Budget` | `Actual - Budget` | 100% |
| 10 | `@ROUND((Actual - Budget) % Budget, 4)` | `@ROUND((Actual - Budget) % Budget, 4)` | 100% |
| 11 | `Actual - Forecast` | `Actual - Forecast` | 100% |
| 12 | `@ROUND((Actual - @PRIOR(Actual, 1, @LEVMBRS(Scenario, 0))) %…` | `@ROUND((Actual - @PRIOR(Actual, 1, @LEVMBRS(Scenario, 0))) %…` | 30% |
| 13 | `@CALCMBR(Local, @XREF(ExchangeRates, Rate))` | `@CALCMBR(Local, @XREF(ExchangeRates, Rate))` | 60% |
| 14 | `@CALCMBR(USD, @XREF(ExchangeRates, EUR_Rate))` | `@CALCMBR(USD, @XREF(ExchangeRates, EUR_Rate))` | 60% |
| 15 | `@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))` | `@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))` | 60% |
| 16 | `Revenue - COGS` | `Revenue - COGS` | 100% |
| 17 | `Gross Profit - Operating Expenses` | `Gross Profit - Operating Expenses` | 60% |
| 18 | `@ROUND(Gross Profit % Revenue, 4)` | `@ROUND(Gross Profit % Revenue, 4)` | 100% |
| 19 | `Actual - Budget` | `Actual - Budget` | 100% |
| 20 | `@ROUND((Actual - Budget) % Budget, 4)` | `@ROUND((Actual - Budget) % Budget, 4)` | 100% |
| 21 | `Revenue - COGS` | `Revenue - COGS` | 100% |
| 22 | `"DIM_DATE"."FULL_DATE"` | `"DIM_DATE"."FULL_DATE"` | 60% |
| 23 | `"DIM_DATE"."YEAR"` | `"DIM_DATE"."YEAR"` | 100% |
| 24 | `"DIM_DATE"."QUARTER"` | `"DIM_DATE"."QUARTER"` | 100% |
| 25 | `"DIM_DATE"."MONTH_NAME"` | `"DIM_DATE"."MONTH_NAME"` | 60% |
| 26 | `"DIM_PRODUCT"."PRODUCT_NAME"` | `"DIM_PRODUCT"."PRODUCT_NAME"` | 60% |
| 27 | `"DIM_PRODUCT"."CATEGORY"` | `"DIM_PRODUCT"."CATEGORY"` | 60% |
| 28 | `NTILE(4)` | `INT(RANKX(ALL('Sales_Analytics'), 1, , ASC) * 4 / COUNTROWS(…` | 100% |
| 29 | `CUME_DIST()` | `DIVIDE(RANKX(ALL('Sales_Analytics'), 1, , ASC), COUNTROWS(AL…` | 100% |
| 30 | `PERCENT_RANK()` | `DIVIDE(RANKX(ALL('Sales_Analytics'), 1, , ASC) - 1, COUNTROW…` | 100% |
| 31 | `MEDIAN("FACT_SALES"."REVENUE")` | `MEDIAN('Sales_Analytics'["FACT_SALES"."REVENUE"])` | 100% |
| 32 | `STDDEV("FACT_SALES"."REVENUE")` | `STDEV.S('Sales_Analytics'["FACT_SALES"."REVENUE"])` | 100% |
| 33 | `PERCENTILE("FACT_SALES"."REVENUE", 0.9)` | `PERCENTILEX.INC('Sales_Analytics', 'Sales_Analytics'["FACT_S…` | 100% |
| 34 | `COUNTIF("FACT_SALES"."REVENUE", "FACT_SALES"."REVENUE" > 100…` | `CALCULATE(COUNT('Sales_Analytics'["FACT_SALES"."REVENUE"]), …` | 100% |
| 35 | `SUMIF("FACT_SALES"."REVENUE", "FACT_SALES"."DISCOUNT_AMOUNT"…` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), "F…` | 100% |
| 36 | `SUM("FACT_SALES"."REVENUE")` | `SUM('Sales_Analytics'["FACT_SALES"."REVENUE"])` | 100% |
| 37 | `SUM("FACT_SALES"."COST")` | `SUM('Sales_Analytics'["FACT_SALES"."COST"])` | 100% |
| 38 | `SUM("FACT_SALES"."QUANTITY")` | `SUM('Sales_Analytics'["FACT_SALES"."QUANTITY"])` | 100% |
| 39 | `AGO(SUM("FACT_SALES"."REVENUE"), YEAR, 1)` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DA…` | 85% |
| 40 | `AGO(SUM("FACT_SALES"."REVENUE"), QUARTER, 1)` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DA…` | 85% |
| 41 | `AGO(SUM("FACT_SALES"."REVENUE"), MONTH, 1)` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DA…` | 85% |
| 42 | `TODATE(SUM("FACT_SALES"."REVENUE"), 'YEAR')` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DA…` | 85% |
| 43 | `TODATE(SUM("FACT_SALES"."REVENUE"), 'QUARTER')` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DA…` | 85% |
| 44 | `TODATE(SUM("FACT_SALES"."REVENUE"), 'MONTH')` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DA…` | 85% |
| 45 | `TODATE(SUM("FACT_SALES"."REVENUE"), 'WEEK')` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DA…` | 85% |
| 46 | `PERIODROLLING(SUM("FACT_SALES"."REVENUE"), 30)` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DA…` | 85% |
| 47 | `PERIODROLLING(SUM("FACT_SALES"."REVENUE"), 90)` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DA…` | 85% |
| 48 | `RSUM(SUM("FACT_SALES"."REVENUE"))` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"], FIL…` | 85% |
| 49 | `RCOUNT(SUM("FACT_SALES"."QUANTITY"))` | `CALCULATE(COUNTROWS({tbl}), FILTER(ALL('Date'), 'Date'[Date]…` | 85% |
| 50 | `RMAX(SUM("FACT_SALES"."REVENUE"))` | `CALCULATE(MAX(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"])…` | 85% |
| 51 | `RMIN(SUM("FACT_SALES"."REVENUE"))` | `CALCULATE(MIN(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"])…` | 85% |
| 52 | `MAVG(SUM("FACT_SALES"."REVENUE"), 7)` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DA…` | 85% |
| 53 | `MSUM(SUM("FACT_SALES"."REVENUE"), 30)` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DA…` | 85% |
| 54 | `PARALLELPERIOD(SUM("FACT_SALES"."REVENUE"), -1, YEAR)` | `CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), PA…` | 85% |
| 55 | `OPENINGBALANCEYEAR(SUM("FACT_SALES"."REVENUE"))` | `OPENINGBALANCEYEAR(SUM('Sales_Analytics'["FACT_SALES"."REVEN…` | 85% |
| 56 | `CLOSINGBALANCEYEAR(SUM("FACT_SALES"."REVENUE"))` | `CLOSINGBALANCEYEAR(SUM('Sales_Analytics'["FACT_SALES"."REVEN…` | 85% |
| 57 | `RANK(SUM("FACT_SALES"."REVENUE"))` | `RANKX(ALL('Sales_Analytics'), SUM('Sales_Analytics'["FACT_SA…` | 100% |
| 58 | `DENSE_RANK(SUM("FACT_SALES"."REVENUE"))` | `RANKX(ALL('Sales_Analytics'), SUM('Sales_Analytics'["FACT_SA…` | 100% |
| 59 | `RATIO_TO_REPORT(SUM("FACT_SALES"."REVENUE"))` | `DIVIDE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"], CALCUL…` | 100% |
| 60 | `COUNTDISTINCT("FACT_SALES"."PRODUCT_KEY")` | `DISTINCTCOUNT('Sales_Analytics'["FACT_SALES"."PRODUCT_KEY"])` | 100% |
| 61 | `SUM("FACT_SALES"."REVENUE") - SUM("FACT_FORECAST"."FORECAST_…` | `SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]) - SUM('Sales_…` | 100% |
| 62 | `"DIM_DATE"."FULL_DATE"` | `"DIM_DATE"."FULL_DATE"` | 60% |
| 63 | `"DIM_DATE"."YEAR"` | `"DIM_DATE"."YEAR"` | 100% |
| 64 | `"DIM_DATE"."QUARTER"` | `"DIM_DATE"."QUARTER"` | 100% |
| 65 | `"DIM_DATE"."MONTH_NAME"` | `"DIM_DATE"."MONTH_NAME"` | 60% |
| 66 | `"DIM_PRODUCT"."PRODUCT_NAME"` | `"DIM_PRODUCT"."PRODUCT_NAME"` | 60% |
| 67 | `"DIM_PRODUCT"."CATEGORY"` | `"DIM_PRODUCT"."CATEGORY"` | 60% |
| 68 | `"DIM_PRODUCT"."SUBCATEGORY"` | `"DIM_PRODUCT"."SUBCATEGORY"` | 60% |
| 69 | `"DIM_PRODUCT"."BRAND"` | `"DIM_PRODUCT"."BRAND"` | 60% |
| 70 | `("DIM_PRODUCT"."UNIT_PRICE" - "DIM_PRODUCT"."UNIT_COST") / "…` | `("DIM_PRODUCT"."UNIT_PRICE" - "DIM_PRODUCT"."UNIT_COST") / "…` | 60% |
| 71 | `"DIM_CUSTOMER"."CUSTOMER_NAME"` | `"DIM_CUSTOMER"."CUSTOMER_NAME"` | 60% |
| 72 | `"DIM_CUSTOMER"."SEGMENT"` | `"DIM_CUSTOMER"."SEGMENT"` | 60% |
| 73 | `"DIM_CUSTOMER"."REGION"` | `"DIM_CUSTOMER"."REGION"` | 60% |
| 74 | `"DIM_CUSTOMER"."COUNTRY"` | `"DIM_CUSTOMER"."COUNTRY"` | 60% |
| 75 | `"DIM_CUSTOMER"."CITY"` | `"DIM_CUSTOMER"."CITY"` | 60% |
| 76 | `"FACT_SALES"."QUANTITY"` | `"FACT_SALES"."QUANTITY"` | 60% |
| 77 | `SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1…` | `SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRI…` | 100% |
| 78 | `SUM("FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST")` | `SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_CO…` | 100% |
| 79 | `SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1…` | `SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRI…` | 100% |
| 80 | `CASE WHEN SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_P…` | `SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY" * "FA…` | 80% |
| 81 | `CASE WHEN SUM("FACT_SALES"."QUANTITY") = 0 THEN 0 ELSE SUM("…` | `SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY"]) = 0…` | 80% |
| 82 | `SUM("FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE") - S…` | `SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRI…` | 100% |
| 83 | `"FACT_RETURNS"."RETURN_QUANTITY"` | `"FACT_RETURNS"."RETURN_QUANTITY"` | 60% |
| 84 | `"FACT_RETURNS"."REASON_CODE"` | `"FACT_RETURNS"."REASON_CODE"` | 60% |
| 85 | `"FACT_BUDGET"."BUDGET_AMOUNT"` | `"FACT_BUDGET"."BUDGET_AMOUNT"` | 60% |
| 86 | `"DIM_DATE"."FULL_DATE"` | `"DIM_DATE"."FULL_DATE"` | 60% |
| 87 | `"DIM_DATE"."YEAR"` | `"DIM_DATE"."YEAR"` | 100% |
| 88 | `"DIM_EMPLOYEE"."EMP_KEY"` | `"DIM_EMPLOYEE"."EMP_KEY"` | 60% |
| 89 | `CONCAT("DIM_EMPLOYEE"."FIRST_NAME", ' ' || "DIM_EMPLOYEE"."L…` | `"DIM_EMPLOYEE"."FIRST_NAME" & ' ' & "DIM_EMPLOYEE"."LAST_NAM…` | 100% |
| 90 | `"DIM_EMPLOYEE"."FIRST_NAME" || ' ' || "DIM_EMPLOYEE"."LAST_N…` | `"DIM_EMPLOYEE"."FIRST_NAME" & ' ' & "DIM_EMPLOYEE"."LAST_NAM…` | 100% |
| 91 | `INITCAP("DIM_EMPLOYEE"."LAST_NAME")` | `UPPER(LEFT("DIM_EMPLOYEE"."LAST_NAME", 1)) & LOWER(MID("DIM_…` | 100% |
| 92 | `SUBSTRING("DIM_EMPLOYEE"."EMAIL", INSTR("DIM_EMPLOYEE"."EMAI…` | `MID("DIM_EMPLOYEE"."EMAIL", FIND('@', "DIM_EMPLOYEE"."EMAIL"…` | 100% |
| 93 | `LEFT("DIM_EMPLOYEE"."EMAIL", INSTR("DIM_EMPLOYEE"."EMAIL", '…` | `LEFT("DIM_EMPLOYEE"."EMAIL", FIND('@', "DIM_EMPLOYEE"."EMAIL…` | 100% |
| 94 | `LENGTH("DIM_EMPLOYEE"."LAST_NAME")` | `LEN("DIM_EMPLOYEE"."LAST_NAME")` | 100% |
| 95 | `UPPER("DIM_EMPLOYEE"."LAST_NAME")` | `UPPER("DIM_EMPLOYEE"."LAST_NAME")` | 100% |
| 96 | `LOWER("DIM_EMPLOYEE"."FIRST_NAME")` | `LOWER("DIM_EMPLOYEE"."FIRST_NAME")` | 100% |
| 97 | `TRIM("DIM_EMPLOYEE"."NOTES")` | `TRIM("DIM_EMPLOYEE"."NOTES")` | 100% |
| 98 | `LTRIM("DIM_EMPLOYEE"."NOTES")` | `TRIM("DIM_EMPLOYEE"."NOTES")` | 100% |
| 99 | `RTRIM("DIM_EMPLOYEE"."NOTES")` | `TRIM("DIM_EMPLOYEE"."NOTES")` | 100% |
| 100 | `REPLACE("DIM_EMPLOYEE"."PHONE", '-', '')` | `SUBSTITUTE("DIM_EMPLOYEE"."PHONE", '-', '')` | 100% |
| 101 | `LPAD("DIM_EMPLOYEE"."JOB_CODE", 8, '0')` | `REPT('0', 8 - LEN("DIM_EMPLOYEE"."JOB_CODE")) & "DIM_EMPLOYE…` | 100% |
| 102 | `RPAD("DIM_EMPLOYEE"."JOB_CODE", 10, ' ')` | `"DIM_EMPLOYEE"."JOB_CODE" & REPT(' ', 10 - LEN("DIM_EMPLOYEE…` | 100% |
| 103 | `ASCII("DIM_EMPLOYEE"."FIRST_NAME")` | `UNICODE("DIM_EMPLOYEE"."FIRST_NAME")` | 100% |
| 104 | `CHR(65)` | `UNICHAR(65)` | 100% |
| 105 | `TRANSLATE("DIM_EMPLOYEE"."STATUS", 'A', 'Active')` | `SUBSTITUTE("DIM_EMPLOYEE"."STATUS", 'A', 'Active')` | 100% |
| 106 | `IFNULL("DIM_EMPLOYEE"."DEPARTMENT", 'Unassigned')` | `IF(ISBLANK("DIM_EMPLOYEE"."DEPARTMENT"), 'Unassigned', "DIM_…` | 100% |
| 107 | `NVL("DIM_EMPLOYEE"."DEPARTMENT", 'General')` | `IF(ISBLANK("DIM_EMPLOYEE"."DEPARTMENT"), 'General', "DIM_EMP…` | 100% |
| 108 | `NVL2("DIM_EMPLOYEE"."DEPARTMENT", "DIM_EMPLOYEE"."DEPARTMENT…` | `IF(ISBLANK("DIM_EMPLOYEE"."DEPARTMENT"), 'N/A', "DIM_EMPLOYE…` | 100% |
| 109 | `COALESCE("DIM_EMPLOYEE"."DEPARTMENT", "DIM_EMPLOYEE"."JOB_CO…` | `COALESCE("DIM_EMPLOYEE"."DEPARTMENT", "DIM_EMPLOYEE"."JOB_CO…` | 100% |
| 110 | `NULLIF("DIM_EMPLOYEE"."STATUS", '')` | `IF("DIM_EMPLOYEE"."STATUS" = '', BLANK(), "DIM_EMPLOYEE"."ST…` | 100% |
| 111 | `GREATEST("DIM_EMPLOYEE"."SALARY", 50000)` | `IF("DIM_EMPLOYEE"."SALARY" >= 50000, "DIM_EMPLOYEE"."SALARY"…` | 100% |
| 112 | `LEAST("DIM_EMPLOYEE"."SALARY", 200000)` | `IF("DIM_EMPLOYEE"."SALARY" <= 200000, "DIM_EMPLOYEE"."SALARY…` | 100% |
| 113 | `DECODE("DIM_EMPLOYEE"."STATUS", 'A', 'Active', 'I', 'Inactiv…` | `SWITCH("DIM_EMPLOYEE"."STATUS",
    'A', 'Active',
    'I', …` | 80% |
| 114 | `CASE WHEN "DIM_EMPLOYEE"."SALARY" > 100000 THEN 'Senior' WHE…` | `SWITCH(TRUE(),
    "DIM_EMPLOYEE"."SALARY" > 100000, 'Senior…` | 80% |
| 115 | `CAST("DIM_EMPLOYEE"."SALARY" AS INT)` | `INT("DIM_EMPLOYEE"."SALARY")` | 100% |
| 116 | `CAST("DIM_EMPLOYEE"."EMP_KEY" AS VARCHAR)` | `FORMAT("DIM_EMPLOYEE"."EMP_KEY", "General")` | 100% |
| 117 | `TO_NUMBER("DIM_EMPLOYEE"."JOB_CODE")` | `VALUE("DIM_EMPLOYEE"."JOB_CODE")` | 100% |
| 118 | `EXTRACT(YEAR FROM "DIM_EMPLOYEE"."HIRE_DATE")` | `YEAR("DIM_EMPLOYEE"."HIRE_DATE")` | 100% |
| 119 | `EXTRACT(MONTH FROM "DIM_EMPLOYEE"."HIRE_DATE")` | `MONTH("DIM_EMPLOYEE"."HIRE_DATE")` | 100% |
| 120 | `EXTRACT(QUARTER FROM "DIM_EMPLOYEE"."HIRE_DATE")` | `QUARTER("DIM_EMPLOYEE"."HIRE_DATE")` | 100% |
| 121 | `MONTHS_BETWEEN(CURRENT_DATE, "DIM_EMPLOYEE"."HIRE_DATE")` | `DATEDIFF("DIM_EMPLOYEE"."HIRE_DATE", TODAY(), MONTH)` | 100% |
| 122 | `ADD_MONTHS("DIM_EMPLOYEE"."HIRE_DATE", 12)` | `EDATE("DIM_EMPLOYEE"."HIRE_DATE", 12)` | 100% |
| 123 | `LAST_DAY("DIM_EMPLOYEE"."HIRE_DATE")` | `EOMONTH("DIM_EMPLOYEE"."HIRE_DATE", 0)` | 100% |
| 124 | `CURRENT_DATE` | `TODAY()` | 100% |
| 125 | `CURRENT_TIMESTAMP` | `NOW()` | 100% |
| 126 | `SYSDATE` | `NOW()` | 100% |
| 127 | `TO_CHAR("DIM_EMPLOYEE"."HIRE_DATE", 'YYYY-MM-DD')` | `FORMAT("DIM_EMPLOYEE"."HIRE_DATE", 'YYYY-MM-DD')` | 100% |
| 128 | `ABS("DIM_EMPLOYEE"."SALARY" - 75000)` | `ABS("DIM_EMPLOYEE"."SALARY" - 75000)` | 100% |
| 129 | `ROUND("DIM_EMPLOYEE"."SALARY", -3)` | `ROUND("DIM_EMPLOYEE"."SALARY", -3)` | 100% |
| 130 | `CEIL("DIM_EMPLOYEE"."SALARY" / 1000)` | `CEILING("DIM_EMPLOYEE"."SALARY" / 1000, 1)` | 100% |
| 131 | `FLOOR("DIM_EMPLOYEE"."SALARY" / 1000)` | `FLOOR("DIM_EMPLOYEE"."SALARY" / 1000, 1)` | 100% |
| 132 | `POWER("DIM_EMPLOYEE"."SALARY", 2)` | `POWER("DIM_EMPLOYEE"."SALARY", 2)` | 100% |
| 133 | `SQRT("DIM_EMPLOYEE"."SALARY")` | `SQRT("DIM_EMPLOYEE"."SALARY")` | 100% |
| 134 | `LOG("DIM_EMPLOYEE"."SALARY")` | `LN("DIM_EMPLOYEE"."SALARY")` | 100% |
| 135 | `EXP(1)` | `EXP(1)` | 100% |
| 136 | `MOD("DIM_EMPLOYEE"."EMP_KEY", 10)` | `MOD("DIM_EMPLOYEE"."EMP_KEY", 10)` | 100% |
| 137 | `SIGN("DIM_EMPLOYEE"."SALARY" - 75000)` | `SIGN("DIM_EMPLOYEE"."SALARY" - 75000)` | 100% |
| 138 | `VALUEOF(NQ_SESSION.USER)` | `USERPRINCIPALNAME()` | 100% |
| 139 | `RAND()` | `RAND()` | 100% |
| 140 | `SUM("FACT_GL"."DEBIT_AMOUNT") - SUM("FACT_GL"."CREDIT_AMOUNT…` | `SUM('General_Ledger'["FACT_GL"."DEBIT_AMOUNT"]) - SUM('Gener…` | 100% |
| 141 | `SUM("FACT_GL"."DEBIT_AMOUNT" * "FACT_GL"."EXCHANGE_RATE")` | `SUM('General_Ledger'["FACT_GL"."DEBIT_AMOUNT" * "FACT_GL"."E…` | 100% |
| 142 | `SUM("FACT_GL"."DEBIT_AMOUNT") - SUM("FACT_BUDGET"."BUDGET_AM…` | `SUM('General_Ledger'["FACT_GL"."DEBIT_AMOUNT"]) - SUM('Gener…` | 100% |
| 143 | `CASE WHEN SUM("FACT_BUDGET"."BUDGET_AMOUNT") = 0 THEN 0 ELSE…` | `SWITCH(TRUE(),
    SUM('General_Ledger'["FACT_BUDGET"."BUDGE…` | 80% |
| 144 | `TOPN(10, SUM("FACT_GL"."DEBIT_AMOUNT"))` | `TOPN(10, 'General_Ledger', SUM('General_Ledger'["FACT_GL"."D…` | 100% |
| 145 | `"EMPLOYEES"."EMP_ID"` | `"EMPLOYEES"."EMP_ID"` | 100% |
| 146 | `"EMPLOYEES"."FIRST_NAME" || ' ' || "EMPLOYEES"."LAST_NAME"` | `"EMPLOYEES"."FIRST_NAME" & ' ' & "EMPLOYEES"."LAST_NAME"` | 100% |
| 147 | `"EMPLOYEES"."HIRE_DATE"` | `"EMPLOYEES"."HIRE_DATE"` | 60% |
| 148 | `"DEPARTMENTS"."DEPT_NAME"` | `"DEPARTMENTS"."DEPT_NAME"` | 60% |
| 149 | `"LOCATIONS"."LOCATION_ID"` | `"LOCATIONS"."LOCATION_ID"` | 60% |
| 150 | `"LOCATIONS"."CITY"` | `"LOCATIONS"."CITY"` | 100% |
| 151 | `"LOCATIONS"."COUNTRY"` | `"LOCATIONS"."COUNTRY"` | 60% |
| 152 | `"PAYROLL"."PAY_ID"` | `"PAYROLL"."PAY_ID"` | 100% |
| 153 | `"PAYROLL"."GROSS_PAY"` | `"PAYROLL"."GROSS_PAY"` | 60% |
| 154 | `"PAYROLL"."GROSS_PAY" - "PAYROLL"."DEDUCTIONS"` | `"PAYROLL"."GROSS_PAY" - "PAYROLL"."DEDUCTIONS"` | 60% |
| 155 | `AVG("EMPLOYEES"."SALARY")` | `AVERAGE('FACT_Payroll'["EMPLOYEES"."SALARY"])` | 100% |
| 156 | `"CUSTOMERS"."CUST_ID"` | `"CUSTOMERS"."CUST_ID"` | 60% |
| 157 | `"CUSTOMERS"."CUST_NAME"` | `"CUSTOMERS"."CUST_NAME"` | 60% |
| 158 | `"CUSTOMERS"."REGION"` | `"CUSTOMERS"."REGION"` | 100% |
| 159 | `"ORDERS"."ORDER_ID"` | `"ORDERS"."ORDER_ID"` | 100% |
| 160 | `"ORDERS"."AMOUNT"` | `"ORDERS"."AMOUNT"` | 100% |
| 161 | `SUM("ORDERS"."AMOUNT") * 0.2` | `SUM('FACT_Orders'["ORDERS"."AMOUNT"]) * 0.2` | 100% |
| 162 | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | 60% |
| 163 | `[Quantity] * [UnitCost] + [TaxAmount] + [FreightCost]` | `[Quantity] * [UnitCost] + [TaxAmount] + [FreightCost]` | 60% |
| 164 | `[Revenue] - [TotalCost]` | `[Revenue] - [TotalCost]` | 60% |
| 165 | `IF [Revenue] > 0 THEN [Profit] / [Revenue] * 100 ELSE 0 END` | `IF [Revenue] > 0 THEN [Profit] / [Revenue] * 100 ELSE 0 END` | 60% |
| 166 | `[Quantity] * [UnitPrice] * [DiscountPct]` | `[Quantity] * [UnitPrice] * [DiscountPct]` | 60% |
| 167 | `IF [UnitPrice] > 500 THEN 'Premium' ELSEIF [UnitPrice] > 100…` | `IF [UnitPrice] > 500 THEN 'Premium' ELSEIF [UnitPrice] > 100…` | 60% |
| 168 | `IF [Revenue] > 5000 THEN 'Yes' ELSE 'No' END` | `IF [Revenue] > 5000 THEN 'Yes' ELSE 'No' END` | 60% |
| 169 | `SUM([Revenue]) / COUNTD([OrderID])` | `SUM('Sales Data Warehouse'[[Revenue]]) / COUNTD([OrderID])` | 100% |
| 170 | `[ForecastAmount] - [BudgetAmount]` | `[ForecastAmount] - [BudgetAmount]` | 60% |
| 171 | `IF [BudgetAmount] > 0 THEN ([ForecastAmount] - [BudgetAmount…` | `IF [BudgetAmount] > 0 THEN ([ForecastAmount] - [BudgetAmount…` | 60% |
| 172 | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | `[Quantity] * [UnitPrice] * (1 - [DiscountPct])` | 60% |
| 173 | `[Revenue] - ([Quantity] * [UnitCost])` | `[Revenue] - ([Quantity] * [UnitCost])` | 60% |
| 174 | `IF [Revenue] > 0 THEN [Profit] / [Revenue] ELSE 0 END` | `IF [Revenue] > 0 THEN [Profit] / [Revenue] ELSE 0 END` | 60% |
| 175 | `[Amount] * [Quantity]` | `[Amount] * [Quantity]` | 60% |

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
| hierarchy | Dim Product | Product Hierarchy | Missing column references |
| hierarchy | Dim Date | Calendar Hierarchy | Missing column references |
| hierarchy | Dim Employee | Org Hierarchy | Missing column references |
| hierarchy | DIM_Employee | OrgHierarchy | Missing column references |
| expression | Time | Prior Year | Untranslatable pattern: PRIOR (hierarchical); No translation rules matched — expression may need manual review |
| expression | Time | YTD | No translation rules matched — expression may need manual review |
| expression | Accounts | EBIT | No translation rules matched — expression may need manual review |
| expression | Scenario | YoY Growth | Untranslatable pattern: PRIOR (hierarchical) |
| expression | Currency | USD | No translation rules matched — expression may need manual review |
| expression | Currency | EUR | No translation rules matched — expression may need manual review |
| expression | Time | YTD | No translation rules matched — expression may need manual review |
| expression | Accounts | Operating Income | No translation rules matched — expression may need manual review |
| expression | Time | Date | No translation rules matched — expression may need manual review |
| expression | Time | Month | No translation rules matched — expression may need manual review |
| expression | Product | Product Name | No translation rules matched — expression may need manual review |
| expression | Product | Category | No translation rules matched — expression may need manual review |
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
| expression | Time | Date | No translation rules matched — expression may need manual review |
| expression | Employee | Employee Key | No translation rules matched — expression may need manual review |
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
    "logicalId": "106329bd-9a9a-4c86-a9a5-4a121c24aecf"
  }
}
```

#### `definition/database.tmdl`

```
compatibilityLevel: 1604

model SemanticModel
    defaultMode: import
    discourageImplicitMeasures
```

#### `definition/expressions.tmdl`

```
expression 'Lakehouse' =
    let
        Source = Sql.Database("{lakehouse_sql_endpoint}", "MigrationLakehouse"),
    in
        Source
    lineageTag: adc9da52-3556-4ee6-bd8e-a72c956672df
    queryGroup: 'Data Sources'
```

#### `definition/perspectives.tmdl`

```
perspective 'Sales Analytics'
    perspectiveTable 'Time Dimension'
        perspectiveColumn Date
        perspectiveColumn Year
        perspectiveColumn Quarter
        perspectiveColumn Month
    perspectiveTable 'Product'
        perspectiveColumn Product Name
        perspectiveColumn Category
    perspectiveTable 'Revenue Metrics'
        perspectiveColumn Total Revenue
        perspectiveColumn Revenue Prior Year
        perspectiveColumn Revenue YTD
        perspectiveColumn Revenue QTD
        perspectiveColumn Rolling 30 Day Revenue
        perspectiveColumn Running Total Revenue
        perspectiveColumn 7 Day Moving Avg
        perspectiveColumn Revenue Rank
        perspectiveColumn Revenue Share
        perspectiveColumn Same Period Last Year
        perspectiveColumn Forecast Variance

perspective 'Statistical Analysis'
    perspectiveTable 'Advanced Metrics'
        perspectiveColumn Distinct Products Sold
        perspectiveColumn Median Revenue
        perspectiveColumn Revenue StdDev
        perspectiveColumn Revenue 90th Pct
        perspectiveColumn Cumulative Distribution
        perspectiveColumn Percentile Rank
        perspectiveColumn Revenue Dense Rank
        perspectiveColumn Revenue Quartile

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

perspective 'Employee Analytics'
    perspectiveTable 'Employee Info'
        perspectiveColumn Full Name
        perspectiveColumn Display Name
        perspectiveColumn Email Domain
        perspectiveColumn Safe Department
        perspectiveColumn Status Label (DECODE)
        perspectiveColumn Salary Band
        perspectiveColumn Hire Year
        perspectiveColumn Months Employed
        perspectiveColumn Rounded Salary
        perspectiveColumn Padded Job Code

perspective 'Financial Reporting'
    perspectiveTable 'GL Metrics'
        perspectiveColumn Net Amount
        perspectiveColumn Converted Amount
        perspectiveColumn Budget Variance
        perspectiveColumn Budget Variance Pct
        perspectiveColumn Top N Accounts

perspective 'SampleApp'
    perspectiveTable 'Revenue'
        perspectiveColumn Revenue
        perspectiveColumn Cost
        perspectiveColumn Profit
        perspectiveColumn Margin %
        perspectiveColumn Quantity
        perspectiveColumn Avg Deal Size
        perspectiveColumn Revenue LY
        perspectiveColumn Revenue YTD
        perspectiveColumn Revenue Growth %
        perspectiveColumn Revenue Rank
        perspectiveColumn Revenue Category
    perspectiveTable 'Customers'
        perspectiveColumn Customer Name
        perspectiveColumn Customer Class
        perspectiveColumn Industry
        perspectiveColumn Region
        perspectiveColumn Status
        perspectiveColumn Display Name
    perspectiveTable 'Products'
        perspectiveColumn Product Name
        perspectiveColumn Category
        perspectiveColumn Sub-Category
        perspectiveColumn Brand
        perspectiveColumn Price Tier
    perspectiveTable 'Time'
        perspectiveColumn Year
        perspectiveColumn Quarter
        perspectiveColumn Month
    perspectiveTable 'Geography'
        perspectiveColumn Country
        perspectiveColumn Region
        perspectiveColumn State
        perspectiveColumn City
    perspectiveTable 'Channel'
        perspectiveColumn Channel Name
        perspectiveColumn Channel Type

perspective 'Operations Analytics'
    perspectiveTable 'Inventory'
        perspectiveColumn Quantity On Hand
        perspectiveColumn Quantity On Order
        perspectiveColumn Inventory Value
        perspectiveColumn Days of Supply
        perspectiveColumn Below Reorder
    perspectiveTable 'Warehouse'
        perspectiveColumn Warehouse Name
        perspectiveColumn Warehouse Region
        perspectiveColumn Capacity
    perspectiveTable 'Products'
        perspectiveColumn Product Name
        perspectiveColumn Category

perspective 'Financial Analytics'
    perspectiveTable 'General Ledger'
        perspectiveColumn Actual Amount
        perspectiveColumn Budget Amount
        perspectiveColumn Variance
        perspectiveColumn Variance %
        perspectiveColumn Amount YTD
    perspectiveTable 'Time'
        perspectiveColumn Fiscal Year
        perspectiveColumn Fiscal Period
    perspectiveTable 'HR'
        perspectiveColumn Employee Name
        perspectiveColumn Department
        perspectiveColumn Job Title
        perspectiveColumn Annual Salary
        perspectiveColumn Years of Service

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
    lineageTag: 3582a586-b2ac-45b5-be77-c3a8a9723504

    partition Accounts = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Accounts = Source{[Schema="dbo", Item="Accounts"]}[Data]
            in
                Accounts

    column 'Gross Profit' = Revenue - COGS
        dataType: string
        lineageTag: 15893f47-b8a1-4a52-a23d-e2d04619cf5e

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

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Budget.tmdl`

```
table Budget
    lineageTag: 5dc3ae20-4be9-473f-bf70-f037abafc082

    partition Budget = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Budget = Source{[Schema="dbo", Item="Budget"]}[Data]
            in
                Budget

    column 'Budget Amount' = "FACT_BUDGET"."BUDGET_AMOUNT"
        dataType: string
        lineageTag: 2b472adc-ffd5-4dcb-91a2-c6daca56fe2e

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Budget_&_Forecast.tmdl`

```
table Budget & Forecast
    lineageTag: 706138aa-0f97-4e9a-8029-f31f890481e4

    partition Budget & Forecast = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Budget_&_Forecast = Source{[Schema="dbo", Item="Budget_&_Forecast"]}[Data]
            in
                Budget_&_Forecast

    column BudgetMonth
        dataType: dateTime
        lineageTag: b4177ce1-d368-49a4-9445-caf72acf3aae
        sourceColumn: BudgetMonth
        summarizeBy: none

    column BudgetRegion
        dataType: string
        lineageTag: bdcf47b9-ad8f-4490-b4e9-78d9db8aa5ff
        sourceColumn: BudgetRegion
        summarizeBy: none

    column BudgetCategory
        dataType: string
        lineageTag: bec879fa-2584-4a08-9ba0-4a008f9c1751
        sourceColumn: BudgetCategory
        summarizeBy: none

    column BudgetAmount
        dataType: string
        lineageTag: 76301630-6ff2-4c60-a66c-717ac88355a0
        sourceColumn: BudgetAmount
        summarizeBy: none

    column ForecastAmount
        dataType: string
        lineageTag: ffe5ed97-5194-4b89-898c-4f3928a4750f
        sourceColumn: ForecastAmount
        summarizeBy: none

    column 'BudgetVariance' = [ForecastAmount] - [BudgetAmount]
        dataType: string
        lineageTag: b3c3a2a1-77bf-47d1-9748-21cca4cdde7c

    column 'VariancePct' = IF [BudgetAmount] > 0 THEN ([ForecastAmount] - [BudgetAmount]) / [BudgetAmount] * 100 ELSE 0 END
        dataType: string
        lineageTag: 106af95c-e010-41da-9227-e00d6cb13cb9

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Calendar.tmdl`

```
table 'Calendar'
    lineageTag: 0e7b1e78-7caf-4bb1-96ea-6cd7164b74df
    description: Auto-generated Calendar table for time intelligence
    isHidden

    partition 'Calendar' = m
        mode: import
        source
            let
                StartDate = 'Date'[StartOfYear]('List'[Min]('Dim Customer'[Created Date])),
                EndDate = 'Date'[EndOfYear]('List'[Max]('Dim Customer'[Created Date])),
                DateList = 'List'[Dates](StartDate, 'Duration'[Days](EndDate - StartDate) + 1, #duration(1,0,0,0)),
                #"Convert to Table" = 'Table'[FromList](DateList, 'Splitter'[SplitByNothing](), {{"Date"}}),
                #"Changed Type" = 'Table'[TransformColumnTypes](#"Convert to Table", {{"Date", type date}}),
                #"Added Year" = 'Table'[AddColumn](#"Changed Type", "Year", each 'Date'[Year]([Date]), 'Int64'[Type]),
                #"Added Quarter" = 'Table'[AddColumn](#"Added Year", "Quarter", each 'Date'[QuarterOfYear]([Date]), 'Int64'[Type]),
                #"Added Month" = 'Table'[AddColumn](#"Added Quarter", "Month", each 'Date'[Month]([Date]), 'Int64'[Type]),
                #"Added MonthName" = 'Table'[AddColumn](#"Added Month", "MonthName", each 'Date'[MonthName]([Date]), type text),
                #"Added Day" = 'Table'[AddColumn](#"Added MonthName", "Day", each 'Date'[Day]([Date]), 'Int64'[Type]),
                #"Added DayOfWeek" = 'Table'[AddColumn](#"Added Day", "DayOfWeek", each 'Date'[DayOfWeek]([Date], 'Day'[Monday]) + 1, 'Int64'[Type]),
                #"Added DayName" = 'Table'[AddColumn](#"Added DayOfWeek", "DayName", each 'Date'[DayOfWeekName]([Date]), type text)
            in
                #"Added DayName"

    column Date
        dataType: dateTime
        lineageTag: 0f9af521-c0ad-47f2-8430-9f1653fd257c
        formatString: yyyy-MM-dd
        sourceColumn: Date
        summarizeBy: none

    column Year
        dataType: int64
        lineageTag: a05b16e7-6b17-4292-87cf-5a05ab35ada6
        formatString: 0
        sourceColumn: Year
        summarizeBy: none

    column Quarter
        dataType: int64
        lineageTag: 4e9b3815-2497-4b04-862a-aaefe8c2a569
        formatString: 0
        sourceColumn: Quarter
        summarizeBy: none

    column Month
        dataType: int64
        lineageTag: 273d5671-0f7b-4534-b5b3-b18e4354e8eb
        formatString: 0
        sourceColumn: Month
        summarizeBy: none

    column MonthName
        dataType: string
        lineageTag: 7acc6ba7-111a-4481-b1c6-f8a023fafb74
        sourceColumn: MonthName
        sortByColumn: Month
        summarizeBy: none

    column Day
        dataType: int64
        lineageTag: fbe668fe-8641-4406-b227-634d62819cc6
        formatString: 0
        sourceColumn: Day
        summarizeBy: none

    column DayOfWeek
        dataType: int64
        lineageTag: b3e302fa-4643-455c-8f3b-d354b7e3b7e0
        formatString: 0
        sourceColumn: DayOfWeek
        summarizeBy: none

    column DayName
        dataType: string
        lineageTag: 3fe22d53-01f9-46d1-a6e0-2690888b2279
        sourceColumn: DayName
        sortByColumn: DayOfWeek
        summarizeBy: none

    hierarchy 'Date Hierarchy'
        lineageTag: 48b26ed5-e180-4e37-8512-bacacca96cc3
        level Year
            lineageTag: 0a0391a1-30fe-41b1-b0c8-1a7ee9cc6e1c
            column: Year
        level Quarter
            lineageTag: 56f2578c-2eea-4004-ac13-824c08c4d941
            column: Quarter
        level Month
            lineageTag: d2ae611f-ebfc-4b5c-9dc8-6990094ff379
            column: Month
        level Day
            lineageTag: 34b4b355-b35b-429d-a9c2-02300e95d00d
            column: Day

    measure 'YTD Sales' = TOTALYTD(SUM('Calendar'[Date]), 'Calendar'[Date])
        lineageTag: 800eadca-1c53-4bb2-8333-d6ddb9fd6601
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence
        description: YTD aggregate — replace SUM('Calendar'[Date]) with your actual measure

    measure 'PY Sales' = CALCULATE([YTD Sales], SAMEPERIODLASTYEAR('Calendar'[Date]))
        lineageTag: 49aca0c7-0645-4cc4-a0d4-f0e2c6a27dbc
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence
        description: Prior Year — references YTD Sales measure

    measure 'YoY %' = DIVIDE([YTD Sales] - [PY Sales], [PY Sales], BLANK())
        lineageTag: 4d66c711-6f50-4bed-90cc-2c4f2e17abae
        formatString: 0.00%
        displayFolder: Time Intelligence
        description: Year-over-Year percentage change

    /// @migration: unreferenced-hidden — consider removing
```

#### `definition/tables/Channel.tmdl`

```
table Channel
    lineageTag: da47ac73-79ad-4e9a-95d5-4c8d6c923c64

    partition Channel = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
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

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Currency.tmdl`

```
table Currency
    lineageTag: f44236c1-e683-410f-8981-5257d4967024

    partition Currency = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Currency = Source{[Schema="dbo", Item="Currency"]}[Data]
            in
                Currency

    column 'USD' = @CALCMBR(Local, @XREF(ExchangeRates, Rate))
        dataType: string
        lineageTag: e23f9dd6-4b92-42f8-9df8-1a7fbc0f7f74

    column 'EUR' = @CALCMBR(USD, @XREF(ExchangeRates, EUR_Rate))
        dataType: string
        lineageTag: a9941175-905f-494a-a09d-105f18cff3af

    hierarchy CurrencyHierarchy
        level Local
            column: Local
        level USD
            column: USD
        level EUR
            column: EUR

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Customer.tmdl`

```
table Customer
    lineageTag: db3f6729-6084-46f4-8415-f4298cc710a0

    partition Customer = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Customer = Source{[Schema="dbo", Item="Customer"]}[Data]
            in
                Customer

    column 'Customer Name' = "DIM_CUSTOMER"."CUSTOMER_NAME"
        dataType: string
        lineageTag: e852735b-47e4-4c85-84c4-1302cba5d01e

    column 'Segment' = "DIM_CUSTOMER"."SEGMENT"
        dataType: string
        lineageTag: ba718361-d02d-4d3c-9cc5-3b486f0d3dfc

    column 'Region' = "DIM_CUSTOMER"."REGION"
        dataType: string
        lineageTag: 7e120ac3-a330-40e0-934d-fdee9316ce0e

    column 'Country' = "DIM_CUSTOMER"."COUNTRY"
        dataType: string
        lineageTag: 24be159e-fa85-4238-92d5-9a2bd8cf3016

    column 'City' = "DIM_CUSTOMER"."CITY"
        dataType: string
        lineageTag: 66dfe4fb-3772-4c95-8a54-57d987b51c86

    hierarchy GeoHierarchy
        level Region
            column: Region
        level Country
            column: Country
        level State
            column: State
        level City
            column: City

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/DIM_Customer.tmdl`

```
table DIM_Customer
    lineageTag: 33702d5f-2824-4f14-a989-5b979bcd6be0

    partition DIM_Customer = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                DIM_Customer = Source{[Schema="dbo", Item="DIM_Customer"]}[Data]
            in
                DIM_Customer

    column 'Customer ID' = "CUSTOMERS"."CUST_ID"
        dataType: string
        lineageTag: 916200b0-fcf1-4528-9d48-85b0830683d9

    column 'Customer Name' = "CUSTOMERS"."CUST_NAME"
        dataType: string
        lineageTag: a55d519d-fa21-4b31-aa40-414ab15e48a1

    column 'Region' = "CUSTOMERS"."REGION"
        dataType: string
        lineageTag: ef14f963-df5a-4ac4-8317-b2c3baa90afd

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/DIM_Employee.tmdl`

```
table DIM_Employee
    lineageTag: 732bf534-f655-46e2-a42f-e2aa755e0529

    partition DIM_Employee = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                DIM_Employee = Source{[Schema="dbo", Item="DIM_Employee"]}[Data]
            in
                DIM_Employee

    column 'Employee ID' = "EMPLOYEES"."EMP_ID"
        dataType: string
        lineageTag: c4969154-c534-4bb5-85bc-9bcdaa3913ee

    column 'Full Name' = "EMPLOYEES"."FIRST_NAME" & ' ' & "EMPLOYEES"."LAST_NAME"
        dataType: string
        lineageTag: 99a16388-e79c-44f1-a067-dbd559710416

    column 'Hire Date' = "EMPLOYEES"."HIRE_DATE"
        dataType: string
        lineageTag: f28fba98-7763-4375-8966-ec054c8dee88

    column 'Department' = "DEPARTMENTS"."DEPT_NAME"
        dataType: string
        lineageTag: 7bdba8ff-dc6a-4b41-8c85-75528d098f2a

    hierarchy OrgHierarchy
        level Country
            column: Country
        level City
            column: City
        level Department
            column: Department
        level Employee
            column: Employee

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/DIM_Location.tmdl`

```
table DIM_Location
    lineageTag: 17ddd5f2-545b-4cdc-98cb-8afc276bf3ae

    partition DIM_Location = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                DIM_Location = Source{[Schema="dbo", Item="DIM_Location"]}[Data]
            in
                DIM_Location

    column 'Location ID' = "LOCATIONS"."LOCATION_ID"
        dataType: string
        lineageTag: 98f1e5d1-602a-4165-ac76-180049400a58

    column 'City' = "LOCATIONS"."CITY"
        dataType: string
        lineageTag: 00a1b572-34c8-45cd-a029-f3134b010e77

    column 'Country' = "LOCATIONS"."COUNTRY"
        dataType: string
        lineageTag: e43a4bbf-2ef4-44e5-b96d-e00f703f761b

    hierarchy GeoHierarchy
        level Country
            column: Country
        level City
            column: City

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Dim_Channel.tmdl`

```
table Dim Channel
    lineageTag: 389caafa-21d1-4933-814e-8e2affe913da

    partition Dim Channel = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Dim_Channel = Source{[Schema="dbo", Item="Dim_Channel"]}[Data]
            in
                Dim_Channel

    column Channel Key
        dataType: string
        lineageTag: 3a86835a-216d-446f-9e3a-0a17f6d16ecb
        sourceColumn: Channel Key
        summarizeBy: none

    column Channel Name
        dataType: string
        lineageTag: eedf1aab-bbc1-4a85-8d21-9143d3ab4013
        sourceColumn: Channel Name
        summarizeBy: none

    column Channel Type
        dataType: string
        lineageTag: 51f72d55-2d5a-4ef2-a2ef-df61955e5ef9
        sourceColumn: Channel Type
        summarizeBy: none

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Dim_Customer.tmdl`

```
table Dim Customer
    lineageTag: 35f8a01a-52a2-445f-93f5-a7e547e9f418

    partition Dim Customer = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Dim_Customer = Source{[Schema="dbo", Item="Dim_Customer"]}[Data]
            in
                Dim_Customer

    column Customer Key
        dataType: string
        lineageTag: dbd788b7-789a-4bfa-a797-bc96ff608211
        sourceColumn: Customer Key
        summarizeBy: none

    column Customer Name
        dataType: string
        lineageTag: b36e8ca4-464b-44c6-8c12-ed2addcba463
        sourceColumn: Customer Name
        summarizeBy: none

    column Customer Class
        dataType: string
        lineageTag: 0ee009c7-6a60-4fb6-b186-b85b3650893e
        sourceColumn: Customer Class
        summarizeBy: none

    column Industry
        dataType: string
        lineageTag: 9c588214-cb76-4729-b51d-b86db976b31d
        sourceColumn: Industry
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: fefdc699-9143-4ad1-b552-77febfc40394
        sourceColumn: Region
        summarizeBy: none

    column Status
        dataType: string
        lineageTag: f808ad19-ae04-4d97-8f2d-4653cbfc0a1d
        sourceColumn: Status
        summarizeBy: none

    column Full Name Upper
        dataType: string
        lineageTag: 5016cf21-d2b1-480a-93e0-2d0b0767e231
        sourceColumn: Full Name Upper
        summarizeBy: none

    column Name Length
        dataType: string
        lineageTag: 352a2e79-31dc-4a60-952c-386fcb41f6ad
        sourceColumn: Name Length
        summarizeBy: none

    column Name Initial
        dataType: string
        lineageTag: ec0c5bed-a3e1-4e29-9327-4c42b6d45fd4
        sourceColumn: Name Initial
        summarizeBy: none

    column Display Name
        dataType: string
        lineageTag: 63619c66-f116-4530-999b-0dc69f508e34
        sourceColumn: Display Name
        summarizeBy: none

    column Customer Since Year
        dataType: string
        lineageTag: 031badfe-07d2-489e-8794-21164a57267d
        sourceColumn: Customer Since Year
        summarizeBy: none

    column Tenure Days
        dataType: string
        lineageTag: e21b1e48-f527-4a2a-b84e-6716f20f735b
        sourceColumn: Tenure Days
        summarizeBy: none

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Dim_Date.tmdl`

```
table Dim Date
    lineageTag: 98f159cb-3e2f-4c70-8743-59be989fd85a

    partition Dim Date = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Dim_Date = Source{[Schema="dbo", Item="Dim_Date"]}[Data]
            in
                Dim_Date

    column Date Key
        dataType: string
        lineageTag: 0982ee16-4c02-4798-8504-ffb846201ec8
        sourceColumn: Date Key
        summarizeBy: none

    column Calendar Date
        dataType: string
        lineageTag: 23f57aae-d62c-461e-a245-828c3795d2cb
        sourceColumn: Calendar Date
        summarizeBy: none

    column Year
        dataType: string
        lineageTag: a17ee150-7d30-40a3-ad76-2324a3e813f3
        sourceColumn: Year
        summarizeBy: none

    column Quarter
        dataType: string
        lineageTag: 4f8ddfd4-1660-4b27-8a9e-c98f1055c1e4
        sourceColumn: Quarter
        summarizeBy: none

    column Month Name
        dataType: string
        lineageTag: 00c92b35-d809-452d-b46e-36ca66aa7eac
        sourceColumn: Month Name
        summarizeBy: none

    column Fiscal Year
        dataType: string
        lineageTag: 31c299bb-42f9-407a-b592-061a137643a2
        sourceColumn: Fiscal Year
        summarizeBy: none

    column Fiscal Period
        dataType: string
        lineageTag: 85e97c51-9aa1-49a4-8419-97d4eb48bc8e
        sourceColumn: Fiscal Period
        summarizeBy: none

    hierarchy Calendar Hierarchy
        level Year
            column: Year
        level Quarter
            column: Quarter
        level Month Name
            column: Month Name
        level Calendar Date
            column: Calendar Date

    hierarchy Fiscal Hierarchy
        level Fiscal Year
            column: Fiscal Year
        level Fiscal Period
            column: Fiscal Period

    hierarchy Calendar Hierarchy
        level Year
            column: Year
        level Quarter
            column: Quarter
        level Month
            column: Month
        level Day
            column: Day

    hierarchy Fiscal Hierarchy
        level Fiscal Year
            column: Fiscal Year
        level Fiscal Period
            column: Fiscal Period

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Dim_Employee.tmdl`

```
table Dim Employee
    lineageTag: 867a48a5-b029-4940-a745-5fec522004a1

    partition Dim Employee = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Dim_Employee = Source{[Schema="dbo", Item="Dim_Employee"]}[Data]
            in
                Dim_Employee

    column Employee Key
        dataType: string
        lineageTag: 86c2c3a4-19fb-4f20-bfc6-52f9b6741c26
        sourceColumn: Employee Key
        summarizeBy: none

    column Full Name
        dataType: string
        lineageTag: ebe81017-e7cb-47ad-897a-6a2efef87f70
        sourceColumn: Full Name
        summarizeBy: none

    column Department
        dataType: string
        lineageTag: aa3e5e99-1ad9-402a-9033-d19afa83f2e8
        sourceColumn: Department
        summarizeBy: none

    column Job Title
        dataType: string
        lineageTag: dfec13c1-2d1b-4318-9a31-e3e3de7faffb
        sourceColumn: Job Title
        summarizeBy: none

    column Salary
        dataType: string
        lineageTag: 68c588ff-636a-497c-9532-6ce7a978db21
        sourceColumn: Salary
        summarizeBy: none

    column Annual Salary
        dataType: string
        lineageTag: 293a8e41-4381-4b00-8630-f342bd14ecbe
        sourceColumn: Annual Salary
        summarizeBy: none

    column Salary Band
        dataType: string
        lineageTag: bdbdd7fa-6465-4241-abb3-dae83df8548f
        sourceColumn: Salary Band
        summarizeBy: none

    column Years of Service
        dataType: string
        lineageTag: 79dd79e3-8e55-4c1f-8597-6575b6e8d0ec
        sourceColumn: Years of Service
        summarizeBy: none

    hierarchy Org Hierarchy
        level Department
            column: Department
        level Employee
            column: Employee

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Dim_Geography.tmdl`

```
table Dim Geography
    lineageTag: 45561b8c-39c7-4581-a5be-6734490a4117

    partition Dim Geography = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Dim_Geography = Source{[Schema="dbo", Item="Dim_Geography"]}[Data]
            in
                Dim_Geography

    column Geography Key
        dataType: string
        lineageTag: e173ffc2-6945-4e7c-8faf-0f9ded1c4bea
        sourceColumn: Geography Key
        summarizeBy: none

    column Country
        dataType: string
        lineageTag: 378dd707-022b-426f-a581-31c05bba8a8f
        sourceColumn: Country
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: 3bc2c161-2fc6-4ce9-8a6d-e50bd3177ed6
        sourceColumn: Region
        summarizeBy: none

    column State
        dataType: string
        lineageTag: 8c0a58c9-0d03-4eba-bdc9-4c6f7f967d06
        sourceColumn: State
        summarizeBy: none

    column City
        dataType: string
        lineageTag: 4281d2e3-bc6a-4d03-b388-e0ff0665be29
        sourceColumn: City
        summarizeBy: none

    hierarchy Geography Hierarchy
        level Country
            column: Country
        level Region
            column: Region
        level State
            column: State
        level City
            column: City

    hierarchy Geography Hierarchy
        level Country
            column: Country
        level Region
            column: Region
        level State
            column: State
        level City
            column: City

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Dim_Product.tmdl`

```
table Dim Product
    lineageTag: b54185da-7d90-40ea-9a51-171360c7fdfd

    partition Dim Product = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Dim_Product = Source{[Schema="dbo", Item="Dim_Product"]}[Data]
            in
                Dim_Product

    column Product Key
        dataType: string
        lineageTag: f0b5859b-bad1-4131-a9bf-87f6c0d1e961
        sourceColumn: Product Key
        summarizeBy: none

    column Product Name
        dataType: string
        lineageTag: e3d1fc8e-3708-4697-b04b-6a5692baffd3
        sourceColumn: Product Name
        summarizeBy: none

    column Category
        dataType: string
        lineageTag: 83262c0e-85dd-4c07-9646-ffa5d8a0c6d6
        sourceColumn: Category
        summarizeBy: none

    column Sub-Category
        dataType: string
        lineageTag: 86452271-4cb1-4b96-a08d-61406754ea83
        sourceColumn: Sub-Category
        summarizeBy: none

    column Brand
        dataType: string
        lineageTag: 72f2fb6e-1f40-47e2-9e6a-404fe6938c56
        sourceColumn: Brand
        summarizeBy: none

    column Unit Price
        dataType: string
        lineageTag: 1ae03cc5-cf65-4638-9778-72775322ef76
        sourceColumn: Unit Price
        summarizeBy: none

    column Price Tier
        dataType: string
        lineageTag: 3536abbd-0441-4b7a-ba54-b56bd463ae8b
        sourceColumn: Price Tier
        summarizeBy: none

    hierarchy Product Hierarchy
        level Category
            column: Category
        level Sub-Category
            column: Sub-Category
        level Product Name
            column: Product Name

    hierarchy Product Hierarchy
        level Category
            column: Category
        level Sub-Category
            column: Sub-Category
        level Product
            column: Product

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Dim_Warehouse.tmdl`

```
table Dim Warehouse
    lineageTag: 9889fe82-5fa9-40ff-9637-7ca021461bc4

    partition Dim Warehouse = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Dim_Warehouse = Source{[Schema="dbo", Item="Dim_Warehouse"]}[Data]
            in
                Dim_Warehouse

    column Warehouse Key
        dataType: string
        lineageTag: b9f29f02-ffd0-4585-a4af-4063ec32d451
        sourceColumn: Warehouse Key
        summarizeBy: none

    column Warehouse Name
        dataType: string
        lineageTag: 821901f0-b8a1-45bf-b3b4-06fa10c32220
        sourceColumn: Warehouse Name
        summarizeBy: none

    column Warehouse Region
        dataType: string
        lineageTag: 1ccef403-85e1-4598-b151-a5d7062b10cf
        sourceColumn: Warehouse Region
        summarizeBy: none

    column Capacity
        dataType: string
        lineageTag: 81c0bcd1-bc7f-43c8-aad0-8ce34d5e3bf4
        sourceColumn: Capacity
        summarizeBy: none

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Employee.tmdl`

```
table Employee
    lineageTag: 21dc81cb-fbad-453f-b59f-177ca5c76391

    partition Employee = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Employee = Source{[Schema="dbo", Item="Employee"]}[Data]
            in
                Employee

    column 'Employee Key' = "DIM_EMPLOYEE"."EMP_KEY"
        dataType: string
        lineageTag: 50b88ea6-37fd-4254-98f6-71e3fbb302d5

    column 'Full Name' = "DIM_EMPLOYEE"."FIRST_NAME" & ' ' & "DIM_EMPLOYEE"."LAST_NAME"
        dataType: string
        lineageTag: 3de7eef8-3de7-4cc7-93e3-a88e4a3f144f

    column 'Full Name Alt' = "DIM_EMPLOYEE"."FIRST_NAME" & ' ' & "DIM_EMPLOYEE"."LAST_NAME"
        dataType: string
        lineageTag: e7833807-aac8-4015-a875-fc41867610d1

    column 'Display Name' = UPPER(LEFT("DIM_EMPLOYEE"."LAST_NAME", 1)) & LOWER(MID("DIM_EMPLOYEE"."LAST_NAME", 2, LEN("DIM_EMPLOYEE"."LAST_NAME")))
        dataType: string
        lineageTag: b50b42b6-109e-44a3-83fe-abdf2dcf3e4d

    column 'Email Domain' = MID("DIM_EMPLOYEE"."EMAIL", FIND('@', "DIM_EMPLOYEE"."EMAIL") + 1, 50)
        dataType: string
        lineageTag: a2766ec9-65d3-419a-abbe-a4b1209c03e5

    column 'Email Prefix' = LEFT("DIM_EMPLOYEE"."EMAIL", FIND('@', "DIM_EMPLOYEE"."EMAIL") - 1)
        dataType: string
        lineageTag: 4b017706-aecc-44dc-96d0-0e8df2fe17d8

    column 'Name Length' = LEN("DIM_EMPLOYEE"."LAST_NAME")
        dataType: string
        lineageTag: df115293-3994-4d10-ab38-13e9f9e7ceed

    column 'Upper Name' = UPPER("DIM_EMPLOYEE"."LAST_NAME")
        dataType: string
        lineageTag: bdd5247f-020b-471a-9acb-c86a788d973f

    column 'Lower Name' = LOWER("DIM_EMPLOYEE"."FIRST_NAME")
        dataType: string
        lineageTag: 066737e0-3f54-4ee3-9367-9fb09af4ee55

    column 'Trimmed Notes' = TRIM("DIM_EMPLOYEE"."NOTES")
        dataType: string
        lineageTag: 957deae9-01a8-4888-b348-dfb860182f42

    column 'Left Trimmed' = TRIM("DIM_EMPLOYEE"."NOTES")
        dataType: string
        lineageTag: 218e1b39-53d0-4ef4-815a-daecfd4d3d97

    column 'Right Trimmed' = TRIM("DIM_EMPLOYEE"."NOTES")
        dataType: string
        lineageTag: 3274c550-066d-4b0f-a295-50fae57c2a7b

    column 'Clean Phone' = SUBSTITUTE("DIM_EMPLOYEE"."PHONE", '-', '')
        dataType: string
        lineageTag: 224cf584-31e1-4e49-8155-bf7d57b1e392

    column 'Padded Job Code' = REPT('0', 8 - LEN("DIM_EMPLOYEE"."JOB_CODE")) & "DIM_EMPLOYEE"."JOB_CODE"
        dataType: string
        lineageTag: cd5192a9-5786-4a84-8aae-951bf56dd692

    column 'Right Padded' = "DIM_EMPLOYEE"."JOB_CODE" & REPT(' ', 10 - LEN("DIM_EMPLOYEE"."JOB_CODE"))
        dataType: string
        lineageTag: 0be557ea-1319-4205-92e0-c15160dd29c6

    column 'Name Char Code' = UNICODE("DIM_EMPLOYEE"."FIRST_NAME")
        dataType: string
        lineageTag: 17c9723d-84b3-46b1-8e9d-50c19c3fcec9

    column 'Char From Code' = UNICHAR(65)
        dataType: string
        lineageTag: b23ecc5d-8e94-4f0f-9680-56cc0baff948

    column 'Translated Status' = SUBSTITUTE("DIM_EMPLOYEE"."STATUS", 'A', 'Active')
        dataType: string
        lineageTag: 51bc3b52-1734-4dff-a89d-d9060fcbbca4

    column 'Safe Department' = IF(ISBLANK("DIM_EMPLOYEE"."DEPARTMENT"), 'Unassigned', "DIM_EMPLOYEE"."DEPARTMENT")
        dataType: string
        lineageTag: ef046a34-5e91-4380-971a-5ac7bbc25fe7

    column 'NVL Department' = IF(ISBLANK("DIM_EMPLOYEE"."DEPARTMENT"), 'General', "DIM_EMPLOYEE"."DEPARTMENT")
        dataType: string
        lineageTag: 53e044e8-69e4-4aaa-b867-335a7c2705e9

    column 'Department Label' = IF(ISBLANK("DIM_EMPLOYEE"."DEPARTMENT"), 'N/A', "DIM_EMPLOYEE"."DEPARTMENT")
        dataType: string
        lineageTag: 33b69e9d-f9f0-48d1-bb0a-bacc199c2274

    column 'Coalesce Name' = COALESCE("DIM_EMPLOYEE"."DEPARTMENT", "DIM_EMPLOYEE"."JOB_CODE", 'None')
        dataType: string
        lineageTag: 93619bf9-86ff-4924-93d1-3d7f34edac98

    column 'NullIf Blank' = IF("DIM_EMPLOYEE"."STATUS" = '', BLANK(), "DIM_EMPLOYEE"."STATUS")
        dataType: string
        lineageTag: 3e97fd74-e301-46bc-98b4-4f36772ccf0b

    column 'Greater Salary' = IF("DIM_EMPLOYEE"."SALARY" >= 50000, "DIM_EMPLOYEE"."SALARY", 50000)
        dataType: string
        lineageTag: 769452ea-aab5-4a21-9f25-e3dfdaccc883

    column 'Lower Bound' = IF("DIM_EMPLOYEE"."SALARY" <= 200000, "DIM_EMPLOYEE"."SALARY", 200000)
        dataType: string
        lineageTag: 532e711d-a053-4e58-aeb1-628b9180effa

    column 'Status Label (DECODE)' = SWITCH("DIM_EMPLOYEE"."STATUS",
    'A', 'Active',
    'I', 'Inactive',
    'T', 'Terminated',
    'Unknown'
)
        dataType: string
        lineageTag: 2ca6e20c-a372-430b-b988-aa9da67cd0d8

    column 'Salary Band' = SWITCH(TRUE(),
    "DIM_EMPLOYEE"."SALARY" > 100000, 'Senior',
    "DIM_EMPLOYEE"."SALARY" > 60000, 'Mid',
    'Junior'
)
        dataType: string
        lineageTag: 8c6a4894-0971-42b6-b6ba-2fba80827c50

    column 'Salary as Int' = INT("DIM_EMPLOYEE"."SALARY")
        dataType: string
        lineageTag: cd056f28-cc14-45de-8460-82250dcd9cd1

    column 'Key as String' = FORMAT("DIM_EMPLOYEE"."EMP_KEY", "General")
        dataType: string
        lineageTag: fb6ee444-4680-4b73-b0d0-765a7af6a204

    column 'Numeric Code' = VALUE("DIM_EMPLOYEE"."JOB_CODE")
        dataType: string
        lineageTag: c120b545-167c-44f9-aa10-0ec1aa03fc05

    column 'Hire Year' = YEAR("DIM_EMPLOYEE"."HIRE_DATE")
        dataType: string
        lineageTag: 55d092a2-125c-403a-b36b-1ce8fcc8fd90

    column 'Hire Month' = MONTH("DIM_EMPLOYEE"."HIRE_DATE")
        dataType: string
        lineageTag: 5572d83e-7e50-44e6-b250-b37383c47a57

    column 'Hire Quarter' = QUARTER("DIM_EMPLOYEE"."HIRE_DATE")
        dataType: string
        lineageTag: 21c5b6ba-28f0-474e-971c-535de09fea1b

    column 'Months Employed' = DATEDIFF("DIM_EMPLOYEE"."HIRE_DATE", TODAY(), MONTH)
        dataType: string
        lineageTag: d0a84c17-4096-4c42-a1a6-20e93db39615

    column 'Next Review Date' = EDATE("DIM_EMPLOYEE"."HIRE_DATE", 12)
        dataType: string
        lineageTag: be427204-706d-4d06-8b02-19984b6f6a8c

    column 'End of Hire Month' = EOMONTH("DIM_EMPLOYEE"."HIRE_DATE", 0)
        dataType: string
        lineageTag: f6d4ded3-fd88-428d-b62f-451e3e9145c7

    column 'Today' = TODAY()
        dataType: string
        lineageTag: a65832c4-542f-4c96-bd54-3a5a5df913ef

    column 'Now Timestamp' = NOW()
        dataType: string
        lineageTag: e06ce52d-7a51-4258-992e-473d1a2d5b3d

    column 'System Date' = NOW()
        dataType: string
        lineageTag: bafb017d-a7b7-4a06-959e-9db5d59cd91f

    column 'Hire Date Formatted' = FORMAT("DIM_EMPLOYEE"."HIRE_DATE", 'YYYY-MM-DD')
        dataType: string
        lineageTag: 9356d6bd-d50e-4886-a519-e8fb94f6651e

    column 'Salary Abs Diff' = ABS("DIM_EMPLOYEE"."SALARY" - 75000)
        dataType: string
        lineageTag: e550a9a1-96d8-4763-b64c-c7520547784d

    column 'Rounded Salary' = ROUND("DIM_EMPLOYEE"."SALARY", -3)
        dataType: string
        lineageTag: c093dca3-09cf-495f-a944-e7ce3b2523c4

    column 'Salary Ceiling' = CEILING("DIM_EMPLOYEE"."SALARY" / 1000, 1)
        dataType: string
        lineageTag: b3bfa746-cd8c-4f7d-9ccb-2b8c4b23b930

    column 'Salary Floor' = FLOOR("DIM_EMPLOYEE"."SALARY" / 1000, 1)
        dataType: string
        lineageTag: 58c2acc3-99e6-4d6f-a89d-11b999575f03

    column 'Salary Squared' = POWER("DIM_EMPLOYEE"."SALARY", 2)
        dataType: string
        lineageTag: 49d95372-d97f-4c11-bb12-c8c5a15676bb

    column 'Salary Sqrt' = SQRT("DIM_EMPLOYEE"."SALARY")
        dataType: string
        lineageTag: 414b78c8-b5d8-49fd-8550-21aa19a2200f

    column 'Salary Log' = LN("DIM_EMPLOYEE"."SALARY")
        dataType: string
        lineageTag: da5fa390-c2b1-4d2b-9f6f-8dc7f967c3ff

    column 'Salary Exp' = EXP(1)
        dataType: string
        lineageTag: 9071f444-7b29-44d3-8be5-f64b7fd08d9e

    column 'Key Modulo' = MOD("DIM_EMPLOYEE"."EMP_KEY", 10)
        dataType: string
        lineageTag: 9a2c7cfd-0cd9-4557-9515-ad96b772c379

    column 'Salary Sign' = SIGN("DIM_EMPLOYEE"."SALARY" - 75000)
        dataType: string
        lineageTag: 6b528107-8dc7-48fd-9771-68e434255672

    column 'Current User' = USERPRINCIPALNAME()
        dataType: string
        lineageTag: 58af0c4e-dc81-438b-8aee-466464f57e24

    column 'Random Value' = RAND()
        dataType: string
        lineageTag: 401f1116-2f00-4298-833f-865db5c7d6da

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Enterprise_Sales.tmdl`

```
table Enterprise Sales
    lineageTag: 85d93565-04b7-4f3c-acd3-5e958ae80697

    partition Enterprise Sales = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Enterprise_Sales = Source{[Schema="dbo", Item="Enterprise_Sales"]}[Data]
            in
                Enterprise_Sales

    column CustomerName
        dataType: string
        lineageTag: da15b07c-ab1f-4b1e-a371-de58ce169535
        sourceColumn: CustomerName
        summarizeBy: none

    column Segment
        dataType: string
        lineageTag: a25be008-d299-4d99-812c-c55ac5a01a95
        sourceColumn: Segment
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: d2c45568-b6c3-4f43-af12-2afb8eb6a8fb
        sourceColumn: Region
        summarizeBy: none

    column Country
        dataType: string
        lineageTag: e8d640b2-5045-4b45-9d8c-560a9a9b7cc2
        sourceColumn: Country
        summarizeBy: none

    column Category
        dataType: string
        lineageTag: 3272226b-1703-46ab-9c4f-9881a4923b47
        sourceColumn: Category
        summarizeBy: none

    column Subcategory
        dataType: string
        lineageTag: 3c09134d-7eab-4d13-9b53-d4f203ad4b59
        sourceColumn: Subcategory
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: 4e08c7d8-e306-44a2-a2d2-ee57a3ba0f4f
        sourceColumn: OrderDate
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: f5ed4b58-0326-4d00-9aee-7f8a422beba8
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column UnitPrice
        dataType: string
        lineageTag: a6c463da-6725-4892-85bc-1bb5077251fb
        sourceColumn: UnitPrice
        summarizeBy: none

    column UnitCost
        dataType: string
        lineageTag: 72e74093-e099-4edb-a222-5d66c1493d24
        sourceColumn: UnitCost
        summarizeBy: none

    column DiscountPct
        dataType: string
        lineageTag: a4734d96-686e-4149-823a-a4fac8124066
        sourceColumn: DiscountPct
        summarizeBy: none

    column 'Revenue' = [Quantity] * [UnitPrice] * (1 - [DiscountPct])
        dataType: string
        lineageTag: 7991ff68-488e-46fd-9701-f2328a4c53aa

    column 'Profit' = [Revenue] - ([Quantity] * [UnitCost])
        dataType: string
        lineageTag: 2b14c49e-5e5c-41ea-836b-1c850be1b5a2

    column 'ProfitMargin' = IF [Revenue] > 0 THEN [Profit] / [Revenue] ELSE 0 END
        dataType: string
        lineageTag: 2fe9b573-bec5-45ab-baa9-1dda0b8fa1d1

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Entity.tmdl`

```
table Entity
    lineageTag: 874e32cc-520d-4aea-ba9d-ad43cd8cbef5

    partition Entity = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
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

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/FACT_Orders.tmdl`

```
table FACT_Orders
    lineageTag: 1131fd40-b700-40d5-a243-c9b8f0b4b60a

    partition FACT_Orders = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                FACT_Orders = Source{[Schema="dbo", Item="FACT_Orders"]}[Data]
            in
                FACT_Orders

    column 'Order ID' = "ORDERS"."ORDER_ID"
        dataType: string
        lineageTag: cbabfc27-b026-4123-a5cc-975685c0b92d

    column 'Order Amount' = "ORDERS"."AMOUNT"
        dataType: string
        lineageTag: d72c68e9-59df-48e0-9d9e-fba32d0e5d5d

    measure 'FACT_Orders_Profit' = SUM('FACT_Orders'["ORDERS"."AMOUNT"]) * 0.2
        lineageTag: 3c7c9dad-5dd2-41c7-a68f-0b0d7f559a1d
        formatString: #,0.00
        displayFolder: Measures

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/FACT_Payroll.tmdl`

```
table FACT_Payroll
    lineageTag: 9e3bf555-49b4-4f8e-99ef-a7ce0595bf81

    partition FACT_Payroll = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                FACT_Payroll = Source{[Schema="dbo", Item="FACT_Payroll"]}[Data]
            in
                FACT_Payroll

    column 'Pay ID' = "PAYROLL"."PAY_ID"
        dataType: string
        lineageTag: 3c934013-5622-4b7b-b770-85483bad5139

    column 'Gross Pay' = "PAYROLL"."GROSS_PAY"
        dataType: string
        lineageTag: ade1fb9a-4c13-4e53-8ebb-041c60d717a7

    column 'Net Pay' = "PAYROLL"."GROSS_PAY" - "PAYROLL"."DEDUCTIONS"
        dataType: string
        lineageTag: c87e1622-6c22-45c1-9c95-965d7771b1c1

    measure 'Avg Salary' = AVERAGE('FACT_Payroll'["EMPLOYEES"."SALARY"])
        lineageTag: 61740fde-d2a4-48ca-b751-5451e2a5182e
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Fact_GL.tmdl`

```
table Fact GL
    lineageTag: 6d1ca0c7-ca8f-4624-9066-cf6871b58894

    partition Fact GL = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Fact_GL = Source{[Schema="dbo", Item="Fact_GL"]}[Data]
            in
                Fact_GL

    column Amount
        dataType: string
        lineageTag: 5da6a24b-9dab-4e34-b0ff-f32015e4f0c1
        sourceColumn: Amount
        summarizeBy: none

    column Actual Amount
        dataType: string
        lineageTag: be4d6579-9731-436b-b023-fd5ee71032e2
        sourceColumn: Actual Amount
        summarizeBy: none

    column Budget Amount
        dataType: string
        lineageTag: 1a869109-265b-41c4-aa70-18b35f1c9d99
        sourceColumn: Budget Amount
        summarizeBy: none

    column Variance
        dataType: string
        lineageTag: 60480642-da5e-489a-915a-0f04472f2cd7
        sourceColumn: Variance
        summarizeBy: none

    column Variance %
        dataType: string
        lineageTag: 53d105b2-d94c-475c-b332-3c8f009a1417
        sourceColumn: Variance %
        summarizeBy: none

    column Amount Prior Year
        dataType: string
        lineageTag: 53ee6955-db46-4e47-855b-08aea2f6eb74
        sourceColumn: Amount Prior Year
        summarizeBy: none

    column Amount YTD
        dataType: string
        lineageTag: a85af213-0118-46e4-b254-a874500d7533
        sourceColumn: Amount YTD
        summarizeBy: none

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Fact_Inventory.tmdl`

```
table Fact Inventory
    lineageTag: 3fb32310-e7a9-4cb3-a099-4a56696d9448

    partition Fact Inventory = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Fact_Inventory = Source{[Schema="dbo", Item="Fact_Inventory"]}[Data]
            in
                Fact_Inventory

    column Quantity On Hand
        dataType: string
        lineageTag: b490224e-d977-4697-b914-2e8b501a5932
        sourceColumn: Quantity On Hand
        summarizeBy: none

    column Quantity On Order
        dataType: string
        lineageTag: 99f3c7c8-0afb-484a-a13f-1d20f6b00e02
        sourceColumn: Quantity On Order
        summarizeBy: none

    column Inventory Value
        dataType: string
        lineageTag: e3fdb3db-7db4-4375-9a88-1c3ecb1ae867
        sourceColumn: Inventory Value
        summarizeBy: none

    column Days of Supply
        dataType: string
        lineageTag: 0fa0710c-f0ae-4e2a-b1b3-9873278c5962
        sourceColumn: Days of Supply
        summarizeBy: none

    column Below Reorder
        dataType: string
        lineageTag: 1aa042e9-495f-45a3-8b20-4c8a3ad05e8d
        sourceColumn: Below Reorder
        summarizeBy: none

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Fact_Sales.tmdl`

```
table Fact Sales
    lineageTag: cbb200b4-586f-4695-9a20-e9a4e58c46aa

    partition Fact Sales = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Fact_Sales = Source{[Schema="dbo", Item="Fact_Sales"]}[Data]
            in
                Fact_Sales

    column Revenue
        dataType: string
        lineageTag: d07d9e5b-ff10-40bd-9b36-858b5a80e6d8
        sourceColumn: Revenue
        summarizeBy: none

    column Cost
        dataType: string
        lineageTag: 67087513-fdb6-4ddb-8cca-027ac180e299
        sourceColumn: Cost
        summarizeBy: none

    column Quantity
        dataType: string
        lineageTag: 73725677-adb4-4a0f-aed6-c147b5ae1473
        sourceColumn: Quantity
        summarizeBy: none

    column Discount
        dataType: string
        lineageTag: f7655510-db65-492e-882d-fa2fa5abd8aa
        sourceColumn: Discount
        summarizeBy: none

    column Profit
        dataType: string
        lineageTag: 38c98ed4-63a4-4b1d-b89a-9498083e7ad0
        sourceColumn: Profit
        summarizeBy: none

    column Margin %
        dataType: string
        lineageTag: 3e36ae8f-af2d-4dc0-8fa9-d3c728c0bd70
        sourceColumn: Margin %
        summarizeBy: none

    column Avg Deal Size
        dataType: string
        lineageTag: c2316660-159a-4ead-a652-1ee24e905ac8
        sourceColumn: Avg Deal Size
        summarizeBy: none

    column Order Count
        dataType: string
        lineageTag: 2d008bed-b4c5-49cd-b41f-20c80f90a601
        sourceColumn: Order Count
        summarizeBy: none

    column Revenue LY
        dataType: string
        lineageTag: b9334e9a-61c1-4528-8a42-25bdbe3c9142
        sourceColumn: Revenue LY
        summarizeBy: none

    column Revenue YTD
        dataType: string
        lineageTag: 215efe5e-912c-4ad1-aa66-4dd5f20f29ce
        sourceColumn: Revenue YTD
        summarizeBy: none

    column Revenue QTD
        dataType: string
        lineageTag: d3c8ddf6-9c77-446b-9ce3-0aea7e32f4b5
        sourceColumn: Revenue QTD
        summarizeBy: none

    column Revenue Rolling 3M
        dataType: string
        lineageTag: 338392fd-87e9-4928-a993-cdb3eeaee465
        sourceColumn: Revenue Rolling 3M
        summarizeBy: none

    column Revenue Moving Avg 6M
        dataType: string
        lineageTag: c9266595-6fb6-4030-8b84-3a57b4af058a
        sourceColumn: Revenue Moving Avg 6M
        summarizeBy: none

    column Revenue Running Sum
        dataType: string
        lineageTag: 2b7a39ec-7ae5-4ce0-bb83-dde7346bd249
        sourceColumn: Revenue Running Sum
        summarizeBy: none

    column Revenue Growth %
        dataType: string
        lineageTag: d992ac18-9d58-479e-bdc9-dc4ddbb9273b
        sourceColumn: Revenue Growth %
        summarizeBy: none

    column Revenue Rank
        dataType: string
        lineageTag: 2ddfd502-d11d-4ae9-b995-c8c2ba4abcab
        sourceColumn: Revenue Rank
        summarizeBy: none

    column Revenue Dense Rank
        dataType: string
        lineageTag: 25e4c3ff-3d31-4296-8682-aeb24e6f7478
        sourceColumn: Revenue Dense Rank
        summarizeBy: none

    column Revenue Ntile 4
        dataType: string
        lineageTag: 3efdad86-090d-4ff1-99ed-a4317f68da05
        sourceColumn: Revenue Ntile 4
        summarizeBy: none

    column Revenue Ratio
        dataType: string
        lineageTag: 835f3ccc-968c-4f0f-bea0-4dcc20c81b84
        sourceColumn: Revenue Ratio
        summarizeBy: none

    column Revenue Percentile
        dataType: string
        lineageTag: b93ecc30-545a-4b65-8bf5-aaac8ae1cf14
        sourceColumn: Revenue Percentile
        summarizeBy: none

    column Revenue Category
        dataType: string
        lineageTag: 64d970b2-279f-4dc9-b96b-4f10d0188569
        sourceColumn: Revenue Category
        summarizeBy: none

    column High Value Orders
        dataType: string
        lineageTag: 9513baad-dfe8-4cf9-ba2a-c69ccdac2c17
        sourceColumn: High Value Orders
        summarizeBy: none

    column Discount Revenue
        dataType: string
        lineageTag: 8b7fa6b1-e90e-4661-81ff-c083bdae48a0
        sourceColumn: Discount Revenue
        summarizeBy: none

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/General_Ledger.tmdl`

```
table General_Ledger
    lineageTag: a4f8fc5d-dd71-45cd-8d1c-e2e61dc3dfce

    partition General_Ledger = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                General_Ledger = Source{[Schema="dbo", Item="General_Ledger"]}[Data]
            in
                General_Ledger

    measure 'Net Amount' = SUM('General_Ledger'["FACT_GL"."DEBIT_AMOUNT"]) - SUM('General_Ledger'["FACT_GL"."CREDIT_AMOUNT"])
        lineageTag: 1edad4b4-b2ff-40d9-bfcd-34653b7ff1bf
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Converted Amount' = SUM('General_Ledger'["FACT_GL"."DEBIT_AMOUNT" * "FACT_GL"."EXCHANGE_RATE"])
        lineageTag: ea53142d-82d1-4c02-a4ef-48b807faaeeb
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'General_Ledger_Budget Variance' = SUM('General_Ledger'["FACT_GL"."DEBIT_AMOUNT"]) - SUM('General_Ledger'["FACT_BUDGET"."BUDGET_AMOUNT"])
        lineageTag: d507dee4-a482-4e1c-abba-2fcaaa7a70f6
        formatString: #,0.00
        displayFolder: Measures

    measure 'Budget Variance Pct' = SWITCH(TRUE(),
    SUM('General_Ledger'["FACT_BUDGET"."BUDGET_AMOUNT"]) = 0, 0,
    (SUM('General_Ledger'["FACT_GL"."DEBIT_AMOUNT"]) - SUM('General_Ledger'["FACT_BUDGET"."BUDGET_AMOUNT"])) / SUM('General_Ledger'["FACT_BUDGET"."BUDGET_AMOUNT"]) * 100
)
        lineageTag: 41808061-4db4-4efb-934f-65821e5927f3
        formatString: 0.00%
        displayFolder: Measures

    measure 'Top N Accounts' = TOPN(10, 'General_Ledger', SUM('General_Ledger'["FACT_GL"."DEBIT_AMOUNT"]))
        lineageTag: 6f00bb76-22c9-47db-8ad0-7440100f58c9
        formatString: #,0.00
        displayFolder: Measures

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Product.tmdl`

```
table Product
    lineageTag: 903990ed-cf49-481c-86e7-ee53d167113c

    partition Product = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Product = Source{[Schema="dbo", Item="Product"]}[Data]
            in
                Product

    column 'Product Name' = "DIM_PRODUCT"."PRODUCT_NAME"
        dataType: string
        lineageTag: 4d849070-e516-417c-b025-de1c6556e62e

    column 'Category' = "DIM_PRODUCT"."CATEGORY"
        dataType: string
        lineageTag: 541e7042-a814-49ee-a72f-bee9d548a9d5

    column 'Subcategory' = "DIM_PRODUCT"."SUBCATEGORY"
        dataType: string
        lineageTag: ab0e19c0-b695-45fa-8821-9dac43f9859a

    column 'Brand' = "DIM_PRODUCT"."BRAND"
        dataType: string
        lineageTag: 4d1449a0-b104-40a8-8d25-5dd566e88f2c

    column 'Margin Pct' = ("DIM_PRODUCT"."UNIT_PRICE" - "DIM_PRODUCT"."UNIT_COST") / "DIM_PRODUCT"."UNIT_PRICE" * 100
        dataType: string
        lineageTag: d1d06f8d-df63-4474-b188-75d48818b6eb

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

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Returns.tmdl`

```
table Returns
    lineageTag: 4385215b-a41c-4f37-a2a9-3f0de9154c32

    partition Returns = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Returns = Source{[Schema="dbo", Item="Returns"]}[Data]
            in
                Returns

    column 'Return Quantity' = "FACT_RETURNS"."RETURN_QUANTITY"
        dataType: string
        lineageTag: 72cd9a70-95fe-4e41-973a-cd8630d49340

    column 'Reason Code' = "FACT_RETURNS"."REASON_CODE"
        dataType: string
        lineageTag: 5ca0494a-2433-4b11-b074-0f0d6e4700c5

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Sales.tmdl`

```
table Sales
    lineageTag: 7654ff35-3a28-42e7-89dd-6b6d42a770c9

    partition Sales = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Sales = Source{[Schema="dbo", Item="Sales"]}[Data]
            in
                Sales

    column 'Quantity' = "FACT_SALES"."QUANTITY"
        dataType: string
        lineageTag: ef4d5039-3fb1-4a78-8dd7-96090834b508

    measure 'Revenue' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"]))
        lineageTag: bd518621-7847-4244-b020-40fc8d070485
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Cost' = SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])
        lineageTag: b632c572-f4b3-4a95-8dca-80aadab729a6
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Profit' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"])) - SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])
        lineageTag: bb322745-951b-43a1-bed8-9023e6a23523
        formatString: #,0.00
        displayFolder: Measures

    measure 'Profit Margin' = SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) = 0, 0,
    (SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE" * (1 - "FACT_SALES"."DISCOUNT_PCT"])) - SUM('Sales'["FACT_SALES"."QUANTITY" * "DIM_PRODUCT"."UNIT_COST"])) / SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) * 100
)
        lineageTag: 3f77e37d-deb2-4aed-b84b-abe257871241
        formatString: #,0.00
        displayFolder: Measures

    measure 'Return Rate' = SWITCH(TRUE(),
    SUM('Sales'["FACT_SALES"."QUANTITY"]) = 0, 0,
    SUM('Sales'["FACT_RETURNS"."RETURN_QUANTITY"]) / SUM('Sales'["FACT_SALES"."QUANTITY"]) * 100
)
        lineageTag: d9dbc92d-210b-4721-bf19-4ebceb056d7c
        formatString: 0.00%
        displayFolder: Measures

    measure 'Budget Variance' = SUM('Sales'["FACT_SALES"."QUANTITY" * "FACT_SALES"."UNIT_PRICE"]) - SUM('Sales'["FACT_BUDGET"."BUDGET_AMOUNT"])
        lineageTag: ff2937a4-a70c-450f-9140-a50fda9cda96
        formatString: #,0.00
        displayFolder: Measures

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Sales_Analytics.tmdl`

```
table Sales_Analytics
    lineageTag: f9ba88d9-a20d-4aff-ae10-2dc1a2beb758

    partition Sales_Analytics = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Sales_Analytics = Source{[Schema="dbo", Item="Sales_Analytics"]}[Data]
            in
                Sales_Analytics

    column 'Revenue Quartile' = INT(RANKX(ALL('Sales_Analytics'), 1, , ASC) * 4 / COUNTROWS(ALL('Sales_Analytics'))) + 1
        dataType: string
        lineageTag: 1f0e3db6-0261-44e7-ad88-d0d00603eb01

    column 'Cumulative Distribution' = DIVIDE(RANKX(ALL('Sales_Analytics'), 1, , ASC), COUNTROWS(ALL('Sales_Analytics')))
        dataType: string
        lineageTag: dd174bfa-0185-4958-b9e8-caf4c2bb4c04

    column 'Percentile Rank' = DIVIDE(RANKX(ALL('Sales_Analytics'), 1, , ASC) - 1, COUNTROWS(ALL('Sales_Analytics')) - 1)
        dataType: string
        lineageTag: 5eba1df0-2798-405b-9c0b-49b51860a073

    column 'Median Revenue' = MEDIAN('Sales_Analytics'["FACT_SALES"."REVENUE"])
        dataType: string
        lineageTag: ac01c3c8-a1fe-4d71-a647-c8c0994350c3

    column 'Revenue StdDev' = 'STDEV'[S]('Sales_Analytics'["FACT_SALES"."REVENUE"])
        dataType: string
        lineageTag: 83bf5ac5-7a34-4d47-af74-600d2c84454b

    column 'Revenue 90th Pct' = 'PERCENTILEX'[INC]('Sales_Analytics', 'Sales_Analytics'["FACT_SALES"."REVENUE"], 0.9)
        dataType: string
        lineageTag: 5535d751-6c8f-45f8-9f87-437dd861b645

    column 'High Value Sales Count' = CALCULATE(COUNT('Sales_Analytics'["FACT_SALES"."REVENUE"]), "FACT_SALES"."REVENUE" > 10000)
        dataType: string
        lineageTag: 98e593a6-6822-4f89-8a96-80f721aab01a

    column 'Discounted Revenue Sum' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), "FACT_SALES"."DISCOUNT_AMOUNT" > 0)
        dataType: string
        lineageTag: 215c6f6d-8b5e-4c31-a32b-fd312df326bd

    measure 'Total Revenue' = SUM('Sales_Analytics'["FACT_SALES"."REVENUE"])
        lineageTag: 5e5f8973-a4df-4636-88b2-3cbb36ac05c4
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Total Cost' = SUM('Sales_Analytics'["FACT_SALES"."COST"])
        lineageTag: 0c5372ac-8d60-4b78-8d13-1dbc487b9b2b
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Total Quantity' = SUM('Sales_Analytics'["FACT_SALES"."QUANTITY"])
        lineageTag: 18fe6010-05be-4b4b-82c4-0e2a4cd17d6a
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Revenue Prior Year' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DATEADD('Date'[Date], -1, YEAR))
        lineageTag: 053c9349-99a0-486e-8219-e149c91357e2
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence

    measure 'Revenue Prior Quarter' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DATEADD('Date'[Date], -1, QUARTER))
        lineageTag: 401bb387-1363-410e-a3d3-a9720c39822d
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence

    measure 'Revenue Prior Month' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DATEADD('Date'[Date], -1, MONTH))
        lineageTag: 61a99631-66f3-463d-9679-3c74683312de
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence

    measure 'Revenue YTD' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DATESYTD('Date'[Date]))
        lineageTag: 4028c5ae-43e6-49bc-aa76-df1a3e813cf3
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence

    measure 'Revenue QTD' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DATESQTD('Date'[Date]))
        lineageTag: eaba44fa-9a6a-4144-a427-4d2e2d906a4c
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence

    measure 'Revenue MTD' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DATESMTD('Date'[Date]))
        lineageTag: 2d47e268-8771-404c-a863-8929c6226526
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence

    measure 'Revenue WTD' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -7, DAY))
        lineageTag: 84b990bc-2d4d-46a3-9f9b-23704bd69bce
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence

    measure 'Rolling 30 Day Revenue' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DATESINPERIOD('Date'[Date], MAX('Date'[Date]), 30, DAY))
        lineageTag: bc682fe2-0c3a-40bb-b86b-fb5feaf96810
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence

    measure 'Rolling 90 Day Revenue' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DATESINPERIOD('Date'[Date], MAX('Date'[Date]), 90, DAY))
        lineageTag: 51685168-a9c2-4577-a842-30322f250cb0
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence

    measure 'Running Total Revenue' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"], FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date]))))
        lineageTag: bdcc6f99-db24-434d-af6d-55f5f1db4932
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Time Intelligence

    measure 'Running Count' = CALCULATE(COUNTROWS({tbl}), FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date]))))
        lineageTag: 7eb2afb5-4f71-4128-86df-dd0ba7d337a2
        formatString: #,0.00
        displayFolder: Measures

    measure 'Running Max Revenue' = CALCULATE(MAX(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date]))))
        lineageTag: ea0e0b06-f39e-4117-83da-142b88624eff
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Running Min Revenue' = CALCULATE(MIN(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date]))))
        lineageTag: fe2081cd-ed7e-474e-8e7f-71466cb977dc
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure '7 Day Moving Avg' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -7, DAY)) / 7
        lineageTag: 68842387-b8a6-47c9-b861-4c1f2b9d2acc
        formatString: #,0.00
        displayFolder: Measures

    measure '30 Day Moving Sum' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -30, DAY))
        lineageTag: bc14758d-132f-42d1-85c1-13a9bf7c2be9
        formatString: #,0.00
        displayFolder: Measures

    measure 'Same Period Last Year' = CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]), PARALLELPERIOD('Date'[Date], -1, YEAR))
        lineageTag: c81d40e7-3f86-483f-b0eb-5222270a7225
        formatString: #,0.00
        displayFolder: Time Intelligence

    measure 'Opening Balance Year' = OPENINGBALANCEYEAR(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"], 'Date'[Date]))
        lineageTag: 86a64bde-20ef-4b1f-a7dd-aabbe3c8d8cf
        formatString: #,0.00
        displayFolder: Measures

    measure 'Closing Balance Year' = CLOSINGBALANCEYEAR(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"], 'Date'[Date]))
        lineageTag: 6c49e4f8-e9af-4324-97e6-32fbe285429f
        formatString: #,0.00
        displayFolder: Measures

    measure 'Revenue Rank' = RANKX(ALL('Sales_Analytics'), SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]))
        lineageTag: 02545479-f52b-482d-99d4-1d7daab15c0f
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Revenue Dense Rank' = RANKX(ALL('Sales_Analytics'), SUM('Sales_Analytics'["FACT_SALES"."REVENUE"], , ASC, DENSE))
        lineageTag: 25ea27a2-6901-4934-bd7f-26a6dc33f645
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Revenue Share' = DIVIDE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"], CALCULATE(SUM('Sales_Analytics'["FACT_SALES"."REVENUE"], ALL('Sales_Analytics'))))
        lineageTag: 702d544e-d2dc-4e23-91fb-79c74ad2f54c
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        displayFolder: Measures

    measure 'Distinct Products Sold' = DISTINCTCOUNT('Sales_Analytics'["FACT_SALES"."PRODUCT_KEY"])
        lineageTag: cddb04d4-21a3-471b-a979-c3e3b20df55f
        formatString: #,0.00
        displayFolder: Measures

    measure 'Forecast Variance' = SUM('Sales_Analytics'["FACT_SALES"."REVENUE"]) - SUM('Sales_Analytics'["FACT_FORECAST"."FORECAST_AMOUNT"])
        lineageTag: a91034e3-8d11-47ac-b5e6-2d2c95b755d7
        formatString: #,0.00
        displayFolder: Measures

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Sales_DB.tmdl`

```
table Sales DB
    lineageTag: 02f1f1f9-1f7e-4aa7-905a-01fb9d808a34

    partition Sales DB = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Sales_DB = Source{[Schema="dbo", Item="Sales_DB"]}[Data]
            in
                Sales_DB

    column OrderID
        dataType: string
        lineageTag: 1d751815-5367-4fcf-8c71-39e7a7da6fd1
        sourceColumn: OrderID
        summarizeBy: none

    column CustomerName
        dataType: string
        lineageTag: d90d2aee-bf57-4c03-b4dd-251120058a38
        sourceColumn: CustomerName
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: 2dadb899-3645-4d44-bb29-3fe3a1cba356
        sourceColumn: Region
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: 5db8a9ce-f6e9-42cc-b59b-f79b0cd0abba
        sourceColumn: OrderDate
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: 9bc54811-e76a-439f-92e9-17690b61312c
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column Amount
        dataType: string
        lineageTag: 3cefd610-2b55-4da6-8ff6-42af24ef2c7c
        sourceColumn: Amount
        summarizeBy: none

    column 'Revenue' = [Amount] * [Quantity]
        dataType: string
        lineageTag: 16f5b393-a841-47e7-9a27-003765c46e2e

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Sales_Data_Warehouse.tmdl`

```
table Sales Data Warehouse
    lineageTag: 8e28a9e9-7c37-46fb-82bf-a7fdffc4e7ab

    partition Sales Data Warehouse = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Sales_Data_Warehouse = Source{[Schema="dbo", Item="Sales_Data_Warehouse"]}[Data]
            in
                Sales_Data_Warehouse

    column OrderID
        dataType: string
        lineageTag: a2e2f97f-dc38-4bd4-9316-158de2067ab7
        sourceColumn: OrderID
        summarizeBy: none

    column OrderDate
        dataType: dateTime
        lineageTag: 07a95fff-5d19-47e2-b99c-189967c0bf4c
        sourceColumn: OrderDate
        summarizeBy: none

    column Year
        dataType: int64
        lineageTag: 63077e62-70bf-4d17-b481-c7e34f02c1e1
        formatString: 0
        sourceColumn: Year
        summarizeBy: none

    column Quarter
        dataType: string
        lineageTag: 9260ed15-5bfe-428f-8df4-91cf2e4810fe
        sourceColumn: Quarter
        summarizeBy: none

    column Month
        dataType: string
        lineageTag: f4a6b04c-590f-4f54-9876-ad29ed42704e
        sourceColumn: Month
        summarizeBy: none

    column CustomerName
        dataType: string
        lineageTag: c86f2832-ad5c-4378-b399-902045eecc1c
        sourceColumn: CustomerName
        summarizeBy: none

    column Segment
        dataType: string
        lineageTag: d67a7391-a61c-4195-86f4-b69924d7f613
        sourceColumn: Segment
        summarizeBy: none

    column Region
        dataType: string
        lineageTag: d841ce5f-c16f-40ba-bc58-0b6ca0830b1e
        sourceColumn: Region
        summarizeBy: none

    column Country
        dataType: string
        lineageTag: 1684cccc-6180-45fc-bab8-c87e9d39474f
        sourceColumn: Country
        summarizeBy: none

    column State
        dataType: string
        lineageTag: 6b4389a4-2059-47d6-ab10-08ebad69e13a
        sourceColumn: State
        summarizeBy: none

    column City
        dataType: string
        lineageTag: 0817e034-76f3-40dd-a8c5-4967917f08d0
        sourceColumn: City
        summarizeBy: none

    column Category
        dataType: string
        lineageTag: 4742f00c-bd30-41e6-8c10-473f59e4170f
        sourceColumn: Category
        summarizeBy: none

    column Subcategory
        dataType: string
        lineageTag: 41090be1-c5a4-4615-83c8-4593824cd4fd
        sourceColumn: Subcategory
        summarizeBy: none

    column Brand
        dataType: string
        lineageTag: f443b218-d543-48eb-a41b-01db5144b715
        sourceColumn: Brand
        summarizeBy: none

    column ProductName
        dataType: string
        lineageTag: 950bd6c9-6abf-48d8-a881-cc2928fcb588
        sourceColumn: ProductName
        summarizeBy: none

    column StoreName
        dataType: string
        lineageTag: 8d19d626-5e3d-43b2-87e9-21db2457e34f
        sourceColumn: StoreName
        summarizeBy: none

    column StoreType
        dataType: string
        lineageTag: 6f3dc4b3-f12c-4222-834d-5ac2c97eb677
        sourceColumn: StoreType
        summarizeBy: none

    column Quantity
        dataType: int64
        lineageTag: 464f58d6-cb6a-4b22-b780-29a6680fe225
        formatString: 0
        sourceColumn: Quantity
        summarizeBy: none

    column UnitPrice
        dataType: string
        lineageTag: 18749081-c3fb-417a-b539-8d25d2c98aa9
        sourceColumn: UnitPrice
        summarizeBy: none

    column UnitCost
        dataType: string
        lineageTag: 621ebf80-45a2-4824-b039-01312f1282bc
        sourceColumn: UnitCost
        summarizeBy: none

    column DiscountPct
        dataType: string
        lineageTag: 93c69651-2608-4fb6-8f62-c2979dcdd35d
        sourceColumn: DiscountPct
        summarizeBy: none

    column TaxAmount
        dataType: string
        lineageTag: cf3617a8-6e1e-48bd-8ba0-55163e14f4e7
        sourceColumn: TaxAmount
        summarizeBy: none

    column FreightCost
        dataType: string
        lineageTag: 41738ca4-fe6c-464e-8d18-a4548e0f8ffe
        sourceColumn: FreightCost
        summarizeBy: none

    column 'Revenue' = [Quantity] * [UnitPrice] * (1 - [DiscountPct])
        dataType: string
        lineageTag: 4eb778f3-d634-4cb1-b5df-ba425c634e95

    column 'TotalCost' = [Quantity] * [UnitCost] + [TaxAmount] + [FreightCost]
        dataType: string
        lineageTag: 54464a9a-be5c-4123-bd5e-c6d72c887a3b

    column 'Profit' = [Revenue] - [TotalCost]
        dataType: string
        lineageTag: 4ed2bca2-d5ab-41be-b3e8-4036b1111642

    column 'ProfitMargin' = IF [Revenue] > 0 THEN [Profit] / [Revenue] * 100 ELSE 0 END
        dataType: string
        lineageTag: 1a5d5b52-0cb7-4779-9e6e-5dbba2157ec2

    column 'DiscountAmount' = [Quantity] * [UnitPrice] * [DiscountPct]
        dataType: string
        lineageTag: 57aa627d-c845-4b7f-876c-0a55e98e53c3

    column 'PriceCategory' = IF [UnitPrice] > 500 THEN 'Premium' ELSEIF [UnitPrice] > 100 THEN 'Mid-Range' ELSE 'Budget' END
        dataType: string
        lineageTag: 411999ae-d4be-457c-9fb4-7564bea3bfe7

    column 'IsHighValue' = IF [Revenue] > 5000 THEN 'Yes' ELSE 'No' END
        dataType: string
        lineageTag: 576c97bd-bb21-415e-aff4-639463732f8d

    measure 'AvgOrderValue' = SUM('Sales Data Warehouse'[[Revenue]]) / COUNTD([OrderID])
        lineageTag: 16b6d7a0-55f4-4a77-a05c-828dadc2e993
        formatString: #,0.00
        displayFolder: Measures

    hierarchy Date
        level Year
            column: Year
        level Quarter
            column: Quarter
        level Month
            column: Month

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Scenario.tmdl`

```
table Scenario
    lineageTag: 3d019b76-dd5a-41ba-a89f-0ee1bff1e6c0

    partition Scenario = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Scenario = Source{[Schema="dbo", Item="Scenario"]}[Data]
            in
                Scenario

    column 'Variance' = Actual - Budget
        dataType: string
        lineageTag: a90226d7-a017-4dbc-ae21-b81b86afae2a

    column 'Variance Pct' = @ROUND((Actual - Budget) % Budget, 4)
        dataType: string
        lineageTag: 27ed59fc-6ed0-4ce8-8811-04ece5a76109

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

        /// @migration: broken-ref-auto-hidden
```

#### `definition/tables/Time.tmdl`

```
table Time
    lineageTag: d13fee29-04ee-463b-8c0c-6b88ec054ddb

    partition Time = m
        mode: import
        source
            let
                Source = 'Sql'[Database]("onelake-sql-endpoint", "MigrationLakehouse"),
                Time = Source{[Schema="dbo", Item="Time"]}[Data]
            in
                Time

    column 'Date' = "DIM_DATE"."FULL_DATE"
        dataType: string
        lineageTag: a04c26de-11f5-4e89-8301-408a4d87af66

    column 'Year' = "DIM_DATE"."YEAR"
        dataType: string
        lineageTag: 6f578d3b-a677-401c-9a70-f3c6e82a5abc

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

        /// @migration: broken-ref-auto-hidden
```

#### `model.tmdl`

```
model SemanticModel
    culture: en-US
    defaultPowerBIDataSourceVersion: powerBI_V3
    sourceQueryCulture: en-US
    lineageTag: 04f9fc0d-a05f-41fc-aaaa-d4cdbbaf438d
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
| Physical tables | 58 |
| Logical tables / dimensions | 50 |
| Analyses / worksheets | 19 |
| Dashboards | 6 |
| Security roles | 9 |
| Prompts / parameters | 19 |
| DDL statements generated | 58 |
| TMDL files generated | 40 |
| Expressions translated | 175 |
| Elapsed time | 0.3s |

---

*Report generated by OAC-to-Fabric Migration Accelerator*