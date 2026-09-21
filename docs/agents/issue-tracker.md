# Issue tracker: GitHub

Issues, specifications and planned engineering work for this repository live in GitHub Issues:

- Repository: `KratosLee-6/Html-ninefox`
- Default branch: `main`
- Issues: enabled
- Pull requests as a triage request surface: no

Use the `gh` CLI for issue operations while inside this repository.

## Common operations

Create an issue:

```bash
gh issue create --title "..." --body-file <file>
```

Read an issue and its comments:

```bash
gh issue view <number> --comments
```

List issues with their labels:

```bash
gh issue list \
  --state open \
  --json number,title,body,labels,comments \
  --jq '[.[] | {
    number,
    title,
    body,
    labels: [.labels[].name],
    comments: [.comments[].body]
  }]'
```

Comment on an issue:

```bash
gh issue comment <number> --body-file <file>
```

Add or remove labels:

```bash
gh issue edit <number> --add-label "<label>"
gh issue edit <number> --remove-label "<label>"
```

Close an issue:

```bash
gh issue close <number> --comment "..."
```

## Skill conventions

When an engineering skill says “publish to the issue tracker”, create a GitHub Issue in `KratosLee-6/Html-ninefox`.

When a skill says “fetch the relevant ticket”, read the corresponding issue, labels and comments.

A bare reference such as `#42` can identify an Issue or Pull Request because GitHub shares their number space. Check the Pull Request first and fall back to the Issue when the type is unclear.

## Pull requests

Pull requests are not part of the default triage queue. External Pull Requests should only enter the issue triage workflow when this file is explicitly changed to enable that behavior.

## Wayfinder operations

A Wayfinder map is represented by a GitHub Issue carrying the `wayfinder:map` label.

Child work is represented by linked sub-issues. If GitHub sub-issues are unavailable, use a task list in the map and add `Part of #<map>` to each child.

Use the following labels for child type:

- `wayfinder:research`
- `wayfinder:prototype`
- `wayfinder:grilling`
- `wayfinder:task`

Represent blocking relationships with GitHub native issue dependencies when available. Otherwise place `Blocked by: #<number>` at the beginning of the child issue.

A ticket is ready to claim only when it is open, unassigned and has no open blockers. Claim it by assigning the current GitHub user before starting implementation.

Resolve a ticket by recording the result, closing it and adding the relevant context pointer to the parent map.
