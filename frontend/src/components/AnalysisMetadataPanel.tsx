'use client'

import { useEffect, useState } from 'react'
import { Badge, Box, Flex, Separator, Text } from '@radix-ui/themes'
import { ChevronDownIcon, ChevronUpIcon } from '@radix-ui/react-icons'
import type { AlgorithmDescription, AnalysisMetadata, StepTiming } from '@/types/graph/analysis'
import { fetchAlgorithms } from '@/lib/api-client'

const STEP_LABELS: Record<string, string> = {
  build_graph: 'Построение графа',
  select_strategy: 'Выбор стратегии',
  detect_patterns: 'Детекция паттернов',
  score: 'Риск-скоринг',
  layout: 'Базовый layout',
  cluster_graph: 'Кластеризация',
  hierarchical_layout: 'Иерархический layout',
  save: 'Сохранение'
}

const METHOD_IDS: Record<string, string[]> = {
  agc: ['agc', 'risk_scoring', 'hierarchical_layout'],
  louvain: ['louvain', 'risk_scoring', 'hierarchical_layout']
}

interface AlgorithmCardProps {
  algo: AlgorithmDescription
  reason?: string
}

function AlgorithmCard({ algo, reason }: AlgorithmCardProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <Box
      style={{
        border: '1px solid var(--gray-4)',
        borderRadius: 'var(--radius-2)',
        overflow: 'hidden'
      }}
    >
      <Flex
        direction="column"
        gap="1"
        p="3"
        style={{ cursor: 'pointer' }}
        onClick={() => setExpanded(v => !v)}
      >
        <Flex align="center" justify="between" gap="2">
          <Text size="2" weight="medium">
            {algo.name}
          </Text>
          {expanded ? (
            <ChevronUpIcon style={{ flexShrink: 0, color: 'var(--gray-9)' }} />
          ) : (
            <ChevronDownIcon style={{ flexShrink: 0, color: 'var(--gray-9)' }} />
          )}
        </Flex>
        <Text size="1" color="gray">
          {algo.short_description}
        </Text>
        {reason && (
          <Box
            style={{
              background: 'var(--accent-2)',
              borderRadius: 'var(--radius-1)',
              padding: '4px 8px',
              marginTop: 2
            }}
          >
            <Text size="1" color="blue">
              {reason}
            </Text>
          </Box>
        )}
      </Flex>

      {expanded && (
        <Box
          style={{
            borderTop: '1px solid var(--gray-4)',
            background: 'var(--gray-1)',
            padding: '10px 12px'
          }}
        >
          <Flex direction="column" gap="2">
            <Text size="1" style={{ lineHeight: 1.6 }}>
              {algo.detailed_description}
            </Text>
            {algo.complexity && (
              <Flex align="center" gap="2">
                <Text size="1" color="gray" weight="medium">
                  Сложность:
                </Text>
                <Badge
                  size="1"
                  variant="soft"
                  color="gray"
                  style={{ fontFamily: 'var(--font-mono)' }}
                >
                  {algo.complexity}
                </Badge>
              </Flex>
            )}
            {algo.reference && (
              <Text size="1" color="gray" style={{ fontStyle: 'italic' }}>
                {algo.reference}
              </Text>
            )}
            <Text size="1" color="gray">
              <Text size="1" weight="medium">
                Применение:{' '}
              </Text>
              {algo.use_case}
            </Text>
          </Flex>
        </Box>
      )}
    </Box>
  )
}

function StepBar({ timing, totalMs }: { timing: StepTiming; totalMs: number }) {
  const pct = totalMs > 0 ? (timing.duration_ms / totalMs) * 100 : 0
  const label = STEP_LABELS[timing.step] ?? timing.step

  return (
    <Flex direction="column" gap="1">
      <Flex align="center" justify="between">
        <Text size="1">{label}</Text>
        <Text size="1" color="gray" style={{ fontFamily: 'var(--font-mono)' }}>
          {timing.duration_ms} мс
        </Text>
      </Flex>
      <Box
        style={{
          height: 6,
          borderRadius: 3,
          background: 'var(--gray-4)',
          overflow: 'hidden'
        }}
      >
        <Box
          style={{
            height: '100%',
            width: `${Math.max(pct, 1)}%`,
            background: 'var(--accent-9)',
            borderRadius: 3
          }}
        />
      </Box>
    </Flex>
  )
}

interface Props {
  metadata: AnalysisMetadata | null
}

