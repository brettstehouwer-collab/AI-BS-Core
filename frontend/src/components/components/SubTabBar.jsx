import React, { useRef } from 'react';
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
  horizontalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const SortableSubTab = ({ sub, isActive, onTabChange, isEditingLayout }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: sub.key, disabled: !isEditingLayout });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 10 : 1,
    opacity: isDragging ? 0.8 : 1,
    flexShrink: 0,
  };

  return (
    <div ref={setNodeRef} style={style} {...(isEditingLayout ? attributes : {})} {...(isEditingLayout ? listeners : {})}>
      <button
        onClick={() => !isEditingLayout && onTabChange(sub.key)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 14px',
          borderRadius: '6px',
          border: isActive ? '1px solid #38bdf8' : '1px solid transparent',
          background: isActive ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.25), rgba(168, 85, 247, 0.25))' : 'rgba(255, 255, 255, 0.03)',
          color: isActive ? '#ffffff' : 'var(--text-muted, #8b949e)',
          fontSize: '0.82rem',
          fontWeight: isActive ? 600 : 400,
          cursor: isEditingLayout ? 'grab' : 'pointer',
          transition: isDragging ? 'none' : 'all 0.2s ease',
          boxShadow: isActive ? '0 0 10px rgba(56, 189, 248, 0.3)' : 'none',
          outline: isEditingLayout ? '1px dashed #38bdf8' : 'none',
          whiteSpace: 'nowrap'
        }}
      >
        {isEditingLayout && (
          <span style={{ marginRight: '4px', cursor: 'grab', opacity: 0.5 }}>⋮⋮</span>
        )}
        <span>{sub.icon || '•'}</span>
        <span>{sub.label}</span>
      </button>
    </div>
  );
};

export default function SubTabBar({ activeTab, onTabChange }) {
  const masterHubs = useAppStore((state) => state.navigationLayout);
  const reorderSubTabs = useAppStore((state) => state.reorderSubTabs);
  const isEditingLayout = useAppStore((state) => state.isEditingLayout);
  const scrollRef = useRef(null);

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

  const currentHub = masterHubs.find((hub) =>
    hub.subTabs.some((sub) => sub.key === activeTab)
  );

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (over && active.id !== over.id && currentHub) {
      const oldIndex = currentHub.subTabs.findIndex((sub) => sub.key === active.id);
      const newIndex = currentHub.subTabs.findIndex((sub) => sub.key === over.id);
      reorderSubTabs(currentHub.key, arrayMove(currentHub.subTabs, oldIndex, newIndex));
    }
  };

  const handleScrollLeft = () => {
    if (scrollRef.current) scrollRef.current.scrollBy({ left: -240, behavior: 'smooth' });
  };

  const handleScrollRight = () => {
    if (scrollRef.current) scrollRef.current.scrollBy({ left: 240, behavior: 'smooth' });
  };

  if (!currentHub || currentHub.subTabs.length <= 1) {
    return null;
  }

  const activeSubKey = currentHub.subTabs.some(sub => sub.key === activeTab)
    ? activeTab
    : currentHub.defaultTab;

  return (
    <div className="subtab-container" style={{
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      padding: '6px 12px',
      background: 'linear-gradient(135deg, rgba(13, 17, 23, 0.98), rgba(22, 27, 34, 0.98))',
      borderBottom: '1px solid rgba(0, 240, 255, 0.2)',
      backdropFilter: 'blur(10px)',
      zIndex: 90,
      position: 'relative'
    }}>
      <style dangerouslySetInnerHTML={{__html: `
        .subtab-scroll-pane::-webkit-scrollbar { height: 5px; }
        .subtab-scroll-pane::-webkit-scrollbar-track { background: #0d1117; }
        .subtab-scroll-pane::-webkit-scrollbar-thumb { background: #38bdf8; border-radius: 4px; }
      `}} />
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        fontSize: '0.85rem',
        fontWeight: 'bold',
        color: '#00f0ff',
        paddingRight: '12px',
        borderRight: '1px solid rgba(255, 255, 255, 0.1)',
        marginRight: '4px',
        flexShrink: 0
      }}>
        <span>{currentHub.icon}</span>
        <span>{currentHub.label}</span>
      </div>

      {/* ◀ SubTab Pan Left */}
      <button 
        onClick={handleScrollLeft}
        title="Scroll Subtabs Left (◀)"
        style={{
          background: '#161b22',
          color: '#38bdf8',
          border: '1px solid #30363d',
          borderRadius: '4px',
          padding: '4px 8px',
          fontSize: '0.75rem',
          cursor: 'pointer',
          flexShrink: 0,
          fontWeight: 'bold'
        }}
      >
        ◀
      </button>

      {/* Scrollable Subtabs Container */}
      <div 
        ref={scrollRef}
        className="subtab-scroll-pane"
        style={{
          display: 'flex',
          gap: '6px',
          alignItems: 'center',
          overflowX: 'auto',
          scrollBehavior: 'smooth',
          flex: 1,
          padding: '2px 0',
          scrollbarWidth: 'thin',
          scrollbarColor: '#38bdf8 #0d1117'
        }}
      >
        <DndContext 
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext 
            items={currentHub.subTabs.map(s => s.key)}
            strategy={horizontalListSortingStrategy}
          >
            {currentHub.subTabs.map(sub => {
              const isActive = activeSubKey === sub.key;
              return (
                <SortableSubTab
                  key={sub.key}
                  sub={sub}
                  isActive={isActive}
                  onTabChange={onTabChange}
                  isEditingLayout={isEditingLayout}
                />
              );
            })}
          </SortableContext>
        </DndContext>
      </div>

      {/* ▶ SubTab Pan Right */}
      <button 
        onClick={handleScrollRight}
        title="Scroll Subtabs Right (▶)"
        style={{
          background: '#161b22',
          color: '#38bdf8',
          border: '1px solid #30363d',
          borderRadius: '4px',
          padding: '4px 8px',
          fontSize: '0.75rem',
          cursor: 'pointer',
          flexShrink: 0,
          fontWeight: 'bold'
        }}
      >
        ▶
      </button>
    </div>
  );
}
