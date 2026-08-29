# Roadmap · 路线图

> Where Html九尾狐 is going — and how you can shape the path.

---

## 🎯 North Star (北极星)

> **By 2027-Q4, Html九尾狐 is the de-facto open-source HTML creation studio with 10k+ GitHub stars, 100+ community-contributed skills, and 1M+ HTML artifacts generated.**

---

## 📅 Version Timeline (版本时间线)

```
2026 Q3          Q4            2027 Q1         Q2            Q3         Q4
  │              │              │              │              │          │
  ▼              ▼              ▼              ▼              ▼          ▼
┌──────┐     ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐   ┌──────┐
│ v0.2 │ ──► │ v0.3 │ ───► │ v0.4 │ ───► │ v1.0 │ ───► │ v1.5 │──►│ v2.0 │
│ ✅   │     │ 🔜   │      │      │      │      │      │      │   │      │
└──────┘     └──────┘      └──────┘      └──────┘      └──────┘   └──────┘
5 agents     Real LLM       B2B SaaS      Public         Community  Enterprise
3 sinks      Web UI         Feishu        Marketplace    Plugins    On-prem
```

---

## 🔜 v0.3 — Real LLM + Web UI (Month 1 · ~Sep 2026)

> **Theme: Make the existing 5 agents production-grade**

### Scope

- [ ] **Real LLM integration** — OpenAI / Claude / Gemini / DeepSeek (configurable via `~/.fox/config.yaml`)
- [ ] **Web UI workbench** — browser-based Brief editor + live preview
- [ ] **3 new templates** — terminal, glassmorphism, bauhaus
- [ ] **Async pipeline** — run [3] asset fetch in parallel with [2] style pick
- [ ] **Result caching** — same Brief hash → instant replay
- [ ] **GitHub Actions CI** — auto-test on every PR (lint, types, integration, security)
- [ ] **Discord community channel**

### Out of Scope

- No paid tier yet (all free + MIT)
- No SaaS dashboard (workbench is local-only)
- No mobile app (web-responsive only)

### Success Metric

- 500 GitHub stars by end of v0.3
- 10 community-contributed alliance skills

---

## 🏢 v0.4 — B2B SaaS Tier (Month 3 · ~Nov 2026)

> **Theme: First revenue, first enterprise pilots**

### Scope

- [ ] **B2B SaaS tier** — paid subscription with team workspaces, audit log, role-based access
- [ ] **Feishu integration** — generate HTML from Feishu doc, push to Feishu wiki
- [ ] **Deploy agent (tail #6)** — auto-deploy to Vercel / Netlify / Cloudflare Pages
- [ ] **Analytics agent (tail #7)** — track HTML opens, time-on-page, conversion
- [ ] **Brand kit** — upload logo, color palette, fonts → all templates respect it

### Out of Scope

- No mobile app
- No AI auto-training (still uses OpenAI / Claude APIs)
- No template marketplace yet

### Success Metric

- 5 paying B2B customers (each $200/mo+)
- 2000 GitHub stars
- 50 community-contributed skills

---

## 🌐 v1.0 — Public Release + Template Marketplace (Month 6 · ~Feb 2027)

> **Theme: This is the LTS-grade release.**

### Scope

- [ ] **Template marketplace** — community submits, votes, downloads templates
- [ ] **A/B test agent (tail #8)** — generate 2 variants, serve, pick winner
- [ ] **Stable API** — `fox.server` HTTP API with OpenAPI spec
- [ ] **Plugin SDK** — write custom agents in any language (not just Python)
- [ ] **Internationalization** — UI + docs in EN / ZH / JA
- [ ] **Performance** — full Brief → HTML in < 10 seconds (P95)

### Out of Scope

- No AI model fine-tuning (still API-based)
- No content moderation tools (out of scope)

### Success Metric

- 10k GitHub stars ⭐
- 100+ marketplace templates
- 50 paying B2B customers
- First 100 SAU (self-hosted active users)

---

## 💼 v1.5 — Community Plugins + Skill Ecosystem (Month 9 · ~May 2027)

> **Theme: Make the alliance truly federated**

### Scope

- [ ] **Federated skill registry** — public/private skill servers
- [ ] **Skill version manager** — semantic versioning, dependency resolution
- [ ] **Skill marketplace revenue share** — community gets 70% of paid skill sales
- [ ] **CLI for skill authors** — `fox skill init`, `fox skill publish`, `fox skill test`
- [ ] **Monetize agent (tail #9)** — auto-insert affiliate links, sponsored sections

### Success Metric

- 500 published skills
- 100 paid skills
- 25k GitHub stars

---

## 🏛️ v2.0 — Enterprise + On-Prem (Month 12 · ~Aug 2027)

> **Theme: Enterprises can self-host with full data sovereignty**

### Scope

- [ ] **On-prem deployment** — Docker Compose + Helm chart
- [ ] **Air-gapped mode** — no external API calls, uses local models
- [ ] **SSO + RBAC** — SAML, OIDC, SCIM
- [ ] **Audit log** — full activity log for compliance
- [ ] **SOC 2 Type II** — for enterprise sales
- [ ] **Dedicated support tier** — $5k/mo+ contracts

### Success Metric

- 5 enterprise on-prem customers ($50k+ ACV each)
- 50k GitHub stars
- Profitable as a company

---

## 🤝 How to Influence the Roadmap (怎么影响路线图)

| Want to push for... | How |
|---------------------|-----|
| A new template style | File an issue with `template-request` label + 2 reference designs |
| A new agent (tail #10+) | Open a discussion in GitHub Discussions > Ideas |
| A new alliance skill | See [CONTRIBUTING.md](../CONTRIBUTING.md) for skill manifest format |
| A breaking change | Major versions only — we follow semver strictly |
| Bug fix priority | File an issue with `bug` + `priority:high` labels |

---

## 🚫 What We Won't Build (不会做)

- ❌ A Figma competitor — Figma is great at what it does
- ❌ A no-code visual editor — use Webflow / Framer
- ❌ A CMS — use Ghost / Strapi / Sanity
- ❌ A mobile app — web-responsive is enough
- ❌ Fine-tuned in-house LLMs — too expensive vs. API quality

---

<p align="center"><sub>🦊 The 9 tails grow one run at a time · Roadmap last updated 2026-08-29</sub></p>
