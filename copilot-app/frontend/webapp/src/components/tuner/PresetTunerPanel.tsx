/**
 * Preset Tuner Panel Component
 * Allows users to tune backtest parameters and see the impact on forecasts
 */

import React, { useState } from 'react';

interface TunerParams {
  confidenceThreshold: number;
  minSampleSize: number;
  timeWindow: string;
  riskTolerance: number;
  modelWeight: number;
}

interface PresetTunerPanelProps {
  onParamsChange?: (params: TunerParams) => void;
  initialParams?: Partial<TunerParams>;
  showRunButton?: boolean;
  onRun?: (params: TunerParams) => void;
}

export const PresetTunerPanel: React.FC<PresetTunerPanelProps> = ({ 
  onParamsChange, 
  initialParams = {},
  showRunButton = true,
  onRun
}) => {
  const [params, setParams] = useState<TunerParams>({
    confidenceThreshold: initialParams.confidenceThreshold ?? 0.6,
    minSampleSize: initialParams.minSampleSize ?? 20,
    timeWindow: initialParams.timeWindow ?? '30d',
    riskTolerance: initialParams.riskTolerance ?? 0.05,
    modelWeight: initialParams.modelWeight ?? 0.7,
  });

  const handleParamChange = (key: keyof TunerParams, value: any) => {
    const newParams = { ...params, [key]: value };
    setParams(newParams);
    
    if (onParamsChange) {
      onParamsChange(newParams);
    }
  };

  const presets = [
    { label: 'Conservative', value: 'conservative', params: { confidenceThreshold: 0.7, riskTolerance: 0.02, modelWeight: 0.6 } },
    { label: 'Moderate', value: 'moderate', params: { confidenceThreshold: 0.6, riskTolerance: 0.05, modelWeight: 0.7 } },
    { label: 'Aggressive', value: 'aggressive', params: { confidenceThreshold: 0.5, riskTolerance: 0.1, modelWeight: 0.8 } },
    { label: 'Day Trading', value: 'day', params: { confidenceThreshold: 0.65, timeWindow: '1d', modelWeight: 0.9 } },
  ];

  const applyPreset = (presetValue: string) => {
    const preset = presets.find(p => p.value === presetValue);
    if (!preset || !preset.params) return;
    
    const newParams = { ...params, ...preset.params };
    setParams(newParams);
    
    if (onParamsChange) {
      onParamsChange(newParams);
    }
  };

  const handleRun = () => {
    if (onRun) {
      onRun(params);
    }
  };

  return (
    <div style={{ 
      border: '1px solid #e2e8f0', 
      padding: '1.5rem', 
      borderRadius: '8px', 
      backgroundColor: '#fff',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
    }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '1rem' 
      }}>
        <h3 style={{ margin: 0, fontWeight: '500', fontSize: '1.2rem' }}>Parameter Tuner</h3>
        <span style={{ fontSize: '1.2rem' }}>⚙️</span>
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <label htmlFor="preset-select" style={{display: 'block', marginBottom: '8px'}}>Preset Strategy</label>
          <select
            id="preset-select"
            onChange={(e) => applyPreset(e.target.value)}
            style={{width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px'}}
          >
            <option value="">Select a preset</option>
            {presets.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          <div style={{fontSize: '0.8rem', color: '#666', marginTop: '4px'}}>Apply predefined parameter sets</div>
        </div>

        <div>
          <label htmlFor="confidence-slider" style={{display: 'block', marginBottom: '8px'}}>Confidence Threshold</label>
          <input 
            id="confidence-slider"
            type="range" 
            min="0.1" 
            max="0.9" 
            step="0.05" 
            value={params.confidenceThreshold} 
            onChange={(e) => handleParamChange('confidenceThreshold', parseFloat(e.target.value))}
            style={{width: '100%'}}
          />
          <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#666'}}>
            <span>Low (0.1)</span>
            <span>High (0.9)</span>
          </div>
        </div>

        <div>
          <label htmlFor="min-sample-input" style={{display: 'block', marginBottom: '8px'}}>Minimum Sample Size</label>
          <input 
            id="min-sample-input"
            type="number" 
            value={params.minSampleSize}
            onChange={(e) => handleParamChange('minSampleSize', parseInt(e.target.value))}
            min="5"
            max="500"
            style={{width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px'}}
          />
          <div style={{fontSize: '0.8rem', color: '#666', marginTop: '4px'}}>Minimum data points for valid forecasts</div>
        </div>

        <div>
          <label htmlFor="time-window-select" style={{display: 'block', marginBottom: '8px'}}>Time Window</label>
          <select
            id="time-window-select"
            value={params.timeWindow}
            onChange={(e) => handleParamChange('timeWindow', e.target.value)}
            style={{width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px'}}
          >
            <option value="1d">1 Day</option>
            <option value="5d">5 Days</option>
            <option value="10d">10 Days</option>
            <option value="30d">30 Days</option>
            <option value="90d">90 Days</option>
          </select>
          <div style={{fontSize: '0.8rem', color: '#666', marginTop: '4px'}}>Historical data window for calculations</div>
        </div>

        <div>
          <label htmlFor="risk-tolerance-slider" style={{display: 'block', marginBottom: '8px'}}>Risk Tolerance</label>
          <input 
            id="risk-tolerance-slider"
            type="range" 
            min="0.01" 
            max="0.2" 
            step="0.01" 
            value={params.riskTolerance} 
            onChange={(e) => handleParamChange('riskTolerance', parseFloat(e.target.value))}
            style={{width: '100%'}}
          />
          <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#666'}}>
            <span>Conservative (0.01)</span>
            <span>High (0.20)</span>
          </div>
        </div>

        <div>
          <label htmlFor="model-weight-slider" style={{display: 'block', marginBottom: '8px'}}>Model Weight</label>
          <input 
            id="model-weight-slider"
            type="range" 
            min="0.1" 
            max="0.9" 
            step="0.05" 
            value={params.modelWeight} 
            onChange={(e) => handleParamChange('modelWeight', parseFloat(e.target.value))}
            style={{width: '100%'}}
          />
          <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#666'}}>
            <span>Low (0.1)</span>
            <span>High (0.9)</span>
          </div>
        </div>
      </Stack>

      {showRunButton && (
        <div style={{textAlign: 'right', marginTop: '1rem'}}>
          <button 
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#4a9eff',
              border: 'none',
              borderRadius: '6px',
              color: '#fff',
              cursor: 'pointer',
            }}
            onClick={handleRun}
          >
            Apply & Run Backtest
          </button>
        </div>
      </div>
    </div>
  );
};

export default PresetTunerPanel;