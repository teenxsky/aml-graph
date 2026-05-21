'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Graph } from '@cosmos.gl/graph'
import { Badge, Box, Flex, IconButton, Text, Tooltip } from '@radix-ui/themes'
import { TargetIcon } from '@radix-ui/react-icons'
import type { NodeData } from '@/types/graph/node'
import type { EdgeData } from '@/types/graph/edge'
import type { ClusteringResult, NodeScoringResult } from '@/types/graph/analysis'

// Entity type: primary colour for cosmos.gl points and canvas overlay.
const ENTITY_RGB: Record<string, [number, number, number]> = {
  account: [102 / 255, 187 / 255, 106 / 255],             // #66bb6a — счёт
  individual: [79 / 255, 195 / 255, 247 / 255],            // #4fc3f7 — физлицо
  business: [255 / 255, 167 / 255, 38 / 255],              // #ffa726 — юрлицо
  payment_institution: [171 / 255, 71 / 255, 188 / 255],   // #ab47bc — платёжный институт
  // backward compat for old data
  client: [79 / 255, 195 / 255, 247 / 255],
  company: [255 / 255, 167 / 255, 38 / 255],
  device: [171 / 255, 71 / 255, 188 / 255],
  unknown: [107 / 255, 114 / 255, 128 / 255]               // #6b7280
}

const ENTITY_HEX: Record<string, string> = {
  account: '#66bb6a',
  individual: '#4fc3f7',
  business: '#ffa726',
  payment_institution: '#ab47bc',
  client: '#4fc3f7',
  company: '#ffa726',
  device: '#ab47bc',
  unknown: '#6b7280'
}

const ENTITY_LABELS: Record<string, string> = {
  account: 'Счета',
  individual: 'Физлица',
  business: 'Юрлица',
  payment_institution: 'Платёжные институты',
  client: 'Клиенты',
  company: 'Юрлица',
  device: 'Устройства',
  unknown: 'Прочее'
}

const ROLE_LABELS: Record<string, string> = {
  hub: 'Концентратор',
  transit: 'Транзитный',
  isolated: 'Одиночный',
  regular: 'Обычный'
}

const ROLE_ICONS: Record<string, { symbol: string; color: string }> = {
  hub: { symbol: '◉', color: '#ff453a' },
  transit: { symbol: '⇄', color: '#ff9f0a' },
  isolated: { symbol: '·', color: '#9ca3af' }
  // regular — без значка
}

const PATTERN_HEX: Record<string, string> = {
  cycles: '#ff453a',
  fanout: '#ff9f0a',
  transit: '#ffd60a',
  shared_device: '#bf5af2'
}

const COLOR_FRAUD: [number, number, number] = [239 / 255, 68 / 255, 68 / 255]
const COLOR_FOCUS: [number, number, number] = [0 / 255, 229 / 255, 255 / 255]
const COLOR_EDGE_DEFAULT = [58 / 255, 70 / 255, 90 / 255, 0.55] as const

const SPACE_SIZE = 8192
const SPACE_HALF = SPACE_SIZE / 2

function buildDegreeMap(nodes: NodeData[], edges: EdgeData[]): Map<string, number> {
  const degree = new Map<string, number>()
  for (const n of nodes) degree.set(n.id, 0)
  for (const e of edges) {
    if (degree.has(e.source)) degree.set(e.source, (degree.get(e.source) ?? 0) + 1)
    if (degree.has(e.target)) degree.set(e.target, (degree.get(e.target) ?? 0) + 1)
  }
  return degree
}

function computeLinkWidth(e: EdgeData): number {
  if (!e.amount_paid || e.amount_paid <= 0) return 1
  return Math.max(1, Math.log10(e.amount_paid / 8000 + 1) * 2.5)
}

