# Domain documentation

Html九尾狐 uses a single-context domain documentation layout.

## Read before exploring or changing behavior

1. Read the root `CONTEXT.md`.
2. Read relevant decisions under `docs/adr/`.
3. Use the canonical terms from `CONTEXT.md` in issue titles, specifications, tests, code and documentation.
4. If a proposed change contradicts an ADR, state the conflict explicitly instead of silently overriding the decision.

Missing ADR files are not an error. Create an ADR only when a decision is difficult to reverse, has a real trade-off and would appear surprising without its context.

## Layout

```text
/
├── AGENTS.md
├── CONTEXT.md
└── docs/
    ├── agents/
    │   ├── issue-tracker.md
    │   ├── triage-labels.md
    │   └── domain.md
    └── adr/
```

`CONTEXT.md` contains domain vocabulary only. It must not become an implementation guide, task list or temporary project note.

`docs/adr/` contains accepted architectural decisions. Use numbered names such as:

- `0001-project-commit-journal.md`
- `0002-application-use-case-interface.md`

Do not create a root `CONTEXT-MAP.md` unless the repository later becomes a genuine multi-context monorepo.

## Canonical vocabulary

Current domain terms include:

- Project
- Workspace
- Canvas Node
- Generation Request
- Artifact
- Revision
- Restore
- Feedback Iteration
- Export
- Recipe Run
- Project Memory
- Adoption Signal
- Memory Recommendation
- Explicit Requirement

The definitions and prohibited synonym usage live in `CONTEXT.md`. Update that file immediately when domain modeling resolves a new term or a conflict between existing terms.
