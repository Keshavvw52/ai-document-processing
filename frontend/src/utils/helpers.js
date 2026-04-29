/**
 * Frontend utilities: status badges, confidence display, type labels.
 */

export const DOC_TYPES = [
  { value: 'invoice',       label: 'Invoice',       icon: '🧾', color: 'text-emerald-400' },
  { value: 'receipt',       label: 'Receipt',        icon: '🏪', color: 'text-green-400' },
  { value: 'business_card', label: 'Business Card',  icon: '💼', color: 'text-blue-400' },
  { value: 'form',          label: 'Form',           icon: '📋', color: 'text-sky-400' },
  { value: 'id_card',       label: 'ID Card',        icon: '🪪', color: 'text-violet-400' },
  { value: 'contract',      label: 'Contract',       icon: '📜', color: 'text-orange-400' },
  { value: 'report',        label: 'Report',         icon: '📊', color: 'text-yellow-400' },
  { value: 'handwritten',   label: 'Handwritten',    icon: '✍️', color: 'text-pink-400' },
  { value: 'whiteboard',    label: 'Whiteboard',     icon: '📌', color: 'text-cyan-400' },
  { value: 'table',         label: 'Table',          icon: '🗃️', color: 'text-indigo-400' },
]

export const STATUSES = {
  uploaded:       { label: 'Uploaded',       class: 'badge-gray',    dot: 'bg-slate-500' },
  preprocessing:  { label: 'Preprocessing',  class: 'badge-warning', dot: 'bg-yellow-500 animate-pulse' },
  ocr_processing: { label: 'OCR Running',    class: 'badge-info',    dot: 'bg-blue-500 animate-pulse' },
  extracting:     { label: 'Extracting',     class: 'badge-info',    dot: 'bg-ink-500 animate-pulse' },
  extracted:      { label: 'Extracted',      class: 'badge-success', dot: 'bg-green-500' },
  under_review:   { label: 'Needs Review',   class: 'badge-warning', dot: 'bg-orange-500' },
  approved:       { label: 'Approved',       class: 'badge-success', dot: 'bg-emerald-500' },
  failed:         { label: 'Failed',         class: 'badge-danger',  dot: 'bg-red-500' },
}

export const getStatusBadge = (status) =>
  STATUSES[status] || { label: status, class: 'badge-gray', dot: 'bg-slate-500' }

export const getDocType = (type) =>
  DOC_TYPES.find((d) => d.value === type) || { value: type, label: type, icon: '📄', color: 'text-slate-400' }

export const getConfidenceClass = (score) => {
  if (typeof score === 'string') {
    if (score === 'high') return 'conf-high'
    if (score === 'medium') return 'conf-medium'
    return 'conf-low'
  }
  if (score >= 0.8) return 'conf-high'
  if (score >= 0.5) return 'conf-medium'
  return 'conf-low'
}

export const getConfidenceLabel = (score) => {
  if (typeof score === 'string') return score
  if (score >= 0.8) return 'High'
  if (score >= 0.5) return 'Medium'
  return 'Low'
}

export const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export const formatDateTime = (dateStr) => {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

export const formatFieldName = (key) =>
  key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

export const isProcessing = (status) =>
  ['preprocessing', 'ocr_processing', 'extracting'].includes(status)

export const isComplete = (status) =>
  ['extracted', 'approved', 'under_review'].includes(status)

export const canProcess = (status) =>
  ['uploaded', 'failed'].includes(status)