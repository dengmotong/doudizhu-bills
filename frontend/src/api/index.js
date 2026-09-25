import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000,
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const detail = err?.response?.data?.detail || err?.message || '请求失败'
    return Promise.reject(new Error(typeof detail === 'string' ? detail : JSON.stringify(detail)))
  },
)

// ---- 图片地址 ----
export const imageUrl = (filename) => `/api/images/${encodeURIComponent(filename)}`

// ---- 玩家 ----
export const fetchPlayers = () => api.get('/players')
export const createPlayer = (name) => api.post('/players', { name })
export const renamePlayer = (id, name) => api.put(`/players/${id}`, { name })
export const deletePlayer = (id) => api.delete(`/players/${id}`)

// ---- 账单 / 对局 ----
export const fetchSessions = () => api.get('/sessions')
export const fetchBills = () => api.get('/bills')
export const deleteSession = (id) => api.delete(`/sessions/${id}`)
export const updateBill = (id, data) => api.put(`/bills/${id}`, data)
export const deleteBill = (id) => api.delete(`/bills/${id}`)
export const saveSessionBatch = (files, payload) => {
  const fd = new FormData()
  files.forEach((f) => fd.append('files', f))
  fd.append('payload', JSON.stringify(payload))
  return api.post('/sessions/batch', fd)
}

// ---- 识别 ----
export const recognize = (files, config = {}) => {
  const fd = new FormData()
  files.forEach((f) => fd.append('files', f))
  if (config.api_key) fd.append('api_key', config.api_key)
  if (config.base_url) fd.append('base_url', config.base_url)
  if (config.model) fd.append('model', config.model)
  return api.post('/recognize', fd)
}

// ---- 统计 ----
export const fetchCumulativeStats = () => api.get('/stats/cumulative')
export const fetchMonthlyStats = () => api.get('/stats/monthly')
export const fetchDailyStats = () => api.get('/stats/daily')
export const fetchSessionStats = () => api.get('/stats/session')

// ---- 结账 ----
export const computeTransfers = (sessionIds, pricePerPoint) =>
  api.post('/settlement/transfers', { session_ids: sessionIds, price_per_point: pricePerPoint })
export const settleSingle = (id, pricePerPoint) =>
  api.post(`/sessions/${id}/settle`, { price_per_point: pricePerPoint })
export const unsettleSingle = (id) => api.post(`/sessions/${id}/unsettle`)
export const batchSettle = (sessionIds, pricePerPoint) =>
  api.post('/settlement/batch-settle', { session_ids: sessionIds, price_per_point: pricePerPoint })

export default api
