/**
 * Upload Page - Document upload with drag-and-drop, auto-classify, and process.
 */

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  Upload, FileText, Trash2, Play, Loader2,
  CheckCircle, AlertCircle, ChevronDown
} from 'lucide-react'
import { uploadSingle, uploadBatch, extractDocument } from '../services/api'
import {
  DOC_TYPES, getDocType, getStatusBadge,
  formatFileSize, isProcessing
} from '../utils/helpers'

const ACCEPTED_TYPES = {
  'image/*': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'],
  'application/pdf': ['.pdf'],
}

const getApiErrorMessage = (err) =>
  err?.response?.data?.detail || err?.message || 'Request failed'

function FileRow({ item, onRemove, onTypeChange, onProcess }) {
  const statusInfo = getStatusBadge(item.status)
  const typeInfo = getDocType(item.documentType)
  const processing = isProcessing(item.status)

  return (
    <div className="flex items-center gap-3 p-3 bg-slate-800/60 rounded-xl border border-slate-700/50 animate-fade-in">
      {/* Icon */}
      <div className="text-2xl flex-shrink-0">{typeInfo.icon}</div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-200 truncate">{item.file.name}</p>
        <p className="text-xs text-slate-500">{formatFileSize(item.file.size)}</p>
      </div>

      {/* Type selector */}
      <div className="relative">
        <select
          value={item.documentType || ''}
          onChange={(e) => onTypeChange(item.id, e.target.value)}
          disabled={processing || item.status === 'extracted'}
          className="appearance-none bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 
                     text-xs text-slate-200 pr-7 cursor-pointer 
                     focus:outline-none focus:ring-1 focus:ring-ink-600
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <option value="">Auto-detect</option>
          {DOC_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        <ChevronDown size={12} className="absolute right-2 top-2 text-slate-400 pointer-events-none" />
      </div>

      {/* Status */}
      <span className={`badge ${statusInfo.class} flex-shrink-0`}>
        <span className={`status-dot ${statusInfo.dot}`} />
        {item.status === 'uploading' ? `${item.uploadProgress || 0}%` : statusInfo.label}
      </span>

      {/* Actions */}
      <div className="flex items-center gap-1.5 flex-shrink-0">
        {item.documentId && !processing && item.status !== 'extracted' && (
          <button
            onClick={() => onProcess(item)}
            className="btn-primary !px-2.5 !py-1.5 text-xs"
            title="Process document"
          >
            {processing ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
            Extract
          </button>
        )}
        {item.status === 'extracted' && (
          <CheckCircle size={16} className="text-green-400" />
        )}
        {item.status === 'failed' && (
          <AlertCircle size={16} className="text-red-400" title={item.error} />
        )}
        <button
          onClick={() => onRemove(item.id)}
          className="p-1.5 text-slate-500 hover:text-red-400 transition-colors rounded-lg hover:bg-red-900/20"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}

export default function UploadPage() {
  const navigate = useNavigate()
  const [files, setFiles] = useState([])
  const [globalType, setGlobalType] = useState('')
  const [batchProcessing, setBatchProcessing] = useState(false)

  const onDrop = useCallback((accepted) => {
    const newFiles = accepted.map((file) => ({
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      file,
      status: 'queued',
      documentType: globalType || '',
      documentId: null,
      uploadProgress: 0,
      error: null,
    }))
    setFiles((prev) => [...prev, ...newFiles])
  }, [globalType])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    multiple: true,
  })

  const updateFile = (id, updates) =>
    setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, ...updates } : f)))

  const removeFile = (id) =>
    setFiles((prev) => prev.filter((f) => f.id !== id))

  const uploadFile = async (item) => {
    updateFile(item.id, { status: 'uploading' })
    try {
      const res = await uploadSingle(
        item.file,
        item.documentType || null,
        (pct) => updateFile(item.id, { uploadProgress: pct })
      )
      updateFile(item.id, {
        status: 'uploaded',
        documentId: res.data.document_id,
      })
      return res.data.document_id
    } catch (err) {
      updateFile(item.id, { status: 'failed', error: getApiErrorMessage(err) })
      return null
    }
  }

  const processFile = async (item) => {
    if (!item.documentId) return
    updateFile(item.id, { status: 'extracting' })
    try {
      await extractDocument(item.documentId, item.documentType || null)
      updateFile(item.id, { status: 'extracted' })
      toast.success(`Extracted: ${item.file.name}`)
    } catch (err) {
      updateFile(item.id, { status: 'failed', error: getApiErrorMessage(err) })
    }
  }

  const handleUploadAll = async () => {
    const queued = files.filter((f) => f.status === 'queued')
    if (!queued.length) {
      toast.error('No queued files to upload')
      return
    }
    let successCount = 0
    let failedCount = 0
    for (const item of queued) {
      const docId = await uploadFile(item)
      if (docId) {
        successCount += 1
      } else {
        failedCount += 1
      }
    }

    if (failedCount === 0) {
      toast.success(`Uploaded ${successCount} file${successCount === 1 ? '' : 's'}`)
    } else if (successCount > 0) {
      toast.error(`Uploaded ${successCount}, failed ${failedCount}`)
    } else {
      toast.error('All uploads failed')
    }
  }

  const handleProcessAll = async () => {
    setBatchProcessing(true)
    const toProcess = files.filter(
      (f) => f.documentId && f.status === 'uploaded'
    )
    if (!toProcess.length) {
      toast.error('Upload files first')
      setBatchProcessing(false)
      return
    }

    for (const item of toProcess) {
      await processFile(item)
    }
    setBatchProcessing(false)
    toast.success('Batch extraction complete!')
  }

  const queuedCount = files.filter((f) => f.status === 'queued').length
  const uploadedCount = files.filter((f) => f.status === 'uploaded').length
  const extractedCount = files.filter((f) => f.status === 'extracted').length
  const failedCount = files.filter((f) => f.status === 'failed').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-serif text-2xl font-bold text-slate-100">
          Document Upload
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Upload documents for AI-powered extraction. Supports invoices, receipts, contracts, IDs, and more.
        </p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200
          ${isDragActive
            ? 'border-ink-500 bg-ink-900/20 scale-[1.01]'
            : 'border-slate-700 hover:border-slate-600 bg-slate-900/40'
          }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-4">
          <div className={`p-4 rounded-2xl transition-colors ${isDragActive ? 'bg-ink-800/50' : 'bg-slate-800'}`}>
            <Upload size={32} className={isDragActive ? 'text-ink-400' : 'text-slate-400'} />
          </div>
          {isDragActive ? (
            <p className="text-ink-300 font-medium text-lg">Drop your documents here!</p>
          ) : (
            <>
              <div>
                <p className="text-slate-200 font-medium text-lg">
                  Drop documents here or click to browse
                </p>
                <p className="text-slate-500 text-sm mt-1">
                  PDF, PNG, JPG, TIFF, BMP, WebP · Up to {50}MB per file
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                {DOC_TYPES.slice(0, 5).map((t) => (
                  <span key={t.value} className="bg-slate-800 px-2.5 py-1 rounded-full">
                    {t.icon} {t.label}
                  </span>
                ))}
                <span className="text-slate-600">+ more</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Controls */}
      {files.length > 0 && (
        <div className="card p-4 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4 text-sm">
            <span className="text-slate-400">
              <span className="text-slate-100 font-medium">{files.length}</span> files
            </span>
            {queuedCount > 0 && (
              <span className="badge badge-gray">{queuedCount} queued</span>
            )}
            {uploadedCount > 0 && (
              <span className="badge badge-info">{uploadedCount} ready</span>
            )}
            {extractedCount > 0 && (
              <span className="badge badge-success">{extractedCount} done</span>
            )}
            {failedCount > 0 && (
              <span className="badge badge-danger">{failedCount} failed</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Global type override */}
            <div className="relative">
              <select
                value={globalType}
                onChange={(e) => setGlobalType(e.target.value)}
                className="appearance-none bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 
                           text-xs text-slate-200 pr-8 cursor-pointer focus:outline-none focus:ring-1 focus:ring-ink-600"
              >
                <option value="">Auto-detect type</option>
                {DOC_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.icon} {t.label}</option>
                ))}
              </select>
              <ChevronDown size={12} className="absolute right-2.5 top-2.5 text-slate-400 pointer-events-none" />
            </div>

            {queuedCount > 0 && (
              <button onClick={handleUploadAll} className="btn-secondary">
                <Upload size={14} />
                Upload All ({queuedCount})
              </button>
            )}

            {uploadedCount > 0 && (
              <button
                onClick={handleProcessAll}
                disabled={batchProcessing}
                className="btn-primary"
              >
                {batchProcessing
                  ? <><Loader2 size={14} className="animate-spin" /> Processing...</>
                  : <><Play size={14} /> Extract All ({uploadedCount})</>
                }
              </button>
            )}

            {extractedCount > 0 && (
              <button
                onClick={() => navigate('/documents')}
                className="btn-secondary"
              >
                <FileText size={14} />
                View Results
              </button>
            )}
          </div>
        </div>
      )}

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((item) => (
            <FileRow
              key={item.id}
              item={item}
              onRemove={removeFile}
              onTypeChange={(id, type) => updateFile(id, { documentType: type })}
              onProcess={async (item) => {
                if (item.status === 'queued') {
                  const docId = await uploadFile(item)
                  if (docId) {
                    const uploaded = { ...item, documentId: docId }
                    await processFile(uploaded)
                  }
                } else {
                  await processFile(item)
                }
              }}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {files.length === 0 && (
        <div className="text-center py-8 text-slate-600">
          <FileText size={40} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">No documents added yet</p>
        </div>
      )}
    </div>
  )
}
