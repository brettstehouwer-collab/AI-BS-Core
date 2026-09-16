import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { theme } from '../../styles/theme';
import { Video, PaintBucket, Sparkles, Droplets, LogOut } from 'lucide-react';

const nodeStyle = {
  background: 'rgba(20, 24, 30, 0.95)',
  border: `1px solid ${theme.colors.border}`,
  borderRadius: '8px',
  padding: '12px',
  minWidth: '180px',
  color: '#fff',
  fontSize: '12px',
  boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
};

const Header = ({ icon: Icon, title, color }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid #30363d', paddingBottom: '8px', marginBottom: '8px' }}>
    <Icon size={14} color={color} />
    <span style={{ fontWeight: 'bold', color }}>{title}</span>
  </div>
);

export const VideoSourceNode = memo(({ data }) => (
  <div style={{ ...nodeStyle, borderTop: '3px solid #ff9900' }}>
    <Header icon={Video} title="Video Source" color="#ff9900" />
    <div style={{ padding: '4px 0', color: '#aaa', fontSize: '10px' }}>
      Timeline: {data.trackName || 'V1'}
    </div>
    <Handle type="source" position={Position.Right} style={{ background: '#ff9900' }} />
  </div>
));

export const ColorTransformNode = memo(({ data }) => (
  <div style={{ ...nodeStyle, borderTop: '3px solid #00f0ff' }}>
    <Handle type="target" position={Position.Left} />
    <Header icon={PaintBucket} title="Color Transform" color="#00f0ff" />
    <div style={{ padding: '4px 0', color: '#aaa', fontSize: '10px' }}>
      LUT: {data.lut || 'Rec.709'}
    </div>
    <Handle type="source" position={Position.Right} style={{ background: '#00f0ff' }} />
  </div>
));

export const BlurNode = memo(({ data }) => (
  <div style={{ ...nodeStyle, borderTop: '3px solid #ff007f' }}>
    <Handle type="target" position={Position.Left} />
    <Header icon={Droplets} title="Gaussian Blur" color="#ff007f" />
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
      <label style={{ fontSize: '9px', color: '#888' }}>Radius: {data.radius || 10}px</label>
      <input type="range" min="0" max="50" defaultValue={data.radius || 10} style={{ accentColor: '#ff007f' }} />
    </div>
    <Handle type="source" position={Position.Right} style={{ background: '#ff007f' }} />
  </div>
));

export const AIGenerativeFillNode = memo(({ data }) => (
  <div style={{ ...nodeStyle, borderTop: '3px solid #d95eff' }}>
    <Handle type="target" position={Position.Left} />
    <Header icon={Sparkles} title="AI Gen-Fill" color="#d95eff" />
    <div style={{ padding: '4px 0', color: '#aaa', fontSize: '10px' }}>
      Prompt: {data.prompt || 'Cyberpunk Cityscape'}
    </div>
    <Handle type="source" position={Position.Right} style={{ background: '#d95eff' }} />
  </div>
));

export const MasterOutNode = memo(({ data }) => (
  <div style={{ ...nodeStyle, borderTop: '3px solid #5eff7b' }}>
    <Handle type="target" position={Position.Left} />
    <Header icon={LogOut} title="Master Output" color="#5eff7b" />
    <div style={{ padding: '4px 0', color: '#aaa', fontSize: '10px' }}>
      Resolution: {data.resolution || '1920x1080'}
    </div>
  </div>
));
