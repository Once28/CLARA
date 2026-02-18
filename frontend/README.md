# CLARA Frontend

Clinical Protocol Regulatory Audit – React dashboard.

## Project Structure

```
clara-frontend/
├── index.html
├── package.json
├── vite.config.js                  # Dev server + API proxy
│
└── src/
    ├── main.jsx                    # Entry point
    ├── App.jsx                     # Root layout (composes all panels)
    │
    ├── components/
    │   ├── Header.jsx              # Top bar: logo, create/upload buttons
    │   ├── AuditCard.jsx           # Single audit card (left panel)
    │   ├── ScoreChart.jsx          # SVG score trend chart (right panel)
    │   ├── SummaryPanel.jsx        # Detailed insights (right panel)
    │   ├── UploadModal.jsx         # Upload modal with drag-drop + metadata
    │   └── ui.jsx                  # Shared atoms: StatusDot, DownloadIcon, etc.
    │
    ├── hooks/
    │   └── useAudits.js            # State management: fetch, upload, select
    │
    ├── services/
    │   └── api.js                  # API layer (mock / live toggle)
    │
    └── styles/
        └── global.css              # CSS variables, fonts, animations
```

## Quick Start

```bash
npm install
npm run dev
```

Opens at http://localhost:5173 with mock data.

## Connecting to the Backend

1. Create a `.env` file:
   ```
   VITE_API_URL=http://localhost:8000
   ```

2. The API service (`src/services/api.js`) automatically switches
   from mock data to live API calls when this variable is set.

3. The Vite dev server proxies `/api/*` to your backend (see `vite.config.js`).

### Expected Backend Endpoints

| Method | Path                | Body / Params              | Returns            |
|--------|---------------------|----------------------------|--------------------|
| GET    | /api/audits         | -                          | Array of audits    |
| GET    | /api/audits/:id     | -                          | Single audit       |
| POST   | /api/audits/upload  | FormData (file + metadata) | New audit object   |
| DELETE | /api/audits/:id     | -                          | { success: true }  |

### Audit Object Shape

```json
{
  "id": "003",
  "filename": "PROT_SAP_003.pdf",
  "uploadDate": "2026-02-01",
  "approvalStatus": "not approved",
  "phase": "Early Stage Phase 0",
  "score": 82,
  "breakdown": [
    {
      "regulation": "21 CFR P50: Protection of Human Subjects",
      "status": "warning",
      "note": "Description of finding"
    }
  ],
  "summary": {
    "regulation": "21 CFR Part 50 - Protection of Human Subjects",
    "focus": "...",
    "retrievedSections": ["Page 14 - ...", "Page 29 - ..."],
    "queryDescription": "...",
    "gaps": ["...", "..."],
    "remediation": ["...", "..."]
  }
}
```

## Adding New Components

- **New regulation type?** Add to `REGULATIONS` array in `UploadModal.jsx`
- **New card field?** Edit `AuditCard.jsx` (receives full audit object as prop)
- **New right panel section?** Create component, import in `App.jsx`
- **New API endpoint?** Add method to both `mockApi` and `liveApi` in `services/api.js`
- **New page/route?** Add `react-router-dom`, wrap `App.jsx` in a router

## Design Tokens

All colors, fonts, and radii are CSS variables in `styles/global.css`.
Change the palette there and it propagates everywhere.
