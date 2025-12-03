import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { X } from 'lucide-react';
import { JourneyStep } from '@/app/page';
import StepDetail from '@/components/StepDetail';
import { ResizableWrapper } from './StepNode';

interface StepDetailNodeData {
  step: JourneyStep;
  onClose: (nodeId: string) => void;
  onChat: (step: JourneyStep, sourceNodeId: string) => void;
  sourceStepNodeId?: string; // Original step node ID
}

const StepDetailNode = ({ data, id, selected }: NodeProps<StepDetailNodeData>) => {
  return (
    <ResizableWrapper nodeId={id} initialWidth={800} initialHeight={600}>
      <div 
        className={`
          w-full h-full bg-[#1e1e1e] rounded-lg shadow-2xl border overflow-hidden flex flex-col
          ${selected ? 'border-blue-500 ring-2 ring-blue-500' : 'border-[#3a3a3a]'}
        `}
      >
        <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-blue-500" />
        
        <div className="p-3 bg-[#252525] border-b border-[#3a3a3a] flex justify-between items-center flex-shrink-0 select-none">
          <span className="font-bold text-[#d4d4d4] ml-2 text-lg">Step {data.step.step_number} Details</span>
          <div className="flex gap-2">
            <button 
              onClick={(e) => {
                e.stopPropagation();
                // Use sourceStepNodeId if available, otherwise use detail node ID (onChat will find the step node)
                data.onChat(data.step, data.sourceStepNodeId || id);
              }}
              className="px-3 py-1.5 text-[#d4d4d4] bg-[#2d2d2d] hover:bg-[#3a3a3a] rounded-md transition-colors flex items-center gap-2 text-sm font-medium border border-[#3a3a3a]"
              title="Open Chat"
            >
              Chat
            </button>
            <button 
              onClick={(e) => {
                e.stopPropagation();
                data.onClose(id);
              }} 
              className="p-1.5 hover:bg-[#2d2d2d] rounded-md text-[#858585] hover:text-[#d4d4d4] transition-colors"
              title="Close"
            >
              <X size={18} />
            </button>
          </div>
        </div>
        <div 
          className="flex-1 overflow-y-auto p-6 nodrag nowheel cursor-auto bg-[#1e1e1e]"
          style={{ 
            scrollbarWidth: 'thin',
            scrollbarColor: '#3a3a3a #1e1e1e',
          }}
        >
          <StepDetail step={data.step} onClose={() => data.onClose(id)} />
        </div>
      </div>
    </ResizableWrapper>
  );
};

export default memo(StepDetailNode);