function buildColors(
  nodes: NodeData[],
  edges: EdgeData[],
  hidden: Set<string>,
  hiddenBehavioralRoles: Set<string>,
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
    const isHidden = hidden.has(n.entity_type) || hiddenBehavioralRoles.has(n.behavioral_role)
    const isHighlighted = highlighted !== null && highlighted.has(n.id)
    const isGreyed = highlighted !== null && !highlighted.has(n.id)
    const clusterId = clusterMap?.get(n.id) ?? -1
    const isFocusDimmed = focusCluster !== null && clusterId !== focusCluster

    let r: number, g: number, b: number

    if (isHighlighted) {
      ;[r, g, b] = COLOR_FOCUS
    } else if (n.is_laundering_node) {
      const deg = degree.get(n.id) ?? 0
      const brightness = 0.4 + 0.6 * (Math.log(deg + 1) / Math.log(maxDegree + 1))
      r = COLOR_FRAUD[0] * brightness
      g = COLOR_FRAUD[1] * brightness
      b = COLOR_FRAUD[2] * brightness
    } else {
      const deg = degree.get(n.id) ?? 0
      const brightness = 0.4 + 0.6 * (Math.log(deg + 1) / Math.log(maxDegree + 1))
      const base = ENTITY_RGB[n.entity_type] ?? ENTITY_RGB.unknown
      const variation = clusterMap !== null && clusterId >= 0 ? (clusterId % 5) * 0.06 - 0.12 : 0
      r = Math.max(0, Math.min(1, base[0] * brightness + variation))
      g = Math.max(0, Math.min(1, base[1] * brightness + variation))
      b = Math.max(0, Math.min(1, base[2] * brightness + variation))
    }

    arr[i * 4] = r
    arr[i * 4 + 1] = g
    arr[i * 4 + 2] = b
    arr[i * 4 + 3] = isHidden ? 0 : isGreyed || isFocusDimmed ? 0.12 : 1
  }
  return arr
}

function buildSizes(
  nodes: NodeData[],
  hidden: Set<string>,
  hiddenBehavioralRoles: Set<string>,
  sizeScale: number,
  scoring: NodeScoringResult | null
): Float32Array {
  const arr = new Float32Array(nodes.length)
  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i]
    if (hidden.has(n.entity_type) || hiddenBehavioralRoles.has(n.behavioral_role)) {
      arr[i] = 0
    } else {
      const risk = scoring ? scoring.scores[i] : (n.risk_score ?? 0)
      arr[i] = (4 + 12 * risk) * sizeScale
    }
  }
  return arr
}

function buildClusterStrength(n: number, scoring: NodeScoringResult | null): Float32Array {
  const arr = new Float32Array(n)
  for (let i = 0; i < n; i++) {
    const risk = scoring ? scoring.scores[i] : 0.5
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
  highlighted: Set<string> | null
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
    const base = computeLinkWidth(e)
    arr[i] = e.is_laundering === true || hi ? base * 2.5 : base
  }
  return arr
}

function drawEntityHalos(
  ctx: CanvasRenderingContext2D,
  typeCentroids: Record<string, [number, number]>,
  nodes: NodeData[],
  hidden: Set<string>,
  g: Graph
) {
  for (const [type, [cx, cy]] of Object.entries(typeCentroids)) {
    if (hidden.has(type)) continue
    const typeNodes = nodes.filter(n => n.entity_type === type && !hidden.has(n.entity_type))
    if (typeNodes.length < 2) continue

    const [cxS, cyS] = g.spaceToScreenPosition([cx * SPACE_HALF, cy * SPACE_HALF])

    let maxR = 0
    for (const n of typeNodes) {
      const [nx, ny] = g.spaceToScreenPosition([(n.x ?? 0) * SPACE_HALF, (n.y ?? 0) * SPACE_HALF])
      const d = Math.hypot(nx - cxS, ny - cyS)
      if (d > maxR) maxR = d
    }
    maxR += 55

    const color = ENTITY_HEX[type] ?? ENTITY_HEX.unknown

    ctx.beginPath()
    ctx.arc(cxS, cyS, maxR, 0, Math.PI * 2)
    ctx.fillStyle = color + '14'
    ctx.fill()
    ctx.strokeStyle = color + '25'
    ctx.lineWidth = 1
    ctx.stroke()

    ctx.font = 'bold 12px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillStyle = color + '80'
    ctx.fillText(ENTITY_LABELS[type] ?? type, cxS, cyS - maxR + 16)
  }
}

function drawBehavioralBadges(
  ctx: CanvasRenderingContext2D,
  nodes: NodeData[],
  hiddenBehavioralRoles: Set<string>,
  g: Graph
) {
  for (const n of nodes) {
    const icon = ROLE_ICONS[n.behavioral_role]
    if (!icon) continue
    if (hiddenBehavioralRoles.has(n.behavioral_role)) continue

    const [sx, sy] = g.spaceToScreenPosition([(n.x ?? 0) * SPACE_HALF, (n.y ?? 0) * SPACE_HALF])
    const offset = 12

    ctx.font = '11px sans-serif'
    ctx.fillStyle = icon.color
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.globalAlpha = 0.9
    ctx.fillText(icon.symbol, sx + offset, sy - offset)
    ctx.globalAlpha = 1
  }
}

