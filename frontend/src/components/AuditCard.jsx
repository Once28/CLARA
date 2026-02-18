import React from "react";
import { StatusDot, DownloadIcon, StatusLegend, formatDate } from "./ui";

export default function AuditCard({ audit, isActive, onClick }) {
  const scoreColor =
    audit.score >= 80 ? "var(--pass)" : audit.score >= 60 ? "#D4930D" : "var(--critical)";

  return (
    <div
      className={`clara-card ${isActive ? "active" : ""}`}
      onClick={() => onClick(audit.id)}
      style={{
        background: isActive ? "var(--card-bg-active)" : "var(--card-bg)",
        backdropFilter: "blur(12px)",
        border: `1px solid ${isActive ? "var(--card-border-active)" : "var(--card-border)"}`,
        borderRadius: "var(--radius-lg)",
        padding: "24px 28px",
        marginBottom: 16,
        cursor: "pointer",
        transition: "all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)",
        boxShadow: isActive
          ? "0 4px 20px rgba(124,111,191,0.14), inset 0 0 0 1px rgba(124,111,191,0.1)"
          : "0 2px 12px rgba(107,98,160,0.06)",
      }}
      onMouseEnter={(e) => {
        if (!isActive) {
          e.currentTarget.style.background = "var(--card-bg-hover)";
          e.currentTarget.style.boxShadow = "0 6px 24px rgba(107,98,160,0.12)";
          e.currentTarget.style.transform = "translateY(-1px)";
        }
      }}
      onMouseLeave={(e) => {
        if (!isActive) {
          e.currentTarget.style.background = "var(--card-bg)";
          e.currentTarget.style.boxShadow = "0 2px 12px rgba(107,98,160,0.06)";
          e.currentTarget.style.transform = "translateY(0)";
        }
      }}
    >
      {/* Header row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center" }}>
            <span style={{ fontWeight: 700, fontSize: 18, letterSpacing: "-0.2px" }}>
              {audit.filename}
            </span>
            <DownloadIcon />
          </div>
          <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 3 }}>
            Uploaded - {formatDate(audit.uploadDate)}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 13 }}>
            <span style={{ fontWeight: 600 }}>Approval Status: </span>
            <span style={{ color: audit.approvalStatus === "not approved" ? "var(--critical)" : "var(--pass)" }}>
              {audit.approvalStatus}
            </span>
          </div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
            <span style={{ fontWeight: 600 }}>Phase: </span>
            {audit.phase}
          </div>
        </div>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: "rgba(124,111,191,0.12)", margin: "14px 0 16px" }} />

      {/* Score */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 12 }}>
        <span style={{ fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700 }}>
          Protocol Score
        </span>
        <span style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-display)", color: scoreColor }}>
          {audit.score}
        </span>
      </div>

      {/* Breakdown */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 32px" }}>
        <div style={{ fontSize: 13, fontStyle: "italic", color: "var(--text-muted)", textDecoration: "underline", marginBottom: 6 }}>
          breakdown
        </div>
        <div style={{ fontSize: 13, fontStyle: "italic", color: "var(--text-muted)", textDecoration: "underline", marginBottom: 6 }}>
          steps to improve
        </div>
        {audit.breakdown.map((item, j) => (
          <React.Fragment key={j}>
            <div style={{ display: "flex", alignItems: "flex-start", fontSize: 13.5, lineHeight: 1.5, marginBottom: 6 }}>
              <StatusDot status={item.status} />
              <span>{item.regulation}</span>
            </div>
            <div style={{ fontSize: 13, color: "rgba(74,65,112,0.7)", lineHeight: 1.5, marginBottom: 6 }}>
              {item.note}
            </div>
          </React.Fragment>
        ))}
      </div>

      <StatusLegend />
    </div>
  );
}
