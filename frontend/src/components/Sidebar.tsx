'use client'

import { useState } from 'react'
import {
  Badge,
  Box,
  Flex,
  IconButton,
  ScrollArea,
  Separator,
  Text,
  Tooltip
} from '@radix-ui/themes'
import {
  ArrowRightIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  LoopIcon,
  MagnifyingGlassIcon,
  MobileIcon,
  Share2Icon
} from '@radix-ui/react-icons'
import type { DetectorResult } from '@/types/graph/detector'
import type { NodeData } from '@/types/graph/node'

const PATTERN_META: Record<string, { label: string; icon: React.ReactNode }> = {
  cycles: { label: 'Транзакционные циклы', icon: <LoopIcon /> },
  fanout: { label: 'Веерное дробление', icon: <Share2Icon /> },
  transit: { label: 'Транзитные узлы', icon: <ArrowRightIcon /> },
  shared_device: { label: 'Общие устройства/IP', icon: <MobileIcon /> }
}

const ENTITY_HEX: Record<string, string> = {
  account: '#66bb6a',
  individual: '#4fc3f7',
  business: '#ffa726',
  payment_institution: '#ab47bc',
  // backward compat
  client: '#4fc3f7',
  company: '#ffa726',
  device: '#ab47bc',
  unknown: '#6b7280'
}

const ENTITY_LABEL: Record<string, string> = {
  account: 'Счета',
  individual: 'Физлица',
  business: 'Юрлица',
  payment_institution: 'Платёжные институты',
  client: 'Клиенты',
  company: 'Юрлица',
  device: 'Устройства',
  unknown: 'Прочее'
}

const ROLE_HEX: Record<string, string> = {
  hub: '#ff453a',
  transit: '#ff9f0a',
  isolated: '#9ca3af',
  regular: '#6b7280'
}

const ROLE_ICON: Record<string, string> = {
  hub: '◉',
  transit: '⇄',
  isolated: '·',
  regular: ''
}

const ROLE_LABEL: Record<string, string> = {
  hub: 'Концентратор',
  transit: 'Транзитный',
  isolated: 'Одиночный',
  regular: 'Обычный'
}

interface SidebarProps {
  detectorResults: DetectorResult[]
  onHighlightPattern: (nodeIds: Set<string> | null) => void
  isCollapsed: boolean
  onToggleCollapse: () => void
  launderingNodes: NodeData[]
  onSelectLaunderingNode: (node: NodeData) => void
  sizeScale: number
  onSizeScaleChange: (v: number) => void
  entityGroups?: { type: string; count: number }[]
  hiddenEntityTypes?: Set<string>
  onToggleEntityType?: (type: string) => void
  behavioralRoleGroups?: { role: string; count: number }[]
  hiddenBehavioralRoles?: Set<string>
  onToggleBehavioralRole?: (role: string) => void
}

function extractNodeIds(result: DetectorResult): Set<string> {
  const ids = new Set<string>()
  for (const item of result.items) {
    if (Array.isArray(item.node_ids)) (item.node_ids as string[]).forEach(id => ids.add(String(id)))
    if (Array.isArray(item.nodes)) (item.nodes as string[]).forEach(id => ids.add(String(id)))
    if (typeof item.node_id === 'string') ids.add(item.node_id)
    if (typeof item.source_node === 'string') ids.add(item.source_node)
    if (Array.isArray(item.receivers))
      (item.receivers as string[]).forEach(id => ids.add(String(id)))
  }
  return ids
}

