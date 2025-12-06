import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  MarkerType,
  Panel,
  ReactFlowProvider,
  useReactFlow,
  BackgroundVariant,
  NodeMouseHandler,
  getRectOfNodes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { Maximize2, MessageSquare } from 'lucide-react';
import { Journey, JourneyStep } from '@/app/page';
import StepNode from './nodes/StepNode';
import ChatNode from './nodes/ChatNode';
import StepDetailNode from './nodes/StepDetailNode';

// Node Types
const nodeTypes = {
  stepNode: StepNode,
  chatNode: ChatNode,
  stepDetailNode: StepDetailNode,
};

interface JourneyCanvasProps {
  journey: Journey | null;
}

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  dagreGraph.setGraph({ rankdir: 'LR' });

  nodes.forEach((node) => {
    // Use actual node dimensions for layout
    const width = node.type === 'stepDetailNode' ? 800 : node.type === 'chatNode' ? 500 : 350;
    const height = node.type === 'stepDetailNode' ? 600 : node.type === 'chatNode' ? 600 : 200;
    dagreGraph.setNode(node.id, { width, height });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.position = {
      x: nodeWithPosition.x - (node.width || 350) / 2,
      y: nodeWithPosition.y - (node.height || 200) / 2,
    };
  });

  return { nodes, edges };
};

