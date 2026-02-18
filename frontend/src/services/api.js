/**
 * API Service Layer
 *
 * Currently uses mock data. To connect to the real backend:
 *   1. Set VITE_API_URL=http://localhost:8000 in your .env
 *   2. The mock layer is bypassed automatically
 *
 * Backend endpoints expected:
 *   POST /api/audits/upload   - upload PDF, returns audit result
 *   GET  /api/audits          - list all past audits
 *   GET  /api/audits/:id      - single audit detail + summary
 *   DEL  /api/audits/:id      - delete an audit
 */

const API_BASE = import.meta.env?.VITE_API_URL || "";
const USE_MOCK = !API_BASE;

// ─── Mock Data Store ─────────────────────────────────────────

let mockStore = [
  {
    id: "003",
    filename: "PROT_SAP_003.pdf",
    uploadDate: "2026-02-01",
    approvalStatus: "not approved",
    phase: "Early Stage Phase 0",
    score: 82,
    breakdown: [
      { regulation: "21 CFR P50: Protection of Human Subjects", status: "warning", note: "Discussed in protocol but missing information on strict guidelines for vulnerable populations" },
      { regulation: "21 CFR P56: IRBs", status: "critical", note: "Content is not discussed within the protocol" },
      { regulation: "21 CFR P11: Electronic Records", status: "pass", note: "Adequate audit trail and e-signature provisions" },
    ],
    summary: {
      regulation: "21 CFR Part 50 – Protection of Human Subjects",
      focus: "Informed consent elements, equitable subject selection, additional safeguards for vulnerable populations.",
      retrievedSections: [
        "Page 14 – Informed Consent Overview",
        "Page 29 – Inclusion/Exclusion Criteria",
        "Page 31 – Recruitment Strategy",
      ],
      queryDescription: 'A query for "21 CFR 50.20 and 50.25 informed consent elements and equitable selection" retrieved regulatory nodes mapped to consent documentation requirements. Semantic similarity scoring linked these nodes to protocol content on pages 14 and 29–31.',
      gaps: [
        "The consent section describes procedures but does not fully detail required consent elements (e.g., alternatives, compensation for injury).",
        "Exclusion criteria lack explicit justification for demographic limitations.",
        "Recruitment strategy does not address outreach to underrepresented populations.",
      ],
      remediation: [
        "Expand consent language to include all required disclosure elements.",
        "Provide rationale for exclusion criteria.",
        "Add an equitable recruitment statement describing inclusion strategies.",
      ],
    },
  },
  {
    id: "002",
    filename: "PROT_SAP_002.pdf",
    uploadDate: "2026-01-15",
    approvalStatus: "not approved",
    phase: "Early Stage Phase 0",
    score: 74,
    breakdown: [
      { regulation: "21 CFR P50: Protection of Human Subjects", status: "warning", note: "Discussed in protocol but missing information on strict guidelines for vulnerable populations" },
      { regulation: "21 CFR P56: IRBs", status: "critical", note: "Content is not discussed within the protocol" },
      { regulation: "21 CFR P11: Electronic Records", status: "warning", note: "Partial coverage of audit trail requirements" },
    ],
    summary: null,
  },
  {
    id: "001",
    filename: "PROT_SAP_001.pdf",
    uploadDate: "2026-01-01",
    approvalStatus: "not approved",
    phase: "Early Stage Phase 0",
    score: 68,
    breakdown: [
      { regulation: "21 CFR P50: Protection of Human Subjects", status: "critical", note: "Informed consent section lacks required disclosure elements" },
      { regulation: "21 CFR P56: IRBs", status: "critical", note: "Content is not discussed within the protocol" },
      { regulation: "21 CFR P11: Electronic Records", status: "warning", note: "No mention of system validation procedures" },
    ],
    summary: null,
  },
];

const delay = (ms = 300) => new Promise((r) => setTimeout(r, ms));

// ─── Mock API ────────────────────────────────────────────────

const mockApi = {
  async listAudits() {
    await delay();
    return [...mockStore];
  },

  async getAudit(id) {
    await delay();
    return mockStore.find((a) => a.id === id) || null;
  },

  async uploadProtocol(file, metadata) {
    await delay(1500);
    const newAudit = {
      id: String(mockStore.length + 1).padStart(3, "0"),
      filename: file.name,
      uploadDate: new Date().toISOString().split("T")[0],
      approvalStatus: "not approved",
      phase: metadata.phase || "Unknown",
      score: Math.floor(Math.random() * 30) + 60,
      breakdown: [
        { regulation: "21 CFR P50: Protection of Human Subjects", status: "warning", note: "Analysis pending full review" },
        { regulation: "21 CFR P56: IRBs", status: "warning", note: "Analysis pending full review" },
      ],
      summary: null,
    };
    mockStore = [newAudit, ...mockStore];
    return newAudit;
  },

  async deleteAudit(id) {
    await delay();
    mockStore = mockStore.filter((a) => a.id !== id);
    return { success: true };
  },
};

// ─── Live API ────────────────────────────────────────────────

const liveApi = {
  async listAudits() {
    const res = await fetch(`${API_BASE}/api/audits`);
    if (!res.ok) throw new Error(`GET /api/audits failed: ${res.status}`);
    return res.json();
  },

  async getAudit(id) {
    const res = await fetch(`${API_BASE}/api/audits/${id}`);
    if (!res.ok) throw new Error(`GET /api/audits/${id} failed: ${res.status}`);
    return res.json();
  },

  async uploadProtocol(file, metadata) {
    const form = new FormData();
    form.append("file", file);
    Object.entries(metadata).forEach(([k, v]) => v && form.append(k, v));
    const res = await fetch(`${API_BASE}/api/audits/upload`, { method: "POST", body: form });
    if (!res.ok) throw new Error(`POST /api/audits/upload failed: ${res.status}`);
    return res.json();
  },

  async deleteAudit(id) {
    const res = await fetch(`${API_BASE}/api/audits/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`DELETE /api/audits/${id} failed: ${res.status}`);
    return res.json();
  },
};

const api = USE_MOCK ? mockApi : liveApi;
export default api;
