'use client'

import { useEffect, useState } from 'react'
import { Box, Button, Flex, Heading, Select, Table, Text } from '@radix-ui/themes'
import type { ColumnMapping } from '@/types/api/column-mapping'

interface EntityTypeHint {
  code: string
  label_ru: string
  short_description: string
}

interface ColumnMapperProps {
  columns: string[]
  preview: string[][]
  onSubmit: (mapping: ColumnMapping) => void
  isLoading: boolean
}

const REQUIRED_FIELDS: { key: keyof ColumnMapping; label: string }[] = [
  { key: 'sender_id', label: 'ID отправителя' },
  { key: 'receiver_id', label: 'ID получателя' },
  { key: 'amount_paid', label: 'Amount Paid' },
  { key: 'timestamp', label: 'Дата / время' }
]

const ENTITY_TYPE_FIELDS: { key: keyof ColumnMapping; label: string; hint: string }[] = [
  {
    key: 'sender_entity_type',
    label: 'Тип отправителя',
    hint: 'Колонка со значениями: account, individual, business, payment_institution'
  },
  {
    key: 'receiver_entity_type',
    label: 'Тип получателя',
    hint: 'Колонка со значениями: account, individual, business, payment_institution'
  }
]

const EXTENDED_FIELDS: { key: keyof ColumnMapping; label: string }[] = [
  { key: 'sender_bank', label: 'From Bank (опционально)' },
  { key: 'receiver_bank', label: 'To Bank (опционально)' },
  { key: 'amount_received', label: 'Amount Received (опционально)' },
  { key: 'payment_currency', label: 'Payment Currency (опционально)' },
  { key: 'receiving_currency', label: 'Receiving Currency (опционально)' },
  { key: 'transaction_type', label: 'Payment Format (опционально)' },
  { key: 'device_id', label: 'Device ID (опционально)' },
  { key: 'ip_address', label: 'IP Address (опционально)' }
]

const NONE = '__none__'

const FALLBACK_ENTITY_TYPES: EntityTypeHint[] = [
  { code: 'account', label_ru: 'Счёт', short_description: 'Банковский счёт без явного владельца.' },
  { code: 'individual', label_ru: 'Физлицо', short_description: 'Физическое лицо — частный клиент банка.' },
  { code: 'business', label_ru: 'Юрлицо', short_description: 'Юридическое лицо — компания, ИП, ООО.' },
  {
    code: 'payment_institution',
    label_ru: 'Платёжный институт',
    short_description: 'Платёжный сервис, обменник, эквайер.'
  }
]

