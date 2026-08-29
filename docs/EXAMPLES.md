# Examples · 5 Real-World Scenarios

> 🦊 Personal project by [@KratosLee-6](https://github.com/KratosLee-6) · MIT licensed.

Five concrete use cases, each with a real Brief input and what the output looks like. Run them yourself with `python -m fox.cli expert`.

---

## 1. 🚀 SaaS Landing Page (SaaS 落地页)

**Use case**: A 5-person startup needs a landing page by EOD.

**Brief input** (`examples/briefs/saas_landing.txt`):

```
Product: TaskFox — AI task manager for remote teams
Audience: Engineering managers, 30-45, knowledge workers
Goal: Sign up for free trial (primary), demo booking (secondary)
Style hint: clean, trustworthy, modern
Tone: confident but not corporate
Assets: hero image (team working), 3 feature icons, customer logo strip
Constraints: < 100 KB total, AAA contrast, mobile-first
```

**Expected output**: `output/landing.html` (~28 KB) + assets/ + `feedback.json` score ≈ 0.87.

**Screenshot placeholder**:

<!-- TODO [KX]: generate after first run -->
![SaaS Landing](assets/screenshots/example-landing.png)

**Run it**:

```bash
python -m fox.cli expert \
    --brief examples/briefs/saas_landing.txt \
    --style swiss \
    --output output/landing.html
```

---

## 2. 📊 Analytics Dashboard (仪表盘)

**Use case**: Internal team dashboard for monitoring API health.

**Brief input** (`examples/briefs/api_dashboard.txt`):

```
Product: API Health Dashboard
Audience: SRE team, internal tool
Goal: Spot incidents fast (p99 latency, error rate)
Style hint: data-dense, dark mode preferred
Tone: technical, no marketing fluff
Assets: status icons, sparkline placeholders
Constraints: real-time refresh, print-friendly fallback
```

**Expected output**: `output/dashboard.html` with 4 KPI cards + 2 charts + log tail, feedback score ≈ 0.82.

**Screenshot placeholder**:

<!-- TODO [KX] -->
![Dashboard](assets/screenshots/example-dashboard.png)

**Run it**:

```bash
python -m fox.cli expert \
    --brief examples/briefs/api_dashboard.txt \
    --style brutalist \
    --output output/dashboard.html
```

---

## 3. 📑 Pitch Deck (PPT / 演示稿)

**Use case**: Seed-round pitch deck for AI startup.

**Brief input** (`examples/briefs/seed_pitch.txt`):

```
Product: Pitch deck — Round Seed
Audience: Tier-1 VCs (a16z, Sequoia, etc.)
Goal: Get second meeting (5 min deck, 10 slides)
Style hint: editorial, magazine-like
Tone: bold, narrative-driven
Assets: founder photo, product screenshots, market size chart
Constraints: print-ready, 16:9, light + dark variants
```

**Expected output**: `output/deck.html` with 10 slides (cover / problem / solution / market / product / traction / team / ask / contact / thanks), each a `<section>`, feedback score ≈ 0.85.

**Screenshot placeholder**:

<!-- TODO [KX] -->
![Pitch Deck](assets/screenshots/example-pitch.png)

**Run it**:

```bash
python -m fox.cli expert \
    --brief examples/briefs/seed_pitch.txt \
    --style editorial \
    --output output/deck.html
```

---

## 4. 👤 Resume / CV (简历)

**Use case**: Senior engineer looking for new role.

**Brief input** (`examples/briefs/senior_engineer_resume.txt`):

```
Person: Alex Chen, Senior Backend Engineer
Audience: Tech hiring managers, FAANG-tier companies
Goal: Get interview callback
Style hint: minimalist, ATS-friendly
Tone: professional, accomplishment-focused
Assets: profile photo, GitHub contribution graph
Constraints: 1-page print, plain text fallback
```

**Expected output**: `output/resume.html` with header + experience + projects + skills + education, plus plain-text fallback, feedback score ≈ 0.90.

**Screenshot placeholder**:

<!-- TODO [KX] -->
![Resume](assets/screenshots/example-resume.png)

**Run it**:

```bash
python -m fox.cli expert \
    --brief examples/briefs/senior_engineer_resume.txt \
    --style swiss \
    --output output/resume.html
```

---

## 5. 🎨 Event Poster (海报)

**Use case**: Tech meetup poster for community event.

**Brief input** (`examples/briefs/dev_meetup_poster.txt`):

```
Event: HTMX + AI meetup, Shanghai, Sep 15
Audience: local devs, 100 attendees expected
Goal: Sell 80 tickets
Style hint: brutalist, eye-catching
Tone: casual, energetic
Assets: speaker headshots, sponsor logos, venue photo
Constraints: A3 print, social-share 1:1 crop
```

**Expected output**: `output/poster.html` (A3 + 1:1 variants), feedback score ≈ 0.78.

**Screenshot placeholder**:

<!-- TODO [KX] -->
![Poster](assets/screenshots/example-poster.png)

**Run it**:

```bash
python -m fox.cli expert \
    --brief examples/briefs/dev_meetup_poster.txt \
    --style brutalist \
    --output output/poster.html
```

---

## 🧪 Try It Yourself + Feedback Loop (自己动手 + 反馈循环)

Run any example brief in 30 seconds:

```bash
ls examples/briefs/        # saas_landing / api_dashboard / seed_pitch / resume / poster
python -m fox.cli expert --brief examples/briefs/<chosen>.txt --style swiss --output output/test.html
open output/test.html      # macOS  ·  xdg-open (Linux)  ·  start (Windows)
```

If the feedback agent scores < 0.8, iterate:

```bash
# Auto-loop until score >= 0.85 or 3 iterations
python -m fox.cli expert \
    --brief examples/briefs/saas_landing.txt --style swiss --output output/landing.html \
    --iterate --max-iter 3
```

Or run `examples/feedback_iteration.sh` / `examples/feedback_python.py` for a full demo of the iteration loop with score progression logging.

---

<p align="center"><sub>🦊 5 scenarios · 5 styles · 1 expert CLI · your turn.</sub></p>
