import React, { useState } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import AuditCard from "./components/AuditCard";
import ScoreChart from "./components/ScoreChart";
import SummaryPanel from "./components/SummaryPanel";
import UploadModal from "./components/UploadModal";
import { useAudits } from "./hooks/useAudits";
import "./styles/global.css";

export default function App() {
  const {
    audits,
    selectedId,
    selectedAudit,
    scoreHistory,
    loading,
    uploading,
    error,
    setSelectedId,
    uploadProtocol,
    clearAll,
  } = useAudits();

  const [showUpload, setShowUpload] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* ── Sidebar ── */}
      <Sidebar
        audits={audits}
        selectedId={selectedId}
        onSelect={setSelectedId}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((c) => !c)}
        onUploadClick={() => setShowUpload(true)}
      />

      {/* ── Main content area ── */}
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <Header
          onUploadClick={() => setShowUpload(true)}
          onCreateClick={() => setShowUpload(true)}
          onClearAll={clearAll}
        />

        {/* Error banner */}
        {error && (
          <div style={{
            margin: "0 36px 12px",
            padding: "10px 16px",
            background: "rgba(232,69,60,0.08)",
            border: "1px solid rgba(232,69,60,0.2)",
            borderRadius: "var(--radius-sm)",
            fontSize: 13,
            color: "var(--critical)",
          }}>
            {error}
          </div>
        )}

        {/* Main two-panel layout */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 380px",
            gap: 24,
            padding: "0 36px 36px",
            flex: 1,
            minHeight: 0,
          }}
        >
          {/* ── Left Panel: Audit Cards ── */}
          <div className="scroll-panel" style={{ overflowY: "auto", paddingRight: 8 }}>
            {loading ? (
              <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text-muted)" }}>
                Loading audits...
              </div>
            ) : audits.length === 0 ? (
              <div
                style={{
                  textAlign: "center",
                  padding: "80px 40px",
                  background: "var(--card-bg)",
                  borderRadius: "var(--radius-lg)",
                  border: "1px solid var(--card-border)",
                }}
              >
                <div style={{ fontSize: 15, color: "var(--text-secondary)", marginBottom: 16 }}>
                  No audits yet. Upload a protocol to get started.
                </div>
                <button className="btn-primary" onClick={() => setShowUpload(true)}>
                  Upload your first protocol
                </button>
              </div>
            ) : (
              audits.map((audit, i) => (
                <div
                  key={audit.id}
                  className="stagger-in"
                  style={{ animationDelay: `${i * 0.08}s` }}
                >
                  <AuditCard
                    audit={audit}
                    isActive={selectedId === audit.id}
                    onClick={setSelectedId}
                  />
                </div>
              ))
            )}
          </div>

          {/* ── Right Panel: Chart + Summary ── */}
          <div className="scroll-panel" style={{ overflowY: "auto", paddingRight: 4 }}>
            {/* Score chart */}
            {scoreHistory.length > 0 && (
              <div
                className="stagger-in right-panel-card"
                style={{
                  animationDelay: "0.15s",
                  background: "var(--card-bg)",
                  backdropFilter: "blur(12px)",
                  border: "1px solid var(--card-border)",
                  borderRadius: "var(--radius-lg)",
                  padding: "24px 26px",
                  marginBottom: 16,
                  boxShadow: "0 2px 12px rgba(107,98,160,0.06)",
                }}
              >
                <h2 style={{ fontFamily: "var(--font-display)", fontSize: 19, fontWeight: 700, marginBottom: 16 }}>
                  Latest Protocol Scores
                </h2>
                <ScoreChart data={scoreHistory} />
              </div>
            )}

            {/* Summary insights */}
            <div className="stagger-in" style={{ animationDelay: "0.25s" }}>
              <SummaryPanel audit={selectedAudit} />
            </div>
          </div>
        </div>
      </div>

      {/* Upload modal */}
      <UploadModal
        open={showUpload}
        onClose={() => setShowUpload(false)}
        onUpload={uploadProtocol}
        uploading={uploading}
      />
    </div>
  );
}
