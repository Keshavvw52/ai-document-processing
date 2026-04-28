import axios from 'axios'
import toast from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 600000, // 10 min for OCR + LLM calls on PDFs or first EasyOCR load
})

// Response interceptor for error handling
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const msg = error.response?.data?.detail || error.message || 'Request failed'
    toast.error(msg)
    return Promise.reject(error)
  }
)

// ── Upload ──────────────────────────────────────────────────────────────────

export const uploadSingle = (file, documentType = null, onProgress) => {
  const fd = new FormData()
  fd.append('file', file)
  if (documentType) fd.append('document_type', documentType)
  return api.post('/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => onProgress?.(Math.round((e.loaded / e.total) * 100)),
  })
}

export const uploadBatch = (files, batchName = null, documentType = null, onProgress) => {
  const fd = new FormData()
  files.forEach((f) => fd.append('files', f))
  if (batchName) fd.append('batch_name', batchName)
  if (documentType) fd.append('document_type', documentType)
  return api.post('/upload/batch', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => onProgress?.(Math.round((e.loaded / e.total) * 100)),
  })
}

// ── Classification ──────────────────────────────────────────────────────────

export const classifyDocument = (documentId) =>
  api.post('/classify', { document_id: documentId })

// ── Extraction ──────────────────────────────────────────────────────────────

export const extractDocument = (documentId, documentType = null, forceReprocess = false) =>
  api.post('/extract', {
    document_id: documentId,
    document_type: documentType,
    force_reprocess: forceReprocess,
  })

export const extractBatch = (documentIds, documentType = null) =>
  api.post('/extract/batch', { document_ids: documentIds, document_type: documentType })

// ── Documents ──────────────────────────────────────────────────────────────

export const listDocuments = (params = {}) =>
  api.get('/documents', { params })

export const getDocument = (id) =>
  api.get(`/documents/${id}`)

export const updateFields = (id, fields) =>
  api.put(`/documents/${id}/fields`, { fields })

export const updateStatus = (id, status) =>
  api.patch(`/documents/${id}/status`, { status })

export const deleteDocument = (id) =>
  api.delete(`/documents/${id}`)

export const getPreview = (id) =>
  api.get(`/documents/${id}/preview`)

export const getTables = (id) =>
  api.get(`/documents/${id}/tables`)

// ── Batch ──────────────────────────────────────────────────────────────────

export const getBatchStatus = (batchId) =>
  api.get(`/batch/${batchId}/status`)

// ── Export ─────────────────────────────────────────────────────────────────

export const exportDocuments = async (documentIds, format = 'json') => {
  const response = await api.post('/export', { document_ids: documentIds, format }, {
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `export.${format}`)
  document.body.appendChild(link)
  link.click()
  link.remove()
}

export const exportBatch = async (batchId, format = 'zip') => {
  const response = await api.post(`/export/batch/${batchId}`, null, {
    params: { format },
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `batch_${batchId}.${format}`)
  document.body.appendChild(link)
  link.click()
  link.remove()
}

// ── Templates & Stats ──────────────────────────────────────────────────────

export const getTemplates = () => api.get('/templates')
export const getStats = () => api.get('/stats')
export const getHealth = () => api.get('/health')

export default api
