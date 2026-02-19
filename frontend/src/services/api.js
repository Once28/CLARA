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

// Compute score as weighted average: pass=100, warning=50, critical=0
function computeScore(breakdown) {
  if (!breakdown || breakdown.length === 0) return 0;
  const statusScore = { pass: 100, warning: 50, critical: 0 };
  const total = breakdown.reduce((sum, item) => sum + (statusScore[item.status] ?? 0), 0);
  return Math.round(total / breakdown.length);
}

let mockStore = [
  {
    id: "003",
    filename: "PROT_SAP_003.pdf",
    uploadDate: "2026-02-01",
    approvalStatus: "not approved",
    phase: "Early Stage Phase 0",
    // score computed after definition
    queryDescription: 'Regulatory nodes for 21 CFR 50.20, 50.25, 56.108, and 11.10 were matched against "PROT_SAP_003" protocol content using semantic similarity scoring. Retrieved sections were ranked by relevance to informed consent, IRB oversight, and electronic record requirements.',
    retrievedSections: [
      "Page 14 – Informed Consent Overview",
      "Page 22 – IRB Review Procedures",
      "Page 29 – Inclusion/Exclusion Criteria",
      "Page 31 – Recruitment Strategy",
      "Page 38 – Data Management & Electronic Records",
    ],
    breakdown: [
      {
        regulation: "21 CFR P50: Protection of Human Subjects",
        status: "warning",
        note: "Discussed in protocol but missing information on strict guidelines for vulnerable populations",
        focus: "Informed consent elements, equitable subject selection, additional safeguards for vulnerable populations.",
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
      {
        regulation: "21 CFR P56: IRBs",
        status: "critical",
        note: "Content is not discussed within the protocol",
        focus: "IRB composition, review procedures, record-keeping, and continuing oversight requirements.",
        gaps: [
          "No mention of IRB review, approval process, or institutional oversight.",
          "Continuing review frequency and quorum requirements are absent.",
        ],
        remediation: [
          "Add a dedicated IRB section describing the review and approval process.",
          "Include details on IRB composition, quorum, and continuing review schedule.",
          "Document amendment and adverse event reporting procedures to the IRB.",
        ],
      },
      {
        regulation: "21 CFR P11: Electronic Records",
        status: "pass",
        note: "Adequate audit trail and e-signature provisions",
        focus: "Electronic record integrity, audit trails, system validation, and e-signature compliance.",
        gaps: [],
        remediation: [],
      },
    ],
  },
  {
    id: "002",
    filename: "PROT_SAP_002.pdf",
    uploadDate: "2026-01-15",
    approvalStatus: "not approved",
    phase: "Early Stage Phase 0",
    // score computed after definition
    queryDescription: 'Regulatory nodes for 21 CFR 50.20, 50.25, 56.108, and 11.10 were matched against "PROT_SAP_002" protocol content using semantic similarity scoring.',
    retrievedSections: [
      "Page 10 – Study Objectives",
      "Page 16 – Informed Consent",
      "Page 25 – Data Handling",
    ],
    breakdown: [
      {
        regulation: "21 CFR P50: Protection of Human Subjects",
        status: "warning",
        note: "Discussed in protocol but missing information on strict guidelines for vulnerable populations",
        focus: "Informed consent elements, equitable subject selection, additional safeguards for vulnerable populations.",
        gaps: [
          "Consent form references exist but lack detail on required elements under 21 CFR 50.25.",
          "No mention of safeguards for vulnerable populations.",
        ],
        remediation: [
          "Expand consent language to include all required disclosure elements.",
          "Add specific safeguards and language for vulnerable populations.",
        ],
      },
      {
        regulation: "21 CFR P56: IRBs",
        status: "critical",
        note: "Content is not discussed within the protocol",
        focus: "IRB composition, review procedures, record-keeping, and continuing oversight requirements.",
        gaps: [
          "No mention of IRB review or institutional oversight.",
        ],
        remediation: [
          "Add a dedicated IRB section with review, approval, and continuing oversight procedures.",
        ],
      },
      {
        regulation: "21 CFR P11: Electronic Records",
        status: "warning",
        note: "Partial coverage of audit trail requirements",
        focus: "Electronic record integrity, audit trails, system validation, and e-signature compliance.",
        gaps: [
          "Audit trail provisions are referenced but system validation procedures are not described.",
        ],
        remediation: [
          "Document system validation procedures and complete audit trail requirements per 21 CFR Part 11.",
        ],
      },
    ],
  },
  {
    id: "001",
    filename: "PROT_SAP_001.pdf",
    uploadDate: "2026-01-01",
    approvalStatus: "not approved",
    phase: "Early Stage Phase 0",
    // score computed after definition
    queryDescription: 'Regulatory nodes for 21 CFR 50.20, 50.25, 56.108, and 11.10 were matched against "PROT_SAP_001" protocol content using semantic similarity scoring.',
    retrievedSections: [
      "Page 8 – Study Overview",
      "Page 14 – Eligibility Criteria",
    ],
    breakdown: [
      {
        regulation: "21 CFR P50: Protection of Human Subjects",
        status: "critical",
        note: "Informed consent section lacks required disclosure elements",
        focus: "Informed consent elements, equitable subject selection, additional safeguards for vulnerable populations.",
        gaps: [
          "Informed consent section is absent or critically deficient.",
          "No mention of alternatives to participation or compensation for injury.",
        ],
        remediation: [
          "Create a comprehensive informed consent section addressing all 21 CFR 50.25 elements.",
          "Include language on alternatives and compensation for research-related injury.",
        ],
      },
      {
        regulation: "21 CFR P56: IRBs",
        status: "critical",
        note: "Content is not discussed within the protocol",
        focus: "IRB composition, review procedures, record-keeping, and continuing oversight requirements.",
        gaps: [
          "No mention of IRB review or institutional oversight.",
        ],
        remediation: [
          "Add a complete IRB section with composition, review, and reporting procedures.",
        ],
      },
      {
        regulation: "21 CFR P11: Electronic Records",
        status: "warning",
        note: "No mention of system validation procedures",
        focus: "Electronic record integrity, audit trails, system validation, and e-signature compliance.",
        gaps: [
          "No mention of system validation or e-signature compliance procedures.",
        ],
        remediation: [
          "Add system validation and e-signature compliance documentation per 21 CFR Part 11.",
        ],
      },
    ],
  },
];

// Compute scores from breakdown statuses
mockStore.forEach((audit) => {
  audit.score = computeScore(audit.breakdown);
  audit.approvalStatus = audit.score >= 75 ? "approved" : "not approved";
});

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

    const statuses = ["pass", "warning", "critical"];
    const pickStatus = () => statuses[Math.floor(Math.random() * 3)];
    const s1 = pickStatus(), s2 = pickStatus(), s3 = pickStatus();

    const statusScore = { pass: 100, warning: 50, critical: 0 };
    const score = Math.round((statusScore[s1] + statusScore[s2] + statusScore[s3]) / 3);

    const breakdownNotes = {
      "pass": {
        "21 CFR P50": "Informed consent procedures adequately address required disclosure elements and vulnerable population safeguards.",
        "21 CFR P56": "IRB review procedures and composition requirements are clearly documented.",
        "21 CFR P11": "Adequate audit trail, e-signature provisions, and system validation procedures in place.",
      },
      "warning": {
        "21 CFR P50": "Consent section present but missing detail on alternatives to participation and compensation for injury.",
        "21 CFR P56": "IRB review mentioned but lacks specifics on continuing review frequency and quorum requirements.",
        "21 CFR P11": "Electronic records referenced but system validation and audit trail procedures are only partially described.",
      },
      "critical": {
        "21 CFR P50": "Informed consent section is absent or critically deficient — required disclosure elements not addressed.",
        "21 CFR P56": "No mention of IRB review, approval process, or institutional oversight.",
        "21 CFR P11": "No provisions for electronic record integrity, audit trails, or e-signature compliance.",
      },
    };

    const title = metadata.title || file.name.replace(/\.pdf$/i, "");

    const gapsMap = {
      "pass": { "21 CFR P50": [], "21 CFR P56": [], "21 CFR P11": [] },
      "warning": {
        "21 CFR P50": ["Consent section present but does not fully enumerate required disclosure elements per 21 CFR 50.25.", "Exclusion criteria lack explicit justification for demographic limitations."],
        "21 CFR P56": ["IRB review mentioned but lacks specifics on continuing review frequency and quorum requirements."],
        "21 CFR P11": ["Electronic records referenced but system validation and audit trail procedures are only partially described."],
      },
      "critical": {
        "21 CFR P50": ["Informed consent section is absent or critically deficient — required disclosure elements not addressed.", "No mention of safeguards for vulnerable populations."],
        "21 CFR P56": ["No mention of IRB review, approval process, or institutional oversight.", "Continuing review and adverse event reporting are completely absent."],
        "21 CFR P11": ["No provisions for electronic record integrity, audit trails, or e-signature compliance."],
      },
    };

    const remediationMap = {
      "pass": { "21 CFR P50": [], "21 CFR P56": [], "21 CFR P11": [] },
      "warning": {
        "21 CFR P50": ["Expand informed consent language to include all required disclosure elements under 21 CFR 50.25.", "Provide scientific rationale for each exclusion criterion."],
        "21 CFR P56": ["Add details on IRB composition, quorum requirements, and continuing review schedule."],
        "21 CFR P11": ["Document system validation procedures and complete audit trail requirements per 21 CFR Part 11."],
      },
      "critical": {
        "21 CFR P50": ["Create a comprehensive informed consent section addressing all 21 CFR 50.25 elements.", "Add specific safeguards and language for vulnerable populations."],
        "21 CFR P56": ["Add a dedicated IRB section describing the review and approval process.", "Include details on IRB composition, quorum, continuing review, and amendment protocols."],
        "21 CFR P11": ["Implement complete audit trail documentation, system validation, and e-signature procedures per 21 CFR Part 11."],
      },
    };

    const newAudit = {
      id: String(mockStore.length + 1).padStart(3, "0"),
      filename: file.name,
      uploadDate: new Date().toISOString().split("T")[0],
      approvalStatus: score >= 75 ? "approved" : "not approved",
      phase: metadata.phase || "Unknown",
      score,
      queryDescription: `Regulatory nodes for 21 CFR 50.20, 50.25, 56.108, and 11.10 were matched against "${title}" protocol content using semantic similarity scoring. Retrieved sections were ranked by relevance to informed consent, IRB oversight, and electronic record requirements.`,
      retrievedSections: [
        "Page 12 – Study Overview & Objectives",
        "Page 18 – Informed Consent Overview",
        "Page 22 – IRB Review Procedures",
        "Page 24 – Inclusion / Exclusion Criteria",
        "Page 30 – Data Management & Electronic Records",
      ],
      breakdown: [
        {
          regulation: "21 CFR P50: Protection of Human Subjects",
          status: s1,
          note: breakdownNotes[s1]["21 CFR P50"],
          focus: "Informed consent elements, equitable subject selection, additional safeguards for vulnerable populations.",
          gaps: gapsMap[s1]["21 CFR P50"],
          remediation: remediationMap[s1]["21 CFR P50"],
        },
        {
          regulation: "21 CFR P56: IRBs",
          status: s2,
          note: breakdownNotes[s2]["21 CFR P56"],
          focus: "IRB composition, review procedures, record-keeping, and continuing oversight requirements.",
          gaps: gapsMap[s2]["21 CFR P56"],
          remediation: remediationMap[s2]["21 CFR P56"],
        },
        {
          regulation: "21 CFR P11: Electronic Records",
          status: s3,
          note: breakdownNotes[s3]["21 CFR P11"],
          focus: "Electronic record integrity, audit trails, system validation, and e-signature compliance.",
          gaps: gapsMap[s3]["21 CFR P11"],
          remediation: remediationMap[s3]["21 CFR P11"],
        },
      ],
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
    if (metadata) {
      Object.entries(metadata).forEach(([k, v]) => {
        if (v) form.append(k, v);
      });
    }
    const res = await fetch(`${API_BASE}/api/audits/upload`, { method: "POST", body: form });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`Upload failed (${res.status}): ${text}`);
    }
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
