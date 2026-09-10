import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

export type Alarm = { id: number; well_id: string; severity: string; event_type: string; status: string; message: string; raised_at: string }
export type Device = { id: string; status: string; last_heartbeat: string | null; metrics: Record<string, unknown> }
export type Telemetry = { timestamp: string; sequence: number; measurements: Record<string, number>; event_hint?: string }

export const getDashboard = () => api.get<{ wells: number; online_devices: number; active_alarms: number }>('/dashboard').then((r) => r.data)
export const getWells = () => api.get<{ id: string; display_name: string }[]>('/wells').then((r) => r.data)
export const getHistory = (wellId: string) => api.get<Telemetry[]>(`/wells/${wellId}/telemetry`).then((r) => r.data)
export const getAlarms = () => api.get<Alarm[]>('/alarms').then((r) => r.data)
export const acknowledge = (id: number) => api.post<Alarm>(`/alarms/${id}/acknowledge`).then((r) => r.data)
export const getDevices = () => api.get<Device[]>('/edge-devices').then((r) => r.data)
export const command = (deviceId: string, payload: Record<string, unknown>) => api.post(`/replay/${deviceId}/commands`, payload).then((r) => r.data)
