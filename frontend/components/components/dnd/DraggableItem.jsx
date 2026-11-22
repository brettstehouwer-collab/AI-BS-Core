import 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

/** @param {{id:string|number,children:import("react").ReactNode,disabled?:boolean,className?:string}} props */
export default function DraggableItem({ id, children, disabled = false, className = '' }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id, disabled });

  /** @type {import("react").CSSProperties} */
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 999 : 'auto',
    position: isDragging ? 'relative' : 'static',
  };

  return (
    <div ref={setNodeRef} style={style} className={`${className} ${isDragging ? 'shadow-xl' : ''}`}>
      <div {...attributes} {...listeners} className="w-full h-full cursor-grab active:cursor-grabbing">
        {children}
      </div>
    </div>
  );
}
