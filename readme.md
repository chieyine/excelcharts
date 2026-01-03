# 📊 Instant Charts

**Upload something. See your story.**

> No buttons. No menus. Just your data, made beautiful.

<!-- TODO: Add demo GIF here -->
<!-- ![Demo](./assets/demo.gif) -->

<!-- TODO: Add live demo link -->
<!-- 🚀 **[Try it now →](https://instantcharts.app)** -->

---

## TL;DR

- 📤 **Drop a file** → Get intelligent charts instantly
- 🎯 **Zero learning curve** — no accounts, no setup, no tutorials
- 🧠 **System chooses the best chart** — one confident answer, not options paralysis
- 💬 **Natural language insights** — "Revenue grew 34% in Q3"
- 🔒 **Privacy-first** — your data is never stored
- ⚡ **Blazing fast** — results in seconds

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Core Features](#core-features)
3. [Technical Architecture](#technical-architecture)
4. [Tech Stack](#tech-stack)
5. [MVP Scope](#mvp-scope)
6. [Future Roadmap](#future-roadmap)
7. [Product Vision](#product-vision)

---

## Design Philosophy

> "Design is not just what it looks like. Design is how it works." — Steve Jobs

### The Three Questions

Every feature must pass:

1. **Can someone use it without thinking?**
2. **Does it feel magical?**
3. **Can we remove anything else?**

### Design Principles

| Principle                   | Implementation                           |
| --------------------------- | ---------------------------------------- |
| **No chrome**               | Minimal UI — the chart IS the interface  |
| **One primary action**      | Every screen has ONE obvious thing to do |
| **Progressive disclosure**  | Advanced options hidden until needed     |
| **Animate with purpose**    | Charts draw on, don't just appear        |
| **White space is sacred**   | Don't fill every pixel                   |
| **Confidence, not options** | Show THE answer, not 10 choices          |

### What We Remove

- ❌ Settings pages (sensible defaults instead)
- ❌ Account systems (until absolutely necessary)
- ❌ Tutorials or onboarding (make it self-evident)
- ❌ "Chart type" dropdowns (system chooses)
- ❌ Any text that says "configure" or "customize"

---

## Core Features

### 🎯 Magical Input

**Multiple ways to get data in — all effortless:**

| Method           | Description                              |
| ---------------- | ---------------------------------------- |
| **Drag & Drop**  | Drag file directly onto the page         |
| **Paste Data**   | Cmd/Ctrl+V from Excel or Sheets          |
| **Paste URL**    | Drop a link to a public CSV/Google Sheet |
| **Click Upload** | Traditional file picker (fallback)       |

**Instant Preview on Drag:**
When a file hovers over the drop zone:

```
"sales_data.xlsx detected — 4 sheets, 2,300 rows"
```

Before they drop, they know it'll work.

---

### ⭐ One Confident Answer

After analysis, show ONE recommended chart — prominently:

```
┌─────────────────────────────────────────────┐
│  ⭐ BEST CHART                              │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │                                       │  │
│  │      [Beautiful Line Chart]           │  │
│  │                                       │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  "Monthly Sales by Region"                  │
│                                             │
│  📈 Revenue grew 34% from Jan to Dec,       │
│     with the biggest jump in Q3.            │
│                                             │
│              [ Export ↓ ]                   │
│                                             │
│  ─────────────────────────────────────────  │
│  Also available: [Bar] [Scatter] [Table]    │
└─────────────────────────────────────────────┘
```

Not "here are 5 options, you decide." **One answer. Confidence.**

---

### 💬 Natural Language Insights

Below each chart, auto-generate a human sentence:

> "📈 Revenue grew 34% from January to December, with the biggest jump in Q3."

> "📊 Product A outsells all others by 2x, but Product C is growing fastest."

> "⚠️ March had an unusual spike — worth investigating."

**This is the insight, not just the chart. We think for the user.**

---

### 🏷️ Smart Auto-Naming

Generate meaningful titles from column detection:

| Raw Columns                | Generated Title           |
| -------------------------- | ------------------------- |
| `date`, `revenue`          | "Revenue Over Time"       |
| `product`, `units_sold`    | "Units Sold by Product"   |
| `region`, `month`, `sales` | "Monthly Sales by Region" |

Never show: "Column A vs Column B"

---

### 📤 Export Anywhere

One-click export with a sleek popover:

```
┌───────────────────────┐
│  📋 Copy to Clipboard │
│  ───────────────────  │
│  📷 PNG (2x quality)  │
│  🎨 SVG (vector)      │
│  📄 PDF               │
│  📊 PowerPoint        │
│  ───────────────────  │
│  🔗 Shareable Link    │
└───────────────────────┘
```

Charts go where people actually use them.

---

### ⏪ Undo Timeline

Every action is reversible. Tiny timeline at the bottom:

```
← Original | Changed axis | Filtered top 10 | Now →
```

**Users should never fear experimenting.**

---

### 🎲 "Surprise Me"

A single button for data exploration:

> "Show me something interesting in this data"

Return an unexpected insight, unusual correlation, or hidden pattern.

**Pure delight.**

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        BROWSER                              │
│                      (Next.js App)                          │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              DROP ZONE / PASTE CAPTURE              │   │
│   │         (Drag, Paste, URL, or Click Upload)         │   │
│   └─────────────────────────┬───────────────────────────┘   │
│                             │                               │
│                             ▼                               │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                 CHART DISPLAY                       │   │
│   │   ┌─────────────────────────────────────────────┐   │   │
│   │   │        ⭐ Recommended Chart (Vega-Lite)     │   │   │
│   │   └─────────────────────────────────────────────┘   │   │
│   │   "Natural language insight below chart"           │   │
│   │   [Export ↓]    [Alternatives: Bar | Scatter]       │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         API                                 │
│                    (FastAPI + Python)                       │
│                                                             │
│   ┌──────────────┐   ┌──────────────┐   ┌───────────────┐   │
│   │ Parse File   │ → │ Profile Data │ → │ Infer Charts  │   │
│   │              │   │              │   │ + Insights    │   │
│   └──────────────┘   └──────────────┘   └───────────────┘   │
│                                                             │
│                    ⚠️ NO DATA STORAGE                       │
│              All processing is ephemeral only               │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Frontend

| Technology              | Purpose         |
| ----------------------- | --------------- |
| Next.js 14 (App Router) | React framework |
| TypeScript (strict)     | Type safety     |
| Tailwind CSS            | Styling         |
| Framer Motion           | Animations      |
| Vega-Lite + Vega-Embed  | Chart rendering |

### Backend

| Technology   | Purpose              |
| ------------ | -------------------- |
| Python 3.11+ | Core language        |
| FastAPI      | API framework        |
| Pandas       | Data manipulation    |
| NumPy        | Numerical operations |
| OpenPyXL     | Excel parsing        |

### Infrastructure

| Component | Choice                                   |
| --------- | ---------------------------------------- |
| Hosting   | Vercel (frontend) + Railway/Render (API) |
| Database  | None (ephemeral only)                    |
| Auth      | None (until needed)                      |

---

## MVP Scope

### ✅ Phase 1: Core Magic (Week 1-2)

| Feature                                | Priority    |
| -------------------------------------- | ----------- |
| Drag & drop file upload                | 🔥 Critical |
| CSV + XLSX parsing                     | 🔥 Critical |
| Data profiling engine                  | 🔥 Critical |
| Chart inference (top 1 recommendation) | 🔥 Critical |
| Vega-Lite spec generation              | 🔥 Critical |
| Basic chart rendering                  | 🔥 Critical |
| PNG/SVG export                         | 🔥 Critical |

### ✅ Phase 2: Polish (Week 3)

| Feature                               | Priority |
| ------------------------------------- | -------- |
| Paste from clipboard (Cmd+V)          | ⭐ High  |
| Natural language insight (1 sentence) | ⭐ High  |
| Smart chart titles                    | ⭐ High  |
| Alternative chart options (2-3)       | ⭐ High  |
| Loading animation                     | ⭐ High  |
| Mobile responsive                     | ⭐ High  |

### ✅ Phase 3: Delight (Week 4)

| Feature                  | Priority  |
| ------------------------ | --------- |
| Chart draw-on animation  | 👍 Medium |
| Undo/redo timeline       | 👍 Medium |
| Copy to clipboard        | 👍 Medium |
| Colorblind-safe palettes | 👍 Medium |
| Print stylesheet         | 👍 Medium |

---

## Future Roadmap

**After MVP is proven:**

| Feature                 | Description                                                  |
| ----------------------- | ------------------------------------------------------------ |
| 📖 **Story Mode**       | Generate 1-page report (title, insights, charts, conclusion) |
| 🎲 **"Surprise Me"**    | Discover unexpected patterns                                 |
| 📋 **Paste URL**        | Auto-fetch public CSV/Google Sheets                          |
| 📱 **PWA / Offline**    | Works without internet                                       |
| 🔗 **Shareable Links**  | Optional, privacy-respecting                                 |
| 🌍 **Multi-language**   | i18n support                                                 |
| 🎨 **Themes**           | Light/dark, brand colors                                     |
| 📊 **More chart types** | Only if user-proven need                                     |

### 🎁 The "One More Thing": Story Mode

Instead of just charts:

> "📖 Generate a 1-page report for this data"

Output a beautiful PDF with:

- Auto-generated title
- 3 key insights (natural language)
- 2-3 relevant charts
- Summary conclusion

**This is what non-technical people actually need.** Not charts — _answers_.

---

## Product Vision

> Build a web application that accepts CSV/XLSX files, profiles the data server-side, infers the single best chart using deterministic rules, generates Vega-Lite specs with beautiful defaults, and renders them with natural language insights.
>
> **Optimize for people who have data but no time.**
>
> Every interaction should feel magical.
> Every output should be print-ready.
> Every decision should be made for the user.

---

## The 95/5 Rule

Over 95% of visualization needs are solved by **5 chart types**:

| Chart        | Use Case         |
| ------------ | ---------------- |
| 📈 Line      | Trends over time |
| 📊 Bar       | Comparisons      |
| 🔵 Scatter   | Relationships    |
| 📉 Histogram | Distributions    |
| 📋 Table     | Exact values     |

Everything else is edge-case or vanity. **Fewer options, done perfectly.**

---

## Privacy & Trust

> **Your data never leaves your session.**

| Principle   | Implementation                     |
| ----------- | ---------------------------------- |
| No storage  | Files processed in-memory only     |
| No logging  | We don't log data content          |
| No accounts | Nothing to track                   |
| Explicit    | UI states "data processed locally" |

---

## Why This Wins

| Aspect          | Others (Tableau, Excel) | Instant Charts               |
| --------------- | ----------------------- | ---------------------------- |
| Chart selection | You decide              | **We decide**                |
| Learning curve  | Hours                   | **Seconds**                  |
| Setup required  | Significant             | **None**                     |
| Account needed  | Yes                     | **No**                       |
| Output quality  | Varies                  | **Always print-ready**       |
| Insight level   | Chart only              | **Chart + natural language** |

---

## Quick Start (Development)

### Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- npm or yarn

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/instant-charts.git
   cd instant-charts
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Create environment file
   cp .env.example .env  # Or create .env manually (see ENV_SETUP.md)
   
   # Start the server
   uvicorn main:app --reload
   ```
   
   The API will be available at `http://localhost:8000`
   API documentation: `http://localhost:8000/docs`

3. **Frontend Setup:**
   ```bash
   cd frontend
   
   # Install dependencies
   npm install
   
   # Create environment file
   cp .env.example .env.local  # Or create .env.local manually
   
   # Start the development server
   npm run dev
   ```
   
   The app will be available at `http://localhost:3000`

4. **Run Tests:**
   ```bash
   # Backend tests
   cd backend
   source venv/bin/activate
   pytest
   
   # Frontend tests
   cd frontend
   npm test
   ```

### Environment Variables

See [ENV_SETUP.md](./ENV_SETUP.md) for detailed environment variable configuration.

**Required Backend Variables:**
- `ALLOWED_ORIGINS` - CORS allowed origins (comma-separated)
- `MAX_FILE_SIZE_MB` - Maximum file size in MB (default: 50)
- `LOG_LEVEL` - Logging level (default: INFO)

**Required Frontend Variables:**
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000/api)

### Troubleshooting

**Backend won't start:**
- Ensure Python 3.9+ is installed
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify `.env` file exists and has correct values

**Frontend won't start:**
- Ensure Node.js 18+ is installed
- Check that all dependencies are installed: `npm install`
- Verify `.env.local` file exists with `NEXT_PUBLIC_API_URL`

**CORS errors:**
- Ensure frontend URL is in `ALLOWED_ORIGINS` in backend `.env`
- Check that both servers are running

**File upload fails:**
- Check file size is under the limit (default: 50MB)
- Verify file is CSV or Excel format
- Check backend logs for detailed error messages

---

## Contributing

We welcome contributions that make the product simpler and more magical.

Before contributing, ask:

1. Does this make it easier for users?
2. Can we achieve this with less UI?
3. Does this feel like magic?

---

## License

MIT License — use it, build on it, make it better.

---

<p align="center">
  <strong>Built for everyone who just wants to see their data.</strong>
  <br><br>
  <em>"Upload something. See your story."</em>
</p>
