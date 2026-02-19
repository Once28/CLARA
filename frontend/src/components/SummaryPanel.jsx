import React, { useState } from "react";
import { StatusDot, DownloadIcon } from "./ui";

export default function SummaryPanel({ audit }) {
  const [expandedIdx, setExpandedIdx] = useState(null);

  if (!audit || !audit.breakdown || audit.breakdown.length === 0) {
    return (
      <div className="right-panel-card">
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 19, fontWeight: 700, marginBottom: 8 }}>
          Audit Summary
        </h2>
        <p style={{ fontSize: 13, color: "var(--text-muted)", lineHeight: 1.6 }}>
          {audit
            ? "Detailed summary not yet available for this audit. Select a more recent document or re-run the analysis."
            : "No audits available. Upload a protocol to get started."}
        </p>
      </div>
    );
  }

  const hasDetailedBreakdown = audit.breakdown.some((b) => b.gaps || b.remediation);

  return (
    <div className="right-panel-card">
      <h2 style={{ fontFamily: "var(--font-display)", fontSize: 19, fontWeight: 700, marginBottom: 4 }}>
        Audit Summary
      </h2>

      {/* Document title */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16 }}>
        <span style={{ fontWeight: 700, fontSize: 14 }}>{audit.filename}</span>
        <DownloadIcon />
      </div>

      {/* Retrieved Sections */}
      {audit.retrievedSections && audit.retrievedSections.length > 0 && (
        <Section title="Retrieved Protocol Sections">
          <ul style={listStyle}>
            {audit.retrievedSections.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </Section>
      )}

      {/* Query description */}
      {audit.queryDescription && (
        <div
          style={{
            fontSize: 12,
            color: "rgba(74,65,112,0.6)",
            lineHeight: 1.65,
            marginBottom: 20,
            padding: "10px 12px",
            background: "rgba(124,111,191,0.05)",
            borderRadius: "var(--radius-sm)",
            borderLeft: "3px solid rgba(124,111,191,0.2)",
          }}
        >
          {audit.queryDescription}
        </div>
      )}

      {/* Regulation breakdowns */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {audit.breakdown.map((item, idx) => {
          const isExpanded = expandedIdx === idx;
          const hasDetail = hasDetailedBreakdown && (item.gaps?.length > 0 || item.remediation?.length > 0 || item.focus);
          const statusColors = { critical: "var(--critical)", warning: "var(--warning)", pass: "var(--pass)" };
          const statusLabels = { critical: "Critical", warning: "Warning", pass: "Pass" };
          const statusBg = { critical: "rgba(232,69,60,0.06)", warning: "rgba(240,160,48,0.06)", pass: "rgba(60,179,113,0.06)" };

          return (
            <div
              key={idx}
              style={{
                border: `1.5px solid ${isExpanded ? statusColors[item.status] : "rgba(124,111,191,0.15)"}`,
                borderRadius: "var(--radius-md)",
                background: isExpanded ? statusBg[item.status] : "rgba(255,255,255,0.5)",
                overflow: "hidden",
                transition: "all 0.25s ease",
              }}
            >
              {/* Header - always visible */}
              <div
                onClick={() => hasDetail && setExpandedIdx(isExpanded ? null : idx)}
                style={{
                  display: "flex", alignItems: "flex-start", gap: 10,
                  padding: "12px 14px",
                  cursor: hasDetail ? "pointer" : "default",
                }}
              >
                <StatusDot status={item.status} size={12} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>
                      {item.regulation}
                    </span>
                    <span style={{
                      fontSize: 11, fontWeight: 600, flexShrink: 0,
                      padding: "2px 8px", borderRadius: 10,
                      color: statusColors[item.status],
                      background: statusBg[item.status],
                      border: `1px solid ${statusColors[item.status]}`,
                    }}>
                      {statusLabels[item.status]}
                    </span>
                  </div>
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5, marginTop: 4 }}>
                    {item.note}
                  </p>
                  {hasDetail && (
                    <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 6, display: "flex", alignItems: "center", gap: 4 }}>
                      <span style={{
                        display: "inline-block", transition: "transform 0.2s",
                        transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
                      }}>▸</span>
                      {isExpanded ? "Hide details" : "View gaps & remediation"}
                    </div>
                  )}
                </div>
              </div>

              {/* Expanded detail */}
              {isExpanded && hasDetail && (
                <div style={{
                  padding: "0 14px 14px",
                  borderTop: "1px solid rgba(124,111,191,0.1)",
                  animation: "fadeSlideIn 0.25s ease",
                }}>
                  {item.focus && (
                    <div style={{ marginTop: 12 }}>
                      <SubSection title="Regulatory Focus">
                        <p style={proseStyle}>{item.focus}</p>
                      </SubSection>
                    </div>
                  )}

                  {item.gaps && item.gaps.length > 0 && (
                    <SubSection title="Identified Gaps">
                      <ul style={listStyle}>
                        {item.gaps.map((g, i) => (
                          <li key={i} style={{ marginBottom: 3 }}>{g}</li>
                        ))}
                      </ul>
                    </SubSection>
                  )}

                  {item.remediation && item.remediation.length > 0 && (
                    <SubSection title="Recommended Remediation">
                      <ul style={listStyle}>
                        {item.remediation.map((r, i) => (
                          <li key={i} style={{ marginBottom: 3 }}>{r}</li>
                        ))}
                      </ul>
                    </SubSection>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
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

function SubSection({ title, children }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontWeight: 700, fontSize: 12, color: "var(--text-muted)", marginBottom: 3 }}>
        {title}:
      </div>
      {children}
    </div>
  );
}

const proseStyle = {
  fontSize: 12,
  color: "rgba(74,65,112,0.75)",
  lineHeight: 1.6,
  margin: 0,
};

const listStyle = {
  paddingLeft: 18,
  fontSize: 12,
  color: "rgba(74,65,112,0.75)",
  lineHeight: 1.7,
};