export default function JourneyCanvas({ journey }: JourneyCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { fitView, getNode, getNodes } = useReactFlow();
  const zIndexCounter = useRef(1000);
  
  const onChatRef = useRef<(step: JourneyStep, sourceNodeId: string) => void>();
  const onExpandRef = useRef<(step: JourneyStep, sourceNodeId: string) => void>();

  // CRITICAL: Wait for node to be measured before fitting
  const fitToNode = useCallback((nodeId: string, padding: number = 0.2) => {
    // Wait for React Flow to measure the node
    const checkAndFit = () => {
      const node = getNode(nodeId);
      
      // Debug: Check if node exists and has dimensions
      console.log('Fitting to node:', nodeId, {
        exists: !!node,
        width: node?.width,
        height: node?.height,
        position: node?.position,
      });

      if (node && node.width && node.height) {
        console.log('✅ Node measured, fitting view');
        fitView({
          nodes: [node],
          padding,
          duration: 800,
          minZoom: 0.5,
          maxZoom: 1.5,
        });
      } else {
        console.log('⏳ Node not measured yet, retrying...');
        setTimeout(checkAndFit, 50); // Retry after 50ms
      }
    };

    // Start checking immediately, but delay a bit to let React render
    setTimeout(checkAndFit, 100);
  }, [fitView, getNode]);

  const findStepNodeId = useCallback((nodeId: string, currentNodes: Node[], currentEdges: Edge[]): string | null => {
    const node = currentNodes.find(n => n.id === nodeId);
    if (node?.type === 'stepNode') return nodeId;
    
    const connectedEdge = currentEdges.find(e => e.target === nodeId);
    if (connectedEdge) {
      const sourceNode = currentNodes.find(n => n.id === connectedEdge.source);
      if (sourceNode?.type === 'stepNode') return connectedEdge.source;
      return findStepNodeId(connectedEdge.source, currentNodes, currentEdges);
    }
    
    return null;
  }, []);

  // Helper to spawn a chat node
  const onChat = useCallback((step: JourneyStep, sourceNodeId: string) => {
    const chatNodeId = `chat-${sourceNodeId}-${Date.now()}`;
    
    const onClose = (id: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== id));
      setEdges((eds) => eds.filter((e) => !(e.target === id || e.source === id)));
    };

    // Find the original step node to position relative to it
    const currentNodes = getNodes();
    const currentEdges = edges;
    const stepNodeId = findStepNodeId(sourceNodeId, currentNodes, currentEdges) || sourceNodeId;
    const stepNode = currentNodes.find(n => n.id === stepNodeId);
    
    // Check if there's already a detail node for this step
    const detailNode = currentNodes.find(n => 
      n.type === 'stepDetailNode' && 
      n.data?.step?.step_number === step.step_number
    );

    zIndexCounter.current += 1;
    const chatNode: Node = {
      id: chatNodeId,
      type: 'chatNode',
      position: { x: 0, y: 0 },
      zIndex: zIndexCounter.current,
      width: 500,
      height: 600,
      data: { 
        step, 
        onClose
      },
    };

    if (detailNode && stepNode) {
      chatNode.position = {
        x: detailNode.position.x,
        y: detailNode.position.y + (detailNode.height || 800) + 50,
      };
    } else if (stepNode) {
      chatNode.position = {
        x: stepNode.position.x,
        y: stepNode.position.y + 350,
      };
    }

    const chatEdge: Edge = {
      id: `e-${stepNodeId}-${chatNodeId}`,
      source: stepNodeId,
      target: chatNodeId,
      sourceHandle: 'chat',
      animated: true,
      style: { stroke: '#a855f7', strokeWidth: 2 },
    };

    setNodes((nds) => nds.concat(chatNode));
    setEdges((eds) => eds.concat(chatEdge));
    
    // Use our new fit function
    fitToNode(chatNodeId, 0.2);
  }, [getNodes, setNodes, setEdges, findStepNodeId, edges, fitToNode]);

  // Helper to spawn a step detail node
  const onExpand = useCallback((step: JourneyStep, sourceNodeId: string) => {
    const detailNodeId = `detail-${sourceNodeId}-${Date.now()}`;
    
    const onClose = (id: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== id));
      setEdges((eds) => eds.filter((e) => !(e.target === id || e.source === id)));
    };

    zIndexCounter.current += 1;
    const detailNode: Node = {
      id: detailNodeId,
      type: 'stepDetailNode',
      position: { x: 0, y: 0 },
      zIndex: zIndexCounter.current,
      width: 800, // Reduced from 1000
      height: 600, // Reduced from 800
      data: { 
        step,
        onClose,
        onChat: onChatRef.current!,
        sourceStepNodeId: sourceNodeId
      },
    };

    const currentNodes = getNodes();
    const sourceNode = currentNodes.find(n => n.id === sourceNodeId);
    if (sourceNode) {
      detailNode.position = {
        x: sourceNode.position.x + 400,
        y: sourceNode.position.y,
      };
    }

    const detailEdge: Edge = {
      id: `e-${sourceNodeId}-${detailNodeId}`,
      source: sourceNodeId,
      target: detailNodeId,
      sourceHandle: 'expand',
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: '#2563eb', strokeWidth: 2 },
    };

    setNodes((nds) => nds.concat(detailNode));
    setEdges((eds) => eds.concat(detailEdge));
    
    // Use our new fit function
    fitToNode(detailNodeId, 0.15);
  }, [getNodes, setNodes, setEdges, fitToNode]);

  // Update refs when callbacks change
  useEffect(() => {
    onChatRef.current = onChat;
    onExpandRef.current = onExpand;
  }, [onChat, onExpand]);

  // Simple node click handler
  const onNodeClick = useCallback<NodeMouseHandler>((event, node) => {
    // Don't pan when clicking interactive elements inside node
    const target = event.target as HTMLElement;
    if (target.closest('button') || target.closest('input') || target.closest('textarea')) {
      return;
    }
    fitToNode(node.id, 0.15);
  }, [fitToNode]);

  // Initial Setup - only depends on journey, not callbacks
  useEffect(() => {
    if (!journey) {
      setNodes([]);
      setEdges([]);
      zIndexCounter.current = 1000;
      return;
    }

    const initialNodes: Node[] = journey.steps.map((step) => ({
      id: `step-${step.step_number}`,
      type: 'stepNode',
      data: {
        step,
        onChat: (s: JourneyStep, id: string) => onChatRef.current?.(s, id),
        onExpand: (s: JourneyStep, id: string) => onExpandRef.current?.(s, id)
      },
      position: { x: 0, y: 0 },
    }));

    const initialEdges: Edge[] = journey.steps
      .slice(0, -1)
      .map((step, index) => ({
        id: `e-${step.step_number}-${journey.steps[index + 1].step_number}`,
        source: `step-${step.step_number}`,
        target: `step-${journey.steps[index + 1].step_number}`,
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: '#2563eb', strokeWidth: 2 },
      }));

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      initialNodes,
      initialEdges
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [journey, setNodes, setEdges]); // Removed onChat and onExpand from dependencies

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  return (
    <div className="w-full h-full bg-[#1e1e1e]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-right"
        minZoom={0.1}
        maxZoom={4}
        // CRITICAL: Enable these
        panOnScroll={true}
        zoomOnScroll={true}
        panOnDrag={true}
        zoomOnPinch={true}
        // Prevent scroll conflicts
        preventScrolling={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#2d2d2d" gap={20} size={1} variant={BackgroundVariant.Dots} />
        <Controls className="!bg-[#252525] !border-[#3a3a3a]" />
        {journey && (
          <Panel position="top-left" className="bg-[#252525]/90 backdrop-blur p-4 rounded-lg shadow border border-[#3a3a3a] max-w-md">
            <h3 className="font-bold text-[#d4d4d4]">
              {journey.intent?.goal || journey.goal}
            </h3>
            {journey.intent?.goal && journey.intent.goal !== journey.goal && (
              <p className="text-xs text-[#5a5a5a] italic mb-1">
                "{journey.goal}"
              </p>
            )}
            {journey.intent?.complexity && (
              <p className="text-xs text-[#a855f7] font-medium mb-1">
                {journey.intent.complexity.charAt(0).toUpperCase() + journey.intent.complexity.slice(1)} Level
              </p>
            )}
            <p className="text-sm text-[#858585]">
              {journey.total_steps} steps • {journey.estimated_time}
            </p>
            <p className="text-xs text-[#5a5a5a] mt-2">
              Click <Maximize2 className="inline w-3 h-3"/> to expand a step. Click <MessageSquare className="inline w-3 h-3"/> to chat about it.
            </p>
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
}
