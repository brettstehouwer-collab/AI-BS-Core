import 'react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';

/** @param {{id:string,items:(string|number|{id:string|number})[],children:import("react").ReactNode,className?:string}} props */
export default function DroppableContainer({ id, items, children, className = '' }) {
  const { isOver, setNodeRef } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      className={`${className} ${isOver ? 'bg-[rgba(255,255,255,0.05)] border-2 border-dashed border-[var(--color-accent)] rounded-md' : ''}`}
    >
      {/* We assume items is an array of IDs */}
      <SortableContext id={id} items={items} strategy={verticalListSortingStrategy}>
        {children}
      </SortableContext>
    </div>
  );
}
