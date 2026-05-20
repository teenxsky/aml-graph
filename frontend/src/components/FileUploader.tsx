'use client'

import { useCallback, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Box, Button, Callout, Flex, Text } from '@radix-ui/themes'
import { ExclamationTriangleIcon, UploadIcon } from '@radix-ui/react-icons'
import ColumnMapper from './ColumnMapper'
import type { ColumnMapping } from '@/types/api/column-mapping'
import type { UploadFormat } from '@/types/api/jobs'
import { uploadCsv, uploadIbm } from '@/lib/api-client'

interface ParsedCSV {
  columns: string[]
  preview: string[][]
  file: File
}

function parseCSVPreview(text: string): { columns: string[]; preview: string[][] } {
  const lines = text.split('\n').filter(l => l.trim())
  if (lines.length === 0) return { columns: [], preview: [] }
  const columns = lines[0].split(',').map(c => c.trim().replace(/^"|"$/g, ''))
  const preview = lines.slice(1, 4).map(l => l.split(',').map(c => c.trim().replace(/^"|"$/g, '')))
  return { columns, preview }
}

export default function FileUploader() {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const [format, setFormat] = useState<UploadFormat>('IBM')
  const [isDragging, setIsDragging] = useState(false)
  const [ibmFile, setIbmFile] = useState<File | null>(null)
  const [parsed, setParsed] = useState<ParsedCSV | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function switchFormat(next: UploadFormat) {
    setFormat(next)
    setIbmFile(null)
    setParsed(null)
    setError(null)
  }

  const readFile = useCallback(
    (file: File) => {
      if (!file.name.endsWith('.csv')) {
        setError('Пожалуйста, загрузите CSV-файл.')
        return
      }
      setError(null)
      if (format === 'IBM') {
        setIbmFile(file)
        return
      }
      const reader = new FileReader()
      reader.onload = e => {
        const text = e.target?.result as string
        const { columns, preview } = parseCSVPreview(text)
        if (columns.length < 2) {
          setError('Не удалось прочитать заголовки CSV.')
          return
        }
        setParsed({ columns, preview, file })
      }
      reader.readAsText(file)
    },
    [format]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) readFile(file)
    },
    [readFile]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => setIsDragging(false), [])

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) readFile(file)
    e.target.value = ''
  }

  async function handleIbmSubmit() {
    if (!ibmFile) return
    setIsLoading(true)
    setError(null)
    try {
      const res = await uploadIbm(ibmFile)
      router.push(`/graph/${res.data.job_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки')
      setIsLoading(false)
    }
  }

  async function handleCustomSubmit(mapping: ColumnMapping) {
    if (!parsed) return
    setIsLoading(true)
    setError(null)
    try {
      const res = await uploadCsv(parsed.file, mapping)
      router.push(`/graph/${res.data.job_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки')
      setIsLoading(false)
    }
  }

  const formatToggle = (
    <Flex gap="1">
      {(['IBM', 'CUSTOM'] as UploadFormat[]).map(f => (
        <Button
          key={f}
          size="1"
          variant={format === f ? 'solid' : 'soft'}
          color={format === f ? 'blue' : 'gray'}
          onClick={() => switchFormat(f)}
        >
          {f === 'IBM' ? 'IBM AML' : 'Custom CSV'}
        </Button>
      ))}
    </Flex>
  )

  const dropZone = (
    <Box
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => inputRef.current?.click()}
      style={{
        width: '100%',
        borderRadius: 'var(--radius-3)',
        border: `2px dashed ${isDragging ? 'var(--accent-8)' : 'var(--gray-6)'}`,
        background: isDragging ? 'var(--accent-2)' : 'var(--gray-2)',
        cursor: 'pointer',
        transition: 'border-color 150ms, background 150ms'
      }}
      p="8"
    >
      <Flex direction="column" align="center" gap="3">
        <Box style={{ color: isDragging ? 'var(--accent-9)' : 'var(--gray-8)' }}>
          <UploadIcon width={32} height={32} />
        </Box>
        <Flex direction="column" align="center" gap="1">
          <Text weight="medium">Перетащите CSV-файл сюда</Text>
          <Text size="2" color="gray">
            или нажмите для выбора файла
          </Text>
        </Flex>
        {format === 'IBM' ? (
          <Text size="1" color="gray">
            Стандартный формат IBM AML — маппинг колонок не требуется
          </Text>
        ) : (
          <Text size="1" color="gray">
            Ожидаемые столбцы: отправитель, получатель, сумма, дата
          </Text>
        )}
      </Flex>
    </Box>
  )

  if (format === 'IBM' && ibmFile) {
    return (
      <Flex direction="column" gap="3" align="start" style={{ width: '100%' }}>
        {formatToggle}
        <Flex align="center" gap="2">
          <Text size="2" color="gray">
            Файл: <Text size="2">{ibmFile.name}</Text>
          </Text>
          <Button
            variant="ghost"
            size="1"
            color="gray"
            onClick={() => {
              setIbmFile(null)
              setError(null)
            }}
          >
            Изменить
          </Button>
        </Flex>

        {error && (
          <Callout.Root color="red" size="1" style={{ width: '100%' }}>
            <Callout.Icon>
              <ExclamationTriangleIcon />
            </Callout.Icon>
            <Callout.Text>{error}</Callout.Text>
          </Callout.Root>
        )}

        <Button size="3" loading={isLoading} disabled={isLoading} onClick={handleIbmSubmit}>
          Анализировать граф
        </Button>
      </Flex>
    )
  }

  if (format === 'CUSTOM' && parsed) {
    return (
      <Flex direction="column" gap="3" align="start" style={{ width: '100%' }}>
        {formatToggle}
        <Flex align="center" gap="2">
          <Text size="2" color="gray">
            Файл: <Text size="2">{parsed.file.name}</Text>
          </Text>
          <Button
            variant="ghost"
            size="1"
            color="gray"
            onClick={() => {
              setParsed(null)
              setError(null)
            }}
          >
            Изменить
          </Button>
        </Flex>

        {error && (
          <Callout.Root color="red" size="1" style={{ width: '100%' }}>
            <Callout.Icon>
              <ExclamationTriangleIcon />
            </Callout.Icon>
            <Callout.Text>{error}</Callout.Text>
          </Callout.Root>
        )}

        <ColumnMapper
          columns={parsed.columns}
          preview={parsed.preview}
          onSubmit={handleCustomSubmit}
          isLoading={isLoading}
        />
      </Flex>
    )
  }

  return (
    <Flex direction="column" gap="3" align="center" style={{ width: '100%' }}>
      {formatToggle}
      {dropZone}
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFileInput}
      />
      {error && (
        <Callout.Root color="red" size="1" style={{ width: '100%' }}>
          <Callout.Icon>
            <ExclamationTriangleIcon />
          </Callout.Icon>
          <Callout.Text>{error}</Callout.Text>
        </Callout.Root>
      )}
    </Flex>
  )
}
