import React from 'react';

interface PageUpperWaveProps {
  className?: string;
}

export const PageUpperWave: React.FC<PageUpperWaveProps> = ({ className = '' }) => {
  return (
    <div
      className={`absolute top-0 right-0 w-[380px] sm:w-[460px] lg:w-[540px] h-[130px] sm:h-[155px] pointer-events-none select-none overflow-hidden z-0 ${className}`}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 540 155"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full object-right-top"
        preserveAspectRatio="none"
      >
        <defs>
          {/* Main Peacock Teal Gradient */}
          <linearGradient id="waveTealGrad" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#009F98" stopOpacity="0.45" />
            <stop offset="40%" stopColor="#39C3B8" stopOpacity="0.30" />
            <stop offset="80%" stopColor="#DDF0F5" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#F5F8FA" stopOpacity="0" />
          </linearGradient>

          {/* Secondary Soft Ice-Blue Gradient */}
          <linearGradient id="waveIceGrad" x1="100%" y1="10%" x2="10%" y2="90%">
            <stop offset="0%" stopColor="#39C3B8" stopOpacity="0.35" />
            <stop offset="50%" stopColor="#BBDCE8" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#EDF7FA" stopOpacity="0.05" />
          </linearGradient>

          {/* Cyan Highlight Line */}
          <linearGradient id="waveLineGrad" x1="100%" y1="0%" x2="0%" y2="80%">
            <stop offset="0%" stopColor="#39C3B8" stopOpacity="0.7" />
            <stop offset="60%" stopColor="#009F98" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#009F98" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Layer 1: Background Soft Flowing Curve */}
        <path
          d="M160 0 C240 60, 360 10, 480 70 C515 88, 535 60, 540 40 L540 0 Z"
          fill="url(#waveIceGrad)"
        />

        {/* Layer 2: Main Foreground Peacock Wave Layer */}
        <path
          d="M80 0 C160 75, 260 135, 390 95 C460 70, 505 110, 540 90 L540 0 Z"
          fill="url(#waveTealGrad)"
        />

        {/* Layer 3: Cyan Accent Ribbons */}
        <path
          d="M100 0 C180 75, 275 130, 400 95 C465 72, 510 110, 540 92"
          stroke="url(#waveLineGrad)"
          strokeWidth="1.75"
        />
        <path
          d="M190 0 C265 50, 345 35, 450 75 C495 90, 525 70, 540 55"
          stroke="#39C3B8"
          strokeWidth="1"
          strokeOpacity="0.4"
        />
      </svg>
    </div>
  );
};

