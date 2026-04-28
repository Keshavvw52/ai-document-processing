import { Link } from 'react-router-dom'
import {
  ArrowRight, BarChart2, CheckCircle, FileSearch, Library,
  ScanLine, ShieldCheck, Sparkles, Upload
} from 'lucide-react'

function SpotlightCard({ children, className = '' }) {
  const handleMouseMove = (event) => {
    const rect = event.currentTarget.getBoundingClientRect()
    event.currentTarget.style.setProperty('--spotlight-x', `${event.clientX - rect.left}px`)
    event.currentTarget.style.setProperty('--spotlight-y', `${event.clientY - rect.top}px`)
  }

  return (
    <div className={`spotlight-card ${className}`} onMouseMove={handleMouseMove}>
      {children}
    </div>
  )
}

const workflow = [
  { icon: <Upload size={18} />, label: 'Upload', text: 'Drop PDFs and images into a guided extraction queue.' },
  { icon: <ScanLine size={18} />, label: 'Extract', text: 'Classify documents and pull structured fields with AI.' },
  { icon: <CheckCircle size={18} />, label: 'Review', text: 'Validate, edit, approve, and export clean results.' },
]

const metrics = [
  ['Document types', 'Invoices, receipts, contracts, IDs'],
  ['Review flow', 'Fields, tables, previews, approvals'],
  ['Exports', 'JSON, CSV, XLSX, ZIP'],
]

export default function HomePage() {
  return (
    <div className="home-page">
      <section className="hero-section animate-fade-up">
        <div className="hero-copy">
          <div className="hero-pill">
            <Sparkles size={14} />
            AI document processing workspace
          </div>
          <h1 className="hero-title">
            Turn messy documents into <span>structured intelligence.</span>
          </h1>
          <p className="hero-subtitle">
            Upload invoices, receipts, contracts, identity documents, and reports. DocuMind classifies each file,
            extracts the important fields, and gives your team a fast review workflow.
          </p>
          <div className="hero-actions">
            <Link to="/upload" className="btn-primary hero-cta">
              Start extracting <ArrowRight size={16} />
            </Link>
            <Link to="/documents" className="btn-secondary hero-cta">
              Open library <Library size={16} />
            </Link>
          </div>
        </div>

        <SpotlightCard className="hero-console">
          <div className="console-top">
            <div>
              <p className="section-label">LIVE PIPELINE</p>
              <h2>Extraction run</h2>
            </div>
            <span className="badge badge-success">
              <span className="status-dot bg-green-400" />
              Ready
            </span>
          </div>

          <div className="console-list">
            {workflow.map((item, index) => (
              <div className="console-row" key={item.label}>
                <div className="console-icon">{item.icon}</div>
                <div>
                  <p>{item.label}</p>
                  <span>{item.text}</span>
                </div>
                <strong>{String(index + 1).padStart(2, '0')}</strong>
              </div>
            ))}
          </div>
        </SpotlightCard>
      </section>

      <section className="home-grid animate-fade-up-1">
        <SpotlightCard className="home-card home-card-large">
          <div className="home-card-icon">
            <FileSearch size={20} />
          </div>
          <p className="section-label">REVIEW FIRST</p>
          <h3>Inspect every extracted field beside the original document preview.</h3>
          <p>
            The review screen keeps confidence, editable values, summaries, and detected tables close to the source
            file so corrections stay simple.
          </p>
        </SpotlightCard>

        <SpotlightCard className="home-card">
          <div className="home-card-icon">
            <ShieldCheck size={20} />
          </div>
          <p className="section-label">CONTROL</p>
          <h3>Approve what matters.</h3>
          <p>Move extracted documents through review and approval without changing the current workflow.</p>
        </SpotlightCard>

        <SpotlightCard className="home-card">
          <div className="home-card-icon">
            <BarChart2 size={20} />
          </div>
          <p className="section-label">ANALYTICS</p>
          <h3>Track processing health.</h3>
          <p>Monitor document volume, confidence, success rate, and service status from one dashboard.</p>
        </SpotlightCard>
      </section>

      <section className="metric-strip animate-fade-up-2">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </section>
    </div>
  )
}
