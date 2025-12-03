import { memo, useState, useEffect } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { X } from 'lucide-react';
import { JourneyStep } from '@/app/page';
import StepChat from '@/components/StepChat';
import { ResizableWrapper } from './StepNode';

interface DocSummary {
  doc_path: string;
  summary: string;
  url: string;
  title: string;
  heading: string;
}

interface ChatNodeData {
  step: JourneyStep;
  onClose: (nodeId: string) => void;
}

const ChatNode = ({ data, id, selected }: NodeProps<ChatNodeData>) => {
  const [summaries, setSummaries] = useState<DocSummary[]>([]);

  useEffect(() => {
    const fetchSummaries = async () => {
      if (data.step.doc_paths.length === 0) {
        return;
      }

      try {
        const response = await fetch("/api/docs/summaries", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            doc_paths: data.step.doc_paths,
            max_length: 3000,
          }),
        });

        if (response.ok) {
          const resData = await response.json();
          setSummaries(resData.summaries || []);
        }
      } catch (error) {
        console.error("Error fetching summaries:", error);
      }
    };

    fetchSummaries();
  }, [data.step.doc_paths]);

  return (
    <ResizableWrapper nodeId={id} initialWidth={500} initialHeight={600} minWidth={350} minHeight={400}>
      <div 
        className={`
          w-full h-full bg-[#1e1e1e] rounded-xl shadow-2xl overflow-hidden flex flex-col
          border transition-all duration-200
          ${selected ? 'border-purple-500 ring-2 ring-purple-500' : 'border-purple-500/30'}
        `}
      >
        <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-purple-500" />
        
        <div className="bg-[#252525] p-3 border-b border-[#3a3a3a] flex justify-between items-center flex-shrink-0 select-none">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="font-semibold text-purple-400 text-sm">Chat: Step {data.step.step_number}</span>
          </div>
          <button 
            onClick={(e) => {
              e.stopPropagation();
              data.onClose(id);
            }}
            className="text-[#858585] hover:text-[#d4d4d4] p-1 hover:bg-[#2d2d2d] rounded transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div 
          className="flex-1 overflow-y-auto p-4 bg-[#1e1e1e] nodrag nowheel cursor-text"
          style={{ 
            scrollbarWidth: 'thin',
            scrollbarColor: '#3a3a3a #1e1e1e',
          }}
        >
          <StepChat step={data.step} summaries={summaries} />
        </div>
      </div>
    </ResizableWrapper>
  );
};

export default memo(ChatNode);
