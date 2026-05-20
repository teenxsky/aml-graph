'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Graph } from '@cosmos.gl/graph'
import { Badge, Box, Flex, IconButton, Text, Tooltip } from '@radix-ui/themes'
import { TargetIcon } from '@radix-ui/react-icons'
import type { NodeData } from '@/types/graph/node'
import type { EdgeData } from '@/types/graph/edge'
import type { ClusteringResult, NodeScoringResult } from '@/types/graph/analysis'

// All RGB values normalised to [0,1] — cosmos.gl shaders clamp gl_FragColor,
// so raw 0-255 integers would collapse to white.

const ENTITY_RGB: Record<string, [number, number, number]> = {
  client: [91 / 255, 156 / 255, 246 / 255], // #5B9CF6 periwinkle blue
  account: [167 / 255, 139 / 255, 250 / 255], // #A78BFA violet
  company: [251 / 255, 146 / 255, 60 / 255], // #FB923C warm orange
  device: [244 / 255, 114 / 255, 182 / 255], // #F472B6 rose/pink
  unknown: [148 / 255, 163 / 255, 184 / 255] // #94A3B8 cool slate
}

// 16 perceptually separated hues, all vibrant on dark background.
// Extend this array if the graph has >16 clusters.
const CLUSTER_PALETTE: [number, number, number][] = [
  [66, 153, 225], // #4299E1 sky-blue
  [159, 122, 234], // #9F7AEA purple
  [56, 178, 172], // #38B2AC teal
  [237, 100, 166], // #ED64A6 pink
  [237, 137, 54], // #ED8936 amber-orange
  [72, 187, 120], // #48BB78 emerald
  [102, 126, 234], // #667EEA indigo
  [246, 173, 85], // #F6AD55 gold
  [118, 228, 247], // #76E4F7 sky
  [252, 129, 129], // #FC8181 salmon
  [104, 211, 145], // #68D391 mint
  [183, 148, 244], // #B794F4 violet-light
  [250, 240, 137], // #FAF089 lemon
  [154, 230, 180], // #9AE6B4 seafoam
  [251, 182, 206], // #FBB6CE blush
  [129, 230, 217] // #81E6D9 cyan-teal
].map(([r, g, b]) => [r / 255, g / 255, b / 255]) as [number, number, number][]

const COLOR_FRAUD: [number, number, number] = [239 / 255, 68 / 255, 68 / 255] // #EF4444
const COLOR_FOCUS: [number, number, number] = [0 / 255, 229 / 255, 255 / 255] // #00E5FF
const COLOR_EDGE_DEFAULT = [58 / 255, 70 / 255, 90 / 255, 0.55] as const

const SPACE_SIZE = 8192

function clusterRGB(id: number): [number, number, number] {
  return CLUSTER_PALETTE[id % CLUSTER_PALETTE.length]
}

function buildDegreeMap(nodes: NodeData[], edges: EdgeData[]): Map<string, number> {
  const degree = new Map<string, number>()
  for (const n of nodes) degree.set(n.id, 0)
  for (const e of edges) {
    if (degree.has(e.source)) degree.set(e.source, (degree.get(e.source) ?? 0) + 1)
    if (degree.has(e.target)) degree.set(e.target, (degree.get(e.target) ?? 0) + 1)
  }
  return degree
}

function buildColors(
  nodes: NodeData[],
  edges: EdgeData[],
  hidden: Set<string>,
  highlighted: Set<string> | null,
  clusterMap: Map<string, number> | null,
  focusCluster: number | null
): Float32Array {
  const degree = buildDegreeMap(nodes, edges)
  let maxDegree = 1
  for (const v of degree.values()) if (v > maxDegree) maxDegree = v

  const arr = new Float32Array(nodes.length * 4)
  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i]
    const isHidden = hidden.has(n.entity_type)
    const isHighlighted = highlighted !== null && highlighted.has(n.id)
    const isGreyed = highlighted !== null && !highlighted.has(n.id)
    const clusterId = clusterMap?.get(n.id) ?? -1
    const isFocusDimmed = focusCluster !== null && clusterId !== focusCluster

    let r: number, g: number, b: number
    if (isHighlighted) {
      ;[r, g, b] = COLOR_FOCUS
    } else {
      // Logarithmic brightness by degree — high-degree hubs are brighter.
      // Tune the 0.4 (min brightness) and 0.6 (brightness range) to taste.
      const deg = degree.get(n.id) ?? 0
      const brightness = 0.4 + 0.6 * (Math.log(deg + 1) / Math.log(maxDegree + 1))

      const base: [number, number, number] = n.is_laundering_node
        ? COLOR_FRAUD
        : clusterMap !== null
          ? clusterRGB(clusterId)
          : (ENTITY_RGB[n.entity_type] ?? ENTITY_RGB.unknown)

      r = base[0] * brightness
      g = base[1] * brightness
      b = base[2] * brightness
    }

    arr[i * 4] = r
    arr[i * 4 + 1] = g
    arr[i * 4 + 2] = b
    // Dimmed nodes get alpha 0.12; tune down further if they're too distracting.
    arr[i * 4 + 3] = isHidden ? 0 : isGreyed || isFocusDimmed ? 0.12 : 1
  }
  return arr
}

