/**
 * Document Library - Grid/list view of all processed documents.
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Filter, RefreshCw, Trash2, Download, Eye, Grid, List } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  listDocuments, deleteDocument, extractDocument, exportDocuments
} from '../services/api'
import {
  getStatusBadge, getDocType, formatFileSize,
  formatDateTime, DOC_TYPES, STATUSES
} from '../utils/helpers'

function DocumentCard({ doc, onDelete, onProcess, onView, selected, onSelect }) {
  const statusInfo = getStatusBadge(doc.status)
  const typeInfo = getDocType(doc.document_type)

  return (
    <div
      className={`card p-4 hover:border-slate-700 transition-all duration-150 cursor-pointer group
        ${selected ? 'border-ink-600 ring-1 ring-ink-600' : ''}`}
      onClick={() => onView(doc)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={selected}
            onChange={(e) => { e.stopPropagation(); onSelect(doc.id) }}
            className="rounded border-slate-600 bg-slate-700 text-ink-600"
            onClick={(e) => e.stopPropagation()}
          />
          <span className="text-xl">{typeInfo.icon}</span>
        </div>
        <span className={`badge ${statusInfo.class}`}>
          <span className={`status-dot ${statusInfo.dot}`} />
          {statusInfo.label}
        </span>
      </div>

      {/* Filename */}
      <p className="text-sm font-medium text-slate-200 truncate mb-1" title={doc.original_filename}>
        {doc.original_filename}
      </p>
      <p className={`text-xs font-medium mb-3 ${typeInfo.color}`}>
        {typeInfo.label}
        {doc.classification_confidence && (
          <span className="text-slate-500 ml-1">
            ({Math.round(doc.classification_confidence * 100)}%)
          </span>
        )}
      </p>

      {/* Meta */}
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>{formatFileSize(doc.file_size)}</span>
        <span>{formatDateTime(doc.created_at)}</span>
      </div>

      {/* Actions (hover) */}
      <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-slate-800 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => { e.stopPropagation(); onView(doc) }}
          className="btn-secondary !px-2 !py-1 text-xs flex-1 justify-center"
        >
          <Eye size={12} /> View
        </button>
        {['uploaded', 'failed'].includes(doc.status) && (
          <button
            onClick={(e) => { e.stopPropagation(); onProcess(doc) }}
            className="btn-primary !px-2 !py-1 text-xs flex-1 justify-center"
          >
            Extract
          </button>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(doc) }}
          className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-900/20 rounded-lg transition-colors"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  )
}

