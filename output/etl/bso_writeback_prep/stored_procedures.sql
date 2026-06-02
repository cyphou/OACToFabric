CREATE OR ALTER PROCEDURE dbo.usp_WriteBudget
    @Period INT,
    @Entity NVARCHAR(100),
    @Product NVARCHAR(100),
    @Scenario NVARCHAR(100),
    @Currency NVARCHAR(100),
    @Revenue DECIMAL(18,2)
AS
BEGIN
    SET NOCOUNT ON;

    -- Capture old value for audit
    DECLARE @OldAmount DECIMAL(18,2);
    SELECT @OldAmount = [Revenue]
    FROM dbo.Budget_Input
    WHERE [Period] = @Period AND [Entity] = @Entity AND [Product] = @Product AND [Scenario] = @Scenario AND [Currency] = @Currency;

    MERGE dbo.Budget_Input AS target
    USING (SELECT @Period, @Entity, @Product, @Scenario, @Currency, @Revenue)
          AS source ([Period], [Entity], [Product], [Scenario], [Currency], [Revenue])
    ON target.[Period] = source.[Period] AND target.[Entity] = source.[Entity] AND target.[Product] = source.[Product] AND target.[Scenario] = source.[Scenario] AND target.[Currency] = source.[Currency]
    WHEN MATCHED THEN
        UPDATE SET [Revenue] = source.[Revenue],
                   [ModifiedBy] = CURRENT_USER,
                   [ModifiedAt] = SYSUTCDATETIME()
    WHEN NOT MATCHED THEN
        INSERT ([Period], [Entity], [Product], [Scenario], [Currency], [Revenue])
        VALUES (@Period, @Entity, @Product, @Scenario, @Currency, @Revenue);

    -- Write audit trail
    INSERT INTO dbo.Budget_Audit
        ([Period], [Entity], [Product], [Scenario], [Currency], [OldAmount], [NewAmount], [ChangedBy])
    VALUES (@Period, @Entity, @Product, @Scenario, @Currency, @OldAmount, @Revenue, CURRENT_USER);
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_ValidateBudget
    @Scenario NVARCHAR(20) = 'Budget'
AS
BEGIN
    SET NOCOUNT ON;

    -- Check for missing required intersections
    SELECT 'Missing' AS CheckType, COUNT(*) AS IssueCount
    FROM dbo.Budget_Input
    WHERE [Revenue] IS NULL AND [Scenario] = @Scenario;

    -- Check for negative values in revenue accounts
    SELECT 'NegativeRevenue' AS CheckType, COUNT(*) AS IssueCount
    FROM dbo.Budget_Input
    WHERE [Revenue] < 0 AND [Scenario] = @Scenario;

    -- Summary totals per scenario
    SELECT [Scenario], COUNT(*) AS RowCount, SUM([Revenue]) AS Total
    FROM dbo.Budget_Input
    GROUP BY [Scenario];
END;
GO