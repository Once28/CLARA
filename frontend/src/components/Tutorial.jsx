import React, { useState, useEffect } from "react";

const STEPS = [
  {
    id: "welcome",
    title: "Welcome to CLARA",
    description:
      "CLARA is your AI-powered clinical trial compliance assistant. It audits protocol documents against FDA and HHS regulations using reversed RAG — the protocol is the knowledge base, and regulations are the queries.",
    target: null,
    placement: "center",
  },
  {
    id: "upload",
    title: "Upload a Protocol",
    description:
      "Click upload to add a clinical trial protocol PDF. CLARA chunks and embeds the protocol, then queries each selected CFR regulation against it to find what's covered and what's missing.",
    target: "[data-tutorial='upload']",
    placement: "bottom",
  },
  {
    id: "audit-cards",
    title: "Audit Cards",
    description:
      "Each uploaded protocol becomes an audit card showing its overall compliance score and worst-case regulation status. Click any card to load the full regulatory breakdown on the right.",
    target: "[data-tutorial='audit-cards']",
    placement: "right",
  },
  {
    id: "score-chart",
    title: "Compliance Trend",
    description:
      "The trend chart tracks compliance scores across all your uploaded protocols. Use it to spot improvements between revisions or compare multiple studies side by side.",
    target: "[data-tutorial='score-chart']",
    placement: "left",
  },
  {
    id: "summary-panel",
    title: "Regulation Breakdown",
    description:
      "Each CFR regulation is listed individually as pass, warning, or critical. Expand any entry to see the specific gaps CLARA identified and the remediation steps it recommends.",
    target: "[data-tutorial='summary-panel']",
    placement: "left",
  },
  {
    id: "sidebar",
    title: "Protocol Navigator",
    description:
      "The sidebar lists all your uploaded protocols with a status indicator. Collapse it to gain screen space or expand to switch between protocols quickly.",
    target: "[data-tutorial='sidebar']",
    placement: "right",
  },
  {
    id: "done",
    title: "You're all set",
    description:
      "Upload a protocol to run your first compliance audit. CLARA will check it against the FDA regulations you select and return a detailed, actionable report in seconds.",
    target: null,
    placement: "center",
  },
];

const TOOLTIP_W = 300;
const PAD = 14; // viewport padding
const SPOT = 8; // spotlight padding around element
const ARROW = 12; // gap between element and tooltip

