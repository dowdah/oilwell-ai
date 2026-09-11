import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

export type Alarm = { id: number; well_id: string; severity: string; event_type: string; status: string; message: string; raised_at: string }
export type Device = { id: string; status: string; last_heartbeat: string | null; metrics: Record<string, unknown> }
export type Telemetry = { timestamp: string; sequence: number; measurements: Record<string, number>; event_hint?: string }
export type Inference = {
  id: number; well_id: string; telemetry_id: number; status: string
  model_type: string; model_mode: 'active' | 'shadow'
  window_start: string | null; window_end: string | null; model_version: string | null
  predicted_class: string | null; confidence: number | null; anomaly_score: number | null
  feature_schema_version: string | null; inference_latency_ms: number | null
}
export type ModelStatus = {
  mode: 'active' | 'shadow'; status: string; error: string | null; model_type: string | null
  version: string | null; training_data_version: string | null; metrics: Record<string, number> | null
  feature_schema_version: string | null
}
export type Citation = { id: string; title: string; url: string; version: string; license: string }
export type Diagnostic = {
  id: number; request_id: string; well_id: string; inference_id: number; status: 'completed' | 'refused'
  model_version: string | null; knowledge_base_version: string; explanation_version: string | null
  content: string; citations: Citation[]; input_summary: Record<string, unknown>
  evidence_status: 'complete' | 'degraded' | 'refused'; degradation_reasons: string[]; created_at: string
}

export const getDashboard = () => api.get<{ wells: number; online_devices: number; active_alarms: number }>('/dashboard').then((r) => r.data)
export const getWells = () => api.get<{ id: string; display_name: string }[]>('/wells').then((r) => r.data)
export const getHistory = (wellId: string) => api.get<Telemetry[]>(`/wells/${wellId}/telemetry`).then((r) => r.data)
export const getLatestInference = (wellId: string) => api.get<Inference>(`/wells/${wellId}/inference/latest`).then((r) => r.data)
export const getLatestComparison = (wellId: string) => api.get<Inference[]>(`/wells/${wellId}/inference/comparison/latest`).then((r) => r.data)
export const createDiagnostic = (wellId: string, inferenceId: number) => api.post<Diagnostic>(`/wells/${wellId}/diagnostics`, { inference_id: inferenceId }).then((r) => r.data)
export const getDiagnostics = (wellId: string) => api.get<Diagnostic[]>(`/wells/${wellId}/diagnostics`).then((r) => r.data)
export const getModels = () => api.get<ModelStatus[]>('/models').then((r) => r.data)
export const getAlarms = () => api.get<Alarm[]>('/alarms').then((r) => r.data)
export const acknowledge = (id: number) => api.post<Alarm>(`/alarms/${id}/acknowledge`).then((r) => r.data)
export const getDevices = () => api.get<Device[]>('/edge-devices').then((r) => r.data)
export const command = (deviceId: string, payload: Record<string, unknown>) => api.post(`/replay/${deviceId}/commands`, payload).then((r) => r.data)
