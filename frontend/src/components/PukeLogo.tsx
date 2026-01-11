export const PukeLogo = ({ className = "w-6 h-6" }: { className?: string }) => {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Face circle */}
      <circle cx="16" cy="14" r="12" fill="currentColor" opacity="0.15" />
      <circle cx="16" cy="14" r="12" stroke="currentColor" strokeWidth="2" fill="none" />
      
      {/* Left eye - X shape */}
      <path
        d="M10 10L13 13M13 10L10 13"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      
      {/* Right eye - X shape */}
      <path
        d="M19 10L22 13M22 10L19 13"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      
      {/* Mouth open */}
      <ellipse cx="16" cy="20" rx="4" ry="3" fill="currentColor" opacity="0.3" />
      <ellipse cx="16" cy="20" rx="4" ry="3" stroke="currentColor" strokeWidth="1.5" fill="none" />
      
      {/* Puke stream */}
      <path
        d="M14 23C14 25 12 27 12 29M16 23C16 26 16 28 16 31M18 23C18 25 20 27 20 29"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      
      {/* Puke drops */}
      <circle cx="11" cy="31" r="1.5" fill="currentColor" />
      <circle cx="16" cy="32" r="1" fill="currentColor" opacity="0.7" />
      <circle cx="21" cy="31" r="1.5" fill="currentColor" />
    </svg>
  );
};