function useElementRect(selector, stepIndex) {
  const [rect, setRect] = useState(null);

  useEffect(() => {
    if (!selector) {
      setRect(null);
      return;
    }
    const update = () => {
      const el = document.querySelector(selector);
      setRect(el ? el.getBoundingClientRect() : null);
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [selector, stepIndex]);

  return rect;
}

function tooltipPosition(rect, placement) {
  if (!rect || placement === "center") {
    return {
      position: "fixed",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
    };
  }

  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const clampX = (x) => Math.min(Math.max(x, PAD), vw - TOOLTIP_W - PAD);
  const clampY = (y) => Math.min(Math.max(y, PAD), vh - 260);

  switch (placement) {
    case "bottom":
      return {
        position: "fixed",
        top: rect.bottom + ARROW,
        left: clampX(rect.left + rect.width / 2 - TOOLTIP_W / 2),
      };
    case "top":
      return {
        position: "fixed",
        top: clampY(rect.top - 260 - ARROW),
        left: clampX(rect.left + rect.width / 2 - TOOLTIP_W / 2),
      };
    case "right":
      return {
        position: "fixed",
        top: clampY(rect.top + rect.height / 2 - 110),
        left: Math.min(rect.right + ARROW, vw - TOOLTIP_W - PAD),
      };
    case "left":
      return {
        position: "fixed",
        top: clampY(rect.top + rect.height / 2 - 110),
        left: clampX(rect.left - TOOLTIP_W - ARROW),
      };
    default:
      return {};
  }
}

export default function Tutorial({ open, onClose }) {
  const [stepIndex, setStepIndex] = useState(0);

  // Reset to first step whenever the tour opens
  useEffect(() => {
    if (open) setStepIndex(0);
  }, [open]);

  const step = STEPS[stepIndex];
  const rect = useElementRect(step.target, stepIndex);

  // Scroll target into view on each step
  useEffect(() => {
    if (!step.target) return;
    const el = document.querySelector(step.target);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [step.target, stepIndex]);

  if (!open) return null;

  const isFirst = stepIndex === 0;
  const isLast = stepIndex === STEPS.length - 1;
  const hasSpotlight = !!rect;

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 9000, pointerEvents: "none" }}>
      {/* Backdrop — full screen for center steps, transparent for spotlight steps */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: hasSpotlight ? "transparent" : "rgba(20,16,48,0.55)",
          backdropFilter: hasSpotlight ? "none" : "blur(4px)",
          WebkitBackdropFilter: hasSpotlight ? "none" : "blur(4px)",
          pointerEvents: "auto",
          transition: "background 0.3s ease",
        }}
        onClick={onClose}
      />

      {/* Spotlight: transparent element whose box-shadow darkens everything around it */}
      {hasSpotlight && (
        <div
          style={{
            position: "fixed",
            top: rect.top - SPOT,
            left: rect.left - SPOT,
            width: rect.width + SPOT * 2,
            height: rect.height + SPOT * 2,
            borderRadius: 14,
            boxShadow: "0 0 0 9999px rgba(20,16,48,0.55)",
            border: "1.5px solid rgba(255,255,255,0.28)",
            pointerEvents: "none",
            transition: "all 0.3s cubic-bezier(0.25,0.46,0.45,0.94)",
            zIndex: 9001,
          }}
        />
      )}

      {/* Tooltip card */}
      <div
        key={stepIndex} // remount to retrigger animation on step change
        style={{
          ...tooltipPosition(rect, step.placement),
          width: TOOLTIP_W,
          background: "rgba(248,246,255,0.94)",
          backdropFilter: "blur(40px) saturate(1.8)",
          WebkitBackdropFilter: "blur(40px) saturate(1.8)",
          border: "1px solid rgba(255,255,255,0.78)",
          borderRadius: "var(--radius-lg)",
          padding: "20px 20px 16px",
          boxShadow:
            "0 20px 60px rgba(20,16,48,0.22), 0 4px 16px rgba(20,16,48,0.10), inset 0 1px 0 rgba(255,255,255,0.95)",
          pointerEvents: "auto",
          zIndex: 9002,
          animation: "modalSlide 0.25s cubic-bezier(0.16,1,0.3,1) forwards",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Progress dots + close */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 14,
          }}
        >
          <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
            {STEPS.map((_, i) => (
              <div
                key={i}
                style={{
                  width: i === stepIndex ? 18 : 6,
                  height: 6,
                  borderRadius: 3,
                  background: i === stepIndex ? "var(--purple)" : "rgba(124,111,191,0.2)",
                  transition: "all 0.25s ease",
                }}
              />
            ))}
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-faint)",
              fontSize: 20,
              lineHeight: 1,
              padding: "0 2px",
              display: "flex",
              alignItems: "center",
              transition: "color 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-faint)")}
          >
            ×
          </button>
        </div>

        {/* Step counter label */}
        <div
          style={{
            fontSize: 10,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.8px",
            color: "var(--text-faint)",
            marginBottom: 6,
          }}
        >
          {stepIndex + 1} / {STEPS.length}
        </div>

        {/* Title */}
        <h3
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 16,
            fontWeight: 700,
            color: "var(--text-primary)",
            marginBottom: 8,
            lineHeight: 1.3,
          }}
        >
          {step.title}
        </h3>

        {/* Description */}
        <p
          style={{
            fontSize: 13,
            lineHeight: 1.65,
            color: "var(--text-secondary)",
            marginBottom: 18,
          }}
        >
          {step.description}
        </p>

        {/* Controls */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          {isFirst ? (
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: 13,
                color: "var(--text-muted)",
                padding: "6px 0",
                transition: "color 0.15s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
            >
              Skip tour
            </button>
          ) : (
            <button
              className="btn-outline"
              onClick={() => setStepIndex((i) => i - 1)}
              style={{ padding: "6px 16px", fontSize: 13 }}
            >
              Back
            </button>
          )}

          <button
            className="btn-primary"
            onClick={() => {
              if (isLast) onClose();
              else setStepIndex((i) => i + 1);
            }}
            style={{ padding: "6px 20px", fontSize: 13 }}
          >
            {isLast ? "Get started" : "Next →"}
          </button>
        </div>
      </div>
    </div>
  );
}
