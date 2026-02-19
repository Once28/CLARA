import React, { useState, useRef, useEffect } from "react";

const REGULATIONS = [
  { id: "21_cfr_11",  label: "21 CFR Part 11",  desc: "Electronic Records & Signatures" },
  { id: "21_cfr_50",  label: "21 CFR Part 50",  desc: "Protection of Human Subjects" },
  { id: "21_cfr_56",  label: "21 CFR Part 56",  desc: "Institutional Review Boards" },
  { id: "21_cfr_58",  label: "21 CFR Part 58",  desc: "Good Laboratory Practice" },
  { id: "21_cfr_211", label: "21 CFR Part 211", desc: "cGMP for Pharmaceuticals" },
  { id: "21_cfr_312", label: "21 CFR Part 312", desc: "Investigational New Drug (IND)" },
  { id: "21_cfr_314", label: "21 CFR Part 314", desc: "NDA / ANDA Applications" },
  { id: "45_cfr_46",  label: "45 CFR Part 46",  desc: "HHS Common Rule" },
];

const LOADING_STEPS = [
  { label: "Uploading document", duration: 1200 },
  { label: "Parsing protocol sections", duration: 1800 },
  { label: "Querying regulatory knowledge base", duration: 2200 },
  { label: "Running compliance analysis", duration: 2400 },
  { label: "Generating audit report", duration: 1600 },
];

function LoadingView({ fileName, onComplete }) {
  const [activeStep, setActiveStep] = useState(0);
  const [stepProgress, setStepProgress] = useState(0);

  useEffect(() => {
    if (activeStep >= LOADING_STEPS.length) return;

    const duration = LOADING_STEPS[activeStep].duration;
    const interval = 30;
    let elapsed = 0;

    const timer = setInterval(() => {
      elapsed += interval;
      setStepProgress(Math.min((elapsed / duration) * 100, 100));
      if (elapsed >= duration) {
        clearInterval(timer);
        if (activeStep < LOADING_STEPS.length - 1) {
          setActiveStep((s) => s + 1);
          setStepProgress(0);
        }
      }
    }, interval);

    return () => clearInterval(timer);
  }, [activeStep]);

  return (
    <div style={{ textAlign: "center" }}>
      {/* Animated spinner */}
      <div style={{ margin: "0 auto 24px", width: 56, height: 56, position: "relative" }}>
        <svg width="56" height="56" viewBox="0 0 56 56" style={{ animation: "spin 1.8s linear infinite" }}>
          <circle cx="28" cy="28" r="24" fill="none" stroke="rgba(124,111,191,0.15)" strokeWidth="4" />
          <circle
            cx="28" cy="28" r="24" fill="none"
            stroke="var(--purple)" strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray="120 150"
            style={{ animation: "spin 1.8s linear infinite" }}
          />
        </svg>
      </div>

      <h3 style={{
        fontFamily: "var(--font-display)", fontSize: 18, fontWeight: 700,
        color: "var(--text-primary)", marginBottom: 6,
      }}>
        Analyzing Protocol
      </h3>
      <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 28 }}>
        {fileName}
      </p>

      {/* Step list */}
      <div style={{ textAlign: "left", maxWidth: 320, margin: "0 auto" }}>
        {LOADING_STEPS.map((step, i) => {
          const isComplete = i < activeStep;
          const isActive = i === activeStep;
          const isPending = i > activeStep;

          return (
            <div
              key={step.label}
              style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "10px 0",
                borderBottom: i < LOADING_STEPS.length - 1 ? "1px solid rgba(124,111,191,0.08)" : "none",
                opacity: isPending ? 0.35 : 1,
                transition: "opacity 0.4s ease",
              }}
            >
              {/* Icon */}
              <div style={{
                width: 24, height: 24, borderRadius: "50%", flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: isComplete ? "var(--pass)" : isActive ? "rgba(124,111,191,0.12)" : "rgba(124,111,191,0.06)",
                transition: "all 0.3s ease",
              }}>
                {isComplete ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                    <path d="M5 13l4 4L19 7" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : isActive ? (
                  <div style={{
                    width: 8, height: 8, borderRadius: "50%",
                    background: "var(--purple)",
                    animation: "pulse 1s ease-in-out infinite",
                  }} />
                ) : (
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: "rgba(124,111,191,0.2)" }} />
                )}
              </div>

              {/* Label + progress */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 13, fontWeight: isActive ? 600 : 400,
                  color: isComplete ? "var(--pass)" : isActive ? "var(--text-primary)" : "var(--text-muted)",
                  transition: "color 0.3s",
                }}>
                  {step.label}
                  {isComplete && " ✓"}
                </div>
                {isActive && (
                  <div style={{
                    marginTop: 5, height: 3, borderRadius: 2,
                    background: "rgba(124,111,191,0.1)", overflow: "hidden",
                  }}>
                    <div style={{
                      height: "100%", borderRadius: 2,
                      background: "var(--purple)",
                      width: `${stepProgress}%`,
                      transition: "width 0.05s linear",
                    }} />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <p style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 24 }}>
        This may take a moment — please don't close this window
      </p>
    </div>
  );
}

