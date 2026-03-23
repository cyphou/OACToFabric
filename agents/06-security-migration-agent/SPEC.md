# Agent 06: Security & Governance Migration Agent — Technical Specification

## 1. Purpose

Migrate the OAC **security model** — including application roles, row-level security (RLS), and object-level permissions — to equivalent **Power BI RLS/OLS** and **Fabric workspace role** configurations.

## 2. Inputs

| Input | Source | Format |
|---|---|---|
| OAC application roles | Fabric Lakehouse `migration_inventory` | Delta table (from Agent 01) |
| OAC RLS definitions (session variables, init blocks) | Fabric Lakehouse `migration_inventory` | Delta table (from Agent 01) |
| OAC object-level permissions | Fabric Lakehouse `migration_inventory` | Delta table (from Agent 01) |
| Deployed semantic model | Fabric workspace | TMDL (from Agent 04) |
| Azure AD user/group mapping | IT/IAM team | CSV or Azure AD export |

## 3. Outputs

| Output | Destination | Format |
|---|---|---|
| Power BI RLS role definitions | TMDL `roles.tmdl` | TMDL |
| Power BI OLS definitions | TMDL table/column metadata | TMDL |
| Fabric workspace role assignments | Fabric workspace | API calls |
| RLS validation test plan | Fabric Lakehouse `validation_results` | Delta table |
| Security migration report | Git repo | Markdown |

## 4. Security Model Mapping

### 4.1 OAC Roles → Fabric/PBI Roles

| OAC Concept | Fabric/PBI Equivalent |
|---|---|
| **Application Role** (e.g., SalesManager) | Power BI RLS Role + Fabric Workspace Role |
| **User → Role assignment** | Azure AD Security Group → RLS Role membership |
| **Row-level filter** (session variable-based) | RLS DAX filter expression |
| **Object permission** (hide column/table) | OLS (Object-Level Security) `none` permission |
| **Data-level security** (init block populates variable) | RLS with `USERPRINCIPALNAME()` or lookup table |

### 4.2 OAC Session Variable → PBI RLS Pattern

| OAC Pattern | PBI RLS DAX Equivalent |
|---|---|
| `VALUEOF(NQ_SESSION.USER)` | `USERPRINCIPALNAME()` |
| `VALUEOF(NQ_SESSION.GROUP)` | Lookup table: `UserRoles[UserEmail] = USERPRINCIPALNAME()` |
| `VALUEOF(NQ_SESSION.REGION)` | Lookup table: `UserRegions[UserEmail] = USERPRINCIPALNAME()` |
| Init block: SQL populates session variable | Create security lookup table in Lakehouse |
| Multi-valued session variable | Lookup table with one-to-many mapping |

### 4.3 Security Lookup Table Pattern

When OAC uses session variables populated by init blocks (SQL queries), we create a **security lookup table** in Fabric:

```sql
-- Security lookup table (populated from OAC init block SQL)
CREATE TABLE Security_UserAccess (
    UserEmail       VARCHAR(256),   -- Maps to USERPRINCIPALNAME()
    Region          VARCHAR(100),   -- Row-level filter dimension
    Department      VARCHAR(100),   -- Another filter dimension
    AccessLevel     VARCHAR(50)     -- Optional: role-level granularity
);
```

### 4.4 RLS DAX Filter Generation

```tmdl
role 'Regional Sales'
    modelPermission: read
    
    tablePermission Sales
        filterExpression =
            VAR CurrentUser = USERPRINCIPALNAME()
            VAR UserRegions = 
                CALCULATETABLE(
                    VALUES(Security_UserAccess[Region]),
                    Security_UserAccess[UserEmail] = CurrentUser
                )
            RETURN
                Sales[Region] IN UserRegions
    
    tablePermission Inventory
        filterExpression =
            VAR CurrentUser = USERPRINCIPALNAME()
            VAR UserRegions = 
                CALCULATETABLE(
                    VALUES(Security_UserAccess[Region]),
                    Security_UserAccess[UserEmail] = CurrentUser
                )
            RETURN
                Inventory[Region] IN UserRegions
```

### 4.5 Object-Level Security (OLS)

| OAC Object Permission | PBI OLS Configuration |
|---|---|
| Column hidden for role | `columnPermission: none` on that column for the OLS role |
| Table hidden for role | `tablePermission: none` on that table for the OLS role |
| Measure hidden for role | Not natively supported — use perspective or conditional visibility |

```tmdl
role 'Finance Only'
    modelPermission: read
    
    tablePermission Sales
        filterExpression = TRUE()
        
        columnPermission Margin
            metadataPermission: none  -- OLS: hide Margin column
        
        columnPermission Cost
            metadataPermission: none  -- OLS: hide Cost column
```

## 5. Core Logic

### 5.1 Security Migration Flow

```
1. Load OAC security objects from Lakehouse
2. Analyze init blocks to understand session variable population
3. For each init block SQL:
   3.1 Convert Oracle SQL → Fabric SQL
   3.2 Create security lookup table in Lakehouse
   3.3 Populate with current data
4. For each OAC application role:
   4.1 Create PBI RLS role definition (DAX)
   4.2 Map session variable references → USERPRINCIPALNAME() + lookup
   4.3 Generate TMDL role entries
5. For each object-level permission:
   5.1 Create OLS definitions in TMDL
6. Map OAC user → role assignments to Azure AD groups
   6.1 Generate group-to-role assignment script
7. Deploy security definitions to semantic model
8. Generate validation test plan
```

### 5.2 Fabric Workspace Role Mapping

| OAC Permission Level | Fabric Workspace Role |
|---|---|
| Admin | Admin |
| Content creator / developer | Contributor |
| Report viewer (with some edit) | Member |
| Report viewer (read-only) | Viewer |

## 6. Security Validation Matrix

For each role, the Validation Agent (07) will test:

| Test | Expected Result |
|---|---|
| Login as User A (Region=East) | See only East data in Sales report |
| Login as User B (Region=West) | See only West data in Sales report |
| Login as Admin | See all data |
| DAX query with RLS context | Returns filtered results matching OAC |
| OLS column visibility | Hidden columns not visible in field list |
| Cross-report security | RLS applies consistently across all reports |

## 7. Error Handling

| Error | Handling |
|---|---|
| Complex init block SQL (dynamic SQL, PL/SQL) | Flag for manual review; provide template |
| Session variable with no clear AAD equivalent | Create custom security table, document mapping |
| M:N role-to-permission mapping | Create composite RLS roles |
| OLS not supported for measures | Document limitation, suggest alternative (perspective) |

## 8. Testing Strategy

| Test Type | Approach |
|---|---|
| Unit | RLS DAX expression generation for each pattern |
| Integration | Deploy RLS to dev workspace, test with multiple users |
| Security | Negative testing — verify restricted data is inaccessible |
| Comparison | Same query, same user on OAC vs PBI, compare row counts |
