import React from 'react';

export const SidebarBottomWave: React.FC = () => {
  return (
    <div
      className="absolute bottom-0 left-0 right-0 h-44 pointer-events-none select-none overflow-hidden z-0"
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 260 176"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full object-cover"
        preserveAspectRatio="none"
      >
        <defs>
          {/* Deep Navy to Peacock Teal Gradient */}
          <linearGradient id="sbWaveGrad1" x1="100%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#009F98" stopOpacity="0.4" />
            <stop offset="60%" stopColor="#007D78" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#0A2036" stopOpacity="0" />
          </linearGradient>

          {/* Foreground Flowing Teal Gradient */}
          <linearGradient id="sbWaveGrad2" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#086E73" stopOpacity="0.6" />
            <stop offset="50%" stopColor="#009F98" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#39C3B8" stopOpacity="0.1" />
          </linearGradient>

          {/* Cyan Curve Stroke Highlight */}
          <linearGradient id="sbStrokeGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#39C3B8" stopOpacity="0.6" />
            <stop offset="80%" stopColor="#009F98" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#102C46" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Base Layer Curve */}
        <path
          d="M0 176 L260 176 L260 70 C200 40, 140 130, 0 80 Z"
          fill="url(#sbWaveGrad1)"
        />

        {/* Foreground Curve rising from right towards left */}
        <path
          d="M0 176 L260 176 L260 110 C180 60, 90 140, 0 100 Z"
          fill="url(#sbWaveGrad2)"
        />

        {/* Flowing Accent Strokes */}
        <path
          d="M0 100 C90 140, 180 60, 260 110"
          stroke="url(#sbStrokeGrad)"
          strokeWidth="1.5"
        />
        <path
          d="M0 80 C140 130, 200 40, 260 70"
          stroke="#39C3B8"
          strokeWidth="1"
          strokeOpacity="0.25"
        />
      </svg>
    </div>
  );
};

