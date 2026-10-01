import React, { useState, useEffect } from 'react';

const API_BASE_URL = "https://ai-career-intelligence-7x5r.onrender.com";

export default function ResumeUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [targetRole, setTargetRole] = useState("Python Backend Developer");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);
  const [history, setHistory] = useState<any[]>([]);

  const userName = localStorage.getItem("userName") || "Aadarsh";
  const userEmail = localStorage.getItem("userEmail") || "aadarsh@example.com";

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/user-history/${userEmail}`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
      }
    } catch (err) {
      console.error("Failed to fetch history", err);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a PDF or DOCX file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("target_role", targetRole);
    formData.append("user_email", userEmail);

    setLoading(true);
    setError(null);
    setNotification(null);

    try {
      const response = await fetch(`${API_BASE_URL}/analyze-career`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to analyze resume. Please check file format or size.");
      }

      const data = await response.json();
      setResult(data);
      
      // Success Notification format
      setNotification(`${userName}, your resume analyzing completed! 🎉`);
      
      fetchHistory();
    } catch (err: any) {
      setError(err.message || "An error occurred while connecting to backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8 mt-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 p-6 rounded-2xl text-white shadow-lg flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Welcome back, {userName}! 👋</h1>
          <p className="text-sm text-blue-100 mt-1">Manage your career intelligence and track your past resume analyses.</p>
        </div>
        <div className="bg-white/10 px-4 py-2 rounded-lg text-xs font-semibold backdrop-blur-md">
          {userEmail}
        </div>
      </div>

      {/* Notification Alert */}
      {notification && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl font-medium shadow-sm flex items-center justify-between">
          <span>✨ {notification}</span>
          <button onClick={() => setNotification(null)} className="text-xs text-emerald-600 font-bold hover:underline">Dismiss</button>
        </div>
      )}

      {/* Upload Card */}
      <div className="bg-white p-8 rounded-2xl shadow-md space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-gray-800">Upload & Analyze New Resume</h2>
            <p className="text-xs text-gray-500">Select your target role and get instant AI diagnostics.</p>
          </div>
          {result && (
            <button 
              onClick={() => window.print()}
              className="px-4 py-2 bg-gray-800 text-white text-xs font-semibold rounded-lg hover:bg-gray-900 transition"
            >
              🖨️ Print Report
            </button>
          )}
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Select Target Role:</label>
            <select 
              value={targetRole} 
              onChange={(e) => setTargetRole(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-xl bg-gray-50 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            >
              <option value="Python Backend Developer">Python Backend Developer</option>
              <option value="Full-Stack Developer">Full-Stack Developer</option>
              <option value="Junior Data Scientist / ML Engineer">Junior Data Scientist / ML Engineer</option>
            </select>
          </div>

          <div className="border-2 border-dashed border-gray-300 p-6 rounded-xl text-center bg-gray-50">
            <input 
              type="file" 
              accept=".pdf,.docx" 
              onChange={handleFileChange} 
              className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
            />
            {file && <p className="mt-2 text-sm text-green-600 font-medium">Selected: {file.name}</p>}
          </div>
        </div>

        <button 
          onClick={handleUpload} 
          disabled={loading}
          className="w-full py-3 px-4 bg-blue-600 text-white font-semibold rounded-xl shadow-md hover:bg-blue-700 disabled:bg-gray-400 transition"
        >
          {loading ? "Analyzing Career Readiness..." : "Upload & Analyze"}
        </button>

        {error && <p className="text-red-500 text-sm bg-red-50 p-3 rounded">{error}</p>}
      </div>

      {/* Current Result Section with FULL Details */}
      {result && (
        <div className="bg-white p-8 rounded-2xl shadow-md space-y-6">
          <h3 className="text-xl font-bold text-gray-800">Latest Analysis Report</h3>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-indigo-50 rounded-xl border border-indigo-100 text-center">
              <h4 className="text-xs uppercase font-bold text-indigo-600 tracking-wider">Role Match Score</h4>
              <p className="text-3xl font-extrabold text-indigo-900 mt-1">{result.match_score}%</p>
            </div>
            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100 text-center">
              <h4 className="text-xs uppercase font-bold text-emerald-600 tracking-wider">Resume Health Score</h4>
              <p className="text-3xl font-extrabold text-emerald-900 mt-1">{result.resume_score}/100</p>
            </div>
          </div>

          <div className="p-5 bg-blue-50 rounded-xl border border-blue-100">
            <h4 className="font-semibold text-blue-900">Extracted Technical Skills</h4>
            <div className="flex flex-wrap gap-2 mt-2">
              {result.extracted_skills.map((skill: string, idx: number) => (
                <span key={idx} className="px-3 py-1 bg-blue-600 text-white text-xs font-medium rounded-full">{skill}</span>
              ))}
            </div>
          </div>

          <div className="p-5 bg-green-50 rounded-xl border border-green-100">
            <h4 className="font-semibold text-green-900">Target Role Fit</h4>
            <p className="text-xs text-green-700 mt-0.5">Targeting: <strong>{result.target_role}</strong></p>
            <ul className="list-disc list-inside mt-2 text-sm text-green-800 space-y-1">
              {result.current_suitability.map((role: string, idx: number) => (
                <li key={idx} className="font-medium">{role}</li>
              ))}
            </ul>
          </div>

          <div className="p-5 bg-amber-50 rounded-xl border border-amber-100">
            <h4 className="font-semibold text-amber-900">Missing Skill Gaps for this Role</h4>
            <ul className="list-disc list-inside mt-2 text-sm text-amber-800 space-y-1">
              {result.skill_gaps.length > 0 ? result.skill_gaps.map((gap: string, i: number) => <li key={i}>{gap}</li>) : <li>No gaps found!</li>}
            </ul>
          </div>

          <div className="p-5 bg-purple-50 rounded-xl border border-purple-100">
            <h4 className="font-semibold text-purple-900">Customized Action Plan & Roadmap</h4>
            <ol className="list-decimal list-inside mt-2 text-sm text-purple-800 space-y-2">
              {result.future_action_plan.map((step: string, idx: number) => (
                <li key={idx} className="font-medium">{step}</li>
              ))}
            </ol>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-5 bg-teal-50 rounded-xl border border-teal-100">
              <h4 className="font-semibold text-teal-900 mb-2">✅ What to Do (Best Practices)</h4>
              <ul className="list-disc list-inside text-xs text-teal-800 space-y-2">
                {result.dos_and_donts.dos.map((item: string, idx: number) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="p-5 bg-rose-50 rounded-xl border border-rose-100">
              <h4 className="font-semibold text-rose-900 mb-2">❌ What to Avoid (Mistakes)</h4>
              <ul className="list-disc list-inside text-xs text-rose-800 space-y-2">
                {result.dos_and_donts.donts.map((item: string, idx: number) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Past History Dashboard Section */}
      <div className="bg-white p-8 rounded-2xl shadow-md space-y-4">
        <h3 className="text-xl font-bold text-gray-800">Your Analysis History ({history.length})</h3>
        {history.length === 0 ? (
          <p className="text-sm text-gray-500">No past analysis history found. Upload a resume above!</p>
        ) : (
          <div className="space-y-3">
            {history.map((item, index) => (
              <div key={index} className="p-4 bg-gray-50 rounded-xl border border-gray-200 flex justify-between items-center">
                <div>
                  <p className="font-semibold text-gray-800 text-sm">{item.filename}</p>
                  <p className="text-xs text-gray-500">Target Role: <span className="font-medium text-blue-600">{item.target_role}</span></p>
                </div>
                <div className="flex gap-4 text-right">
                  <div>
                    <p className="text-xs text-gray-400">Match</p>
                    <p className="text-sm font-bold text-indigo-600">{item.match_score}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Health</p>
                    <p className="text-sm font-bold text-emerald-600">{item.resume_score}/100</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}