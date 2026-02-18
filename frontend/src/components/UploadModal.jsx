import React, { useState, useRef } from "react";

const REGULATIONS = [
  { label: "21 CFR Part 11", active: true },
  { label: "21 CFR Part 50", active: true },
  { label: "21 CFR Part 56", active: true },
  { label: "ICH-GCP", active: false },
  { label: "EMA", active: false },
];

export default function UploadModal({ open, onClose, onUpload, uploading }) {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [metadata, setMetadata] = useState({
    title: "",
    nctId: "",
    phase: "",
    therapeuticArea: "",
  });
  const fileInputRef = useRef(null);

  if (!open) return null;

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === "application/pdf") {
      setFile(droppedFile);
    }
  };

  const handleFileSelect = (e) => {
    const selected = e.target.files[0];
    if (selected) setFile(selected);
  };

  const handleSubmit = async () => {
    if (!file) return;
    try {
      await onUpload(file, metadata);
      // Reset and close
      setFile(null);
      setMetadata({ title: "", nctId: "", phase: "", therapeuticArea: "" });
      onClose();
    } catch {
      // Error handled by parent hook
    }
  };

  const updateMeta = (key, value) =>
    setMetadata((prev) => ({ ...prev, [key]: value }));

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(44,38,80,0.35)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        animation: "fadeIn 0.2s ease",
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "white",
          borderRadius: "var(--radius-xl)",
          padding: 40,
          width: 480,
          maxWidth: "90vw",
          boxShadow: "0 24px 64px rgba(44,38,80,0.2)",
          animation: "modalSlide 0.3s ease",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
          <h2 style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700 }}>
            Upload Protocol
          </h2>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: 22, color: "#999", lineHeight: 1 }}
          >
            ×
          </button>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? "rgba(124,111,191,0.6)" : "rgba(124,111,191,0.35)"}`,
            borderRadius: 14,
            padding: file ? "24px" : "48px 24px",
            textAlign: "center",
            transition: "all 0.25s ease",
            cursor: "pointer",
            background: dragOver ? "rgba(232,226,244,0.4)" : "rgba(232,226,244,0.2)",
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            style={{ display: "none" }}
          />

          {file ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="var(--purple)" strokeWidth="2" />
                <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="var(--purple)" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <span style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)" }}>
                {file.name}
              </span>
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                ({(file.size / 1024 / 1024).toFixed(1)} MB)
              </span>
            </div>
          ) : (
            <>
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" style={{ margin: "0 auto 12px", display: "block", opacity: 0.4 }}>
                <path d="M12 16V4M12 4l-4 4M12 4l4 4M4 20h16" stroke="var(--purple-dark)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <div style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 6 }}>
                Drag & drop your protocol PDF here
              </div>
              <div style={{ fontSize: 12, color: "var(--text-faint)" }}>
                or click to browse · PDF files only
              </div>
            </>
          )}
        </div>

        {/* Metadata fields */}
        <div style={{ marginTop: 24, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {[
            { label: "Protocol Title", key: "title" },
            { label: "NCT ID", key: "nctId" },
            { label: "Phase", key: "phase" },
            { label: "Therapeutic Area", key: "therapeuticArea" },
          ].map(({ label, key }) => (
            <div key={key}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 5 }}>
                {label}
              </div>
              <input
                type="text"
                placeholder={label}
                value={metadata[key]}
                onChange={(e) => updateMeta(key, e.target.value)}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  border: "1.5px solid rgba(124,111,191,0.2)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: 13,
                  fontFamily: "var(--font-body)",
                  color: "var(--text-primary)",
                  background: "rgba(232,226,244,0.15)",
                  outline: "none",
                  transition: "border-color 0.2s",
                }}
                onFocus={(e) => (e.target.style.borderColor = "rgba(124,111,191,0.5)")}
                onBlur={(e) => (e.target.style.borderColor = "rgba(124,111,191,0.2)")}
              />
            </div>
          ))}
        </div>

        {/* Regulation scope */}
        <div style={{ marginTop: 20, marginBottom: 24 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 8 }}>
            Audit Against
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {REGULATIONS.map((reg) => (
              <span
                key={reg.label}
                style={{
                  padding: "5px 12px",
                  borderRadius: 20,
                  fontSize: 12,
                  fontWeight: 500,
                  border: `1.5px solid ${reg.active ? "rgba(124,111,191,0.4)" : "rgba(124,111,191,0.15)"}`,
                  color: reg.active ? "#4A4170" : "rgba(74,65,112,0.35)",
                  background: reg.active ? "rgba(124,111,191,0.08)" : "transparent",
                  cursor: reg.active ? "pointer" : "default",
                }}
              >
                {reg.label}
                {!reg.active && <span style={{ fontSize: 10, marginLeft: 4 }}>soon</span>}
              </span>
            ))}
          </div>
        </div>

        {/* Submit */}
        <button
          className="btn-primary"
          disabled={!file || uploading}
          onClick={handleSubmit}
          style={{
            width: "100%",
            justifyContent: "center",
            padding: "13px",
            fontSize: 15,
            opacity: !file || uploading ? 0.6 : 1,
            cursor: !file || uploading ? "not-allowed" : "pointer",
          }}
        >
          {uploading ? "Running Audit..." : "Run Regulatory Audit"}
        </button>
      </div>
    </div>
  );
}
