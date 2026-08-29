# Design Philosophy · 设计哲学

> 🦊 Personal project by [@KratosLee-6](https://github.com/KratosLee-6) · MIT licensed.

Why Html九尾狐 exists, what problem it solves, and the methodology behind it.

---

## 🎯 The Problem (问题)

Most HTML generation tools fall into two camps:

1. **Pure AI generators** (V0, Lovable, Bolt) — fast but opaque. You get HTML but no understanding, no reusability, no沉淀 (accumulation).
2. **Pure template engines** (Jinja2, Hugo) — predictable but rigid. You get consistency but no intelligence, no adaptation.

Neither solves the real problem for **HTML creators** (designers, devs, marketers):

> "I want to produce great HTML **faster**, and I want every project to make the next one **easier**."

Html九尾狐 sits in the middle: **structured input + AI agents + accumulated knowledge**.

---

## 🦊 The 飞书绝活方法论 (Feishue Juehuo Methodology)

The core methodology is **三件套 (three-pillar trio)**:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   📋 BRIEF          🎨 模板             🔁 反馈          │
│   (input)           (templates)         (feedback)      │
│                                                         │
│   "What to build"   "How it looks"      "What to fix"   │
│                                                         │
└─────────────────────────────────────────────────────────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  🦊 Html九尾狐      │
                    │  (orchestrator)     │
                    └─────────────────────┘
```

### 1. 📋 Brief (简报) — Structured Input

A Brief is **not** a prompt. It's a **contract**:

- Audience (target users)
- Goal (what success looks like)
- Style hint (Swiss / Brutalist / Editorial / Playful / Corporate)
- Asset list (images / icons / fonts needed)
- Constraints (max file size, accessibility, browser support)

See `fox/agents/brief.py` for the parser. BriefSpec schema is in `docs/SCHEMAS.md` (v0.3).

### 2. 🎨 模板 (Templates) — Style as Data

Templates are **Jinja2 files with metadata**, not just HTML:

```yaml
# template_lib/manifests/swiss.yaml
id: swiss
display_name: Swiss Design
grid: 12-column
typography: helvetica, akzidenz
colors: [black, white, red]
best_for: [landing, dashboard, report]
```

This lets the **style agent** pick the right template automatically based on Brief signal.

### 3. 🔁 反馈 (Feedback) — Looped Improvement

Every run produces a `feedback.json`:

```json
{
  "score": 0.87,
  "issues": ["contrast AAA fail in hero CTA"],
  "suggestions": ["darken button bg from #2563eb to #1e40af"],
  "next_iteration": true
}
```

This feedback is **stored** in `feedback_lib/` and **retrieved** by future runs to avoid repeating mistakes.

---

## 🦊 Html九尾狐's Role: Main Orchestrator (主编排器)

There are 9 tails in the full vision. v0.2 ships 5:

```
┌──────────────────────────────────────────────────────────┐
│  THE 9 TAILS (愿景)                                       │
│  ─────────────────────────────────────────────────────   │
│  1. brief agent          ✅ v0.2                         │
│  2. style agent          ✅ v0.2                         │
│  3. asset agent          ✅ v0.2                         │
│  4. generate agent       ✅ v0.2                         │
│  5. feedback agent       ✅ v0.2                         │
│  6. deploy agent         🔜 v0.3                         │
│  7. analytics agent      🔜 v0.4                         │
│  8. A/B test agent       🔜 v0.4                         │
│  9. monetize agent       🔜 v1.0                         │
└──────────────────────────────────────────────────────────┘
```

Html九尾狐 is the **orchestrator** — it doesn't try to be the best at any single tail. Instead, it:

- Defines **contracts** (what each agent must accept / produce)
- Provides **3 sinks** (brief_lib, template_lib, feedback_lib) for knowledge accumulation
- Runs the **alliance router** so community-contributed agents plug in cleanly

This is the difference between Html九尾狐 and a single-purpose tool:

> **Html九尾狐 is a Skill Alliance. The main tool is just the orchestrator.**

---

## ⚖️ vs Other Tools (对比)

| Tool | Strength | Weakness | Html九尾狐's edge |
|------|----------|----------|-------------------|
| **V0 / Lovable** | Fast HTML generation | No reuse, no knowledge沉淀 | Brief + feedback loop makes every run smarter |
| **shadcn / Tailwind UI** | Beautiful, copy-paste | Manual selection, no AI | Auto-pick template from Brief signal |
| **Jinja2 / Hugo** | Predictable, fast | Rigid, no intelligence | LLM fills gaps in structure |
| **Figma-to-code** | Designer-friendly | One-shot, no iteration | Feedback loop = continuous improvement |
| **Webflow / Framer** | Visual editor | Lock-in, expensive | Open-source, MIT, your own output |

---

## 👥 The 5 Agents' Responsibilities (智能体职责)

| Agent | Input | Output | Failure mode |
|-------|-------|--------|--------------|
| **brief** | Free text + hints | `BriefSpec` JSON | Falls back to "minimal viable brief" with warning |
| **style** | `BriefSpec` | `StyleProfile` + template ref | Defaults to `swiss` if no signal |
| **asset** | `BriefSpec` | Downloaded assets in `output/assets/` | Falls back to placeholders + flags missing |
| **generate** | All above | Rendered HTML | Logs template render errors, never crashes |
| **feedback** | Generated HTML | `feedback.json` with score | Score=0.5 if LLM unavailable |

---

## 🧠 The 三重沉淀 (Triple Sinks) Design

Every run writes to 3 sinks. Every future run reads from them:

```
[Run #1: Landing page for SaaS X]
   brief  → brief_lib  (saved)
   style  → template_lib (saved new style usage stat)
   feedback → feedback_lib (saved issues)

[Run #47: Another landing page]
   brief agent reads brief_lib      → "I've seen 5 SaaS landings, here's what worked"
   style agent reads template_lib   → "swiss was picked 12 times, editorial 3 times"
   generate agent reads feedback_lib → "Avoid low-contrast CTAs (12 past failures)"
   feedback agent writes new score  → feedback_lib (updated)
```

The system gets **smarter over time** without retraining.

---

## 🚫 What Html九尾狐 is NOT

- ❌ Not a Figma replacement (use Figma for design)
- ❌ Not a no-code website builder (use Webflow for that)
- ❌ Not an AI chatbot (it's a structured pipeline)
- ❌ Not a CMS (use Ghost / Strapi for content)

Html九尾狐 **is**:
- ✅ A **structured pipeline** for HTML creation
- ✅ A **knowledge accumulator** via 3 sinks
- ✅ A **Skill Alliance** where community agents plug in
- ✅ **Open-source** under MIT — your output, your code

---

<p align="center"><sub>🦊 The 9 tails grow one run at a time.</sub></p>
