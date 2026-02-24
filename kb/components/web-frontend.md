---
type: component
title: "Web Frontend"
kind: application
path: "web/"
owner: "markr"
dependencies: ["svelte5", "sveltekit", "tailwindcss", "codemirror", "marked", "fuse.js"]
tags: [web, frontend, svelte, ui]
---

# Web Frontend

SvelteKit 5 single-page application for browsing, editing, and managing knowledge bases. Built with Svelte 5 runes, Tailwind CSS, and CodeMirror 6.

## Architecture

```
web/
  src/
    routes/
      +layout.svelte          # Root layout: Sidebar + main + ChatSidebar
      +page.svelte             # Dashboard
      entries/
        +page.svelte           # Entry list with search
        [id]/+page.svelte      # Entry view/edit with toolbar, AI actions, panels
        new/+page.svelte       # Create entry
      settings/+page.svelte    # Settings page (appearance, general, AI provider)
      daily/+page.svelte       # Daily notes with calendar
      timeline/+page.svelte    # Timeline visualization
    lib/
      api/
        client.ts              # ApiClient singleton with typed methods
        types.ts               # TypeScript interfaces matching Pydantic schemas
      stores/
        kbs.svelte.ts          # Knowledge base list
        entries.svelte.ts      # Current entry, CRUD operations
        search.svelte.ts       # Search with debounce, mode support
        settings.svelte.ts     # Settings read/write
        starred.svelte.ts      # Starred entries
        ui.svelte.ts           # Theme, sidebar, panels, toasts, chat toggle
        ai.svelte.ts           # AI chat messages, SSE streaming, entry context
      components/
        layout/
          Sidebar.svelte       # Navigation sidebar with KB switcher
          Topbar.svelte        # Breadcrumbs and page title
          SplitPane.svelte     # Resizable split pane for side panels
        entry/
          EntryCard.svelte     # Entry card for lists
          EntryList.svelte     # Paginated entry list
          EntryMeta.svelte     # Metadata sidebar (tags, dates, links)
          BacklinksPanel.svelte # Backlinks side panel
          OutlinePanel.svelte  # Table of contents from headings
          VersionHistoryPanel.svelte # Git version history
          TemplatePicker.svelte # Template selection for new entries
        ai/
          ChatSidebar.svelte   # AI chat panel with SSE streaming
          SearchResults.svelte # Reusable search results component
        common/
          Toast.svelte         # Toast notifications
          TagBadge.svelte      # Tag pill component
          TagTree.svelte       # Hierarchical tag tree
          ThemeToggle.svelte   # Dark/light theme toggle
          KBSwitcher.svelte    # KB dropdown selector
        QuickSwitcher.svelte   # Cmd+O fuzzy entry finder
        CommandPalette.svelte  # Cmd+K command palette
        StarButton.svelte      # Star/unstar toggle
        Calendar.svelte        # Calendar for daily notes
      editor/
        Editor.svelte          # CodeMirror 6 markdown editor
        wikilink-utils.ts      # [[wikilink]] rendering and parsing
        callouts.ts            # Obsidian-style callout rendering
      utils/
        keyboard.ts            # Global keyboard shortcut manager
```

## Store Pattern

All stores use **Svelte 5 runes** with class-based state:

```typescript
class SomeStore {
    value = $state<Type>(initial);
    loading = $state(false);
    error = $state<string | null>(null);

    async load() {
        this.loading = true;
        try {
            this.value = await api.fetchData();
        } catch (e) {
            this.error = e instanceof Error ? e.message : 'Failed';
        } finally {
            this.loading = false;
        }
    }
}
export const someStore = new SomeStore();
```

## AI Features

### Chat Sidebar (`ChatSidebar.svelte` + `ai.svelte.ts`)

- Global right-side panel toggled via `Cmd+Shift+K` or "Ask AI about this" button
- Streams responses via SSE (`POST /api/ai/chat`)
- RAG pipeline: user query → backend search → context injection → LLM streaming
- Citations rendered as `[[entry-id]]` clickable links
- Source entries displayed as cards below responses
- Entry context: can be pre-filled from the current entry page

### AI Actions (entry page toolbar)

- **Summarize**: Generates 2-3 sentence summary via `/api/ai/summarize`
- **Suggest Tags**: AI suggests tags from existing vocabulary via `/api/ai/auto-tag`, click to accept
- **Find Links**: Searches related entries, AI identifies link candidates via `/api/ai/suggest-links`

Results shown in a purple banner below the toolbar with accept/dismiss controls.

### Settings

AI Provider section in Settings page:
- Provider dropdown (Anthropic, OpenAI, OpenRouter, Ollama, None)
- Model text input with per-provider placeholder defaults
- API key (password field)
- Base URL (for custom endpoints)
- "Test Connection" button → `GET /api/ai/status`

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+O` | Quick Switcher (fuzzy entry search) |
| `Cmd+K` | Command Palette |
| `Cmd+D` | Navigate to today's daily note |
| `Cmd+Shift+K` | Toggle AI chat sidebar |
| `Cmd+Shift+B` | Toggle backlinks panel (entry page) |
| `Cmd+Shift+O` | Toggle outline panel (entry page) |
| `Cmd+Shift+H` | Toggle version history (entry page) |

## CSS Conventions

- **Tailwind** with `dark:` variants throughout
- **Colors**: `zinc-*` neutrals, `blue-*` interactive, `purple-*` AI features, `red-500` errors, `amber-500` warnings
- **Borders**: `border-zinc-200 dark:border-zinc-800`
- **Panels**: `border-l` or `border-r` separators

## Build

```bash
cd web && npm run build    # → dist/ (static adapter)
cd web && npm run dev      # Dev server with Vite proxy to FastAPI
cd web && npm run test:unit # Vitest unit tests
```

## Related

- [REST API Server](rest-api.md) — Backend API consumed by this frontend
- [LLM Service](llm-service.md) — Powers AI features via REST endpoints
- [Search Service](search-service.md) — Provides search functionality
