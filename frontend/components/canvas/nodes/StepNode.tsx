import { memo, useState, useRef, useEffect } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { Maximize2, MessageSquare, Minimize2, BookOpen } from 'lucide-react';
import { JourneyStep } from '@/app/page';
import StepDetail from '@/components/StepDetail';

// Resizable wrapper component - shared between all node types
export const ResizableWrapper = ({ 
  children, 
  nodeId,
  initialWidth = 1000, 
  initialHeight = 800,
  minWidth = 400,
  minHeight = 300,
  maxWidth = 2000,
  maxHeight = 1600
}: { 
  children: React.ReactNode;
  nodeId?: string;
  initialWidth?: number;
  initialHeight?: number;
  minWidth?: number;
  minHeight?: number;
  maxWidth?: number;
  maxHeight?: number;
}) => {
  const [size, setSize] = useState({ width: initialWidth, height: initialHeight });
  const [isResizing, setIsResizing] = useState(false);
  const [resizeHandle, setResizeHandle] = useState<string | null>(null);
  
  // Refs for drag state
  const dragStartRef = useRef({ x: 0, y: 0, width: 0, height: 0 });
  const { getZoom, updateNode } = useReactFlow();

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !resizeHandle) return;

      e.preventDefault();
      e.stopPropagation();

      const zoom = getZoom();
      const deltaX = (e.clientX - dragStartRef.current.x) / zoom;
      const deltaY = (e.clientY - dragStartRef.current.y) / zoom;

      let newWidth = dragStartRef.current.width;
      let newHeight = dragStartRef.current.height;

      if (resizeHandle.includes('right')) {
        newWidth = Math.min(maxWidth, Math.max(minWidth, dragStartRef.current.width + deltaX));
      }
      if (resizeHandle.includes('bottom')) {
        newHeight = Math.min(maxHeight, Math.max(minHeight, dragStartRef.current.height + deltaY));
      }

      setSize({ width: newWidth, height: newHeight });
      
      // Update React Flow node dimensions so panning works correctly
      if (nodeId && updateNode) {
        updateNode(nodeId, {
          width: newWidth,
          height: newHeight,
        });
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      setResizeHandle(null);
    };

    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove, { passive: false });
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isResizing, resizeHandle, minWidth, minHeight, maxWidth, maxHeight, getZoom, nodeId, updateNode]);

  const handleMouseDown = (handle: string) => (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    
    setIsResizing(true);
    setResizeHandle(handle);
    
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      width: size.width,
      height: size.height
    };
  };

  return (
    <div 
      className="relative"
      style={{ width: size.width, height: size.height }}
    >
      {children}
      
      {/* Resize handles */}
      <div
        className="absolute right-0 top-0 bottom-0 w-4 cursor-ew-resize hover:bg-blue-500/20 transition-colors z-50 nodrag"
        onMouseDown={handleMouseDown('right')}
      />
      <div
        className="absolute bottom-0 left-0 right-0 h-4 cursor-ns-resize hover:bg-blue-500/20 transition-colors z-50 nodrag"
        onMouseDown={handleMouseDown('bottom')}
      />
      <div
        className="absolute right-0 bottom-0 w-6 h-6 cursor-nwse-resize hover:bg-blue-500/20 transition-colors z-50 nodrag rounded-tl"
        onMouseDown={handleMouseDown('bottom-right')}
      >
        <div className="absolute bottom-1 right-1 w-2 h-2 bg-blue-500/50 rounded-sm" />
      </div>
    </div>
  );
};

const StepNode = ({ data, id, selected }: NodeProps<{ step: JourneyStep; onChat: (step: JourneyStep, nodeId: string) => void; onExpand: (step: JourneyStep, nodeId: string) => void }>) => {
  return (
    <div 
      className={`
        w-[300px] bg-[#1e1e1e] rounded-xl shadow-lg 
        transition-all duration-200 group
        ${selected 
          ? 'border-2 border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.3)]' 
          : 'border border-[#3a3a3a] hover:border-blue-500 hover:shadow-md'
        }
      `}
    >
      {/* Input Handle */}
      <Handle type="target" position={Position.Left} className="w-3 h-3 !bg-blue-500" />

      <div className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center font-bold text-sm border border-blue-500/30">
              {data.step.step_number}
            </div>
            <span className="text-xs font-medium text-[#858585] bg-[#252525] px-2 py-1 rounded border border-[#3a3a3a]">
              {data.step.estimated_time}
            </span>
          </div>
          <div className="flex gap-1">
            <button 
              onClick={(e) => {
                e.stopPropagation();
                data.onChat(data.step, id);
              }}
              className="p-1.5 text-[#858585] hover:text-purple-400 hover:bg-[#2d2d2d] rounded-lg transition-colors"
              title="Ask Question"
            >
              <MessageSquare size={16} />
            </button>
            <button 
              onClick={(e) => {
                e.stopPropagation();
                data.onExpand(data.step, id);
              }}
              className="p-1.5 text-[#858585] hover:text-blue-400 hover:bg-[#2d2d2d] rounded-lg transition-colors"
              title="Expand Details"
            >
              <Maximize2 size={16} />
            </button>
          </div>
        </div>

        <h3 className="font-bold text-[#d4d4d4] mb-2 line-clamp-2">
          {data.step.title}
        </h3>
        
        <p className="text-sm text-[#858585] line-clamp-3 mb-4">
          {data.step.description}
        </p>

        <div className="flex items-center gap-4 text-xs text-[#5a5a5a]">
          <div className="flex items-center gap-1">
            <BookOpen size={14} />
            <span>{data.step.doc_urls.length} resources</span>
          </div>
        </div>
      </div>

      {/* Output Handle */}
      <Handle type="source" position={Position.Right} className="w-3 h-3 !bg-blue-500" />
      
      {/* Chat Handle */}
      <Handle type="source" position={Position.Bottom} id="chat" className="w-3 h-3 !bg-purple-500 !opacity-0 group-hover:!opacity-100 transition-opacity" />
      
      {/* Expand Handle */}
      <Handle type="source" position={Position.Bottom} id="expand" className="w-3 h-3 !bg-blue-500 !opacity-0 group-hover:!opacity-100 transition-opacity" />
    </div>
  );
};

export default memo(StepNode);
