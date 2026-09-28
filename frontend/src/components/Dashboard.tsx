import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  TrendingUp, Award, BarChart2, Calendar, 
  Loader2, AlertTriangle 
} from 'lucide-react';

interface ScoreProgressPoint {
  date: string;
  grammar: number;
  vocabulary: number;
  fluency: number;
}

interface StatsData {
  avg_grammar_score: number;
  avg_vocabulary_score: number;
  avg_fluency_score: number;
  total_sessions: number;
  total_messages: number;
  mode_counts: { [key: string]: number };
  score_progress: ScoreProgressPoint[];
}

export const Dashboard: React.FC = () => {
  const { apiFetch } = useAuth();
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/api/dashboard/stats');
      if (!res.ok) throw new Error('Failed to load dashboard metrics');
      const data = await res.json();
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Error pulling user progress logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  // Helper to draw custom SVG charts dynamically
  const renderSVGChart = (points: ScoreProgressPoint[]) => {
    if (points.length < 2) {
      return (
        <div className="h-full flex items-center justify-center text-slate-500 text-xs">
          Not enough data points yet. Speak in more sessions to populate progress trends!
        </div>
      );
    }

    const width = 500;
    const height = 180;
    const padding = 20;

    // Extract dates and scores
    const xCoords = points.map((_, index) => padding + (index / (points.length - 1)) * (width - padding * 2));
    
    // Function to map score (0-100) to Y pixel (top to bottom)
    const mapY = (score: number) => height - padding - (score / 100) * (height - padding * 2);

    const makePath = (key: 'grammar' | 'vocabulary' | 'fluency') => {
      return points.map((p, idx) => {
        const x = xCoords[idx];
        const y = mapY(p[key]);
        return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
      }).join(' ');
    };

    const grammarPath = makePath('grammar');
    const vocabPath = makePath('vocabulary');
    const fluencyPath = makePath('fluency');

    return (
      <div className="relative w-full h-full">
        <svg className="w-full h-full" viewBox={`0 0 ${width} ${height}`}>
          {/* Y Axis Gridlines */}
          {[0, 25, 50, 75, 100].map((val) => {
            const y = mapY(val);
            return (
              <g key={val}>
                <line x1={padding} y1={y} x2={width - padding} y2={y} stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
                <text x={padding - 5} y={y + 3} fill="rgba(255,255,255,0.3)" fontSize="8" textAnchor="end">{val}</text>
              </g>
            );
          })}

          {/* Grammar Line */}
          <path d={grammarPath} fill="none" stroke="#8b5cf6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          {/* Vocabulary Line */}
          <path d={vocabPath} fill="none" stroke="#6366f1" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          {/* Fluency Line */}
          <path d={fluencyPath} fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

          {/* Dots on points */}
          {points.map((p, idx) => (
            <g key={idx}>
              <circle cx={xCoords[idx]} cy={mapY(p.grammar)} r="3" fill="#8b5cf6" />
              <circle cx={xCoords[idx]} cy={mapY(p.vocabulary)} r="3" fill="#6366f1" />
              <circle cx={xCoords[idx]} cy={mapY(p.fluency)} r="3" fill="#10b981" />
            </g>
          ))}
        </svg>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center h-[calc(100vh-150px)]">
        <Loader2 className="w-10 h-10 text-violet-500 animate-spin mb-4" />
        <span className="text-slate-400 text-sm font-semibold">Gathering your progress...</span>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-white mb-2">Error Loading Dashboard</h3>
        <p className="text-sm text-slate-400 mb-6">{error || 'Could not fetch metrics.'}</p>
        <button
          onClick={fetchStats}
          className="px-6 py-2.5 bg-violet-600 hover:bg-violet-500 text-white font-semibold rounded-xl transition-all"
        >
          Retry Load
        </button>
      </div>
    );
  }

  const modeLabels: { [key: string]: string } = {
    casual: 'Casual Talk',
    interview: 'Job Interview',
    ielts: 'IELTS Prep',
    business: 'Business Eng',
    daily: 'Daily Life'
  };

  return (
    <div className="max-w-5xl mx-auto px-3 sm:px-4 py-6 sm:py-8 space-y-6 sm:space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-2 bg-gradient-to-r from-white via-slate-200 to-violet-400 bg-clip-text text-transparent">
          Student Progress Dashboard
        </h1>
        <p className="text-slate-400 font-medium text-xs sm:text-sm">
          Track speaking performance, review average grades, and view historical details.
        </p>
      </div>

      {/* Main Aggregated Scores */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
        <div className="glass-card rounded-3xl p-6 border border-white/5 relative overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs text-violet-400 font-bold uppercase tracking-wider">Grammar</span>
            <Award className="w-5 h-5 text-violet-500" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-black text-white">{stats.avg_grammar_score}</span>
            <span className="text-xs text-slate-400 font-bold">/ 100</span>
          </div>
          <p className="text-xs text-slate-400 mt-2 font-medium">Your average accuracy across all recorded messages.</p>
        </div>

        <div className="glass-card rounded-3xl p-6 border border-white/5 relative overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs text-indigo-400 font-bold uppercase tracking-wider">Vocabulary</span>
            <TrendingUp className="w-5 h-5 text-indigo-500" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-black text-white">{stats.avg_vocabulary_score}</span>
            <span className="text-xs text-slate-400 font-bold">/ 100</span>
          </div>
          <p className="text-xs text-slate-400 mt-2 font-medium">Your lexical diversity and use of appropriate word forms.</p>
        </div>

        <div className="glass-card rounded-3xl p-6 border border-white/5 relative overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs text-emerald-400 font-bold uppercase tracking-wider">Fluency</span>
            <BarChart2 className="w-5 h-5 text-emerald-500" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-black text-white">{stats.avg_fluency_score}</span>
            <span className="text-xs text-slate-400 font-bold">/ 100</span>
          </div>
          <p className="text-xs text-slate-400 mt-2 font-medium">Estimated speech volume, response length, and coherence.</p>
        </div>
      </div>

      {/* Analytics Graph & Topic Breakdowns */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6">
        {/* SVG Progress Graph */}
        <div className="lg:col-span-8 glass-card rounded-2xl sm:rounded-3xl p-4 sm:p-6 border border-white/5 flex flex-col h-[260px] sm:h-[320px]">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-violet-400" />
              <h3 className="text-lg font-bold text-white">Score Progress Over Time</h3>
            </div>
            {/* Color key legends */}
            <div className="flex gap-4 text-[10px] font-bold tracking-wide uppercase">
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-violet-500" /> Grammar</div>
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-indigo-500" /> Vocab</div>
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-emerald-500" /> Fluency</div>
            </div>
          </div>
          <div className="flex-1">
            {renderSVGChart(stats.score_progress)}
          </div>
        </div>

        {/* Mode Breakdown */}
        <div className="lg:col-span-4 glass-card rounded-2xl sm:rounded-3xl p-4 sm:p-6 border border-white/5 flex flex-col h-[260px] sm:h-[320px]">
          <h3 className="text-lg font-bold text-white mb-6">Practiced Scenarios</h3>
          
          <div className="flex-1 flex flex-col justify-around">
            {Object.entries(stats.mode_counts).map(([mode, count]) => {
              const maxCount = Math.max(...Object.values(stats.mode_counts), 1);
              const ratio = (count / maxCount) * 100;
              return (
                <div key={mode} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-300">{modeLabels[mode]}</span>
                    <span className="text-slate-400">{count} {count === 1 ? 'session' : 'sessions'}</span>
                  </div>
                  <div className="w-full bg-slate-950/40 rounded-full h-2 overflow-hidden border border-white/5">
                    <div 
                      className={`h-full rounded-full transition-all duration-500 ${
                        mode === 'casual' ? 'bg-blue-600' :
                        mode === 'interview' ? 'bg-orange-600' :
                        mode === 'ielts' ? 'bg-emerald-600' :
                        mode === 'business' ? 'bg-purple-600' :
                        'bg-pink-600'
                      }`}
                      style={{ width: `${ratio}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Summary totals */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 pt-4 border-t border-white/5">
        <div className="text-center md:text-left">
          <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Total Sessions</span>
          <p className="text-2xl font-extrabold text-white mt-1">{stats.total_sessions}</p>
        </div>
        <div className="text-center md:text-left">
          <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Messages Exchanged</span>
          <p className="text-2xl font-extrabold text-white mt-1">{stats.total_messages}</p>
        </div>
        <div className="text-center md:text-left">
          <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Days Active</span>
          <p className="text-2xl font-extrabold text-white mt-1">{stats.score_progress.length}</p>
        </div>
        <div className="text-center md:text-left">
          <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Overall Coach Rating</span>
          <p className="text-2xl font-extrabold text-violet-400 mt-1">
            {stats.total_messages > 0 
              ? `${Math.round((stats.avg_grammar_score + stats.avg_vocabulary_score + stats.avg_fluency_score) / 3)}%`
              : 'N/A'
            }
          </p>
        </div>
      </div>
    </div>
  );
};
