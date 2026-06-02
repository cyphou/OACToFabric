-- ============================================
-- Dimension tables for: longview_budget_writeback
-- Source: Essbase outline dimensions
-- Phase A: Longview backend migration
-- ============================================

IF OBJECT_ID('dbo.Dim_Period', 'U') IS NULL
CREATE TABLE dbo.Dim_Period (
    [PeriodKey] INT IDENTITY(1,1),
    [Period] NVARCHAR(100) NOT NULL,
    [ParentMember] NVARCHAR(100),
    [Level] INT DEFAULT 0,
    [IsLeaf] BIT DEFAULT 1,
    [SortOrder] INT DEFAULT 0,
    CONSTRAINT PK_Dim_Period PRIMARY KEY NONCLUSTERED ([PeriodKey]) NOT ENFORCED
);

-- Seed members for Period
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'FY2026', NULL, 0, 1, 0);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Q1', NULL, 0, 1, 1);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Jan', NULL, 0, 1, 2);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Feb', NULL, 0, 1, 3);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Mar', NULL, 0, 1, 4);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Q2', NULL, 0, 1, 5);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Apr', NULL, 0, 1, 6);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'May', NULL, 0, 1, 7);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Jun', NULL, 0, 1, 8);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Q3', NULL, 0, 1, 9);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Jul', NULL, 0, 1, 10);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Aug', NULL, 0, 1, 11);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Sep', NULL, 0, 1, 12);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Q4', NULL, 0, 1, 13);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Oct', NULL, 0, 1, 14);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Nov', NULL, 0, 1, 15);
INSERT INTO dbo.Dim_Period ([Period], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Dec', NULL, 0, 1, 16);

IF OBJECT_ID('dbo.Dim_Entity', 'U') IS NULL
CREATE TABLE dbo.Dim_Entity (
    [EntityKey] INT IDENTITY(1,1),
    [Entity] NVARCHAR(100) NOT NULL,
    [ParentMember] NVARCHAR(100),
    [Level] INT DEFAULT 0,
    [IsLeaf] BIT DEFAULT 1,
    [SortOrder] INT DEFAULT 0,
    CONSTRAINT PK_Dim_Entity PRIMARY KEY NONCLUSTERED ([EntityKey]) NOT ENFORCED
);

-- Seed members for Entity
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Corporate', NULL, 0, 1, 0);
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'North_America', NULL, 0, 1, 1);
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'USA_East', NULL, 0, 1, 2);
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'USA_West', NULL, 0, 1, 3);
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Canada', NULL, 0, 1, 4);
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'EMEA', NULL, 0, 1, 5);
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'UK', NULL, 0, 1, 6);
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'France', NULL, 0, 1, 7);
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Germany', NULL, 0, 1, 8);
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'APAC', NULL, 0, 1, 9);
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Japan', NULL, 0, 1, 10);
INSERT INTO dbo.Dim_Entity ([Entity], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Australia', NULL, 0, 1, 11);

IF OBJECT_ID('dbo.Dim_Product', 'U') IS NULL
CREATE TABLE dbo.Dim_Product (
    [ProductKey] INT IDENTITY(1,1),
    [Product] NVARCHAR(100) NOT NULL,
    [ParentMember] NVARCHAR(100),
    [Level] INT DEFAULT 0,
    [IsLeaf] BIT DEFAULT 1,
    [SortOrder] INT DEFAULT 0,
    CONSTRAINT PK_Dim_Product PRIMARY KEY NONCLUSTERED ([ProductKey]) NOT ENFORCED
);

-- Seed members for Product
INSERT INTO dbo.Dim_Product ([Product], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'All_Products', NULL, 0, 1, 0);
INSERT INTO dbo.Dim_Product ([Product], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Software', NULL, 0, 1, 1);
INSERT INTO dbo.Dim_Product ([Product], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Licenses', NULL, 0, 1, 2);
INSERT INTO dbo.Dim_Product ([Product], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Subscriptions', NULL, 0, 1, 3);
INSERT INTO dbo.Dim_Product ([Product], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Services', NULL, 0, 1, 4);
INSERT INTO dbo.Dim_Product ([Product], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Consulting', NULL, 0, 1, 5);
INSERT INTO dbo.Dim_Product ([Product], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Training', NULL, 0, 1, 6);

IF OBJECT_ID('dbo.Dim_Scenario', 'U') IS NULL
CREATE TABLE dbo.Dim_Scenario (
    [ScenarioKey] INT IDENTITY(1,1),
    [Scenario] NVARCHAR(100) NOT NULL,
    [ParentMember] NVARCHAR(100),
    [Level] INT DEFAULT 0,
    [IsLeaf] BIT DEFAULT 1,
    [SortOrder] INT DEFAULT 0,
    CONSTRAINT PK_Dim_Scenario PRIMARY KEY NONCLUSTERED ([ScenarioKey]) NOT ENFORCED
);

-- Seed members for Scenario
INSERT INTO dbo.Dim_Scenario ([Scenario], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Budget', NULL, 0, 1, 0);
INSERT INTO dbo.Dim_Scenario ([Scenario], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Forecast', NULL, 0, 1, 1);
INSERT INTO dbo.Dim_Scenario ([Scenario], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'Actual', NULL, 0, 1, 2);

IF OBJECT_ID('dbo.Dim_Currency', 'U') IS NULL
CREATE TABLE dbo.Dim_Currency (
    [CurrencyKey] INT IDENTITY(1,1),
    [Currency] NVARCHAR(100) NOT NULL,
    [ParentMember] NVARCHAR(100),
    [Level] INT DEFAULT 0,
    [IsLeaf] BIT DEFAULT 1,
    [SortOrder] INT DEFAULT 0,
    CONSTRAINT PK_Dim_Currency PRIMARY KEY NONCLUSTERED ([CurrencyKey]) NOT ENFORCED
);

-- Seed members for Currency
INSERT INTO dbo.Dim_Currency ([Currency], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'USD', NULL, 0, 1, 0);
INSERT INTO dbo.Dim_Currency ([Currency], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'EUR', NULL, 0, 1, 1);
INSERT INTO dbo.Dim_Currency ([Currency], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'GBP', NULL, 0, 1, 2);
INSERT INTO dbo.Dim_Currency ([Currency], [ParentMember], [Level], [IsLeaf], [SortOrder]) VALUES (N'JPY', NULL, 0, 1, 3);