function drawFocusedArrows(
  ctx: CanvasRenderingContext2D,
  selectedId: string,
  neighborEdges: EdgeData[],
  nodesMap: Map<string, NodeData>,
  g: Graph
) {
  for (const e of neighborEdges) {
    const src = nodesMap.get(e.source)
    const tgt = nodesMap.get(e.target)
    if (!src || !tgt) continue

    const [x1, y1] = g.spaceToScreenPosition([(src.x ?? 0) * SPACE_HALF, (src.y ?? 0) * SPACE_HALF])
    const [x2, y2] = g.spaceToScreenPosition([(tgt.x ?? 0) * SPACE_HALF, (tgt.y ?? 0) * SPACE_HALF])

    const dx = x2 - x1
    const dy = y2 - y1
    const dist = Math.hypot(dx, dy) || 1
    const nx = dx / dist
    const ny = dy / dist

    const tgtR = (g.getPointRadiusByIndex(nodesMap.size) ?? 8) + 4
    const ex = x2 - nx * tgtR
    const ey = y2 - ny * tgtR

    const lw = computeLinkWidth(e)
    ctx.beginPath()
    ctx.moveTo(x1, y1)
    ctx.lineTo(ex, ey)
    ctx.strokeStyle = '#4a9eff'
    ctx.lineWidth = lw
    ctx.globalAlpha = 0.85
    ctx.stroke()

    const angle = Math.atan2(dy, dx)
    const headLen = 9
    const spread = 0.42
    ctx.beginPath()
    ctx.moveTo(ex, ey)
    ctx.lineTo(ex - headLen * Math.cos(angle - spread), ey - headLen * Math.sin(angle - spread))
    ctx.moveTo(ex, ey)
    ctx.lineTo(ex - headLen * Math.cos(angle + spread), ey - headLen * Math.sin(angle + spread))
    ctx.stroke()

    ctx.globalAlpha = 1
  }
}

function drawTransactionParticles(
  ctx: CanvasRenderingContext2D,
  neighborEdges: EdgeData[],
  nodesMap: Map<string, NodeData>,
  g: Graph
) {
  const now = performance.now() / 1000

  neighborEdges.forEach((e, i) => {
    if (!e.payment_format && !e.amount_paid) return
    const src = nodesMap.get(e.source)
    const tgt = nodesMap.get(e.target)
    if (!src || !tgt) return

    const [x1, y1] = g.spaceToScreenPosition([(src.x ?? 0) * SPACE_HALF, (src.y ?? 0) * SPACE_HALF])
    const [x2, y2] = g.spaceToScreenPosition([(tgt.x ?? 0) * SPACE_HALF, (tgt.y ?? 0) * SPACE_HALF])

    for (let p = 0; p < 2; p++) {
      const t = (now * 0.35 + i * 0.28 + p * 0.5) % 1
      const x = x1 + (x2 - x1) * t
      const y = y1 + (y2 - y1) * t
      const alpha = Math.sin(t * Math.PI) * 0.85

      ctx.globalAlpha = alpha
      ctx.fillStyle = '#4a9eff'
      ctx.beginPath()
      ctx.arc(x, y, 2.2, 0, Math.PI * 2)
      ctx.fill()
    }
  })

  ctx.globalAlpha = 1
}

// ── Component ────────────────────────────────────────────────────────────────

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
  hiddenBehavioralRoles?: Set<string>
  highlightedNodeIds: Set<string> | null
  onNodeClick: (node: NodeData | null) => void
  sizeScale: number
  zoomTarget: { id: string; ts: number } | null
  clustering: ClusteringResult | null
  clusterMap: Map<string, number> | null
  scoring: NodeScoringResult | null
  focusCluster: number | null
  simConfig?: SimConfig
  selectedNodeId?: string | null
  rerunTrigger?: number
  typeCentroids?: Record<string, [number, number]>
  nodePatterns?: Map<string, string[]>
}

