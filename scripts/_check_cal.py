"""Check Calendar M query replacement."""
min_expr = "'Time'[Date]"
max_expr = min_expr
q = '''let
    StartDate = Date.StartOfYear(List.Min({{min_date_expr}})),
    EndDate = Date.EndOfYear(List.Max({{max_date_expr}}))
in
    Result'''
q = q.replace('{{min_date_expr}}', min_expr)
q = q.replace('{{max_date_expr}}', max_expr)
print(q)
