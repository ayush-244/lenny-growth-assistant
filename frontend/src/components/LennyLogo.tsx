import React from 'react';

interface LennyLogoProps {
  size?: number;
}

export const LennyLogo: React.FC<LennyLogoProps> = ({ size = 36 }) => {
  return (
    <span className="lenny-logo" aria-hidden="true" style={{ width: size, height: size }}>
      <svg viewBox="0 0 32 32" width={size} height={size} fill="none">
        <rect width="32" height="32" rx="10" fill="url(#lenny-leaf-bg)" />
        <path
          d="M16.2 7.2c4.8 1.1 8.1 5.2 8.1 10.1 0 3.3-1.6 5.6-4.2 7.1-1.1-4.2-3.4-7.4-6.9-9.6 1.6-2.8 2.4-5.2 3-7.6Z"
          fill="#fff"
          opacity="0.95"
        />
        <path
          d="M10.4 12.4c3.8 0.4 6.8 2.6 8.6 6.2-2.1 2.8-5.1 4.4-8.6 4.8-.2-3.7.0-7.4 0-11Z"
          fill="#FCE7EF"
        />
        <path
          d="M16 8.4c.2 5.6.2 10.4 0 16.2"
          stroke="#C92F68"
          strokeWidth="1.4"
          strokeLinecap="round"
        />
        <defs>
          <linearGradient id="lenny-leaf-bg" x1="6" y1="4" x2="28" y2="30">
            <stop stopColor="#E84A82" />
            <stop offset="1" stopColor="#C92F68" />
          </linearGradient>
        </defs>
      </svg>
    </span>
  );
};
