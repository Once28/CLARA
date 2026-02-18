import React from "react";
import { StatusDot, DownloadIcon } from "./ui";

export default function SummaryPanel({ audit }) {
  if (!audit || !audit.summary) {
    return (
      <div className="right-panel-card">
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 19, fontWeight: 700, marginBottom: 8 }}>
          Recent Summary
        </h2>
        <p style={{ fontSize: 13, color: "var(--text-muted)", lineHeight: 1.6 }}>
          {audit
            ? "Detailed summary not yet available for this audit. Select a more recent document or re-run the analysis."
            : "No audits available. Upload a protocol to get started."}
        </p>
      </div>
    );
  }

  const { summary } = audit;

  return (
    <div className="right-panel-card">
      <h2 style={{ fontFamily: "var(--font-display)", fontSize: 19, fontWeight: 700, marginBottom: 4 }}>
        Recent Summary
      </h2>

      {/* Document title */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 14 }}>
        <span style={{ fontWeight: 700, fontSize: 14 }}>Most Recent Document</span>
        <DownloadIcon />
      </div>

      {/* Regulation badge */}
      <div style={{ display: "flex", alignItems: "center", marginBottom: 16, fontSize: 13 }}>
        <StatusDot status="warning" />
        <span style={{ fontWeight: 600 }}>{summary.regulation}</span>
      </div>

      {/* Focus */}
      <Section title="Regulatory Focus">
        <p style={proseStyle}>{summary.focus}</p>
      </Section>

      {/* Retrieved Sections */}
      <Section title="Retrieved Protocol Sections">
        <ul style={listStyle}>
          {summary.retrievedSections.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </Section>

      {/* Query description */}
      <div
        style={{
          fontSize: 12,
          color: "rgba(74,65,112,0.6)",
          lineHeight: 1.65,
          marginBottom: 16,
          padding: "10px 12px",
          background: "rgba(124,111,191,0.05)",
          borderRadius: "var(--radius-sm)",
          borderLeft: "3px solid rgba(124,111,191,0.2)",
        }}
      >
        {summary.queryDescription}
      </div>

      {/* Gaps */}
      <Section title="Identified Gap">
        <ul style={listStyle}>
          {summary.gaps.map((g, i) => (
            <li key={i} style={{ marginBottom: 4 }}>{g}</li>
          ))}
        </ul>
      </Section>

      {/* Remediation */}
      <Section title="Recommended Remediation">
        <ul style={listStyle}>
          {summary.remediation.map((r, i) => (
            <li key={i} style={{ marginBottom: 4 }}>{r}</li>
          ))}
        </ul>
      </Section>
    </div>
  );
}

// ─── Sub-components ──────────────────────────────────────────

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontWeight: 700, fontSize: 13, textDecoration: "underline", marginBottom: 4 }}>
        {title}:
      </div>
      {children}
    </div>
  );
}

const proseStyle = {
  fontSize: 12.5,
  color: "rgba(74,65,112,0.75)",
  lineHeight: 1.6,
  margin: 0,
};

const listStyle = {
  paddingLeft: 18,
  fontSize: 12.5,
  color: "rgba(74,65,112,0.75)",
  lineHeight: 1.8,
};
