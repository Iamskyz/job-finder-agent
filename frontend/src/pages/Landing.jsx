import { Link } from 'react-router-dom'
import { Search, Mail, Clock, Zap, Globe, Shield } from 'lucide-react'

export default function Landing() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-transparent to-indigo-900/20"></div>
        <div className="max-w-6xl mx-auto px-6 py-20 relative">
          <nav className="flex justify-between items-center mb-20">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-indigo-400 bg-clip-text text-transparent">Job Finder AI</h1>
            <div className="flex gap-4">
              <Link to="/login" className="btn-secondary text-sm py-2 px-5">Login</Link>
              <Link to="/signup" className="btn-primary text-sm py-2 px-5">Get Started Free</Link>
            </div>
          </nav>

          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-sm mb-8">
              <Zap size={14} /> AI-Powered Job Search Agent
            </div>
            <h2 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
              Find Your Dream Job
              <span className="block bg-gradient-to-r from-purple-400 to-indigo-400 bg-clip-text text-transparent">Delivered to Your Inbox</span>
            </h2>
            <p className="text-gray-400 text-lg mb-10 max-w-2xl mx-auto">
              Set your preferences once. Our AI agent searches LinkedIn, Indeed, Naukri, Internshala, CutShort & more — then sends matching jobs directly to your email.
            </p>
            <div className="flex gap-4 justify-center">
              <Link to="/signup" className="btn-primary text-lg py-4 px-8">Start Finding Jobs →</Link>
            </div>
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="max-w-6xl mx-auto px-6 py-20">
        <h3 className="text-3xl font-bold text-center mb-16">How It Works</h3>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            { icon: Search, title: 'Set Preferences', desc: 'Choose your roles, skills, locations, and job types (Walk-in, WFO, Remote)' },
            { icon: Globe, title: 'AI Searches 10+ Sites', desc: 'LinkedIn, Indeed, Naukri, Internshala, CutShort, InstaHyre, Google Jobs & more' },
            { icon: Mail, title: 'Get Email Alerts', desc: 'Receive categorized job matches directly in your inbox — automatically' },
          ].map((f, i) => (
            <div key={i} className="glass-card p-8 text-center hover:border-purple-500/30 transition-all">
              <div className="w-14 h-14 rounded-xl bg-purple-500/10 flex items-center justify-center mx-auto mb-5">
                <f.icon className="text-purple-400" size={24} />
              </div>
              <h4 className="text-lg font-semibold mb-3">{f.title}</h4>
              <p className="text-gray-400 text-sm">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Platforms */}
      <div className="max-w-6xl mx-auto px-6 py-16">
        <h3 className="text-2xl font-bold text-center mb-10">We Search Across</h3>
        <div className="flex flex-wrap justify-center gap-4">
          {['LinkedIn', 'Indeed', 'Naukri', 'Internshala', 'CutShort', 'InstaHyre', 'Google Jobs', 'Glassdoor', 'RemoteOK', 'FreshersWorld'].map((p) => (
            <span key={p} className="px-5 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-gray-300">{p}</span>
          ))}
        </div>
      </div>

      {/* Auto Search Feature */}
      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="glass-card p-10 flex flex-col md:flex-row items-center gap-10">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-4">
              <Clock className="text-purple-400" size={24} />
              <h3 className="text-2xl font-bold">Auto-Search Feature</h3>
            </div>
            <p className="text-gray-400 mb-4">Enable auto-search and choose your interval (1-72 hours). Our agent will automatically search and email you new job matches — even while you sleep.</p>
            <ul className="text-gray-400 text-sm space-y-2">
              <li className="flex items-center gap-2"><Shield size={14} className="text-green-400" /> No spam — only relevant matches</li>
              <li className="flex items-center gap-2"><Shield size={14} className="text-green-400" /> Disable anytime from dashboard</li>
              <li className="flex items-center gap-2"><Shield size={14} className="text-green-400" /> Customize search frequency</li>
            </ul>
          </div>
          <div className="flex-1 text-center">
            <Link to="/signup" className="btn-primary text-lg py-4 px-8">Get Started Free →</Link>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8 text-center text-gray-500 text-sm">
        <p>Job Finder AI Agent — Built with React, Flask, MongoDB</p>
      </footer>
    </div>
  )
}
