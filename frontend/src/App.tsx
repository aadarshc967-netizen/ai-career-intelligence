import { Routes, Route } from 'react-router-dom'
import ResumeUpload from './pages/ResumeUpload'

function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <nav className="border-b border-slate-800 px-8 py-5">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <h1 className="text-xl font-bold">🧠 CareerIQ</h1>

          <div className="flex gap-6 text-sm text-slate-300">
            <a href="/">Home</a>
            <a href="/resume">Resume</a>
            <a href="/dashboard">Dashboard</a>
          </div>

          <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium">
            Profile
          </button>
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-8 py-16">
        <p className="mb-4 text-sm font-medium text-blue-400">
          AI CAREER INTELLIGENCE
        </p>

        <h2 className="text-5xl font-bold leading-tight">
          Build the career
          <br />
          you're aiming for.
        </h2>

        <p className="mt-6 max-w-2xl text-lg text-slate-400">
          Analyze your resume, discover skill gaps and get a
          personalized career roadmap powered by AI.
        </p>

        <a
          href="/resume"
          className="mt-8 inline-block rounded-xl bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-500"
        >
          Analyze My Resume
        </a>
      </main>
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/resume" element={<ResumeUpload />} />

      <Route
        path="/dashboard"
        element={
          <div className="min-h-screen bg-slate-950 p-10 text-white">
            Dashboard coming soon...
          </div>
        }
      />
    </Routes>
  )
}

export default App