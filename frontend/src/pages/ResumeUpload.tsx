import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, apiRequest } from '../lib/api'

const MAX_FILE_SIZE = 5 * 1024 * 1024

type KeywordDiagnostic = {
  term: string
  mentions: number
  density_percent: number
  benchmark_percent: string
  status: 'missing' | 'low' | 'high' | 'within_benchmark'
}

type AnalysisResult = {
  filename: string
  extracted_skills: string[]
  target_role: string
  match_score: number
  resume_score: number
  ats_analysis: {
    score: number
    word_count: number
    issues: string[]
    keyword_heatmap: KeywordDiagnostic[]
    benchmark_note: string
  }
  skill_gaps: string[]
  future_action_plan: string[]
  tailored_bullets: string[]
}

type HistoryItem = {
  id: number
  filename: string
  target_role: string
  match_score: number
  resume_score: number
  ats_score: number
  skill_gaps: string[]
  action_roadmap: string[]
  keyword_heatmap: KeywordDiagnostic[]
  ats_issues: string[]
  tailored_bullets: string[]
  created_at: string | null
}

type AuthResponse = {
  access_token: string
  name: string
  email: string
}

function keywordStatus(status: KeywordDiagnostic['status']): string {
  switch (status) {
    case 'missing':
      return 'Missing'
    case 'low':
      return 'Low'
    case 'high':
      return 'High'
    case 'within_benchmark':
      return 'On target'
  }
}

