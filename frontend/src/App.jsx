import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { Zap, Upload, Library, BarChart2, BookOpen, Cpu, Home } from 'lucide-react'
import HomePage from './pages/HomePage'
import UploadPage from './pages/UploadPage'
import DocumentsPage from './pages/DocumentsPage'
import DocumentReviewPage from './pages/DocumentReviewPage'
import StatsPage from './pages/StatsPage'

function Logo() {
  return (
    <div style={{display:'flex',alignItems:'center',gap:10}}>
      <div style={{width:30,height:30,background:'linear-gradient(135deg,#5E6AD2 0%,#818cf8 100%)',borderRadius:8,display:'flex',alignItems:'center',justifyContent:'center',boxShadow:'0 0 0 1px rgba(94,106,210,0.4),0 4px 12px rgba(94,106,210,0.3)',flexShrink:0}}>
        <Zap size={15} color="#fff" strokeWidth={2.5} />
      </div>
      <div>
        <p style={{fontSize:13,fontWeight:600,color:'#EDEDEF',letterSpacing:'-0.03em',lineHeight:1.2}}>DocuMind</p>
        <p style={{fontSize:10,color:'#8A8F98',letterSpacing:'0.05em',fontFamily:'JetBrains Mono,monospace'}}>AI EXTRACTION</p>
      </div>
    </div>
  )
}

function Sidebar() {
  const navItems = [
    { to:'/',          Icon:Home,     label:'Home'      },
    { to:'/upload',    Icon:Upload,   label:'Upload'    },
    { to:'/documents', Icon:Library,  label:'Library'   },
    { to:'/stats',     Icon:BarChart2,label:'Analytics' },
  ]
  return (
    <aside className="sidebar">
      <div style={{padding:'20px 16px 16px',borderBottom:'1px solid rgba(255,255,255,0.06)'}}>
        <Logo />
      </div>
      <nav style={{flex:1,padding:'8px',overflowY:'auto'}}>
        <p className="section-label" style={{padding:'14px 10px 6px'}}>Workspace</p>
        {navItems.map(({to,Icon,label})=>(
          <NavLink key={to} to={to} end={to === '/'} className={({isActive})=>`nav-item${isActive?' active':''}`}>
            <Icon size={15} strokeWidth={1.8}/>{label}
          </NavLink>
        ))}
       </nav>
      <div style={{padding:'12px 16px',borderTop:'1px solid rgba(255,255,255,0.06)'}}>
        <div style={{display:'flex',alignItems:'center',gap:8,padding:'7px 10px',background:'rgba(34,197,94,0.06)',border:'1px solid rgba(34,197,94,0.14)',borderRadius:8}}>
          <span style={{width:6,height:6,borderRadius:'50%',background:'#4ade80',boxShadow:'0 0 6px #4ade80',flexShrink:0}}/>
          <span style={{fontSize:11,color:'#4ade80',fontWeight:500}}>Systems operational</span>
        </div>
        <p style={{marginTop:8,fontSize:10,color:'rgba(255,255,255,0.18)',fontFamily:'JetBrains Mono,monospace',letterSpacing:'0.04em'}}>v1.0.0 · Groq Vision</p>
      </div>
    </aside>
  )
}

function AmbientBackground() {
  return (
    <>
      <div className="noise-overlay"/>
      <div className="grid-overlay"/>
      <div className="blob blob-primary"/>
      <div className="blob blob-secondary"/>
      <div className="blob blob-tertiary"/>
      <div className="blob blob-bottom"/>
    </>
  )
}

function Layout({children}) {
  return (
    <div className="app-shell">
      <AmbientBackground/>
      <Sidebar/>
      <main className="main-content" style={{position:'relative',zIndex:1}}>
        <div className="page-wrapper">{children}</div>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <Router>
      <Toaster position="top-right" toastOptions={{style:{background:'#0a0a0c',color:'#EDEDEF',border:'1px solid rgba(255,255,255,0.08)',borderRadius:10,fontSize:13,fontFamily:'Inter,sans-serif',letterSpacing:'-0.01em',boxShadow:'0 8px 32px rgba(0,0,0,0.5)'},success:{iconTheme:{primary:'#4ade80',secondary:'#0a0a0c'}},error:{iconTheme:{primary:'#f87171',secondary:'#0a0a0c'}}}}/>
      <Layout>
        <Routes>
          <Route path="/"              element={<HomePage/>}/>
          <Route path="/upload"        element={<UploadPage/>}/>
          <Route path="/documents"     element={<DocumentsPage/>}/>
          <Route path="/documents/:id" element={<DocumentReviewPage/>}/>
          <Route path="/stats"         element={<StatsPage/>}/>
          <Route path="*"             element={<UploadPage/>}/>
        </Routes>
      </Layout>
    </Router>
  )
}
