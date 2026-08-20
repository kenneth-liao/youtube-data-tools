# Domain Docs

How the engineering skills should consume this repository's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repository root.
- **`docs/adr/`** — read ADRs that touch the area you are about to work in.

If relevant ADRs do not exist, proceed silently. Create ADRs lazily only when a decision needs a durable record.

## File structure

This is a single-context repository:

```text
/
├── CONTEXT.md
├── docs/
│   └── adr/
└── yt_tools/
```

## Use the glossary's vocabulary

When output names a domain concept—in an issue title, proposal, test name, or code interface—use the term defined in `CONTEXT.md`. Do not drift to synonyms that the glossary explicitly avoids.

If a required concept is absent, reconsider whether new language is necessary or note the gap for domain-modeling work.

## Flag ADR conflicts

Surface any conflict with an accepted ADR instead of silently overriding it.
