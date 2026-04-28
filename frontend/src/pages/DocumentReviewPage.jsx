/**
 * Document Review Page - Split view: image with bbox overlays + editable extracted fields.
 */

import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch'
import toast from 'react-hot-toast'
import {
  ArrowLeft, ZoomIn, ZoomOut, RotateCcw, CheckCircle,
  Edit3, Save, X, Download, RefreshCw, Loader2,
  ChevronRight, Table2, FileText, Eye
} from 'lucide-react'
import {
  getDocument, updateFields, updateStatus,
  extractDocument, exportDocuments, getPreview
} from '../services/api'
import {
  getStatusBadge, getDocType, getConfidenceClass,
  getConfidenceLabel, formatFieldName, formatDateTime, isProcessing
} from '../utils/helpers'

// ── Confidence Badge ──────────────────────────────────────────────────────

function ConfBadge({ score }) {
  const cls = getConfidenceClass(score)
  const label = getConfidenceLabel(score)
  const dot = score === 'high' || score >= 0.8 ? 'bg-green-500'
    : score === 'medium' || score >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <span className={`inline-flex items-center gap-1 text-xs ${cls} font-medium`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  )
}

// ── Editable Field Row ────────────────────────────────────────────────────

function FieldRow({ name, value, confidence, onSave }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  const displayValue = Array.isArray(value)
    ? `${value.length} items`
    : typeof value === 'object' && value !== null
      ? JSON.stringify(value)
      : String(value ?? '—')

  const startEdit = () => {
    setDraft(typeof value === 'string' ? value : JSON.stringify(value))
    setEditing(true)
  }

  const save = () => {
    onSave(name, draft)
    setEditing(false)
    toast.success('Field saved')
  }

  return (
    <div className="group flex items-start gap-3 py-2.5 border-b border-slate-800/60 last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="field-label">{formatFieldName(name)}</span>
          {confidence && <ConfBadge score={confidence} />}
        </div>
        {editing ? (
          <div className="flex items-center gap-2 mt-1">
            <input
              autoFocus
              className="input !py-1 !text-xs flex-1"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') save()
                if (e.key === 'Escape') setEditing(false)
              }}
            />
            <button onClick={save} className="p-1.5 text-green-400 hover:bg-green-900/20 rounded-lg">
              <Save size={13} />
            </button>
            <button onClick={() => setEditing(false)} className="p-1.5 text-slate-500 hover:bg-slate-700 rounded-lg">
              <X size={13} />
            </button>
          </div>
        ) : (
          <span className="field-value break-all">{displayValue}</span>
        )}
      </div>
      {!editing && (
        <button
          onClick={startEdit}
          className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-500 
                     hover:text-slate-300 hover:bg-slate-700 rounded-lg transition-all"
        >
          <Edit3 size={13} />
        </button>
      )}
    </div>
  )
}

// ── Table Preview ─────────────────────────────────────────────────────────

