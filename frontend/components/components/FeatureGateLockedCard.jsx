import React from 'react';
import { USER_TIERS, TAB_PERMISSIONS } from './accessControl';

export default function FeatureGateLockedCard({
  tabKey,
  tabLabel = 'Feature Locked',
  activeTier,
  onNavigateToPricing
}) {
  const allowedTierIds = TAB_PERMISSIONS[tabKey] || [];
  const requiredTier = Object.values(USER_TIERS).find(t => allowedTierIds.includes(t.id) && t.id !== 'admin') || USER_TIERS.ENTERPRISE_ALL_ACCESS;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        minHeight: '480px',
        padding: '24px',
        backgroundColor: '#0d1117'
      }}
    >
      <div
        style={{
          maxWidth: '540px',
          width: '100%',
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '12px',
          padding: '36px',
          textAlign: 'center',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px'
        }}
      >
        <div
          style={{
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            backgroundColor: 'rgba(218, 54, 51, 0.15)',
            border: '1px solid #da3633',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '28px'
          }}
        >
          🔒
        </div>

        <div>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 'bold',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              padding: '3px 10px',
              borderRadius: '12px',
              backgroundColor: `${requiredTier.color}22`,
              color: requiredTier.color,
              border: `1px solid ${requiredTier.color}55`
            }}
          >
            {requiredTier.badge}
          </span>

          <h2 style={{ margin: '12px 0 6px 0', fontSize: '22px', color: '#f0f6fc' }}>
            {tabLabel}
          </h2>

          <p style={{ margin: 0, fontSize: '13px', color: '#8b949e', lineHeight: '1.5' }}>
            This feature is locked on your current plan (<strong>{activeTier?.name || 'Free Tier'}</strong>).
            Unlock full access to this tool with the <strong>{requiredTier.name}</strong>.
          </p>
        </div>

        <div
          style={{
            backgroundColor: '#0d1117',
            border: '1px solid #30363d',
            borderRadius: '8px',
            padding: '14px 18px',
            width: '100%',
            textAlign: 'left',
            fontSize: '12px',
            color: '#c9d1d9'
          }}
        >
          <div style={{ fontWeight: 'bold', color: '#f0f6fc', marginBottom: '4px' }}>
            ✨ Included in this upgrade:
          </div>
          <div style={{ color: '#8b949e', lineHeight: '1.4' }}>
            {requiredTier.description}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', width: '100%', marginTop: '8px' }}>
          <button
            onClick={onNavigateToPricing}
            style={{
              flex: 1,
              padding: '12px 20px',
              backgroundColor: '#238636',
              border: 'none',
              borderRadius: '6px',
              color: '#ffffff',
              fontWeight: 'bold',
              fontSize: '14px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              boxShadow: '0 2px 8px rgba(35,134,54,0.4)',
              transition: 'background 0.2s'
            }}
          >
            <span>💎</span> Upgrade / Unlock Plan
          </button>
        </div>
      </div>
    </div>
  );
}
