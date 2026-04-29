/**
 * Stats Dashboard - Processing statistics, charts, and platform health.
 */

import { useState, useEffect } from 'react'
import {
  BarChart, Bar, PieChart, Pie, Cell, Tooltip,
  ResponsiveContainer, XAxis, YAxis, CartesianGrid, Legend
} from 'recharts'
import { RefreshCw, FileText, CheckCircle, AlertTriangle, Layers } from 'lucide-react'
import { getStats, getHealth } from '../services/api'
import { getDocType, getStatusBadge } from '../utils/helpers'

const COLORS = ['#4a5eff', '#22c55e', '#eab308', '#ef4444', '#a855f7', '#06b6d4', '#f97316', '#ec4899']

function StatCard({ label, value, icon, sub, color = 'text-slate-100' }) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-slate-400 text-sm">{label}</span>
        <div className="p-2 bg-slate-800 rounded-xl text-slate-400">{icon}</div>
      </div>
      <p className={`text-3xl font-display font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  )
}

export default function StatsPage() {
  const [stats, setStats] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [sRes, hRes] = await Promise.all([getStats(), getHealth()])
      setStats(sRes.data)
      setHealth(hRes.data)
    } catch { } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAll() }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500">
        <RefreshCw size={24} className="animate-spin mr-2" />
        Loading stats...
      </div>
    )
  }

  const byTypeData = Object.entries(stats?.by_type || {})
    .map(([key, count]) => {
      const t = getDocType(key)
      return { name: t.label, count, icon: t.icon }
    })
    .sort((a, b) => b.count - a.count)

  const byStatusData = Object.entries(stats?.by_status || {})
    .map(([key, count]) => {
      const s = getStatusBadge(key)
      return { name: s.label, count }
    })

  const successRate = stats?.total_documents
    ? Math.round(
        (((stats.by_status?.extracted || 0) + (stats.by_status?.approved || 0)) /
          stats.total_documents) * 100
      )
    : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-100">Analytics Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">Platform processing statistics and health</p>
        </div>
        <button onClick={fetchAll} className="btn-secondary">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Documents"
          value={stats?.total_documents ?? 0}
          icon={<FileText size={18} />}
          sub={`${stats?.processing_today ?? 0} today`}
        />
        <StatCard
          label="Success Rate"
          value={`${successRate}%`}
          icon={<CheckCircle size={18} />}
          color={successRate >= 80 ? 'text-green-400' : successRate >= 50 ? 'text-yellow-400' : 'text-red-400'}
          sub="extracted + approved"
        />
        <StatCard
          label="Avg Confidence"
          value={
            stats?.average_confidence
              ? `${Math.round(stats.average_confidence * 100)}%`
              : '—'
          }
          icon={<AlertTriangle size={18} />}
          color="text-ink-300"
          sub="across all extractions"
        />
        <StatCard
          label="Total Batches"
          value={stats?.total_batches ?? 0}
          icon={<Layers size={18} />}
          sub="batch jobs created"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Type Bar Chart */}
        <div className="card p-5">
          <h3 className="font-medium text-slate-200 mb-4">Documents by Type</h3>
          {byTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={byTypeData} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: '#0f172a',
                    border: '1px solid #1e293b',
                    borderRadius: 12,
                    color: '#e2e8f0',
                  }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {byTypeData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-600 text-sm">
              No data yet
            </div>
          )}
        </div>

        {/* By Status Pie Chart */}
        <div className="card p-5">
          <h3 className="font-medium text-slate-200 mb-4">Processing Status</h3>
          {byStatusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={byStatusData}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  innerRadius={50}
                  paddingAngle={3}
                >
                  {byStatusData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: '#0f172a',
                    border: '1px solid #1e293b',
                    borderRadius: 12,
                    color: '#e2e8f0',
                  }}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: 12, color: '#94a3b8' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-600 text-sm">
              No data yet
            </div>
          )}
        </div>
      </div>

      {/* Health status */}
      {health && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium text-slate-200">System Health</h3>
            <span
              className={`badge ${health.status === 'ok' ? 'badge-success' : 'badge-warning'}`}
            >
              <span className={`status-dot ${health.status === 'ok' ? 'bg-green-500' : 'bg-yellow-500'}`} />
              {health.status === 'ok' ? 'All systems operational' : 'Degraded'}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.entries(health.services || {}).map(([svc, status]) => (
              <div key={svc} className="bg-slate-800/50 rounded-xl p-3 border border-slate-700/50">
                <p className="text-xs text-slate-500 mb-1 capitalize">{svc}</p>
                <div className="flex items-center gap-1.5">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      status === 'ok' || status === 'configured' || status === 'available'
                        ? 'bg-green-500'
                        : status === 'error'
                          ? 'bg-red-500'
                          : 'bg-yellow-500'
                    }`}
                  />
                  <span className="text-xs text-slate-300 capitalize">{status}</span>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-600 mt-3">Version {health.version}</p>
        </div>
      )}
    </div>
  )
}