function TablePreview({ tables }) {
  const [activeTable, setActiveTable] = useState(0)
  if (!tables?.length) return null

  const table = tables[activeTable]
  return (
    <div className="space-y-3">
      {tables.length > 1 && (
        <div className="flex gap-2">
          {tables.map((t, i) => (
            <button
              key={i}
              onClick={() => setActiveTable(i)}
              className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                activeTable === i
                  ? 'bg-ink-600 text-white'
                  : 'bg-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              {t.name || `Table ${i + 1}`}
            </button>
          ))}
        </div>
      )}
      <div className="overflow-auto rounded-xl border border-slate-700">
        <table className="w-full text-xs">
          <thead className="bg-slate-800">
            <tr>
              {(table.headers || []).map((h, i) => (
                <th key={i} className="px-3 py-2 text-left text-slate-300 font-medium whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {(table.rows || []).map((row, ri) => (
              <tr key={ri} className="hover:bg-slate-800/40">
                {(Array.isArray(row) ? row : Object.values(row)).map((cell, ci) => (
                  <td key={ci} className="px-3 py-2 text-slate-300 whitespace-nowrap">
                    {String(cell ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500">
        {table.rows?.length || 0} rows · {table.headers?.length || 0} columns
      </p>
    </div>
  )
}

// ── Main Review Page ──────────────────────────────────────────────────────

export default function DocumentReviewPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [doc, setDoc] = useState(null)
  const [loading, setLoading] = useState(true)
  const [previewImage, setPreviewImage] = useState(null)
  const [activeTab, setActiveTab] = useState('fields') // fields | tables | summary
  const [processing, setProcessing] = useState(false)
  const [savingStatus, setSavingStatus] = useState(false)

  const fetchDoc = async () => {
    try {
      const res = await getDocument(id)
      setDoc(res.data)
      try {
        const previewRes = await getPreview(id)
        const mediaType = previewRes.data.media_type || 'image/jpeg'
        setPreviewImage(`data:${mediaType};base64,${previewRes.data.image_base64}`)
      } catch {
        setPreviewImage(null)
      }
    } catch {
      toast.error('Failed to load document')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchDoc() }, [id])

  const handleSaveField = async (fieldName, value) => {
    try {
      await updateFields(id, { [fieldName]: value })
      setDoc((prev) => ({
        ...prev,
        extraction_result: {
          ...prev.extraction_result,
          corrected_fields: {
            ...(prev.extraction_result?.corrected_fields || {}),
            [fieldName]: value,
          },
        },
      }))
    } catch {
      toast.error('Failed to save field')
    }
  }

  const handleApprove = async () => {
    setSavingStatus(true)
    try {
      await updateStatus(id, 'approved')
      setDoc((prev) => ({ ...prev, status: 'approved' }))
      toast.success('Document approved!')
    } catch { } finally {
      setSavingStatus(false)
    }
  }

const handleRequestReview = async () => {
  try {
    await updateStatus(id, "under_review")
    toast.success("Document sent for review")
  } catch (err) {
    toast.error(
      err?.response?.data?.detail ||
      "Failed to request review. Please try again."
    )
  }
}



  const handleReprocess = async () => {
    setProcessing(true)
    try {
      await extractDocument(id, null, true)
      toast.success('Reprocessed successfully')
      fetchDoc()
    } catch { } finally {
      setProcessing(false)
    }
  }

  const handleExport = async (format) => {
    await exportDocuments([id], format)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500">
        <Loader2 size={28} className="animate-spin mr-3" />
        Loading document...
      </div>
    )
  }

  if (!doc) {
    return (
      <div className="text-center py-16 text-slate-500">
        <p>Document not found</p>
        <button onClick={() => navigate('/documents')} className="btn-secondary mt-4">
          Back to Library
        </button>
      </div>
    )
  }

  const statusInfo = getStatusBadge(doc.status)
  const typeInfo = getDocType(doc.document_type)
  const result = doc.extraction_result
  const fields = { ...(result?.fields || {}), ...(result?.corrected_fields || {}) }
  const confidence = result?.confidence_scores || {}
  const tables = result?.tables || []
  const isInProgress = isProcessing(doc.status)

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/documents')}
            className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-xl transition-colors"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg">{typeInfo.icon}</span>
              <h1 className="font-display font-bold text-slate-100 truncate max-w-xs" title={doc.original_filename}>
                {doc.original_filename}
              </h1>
              <span className={`badge ${statusInfo.class}`}>
                <span className={`status-dot ${statusInfo.dot}`} />
                {statusInfo.label}
              </span>
            </div>
            <p className={`text-xs mt-0.5 ${typeInfo.color}`}>
              {typeInfo.label}
              {result?.overall_confidence && (
                <span className="text-slate-500 ml-2">
                  Confidence: {Math.round(result.overall_confidence * 100)}%
                </span>
              )}
              {doc.processed_at && (
                <span className="text-slate-600 ml-2">· {formatDateTime(doc.processed_at)}</span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Reprocess */}
          <button
            onClick={handleReprocess}
            disabled={processing || isInProgress}
            className="btn-secondary"
          >
            {processing
              ? <><Loader2 size={14} className="animate-spin" /> Processing...</>
              : <><RefreshCw size={14} /> Re-extract</>
            }
          </button>

          {/* Status actions */}
          {doc.status !== 'approved' && result && (
            <button onClick={handleApprove} disabled={savingStatus} className="btn-primary">
              <CheckCircle size={14} />
              Approve
            </button>
          )}
          {doc.status === 'extracted' && (
            <button onClick={handleRequestReview} className="btn-secondary">
              Flag for Review
            </button>
          )}

          {/* Export */}
          {result && (
            <div className="relative group">
              <button className="btn-secondary">
                <Download size={14} /> Export
              </button>
              <div className="absolute right-0 top-full mt-1 bg-slate-800 border border-slate-700 
                              rounded-xl shadow-xl z-20 hidden group-hover:block min-w-[120px]">
                {['json', 'csv', 'xlsx'].map((fmt) => (
                  <button
                    key={fmt}
                    onClick={() => handleExport(fmt)}
                    className="w-full px-3 py-2 text-left text-sm text-slate-200 
                               hover:bg-slate-700 first:rounded-t-xl last:rounded-b-xl"
                  >
                    .{fmt.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Processing indicator */}
      {isInProgress && (
        <div className="card p-4 flex items-center gap-3 border-ink-800/50 bg-ink-900/20">
          <Loader2 size={18} className="animate-spin text-ink-400" />
          <div>
            <p className="text-sm font-medium text-ink-300">Processing document...</p>
            <p className="text-xs text-slate-500 capitalize">{doc.status.replace('_', ' ')}</p>
          </div>
        </div>
      )}

      {/* Error message */}
      {doc.status === 'failed' && doc.error_message && (
        <div className="card p-4 border-red-800/50 bg-red-900/10">
          <p className="text-sm text-red-400 font-medium">Extraction failed</p>
          <p className="text-xs text-slate-400 mt-1">{doc.error_message}</p>
        </div>
      )}

      {/* Main split layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1">
        {/* Left: Document Image Viewer */}
        <div className="card overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
            <span className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <Eye size={14} /> Document Preview
            </span>
            <span className="text-xs text-slate-500">Scroll/pinch to zoom</span>
          </div>
          <div className="flex-1 bg-slate-950 relative overflow-hidden" style={{ minHeight: 400 }}>
            {previewImage ? (
              <TransformWrapper
                initialScale={1}
                minScale={0.3}
                maxScale={5}
                centerOnInit
              >
                {({ zoomIn, zoomOut, resetTransform }) => (
                  <>
                    {/* Zoom controls */}
                    <div className="absolute top-3 right-3 z-10 flex flex-col gap-1">
                      <button
                        onClick={() => zoomIn()}
                        className="p-2 bg-slate-800/90 hover:bg-slate-700 text-slate-300 rounded-lg backdrop-blur-sm"
                      >
                        <ZoomIn size={14} />
                      </button>
                      <button
                        onClick={() => zoomOut()}
                        className="p-2 bg-slate-800/90 hover:bg-slate-700 text-slate-300 rounded-lg backdrop-blur-sm"
                      >
                        <ZoomOut size={14} />
                      </button>
                      <button
                        onClick={() => resetTransform()}
                        className="p-2 bg-slate-800/90 hover:bg-slate-700 text-slate-300 rounded-lg backdrop-blur-sm"
                      >
                        <RotateCcw size={14} />
                      </button>
                    </div>
                    <TransformComponent
                      wrapperStyle={{ width: '100%', height: '100%' }}
                      contentStyle={{ width: '100%', display: 'flex', justifyContent: 'center' }}
                    >
                      <img
                        src={previewImage}
                        alt="Document preview"
                        className="max-w-full h-auto"
                        style={{ maxHeight: 700 }}
                        onError={(e) => { e.target.src = '/placeholder-doc.png' }}
                      />
                    </TransformComponent>
                  </>
                )}
              </TransformWrapper>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-600">
                <FileText size={48} className="opacity-40" />
              </div>
            )}
          </div>
          {/* PDF pages nav */}
          {doc.page_count > 1 && (
            <div className="px-4 py-2 border-t border-slate-800 flex items-center gap-2 overflow-x-auto">
              <span className="text-xs text-slate-500 flex-shrink-0">{doc.page_count} pages</span>
              {(doc.pages || []).map((page) => (
                <button
                  key={page.id}
                  className="text-xs px-2.5 py-1 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-300 flex-shrink-0"
                >
                  {page.page_number}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Extracted Data */}
        <div className="card flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-slate-800">
            {[
              { id: 'fields', label: 'Fields', icon: <Edit3 size={14} />, count: Object.keys(fields).length },
              { id: 'tables', label: 'Tables', icon: <Table2 size={14} />, count: tables.length },
              { id: 'summary', label: 'Summary', icon: <FileText size={14} /> },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-ink-500 text-ink-300'
                    : 'border-transparent text-slate-500 hover:text-slate-300'
                }`}
              >
                {tab.icon}
                {tab.label}
                {tab.count != null && tab.count > 0 && (
                  <span className="badge badge-gray !px-1.5 !py-0 text-xs">{tab.count}</span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-auto p-4">
            {/* Fields tab */}
            {activeTab === 'fields' && (
              <>
                {!result && (
                  <div className="text-center py-12 text-slate-500">
                    <Edit3 size={36} className="mx-auto mb-3 opacity-30" />
                    <p className="text-sm">No extraction results yet</p>
                    {['uploaded', 'failed'].includes(doc.status) && (
                      <button onClick={handleReprocess} className="btn-primary mt-4">
                        Extract Now
                      </button>
                    )}
                  </div>
                )}
                {result && Object.keys(fields).length === 0 && (
                  <p className="text-slate-500 text-sm text-center py-8">No fields extracted</p>
                )}
                {result && Object.entries(fields).map(([key, val]) => {
                  if (Array.isArray(val) && val.length > 0 && typeof val[0] === 'object') {
                    // Line items / nested arrays → render as mini table
                    return (
                      <div key={key} className="py-2.5 border-b border-slate-800/60">
                        <p className="field-label mb-2">{formatFieldName(key)}</p>
                        <div className="overflow-auto rounded-lg border border-slate-700">
                          <table className="w-full text-xs">
                            <thead className="bg-slate-800">
                              <tr>
                                {Object.keys(val[0]).map((h) => (
                                  <th key={h} className="px-2 py-1.5 text-left text-slate-400 font-medium">
                                    {formatFieldName(h)}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                              {val.map((row, ri) => (
                                <tr key={ri}>
                                  {Object.values(row).map((cell, ci) => (
                                    <td key={ci} className="px-2 py-1.5 text-slate-300">
                                      {String(cell ?? '')}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )
                  }
                  return (
                    <FieldRow
                      key={key}
                      name={key}
                      value={val}
                      confidence={confidence[key]}
                      onSave={handleSaveField}
                    />
                  )
                })}

                {/* OCR engine info */}
                {result?.ocr_engine && (
                  <div className="mt-4 pt-3 border-t border-slate-800 flex items-center gap-2 text-xs text-slate-600">
                    <span>OCR engine: <span className="text-slate-400 font-mono">{result.ocr_engine}</span></span>
                    {doc.language_detected && (
                      <span>· Language: <span className="text-slate-400">{doc.language_detected}</span></span>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Tables tab */}
            {activeTab === 'tables' && (
              <>
                {tables.length === 0 ? (
                  <div className="text-center py-12 text-slate-500">
                    <Table2 size={36} className="mx-auto mb-3 opacity-30" />
                    <p className="text-sm">No tables detected</p>
                  </div>
                ) : (
                  <TablePreview tables={tables} />
                )}
              </>
            )}

            {/* Summary tab */}
            {activeTab === 'summary' && (
              <div>
                {result?.summary ? (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                        {result.summary}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-500">
                    <FileText size={36} className="mx-auto mb-3 opacity-30" />
                    <p className="text-sm">No summary available</p>
                    <p className="text-xs mt-1 text-slate-600">
                      Summaries are generated for contracts, reports, and multi-page PDFs
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