function buildSizes(
  nodes: NodeData[],
  hidden: Set<string>,
  sizeScale: number,
  scoring: NodeScoringResult | null
): Float32Array {
  const arr = new Float32Array(nodes.length)
  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i]
    if (hidden.has(n.entity_type)) {
      arr[i] = 0
    } else {
      const risk = scoring ? scoring.scores[i] : (n.risk_score ?? 0)
      // Min size 4px, max 16px. Tune the 4 (base) and 12 (risk range) multipliers.
      arr[i] = (4 + 12 * risk) * sizeScale
    }
  }
  return arr
}

function buildClusterStrength(n: number, scoring: NodeScoringResult | null): Float32Array {
  const arr = new Float32Array(n)
  for (let i = 0; i < n; i++) {
    const risk = scoring ? scoring.scores[i] : 0.5
    // High-risk nodes are pulled toward their cluster centroid more strongly.
    // Range [0.3, 1.0] — tune the floor (0.3) and ceiling to change cohesion.
    arr[i] = 0.3 + 0.7 * risk
  }
  return arr
}

function buildLinkColors(
  edges: EdgeData[],
  idxMap: Map<string, number>,
  nodes: NodeData[],
  highlighted: Set<string> | null
): Float32Array {
  const arr = new Float32Array(edges.length * 4)
  for (let i = 0; i < edges.length; i++) {
    const e = edges[i]
    const si = idxMap.get(e.source)
    const ti = idxMap.get(e.target)
    const isHighEdge =
      highlighted !== null &&
      si !== undefined &&
      ti !== undefined &&
      highlighted.has(nodes[si]?.id) &&
      highlighted.has(nodes[ti]?.id)

    if (e.is_laundering === true) {
      arr[i * 4] = COLOR_FRAUD[0]
      arr[i * 4 + 1] = COLOR_FRAUD[1]
      arr[i * 4 + 2] = COLOR_FRAUD[2]
      arr[i * 4 + 3] = 0.9
    } else if (isHighEdge) {
      arr[i * 4] = COLOR_FOCUS[0]
      arr[i * 4 + 1] = COLOR_FOCUS[1]
      arr[i * 4 + 2] = COLOR_FOCUS[2]
      arr[i * 4 + 3] = 0.9
    } else {
      arr[i * 4] = COLOR_EDGE_DEFAULT[0]
      arr[i * 4 + 1] = COLOR_EDGE_DEFAULT[1]
      arr[i * 4 + 2] = COLOR_EDGE_DEFAULT[2]
      arr[i * 4 + 3] = COLOR_EDGE_DEFAULT[3]
    }
  }
  return arr
}

function buildLinkWidths(
  edges: EdgeData[],
  idxMap: Map<string, number>,
  nodes: NodeData[],
  highlighted: Set<string> | null,
  base: number
): Float32Array {
  const arr = new Float32Array(edges.length)
  for (let i = 0; i < edges.length; i++) {
    const e = edges[i]
    const si = idxMap.get(e.source)
    const ti = idxMap.get(e.target)
    const hi =
      highlighted !== null &&
      si !== undefined &&
      ti !== undefined &&
      highlighted.has(nodes[si]?.id) &&
      highlighted.has(nodes[ti]?.id)
    arr[i] = e.is_laundering === true || hi ? base * 2.5 : base
  }
  return arr
}

export interface SimConfig {
  gravity?: number
  repulsion?: number
  linkSpring?: number
  clusterStrength?: number
}

