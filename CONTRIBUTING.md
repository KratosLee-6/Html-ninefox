# Contributing to Html九尾狐 / Fox-of-Nine-Tails HTML Studio

🦊 **Thanks for your interest in making Html九尾狐 better!** Whether you're fixing a typo, adding a new agent, or proposing a new template style — every contribution matters.

This guide is intentionally short. Read it once, then jump in.

---

## 🐛 1. File an Issue (提 Issue)

Before writing code, check if a related issue already exists. If not, file one with:

- **Clear title**: e.g. "asset agent fails on SVG URLs"
- **Repro steps**: exact command + Brief input that triggers the bug
- **Expected vs actual**: what you expected, what you got
- **Environment**: OS, Python version, LLM provider (if relevant)

Bug templates live at `.github/ISSUE_TEMPLATE/` (after we add them in v0.3).

For **feature requests**, use the `enhancement` label and describe:
- What problem does this solve?
- Who benefits? (designers? devs? PMs?)
- Rough sketch of the API/UX

---

## 🍴 2. Fork & Pull Request (Fork PR)

Workflow:

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/html-nine-tails.git
cd html-nine-tails

# 2. Create a feature branch
git checkout -b feat/awesome-template

# 3. Make changes, commit
git add .
git commit -m "feat: add brutalist-portfolio template"

# 4. Push and open a PR
git push origin feat/awesome-template
gh pr create --fill
```

PR title convention (Conventional Commits):

- `feat: ...` — new feature
- `fix: ...` — bug fix
- `docs: ...` — docs only
- `test: ...` — tests only
- `refactor: ...` — code change that neither fixes a bug nor adds a feature
- `chore: ...` — tooling, deps

---

## 📐 3. Code Style (代码规范)

- **Python**: PEP8 + type hints (`mypy` strict mode)
- **Line length**: 100 chars max
- **Naming**: snake_case for functions/vars, PascalCase for classes
- **Docstrings**: Google style for public APIs
- **Commits**: Conventional Commits (see above)

Run before committing:

```bash
ruff check fox/ tests/         # linting
black fox/ tests/              # formatting
mypy fox/                      # type check
```

---

## ✅ 4. Testing (测试要求)

Every PR **must include tests**:

- **New feature** → add at least 1 integration test under `tests/integration/`
- **Bug fix** → add a regression test that fails before your fix
- **Security-sensitive change** → add a test under `tests/security/`

Run all tests:

```bash
pytest tests/ -v
pytest tests/integration/ -v    # must pass 4/4
pytest tests/security/ -v       # must pass 12/12
```

CI will reject PRs that break existing tests.

---

## 🌍 5. Community (社区)

- **GitHub Discussions** — Q&A, show & tell, ideas
- **GitHub Issues** — bugs, feature requests
- **Discord** — coming in v0.3
- **Email** — kratoslee@users.noreply.github.com

### Code of Conduct (行为准则)

Be kind. Be patient. We assume good faith. No harassment, no spam, no AI-generated essays pretending to be human replies.

---

## 📚 Reference Docs (引用)

When contributing, please review:

- **[docs/DESIGN.md](docs/DESIGN.md)** — design philosophy + Brief schema
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — 5-agent contracts + alliance router protocol
- **[CHANGELOG.md](CHANGELOG.md)** — what shipped in each version

---

<p align="center">
  <sub>🦊 Built by KratosLee · MIT licensed · Welcome contributors of all backgrounds</sub>
</p>