function SuccessView({ audit, onClose }) {
  return (
    <div style={{ textAlign: "center" }}>
      {/* Checkmark */}
      <div style={{
        width: 56, height: 56, borderRadius: "50%", margin: "0 auto 20px",
        background: "rgba(60,179,113,0.1)", display: "flex",
        alignItems: "center", justifyContent: "center",
        animation: "scaleIn 0.35s ease",
      }}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <path d="M5 13l4 4L19 7" stroke="var(--pass)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      <h3 style={{
        fontFamily: "var(--font-display)", fontSize: 18, fontWeight: 700,
        color: "var(--text-primary)", marginBottom: 6,
      }}>
        Audit Complete
      </h3>
      <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>
        Your protocol has been analyzed successfully.
      </p>

      {audit && (
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8,
          background: "rgba(124,111,191,0.06)", borderRadius: 12,
          padding: "10px 20px", marginBottom: 28,
        }}>
          <span style={{ fontSize: 28, fontWeight: 700, color: "var(--purple)", fontFamily: "var(--font-display)" }}>
            {audit.score}
          </span>
          <span style={{ fontSize: 12, color: "var(--text-muted)", textAlign: "left", lineHeight: 1.3 }}>
            Compliance<br />Score
          </span>
        </div>
      )}

      <button
        className="btn-primary"
        onClick={onClose}
        style={{ width: "100%", justifyContent: "center", padding: "13px", fontSize: 15 }}
      >
        View Audit Results
      </button>
    </div>
  );
}

