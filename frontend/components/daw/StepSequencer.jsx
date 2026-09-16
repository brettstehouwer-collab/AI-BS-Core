import React from 'react';
import { useDawStore } from './dawStore';
import { theme } from '../../styles/theme';

const StepSequencer = ({ channel }) => {
  const toggleStep = useDawStore((state) => state.toggleStep);
  const currentStep = useDawStore((state) => state.currentStep);
  const isPlaying = useDawStore((state) => state.isPlaying);
  const stepCount = useDawStore((state) => state.stepCount);

  return (
    <div style={{ display: 'flex', gap: '3px', alignItems: 'center' }}>
      {channel.steps.slice(0, stepCount).map((stepActive, index) => {
        // FL Studio groups steps in 4s (Beats 1, 2, 3, 4)
        const isBeatStart = index % 4 === 0;
        const isEvenBar = Math.floor(index / 4) % 2 === 0;
        const isCurrent = isPlaying && currentStep === index;
        
        let bgColor = isEvenBar ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.03)';
        let boxShadow = 'none';

        if (stepActive) {
          bgColor = channel.color || theme.colors.accent;
          boxShadow = `0 0 10px ${channel.color || theme.colors.accent}`;
        }
        if (isCurrent) {
          boxShadow = '0 0 12px #ffffff';
        }

        return (
          <div
            key={index}
            onClick={() => toggleStep(channel.id, index)}
            title={`Step ${index + 1} (${channel.name})`}
            style={{
              width: stepCount > 16 ? '16px' : '22px',
              height: '32px',
              background: bgColor,
              border: isCurrent 
                ? '2px solid #ffffff' 
                : isBeatStart 
                ? '1px solid rgba(255,255,255,0.3)' 
                : '1px solid rgba(0,0,0,0.5)',
              borderRadius: '3px',
              cursor: 'pointer',
              boxShadow: boxShadow,
              transition: 'background 0.08s, box-shadow 0.08s, border 0.05s',
              position: 'relative'
            }}
          >
            {isCurrent && (
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: '3px',
                background: '#fff',
                borderRadius: '2px 2px 0 0'
              }} />
            )}
          </div>
        );
      })}
    </div>
  );
};

export default StepSequencer;
