/**
 * Ring Progress Component for Robustness Score Visualization
 * Shows the robustness score as a circular progress ring with color coding
 */

import React from 'react';

interface RingProps {
  value: number;        // Score value between 0 and 1
  size?: number;        // Size in pixels
  strokeWidth?: number; // Stroke width
  label?: string;       // Label to display
  showPercentage?: boolean; // Whether to show percentage
  color?: string;       // Color override
}

export const Ring: React.FC<RingProps> = ({ 
  value = 0, 
  size = 120, 
  strokeWidth = 8, 
  label = 'Score',
  showPercentage = true,
  color 
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (value * circumference);
  
  // Determine color based on score if not provided
  const scoreColor = color || (
    value >= 0.8 ? '#10B981' :  // Green for high scores (A, S grades)
    value >= 0.6 ? '#22C55E' :  // Light green for good scores (B grade)
    value >= 0.4 ? '#F59E0B' :  // Amber for average scores (C grade)
    value >= 0.2 ? '#EF4444' :  // Red for low scores (D grade)
                 '#78716C'      // Gray for very poor scores (E grade)
  );
  
  // Determine text color based on background
  const textColor = value >= 0.5 ? '#1F2937' : '#FFFFFF';
  
  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center',
      justifyContent: 'center' 
    }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          style={{ transform: 'rotate(-90deg)' }}
        >
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#E5E7EB"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={scoreColor}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{
              transition: 'stroke-dashoffset 0.3s ease-in-out',
              transformOrigin: 'center',
              transform: 'rotate(-90deg)',
            }}
          />
        </svg>
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          {showPercentage ? (
            <span style={{
              fontSize: size * 0.2,
              fontWeight: 'bold',
              color: textColor,
              lineHeight: 1
            }}>
              {Math.round(value * 100)}%
            </span>
          ) : (
            <span style={{
              fontSize: size * 0.15,
              fontWeight: 'bold',
              color: textColor,
              lineHeight: 1
            }}>
              {value.toFixed(2)}
            </span>
          )}
        </div>
      </div>
      {label && (
        <div style={{
          marginTop: size * 0.1,
          fontSize: size * 0.12,
          color: '#6B7280',
          textAlign: 'center'
        }}>
          {label}
        </div>
      )}
    </div>
  );
};

export default Ring;