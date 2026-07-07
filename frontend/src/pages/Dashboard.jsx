import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import { Search, Mail, Clock, LogOut, Settings, Briefcase, MapPin, Zap, X, Plus, CheckCircle, AlertCircle, Loader, Timer, User, History } from 'lucide-react'

const SUGGESTED_ROLES = [
  'MERN Stack Developer', 'Full Stack Developer', 'React.js Developer',
  'Frontend Developer', 'Node.js Developer', 'Backend Developer',
  'JavaScript Developer', 'Web Developer', 'Software Engineer',
  'Associate Software Engineer', 'Full Stack Engineer', 'Software Developer',
  'Application Developer', 'Product Engineer', 'UI Developer',
  'Python Developer', 'AI/ML Engineer', 'Data Analyst',
]

const SUGGESTED_SKILLS = [
  'React.js', 'Node.js', 'JavaScript', 'TypeScript', 'MongoDB', 'Express.js',
  'Python', 'HTML', 'CSS', 'Tailwind CSS', 'Redux', 'Next.js', 'REST API',
  'Git', 'SQL', 'AWS', 'Docker', 'Machine Learning', 'Java', 'C++',
]

const JOB_TYPES = ['Work from Office', 'Remote', 'Walk-in Interview', 'Hybrid']

export default function Dashboard() {
  const { user, logout, updatePreferences, updateProfile, updateAutoSearch, searchJobs, API } = useAuth()
  const [activeTab, setActiveTab] = useState('search')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState(null)

  // Progress state
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')
  const [platformResults, setPlatformResults] = useState([])
  const [currentStep, setCurrentStep] = useState(0)
  const [totalSteps, setTotalSteps] = useState(12)

  // Preferences state
  const prefs = user?.job_preferences || {}
  const [roles, setRoles] = useState(prefs.roles || [])
  const [skills, setSkills] = useState(prefs.skills || [])
  const [experience, setExperience] = useState(prefs.experience || '0-1 years')
  const [locations, setLocations] = useState(prefs.locations || [])
  const [jobTypes, setJobTypes] = useState(prefs.job_types || JOB_TYPES)
  const [locationInput, setLocationInput] = useState('')

  // Auto-search state
  const INTERVAL_HOURS = 24
  const autoSearch = user?.auto_search || {}
  const [autoEnabled, setAutoEnabled] = useState(autoSearch.enabled || false)
  const [countdown, setCountdown] = useState(null)
  const [nextRunTime, setNextRunTime] = useState(null)
  const countdownRef = useRef(null)

  // Profile state
  const [profileName, setProfileName] = useState(user?.name || '')
  const [notificationEmail, setNotificationEmail] = useState(user?.notification_email || user?.email || '')
  const [savingProfile, setSavingProfile] = useState(false)

  // History state
  const [searchHistory, setSearchHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)

  const [testingAutoSearch, setTestingAutoSearch] = useState(false)

  // Fetch next run time and start countdown
  const fetchNextRun = async () => {
    try {
      const status = await API.get('/user/auto-search')
      const data = status.data?.auto_search
      if (data?.next_run) {
        setNextRunTime(new Date(data.next_run))
      } else {
        setNextRunTime(null)
        setCountdown(null)
      }
      // Sync enabled state from server
      if (data?.enabled !== undefined) setAutoEnabled(data.enabled)
    } catch {
      // Server unreachable — stop timer, don't retry automatically
      setNextRunTime(null)
      setCountdown(null)
    }
  }

  useEffect(() => {
    fetchNextRun()
    return () => { if (countdownRef.current) clearInterval(countdownRef.current) }
  }, [])

  useEffect(() => {
    if (countdownRef.current) clearInterval(countdownRef.current)
    if (!nextRunTime || !autoEnabled) { setCountdown(null); return }

    const tick = () => {
      const diff = nextRunTime - new Date()
      if (diff <= 0) {
        clearInterval(countdownRef.current)
        countdownRef.current = null
        setCountdown('Running now...')
        // Fetch once after a short delay — if server is down, timer stays stopped
        setTimeout(fetchNextRun, 3000)
        return
      }
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      setCountdown(`${h}h ${m}m ${s}s`)
    }
    tick()
    countdownRef.current = window.setInterval(tick, 1000)
    return () => { if (countdownRef.current) clearInterval(countdownRef.current) }
  }, [nextRunTime, autoEnabled])

  const handleSavePreferences = async () => {
    if (roles.length === 0) return toast.error('Add at least one role')
    if (locations.length === 0) return toast.error('Add at least one location')
    try {
      await updatePreferences({ roles, skills, experience, locations, job_types: jobTypes })
      toast.success('Preferences saved!')
    } catch (err) {
      toast.error('Failed to save preferences')
    }
  }

  const handleSaveProfile = async () => {
    if (!profileName.trim()) return toast.error('Name cannot be empty')
    if (!notificationEmail.trim()) return toast.error('Notification email cannot be empty')
    setSavingProfile(true)
    try {
      await updateProfile({ name: profileName, notification_email: notificationEmail })
      toast.success('Profile updated!')
    } catch {
      toast.error('Failed to update profile')
    } finally {
      setSavingProfile(false)
    }
  }

  const fetchHistory = async () => {
    setHistoryLoading(true)
    try {
      const res = await API.get('/jobs/history')
      setSearchHistory(res.data.history || [])
    } catch {
      toast.error('Failed to load history')
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleSearchWithProgress = async () => {
    if (roles.length === 0 || locations.length === 0) {
      return toast.error('Please set your preferences first')
    }

    setSearching(true)
    setSearchResults(null)
    setProgress(0)
    setPlatformResults([])
    setProgressMessage('Saving preferences...')
    setCurrentStep(0)

    try {
      // Save preferences first
      await updatePreferences({ roles, skills, experience, locations, job_types: jobTypes })

      setProgressMessage('Starting job search...')

      // Use SSE for real-time progress
      const token = localStorage.getItem('token')
      const apiBase = import.meta.env.VITE_API_URL || '/api'
      const eventSource = new EventSource(`${apiBase}/jobs/search-stream?token=${token}`)

      // Since EventSource doesn't support headers, use fetch with ReadableStream
      const response = await fetch(`${apiBase}/jobs/search-stream`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              if (data.type === 'progress') {
                setProgress(data.progress)
                setProgressMessage(data.message)
                setCurrentStep(data.step)
                setTotalSteps(data.total_steps)
              } else if (data.type === 'platform_done') {
                setPlatformResults(prev => [...prev, { name: data.platform, found: data.found, status: 'done' }])
              } else if (data.type === 'platform_error') {
                setPlatformResults(prev => [...prev, { name: data.platform, found: 0, status: 'error' }])
              } else if (data.type === 'complete') {
                setProgress(100)
                setProgressMessage(data.message)
                setSearchResults(data)
                setSearching(false)
                if (data.email_sent) toast.success(`${data.jobs_found} jobs found & emailed!`)
                else toast.success(`${data.jobs_found} jobs found!`)
              }
            } catch (e) { /* skip parse errors */ }
          }
        }
      }
    } catch (err) {
      // Fallback to regular search if SSE fails
      try {
        const result = await searchJobs()
        setSearchResults(result)
        setProgress(100)
        setSearching(false)
        if (result.email_sent) toast.success(`Found ${result.jobs_found} jobs! Email sent.`)
      } catch (fallbackErr) {
        toast.error(fallbackErr.response?.data?.error || 'Search failed. Try again.')
        setSearching(false)
      }
    }
  }

  const handleAutoSearch = async () => {
    try {
      await updateAutoSearch({ enabled: !autoEnabled, interval_hours: INTERVAL_HOURS })
      setAutoEnabled(!autoEnabled)
      if (!autoEnabled) {
        toast.success('Auto-search enabled! First search running now — check your email shortly.')
        setTimeout(fetchNextRun, 500)
      } else {
        toast.success('Auto-search disabled')
        setNextRunTime(null)
        setCountdown(null)
      }
    } catch (err) {
      toast.error('Failed to update auto-search')
    }
  }

  const handleTestAutoSearch = async () => {
    setTestingAutoSearch(true)
    try {
      await API.post('/user/auto-search/test')
      toast.success('Test triggered! Check your email in a few minutes.')
      setTimeout(fetchNextRun, 2000)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Test failed')
    } finally {
      setTestingAutoSearch(false)
    }
  }

  const addLocation = () => {
    if (locationInput.trim() && !locations.includes(locationInput.trim())) {
      setLocations([...locations, locationInput.trim()])
      setLocationInput('')
    }
  }

  const toggleItem = (item, list, setList) => {
    if (list.includes(item)) setList(list.filter((i) => i !== item))
    else setList([...list, item])
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-white/5 bg-black/20 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold bg-gradient-to-r from-purple-400 to-indigo-400 bg-clip-text text-transparent">Job Finder AI</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-400">Hi, {user?.name}</span>
            <button onClick={logout} className="text-gray-400 hover:text-white transition-colors"><LogOut size={18} /></button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Tabs */}
        <div className="flex gap-2 mb-8 flex-wrap">
          {[
            { id: 'search', icon: Search, label: 'Search Jobs' },
            { id: 'preferences', icon: Settings, label: 'Preferences' },
            { id: 'auto', icon: Clock, label: 'Auto-Search' },
            { id: 'history', icon: History, label: 'History' },
            { id: 'profile', icon: User, label: 'Profile' },
          ].map((tab) => (
            <button key={tab.id} onClick={() => {
              setActiveTab(tab.id)
              if (tab.id === 'history') fetchHistory()
            }}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${activeTab === tab.id ? 'bg-purple-600 text-white' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}>
              <tab.icon size={16} />{tab.label}
            </button>
          ))}
        </div>

        {/* Search Tab */}
        {activeTab === 'search' && (
          <div className="space-y-6">

            {/* Search Button Card */}
            {!searching && !searchResults && (
              <div className="glass-card p-8 text-center">
                <div className="w-16 h-16 rounded-2xl bg-purple-500/10 flex items-center justify-center mx-auto mb-5">
                  <Search className="text-purple-400" size={28} />
                </div>
                <h2 className="text-2xl font-bold mb-2">Find Jobs Now</h2>
                <p className="text-gray-400 mb-6 max-w-md mx-auto">
                  Searches LinkedIn, Indeed, Naukri, Internshala, CutShort & more.<br />
                  Only <strong className="text-purple-300">India-based</strong> jobs (Ahmedabad, Gandhinagar, Remote India).
                </p>

                {roles.length > 0 && locations.length > 0 ? (
                  <button onClick={handleSearchWithProgress} className="btn-primary text-lg py-4 px-10 flex items-center gap-3 mx-auto">
                    <Zap size={20} /><span>Search & Send to Email</span>
                  </button>
                ) : (
                  <div className="text-yellow-400 text-sm">Set your preferences first (Preferences tab)</div>
                )}

                {roles.length > 0 && (
                  <div className="mt-8 text-left max-w-lg mx-auto bg-white/5 rounded-xl p-5">
                    <h4 className="text-sm font-semibold text-gray-300 mb-3">Your Search Criteria:</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex gap-2"><Briefcase size={14} className="text-purple-400 mt-0.5" /><span className="text-gray-400">Roles: {roles.slice(0, 5).join(', ')}{roles.length > 5 ? ` +${roles.length - 5} more` : ''}</span></div>
                      <div className="flex gap-2"><MapPin size={14} className="text-purple-400 mt-0.5" /><span className="text-gray-400">Locations: {locations.join(', ')}</span></div>
                      <div className="flex gap-2"><Clock size={14} className="text-purple-400 mt-0.5" /><span className="text-gray-400">Experience: {experience}</span></div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Progress UI */}
            {searching && (
              <div className="glass-card p-8">
                <div className="text-center mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-purple-500/10 flex items-center justify-center mx-auto mb-4 animate-pulse">
                    <Search className="text-purple-400" size={28} />
                  </div>
                  <h2 className="text-xl font-bold mb-1">Searching Jobs...</h2>
                  <p className="text-gray-400 text-sm">{progressMessage}</p>
                </div>

                {/* Progress Bar */}
                <div className="mb-6">
                  <div className="flex justify-between text-xs text-gray-400 mb-2">
                    <span>Step {currentStep} of {totalSteps}</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="w-full h-3 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-purple-600 to-indigo-500 rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                </div>

                {/* Platform Results */}
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {platformResults.map((p, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                      <div className="flex items-center gap-3">
                        {p.status === 'done' ? (
                          <CheckCircle size={16} className="text-green-400" />
                        ) : (
                          <AlertCircle size={16} className="text-yellow-400" />
                        )}
                        <span className="text-sm font-medium">{p.name}</span>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full ${p.found > 0 ? 'bg-green-500/20 text-green-300' : 'bg-white/10 text-gray-400'}`}>
                        {p.found} jobs
                      </span>
                    </div>
                  ))}

                  {/* Currently searching indicator */}
                  {searching && platformResults.length < 10 && (
                    <div className="flex items-center gap-3 p-3 bg-purple-500/10 rounded-lg border border-purple-500/20">
                      <Loader size={16} className="text-purple-400 animate-spin" />
                      <span className="text-sm text-purple-300">{progressMessage}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Search Results */}
            {searchResults && !searching && (
              <div className="space-y-4">
                {/* Summary */}
                <div className="glass-card p-6 border-green-500/20">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center">
                      <CheckCircle className="text-green-400" size={20} />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold">Search Complete!</h3>
                      <p className="text-sm text-gray-400">
                        Found <strong className="text-green-300">{searchResults.jobs_found}</strong> India-based jobs
                        {searchResults.email_sent && ' • Email sent'}
                      </p>
                    </div>
                  </div>

                  {/* Platform breakdown */}
                  {platformResults.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                      {platformResults.filter(p => p.found > 0).map((p, i) => (
                        <span key={i} className="text-xs px-3 py-1 rounded-full bg-white/5 text-gray-300">
                          {p.name}: {p.found}
                        </span>
                      ))}
                    </div>
                  )}

                  <button onClick={() => { setSearchResults(null); setPlatformResults([]) }} className="btn-secondary text-sm py-2 px-4">
                    Search Again
                  </button>
                </div>

                {/* Job List */}
                <div className="glass-card p-6">
                  <h4 className="font-semibold mb-4">Top Matches (all sent to email)</h4>
                  <div className="max-h-[500px] overflow-y-auto space-y-3">
                    {searchResults.jobs?.slice(0, 30).map((job, i) => (
                      <div key={i} className="flex justify-between items-start p-4 bg-white/5 rounded-xl hover:bg-white/8 transition-all">
                        <div className="flex-1">
                          <div className="font-medium text-sm mb-1">{job.title}</div>
                          <div className="text-xs text-gray-400 mb-2">{job.company} • {job.location}</div>
                          <div className="flex flex-wrap gap-1.5">
                            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium ${
                              job.job_type === 'Walk-in Interview' ? 'bg-red-500/20 text-red-300' :
                              job.job_type === 'Remote' ? 'bg-green-500/20 text-green-300' :
                              'bg-blue-500/20 text-blue-300'
                            }`}>{job.job_type}</span>
                            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium ${
                              job.company_type === 'Product' ? 'bg-purple-500/20 text-purple-300' :
                              job.company_type === 'Service' ? 'bg-orange-500/20 text-orange-300' :
                              job.company_type === 'Startup' ? 'bg-teal-500/20 text-teal-300' :
                              'bg-white/10 text-gray-400'
                            }`}>{job.company_type === 'Product' ? 'Product' : job.company_type === 'Service' ? 'Service' : job.company_type || 'Other'}</span>
                            <span className="inline-block px-2 py-0.5 rounded text-[10px] bg-white/10 text-gray-400">{job.source}</span>
                            {job.experience && <span className="inline-block px-2 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-300">{job.experience}</span>}
                            {job.salary && <span className="inline-block px-2 py-0.5 rounded text-[10px] bg-green-500/20 text-green-300">{job.salary}</span>}
                          </div>
                        </div>
                        <a href={job.url} target="_blank" rel="noopener noreferrer" className="ml-3 text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white px-4 py-2 rounded-lg font-medium whitespace-nowrap">Apply</a>
                      </div>
                    ))}
                  </div>
                  {searchResults.jobs_found > 30 && (
                    <p className="text-center text-gray-400 text-sm mt-4 pt-4 border-t border-white/5">
                      + {searchResults.jobs_found - 30} more jobs sent to your email
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Preferences Tab */}
        {activeTab === 'preferences' && (
          <div className="space-y-6">
            {/* Roles */}
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><Briefcase size={18} className="text-purple-400" />Job Roles</h3>
              <div className="flex flex-wrap gap-2 mb-4">
                {roles.map((role) => (
                  <span key={role} className="tag flex items-center gap-1">{role}<button onClick={() => setRoles(roles.filter(r => r !== role))}><X size={12} /></button></span>
                ))}
              </div>
              <p className="text-xs text-gray-500 mb-2">Click to add:</p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTED_ROLES.filter(r => !roles.includes(r)).map((role) => (
                  <button key={role} onClick={() => setRoles([...roles, role])} className="text-xs px-3 py-1 rounded-full bg-white/5 text-gray-400 hover:bg-purple-500/20 hover:text-purple-300 border border-white/5 transition-all">
                    <Plus size={10} className="inline mr-1" />{role}
                  </button>
                ))}
              </div>
            </div>

            {/* Skills */}
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><Zap size={18} className="text-purple-400" />Skills</h3>
              <div className="flex flex-wrap gap-2 mb-4">
                {skills.map((skill) => (
                  <span key={skill} className="tag flex items-center gap-1">{skill}<button onClick={() => setSkills(skills.filter(s => s !== skill))}><X size={12} /></button></span>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                {SUGGESTED_SKILLS.filter(s => !skills.includes(s)).map((skill) => (
                  <button key={skill} onClick={() => setSkills([...skills, skill])} className="text-xs px-3 py-1 rounded-full bg-white/5 text-gray-400 hover:bg-purple-500/20 hover:text-purple-300 border border-white/5 transition-all">
                    <Plus size={10} className="inline mr-1" />{skill}
                  </button>
                ))}
              </div>
            </div>

            {/* Locations */}
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><MapPin size={18} className="text-purple-400" />Locations</h3>
              <p className="text-xs text-yellow-400/80 mb-3">WFO jobs: Ahmedabad & Gandhinagar only | Remote: India-based only</p>
              <div className="flex flex-wrap gap-2 mb-4">
                {locations.map((loc) => (
                  <span key={loc} className="tag flex items-center gap-1">{loc}<button onClick={() => setLocations(locations.filter(l => l !== loc))}><X size={12} /></button></span>
                ))}
              </div>
              <div className="flex gap-2">
                <input value={locationInput} onChange={(e) => setLocationInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addLocation()} placeholder="Type city name and press Enter" className="input-field flex-1" />
                <button onClick={addLocation} className="btn-secondary px-4">Add</button>
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                {['Ahmedabad', 'Gandhinagar', 'Remote'].filter(l => !locations.includes(l)).map((loc) => (
                  <button key={loc} onClick={() => setLocations([...locations, loc])} className="text-xs px-3 py-1 rounded-full bg-white/5 text-gray-400 hover:bg-purple-500/20 hover:text-purple-300 border border-white/5 transition-all">
                    <Plus size={10} className="inline mr-1" />{loc}
                  </button>
                ))}
              </div>
            </div>

            {/* Experience & Job Type */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="glass-card p-6">
                <h3 className="text-lg font-semibold mb-4">Experience Level</h3>
                <select value={experience} onChange={(e) => setExperience(e.target.value)} className="input-field">
                  <option value="0-1 years">Fresher (0-1 years)</option>
                  <option value="1-3 years">1-3 years</option>
                  <option value="3-5 years">3-5 years</option>
                  <option value="5+ years">5+ years</option>
                </select>
              </div>
              <div className="glass-card p-6">
                <h3 className="text-lg font-semibold mb-4">Job Types</h3>
                <div className="space-y-2">
                  {JOB_TYPES.map((type) => (
                    <label key={type} className="flex items-center gap-3 cursor-pointer">
                      <input type="checkbox" checked={jobTypes.includes(type)} onChange={() => toggleItem(type, jobTypes, setJobTypes)} className="w-4 h-4 rounded border-gray-600 text-purple-600 focus:ring-purple-500" />
                      <span className="text-sm text-gray-300">{type}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <button onClick={handleSavePreferences} className="btn-primary w-full">Save Preferences</button>
          </div>
        )}

        {/* Auto-Search Tab */}
        {activeTab === 'auto' && (
          <div className="space-y-6">
            <div className="glass-card p-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-xl font-bold flex items-center gap-2"><Clock className="text-purple-400" size={22} />Daily Auto-Search</h3>
                  <p className="text-gray-400 text-sm mt-1">Get fresh India-based job matches emailed to you every day</p>
                </div>
                <button onClick={handleAutoSearch} className={`relative w-14 h-7 rounded-full transition-all ${autoEnabled ? 'bg-purple-600' : 'bg-white/10'}`}>
                  <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-all ${autoEnabled ? 'left-8' : 'left-1'}`}></div>
                </button>
              </div>

              <div className="p-4 bg-white/5 rounded-xl flex items-center gap-4 mb-5">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center shrink-0">
                  <Mail className="text-purple-400" size={20} />
                </div>
                <div>
                  <p className="text-sm font-medium">Every 24 hours</p>
                  <p className="text-xs text-gray-400">Jobs sent to {user?.notification_email || user?.email}</p>
                </div>
              </div>

              {autoEnabled && countdown && (
                <div className="p-4 bg-purple-500/10 border border-purple-500/20 rounded-xl">
                  <div className="flex items-center gap-3">
                    <Timer size={20} className="text-purple-400" />
                    <div>
                      <p className="text-sm text-gray-300">Next search in:</p>
                      <p className="text-2xl font-bold text-purple-300 font-mono">{countdown}</p>
                    </div>
                  </div>
                </div>
              )}

              {!autoEnabled && (
                <p className="text-xs text-gray-500">Enable to receive daily job alerts automatically</p>
              )}

              {autoEnabled && (
                <button
                  onClick={handleTestAutoSearch}
                  disabled={testingAutoSearch}
                  className="mt-5 w-full btn-secondary flex items-center justify-center gap-2 text-sm"
                >
                  {testingAutoSearch ? <Loader size={15} className="animate-spin" /> : <Zap size={15} />}
                  {testingAutoSearch ? 'Running test...' : 'Test Now (send email immediately)'}
                </button>
              )}
            </div>

            {/* Status */}
            <div className="glass-card p-6">
              <h4 className="font-semibold mb-3">Status</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-400">Auto-search:</span><span className={autoEnabled ? 'text-green-400' : 'text-red-400'}>{autoEnabled ? 'Active' : 'Disabled'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Frequency:</span><span className="text-gray-300">Every 24 hours</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Notification email:</span><span className="text-gray-300">{user?.notification_email || user?.email}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Filter:</span><span className="text-gray-300">India only (WFO + Remote India)</span></div>
                {countdown && autoEnabled && <div className="flex justify-between"><span className="text-gray-400">Next run:</span><span className="text-purple-300 font-mono">{countdown}</span></div>}
                {autoSearch.last_run && <div className="flex justify-between"><span className="text-gray-400">Last run:</span><span className="text-gray-300">{new Date(autoSearch.last_run).toLocaleString()}</span></div>}
              </div>
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="space-y-4">
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2"><History size={18} className="text-purple-400" />Search History</h3>
                <button onClick={fetchHistory} className="btn-secondary text-xs py-1.5 px-3">Refresh</button>
              </div>
              {historyLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader size={24} className="text-purple-400 animate-spin" />
                </div>
              ) : searchHistory.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <History size={40} className="mx-auto mb-3 opacity-30" />
                  <p>No search history yet</p>
                  <p className="text-xs mt-1">Run a manual or auto search to see history here</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {[...searchHistory].reverse().map((item, i) => (
                    <div key={i} className="flex items-center justify-between p-4 bg-white/5 rounded-xl">
                      <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${item.type === 'auto' ? 'bg-purple-400' : 'bg-green-400'}`} />
                        <div>
                          <p className="text-sm font-medium">{item.jobs_found} jobs found</p>
                          <p className="text-xs text-gray-400">{new Date(item.timestamp).toLocaleString()}</p>
                        </div>
                      </div>
                      <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                        item.type === 'auto' ? 'bg-purple-500/20 text-purple-300' : 'bg-green-500/20 text-green-300'
                      }`}>{item.type === 'auto' ? 'Auto' : 'Manual'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="space-y-6">
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2"><User size={18} className="text-purple-400" />Profile</h3>
              <div className="space-y-5">
                <div>
                  <label className="text-sm text-gray-400 mb-1.5 block">Display Name</label>
                  <input
                    value={profileName}
                    onChange={(e) => setProfileName(e.target.value)}
                    className="input-field"
                    placeholder="Your name"
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400 mb-1.5 block">Login Email</label>
                  <input value={user?.email} disabled className="input-field opacity-50 cursor-not-allowed" />
                  <p className="text-xs text-gray-500 mt-1">Login email cannot be changed</p>
                </div>
                <div>
                  <label className="text-sm text-gray-400 mb-1.5 block">Notification Email</label>
                  <input
                    value={notificationEmail}
                    onChange={(e) => setNotificationEmail(e.target.value)}
                    className="input-field"
                    placeholder="Email to receive job alerts"
                    type="email"
                  />
                  <p className="text-xs text-gray-500 mt-1">Job alert emails will be sent to this address</p>
                </div>
                <button onClick={handleSaveProfile} disabled={savingProfile} className="btn-primary w-full flex items-center justify-center gap-2">
                  {savingProfile ? <Loader size={16} className="animate-spin" /> : <CheckCircle size={16} />}
                  {savingProfile ? 'Saving...' : 'Save Profile'}
                </button>
              </div>
            </div>

            <div className="glass-card p-6">
              <h4 className="font-semibold mb-3">Account Info</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-400">Name:</span><span className="text-gray-300">{user?.name}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Login email:</span><span className="text-gray-300">{user?.email}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Notification email:</span><span className="text-purple-300">{user?.notification_email || user?.email}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Auto-search:</span><span className={autoEnabled ? 'text-green-400' : 'text-gray-400'}>{autoEnabled ? 'Active' : 'Disabled'}</span></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