export default function GraphCanvas({
  nodes,
  edges,
  isReady,
  hiddenEntityTypes,
  hiddenBehavioralRoles,
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
  rerunTrigger,
  typeCentroids,
  nodePatterns
}: GraphCanvasProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null)
  const graphRef = useRef<Graph | null>(null)
  const nodesRef = useRef<NodeData[]>(nodes)
  const onNodeClickRef = useRef(onNodeClick)
  const idxMapRef = useRef<Map<string, number>>(new Map())
  const validEdgesRef = useRef<EdgeData[]>([])
  const nodesMapRef = useRef<Map<string, NodeData>>(new Map())

  const typeCentroidsRef = useRef<Record<string, [number, number]>>(typeCentroids ?? {})
  const nodePatternsRef = useRef<Map<string, string[]>>(nodePatterns ?? new Map())
  const selectedNodeIdRef = useRef<string | null>(selectedNodeId ?? null)
  const hiddenRef = useRef<Set<string>>(hiddenEntityTypes)
  const hiddenBehavioralRolesRef = useRef<Set<string>>(hiddenBehavioralRoles ?? new Set())
  const focusNeighborsRef = useRef<Set<string> | null>(null)

  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const [hovered, setHovered] = useState<{ node: NodeData; index: number } | null>(null)
  const [focusNeighbors, setFocusNeighbors] = useState<Set<string> | null>(null)

  const effectiveFocusNeighbors = selectedNodeId ? focusNeighbors : null

  useEffect(() => {
    nodesRef.current = nodes
    onNodeClickRef.current = onNodeClick
  })

  useEffect(() => { typeCentroidsRef.current = typeCentroids ?? {} }, [typeCentroids])
  useEffect(() => { nodePatternsRef.current = nodePatterns ?? new Map() }, [nodePatterns])
  useEffect(() => { selectedNodeIdRef.current = selectedNodeId ?? null }, [selectedNodeId])
  useEffect(() => { hiddenRef.current = hiddenEntityTypes }, [hiddenEntityTypes])
  useEffect(() => { hiddenBehavioralRolesRef.current = hiddenBehavioralRoles ?? new Set() }, [hiddenBehavioralRoles])
  useEffect(() => { focusNeighborsRef.current = effectiveFocusNeighbors }, [effectiveFocusNeighbors])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect()
    setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }, [])

  // Init cosmos.gl
  useEffect(() => {
    if (!divRef.current) return
    graphRef.current = new Graph(divRef.current, {
      backgroundColor: '#0d1117',
      enableSimulation: true,
      fitViewOnInit: true,
      fitViewDelay: 200,
      renderHoveredPointRing: true,
      hoveredPointCursor: 'pointer',
      pointDefaultSize: 4,
      linkDefaultColor: [...COLOR_EDGE_DEFAULT] as [number, number, number, number],
      linkVisibilityDistanceRange: [20, 5000],
      linkVisibilityMinTransparency: 0.8,
      curvedLinks: false,
      spaceSize: SPACE_SIZE,

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

  // Overlay canvas RAF loop
  useEffect(() => {
    const canvas = overlayCanvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let rafId = 0

    const tick = () => {
      const g = graphRef.current
      const allNodes = nodesRef.current

      const parent = canvas.parentElement
      if (parent) {
        const w = parent.clientWidth
        const h = parent.clientHeight
        if (canvas.width !== w || canvas.height !== h) {
          canvas.width = w
          canvas.height = h
        }
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      if (g && allNodes.length > 0) {
        const tc = typeCentroidsRef.current
        const selId = selectedNodeIdRef.current
        const hidden = hiddenRef.current
        const hiddenRoles = hiddenBehavioralRolesRef.current

        if (Object.keys(tc).length > 0) {
          drawEntityHalos(ctx, tc, allNodes, hidden, g)
        }

        drawBehavioralBadges(ctx, allNodes, hiddenRoles, g)

        if (selId) {
          const nm = nodesMapRef.current
          const neighborEdges = validEdgesRef.current.filter(
            e => e.source === selId || e.target === selId
          )
          if (neighborEdges.length > 0) {
            drawFocusedArrows(ctx, selId, neighborEdges, nm, g)
            drawTransactionParticles(ctx, neighborEdges, nm, g)
          }
        }
      }

      rafId = requestAnimationFrame(tick)
    }

    rafId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafId)
  }, [])

  // Simulation config
  useEffect(() => {
    if (!graphRef.current || !simConfig) return
    graphRef.current.setConfig({
      simulationGravity: simConfig.gravity ?? 0.05,
      simulationRepulsion: simConfig.repulsion ?? 2.0,
      simulationLinkSpring: simConfig.linkSpring ?? 0.3,
      simulationCluster: simConfig.clusterStrength ?? 0.4
    })
    graphRef.current.start()
    setTimeout(() => graphRef.current?.pause(), 2000)
  }, [simConfig])

  // Data update — positions, colours, links
  useEffect(() => {
    const g = graphRef.current
    if (!g || !isReady || nodes.length === 0) return

    const idxMap = new Map<string, number>()
    nodes.forEach((n, i) => idxMap.set(n.id, i))
    idxMapRef.current = idxMap

    nodesMapRef.current = new Map(nodes.map(n => [n.id, n]))

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

    const hiddenRoles = hiddenBehavioralRoles ?? new Set<string>()

    g.setPointPositions(positions)
    g.setPointColors(
      buildColors(nodes, validEdges, hiddenEntityTypes, hiddenRoles, highlightedNodeIds, clusterMap, focusCluster)
    )
    g.setPointSizes(buildSizes(nodes, hiddenEntityTypes, hiddenRoles, sizeScale, scoring))
    g.setPointShapes(new Float32Array(nodes.length))
    g.setLinks(links)
    g.setLinkColors(buildLinkColors(validEdges, idxMap, nodes, highlightedNodeIds))
    g.setLinkWidths(buildLinkWidths(validEdges, idxMap, nodes, highlightedNodeIds))

    if (clustering?.cluster_centroids_2d && clusterMap) {
      const raw = clustering.cluster_centroids_2d
      const maxR = Math.max(...raw.map(([x, y]) => Math.sqrt(x * x + y * y)), 1)
      const scale = (SPACE_SIZE * 0.25) / maxR
      const clusterPos: number[] = new Array(2 * clustering.n_clusters)
      raw.forEach(([x, y], c) => {
        clusterPos[2 * c] = x * scale
        clusterPos[2 * c + 1] = y * scale
      })
      const pointClusters = Array.from(
        { length: nodes.length },
        (_, i) => clusterMap.get(nodes[i].id) ?? -1
      )
      g.setPointClusters(pointClusters)
      g.setClusterPositions(clusterPos)
    }

    g.setPointClusterStrength(buildClusterStrength(nodes.length, scoring))
    g.render(1)
    g.pause()
  }, [isReady, nodes, edges, rerunTrigger]) // eslint-disable-line react-hooks/exhaustive-deps

  // Appearance-only updates (no position change)
  useEffect(() => {
    const g = graphRef.current
    if (!g || nodes.length === 0) return
    const idxMap = idxMapRef.current
    const validEdges = validEdgesRef.current
    const effectiveHighlight = effectiveFocusNeighbors ?? highlightedNodeIds
    const hiddenRoles = hiddenBehavioralRoles ?? new Set<string>()

    g.setPointColors(
      buildColors(nodes, validEdges, hiddenEntityTypes, hiddenRoles, effectiveHighlight, clusterMap, focusCluster)
    )
    g.setPointSizes(buildSizes(nodes, hiddenEntityTypes, hiddenRoles, sizeScale, scoring))
    g.setLinkColors(buildLinkColors(validEdges, idxMap, nodes, effectiveHighlight))
    g.setLinkWidths(buildLinkWidths(validEdges, idxMap, nodes, effectiveHighlight))
    g.setPointClusterStrength(buildClusterStrength(nodes.length, scoring))
    g.render()
  }, [
    hiddenEntityTypes,
    hiddenBehavioralRoles,
    highlightedNodeIds,
    effectiveFocusNeighbors,
    sizeScale,
    nodes,
    clustering,
    scoring,
    focusCluster,
    clusterMap
  ])

  // Zoom to target
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
  const behavioralRole = hovered?.node.behavioral_role

  return (
    <div
      className="w-full h-full"
      style={{ position: 'relative', background: '#0d1117' }}
      onMouseMove={handleMouseMove}
    >
      <div ref={divRef} className="w-full h-full" />

      <canvas
        ref={overlayCanvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none'
        }}
      />

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
                <Badge
                  size="1"
                  style={{
                    background: (ENTITY_HEX[hovered.node.entity_type] ?? '#6b7280') + '33',
                    color: ENTITY_HEX[hovered.node.entity_type] ?? '#6b7280'
                  }}
                >
                  {ENTITY_LABELS[hovered.node.entity_type] ?? hovered.node.entity_type}
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
              {behavioralRole && behavioralRole !== 'regular' && (
                <Badge
                  size="1"
                  variant="soft"
                  style={{
                    background: (ROLE_ICONS[behavioralRole]?.color ?? '#6b7280') + '22',
                    color: ROLE_ICONS[behavioralRole]?.color ?? '#6b7280'
                  }}
                >
                  {ROLE_ICONS[behavioralRole]?.symbol} {ROLE_LABELS[behavioralRole] ?? behavioralRole}
                </Badge>
              )}
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
