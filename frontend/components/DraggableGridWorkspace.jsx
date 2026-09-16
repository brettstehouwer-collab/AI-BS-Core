import React, { useEffect, useState, useMemo } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout/legacy';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { useAppStore } from './useAppStore.js';

const ResponsiveGridLayout = WidthProvider(Responsive);

/**
 * A wrapper component that applies a 24-column draggable grid layout
 * and provides a global DND Context for dragging items within or between modules.
 */
export default function DraggableGridWorkspace({ tabKey, defaultLayout, children, onDragEnd }) {
  const { isEditingLayout, globalWidgetLayouts, saveGlobalLayout } = useAppStore();
  const [layoutLoaded, setLayoutLoaded] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5, // 5px movement required before dragging inner items starts
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const currentLayout = globalWidgetLayouts[tabKey] || defaultLayout;

  const layouts = useMemo(() => {
    return {
      lg: currentLayout,
      md: currentLayout,
      sm: currentLayout,
      xs: currentLayout,
      xxs: currentLayout
    };
  }, [currentLayout]);

  useEffect(() => {
    setLayoutLoaded(true);
  }, []);

  const handleLayoutChange = (newLayout, allLayouts) => {
    if (!isEditingLayout) return;
    saveGlobalLayout(tabKey, newLayout);
  };

  if (!layoutLoaded) {
    return <div className="p-4 text-[var(--color-text-secondary)]">Loading layout...</div>;
  }

  return (
    <DndContext 
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={onDragEnd}
    >
      <div className={`w-full h-full overflow-y-auto overflow-x-hidden ${isEditingLayout ? 'bg-[rgba(255,255,255,0.02)] border-2 border-dashed border-[var(--color-accent)] rounded-lg' : ''}`}>
        <ResponsiveGridLayout
          className="layout"
          layouts={layouts}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 24, md: 24, sm: 12, xs: 12, xxs: 6 }}
          rowHeight={40}
          onLayoutChange={handleLayoutChange}
          isDraggable={true}
          isResizable={true}
          compactType="vertical"
          margin={[16, 16]}
          draggableHandle=".drag-handle"
        >
          {children}
        </ResponsiveGridLayout>
      </div>
    </DndContext>
  );
}
