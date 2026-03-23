# OAC API Notes — Known Behaviors & Workarounds

This document captures Oracle Analytics Cloud REST API quirks, undocumented
behaviors, and workarounds discovered during migration development.

## Authentication (IDCS OAuth2)

### Token Endpoint
- OAC uses Oracle IDCS (Identity Cloud Service) for OAuth2.
- Token URL format: `https://<idcs-domain>/oauth2/v1/token`
- Grant type: `client_credentials`
- Scope: `urn:opc:idm:__myscopes__` (required for full catalog access).
- Tokens expire in 3600s by default. Always check `expires_in` field.

### Known Issues
1. **401 after token refresh**: Occasionally, a freshly obtained token returns
   401 on the first request. **Workaround**: Retry with a 1s delay and re-auth.
2. **Rate limiting on token endpoint**: IDCS may throttle token requests if
   called too frequently. Cache tokens (see `OACAuth.get_token()`).

## Catalog API

### Endpoint
- Base: `GET /api/{version}/catalog`
- Folder listing: `?path=/shared/folder`
- Asset details: `?path=/shared/folder/analysis`

### Pagination
- Default page size: 25 items.
- Max page size: 100 (server-enforced; larger values are silently capped).
- Pagination uses `offset` parameter (0-based).
- When `offset + limit >= totalResults`, no more pages.

### Known Issues
1. **Empty folders return 200 with empty items**: Not a 404.
2. **Hidden system folders**: `/shared/system` and `/shared/_portal` contain
   internal assets that should be excluded from inventory.
3. **Stale metadata**: `lastModified` timestamps may lag actual changes by
   minutes (eventual consistency in OAC metadata cache).
4. **Path encoding**: Folder names with spaces must be URL-encoded, but
   forward slashes in paths must NOT be encoded.
5. **Case sensitivity**: OAC catalog paths are case-insensitive on lookup
   but preserve original case on return.

## Subject Areas

### Endpoint
- `GET /api/{version}/subjectareas`
- Individual: `GET /api/{version}/subjectareas/{name}`

### Known Issues
1. **Subject area names with special characters**: Names containing `/`, `.`,
   or `#` cause lookup failures. **Workaround**: Use catalog path instead.
2. **Column ordering**: Subject area columns are returned in alphabetical
   order, not presentation order. Presentation order must be extracted from
   RPD XML.

## Data Flows

### Endpoint
- List: `GET /api/{version}/dataflows`
- Individual: `GET /api/{version}/dataflows/{id}`

### Known Issues
1. **Step parameter references**: Data flow steps may reference parameters
   by internal ID rather than name. Cross-reference with parameter definitions.
2. **Schedule metadata**: The `schedule` field is only populated for flows
   that have been scheduled at least once. Flows executed only manually
   have `schedule: null`.
3. **Execution history truncation**: `GET /dataflows/{id}/executions` caps at
   100 entries regardless of `limit` parameter.

## RPD XML Export (XUDML)

### Export Format
- RPD exports use Oracle's XUDML (XML Unified Description Markup Language).
- The XML may be wrapped in a `.rpd` binary container — extract first.
- Encoding: UTF-8 with possible BOM.
- Namespace: XUDML elements use no namespace prefix by default.

### Element Hierarchy
```
Repository
  ├── PhysicalLayer
  │     └── Database → Schema → PhysicalTable → PhysicalColumn
  ├── BusinessModel (LogicalLayer)
  │     └── LogicalTableSource → LogicalColumn
  ├── PresentationLayer
  │     └── PresentationCatalog → PresentationTable → PresentationColumn
  └── SecurityLayer
        └── Group → ApplicationRole → RowLevelSecurityFilter
```

### Known Issues
1. **Missing elements**: Some RPD exports omit `<Alias>` elements for
   presentation columns. **Workaround**: Fall back to column name.
2. **Circular references**: Logical table sources may reference each other
   in complex star schemas. The dependency graph builder handles cycles by
   tracking visited nodes.
3. **Large RPDs (>100MB)**: Full DOM parsing (`lxml.etree.parse`) may exhaust
   memory on 32-bit systems. Use `StreamingRPDParser` for files >50MB.
4. **Encoded expressions**: Calculation expressions in RPD use `&amp;`, `&lt;`,
   `&gt;` HTML entities. The parser decodes these automatically.
5. **Multi-language RPDs**: Columns may have locale-specific aliases under
   `<Description>` elements with `lang` attributes. Only the default (first)
   locale is extracted.
6. **Connection pool references**: RPD `<ConnectionPool>` elements reference
   physical database connections by `mdsid` (internal UUID). Map these to
   `oracle_connection_name` during schema migration.

## General Recommendations

1. **Always paginate**: Never assume catalog results fit in a single response.
2. **Retry on 429 and 503**: OAC will throttle during heavy load. Implement
   exponential backoff (see `tenacity` retry decorators).
3. **Validate before migration**: Run discovery in read-only mode first to
   identify unsupported constructs before committing to a full migration.
4. **Timestamp handling**: OAC uses ISO 8601 timestamps in UTC. Always convert
   to `datetime.now(timezone.utc)` for internal consistency.
5. **Security scope**: OAC API calls respect the authenticated user's permissions.
   Ensure the migration service account has full admin access to see all assets.
