import type { ColumnMapping } from '@/types/api/column-mapping'
import type { JobCreated, JobInfo, PaginatedResponseDTO, ResponseDTO } from '@/types/api/jobs'
import type { AlgorithmDescription } from '@/types/graph/analysis'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? ''

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `Ошибка запроса (${res.status})`)
  }
  return (await res.json()) as Promise<T>
}

/** POST /api/v1/graph/processing/ibm - загрузка IBM AML CSV без маппинга. */
export async function uploadIbm(file: File): Promise<ResponseDTO<JobCreated>> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/api/v1/graph/processing/ibm`, {
    method: 'POST',
    body: form
  })
  return handleResponse<ResponseDTO<JobCreated>>(res)
}

/** POST /api/v1/graph/processing - загрузка CSV с маппингом колонок. */
export async function uploadCsv(
  file: File,
  columnMapping: ColumnMapping
): Promise<ResponseDTO<JobCreated>> {
  const form = new FormData()
  form.append('file', file)
  form.append('column_mapping', JSON.stringify(columnMapping))
  const res = await fetch(`${API_BASE}/api/v1/graph/processing`, {
    method: 'POST',
    body: form
  })
  return handleResponse<ResponseDTO<JobCreated>>(res)
}

/** GET /api/v1/algorithms - описания алгоритмов для вкладки метаданных. */
export async function fetchAlgorithms(): Promise<AlgorithmDescription[]> {
  const res = await fetch(`${API_BASE}/api/v1/algorithms`)
  return handleResponse<AlgorithmDescription[]>(res)
}

/** GET /api/v1/graph/processing/latest - последние задачи текущего пользователя. */
export async function getLatestJobs(
  page = 1,
  pageSize = 10
): Promise<PaginatedResponseDTO<JobInfo[]>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize)
  })
  const res = await fetch(`${API_BASE}/api/v1/graph/processing/latest?${params}`)
  return handleResponse<PaginatedResponseDTO<JobInfo[]>>(res)
}
