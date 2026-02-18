import React from "react";

export default function ScoreChart({ data }) {
  if (!data || data.length === 0) return null;

  const maxScore = 100;
  const chartW = 280;
  const chartH = 140;
  const padL = 32;
  const padR = 16;
  const padT = 12;
  const padB = 20;
  const plotW = chartW - padL - padR;
  const plotH = chartH - padT - padB;

  const points = data.map((d, i) => ({
    x: padL + (data.length === 1 ? plotW / 2 : (i / (data.length - 1)) * plotW),
    y: padT + plotH - (d.score / maxScore) * plotH,
    score: d.score,
    label: d.label,
  }));

  const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const gridLines = [0, 25, 50, 75, 100];

  const dotColor = (score) =>
    score >= 80 ? "var(--pass)" : score >= 60 ? "var(--warning)" : "var(--critical)";

  return (
    <svg width={chartW} height={chartH} style={{ overflow: "visible" }}>
      <defs>
        <linearGradient id="scoreLineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#7C6FBF" />
          <stop offset="100%" stopColor="#5AA5B5" />
        </linearGradient>
      </defs>

      {/* Grid lines */}
      {gridLines.map((v) => {
        const y = padT + plotH - (v / maxScore) * plotH;
        return (
          <g key={v}>
            <line x1={padL} y1={y} x2={chartW - padR} y2={y} stroke="rgba(107,98,160,0.15)" strokeWidth="1" strokeDasharray="4 3" />
            <text x={padL - 8} y={y + 4} textAnchor="end" fill="rgba(107,98,160,0.55)" fontSize="11" fontFamily="var(--font-body)">
              {v}
            </text>
          </g>
        );
      })}

      {/* Line */}
      <path d={pathD} fill="none" stroke="url(#scoreLineGrad)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

      {/* Data points */}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="5.5" fill="white" stroke={dotColor(p.score)} strokeWidth="2.5" />
          <text x={p.x} y={chartH - 2} textAnchor="middle" fill="rgba(107,98,160,0.55)" fontSize="10" fontFamily="var(--font-body)">
            {p.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