export default function AnalysisMetadataPanel({ metadata }: Props) {
  const [algorithms, setAlgorithms] = useState<AlgorithmDescription[]>([])

  useEffect(() => {
    fetchAlgorithms()
      .then(setAlgorithms)
      .catch(() => {})
  }, [])

  if (!metadata) {
    return (
      <Flex align="center" justify="center" p="4">
        <Text size="2" color="gray" style={{ fontStyle: 'italic' }}>
          Метаданные появятся после завершения анализа
        </Text>
      </Flex>
    )
  }

  const algoMap = Object.fromEntries(algorithms.map(a => [a.id, a]))
  const clusteringAlgoId = metadata.clustering_method
  const relevantAlgoIds = METHOD_IDS[clusteringAlgoId] ?? [clusteringAlgoId]

  const totalMs =
    metadata.total_duration_ms || metadata.step_timings.reduce((s, t) => s + t.duration_ms, 0)

  return (
    <Flex direction="column" gap="3" p="3">
      {/* Секция 1: Сводка */}
      <Flex direction="column" gap="1">
        <Text
          size="1"
          weight="medium"
          color="gray"
          style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
        >
          Сводка
        </Text>
        <Flex direction="column" gap="1" style={{ paddingLeft: 2 }}>
          <Flex justify="between">
            <Text size="2" color="gray">
              Узлов
            </Text>
            <Text size="2" weight="medium">
              {metadata.n_nodes.toLocaleString('ru-RU')}
            </Text>
          </Flex>
          <Flex justify="between">
            <Text size="2" color="gray">
              Рёбер
            </Text>
            <Text size="2" weight="medium">
              {metadata.n_edges.toLocaleString('ru-RU')}
            </Text>
          </Flex>
          <Flex justify="between">
            <Text size="2" color="gray">
              Плотность
            </Text>
            <Text size="2" weight="medium">
              {metadata.density.toFixed(4)}
            </Text>
          </Flex>
          <Flex justify="between">
            <Text size="2" color="gray">
              Общее время
            </Text>
            <Text size="2" weight="medium">
              {(totalMs / 1000).toFixed(2)} с
            </Text>
          </Flex>
        </Flex>
      </Flex>

      <Separator size="4" />

      {/* Секция 2: Алгоритмы */}
      <Flex direction="column" gap="2">
        <Text
          size="1"
          weight="medium"
          color="gray"
          style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
        >
          Применённые алгоритмы
        </Text>
        {relevantAlgoIds.map(id => {
          const algo = algoMap[id]
          if (!algo) return null
          const reason =
            id === clusteringAlgoId
              ? metadata.clustering_reason
              : id === 'risk_scoring'
                ? metadata.scoring_reason
                : undefined
          return <AlgorithmCard key={id} algo={algo} reason={reason} />
        })}
      </Flex>

      {metadata.step_timings.length > 0 && (
        <>
          <Separator size="4" />

          {/* Секция 3: Тайминги */}
          <Flex direction="column" gap="2">
            <Text
              size="1"
              weight="medium"
              color="gray"
              style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
            >
              Время выполнения шагов
            </Text>
            <Flex direction="column" gap="2">
              {metadata.step_timings.map((t, i) => (
                <StepBar key={i} timing={t} totalMs={totalMs} />
              ))}
            </Flex>
          </Flex>
        </>
      )}

      <Separator size="4" />

      {/* Секция 4: Технические детали */}
      <Flex direction="column" gap="2">
        <Text
          size="1"
          weight="medium"
          color="gray"
          style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
        >
          Технические параметры
        </Text>

        {Object.keys(metadata.scoring_weights).length > 0 && (
          <Flex direction="column" gap="1">
            <Text size="1" color="gray" weight="medium">
              Веса скоринга
            </Text>
            {Object.entries(metadata.scoring_weights).map(([k, v]) => (
              <Flex key={k} justify="between" style={{ paddingLeft: 8 }}>
                <Text size="1" color="gray" style={{ fontFamily: 'var(--font-mono)' }}>
                  {k}
                </Text>
                <Text size="1" style={{ fontFamily: 'var(--font-mono)' }}>
                  {(v as number).toFixed(2)}
                </Text>
              </Flex>
            ))}
          </Flex>
        )}

        <Flex direction="column" gap="1">
          <Text size="1" color="gray" weight="medium">
            Betweenness
          </Text>
          <Flex align="center" gap="2" style={{ paddingLeft: 8 }}>
            <Badge size="1" variant="soft" color={metadata.betweenness_exact ? 'green' : 'amber'}>
              {metadata.betweenness_exact ? 'Точный' : `Sampling k=${metadata.betweenness_k}`}
            </Badge>
          </Flex>
        </Flex>

        {Object.keys(metadata.algorithm_versions).length > 0 && (
          <Flex direction="column" gap="1">
            <Text size="1" color="gray" weight="medium">
              Версии алгоритмов
            </Text>
            {Object.entries(metadata.algorithm_versions).map(([algo, ref]) => (
              <Flex key={algo} direction="column" style={{ paddingLeft: 8 }}>
                <Text size="1" weight="medium" style={{ fontFamily: 'var(--font-mono)' }}>
                  {algo}
                </Text>
                <Text
                  size="1"
                  color="gray"
                  style={{ fontStyle: 'italic', wordBreak: 'break-word' }}
                >
                  {ref}
                </Text>
              </Flex>
            ))}
          </Flex>
        )}
      </Flex>
    </Flex>
  )
}
