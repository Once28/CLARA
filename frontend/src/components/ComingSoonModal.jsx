import React from "react";

const PLANNED = [
  "AI-assisted section drafting",
  "Regulation-aware content suggestions",
  "Structured templates per study phase",
  "Export to PDF and Word",
];

export default function ComingSoonModal({ open, onClose }) {
  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 200,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(20,16,48,0.45)",
        backdropFilter: "blur(12px) saturate(1.4)",
        WebkitBackdropFilter: "blur(12px) saturate(1.4)",
      }}
      onClick={onClose}
    >
      <div
        className="liquid-glass-heavy"
        style={{
          width: 400,
          maxWidth: "90vw",
          borderRadius: "var(--radius-xl)",
          padding: "36px 32px",
          animation: "modalSlide 0.3s cubic-bezier(0.16,1,0.3,1) forwards",
          textAlign: "center",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Icon */}
        <div
          style={{
            width: 60,
            height: 60,
            borderRadius: "50%",
            background:
              "linear-gradient(135deg, rgba(124,111,191,0.12) 0%, rgba(107,98,160,0.22) 100%)",
            border: "1.5px solid rgba(124,111,191,0.25)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 20px",
          }}
        >
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
            <path
              d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"
              stroke="var(--purple)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path d="M12 20h9" stroke="var(--purple)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>

        {/* Title */}
        <h2
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 21,
            fontWeight: 700,
            color: "var(--text-primary)",
            marginBottom: 10,
          }}
        >
          Protocol Builder
        </h2>

        {/* Badge */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "4px 12px",
            background: "rgba(124,111,191,0.10)",
            border: "1px solid rgba(124,111,191,0.22)",
            borderRadius: 20,
            fontSize: 11,
            fontWeight: 700,
            color: "var(--purple)",
            marginBottom: 16,
            letterSpacing: "0.5px",
            textTransform: "uppercase",
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "var(--purple)",
              display: "inline-block",
              animation: "pulse 1.8s ease-in-out infinite",
            }}
          />
          Coming Soon
        </div>

        <p
          style={{
            fontSize: 14,
            lineHeight: 1.65,
            color: "var(--text-secondary)",
            marginBottom: 20,
          }}
        >
          Build clinical trial protocols from scratch with AI-assisted drafting, structured
          section templates, and real-time regulatory guidance — all without leaving CLARA.
        </p>

        {/* Planned features */}
        <div
          style={{
            background: "rgba(255,255,255,0.5)",
            border: "1px solid rgba(255,255,255,0.7)",
            borderRadius: "var(--radius-md)",
            padding: "14px 18px",
            marginBottom: 24,
            textAlign: "left",
          }}
        >
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.9px",
              color: "var(--text-faint)",
              marginBottom: 10,
            }}
          >
            Planned features
          </div>
          {PLANNED.map((feature, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                marginBottom: i < PLANNED.length - 1 ? 9 : 0,
              }}
            >
              <div
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: "50%",
                  background: "rgba(124,111,191,0.45)",
                  flexShrink: 0,
                }}
              />
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{feature}</span>
            </div>
          ))}
        </div>

        <button
          className="btn-primary"
          onClick={onClose}
          style={{ width: "100%", justifyContent: "center" }}
        >
          Got it
        </button>
      </div>
    </div>
  );
}
