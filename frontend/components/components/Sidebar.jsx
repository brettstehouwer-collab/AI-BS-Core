import React, { useState } from 'react';
import { useAppStore } from './useAppStore';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const SortableHubItem = ({ hub, isHubActive, isCollapsed, onTabChange, activeTab, isEditingLayout }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: hub.key, disabled: !isEditingLayout });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 10 : 1,
    opacity: isDragging ? 0.8 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...(isEditingLayout ? attributes : {})} {...(isEditingLayout ? listeners : {})}>
      <button
        onClick={() => !isEditingLayout && onTabChange?.(isHubActive ? activeTab : hub.defaultTab)}
        title={isCollapsed ? hub.label : ''}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: isCollapsed ? 'center' : 'flex-start',
          gap: isCollapsed ? '0' : '10px',
          padding: '10px 16px',
          border: 'none',
          background: isHubActive ? 'linear-gradient(135deg, var(--accent-glow), rgba(0, 229, 255, 0.1))' : 'transparent',
          color: isHubActive ? 'var(--accent-neon)' : 'var(--text-muted)',
          cursor: isEditingLayout ? 'grab' : 'pointer',
          fontSize: '0.88rem',
          fontWeight: isHubActive ? 600 : 400,
          textAlign: 'left',
          borderLeft: isHubActive ? '3px solid var(--accent-neon)' : '3px solid transparent',
          transition: isDragging ? 'none' : 'all 0.15s ease',
          whiteSpace: 'nowrap',
          marginBottom: '4px',
          outline: isEditingLayout ? '1px dashed var(--accent-neon)' : 'none'
        }}
        onMouseEnter={(e) => {
          if (!isHubActive && !isDragging) {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
            e.currentTarget.style.color = 'var(--text-main)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isHubActive && !isDragging) {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'var(--text-muted)';
          }
        }}
      >
        {isEditingLayout && !isCollapsed && (
          <span style={{ marginRight: '8px', cursor: 'grab', opacity: 0.5 }}>⋮⋮</span>
        )}
        <span style={{ fontSize: '1.1rem' }}>{hub.icon}</span>
        {!isCollapsed && <span>{hub.label}</span>}
      </button>
    </div>
  );
};

const Sidebar = ({ activeTab, onTabChange }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const navigationLayout = useAppStore(state => state.navigationLayout);
  const reorderMasterHubs = useAppStore(state => state.reorderMasterHubs);
  const isEditingLayout = useAppStore(state => state.isEditingLayout);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = navigationLayout.findIndex((hub) => hub.key === active.id);
      const newIndex = navigationLayout.findIndex((hub) => hub.key === over.id);
      reorderMasterHubs(arrayMove(navigationLayout, oldIndex, newIndex));
    }
  };

  return (
    <div style={{
      width: '100%',
      background: 'var(--glass-bg)',
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      borderRight: '1px solid var(--glass-border)',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflowY: 'auto',
      overflowX: 'hidden',
      transition: 'width 0.2s ease',
    }}>
      {/* Brand */}
      <div style={{
        padding: isCollapsed ? '16px 0' : '16px 12px',
        borderBottom: '1px solid var(--glass-border)',
        background: 'transparent',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        {!isCollapsed && (
          <div style={{ overflow: 'hidden' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px', whiteSpace: 'nowrap' }}>
              Stehouwer Publishing
            </div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>v5.296.0</div>
          </div>
        )}
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#8b949e',
            cursor: 'pointer',
            padding: '8px',
            margin: isCollapsed ? '0 auto' : '0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '4px',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = '#21262d'; e.currentTarget.style.color = '#c9d1d9'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#8b949e'; }}
          title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {isCollapsed ? '»' : '«'}
        </button>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: '12px 0' }}>
        {!isCollapsed && (
          <div style={{
            padding: '4px 16px',
            fontSize: '0.65rem',
            color: '#484f58',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginBottom: '8px'
          }}>
            Master Workspace Hubs
          </div>
        )}
        <DndContext 
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext 
            items={navigationLayout.map(h => h.key)}
            strategy={verticalListSortingStrategy}
          >
            {navigationLayout.map((hub) => {
              const isHubActive = hub.key === activeTab || hub.subTabs.some(sub => sub.key === activeTab);
              return (
                <SortableHubItem
                  key={hub.key}
                  hub={hub}
                  isHubActive={isHubActive}
                  isCollapsed={isCollapsed}
                  onTabChange={onTabChange}
                  activeTab={activeTab}
                  isEditingLayout={isEditingLayout}
                />
              );
            })}
          </SortableContext>
        </DndContext>
      </nav>

      {/* Footer */}
      <div style={{
        padding: '12px',
        borderTop: '1px solid var(--glass-border)',
        fontSize: '0.7rem',
        color: 'var(--text-muted)',
        textAlign: 'center',
        whiteSpace: 'nowrap',
        overflow: 'hidden'
      }}>
        {isCollapsed ? '©' : 'AI-BS Matrix © 2026'}
      </div>
    </div>
  );
};

export default Sidebar;






