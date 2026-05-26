'use client'

import { Flex, Progress, Spinner, Text } from '@radix-ui/themes'
import type { StreamStage } from '@/types/graph/stream'

interface StreamProgressProps {
  stage: StreamStage
  jobStatus?: string
  nodeCount?: number
  edgeCount?: number
  receivedNodes?: number
}

export const JOB_STATUS_LABEL: Record<string, string> = {
  PENDING: 'Ожидание в очереди...',
  PROCESSING: 'Обработка файла...',
  GRAPH_BUILDING: 'Построение графа...',
  DETECTING: 'Выявление паттернов...',
  SCORING: 'Оценка рисков...',
  LAYOUT: 'Вычисление расположения...',
  CLUSTERING: 'Кластеризация узлов...',
  HIERARCHICAL_LAYOUT: 'Иерархическое расположение...',
  SAVING: 'Сохранение результатов...'
}

const STAGE_LABEL: Record<string, string> = {
  connecting: 'Подключение к серверу...',
  streaming: 'Загрузка данных графа',
  detectors: 'Анализ паттернов...'
}

export default function StreamProgress({
  stage,
  jobStatus,
  nodeCount,
  edgeCount,
  receivedNodes
}: StreamProgressProps) {
  if (stage === 'idle' || stage === 'done' || stage === 'error') return null

  const total = nodeCount ?? 0
  const pct =
    stage === 'streaming' && total > 0 && receivedNodes !== undefined
      ? Math.min(100, Math.round((receivedNodes / total) * 100))
      : null

  const label =
    stage === 'connecting' && jobStatus
      ? (JOB_STATUS_LABEL[jobStatus] ?? 'Обработка задачи...')
      : (STAGE_LABEL[stage] ?? '')

  return (
    <Flex
      align="center"
      gap="3"
      px="4"
      py="2"
      style={{
        position: 'fixed',
        top: 'var(--space-4)',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 50,
        background: 'var(--color-panel-solid)',
        border: '1px solid var(--gray-5)',
        borderRadius: 'var(--radius-5)',
        boxShadow: 'var(--shadow-4)',
        backdropFilter: 'blur(8px)',
        minWidth: 300
      }}
    >
      <Spinner size="1" style={{ flexShrink: 0 }} />
      <Flex direction="column" gap="1" style={{ flex: 1, minWidth: 0 }}>
        <Flex align="center" justify="between" gap="2">
          <Text size="2" weight={pct !== null ? 'medium' : 'regular'}>
            {label}
          </Text>
          {pct !== null && (
            <Text size="2" color="gray" style={{ flexShrink: 0 }}>
              {pct}%
            </Text>
          )}
        </Flex>

        {pct !== null && (
          <>
            <Progress value={pct} size="1" color="blue" style={{ width: '100%' }} />
            <Text size="1" color="gray">
              {receivedNodes?.toLocaleString('ru-RU')} / {nodeCount?.toLocaleString('ru-RU')} узлов
              {edgeCount !== undefined && ` · ${edgeCount.toLocaleString('ru-RU')} рёбер`}
            </Text>
          </>
        )}
      </Flex>
    </Flex>
  )
}
