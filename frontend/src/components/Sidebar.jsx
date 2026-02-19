import React from "react";
import { StatusDot } from "./ui";

const STATUS_PRIORITY = { critical: 0, warning: 1, pass: 2 };

function getWorstStatus(breakdown) {
  if (!breakdown || breakdown.length === 0) return null;
  return breakdown.reduce((worst, item) => {
    if ((STATUS_PRIORITY[item.status] ?? 9) < (STATUS_PRIORITY[worst] ?? 9)) return item.status;
    return worst;
  }, "pass");
}

export default function Sidebar({ audits, selectedId, onSelect, collapsed, onToggle, onUploadClick }) {
  return (
    <div
      className="sidebar liquid-glass"
      style={{
        width: collapsed ? 56 : 260,
        minWidth: collapsed ? 56 : 260,
        height: "100vh",
        background: "rgba(255, 255, 255, 0.3)",
        backdropFilter: "blur(40px) saturate(1.8)",
        WebkitBackdropFilter: "blur(40px) saturate(1.8)",
        borderRight: "1px solid rgba(255, 255, 255, 0.4)",
        display: "flex",
        flexDirection: "column",
        transition: "width 0.3s cubic-bezier(0.25,0.46,0.45,0.94), min-width 0.3s cubic-bezier(0.25,0.46,0.45,0.94)",
        overflow: "hidden",
        position: "sticky",
        top: 0,
        zIndex: 60,
        boxShadow: "4px 0 24px rgba(107, 98, 160, 0.06), inset -1px 0 0 rgba(255,255,255,0.2)",
      }}
    >
      {/* Logo + collapse toggle */}
      <div style={{
        padding: collapsed ? "20px 10px" : "20px 20px",
        display: "flex",
        alignItems: "center",
        justifyContent: collapsed ? "center" : "space-between",
        borderBottom: "1px solid rgba(255, 255, 255, 0.35)",
        minHeight: 72,
      }}>
        {!collapsed && (
          <h1 style={{
            fontFamily: "'Montserrat', sans-serif",
            fontSize: 26,
            fontWeight: 800,
            letterSpacing: "3px",
            color: "var(--text-primary)",
            lineHeight: 1,
            whiteSpace: "nowrap",
          }}>
            CLARA.ai
          </h1>
        )}
        <button
          onClick={onToggle}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 6,
            borderRadius: "var(--radius-sm)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--text-muted)",
            transition: "background 0.15s, color 0.15s",
            flexShrink: 0,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(124,111,191,0.1)";
            e.currentTarget.style.color = "var(--text-primary)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "none";
            e.currentTarget.style.color = "var(--text-muted)";
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" style={{
            transition: "transform 0.3s",
            transform: collapsed ? "rotate(180deg)" : "rotate(0deg)",
          }}>
            <path d="M15 19l-7-7 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {/* Section heading */}
      {!collapsed && (
        <div style={{
          padding: "16px 20px 8px",
          fontSize: 11,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.8px",
          color: "var(--text-faint)",
        }}>
          Protocols
        </div>
      )}

      {/* Protocol list */}
      <div className="scroll-panel" style={{ flex: 1, overflowY: "auto", padding: collapsed ? "8px 6px" : "4px 10px" }}>
        {audits.map((audit) => {
          const isActive = selectedId === audit.id;
          const worstStatus = getWorstStatus(audit.breakdown);

          return (
            <div
              key={audit.id}
              onClick={() => onSelect(audit.id)}
              title={collapsed ? `${audit.filename} — Score: ${audit.score}` : undefined}
              style={{
                padding: collapsed ? "10px 6px" : "10px 12px",
                borderRadius: "var(--radius-sm)",
                cursor: "pointer",
                background: isActive ? "rgba(255, 255, 255, 0.45)" : "transparent",
                backdropFilter: isActive ? "blur(8px)" : "none",
                WebkitBackdropFilter: isActive ? "blur(8px)" : "none",
                borderLeft: isActive ? "3px solid var(--purple)" : "3px solid transparent",
                marginBottom: 2,
                transition: "all 0.2s ease",
                display: "flex",
                alignItems: collapsed ? "center" : "flex-start",
                justifyContent: collapsed ? "center" : "flex-start",
                gap: 10,
                boxShadow: isActive ? "0 2px 8px rgba(124,111,191,0.06), inset 0 1px 1px rgba(255,255,255,0.5)" : "none",
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.background = "rgba(255, 255, 255, 0.25)";
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.background = "transparent";
              }}
            >
              {/* Status indicator */}
              <div style={{ flexShrink: 0, marginTop: collapsed ? 0 : 2 }}>
                <StatusDot status={worstStatus} size={10} />
              </div>

              {/* Protocol details */}
              {!collapsed && (
                <div style={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
                  <div style={{
                    fontSize: 13,
                    fontWeight: isActive ? 700 : 500,
                    color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}>
                    {audit.filename.replace(/\.pdf$/i, "")}
                  </div>
                  <div style={{
                    fontSize: 11,
                    color: "var(--text-faint)",
                    marginTop: 2,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}>
                    <span>ID: {audit.id}</span>
                    <span>·</span>
                    <span style={{
                      fontWeight: 600,
                      color: audit.score >= 75 ? "var(--pass)" : audit.score >= 50 ? "var(--warning)" : "var(--critical)",
                    }}>
                      {audit.score}
                    </span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Upload button at bottom */}
      <div style={{
        padding: collapsed ? "12px 8px" : "12px 16px",
        borderTop: "1px solid rgba(255, 255, 255, 0.35)",
      }}>
        <button
          className="btn-primary"
          onClick={onUploadClick}
          style={{
            width: "100%",
            justifyContent: "center",
            padding: collapsed ? "10px" : "10px 16px",
            fontSize: collapsed ? 0 : 13,
            gap: collapsed ? 0 : 8,
          }}
          title="Upload protocol"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
            <path d="M8 11V1M8 1l-3 3M8 1l3 3M2 14h12" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {!collapsed && "Upload"}
        </button>
      </div>
    </div>
  );
}