export default function UploadModal({ open, onClose, onUpload, uploading }) {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [metadata, setMetadata] = useState({
    title: "",
    nctId: "",
    phase: "",
    therapeuticArea: "",
  });
  // 'form' | 'loading' | 'success'
  const [phase, setPhase] = useState("form");
  const [auditResult, setAuditResult] = useState(null);
  const [selectedRegs, setSelectedRegs] = useState(new Set(["21_cfr_11", "21_cfr_50", "21_cfr_56"]));
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
    setPhase("loading");
    try {
      const result = await onUpload(file, { ...metadata, regulations: [...selectedRegs].join(",") });
      setAuditResult(result);
      setPhase("success");
    } catch {
      // Error handled by parent hook — go back to form
      setPhase("form");
    }
  };

  const handleClose = () => {
    setFile(null);
    setMetadata({ title: "", nctId: "", phase: "", therapeuticArea: "" });
    setPhase("form");
    setAuditResult(null);
    onClose();
  };

  const updateMeta = (key, value) =>
    setMetadata((prev) => ({ ...prev, [key]: value }));

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(44,38,80,0.25)",
        backdropFilter: "blur(12px) saturate(1.4)",
        WebkitBackdropFilter: "blur(12px) saturate(1.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        animation: "fadeIn 0.2s ease",
      }}
      onClick={phase === "form" ? handleClose : undefined}
    >
      <div
        className="liquid-glass-heavy"
        style={{
          background: "rgba(255, 255, 255, 0.6)",
          backdropFilter: "blur(40px) saturate(1.8)",
          WebkitBackdropFilter: "blur(40px) saturate(1.8)",
          borderRadius: "var(--radius-xl)",
          padding: 40,
          width: 480,
          maxWidth: "90vw",
          boxShadow: "0 24px 80px rgba(44,38,80,0.15), 0 8px 32px rgba(107, 98, 160, 0.08), inset 0 1px 1px rgba(255, 255, 255, 0.7)",
          border: "1px solid rgba(255, 255, 255, 0.55)",
          borderTopColor: "rgba(255, 255, 255, 0.85)",
          animation: "modalSlide 0.3s ease",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Loading phase */}
        {phase === "loading" && (
          <LoadingView fileName={file?.name} />
        )}

        {/* Success phase */}
        {phase === "success" && (
          <SuccessView audit={auditResult} onClose={handleClose} />
        )}

        {/* Form phase */}
        {phase === "form" && <>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
          <h2 style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700 }}>
            Upload Protocol
          </h2>
          <button
            onClick={handleClose}
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
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)" }}>
              Regulation Requirements
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <button
                type="button"
                onClick={() => {
                  if (selectedRegs.size === REGULATIONS.length) {
                    setSelectedRegs(new Set());
                  } else {
                    setSelectedRegs(new Set(REGULATIONS.map((r) => r.id)));
                  }
                }}
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: "var(--purple)",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: 0,
                  textDecoration: "underline",
                  textUnderlineOffset: 2,
                  opacity: 0.8,
                  transition: "opacity 0.15s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.8")}
              >
                {selectedRegs.size === REGULATIONS.length ? "Deselect all" : "Select all"}
              </button>
              <div style={{ fontSize: 11, color: "var(--text-faint)" }}>
                {selectedRegs.size} of {REGULATIONS.length} selected
              </div>
            </div>
          </div>
          <div
            className="scroll-panel"
            style={{
              maxHeight: 152,
              overflowY: "auto",
              border: "1.5px solid rgba(124,111,191,0.15)",
              borderRadius: "var(--radius-sm)",
              background: "rgba(232,226,244,0.08)",
            }}
          >
            {REGULATIONS.map((reg, i) => {
              const isSelected = selectedRegs.has(reg.id);
              return (
                <div
                  key={reg.id}
                  onClick={() => {
                    setSelectedRegs((prev) => {
                      const next = new Set(prev);
                      if (next.has(reg.id)) next.delete(reg.id);
                      else next.add(reg.id);
                      return next;
                    });
                  }}
                  style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "9px 12px",
                    cursor: "pointer",
                    background: isSelected ? "rgba(124,111,191,0.06)" : "transparent",
                    borderBottom: i < REGULATIONS.length - 1 ? "1px solid rgba(124,111,191,0.08)" : "none",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = "rgba(124,111,191,0.04)"; }}
                  onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
                >
                  {/* Checkbox */}
                  <div style={{
                    width: 16, height: 16, borderRadius: 4, flexShrink: 0,
                    border: `1.5px solid ${isSelected ? "var(--purple)" : "rgba(124,111,191,0.3)"}`,
                    background: isSelected ? "var(--purple)" : "transparent",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    transition: "all 0.15s",
                  }}>
                    {isSelected && (
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                        <path d="M5 13l4 4L19 7" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </div>
                  {/* Label */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 12.5, fontWeight: isSelected ? 600 : 500,
                      color: isSelected ? "var(--text-primary)" : "var(--text-secondary)",
                    }}>
                      {reg.label}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 1 }}>
                      {reg.desc}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Submit */}
        <button
          className="btn-primary"
          disabled={!file || uploading || selectedRegs.size === 0}
          onClick={handleSubmit}
          style={{
            width: "100%",
            justifyContent: "center",
            padding: "13px",
            fontSize: 15,
            opacity: !file || uploading || selectedRegs.size === 0 ? 0.6 : 1,
            cursor: !file || uploading || selectedRegs.size === 0 ? "not-allowed" : "pointer",
          }}
        >
          Run Regulatory Audit
        </button>
        </>}
      </div>
    </div>
  );
}
