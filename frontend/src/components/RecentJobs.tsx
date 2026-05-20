'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Badge, Box, Button, Flex, Spinner, Text } from '@radix-ui/themes'
import { ReloadIcon } from '@radix-ui/react-icons'
import { getLatestJobs } from '@/lib/api-client'
import type { JobInfo, JobStatus } from '@/types/api/jobs'

const STATUS_LABEL: Record<JobStatus, string> = {
  PENDING: 'В очереди',
  PROCESSING: 'Обработка',
  GRAPH_BUILDING: 'Построение графа',
  DETECTING: 'Детекция паттернов',
  SCORING: 'Скоринг',
  LAYOUT: 'Layout',
  CLUSTERING: 'Кластеризация',
  HIERARCHICAL_LAYOUT: 'Иерархический layout',
  SAVING: 'Сохранение',
  COMPLETED: 'Готово',
  FAILED: 'Ошибка'
}

const STATUS_COLOR: Record<JobStatus, 'green' | 'red' | 'blue' | 'gray'> = {
  PENDING: 'gray',
  PROCESSING: 'blue',
  GRAPH_BUILDING: 'blue',
  DETECTING: 'blue',
  SCORING: 'blue',
  LAYOUT: 'blue',
  CLUSTERING: 'blue',
  HIERARCHICAL_LAYOUT: 'blue',
  SAVING: 'blue',
  COMPLETED: 'green',
  FAILED: 'red'
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export default function RecentJobs() {
  const router = useRouter()
  const [jobs, setJobs] = useState<JobInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  function reload() {
    setLoading(true)
    setError(false)
    getLatestJobs(1, 5)
      .then(res => setJobs(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    getLatestJobs(1, 5)
      .then(res => setJobs(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <Flex align="center" justify="center" py="4">
        <Spinner size="2" />
      </Flex>
    )
  }

  if (error || jobs.length === 0) return null

  return (
    <Flex direction="column" gap="2" style={{ width: '100%' }}>
      <Flex align="center" justify="between">
        <Text size="2" weight="medium" color="gray">
          Последние задачи
        </Text>
        <Button variant="ghost" size="1" color="gray" onClick={reload}>
          <ReloadIcon />
        </Button>
      </Flex>

      <Flex direction="column" gap="1">
        {jobs.map(job => {
          const isDone = job.status === 'COMPLETED'
          const isFailed = job.status === 'FAILED'
          const isActive = !isDone && !isFailed

          return (
            <Box
              key={job.id}
              onClick={isDone ? () => router.push(`/graph/${job.id}`) : undefined}
              style={{
                borderRadius: 'var(--radius-2)',
                padding: '8px 10px',
                background: 'var(--gray-2)',
                cursor: isDone ? 'pointer' : 'default',
                transition: 'background 150ms'
              }}
              className={isDone ? 'hover:bg-[var(--gray-4)]' : undefined}
            >
              <Flex align="center" justify="between" gap="2">
                <Flex direction="column" gap="1" style={{ minWidth: 0 }}>
                  <Flex align="center" gap="2">
                    <Badge size="1" variant="soft" color="gray">
                      {job.format}
                    </Badge>
                    <Text
                      size="1"
                      style={{
                        fontFamily: 'var(--font-mono)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      {job.id.slice(0, 8)}…
                    </Text>
                  </Flex>
                  <Text size="1" color="gray">
                    {formatDate(job.created_at)}
                  </Text>
                  {isFailed && job.error_msg && (
                    <Text size="1" color="red" style={{ wordBreak: 'break-word' }}>
                      {job.error_msg.slice(0, 80)}
                    </Text>
                  )}
                </Flex>

                <Flex align="center" gap="2" style={{ flexShrink: 0 }}>
                  {isActive && <Spinner size="1" />}
                  <Badge size="1" color={STATUS_COLOR[job.status]} variant="soft">
                    {STATUS_LABEL[job.status]}
                  </Badge>
                  {isDone && (
                    <Button size="1" variant="soft" color="blue">
                      Открыть
                    </Button>
                  )}
                </Flex>
              </Flex>
            </Box>
          )
        })}
      </Flex>
    </Flex>
  )
}
