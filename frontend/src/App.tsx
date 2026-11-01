import { Link, Navigate, Route, Routes } from 'react-router-dom'
import ResumeUpload from './pages/ResumeUpload'

function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <nav className="border-b border-slate-800 px-5 py-5 md:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link to="/" className="text-xl font-bold">CareerIQ</Link>
          <div className="flex gap-5 text-sm text-slate-300">
            <Link to="/" className="hover:text-white">Home</Link>
            <Link to="/resume" className="hover:text-white">Resume analysis</Link>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-24">
        <p className="mb-4 text-sm font-semibold tracking-widest text-blue-400">AI CAREER INTELLIGENCE</p>
        <h1 className="max-w-3xl text-4xl font-bold leading-tight md:text-6xl">
          Build the career you&apos;re aiming for.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-slate-400">
          Analyze your resume, find skill gaps, compare a target job description, and build a personalized career roadmap.
        </p>
        <Link
          to="/resume"
          className="mt-8 inline-block rounded-xl bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-500"
        >
          Analyze my resume
        </Link>
      </main>
    </div>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white px-5 py-4">
        <nav className="mx-auto flex max-w-5xl items-center justify-between">
          <Link to="/" className="font-bold text-slate-900">CareerIQ</Link>
          <div className="flex gap-5 text-sm font-medium text-slate-600">
            <Link to="/" className="hover:text-blue-700">Home</Link>
            <Link to="/resume" className="hover:text-blue-700">Resume analysis</Link>
          </div>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/resume" element={<ResumeUpload />} />
        <Route path="/dashboard" element={<Navigate to="/resume" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App