export interface GraphCanvasProps {
  nodes: NodeData[]
  edges: EdgeData[]
  isReady: boolean
  hiddenEntityTypes: Set<string>
  highlightedNodeIds: Set<string> | null
  onNodeClick: (node: NodeData | null) => void
  sizeScale: number
  zoomTarget: { id: string; ts: number } | null
  /** Track A — unsupervised; independent of scoring */
  clustering: ClusteringResult | null
  /** Привязка node_id → cluster_id; надёжнее позиционного индекса из clustering.labels */
  clusterMap: Map<string, number> | null
  /** Track B — supervised/heuristic; independent of clustering */
  scoring: NodeScoringResult | null
  /** If set, dim all clusters except this one */
  focusCluster: number | null
  simConfig?: SimConfig
  /** Mirrors the externally selected node id; when null, focus highlight is cleared */
  selectedNodeId?: string | null
  /** Increment to trigger a full re-layout (re-scatters positions and restarts simulation) */
  rerunTrigger?: number
}

export default function GraphCanvas({
  nodes,
  edges,
  isReady,
  hiddenEntityTypes,
  highlightedNodeIds,
  onNodeClick,
  sizeScale,
  zoomTarget,
  clustering,
  clusterMap,
  scoring,
  focusCluster,
  simConfig,
  selectedNodeId,
  rerunTrigger
}: GraphCanvasProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<Graph | null>(null)
  const nodesRef = useRef<NodeData[]>(nodes)
  const onNodeClickRef = useRef(onNodeClick)
  const idxMapRef = useRef<Map<string, number>>(new Map())
  const validEdgesRef = useRef<EdgeData[]>([])
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const [hovered, setHovered] = useState<{ node: NodeData; index: number } | null>(null)
  const [focusNeighbors, setFocusNeighbors] = useState<Set<string> | null>(null)

  // When selectedNodeId is cleared externally, suppress the neighbor highlight derived from it
  const effectiveFocusNeighbors = selectedNodeId ? focusNeighbors : null

  useEffect(() => {
    nodesRef.current = nodes
    onNodeClickRef.current = onNodeClick
  })

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect()
    setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }, [])

  useEffect(() => {
    if (!divRef.current) return
    graphRef.current = new Graph(divRef.current, {
      backgroundColor: '#0d1117',
      enableSimulation: true,
      fitViewOnInit: true,
      fitViewDelay: 200, // ms before the initial fit-to-view zoom fires
      renderHoveredPointRing: true,
      hoveredPointCursor: 'pointer',
      pointDefaultSize: 4,
      linkDefaultColor: [...COLOR_EDGE_DEFAULT] as [number, number, number, number],
      linkVisibilityDistanceRange: [20, 5000],
      linkVisibilityMinTransparency: 0.8,
      curvedLinks: false,

      // spaceSize: canvas coordinate system size. Library max is 8192.
      spaceSize: SPACE_SIZE,

      // simulationDecay: how fast alpha drops per tick (smaller = cools slower).
      // Default 5000 — we use 2000 so it settles faster without manual pause.
      // Raise toward 5000 if you want longer organic spreading.
      // simulationDecay: 2000,

      // simulationFriction: fraction of velocity RETAINED each tick [0,1].
      // Default 0.85 — keeps 85% velocity → nearly never stops.
      // 0.15 means 85% damped per tick, settles in a few seconds.
      // Raise toward 0.5 if the layout collapses too quickly.
      // simulationFriction: 0.15,

      // simulationGravity: pull toward canvas centre [0, ∞].
      // Too high → everything collapses to one point. Too low → disconnected components drift off.
      // simulationGravity: simConfig?.gravity ?? 0.05,

      // simulationRepulsion: node-node repulsion strength [0, ∞].
      // Raise for more spread; lower if clusters are too far apart.
      // simulationRepulsion: simConfig?.repulsion ?? 2.0,

      // simulationRepulsionTheta: Barnes–Hut approximation threshold.
      // Higher = faster but less accurate repulsion. 1.15 is default; 1.5 gives good perf.
      // simulationRepulsionTheta: 1.5,

      // simulationLinkSpring: edge spring stiffness [0, ∞].
      // High values pull connected nodes tightly together; low lets them breathe.
      // simulationLinkSpring: simConfig?.linkSpring ?? 0.3,

      // simulationLinkDistance: preferred rest length for edge springs (pixels).
      // simulationLinkDistance: 20,

      // simulationCluster: strength of cluster-centroid attraction [0, ∞].
      // Works only when setPointClusters / setClusterPositions are called.
      // simulationCluster: simConfig?.clusterStrength ?? 0.4,

      onPointMouseOver: (index: number) => {
        const node = nodesRef.current[index]
        if (node) setHovered({ node, index })
      },
      onPointMouseOut: () => setHovered(null),
      onPointClick: (index: number) => {
        const node = nodesRef.current[index] ?? null
        onNodeClickRef.current(node)
        if (graphRef.current && node) {
          graphRef.current.zoomToPointByIndex(index, 500, 4)
          const neighbors = new Set<string>([node.id])
          for (const e of validEdgesRef.current) {
            if (e.source === node.id) neighbors.add(e.target)
            else if (e.target === node.id) neighbors.add(e.source)
          }
          setFocusNeighbors(neighbors)
        }
      },
      onBackgroundClick: () => {
        onNodeClickRef.current(null)
        setFocusNeighbors(null)
      }
    })
    return () => {
      graphRef.current?.destroy()
      graphRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!graphRef.current || !simConfig) return
    graphRef.current.setConfig({
      simulationGravity: simConfig.gravity ?? 0.05,
      simulationRepulsion: simConfig.repulsion ?? 2.0,
      simulationLinkSpring: simConfig.linkSpring ?? 0.3,
      simulationCluster: simConfig.clusterStrength ?? 0.4
    })
    graphRef.current.start()
    // Кратковременная симуляция после изменения параметров — останавливаем через 2с
    setTimeout(() => graphRef.current?.pause(), 2000)
  }, [simConfig])

  useEffect(() => {
    const g = graphRef.current
    if (!g || !isReady || nodes.length === 0) return

    const idxMap = new Map<string, number>()
    nodes.forEach((n, i) => idxMap.set(n.id, i))
    idxMapRef.current = idxMap

    // Координаты бэкенда нормализованы в [-1, 1] — масштабируем в пространство cosmos.gl.
    const SPACE_HALF = SPACE_SIZE / 2
    const scatter = SPACE_HALF * 1.2
    const positions = new Float32Array(nodes.length * 2)
    for (let i = 0; i < nodes.length; i++) {
      const x = nodes[i].x
      const y = nodes[i].y
      positions[i * 2] = x != null ? x * SPACE_HALF : (Math.random() - 0.5) * scatter
      positions[i * 2 + 1] = y != null ? y * SPACE_HALF : (Math.random() - 0.5) * scatter
    }

    const validEdges = edges.filter(e => idxMap.has(e.source) && idxMap.has(e.target))
    validEdgesRef.current = validEdges
    setFocusNeighbors(null)

    const links = new Float32Array(validEdges.length * 2)
    for (let i = 0; i < validEdges.length; i++) {
      links[i * 2] = idxMap.get(validEdges[i].source)!
      links[i * 2 + 1] = idxMap.get(validEdges[i].target)!
    }

    const count = nodes.length
    const baseWidth = count < 500 ? 2 : count < 2000 ? 1.5 : 1

    g.setPointPositions(positions)
    g.setPointColors(
      buildColors(
        nodes,
        validEdges,
        hiddenEntityTypes,
        highlightedNodeIds,
        clusterMap,
        focusCluster
      )
    )
    g.setPointSizes(buildSizes(nodes, hiddenEntityTypes, sizeScale, scoring))
    g.setPointShapes(new Float32Array(nodes.length))
    g.setLinks(links)
    g.setLinkColors(buildLinkColors(validEdges, idxMap, nodes, highlightedNodeIds))
    g.setLinkWidths(buildLinkWidths(validEdges, idxMap, nodes, highlightedNodeIds, baseWidth))

    // Track A: центроиды кластеров масштабируем в SPACE_SIZE*0.25 радиус.
    if (clustering?.cluster_centroids_2d && clusterMap) {
      const raw = clustering.cluster_centroids_2d
      const maxR = Math.max(...raw.map(([x, y]) => Math.sqrt(x * x + y * y)), 1)
      const scale = (SPACE_SIZE * 0.25) / maxR
      const clusterPos: number[] = new Array(2 * clustering.n_clusters)
      raw.forEach(([x, y], c) => {
        clusterPos[2 * c] = x * scale
        clusterPos[2 * c + 1] = y * scale
      })
      // Привязка узлов к кластерам по nodeId через clusterMap (надёжнее позиционного индекса)
      const pointClusters = Array.from(
        { length: nodes.length },
        (_, i) => clusterMap.get(nodes[i].id) ?? -1
      )
      g.setPointClusters(pointClusters)
      g.setClusterPositions(clusterPos)
    }

    // Track B: высокорисковые узлы притягиваются к центроиду сильнее
    g.setPointClusterStrength(buildClusterStrength(nodes.length, scoring))

    // Координаты вычислены сервером — останавливаем симуляцию после первого рендера.
    g.render(1)
    g.pause()
  }, [isReady, nodes, edges, rerunTrigger]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const g = graphRef.current
    if (!g || nodes.length === 0) return
    const idxMap = idxMapRef.current
    const validEdges = validEdgesRef.current
    const count = nodes.length
    const baseWidth = count < 500 ? 2 : count < 2000 ? 1.5 : 1

    const effectiveHighlight = effectiveFocusNeighbors ?? highlightedNodeIds
    g.setPointColors(
      buildColors(
        nodes,
        validEdgesRef.current,
        hiddenEntityTypes,
        effectiveHighlight,
        clusterMap,
        focusCluster
      )
    )
    g.setPointSizes(buildSizes(nodes, hiddenEntityTypes, sizeScale, scoring))
    g.setLinkColors(buildLinkColors(validEdges, idxMap, nodes, effectiveHighlight))
    g.setLinkWidths(buildLinkWidths(validEdges, idxMap, nodes, effectiveHighlight, baseWidth))
    g.setPointClusterStrength(buildClusterStrength(nodes.length, scoring))
    g.render()
  }, [
    hiddenEntityTypes,
    highlightedNodeIds,
    effectiveFocusNeighbors,
    sizeScale,
    nodes,
    clustering,
    scoring,
    focusCluster,
    clusterMap
  ])

  useEffect(() => {
    if (!zoomTarget || !graphRef.current) return
    const idx = idxMapRef.current.get(zoomTarget.id)
    if (idx !== undefined) graphRef.current.zoomToPointByIndex(idx, 600, 5)
  }, [zoomTarget])

  const riskScore = hovered
    ? scoring
      ? scoring.scores[hovered.index]
      : (hovered.node.risk_score ?? 0)
    : 0
  const clusterLabel = hovered && clusterMap ? (clusterMap.get(hovered.node.id) ?? null) : null

  return (
    <div
      className="w-full h-full"
      style={{ position: 'relative', background: '#0d1117' }}
      onMouseMove={handleMouseMove}
    >
      <div ref={divRef} className="w-full h-full" />

      {/* Fit-view button */}
      <div style={{ position: 'absolute', bottom: 16, right: 16, zIndex: 20 }}>
        <Tooltip content="Вписать в экран">
          <IconButton
            size="2"
            variant="soft"
            color="gray"
            style={{ cursor: 'pointer' }}
            onClick={() => graphRef.current?.fitView(600)}
          >
            <TargetIcon />
          </IconButton>
        </Tooltip>
      </div>

      {hovered && (
        <div
          style={{
            position: 'absolute',
            left: mousePos.x + 14,
            top: mousePos.y - 10,
            pointerEvents: 'none',
            zIndex: 100
          }}
        >
          <Box
            p="2"
            style={{
              background: 'var(--color-panel-solid)',
              border: '1px solid var(--gray-5)',
              borderRadius: 'var(--radius-3)',
              minWidth: 160,
              maxWidth: 240,
              boxShadow: '0 4px 16px rgba(0,0,0,0.5)'
            }}
          >
            <Flex direction="column" gap="1">
              <Text
                size="1"
                weight="medium"
                style={{ fontFamily: 'var(--font-mono)', wordBreak: 'break-all' }}
              >
                {hovered.node.id.length > 24 ? hovered.node.id.slice(0, 22) + '…' : hovered.node.id}
              </Text>
              <Flex align="center" gap="1" wrap="wrap">
                <Badge size="1" color="gray" variant="soft">
                  {hovered.node.entity_type}
                </Badge>
                {clusterLabel !== null && (
                  <Badge size="1" color="blue" variant="soft">
                    кластер {clusterLabel}
                  </Badge>
                )}
                <Badge
                  size="1"
                  color={riskScore > 0.7 ? 'red' : riskScore > 0.4 ? 'amber' : 'green'}
                  variant="soft"
                >
                  риск {Math.round(riskScore * 100)}%
                </Badge>
              </Flex>
              {hovered.node.is_laundering_node && (
                <Badge size="1" color="red" variant="surface">
                  Подозрение в отмывании
                </Badge>
              )}
              {hovered.node.alerts.length > 0 && (
                <Text size="1" color="amber">
                  {hovered.node.alerts.length} предупрежд.
                </Text>
              )}
            </Flex>
          </Box>
        </div>
      )}
    </div>
  )
}
