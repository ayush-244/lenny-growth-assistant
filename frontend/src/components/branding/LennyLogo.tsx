import React from 'react';

interface LennyLogoProps {
  size?: number;
}

export const LennyLogo: React.FC<LennyLogoProps> = ({ size = 36 }) => {
  return (
    <span className="lenny-logo" style={{ width: size, height: size }} aria-hidden="true">
      <svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="18" cy="18" r="18" fill="url(#lennyLogoBg)" />
        <path
          d="M18.2 8.2c.3 3.4-1.1 6.2-3.8 8.2 2.2.2 4.3-.4 6.1-1.8-.2 3.6-1.8 6.4-4.7 8.4 3 .1 5.6-1 7.6-3.1-.6 4.2-3.4 7-7.4 8.4 5.8-1 10.2-4.8 11.4-10.2C28.8 12.4 24.2 8.4 18.2 8.2Z"
          fill="#fff"
          opacity="0.95"
        />
        <path
          d="M13.4 12.6c1.8-1.8 4.4-2.6 6.2-2.4-1.4 2.6-3.6 4.2-6.2 5.1 1.2-1 2-1.8 0-2.7Z"
          fill="#FCE7EF"
        />
        <defs>
          <linearGradient id="lennyLogoBg" x1="6" y1="4" x2="30" y2="32" gradientUnits="userSpaceOnUse">
            <stop stopColor="#E84A82" />
            <stop offset="1" stopColor="#C92F68" />
          </linearGradient>
        </defs>
      </svg>
    </span>
  );
};
