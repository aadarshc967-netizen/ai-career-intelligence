import { useState } from 'react'
import { Link } from 'react-router-dom'

function ResumeUpload() {
  const [file, setFile] = useState<File | null>(null)
  const [message, setMessage] = useState('')
  const [uploading, setUploading] = useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]

    if (selectedFile) {
      setFile(selectedFile)
      setMessage('')
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setMessage('Please select a resume first.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    try {
      setUploading(true)
      setMessage('Uploading resume...')

      const response = await fetch('http://127.0.0.1:8000/upload-resume', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed')
      }

      setMessage(`✅ ${data.message}: ${data.filename}`)
    } catch (error) {
      setMessage(
        `❌ ${error instanceof Error ? error.message : 'Upload failed'}`
      )
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 px-6 py-12 text-white">
      <div className="mx-auto max-w-4xl">

        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
        >
          ← Back to Home
        </Link>

        <h1 className="mt-8 text-4xl font-bold">
          Analyze Your Resume
        </h1>

        <p className="mt-3 text-slate-400">
          Upload your resume and let CareerIQ identify your
          skills, experience and potential career gaps.
        </p>

        <div className="mt-10 rounded-2xl border border-dashed border-slate-700 bg-slate-900 p-12 text-center">

          <div className="text-5xl">📄</div>

          <h2 className="mt-5 text-xl font-semibold">
            Upload your resume
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            PDF or DOCX • Maximum 5MB
          </p>

          <label className="mt-6 inline-block cursor-pointer rounded-xl bg-blue-600 px-6 py-3 font-semibold transition hover:bg-blue-500">
            Choose Resume

            <input
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={handleFileChange}
            />
          </label>

          {file && (
            <div className="mt-5 text-sm text-slate-300">
              Selected: <span className="font-semibold">{file.name}</span>
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="mt-5 rounded-xl bg-emerald-600 px-6 py-3 font-semibold transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Upload Resume'}
          </button>

          {message && (
            <p className="mt-5 text-sm text-slate-300">
              {message}
            </p>
          )}

        </div>
      </div>
    </div>
  )
}

export default ResumeUpload