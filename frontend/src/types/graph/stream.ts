import type { NodeData } from './node'
import type { EdgeData } from './edge'
import type { GraphMeta } from './meta'
import type { DetectorResult } from './detector'
import type { AnalysisResult } from './analysis'

export interface SSEHandlers {
  onGraphMeta?: (meta: GraphMeta) => void
  onNodesChunk?: (nodes: NodeData[]) => void
  onEdgesChunk?: (edges: EdgeData[]) => void
  onAnalysisResult?: (result: AnalysisResult) => void
  /** Все данные получены - граф готов к отображению */
  onCompleted?: (data: { job_id: string }) => void
  /** Промежуточный статус job во время обработки */
  onStatus?: (data: { status: string; job_id: string }) => void
  /** Серверная ошибка с сообщением (отдельно от сетевых ошибок es.onerror) */
  onServerError?: (data: { message: string }) => void
  onDetectorResult?: (result: DetectorResult) => void
  onStreamDone?: () => void
  onError?: (error: Event) => void
}

export type StreamStage = 'idle' | 'connecting' | 'streaming' | 'detectors' | 'done' | 'error'
