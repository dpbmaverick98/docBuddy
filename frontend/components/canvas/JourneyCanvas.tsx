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
  dagreGraph.setGraph({ rankdir: 'LR' }); // Left to Right layout

  nodes.forEach((node) => {
    const width = node.type === 'stepDetailNode' ? 1000 : node.type === 'chatNode' ? 500 : 350;
    const height = node.type === 'stepDetailNode' ? 800 : node.type === 'chatNode' ? 600 : 200;
    dagreGraph.setNode(node.id, { width, height });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const width = node.type === 'stepDetailNode' ? 1000 : node.type === 'chatNode' ? 500 : 350;
    const height = node.type === 'stepDetailNode' ? 800 : node.type === 'chatNode' ? 600 : 200;
    node.position = {
      x: nodeWithPosition.x - width / 2,
      y: nodeWithPosition.y - height / 2,
    };
  });

  return { nodes, edges };
};

export default function JourneyCanvas({ journey }: JourneyCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { getNodes, getNode, setCenter, getViewport } = useReactFlow();
  const zIndexCounter = useRef(1000);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  
  // Use refs to store callbacks to avoid circular dependencies
  const onChatRef = useRef<(step: JourneyStep, sourceNodeId: string) => void>();
  const onExpandRef = useRef<(step: JourneyStep, sourceNodeId: string) => void>();

  // Helper function to pan to a node
  const panToNode = useCallback((node: Node, padding: number = 200) => {
    if (!reactFlowWrapper.current) return;
    
    const viewport = getViewport();
    const zoom = viewport.zoom;
    
    // Get viewport dimensions (in screen pixels)
    const viewportWidth = reactFlowWrapper.current.clientWidth;
    const viewportHeight = reactFlowWrapper.current.clientHeight;
    
    // Convert to flow coordinates
    const flowViewportWidth = viewportWidth / zoom;
    const flowViewportHeight = viewportHeight / zoom;
    
    // Get node dimensions
    const nodeWidth = node.width || (node.type === 'stepDetailNode' ? 800 : node.type === 'chatNode' ? 500 : 350);
    const nodeHeight = node.height || (node.type === 'stepDetailNode' ? 600 : node.type === 'chatNode' ? 600 : 200);
    
    // Node bounds
    const nodeLeft = node.position.x;
    const nodeRight = node.position.x + nodeWidth;
    const nodeTop = node.position.y;
    const nodeBottom = node.position.y + nodeHeight;
    const nodeCenterX = node.position.x + nodeWidth / 2;
    const nodeCenterY = node.position.y + nodeHeight / 2;
    
    // Calculate the area we want visible (node + padding)
    const visibleLeft = nodeLeft - padding;
    const visibleRight = nodeRight + padding;
    const visibleTop = nodeTop - padding;
    const visibleBottom = nodeBottom + padding;
    const visibleWidth = visibleRight - visibleLeft;
    const visibleHeight = visibleBottom - visibleTop;
    
    // Calculate target center to show the node with padding
    let targetCenterX = nodeCenterX;
    let targetCenterY = nodeCenterY;
    
    // If the visible area is smaller than viewport, center it
    if (visibleWidth < flowViewportWidth) {
      targetCenterX = (visibleLeft + visibleRight) / 2;
    }
    if (visibleHeight < flowViewportHeight) {
      targetCenterY = (visibleTop + visibleBottom) / 2;
    }
    
    // If the visible area is larger than viewport, ensure node is centered
    // (which is already the case)
    
    setCenter(targetCenterX, targetCenterY, { duration: 800 });
  }, [setCenter, getViewport]);

  // Helper function to find the original step node ID from any node
  const findStepNodeId = useCallback((nodeId: string, currentNodes: Node[], currentEdges: Edge[]): string | null => {
    // If it's already a step node, return it
    const node = currentNodes.find(n => n.id === nodeId);
    if (node?.type === 'stepNode') {
      return nodeId;
    }
    
    // Otherwise, find the step node it's connected to
    const connectedEdge = currentEdges.find(e => e.target === nodeId);
    if (connectedEdge) {
      const sourceNode = currentNodes.find(n => n.id === connectedEdge.source);
      if (sourceNode?.type === 'stepNode') {
        return connectedEdge.source;
      }
      // Recursively find the step node
      return findStepNodeId(connectedEdge.source, currentNodes, currentEdges);
    }
    
    return null;
  }, []);

  // Helper to spawn a chat node
  const onChat = useCallback((step: JourneyStep, sourceNodeId: string) => {
    const chatNodeId = `chat-${sourceNodeId}-${Date.now()}`;
    
    const onClose = (id: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== id));
      setEdges((eds) => eds.filter((e) => e.target !== id || e.source === id));
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

      // Position chat node: if detail exists, place it below detail; otherwise below step
      if (detailNode && stepNode) {
        chatNode.position = {
          x: detailNode.position.x,
          y: detailNode.position.y + (detailNode.height || 600) + 50,
        };
    } else if (stepNode) {
      chatNode.position = {
        x: stepNode.position.x,
        y: stepNode.position.y + 350,
      };
    }

    // Connect to the original step node, not the detail node
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
    
    // Pan to the new chat node after React Flow has measured it
    setTimeout(() => {
      const actualNode = getNode(chatNodeId);
      if (actualNode) {
        panToNode(actualNode, 200);
      }
    }, 300); // Give React Flow time to measure the node
  }, [getNodes, setNodes, setEdges, findStepNodeId, edges, panToNode]);

  // Helper to spawn a step detail node
  const onExpand = useCallback((step: JourneyStep, sourceNodeId: string) => {
    const detailNodeId = `detail-${sourceNodeId}-${Date.now()}`;
    
    const onClose = (id: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== id));
      setEdges((eds) => eds.filter((e) => e.target !== id || e.source === id));
    };

    zIndexCounter.current += 1;
    const detailNode: Node = {
      id: detailNodeId,
      type: 'stepDetailNode',
      position: { x: 0, y: 0 },
      zIndex: zIndexCounter.current,
      width: 800,
      height: 600,
      data: { 
        step,
        onClose,
        onChat: onChatRef.current!,
        sourceStepNodeId: sourceNodeId
      },
    };

    // Position it to the right of the source step node
    const currentNodes = getNodes();
    const sourceNode = currentNodes.find(n => n.id === sourceNodeId);
    if (sourceNode) {
      detailNode.position = {
        x: sourceNode.position.x + 400,
        y: sourceNode.position.y,
      };
    }

    // Create edge connecting step node to detail node
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
    
    // Pan to the new detail node after React Flow has measured it
    setTimeout(() => {
      const actualNode = getNode(detailNodeId);
      if (actualNode) {
        panToNode(actualNode, 200);
      }
    }, 300); // Give React Flow time to measure the node
  }, [getNodes, setNodes, setEdges, panToNode]);

  // Update refs when callbacks change
  useEffect(() => {
    onChatRef.current = onChat;
    onExpandRef.current = onExpand;
  }, [onChat, onExpand]);

  // Handle node click to pan to it with proper fitting
  const onNodeClick: NodeMouseHandler = useCallback((event, node) => {
    panToNode(node, 100);
  }, [panToNode]);

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
    <div ref={reactFlowWrapper} className="w-full h-full bg-[#1e1e1e]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2, minZoom: 0.5, maxZoom: 1.5 }}
        attributionPosition="bottom-right"
        minZoom={0.1}
        maxZoom={4}
        proOptions={{ hideAttribution: true }}
        panOnScroll={true}
        zoomOnScroll={true}
        panOnDrag={true}
      >
        <Background color="#2d2d2d" gap={20} size={1} variant={BackgroundVariant.Dots} />
        <Controls className="!bg-[#252525] !border-[#3a3a3a]" />
        {journey && (
          <Panel position="top-left" className="bg-[#252525]/90 backdrop-blur p-4 rounded-lg shadow border border-[#3a3a3a] max-w-md">
            <h3 className="font-bold text-[#d4d4d4]">{journey.goal}</h3>
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
