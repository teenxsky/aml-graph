'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import { Badge, Box, Button, Flex, ScrollArea, Separator, Spinner, Text } from '@radix-ui/themes'
import { ChevronLeftIcon, ExclamationTriangleIcon } from '@radix-ui/react-icons'
import { createSSEClient } from '@/lib/sse-client'
import type { NodeData } from '@/types/graph/node'
import type { EdgeData } from '@/types/graph/edge'
import type { GraphMeta } from '@/types/graph/meta'
import type { DetectorResult } from '@/types/graph/detector'
import type { StreamStage } from '@/types/graph/stream'
import type { AnalysisResult, ClusteringResult, NodeScoringResult } from '@/types/graph/analysis'
import StreamProgress, { JOB_STATUS_LABEL } from '@/components/StreamProgress'
import Sidebar from '@/components/Sidebar'
import DetailPanel from '@/components/DetailPanel'
import AnalysisMetadataPanel from '@/components/AnalysisMetadataPanel'

const GraphCanvas = dynamic(() => import('@/components/GraphCanvas'), { ssr: false })

function extractPatternNodeIds(result: {
  pattern_type: string
  items: {
    node_ids?: string[]
    nodes?: string[]
    node_id?: string
    source_node?: string
    receivers?: string[]
  }[]
}): string[] {
  const ids: string[] = []
  for (const item of result.items) {
    if (Array.isArray(item.node_ids)) item.node_ids.forEach(id => ids.push(String(id)))
    if (Array.isArray(item.nodes)) item.nodes.forEach(id => ids.push(String(id)))
    if (typeof item.node_id === 'string') ids.push(item.node_id)
    if (typeof item.source_node === 'string') ids.push(item.source_node)
    if (Array.isArray(item.receivers)) item.receivers.forEach(id => ids.push(String(id)))
  }
  return ids
}

const CLUSTER_PALETTE: [number, number, number][] = [
  [100, 149, 237],
  [50, 205, 50],
  [255, 165, 0],
  [220, 20, 60],
  [64, 224, 208],
  [218, 112, 214],
  [255, 215, 0],
  [127, 255, 0],
  [0, 191, 255],
  [255, 105, 180],
  [152, 251, 152],
  [255, 140, 0],
  [135, 206, 250],
  [144, 238, 144],
  [255, 182, 193],
  [176, 196, 222]
]

function paletteHex(id: number): string {
  const [r, g, b] = CLUSTER_PALETTE[id % CLUSTER_PALETTE.length]
  return `rgb(${r},${g},${b})`
}

interface ClusterLegendRow {
  id: number
  count: number
  meanRisk: number
}

function buildLegend(
  nodes: NodeData[],
  clustering: ClusteringResult | null,
  scoring: NodeScoringResult | null
): ClusterLegendRow[] {
  if (!clustering) return []
  const rows: Map<number, { count: number; riskSum: number }> = new Map()

  for (let i = 0; i < nodes.length; i++) {
    const c = clustering.labels[i]
    const risk = scoring ? scoring.scores[i] : (nodes[i].risk_score ?? 0)
    if (!rows.has(c)) rows.set(c, { count: 0, riskSum: 0 })
    const row = rows.get(c)!
    row.count++
    row.riskSum += risk
  }

  return Array.from(rows.entries())
    .map(([id, { count, riskSum }]) => ({
      id,
      count,
      meanRisk: riskSum / count
    }))
    .sort((a, b) => b.meanRisk - a.meanRisk)
}

