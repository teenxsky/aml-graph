export type JobStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'GRAPH_BUILDING'
  | 'DETECTING'
  | 'SCORING'
  | 'LAYOUT'
  | 'CLUSTERING'
  | 'HIERARCHICAL_LAYOUT'
  | 'SAVING'
  | 'COMPLETED'
  | 'FAILED'

export type UploadFormat = 'IBM' | 'CUSTOM'

export interface JobCreated {
  job_id: string
  status: JobStatus
  created_at: string
}

export interface JobInfo {
  id: string
  status: JobStatus
  format: UploadFormat
  user_ip: string
  file_path: string | null
  column_mapping: Record<string, unknown> | null
  ladybug_ref: string | null
  detector_results: Record<string, unknown> | null
  error_msg: string | null
  created_at: string
  updated_at: string
}

export interface ResponseDTO<T> {
  data: T
  meta?: Record<string, unknown>
}

export interface PaginationMetaDTO {
  total: number
  limit: number
  offset: number
}

export interface PaginatedResponseDTO<T> {
  data: T
  meta: PaginationMetaDTO
}
