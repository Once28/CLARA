import React from "react";

// Status indicator dot (critical / warning / pass)
export function StatusDot({ status, size = 13 }) {
  const colors = {
    critical: "var(--critical)",
    warning: "var(--warning)",
    pass: "var(--pass)",
  };
  return (
    <span
      style={{
        display: "inline-block",
        width: size,
        height: size,
        borderRadius: "50%",
        border: `2.5px solid ${colors[status] || "#999"}`,
        marginRight: 10,
        flexShrink: 0,
        marginTop: 2,
      }}
    />
  );
}

// Download icon
export function DownloadIcon({ size = 16 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      style={{ marginLeft: 8, cursor: "pointer", opacity: 0.6, transition: "opacity 0.2s" }}
      onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
      onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.6")}
    >
      <path
        d="M8 1v10M8 11l-3-3M8 11l3-3M2 14h12"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// Status legend row
export function StatusLegend() {
  return (
    <div style={{ marginTop: 12, display: "flex", gap: 16, fontSize: 11.5, color: "var(--text-muted)" }}>
      <span>
        <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", border: "2px solid var(--critical)", marginRight: 6 }} />
        Critical
      </span>
      <span>
        <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", border: "2px solid var(--warning)", marginRight: 6 }} />
        Warning
      </span>
      <span>
        <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", border: "2px solid var(--pass)", marginRight: 6 }} />
        Requirements Met
      </span>
    </div>
  );
}

// Format date string to readable format
export function formatDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
}