export default function DocumentsPage() {
  const navigate = useNavigate()
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState('grid') // grid | list
  const [selected, setSelected] = useState(new Set())
  const [filters, setFilters] = useState({ status: '', document_type: '', search: '' })
  const [showFilters, setShowFilters] = useState(false)

  const fetchDocs = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (filters.status) params.status = filters.status
      if (filters.document_type) params.document_type = filters.document_type
      const res = await listDocuments(params)
      setDocs(res.data)
    } catch (err) {
      toast.error('Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [filters.status, filters.document_type])

  useEffect(() => { fetchDocs() }, [fetchDocs])

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const s = new Set(prev)
      s.has(id) ? s.delete(id) : s.add(id)
      return s
    })
  }

  const selectAll = () => {
    if (selected.size === filteredDocs.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(filteredDocs.map((d) => d.id)))
    }
  }

  const handleDelete = async (doc) => {
    if (!confirm(`Delete "${doc.original_filename}"?`)) return
    try {
      await deleteDocument(doc.id)
      toast.success('Document deleted')
      fetchDocs()
    } catch { }
  }

  const handleProcess = async (doc) => {
    try {
      await extractDocument(doc.id)
      toast.success('Extraction complete')
      fetchDocs()
    } catch { }
  }

  const handleBulkExport = async (format) => {
    if (!selected.size) { toast.error('Select documents first'); return }
    await exportDocuments([...selected], format)
  }

  const handleBulkDelete = async () => {
    if (!selected.size) return
    if (!confirm(`Delete ${selected.size} documents?`)) return
    for (const id of selected) {
      try { await deleteDocument(id) } catch { }
    }
    setSelected(new Set())
    fetchDocs()
    toast.success(`Deleted ${selected.size} documents`)
  }

  // Client-side text search
  const filteredDocs = docs.filter((d) => {
    if (!filters.search) return true
    const q = filters.search.toLowerCase()
    return (
      d.original_filename.toLowerCase().includes(q) ||
      (d.document_type || '').toLowerCase().includes(q)
    )
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-100">Document Library</h1>
          <p className="text-slate-400 text-sm mt-1">
            {docs.length} documents · {selected.size > 0 && `${selected.size} selected`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {selected.size > 0 && (
            <>
              <div className="relative group">
                <button className="btn-secondary">
                  <Download size={14} /> Export
                </button>
                <div className="absolute right-0 top-full mt-1 bg-slate-800 border border-slate-700 
                                rounded-xl shadow-xl z-10 hidden group-hover:block min-w-[120px]">
                  {['json', 'csv', 'xlsx', 'zip'].map((fmt) => (
                    <button
                      key={fmt}
                      onClick={() => handleBulkExport(fmt)}
                      className="w-full px-3 py-2 text-left text-sm text-slate-200 
                                 hover:bg-slate-700 first:rounded-t-xl last:rounded-b-xl"
                    >
                      .{fmt.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
              <button onClick={handleBulkDelete} className="btn-danger">
                <Trash2 size={14} /> Delete ({selected.size})
              </button>
            </>
          )}
          <button onClick={fetchDocs} className="btn-secondary">
            <RefreshCw size={14} />
          </button>
          <div className="flex border border-slate-700 rounded-xl overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 ${viewMode === 'grid' ? 'bg-slate-700 text-slate-100' : 'text-slate-400 hover:bg-slate-800'}`}
            >
              <Grid size={16} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 ${viewMode === 'list' ? 'bg-slate-700 text-slate-100' : 'text-slate-400 hover:bg-slate-800'}`}
            >
              <List size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex items-center gap-3">
        <div className="flex-1 relative">
          <Search size={16} className="absolute left-3 top-2.5 text-slate-500" />
          <input
            className="input pl-9"
            placeholder="Search by filename or type..."
            value={filters.search}
            onChange={(e) => setFilters((p) => ({ ...p, search: e.target.value }))}
          />
        </div>
        <select
          className="input !w-44"
          value={filters.status}
          onChange={(e) => setFilters((p) => ({ ...p, status: e.target.value }))}
        >
          <option value="">All Statuses</option>
          {Object.entries(STATUSES).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <select
          className="input !w-44"
          value={filters.document_type}
          onChange={(e) => setFilters((p) => ({ ...p, document_type: e.target.value }))}
        >
          <option value="">All Types</option>
          {DOC_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.icon} {t.label}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={selected.size === filteredDocs.length && filteredDocs.length > 0}
            onChange={selectAll}
            className="rounded border-slate-600 bg-slate-700 text-ink-600"
          />
          All
        </label>
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-12 text-slate-500">
          <RefreshCw size={32} className="animate-spin mx-auto mb-3 opacity-40" />
          <p>Loading documents...</p>
        </div>
      )}

      {/* Documents Grid */}
      {!loading && filteredDocs.length > 0 && viewMode === 'grid' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredDocs.map((doc) => (
            <DocumentCard
              key={doc.id}
              doc={doc}
              selected={selected.has(doc.id)}
              onSelect={toggleSelect}
              onView={(d) => navigate(`/documents/${d.id}`)}
              onDelete={handleDelete}
              onProcess={handleProcess}
            />
          ))}
        </div>
      )}

      {/* List view */}
      {!loading && filteredDocs.length > 0 && viewMode === 'list' && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-800">
              <tr className="text-left">
                <th className="px-4 py-3 text-slate-500 font-medium w-8">
                  <input type="checkbox" checked={selected.size === filteredDocs.length}
                    onChange={selectAll} className="rounded border-slate-600 bg-slate-700 text-ink-600" />
                </th>
                <th className="px-4 py-3 text-slate-500 font-medium">Filename</th>
                <th className="px-4 py-3 text-slate-500 font-medium">Type</th>
                <th className="px-4 py-3 text-slate-500 font-medium">Status</th>
                <th className="px-4 py-3 text-slate-500 font-medium">Confidence</th>
                <th className="px-4 py-3 text-slate-500 font-medium">Size</th>
                <th className="px-4 py-3 text-slate-500 font-medium">Date</th>
                <th className="px-4 py-3 text-slate-500 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {filteredDocs.map((doc) => {
                const s = getStatusBadge(doc.status)
                const t = getDocType(doc.document_type)
                return (
                  <tr key={doc.id} className="hover:bg-slate-800/30 transition-colors cursor-pointer"
                    onClick={() => navigate(`/documents/${doc.id}`)}>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" checked={selected.has(doc.id)}
                        onChange={() => toggleSelect(doc.id)}
                        className="rounded border-slate-600 bg-slate-700 text-ink-600" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span>{t.icon}</span>
                        <span className="text-slate-200 truncate max-w-[200px]" title={doc.original_filename}>
                          {doc.original_filename}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium ${t.color}`}>{t.label}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`badge ${s.class}`}>
                        <span className={`status-dot ${s.dot}`} />
                        {s.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {doc.classification_confidence
                        ? `${Math.round(doc.classification_confidence * 100)}%`
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-400">{formatFileSize(doc.file_size)}</td>
                    <td className="px-4 py-3 text-slate-400">{formatDateTime(doc.created_at)}</td>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-1">
                        <button onClick={() => navigate(`/documents/${doc.id}`)}
                          className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-700 rounded-lg">
                          <Eye size={14} />
                        </button>
                        <button onClick={() => handleDelete(doc)}
                          className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-900/20 rounded-lg">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty state */}
      {!loading && filteredDocs.length === 0 && (
        <div className="text-center py-16">
          <div className="text-5xl mb-4">📄</div>
          <p className="text-slate-400 font-medium">No documents found</p>
          <p className="text-slate-600 text-sm mt-1">Upload documents to get started</p>
          <button onClick={() => navigate('/upload')} className="btn-primary mt-4">
            Upload Documents
          </button>
        </div>
      )}
    </div>
  )
}