export default function Sidebar({
  detectorResults,
  onHighlightPattern,
  isCollapsed,
  onToggleCollapse,
  launderingNodes,
  onSelectLaunderingNode,
  sizeScale,
  onSizeScaleChange,
  entityGroups,
  hiddenEntityTypes,
  onToggleEntityType,
  behavioralRoleGroups,
  hiddenBehavioralRoles,
  onToggleBehavioralRole
}: SidebarProps) {
  const [activePattern, setActivePattern] = useState<string | null>(null)

  function handlePatternClick(patternType: string, result: DetectorResult) {
    if (activePattern === patternType) {
      setActivePattern(null)
      onHighlightPattern(null)
    } else {
      setActivePattern(patternType)
      onHighlightPattern(extractNodeIds(result))
    }
  }

  if (isCollapsed) {
    return (
      <Flex
        direction="column"
        align="center"
        py="3"
        gap="3"
        style={{
          width: 40,
          flexShrink: 0,
          borderRight: '1px solid var(--gray-4)',
          background: 'var(--color-panel-solid)'
        }}
      >
        <Tooltip content="Развернуть панель" side="right">
          <IconButton variant="ghost" color="gray" size="1" onClick={onToggleCollapse}>
            <ChevronRightIcon />
          </IconButton>
        </Tooltip>
        {launderingNodes.length > 0 && (
          <Badge color="red" variant="solid" size="1" style={{ fontSize: 9 }}>
            {launderingNodes.length}
          </Badge>
        )}
      </Flex>
    )
  }

  return (
    <Flex
      direction="column"
      style={{
        width: 220,
        flexShrink: 0,
        borderRight: '1px solid var(--gray-4)',
        background: 'var(--color-panel-solid)'
      }}
    >
      <Flex
        align="center"
        justify="between"
        px="3"
        py="2"
        style={{ borderBottom: '1px solid var(--gray-4)' }}
      >
        <Text size="2" weight="medium">
          Фильтры
        </Text>
        <Tooltip content="Свернуть панель" side="right">
          <IconButton variant="ghost" color="gray" size="1" onClick={onToggleCollapse}>
            <ChevronLeftIcon />
          </IconButton>
        </Tooltip>
      </Flex>

      <ScrollArea style={{ flex: 1 }}>
        <Flex direction="column" gap="1" p="3">

          {/* Тип сущности */}
          {entityGroups && entityGroups.length > 0 && (
            <>
              <Text
                size="1"
                weight="medium"
                color="gray"
                mb="1"
                style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
              >
                Тип сущности
              </Text>
              <Flex direction="column" gap="1">
                {entityGroups.map(({ type, count }) => {
                  const isHidden = hiddenEntityTypes?.has(type) ?? false
                  const color = ENTITY_HEX[type] ?? ENTITY_HEX.unknown
                  return (
                    <Box
                      key={type}
                      onClick={() => onToggleEntityType?.(type)}
                      style={{
                        cursor: 'pointer',
                        borderRadius: 'var(--radius-2)',
                        padding: '5px 8px',
                        opacity: isHidden ? 0.4 : 1,
                        transition: 'opacity 150ms, background 150ms'
                      }}
                      className="hover:bg-[var(--gray-3)]"
                    >
                      <Flex align="center" justify="between" gap="2">
                        <Flex align="center" gap="2">
                          <div
                            style={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              background: color,
                              flexShrink: 0
                            }}
                          />
                          <Text size="2" style={{ color: 'var(--gray-12)' }}>
                            {ENTITY_LABEL[type] ?? type}
                          </Text>
                        </Flex>
                        <Badge size="1" color="gray" variant="soft" style={{ flexShrink: 0 }}>
                          {count}
                        </Badge>
                      </Flex>
                    </Box>
                  )
                })}
              </Flex>
              <Separator size="4" my="2" />
            </>
          )}

          {/* Роль в графе */}
          {behavioralRoleGroups && behavioralRoleGroups.length > 0 && (
            <>
              <Text
                size="1"
                weight="medium"
                color="gray"
                mb="1"
                style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
              >
                Роль в графе
              </Text>
              <Flex direction="column" gap="1">
                {behavioralRoleGroups.map(({ role, count }) => {
                  const isHidden = hiddenBehavioralRoles?.has(role) ?? false
                  const color = ROLE_HEX[role] ?? '#6b7280'
                  const icon = ROLE_ICON[role] ?? ''
                  return (
                    <Box
                      key={role}
                      onClick={() => onToggleBehavioralRole?.(role)}
                      style={{
                        cursor: 'pointer',
                        borderRadius: 'var(--radius-2)',
                        padding: '5px 8px',
                        opacity: isHidden ? 0.4 : 1,
                        transition: 'opacity 150ms, background 150ms'
                      }}
                      className="hover:bg-[var(--gray-3)]"
                    >
                      <Flex align="center" justify="between" gap="2">
                        <Flex align="center" gap="2">
                          <Text size="2" style={{ color, flexShrink: 0, minWidth: 12 }}>
                            {icon}
                          </Text>
                          <Text size="2" style={{ color: 'var(--gray-12)' }}>
                            {ROLE_LABEL[role] ?? role}
                          </Text>
                        </Flex>
                        <Badge size="1" color="gray" variant="soft" style={{ flexShrink: 0 }}>
                          {count}
                        </Badge>
                      </Flex>
                    </Box>
                  )
                })}
              </Flex>
              <Separator size="4" my="2" />
            </>
          )}

          {/* Размер узлов */}
          <Text
            size="1"
            weight="medium"
            color="gray"
            mb="1"
            style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
          >
            Размер
          </Text>

          <Flex direction="column" gap="1" px="1">
            <Flex align="center" justify="between">
              <Text size="1" color="gray">
                Масштаб узлов
              </Text>
              <Text size="1" weight="medium">
                {sizeScale.toFixed(1)}×
              </Text>
            </Flex>
            <input
              type="range"
              min="0.5"
              max="3"
              step="0.1"
              value={sizeScale}
              onChange={e => onSizeScaleChange(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-9)' }}
            />
          </Flex>

          <Separator size="4" my="2" />

          {/* Паттерны */}
          <Text
            size="1"
            weight="medium"
            color="gray"
            mb="1"
            style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
          >
            Паттерны
          </Text>

          {detectorResults.length === 0 ? (
            <Text size="2" color="gray" style={{ fontStyle: 'italic' }}>
              Ожидание анализа...
            </Text>
          ) : (
            <Flex direction="column" gap="1">
              {detectorResults.map(result => {
                const meta = PATTERN_META[result.pattern_type]
                const isActive = activePattern === result.pattern_type
                const count = result.items.length
                return (
                  <Box
                    key={result.pattern_type}
                    onClick={() => handlePatternClick(result.pattern_type, result)}
                    style={{
                      cursor: 'pointer',
                      borderRadius: 'var(--radius-2)',
                      padding: '5px 8px',
                      background: isActive ? 'var(--accent-3)' : undefined,
                      transition: 'background 150ms'
                    }}
                    className={isActive ? undefined : 'hover:bg-[var(--gray-3)]'}
                  >
                    <Flex align="center" justify="between" gap="2">
                      <Flex
                        align="center"
                        gap="2"
                        style={{ color: isActive ? 'var(--accent-11)' : undefined, minWidth: 0 }}
                      >
                        <Box style={{ flexShrink: 0, color: 'inherit' }}>
                          {meta?.icon ?? <MagnifyingGlassIcon />}
                        </Box>
                        <Text size="2" style={{ color: 'inherit' }}>
                          {meta?.label ?? result.pattern_type}
                        </Text>
                      </Flex>
                      <Badge
                        color={count > 0 ? 'amber' : 'gray'}
                        variant="soft"
                        size="1"
                        style={{ flexShrink: 0 }}
                      >
                        {count}
                      </Badge>
                    </Flex>
                  </Box>
                )
              })}
            </Flex>
          )}

          {activePattern && (
            <Box mt="2">
              <Text
                size="1"
                color="gray"
                style={{ cursor: 'pointer', textDecoration: 'underline' }}
                onClick={() => {
                  setActivePattern(null)
                  onHighlightPattern(null)
                }}
              >
                Сбросить подсветку
              </Text>
            </Box>
          )}

          {launderingNodes.length > 0 && (
            <>
              <Separator size="4" my="2" />

              <Flex align="center" justify="between" mb="1">
                <Text
                  size="1"
                  weight="medium"
                  color="gray"
                  style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
                >
                  Подозреваемые узлы
                </Text>
                <Badge color="red" variant="soft" size="1">
                  {launderingNodes.length}
                </Badge>
              </Flex>

              <Box style={{ maxHeight: 200, overflowY: 'auto' }}>
                <Flex direction="column" gap="1">
                  {launderingNodes.map(node => (
                    <Box
                      key={node.id}
                      onClick={() => onSelectLaunderingNode(node)}
                      style={{
                        cursor: 'pointer',
                        borderRadius: 'var(--radius-2)',
                        padding: '4px 8px',
                        transition: 'background 150ms'
                      }}
                      className="hover:bg-[var(--gray-3)]"
                    >
                      <Flex direction="column" gap="1">
                        <Text
                          size="1"
                          weight="medium"
                          style={{ fontFamily: 'var(--font-mono)', wordBreak: 'break-all' }}
                        >
                          {node.id.length > 20 ? node.id.slice(0, 18) + '…' : node.id}
                        </Text>
                        <Flex gap="1" wrap="wrap">
                          <Badge size="1" color="gray" variant="soft">
                            {ENTITY_LABEL[node.entity_type] ?? node.entity_type}
                          </Badge>
                          <Badge
                            size="1"
                            color={(node.risk_score ?? 0) > 0.7 ? 'red' : 'amber'}
                            variant="soft"
                          >
                            {Math.round((node.risk_score ?? 0) * 100)}%
                          </Badge>
                        </Flex>
                      </Flex>
                    </Box>
                  ))}
                </Flex>
              </Box>
            </>
          )}
        </Flex>
      </ScrollArea>
    </Flex>
  )
}
