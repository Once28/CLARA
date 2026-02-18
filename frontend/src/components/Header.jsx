import React from "react";

export default function Header({ onUploadClick, onCreateClick }) {
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "20px 36px",
        position: "sticky",
        top: 0,
        zIndex: 50,
        background:
          "linear-gradient(180deg, rgba(232,226,244,0.95) 0%, rgba(232,226,244,0.0) 100%)",
        backdropFilter: "blur(8px)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
        <h1
          style={{
            fontFamily: "'Montserrat', sans-serif",
            fontSize: 48,
            fontWeight: 800,
            letterSpacing: "5px",
            color: "var(--text-primary)",
            lineHeight: 1,
          }}
        >
          CLARA.ai
        </h1>

        <button className="btn-outline" onClick={onCreateClick}>
          + create new
        </button>

        <button className="btn-primary" onClick={onUploadClick}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path
              d="M8 11V1M8 1l-3 3M8 1l3 3M2 14h12"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          upload
        </button>
      </div>

      {/* GitHub / Profile */}
      <a
        href="https://github.com/Once28/CLARA"
        target="_blank"
        rel="noopener noreferrer"
        style={{
          width: 40,
          height: 40,
          borderRadius: "50%",
          background: "rgba(45,38,80,0.08)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          transition: "background 0.2s",
          textDecoration: "none",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(45,38,80,0.14)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(45,38,80,0.08)")}
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="var(--text-primary)">
          <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.161 22 16.416 22 12c0-5.523-4.477-10-10-10z" />
        </svg>
      </a>
    </header>
  );
}