export default function ResumeUpload() {
  const [token, setToken] = useState(() => localStorage.getItem('accessToken') ?? '')
  const [userName, setUserName] = useState(() => localStorage.getItem('userName') ?? '')
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem('userEmail') ?? '')
  const [registering, setRegistering] = useState(false)
  const [nameInput, setNameInput] = useState('')
  const [emailInput, setEmailInput] = useState(userEmail)
  const [password, setPassword] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [targetRole, setTargetRole] = useState('Python Backend Developer')
  const [jobDescription, setJobDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [authLoading, setAuthLoading] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const authInFlight = useRef(false)
  const analysisInFlight = useRef(false)

  const logout = useCallback((message?: string) => {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('userName')
    localStorage.removeItem('userEmail')
    setToken('')
    setUserName('')
    setUserEmail('')
    setHistory([])
    setResult(null)
    setError(message ?? null)
  }, [])

  const handleProtectedRequestError = useCallback((requestError: unknown, requestToken: string) => {
    if (!(requestError instanceof ApiError) || requestError.status !== 401) return false
    if (localStorage.getItem('accessToken') === requestToken) {
      logout('Your session has expired or is no longer valid. Please sign in again.')
    }
    return true
  }, [logout])

  useEffect(() => {
    const synchronizeSession = (event: StorageEvent) => {
      if (event.key !== null && !['accessToken', 'userName', 'userEmail'].includes(event.key)) return
      const latestToken = localStorage.getItem('accessToken') ?? ''
      if (!latestToken) {
        logout()
        return
      }
      setToken(latestToken)
      setUserName(localStorage.getItem('userName') ?? '')
      setUserEmail(localStorage.getItem('userEmail') ?? '')
    }
    window.addEventListener('storage', synchronizeSession)
    return () => window.removeEventListener('storage', synchronizeSession)
  }, [logout])

  useEffect(() => {
    if (!token || !userEmail) return
    let active = true
    const fetchHistory = async () => {
      setHistoryLoading(true)
      try {
        const data = await apiRequest<HistoryItem[]>(
          `/user-history/${encodeURIComponent(userEmail)}`,
          { token },
        )
        if (!Array.isArray(data)) throw new Error('The history response was invalid.')
        if (active) setHistory(data)
      } catch (requestError) {
        if (active && !handleProtectedRequestError(requestError, token)) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load analysis history.')
        }
      } finally {
        if (active) setHistoryLoading(false)
      }
    }
    void fetchHistory()
    return () => {
      active = false
    }
  }, [handleProtectedRequestError, token, userEmail])

  const handleAuthentication = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (authInFlight.current) return
    authInFlight.current = true
    setError(null)
    setAuthLoading(true)
    try {
      const data = await apiRequest<AuthResponse>(`/${registering ? 'register' : 'login'}`, {
        method: 'POST',
        json: {
          ...(registering ? { name: nameInput } : {}),
          email: emailInput,
          password,
        },
      })
      localStorage.setItem('accessToken', data.access_token)
      localStorage.setItem('userName', data.name)
      localStorage.setItem('userEmail', data.email)
      setToken(data.access_token)
      setUserName(data.name)
      setUserEmail(data.email)
      setPassword('')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to authenticate.')
    } finally {
      authInFlight.current = false
      setAuthLoading(false)
    }
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0]
    setError(null)
    if (!selected) {
      setFile(null)
      return
    }
    if (!/\.(pdf|docx)$/i.test(selected.name)) {
      setFile(null)
      setError('Choose a PDF or DOCX resume.')
      event.target.value = ''
      return
    }
    if (selected.size > MAX_FILE_SIZE) {
      setFile(null)
      setError('The resume must be smaller than 5 MiB.')
      event.target.value = ''
      return
    }
    setFile(selected)
  }

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (analysisInFlight.current) return
    if (!file) {
      setError('Please select a PDF or DOCX file first.')
      return
    }
    const formData = new FormData()
    formData.append('file', file)
    formData.append('target_role', targetRole)
    formData.append('job_description', jobDescription)

    analysisInFlight.current = true
    setLoading(true)
    setError(null)
    try {
      const data = await apiRequest<AnalysisResult>('/analyze-career', {
        method: 'POST',
        token,
        body: formData,
      })
      setResult(data)
      try {
        const updatedHistory = await apiRequest<HistoryItem[]>(
          `/user-history/${encodeURIComponent(userEmail)}`,
          { token },
        )
        if (!Array.isArray(updatedHistory)) throw new Error('The history response was invalid.')
        setHistory(updatedHistory)
      } catch (historyError) {
        if (!handleProtectedRequestError(historyError, token)) {
          setError(
            `Analysis completed, but history could not be refreshed: ${
              historyError instanceof Error ? historyError.message : 'Please reload history.'
            }`,
          )
        }
      }
    } catch (requestError) {
      if (!handleProtectedRequestError(requestError, token)) {
        setError(requestError instanceof Error ? requestError.message : 'Unable to analyze this resume.')
      }
    } finally {
      analysisInFlight.current = false
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <main className="mx-auto mt-12 max-w-lg px-5 pb-12">
        <section className="rounded-2xl bg-white p-8 shadow-lg">
          <p className="text-sm font-bold uppercase tracking-widest text-blue-600">CareerIQ account</p>
          <h1 className="mt-2 text-3xl font-bold text-slate-900">
            {registering ? 'Create your account' : 'Welcome back'}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Sign in to securely analyze resumes and access your private history.
          </p>
          <form onSubmit={handleAuthentication} className="mt-6 space-y-4">
            {registering && (
              <label className="block text-sm font-medium text-slate-700">
                Name
                <input
                  required
                  maxLength={120}
                  autoComplete="name"
                  value={nameInput}
                  onChange={(event) => setNameInput(event.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 p-3"
                />
              </label>
            )}
            <label className="block text-sm font-medium text-slate-700">
              Email
              <input
                required
                type="email"
                maxLength={254}
                autoComplete="email"
                value={emailInput}
                onChange={(event) => setEmailInput(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 p-3"
              />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Password
              <input
                required
                type="password"
                minLength={registering ? 8 : 1}
                maxLength={128}
                autoComplete={registering ? 'new-password' : 'current-password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 p-3"
              />
            </label>
            {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
            <button
              type="submit"
              disabled={authLoading}
              className="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
            >
              {authLoading ? 'Please wait…' : registering ? 'Create account' : 'Sign in'}
            </button>
          </form>
          <button
            type="button"
            onClick={() => {
              setRegistering(!registering)
              setError(null)
            }}
            className="mt-4 w-full text-sm font-medium text-blue-700 hover:underline"
          >
            {registering ? 'Already have an account? Sign in' : 'New here? Create an account'}
          </button>
        </section>
      </main>
    )
  }

  return (
    <main className="mx-auto mt-8 max-w-5xl space-y-6 px-5 pb-12">
      <section className="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-gradient-to-r from-blue-700 to-indigo-700 p-6 text-white shadow-lg">
        <div>
          <p className="text-sm font-medium text-blue-100">Your career intelligence workspace</p>
          <h1 className="mt-1 text-2xl font-bold">Welcome, {userName}</h1>
          <p className="mt-1 text-sm text-blue-100">{userEmail}</p>
        </div>
        <button onClick={() => logout()} className="rounded-lg border border-white/50 px-4 py-2 text-sm hover:bg-white/10">
          Sign out
        </button>
      </section>

      {error && (
        <div role="alert" className="flex items-start justify-between gap-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-semibold underline">Dismiss</button>
        </div>
      )}

      <form onSubmit={handleUpload} className="space-y-5 rounded-2xl bg-white p-6 shadow-md md:p-8">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Analyze your resume</h2>
          <p className="mt-1 text-sm text-slate-600">Get role fit, ATS diagnostics, and keyword coverage.</p>
        </div>
        <label className="block text-sm font-semibold text-slate-700">
          Target role
          <select
            value={targetRole}
            onChange={(event) => setTargetRole(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-slate-50 p-3"
          >
            <option>Python Backend Developer</option>
            <option>Full-Stack Developer</option>
            <option>Junior Data Scientist / ML Engineer</option>
          </select>
        </label>
        <label className="block text-sm font-semibold text-slate-700">
          Target job description <span className="font-normal text-slate-500">(optional; enables AI bullet tailoring)</span>
          <textarea
            maxLength={20000}
            rows={5}
            value={jobDescription}
            onChange={(event) => setJobDescription(event.target.value)}
            placeholder="Paste the job description to score its keywords and tailor your resume bullets."
            className="mt-1 w-full rounded-lg border border-slate-300 p-3 font-normal"
          />
          <span className="mt-1 block text-right text-xs font-normal text-slate-500">{jobDescription.length}/20,000</span>
        </label>
        <label className="block rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-5 text-sm font-medium text-slate-700">
          Resume file (PDF or DOCX, up to 5 MiB)
          <input
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={handleFileChange}
            className="mt-3 block w-full text-sm"
          />
          {file && <span className="mt-2 block text-emerald-700">Selected: {file.name}</span>}
        </label>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:cursor-wait disabled:opacity-60"
        >
          {loading ? 'Analyzing…' : 'Analyze resume'}
        </button>
        {jobDescription.trim() && (
          <p className="text-xs text-slate-500">
            Resume text is sent to the configured LLM provider only for this requested tailoring.
          </p>
        )}
      </form>

      {result && (
        <section className="space-y-6 rounded-2xl bg-white p-6 shadow-md md:p-8">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Analysis report</h2>
              <p className="mt-1 text-sm text-slate-600">{result.filename} · {result.target_role}</p>
            </div>
            <button onClick={() => window.print()} className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white">
              Print report
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ['Role match', `${result.match_score}%`],
              ['Resume health', `${result.resume_score}/100`],
              ['ATS readiness', `${result.ats_analysis.score}/100`],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl bg-indigo-50 p-4 text-center">
                <p className="text-xs font-bold uppercase tracking-wide text-indigo-700">{label}</p>
                <p className="mt-1 text-3xl font-extrabold text-indigo-950">{value}</p>
              </div>
            ))}
          </div>

          <div>
            <h3 className="font-semibold text-slate-900">Keyword heatmap</h3>
            <p className="mb-3 text-xs text-slate-500">
              {result.ats_analysis.word_count} words · {result.ats_analysis.benchmark_note}
            </p>
            {result.ats_analysis.keyword_heatmap.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead><tr className="border-b text-xs uppercase text-slate-500"><th className="p-2">Keyword</th><th className="p-2">Mentions</th><th className="p-2">Density</th><th className="p-2">Status</th></tr></thead>
                  <tbody>
                    {result.ats_analysis.keyword_heatmap.map((item) => (
                      <tr key={item.term} className="border-b border-slate-100">
                        <td className="p-2 font-medium">{item.term}</td>
                        <td className="p-2">{item.mentions}</td>
                        <td className="p-2">{item.density_percent}%</td>
                        <td className={`p-2 font-semibold ${item.status === 'missing' || item.status === 'high' ? 'text-amber-700' : 'text-emerald-700'}`}>{keywordStatus(item.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className="text-sm text-slate-600">No reference keywords were available to compare.</p>}
          </div>

          <div>
            <h3 className="font-semibold text-slate-900">ATS structure checks</h3>
            {result.ats_analysis.issues.length ? (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-800">
                {result.ats_analysis.issues.map((issue) => <li key={issue}>{issue}</li>)}
              </ul>
            ) : <p className="mt-1 text-sm text-emerald-700">No structural issues detected.</p>}
          </div>

          <div>
            <h3 className="font-semibold text-slate-900">Extracted skills</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {result.extracted_skills.length
                ? result.extracted_skills.map((skill) => <span key={skill} className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800">{skill}</span>)
                : <span className="text-sm text-slate-600">No recognized skills detected.</span>}
            </div>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <div>
              <h3 className="font-semibold text-slate-900">Priority skill gaps</h3>
              {result.skill_gaps.length
                ? <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-800">{result.skill_gaps.map((gap) => <li key={gap}>{gap}</li>)}</ul>
                : <p className="mt-2 text-sm text-emerald-700">No keyword gaps were detected.</p>}
            </div>
            <div>
              <h3 className="font-semibold text-slate-900">Action roadmap</h3>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-700">
                {result.future_action_plan.map((step) => <li key={step}>{step}</li>)}
              </ol>
            </div>
          </div>

          {result.tailored_bullets.length > 0 && (
            <div className="rounded-xl border border-purple-200 bg-purple-50 p-5">
              <h3 className="font-semibold text-purple-950">JD-tailored bullet suggestions</h3>
              <p className="mt-1 text-xs text-purple-800">Verify every suggestion; AI must not replace your actual experience or invent results.</p>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-purple-950">
                {result.tailored_bullets.map((bullet, index) => <li key={`${index}-${bullet}`}>{bullet}</li>)}
              </ul>
            </div>
          )}
        </section>
      )}

      <section className="space-y-4 rounded-2xl bg-white p-6 shadow-md md:p-8">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-bold text-slate-900">Analysis history</h2>
          <span className="text-sm text-slate-500">{historyLoading ? 'Refreshing…' : `${history.length} saved`}</span>
        </div>
        {history.length === 0 ? (
          <p className="text-sm text-slate-600">No previous analyses found.</p>
        ) : (
          <ul className="space-y-3">
            {history.map((item) => (
              <li key={item.id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div>
                  <p className="font-semibold text-slate-900">{item.filename}</p>
                  <p className="text-xs text-slate-600">{item.target_role}{item.created_at ? ` · ${new Date(item.created_at).toLocaleString()}` : ''}</p>
                  {item.skill_gaps.length > 0 && <p className="mt-1 text-xs text-amber-800">Gaps: {item.skill_gaps.join(', ')}</p>}
                  <details className="mt-2 text-xs text-slate-700">
                    <summary className="cursor-pointer font-semibold text-blue-700">Saved roadmap and diagnostics</summary>
                    <ol className="mt-2 list-decimal space-y-1 pl-5">
                      {item.action_roadmap.map((step) => <li key={step}>{step}</li>)}
                    </ol>
                    {item.ats_issues.length > 0 && (
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-amber-800">
                        {item.ats_issues.map((issue) => <li key={issue}>{issue}</li>)}
                      </ul>
                    )}
                    {item.keyword_heatmap.length > 0 && (
                      <p className="mt-2">Keyword checks: {item.keyword_heatmap.map((keyword) => `${keyword.term} (${keyword.status})`).join(', ')}</p>
                    )}
                    {item.tailored_bullets.length > 0 && (
                      <ul className="mt-2 list-disc space-y-1 pl-5">
                        {item.tailored_bullets.map((bullet, bulletIndex) => <li key={`${bulletIndex}-${bullet}`}>{bullet}</li>)}
                      </ul>
                    )}
                  </details>
                </div>
                <div className="flex gap-4 text-right text-sm">
                  <span><span className="block text-xs text-slate-500">Match</span><strong>{item.match_score}%</strong></span>
                  <span><span className="block text-xs text-slate-500">Health</span><strong>{item.resume_score}/100</strong></span>
                  <span><span className="block text-xs text-slate-500">ATS</span><strong>{item.ats_score}/100</strong></span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}