export default function ColumnMapper({ columns, preview, onSubmit, isLoading }: ColumnMapperProps) {
  const [entityTypeHints, setEntityTypeHints] = useState<EntityTypeHint[]>(FALLBACK_ENTITY_TYPES)

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? ''
    fetch(`${apiBase}/api/v1/entity-types`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (Array.isArray(data)) setEntityTypeHints(data) })
      .catch(() => {/* use fallback */})
  }, [])

  const [mapping, setMapping] = useState<Partial<ColumnMapping>>(() => {
    const auto: Partial<ColumnMapping> = {}
    const lc = columns.map(c => c.toLowerCase())
    const candidates: [keyof ColumnMapping, string[]][] = [
      ['sender_id', ['sender_id', 'sender', 'from', 'source']],
      ['receiver_id', ['receiver_id', 'receiver', 'to', 'target', 'destination']],
      ['amount_paid', ['amount_paid', 'amount', 'value', 'sum', 'transaction_amount']],
      ['timestamp', ['timestamp', 'time', 'date', 'created_at', 'ts']],
      ['sender_entity_type', ['sender_entity_type', 'sender_type', 'from_type', 'entity_type', 'type']],
      ['receiver_entity_type', ['receiver_entity_type', 'receiver_type', 'to_type']],
      ['device_id', ['device_id', 'device', 'device_name']],
      ['ip_address', ['ip_address', 'ip', 'ip_addr']],
      ['sender_bank', ['sender_bank', 'from_bank', 'sending_bank']],
      ['receiver_bank', ['receiver_bank', 'to_bank', 'receiving_bank']],
      ['amount_received', ['amount_received', 'received_amount']],
      ['payment_currency', ['payment_currency']],
      ['receiving_currency', ['receiving_currency']],
      ['transaction_type', ['transaction_type', 'payment_type', 'payment_format', 'type']],
      ['is_laundering', ['is_laundering', 'laundering', 'label', 'fraud']]
    ]
    for (const [field, hints] of candidates) {
      const idx = hints.map(h => lc.indexOf(h)).find(i => i !== -1)
      if (idx !== undefined) auto[field] = columns[idx]
    }
    return auto
  })

  function handleChange(field: keyof ColumnMapping, value: string) {
    setMapping(prev => ({ ...prev, [field]: value === NONE || !value ? undefined : value }))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const { sender_id, receiver_id, amount_paid, timestamp, sender_entity_type, receiver_entity_type } = mapping
    if (!sender_id || !receiver_id || !amount_paid || !timestamp || !sender_entity_type || !receiver_entity_type) return
    onSubmit({
      sender_id,
      receiver_id,
      amount_paid,
      timestamp,
      sender_entity_type,
      receiver_entity_type,
      ...mapping
    })
  }

  const isValid = !!(
    mapping.sender_id &&
    mapping.receiver_id &&
    mapping.amount_paid &&
    mapping.timestamp &&
    mapping.sender_entity_type &&
    mapping.receiver_entity_type
  )

  const allowedValuesText = entityTypeHints.map(t => `${t.code} (${t.label_ru})`).join(' · ')

  return (
    <Flex direction="column" gap="5" style={{ width: '100%' }}>
      <Flex direction="column" gap="1">
        <Heading size="4">Сопоставление столбцов CSV</Heading>
        <Text size="2" color="gray">
          Выберите, какой столбец CSV соответствует каждому полю.
        </Text>
      </Flex>

      {preview.length > 0 && (
        <Box style={{ overflowX: 'auto' }}>
          <Table.Root size="1" variant="surface">
            <Table.Header>
              <Table.Row>
                {columns.map(col => (
                  <Table.ColumnHeaderCell key={col}>{col}</Table.ColumnHeaderCell>
                ))}
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {preview.map((row, ri) => (
                <Table.Row key={ri}>
                  {row.map((cell, ci) => (
                    <Table.Cell key={ci}>
                      <Text
                        size="1"
                        color="gray"
                        style={{
                          maxWidth: 120,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          display: 'block'
                        }}
                      >
                        {cell}
                      </Text>
                    </Table.Cell>
                  ))}
                </Table.Row>
              ))}
            </Table.Body>
          </Table.Root>
        </Box>
      )}

      <form onSubmit={handleSubmit}>
        <Flex direction="column" gap="4">
          {/* Основные */}
          <Flex direction="column" gap="2">
            <Text
              size="1"
              weight="medium"
              color="gray"
              style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
            >
              Основные
            </Text>
            <Box style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              {REQUIRED_FIELDS.map(({ key, label }) => (
                <Flex key={key} direction="column" gap="1">
                  <Text as="label" size="2" weight="medium">
                    {label}{' '}
                    <Text size="2" color="red">
                      *
                    </Text>
                  </Text>
                  <Select.Root
                    value={(mapping[key] as string | undefined) ?? NONE}
                    onValueChange={v => handleChange(key, v)}
                  >
                    <Select.Trigger placeholder="— выбрать —" style={{ width: '100%' }} />
                    <Select.Content>
                      {columns.map(col => (
                        <Select.Item key={col} value={col}>
                          {col}
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Root>
                </Flex>
              ))}
            </Box>
          </Flex>

          {/* Типы сущностей */}
          <Flex direction="column" gap="2">
            <Text
              size="1"
              weight="medium"
              color="gray"
              style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
            >
              Типы сущностей
            </Text>
            <Box style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              {ENTITY_TYPE_FIELDS.map(({ key, label }) => (
                <Flex key={key} direction="column" gap="1">
                  <Text as="label" size="2" weight="medium">
                    {label}{' '}
                    <Text size="2" color="red">
                      *
                    </Text>
                  </Text>
                  <Select.Root
                    value={(mapping[key] as string | undefined) ?? NONE}
                    onValueChange={v => handleChange(key, v)}
                  >
                    <Select.Trigger placeholder="— выбрать —" style={{ width: '100%' }} />
                    <Select.Content>
                      {columns.map(col => (
                        <Select.Item key={col} value={col}>
                          {col}
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Root>
                  <Text size="1" color="gray">
                    {allowedValuesText}
                  </Text>
                </Flex>
              ))}
            </Box>
          </Flex>

          {/* Расширенные */}
          <Flex direction="column" gap="2">
            <Text
              size="1"
              weight="medium"
              color="gray"
              style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
            >
              Расширенные
            </Text>
            <Box style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              {EXTENDED_FIELDS.map(({ key, label }) => (
                <Flex key={key} direction="column" gap="1">
                  <Text as="label" size="2" color="gray">
                    {label}
                  </Text>
                  <Select.Root
                    value={(mapping[key] as string | null | undefined) ?? NONE}
                    onValueChange={v => handleChange(key, v)}
                  >
                    <Select.Trigger placeholder="— нет —" style={{ width: '100%' }} />
                    <Select.Content>
                      <Select.Item value={NONE}>— нет —</Select.Item>
                      {columns.map(col => (
                        <Select.Item key={col} value={col}>
                          {col}
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Root>
                </Flex>
              ))}
            </Box>
          </Flex>

          {/* Валидация */}
          <Flex direction="column" gap="2">
            <Text
              size="1"
              weight="medium"
              color="gray"
              style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
            >
              Валидация
            </Text>
            <Box style={{ maxWidth: 'calc(50% - var(--space-2))' }}>
              <Flex direction="column" gap="1">
                <Text as="label" size="2" color="gray">
                  Is Laundering (ground truth) (опционально)
                </Text>
                <Select.Root
                  value={(mapping.is_laundering as string | null | undefined) ?? NONE}
                  onValueChange={v => handleChange('is_laundering', v)}
                >
                  <Select.Trigger placeholder="— нет —" style={{ width: '100%' }} />
                  <Select.Content>
                    <Select.Item value={NONE}>— нет —</Select.Item>
                    {columns.map(col => (
                      <Select.Item key={col} value={col}>
                        {col}
                      </Select.Item>
                    ))}
                  </Select.Content>
                </Select.Root>
                <Text size="1" color="gray">
                  Используется только для валидации. Не участвует в анализе.
                </Text>
              </Flex>
            </Box>
          </Flex>

          <Button type="submit" disabled={!isValid || isLoading} loading={isLoading} size="3">
            Анализировать граф
          </Button>
        </Flex>
      </form>
    </Flex>
  )
}