function GraphPageContent({ sessionId }: { sessionId: string }) {
  const router = useRouter()

  const pendingNodesRef = useRef<NodeData[]>([])
  const pendingEdgesRef = useRef<EdgeData[]>([])

  const [stage, setStage] = useState<StreamStage>('connecting')
  const [jobStatus, setJobStatus] = useState<string>('')
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [graphMeta, setGraphMeta] = useState<GraphMeta | null>(null)
  const [nodes, setNodes] = useState<NodeData[]>([])
  const [edges, setEdges] = useState<EdgeData[]>([])
  const [detectorResults, setDetectorResults] = useState<DetectorResult[]>([])
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [clusterMap, setClusterMap] = useState<Map<string, number> | null>(null)
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null)
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<Set<string> | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sizeScale, setSizeScale] = useState(1.0)
  const [zoomTarget, setZoomTarget] = useState<{ id: string; ts: number } | null>(null)
  const [focusCluster, setFocusCluster] = useState<number | null>(null)
  const [receivedNodeCount, setReceivedNodeCount] = useState(0)

  const [hiddenEntityTypes, setHiddenEntityTypes] = useState<Set<string>>(new Set())
  const [hiddenBehavioralRoles, setHiddenBehavioralRoles] = useState<Set<string>>(new Set())
  const [rightTab, setRightTab] = useState<'clusters' | 'metadata'>('clusters')

  useEffect(() => {
    if (!sessionId) return

    const client = createSSEClient(sessionId, {
      onGraphMeta: meta => {
        pendingNodesRef.current = []
        pendingEdgesRef.current = []
        setGraphMeta(meta)
        setStage('streaming')
      },
      onNodesChunk: newNodes => {
        pendingNodesRef.current.push(...newNodes)
        setReceivedNodeCount(prev => prev + newNodes.length)
      },
      onEdgesChunk: newEdges => {
        pendingEdgesRef.current.push(...newEdges)
      },
      onAnalysisResult: result => {
        setAnalysisResult(result)
        if (result.clustering) {
          const map = new Map<string, number>()
          result.clustering.node_ids.forEach((id, i) => {
            map.set(id, result.clustering!.labels[i])
          })
          setClusterMap(map)
        }
      },
      onCompleted: () => {
        setNodes([...pendingNodesRef.current])
        setEdges([...pendingEdgesRef.current])
        setStage('done')
      },
      onStatus: data => {
        setJobStatus(data.status)
      },
      onServerError: data => {
        setErrorMessage(data.message)
        setStage('error')
      },
      onDetectorResult: result => {
        setDetectorResults(prev => [...prev, result])
        setStage(s => (s !== 'done' ? 'detectors' : s))
      },
      onStreamDone: () => {
        setNodes(prev => (prev.length > 0 ? prev : [...pendingNodesRef.current]))
        setEdges(prev => (prev.length > 0 ? prev : [...pendingEdgesRef.current]))
        setStage('done')
      },
      onError: () => {
        setStage(prev => {
          if (prev === 'done') return 'done'
          setErrorMessage('Соединение с сервером прервано')
          return 'error'
        })
      }
    })
    return () => client.close()
  }, [sessionId])

  const launderingNodes = useMemo(() => nodes.filter(n => n.is_laundering_node), [nodes])

  const entityGroups = useMemo(() => {
    const counts = new Map<string, number>()
    for (const n of nodes) counts.set(n.entity_type, (counts.get(n.entity_type) ?? 0) + 1)
    return [...counts.entries()].map(([type, count]) => ({ type, count }))
  }, [nodes])

  const behavioralRoleGroups = useMemo(() => {
    const counts = new Map<string, number>()
    for (const n of nodes) counts.set(n.behavioral_role, (counts.get(n.behavioral_role) ?? 0) + 1)
    return [...counts.entries()].map(([role, count]) => ({ role, count }))
  }, [nodes])

  const nodePatterns = useMemo(() => {
    const map = new Map<string, string[]>()
    for (const result of detectorResults) {
      for (const id of extractPatternNodeIds(result)) {
        const existing = map.get(id) ?? []
        existing.push(result.pattern_type)
        map.set(id, existing)
      }
    }
    return map
  }, [detectorResults])

  const clusteringResult: ClusteringResult | null = analysisResult?.clustering ?? null
  const scoringResult: NodeScoringResult | null = analysisResult?.node_scoring ?? null

  const typeCentroids = clusteringResult?.type_centroids ?? {}

  const legend = useMemo(
    () => buildLegend(nodes, clusteringResult, scoringResult),
    [nodes, clusteringResult, scoringResult]
  )

  const isGraphReady = nodes.length > 0

  return (
    <Flex direction="column" style={{ height: '100vh', background: '#0d1117', overflow: 'hidden' }}>
      {/* Header */}
      <Flex
        align="center"
        justify="between"
        px="3"
        py="2"
        style={{
          flexShrink: 0,
          borderBottom: '1px solid var(--gray-4)',
          background: 'var(--color-panel-solid)',
          zIndex: 10
        }}
      >
        <Flex align="center" gap="3">
          <Button variant="ghost" color="gray" size="1" onClick={() => router.push('/')}>
            <ChevronLeftIcon />
            Назад
          </Button>
          <Separator orientation="vertical" />
          <Text size="2" weight="medium">
            AML Graph Visualizer
          </Text>
          {graphMeta && (
            <Text size="2" color="gray">
              {graphMeta.node_count.toLocaleString('ru-RU')} узлов ·{' '}
              {graphMeta.edge_count.toLocaleString('ru-RU')} рёбер
            </Text>
          )}
        </Flex>
        <Badge variant="soft" color="gray" size="1" style={{ fontFamily: 'var(--font-mono)' }}>
          {sessionId}
        </Badge>
      </Flex>

      <StreamProgress
        stage={stage}
        jobStatus={jobStatus}
        nodeCount={graphMeta?.node_count}
        edgeCount={graphMeta?.edge_count}
        receivedNodes={receivedNodeCount}
      />

      <Flex style={{ flex: 1, overflow: 'hidden' }}>
        <Sidebar
          detectorResults={detectorResults}
          onHighlightPattern={setHighlightedNodeIds}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(v => !v)}
          launderingNodes={launderingNodes}
          onSelectLaunderingNode={node => {
            setSelectedNode(node)
            setZoomTarget({ id: node.id, ts: Date.now() })
          }}
          sizeScale={sizeScale}
          onSizeScaleChange={setSizeScale}
          entityGroups={entityGroups}
          hiddenEntityTypes={hiddenEntityTypes}
          onToggleEntityType={type =>
            setHiddenEntityTypes(prev => {
              const next = new Set(prev)
              if (next.has(type)) next.delete(type)
              else next.add(type)
              return next
            })
          }
          behavioralRoleGroups={behavioralRoleGroups}
          hiddenBehavioralRoles={hiddenBehavioralRoles}
          onToggleBehavioralRole={role =>
            setHiddenBehavioralRoles(prev => {
              const next = new Set(prev)
              if (next.has(role)) next.delete(role)
              else next.add(role)
              return next
            })
          }
        />

        <Box style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          {!isGraphReady && stage !== 'error' && (
            <Flex
              direction="column"
              align="center"
              justify="center"
              gap="3"
              style={{ position: 'absolute', inset: 0, zIndex: 10 }}
            >
              <Spinner size="3" />
              <Text size="2" color="gray">
                {stage === 'connecting'
                  ? jobStatus
                    ? (JOB_STATUS_LABEL[jobStatus] ?? 'Обработка задачи...')
                    : 'Подключение...'
                  : 'Загрузка данных графа...'}
              </Text>
            </Flex>
          )}
          {stage === 'error' && (
            <Flex
              direction="column"
              align="center"
              justify="center"
              gap="4"
              style={{
                position: 'absolute',
                inset: 0,
                zIndex: 10,
                background: 'rgba(13, 17, 23, 0.92)'
              }}
            >
              <ExclamationTriangleIcon width="36" height="36" color="var(--red-9)" />
              <Flex direction="column" align="center" gap="2">
                <Text size="4" weight="medium" color="red">
                  Ошибка обработки
                </Text>
                <Text size="2" color="gray" style={{ maxWidth: 400, textAlign: 'center' }}>
                  {errorMessage || 'Произошла неизвестная ошибка'}
                </Text>
              </Flex>
              <Button onClick={() => router.push('/')} color="gray" variant="soft" size="2">
                На главную
              </Button>
            </Flex>
          )}
          <GraphCanvas
            nodes={nodes}
            edges={edges}
            isReady={isGraphReady}
            hiddenEntityTypes={hiddenEntityTypes}
            hiddenBehavioralRoles={hiddenBehavioralRoles}
            highlightedNodeIds={highlightedNodeIds}
            onNodeClick={setSelectedNode}
            sizeScale={sizeScale}
            zoomTarget={zoomTarget}
            clustering={clusteringResult}
            clusterMap={clusterMap}
            scoring={scoringResult}
            focusCluster={focusCluster}
            selectedNodeId={selectedNode?.id ?? null}
            typeCentroids={typeCentroids}
            nodePatterns={nodePatterns}
          />
        </Box>

        <Flex
          direction="column"
          style={{
            width: 240,
            flexShrink: 0,
            borderLeft: '1px solid var(--gray-4)',
            background: 'var(--color-panel-solid)',
            overflow: 'hidden'
          }}
        >
          <Flex style={{ borderBottom: '1px solid var(--gray-4)', flexShrink: 0 }}>
            {(['clusters', 'metadata'] as const).map(tab => (
              <Box
                key={tab}
                onClick={() => setRightTab(tab)}
                style={{
                  flex: 1,
                  padding: '6px 4px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  borderBottom:
                    rightTab === tab ? '2px solid var(--accent-9)' : '2px solid transparent',
                  background: rightTab === tab ? 'var(--accent-2)' : undefined,
                  transition: 'background 150ms'
                }}
              >
                <Text
                  size="1"
                  weight={rightTab === tab ? 'medium' : 'regular'}
                  color={rightTab === tab ? 'blue' : 'gray'}
                >
                  {tab === 'clusters' ? 'Кластеры' : 'Метаданные'}
                </Text>
              </Box>
            ))}
          </Flex>

          {rightTab === 'clusters' ? (
            <ScrollArea scrollbars="vertical" style={{ flex: 1 }}>
              <Flex direction="column" gap="2" p="3" style={{ minWidth: 0 }}>
                {legend.length > 0 ? (
                  <>
                    <Flex align="center" justify="between">
                      <Text
                        size="1"
                        weight="medium"
                        color="gray"
                        style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
                      >
                        Кластеры
                      </Text>
                      <Badge size="1" color="blue" variant="soft">
                        {legend.length}
                      </Badge>
                    </Flex>

                    {focusCluster !== null && (
                      <Text
                        size="1"
                        color="blue"
                        style={{ cursor: 'pointer', textDecoration: 'underline' }}
                        onClick={() => setFocusCluster(null)}
                      >
                        Показать все кластеры
                      </Text>
                    )}

                    <Flex direction="column" gap="1">
                      {legend.map(row => (
                        <Box
                          key={row.id}
                          onClick={() => setFocusCluster(focusCluster === row.id ? null : row.id)}
                          style={{
                            cursor: 'pointer',
                            borderRadius: 'var(--radius-2)',
                            padding: '5px 8px',
                            background: focusCluster === row.id ? 'var(--accent-3)' : undefined,
                            transition: 'background 150ms',
                            opacity: focusCluster !== null && focusCluster !== row.id ? 0.5 : 1
                          }}
                          className={
                            focusCluster === row.id ? undefined : 'hover:bg-[var(--gray-3)]'
                          }
                        >
                          <Flex align="center" gap="2">
                            <div
                              style={{
                                width: 10,
                                height: 10,
                                borderRadius: '50%',
                                background: paletteHex(row.id),
                                flexShrink: 0
                              }}
                            />
                            <Flex direction="column" style={{ minWidth: 0, flex: 1 }}>
                              <Flex align="center" justify="between">
                                <Text size="1" weight="medium">
                                  Кластер {row.id}
                                </Text>
                                <Text size="1" color="gray">
                                  {row.count}
                                </Text>
                              </Flex>
                              <Badge
                                size="1"
                                color={
                                  row.meanRisk > 0.7
                                    ? 'red'
                                    : row.meanRisk > 0.4
                                      ? 'amber'
                                      : 'green'
                                }
                                variant="soft"
                              >
                                {Math.round(row.meanRisk * 100)}% риск
                              </Badge>
                            </Flex>
                          </Flex>
                        </Box>
                      ))}
                    </Flex>
                  </>
                ) : (
                  <Text size="2" color="gray" style={{ fontStyle: 'italic' }}>
                    Кластеры появятся после завершения анализа
                  </Text>
                )}
              </Flex>
            </ScrollArea>
          ) : (
            <ScrollArea scrollbars="vertical" style={{ flex: 1 }}>
              <AnalysisMetadataPanel metadata={analysisResult?.clustering?.metadata ?? null} />
            </ScrollArea>
          )}
        </Flex>

        {selectedNode && (
          <DetailPanel
            node={selectedNode}
            allNodes={nodes}
            edges={edges}
            detectorResults={detectorResults}
            onClose={() => setSelectedNode(null)}
            onSelectNode={setSelectedNode}
          />
        )}
      </Flex>
    </Flex>
  )
}

export default function GraphPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  if (!sessionId) return null
  return <GraphPageContent key={sessionId} sessionId={sessionId} />
}
