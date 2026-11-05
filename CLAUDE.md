# CLAUDE.md

Factory Inventory Management System Demo with GitHub integration - Full-stack application with Vue 3 frontend, Python FastAPI backend, and in-memory mock data (no database).

> ⚠️ **This repository and any fork you create are PUBLIC.** Do not commit credentials, internal hostnames, or private registry URLs. `client/.npmrc` pins the public npm registry and `client/package-lock.json` is gitignored to prevent locally-configured registries from leaking into commits — leave both in place.

## Critical Tool Usage Rules

### Subagents
Use the Task tool with these specialized subagents for appropriate tasks:

- **vue-expert**: Use for Vue 3 frontend features, UI components, styling, and client-side functionality
  - Examples: Creating components, fixing reactivity issues, performance optimization, complex state management
  - **MANDATORY RULE: ANY time you need to create or significantly modify a .vue file, you MUST delegate to vue-expert**
- **code-reviewer**: Use after writing significant code to review quality and best practices
- **Explore**: Use for understanding codebase structure, searching for patterns, or answering questions about how components work
- **general-purpose**: Use for complex multi-step tasks or when other agents don't fit

### Skills
- **backend-api-test** skill: Use when writing or modifying tests in `tests/backend` directory with pytest and FastAPI TestClient

### MCP Tools
- **ALWAYS use GitHub MCP tools** (`mcp__github__*`) for ALL GitHub operations
  - Exception: Local branches only - use `git checkout -b` instead of `mcp__github__create_branch`
- **ALWAYS use Playwright MCP tools** (`mcp__playwright__*`) for browser testing
  - Test against: `http://localhost:3000` (frontend), `http://localhost:8001` (API)

## Stack
- **Frontend**: Vue 3 + Composition API + Vite (port 3000)
- **Backend**: Python FastAPI (port 8001)
- **Data**: JSON files in `server/data/` loaded via `server/mock_data.py`

## Quick Start

```bash
# Backend
cd server
uv run python main.py

# Frontend
cd client
npm install && npm run dev
```

## Key Patterns

**Filter System**: 4 filters (Time Period, Warehouse, Category, Order Status) apply to all data via query params
**Data Flow**: Vue filters → `client/src/api.js` → FastAPI → In-memory filtering → Pydantic validation → Computed properties
**Reactivity**: Raw data in refs (`allOrders`, `inventoryItems`), derived data in computed properties

## API Endpoints
- `GET /api/inventory` - Filters: warehouse, category
- `GET /api/orders` - Filters: warehouse, category, status, month
- `GET /api/dashboard/summary` - All filters
- `GET /api/demand`, `/api/backlog` - No filters
- `GET /api/spending/*` - Summary, monthly, categories, transactions

## Common Issues
1. Use unique keys in v-for (not `index`) - use `sku`, `month`, etc.
2. Validate dates before `.getMonth()` calls
3. Update Pydantic models when changing JSON data structure
4. Inventory filters don't support month (no time dimension)
5. Revenue goals: $800K/month single, $9.6M YTD all months

## File Locations
- Views: `client/src/views/*.vue`
- API Client: `client/src/api.js`
- Backend: `server/main.py`, `server/mock_data.py`
- Data: `server/data/*.json`
- Styles: `client/src/App.vue`

## Design System
Modeled on trusteq.de. Tokens are CSS variables on `:root` in `client/src/App.vue` - always use `var(--...)`, never hardcode hex/rgba values in views or components.
- Colors: page background `--tq-bg` #FCFDFE, text/primary TQ Blau #003366, `--tq-navy-2` #004181 (hover), Hellblau #0069D1 (links, accents), Tint #EBF1FB (card fill), Sand #E7E0D0 (secondary buttons), Lime #DAFF7D (primary buttons/active marker only), Gold #AE9966 (logo only), Grau #C3C3C9 (dividers, never text), `--tq-text-muted` #4A5D73. Lime is never used as text on a light background
- Layout: full-width navy header band with the light logo; borderless Tint cards with generous padding; tables with thin row dividers and uppercase muted headers; no outlines around cards, no shadows, no gradients, sharp corners
- Buttons: primary = Lime fill + navy bold uppercase text; secondary = Sand; active nav = lime underline, not a filled tab
- Status: green/blue/yellow/red as muted semantic tokens (`--ok`, `--warn`, `--bad`, info = Hellblau on Tint); always keep the text label, never rely on color alone
- Contrast: keep WCAG AA (4.5:1 text, 3:1 large text/UI) for every text/background pair
- Fonts: Lora 500 for headings, Karla 400/700 for body and labels, self-hosted via `@fontsource/lora` and `@fontsource/karla`; stacks fall back to Japanese-capable system fonts
- Logo: `client/src/assets/trusteq-logo-light.svg` (white wordmark) on the navy header, `trusteq-logo.svg` on light backgrounds; do not recolor
- Charts: Custom SVG, CSS Grid for layouts; categorical colors come from `--chart-1..5` / `client/src/utils/palette.js` so a category has the same color on every page
- Do not run prettier over existing files: the codebase uses single quotes and no semicolons, a default run reformats everything
- No emojis in UI
