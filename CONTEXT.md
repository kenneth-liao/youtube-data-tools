# YouTube Data Tools

This context covers command-line access to public YouTube data and authorized private channel analytics.

## Language

**Authorized channel**:
A YouTube channel owned by, or explicitly granting access to, the user who completes authorization.
_Avoid_: Target channel, private channel

**Analytics query**:
A user-defined, synchronous retrieval of authorized channel analytics expressed as metrics, dimensions, filters, and a date range.
_Avoid_: Custom report, raw report

**Analytics snapshot**:
A predefined performance view containing period totals, daily trends, and comparison with the preceding equal-length period.
_Avoid_: Performance report, analytics query

**Reporting job**:
A YouTube-managed asynchronous request that produces downloadable daily reporting files.
_Avoid_: Analytics query, background query

**Reach report**:
A reporting file containing video thumbnail impressions and thumbnail impression click-through rate.
_Avoid_: Ad impressions report
