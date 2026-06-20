import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { 
  Play, Square, Mic, Volume2, Sparkles, MessageSquare, 
  HelpCircle, ChevronRight, AlertCircle, ArrowLeft
} from 'lucide-react';

interface FeedbackData {
  original_text: string;
  corrected_text: string;
  explanation: string;
  suggestions: string;
  response_text: string;
  follow_up_question: string;
  scores: {
    grammar: number;
    vocabulary: number;
    fluency: number;
  };
}

interface Message {
  id: string | number;
  role: 'user' | 'assistant';
  content: string;
  feedback?: FeedbackData;
  created_at: string;
}

export const VoiceCoach: React.FC = () => {
  const { token, apiFetch } = useAuth();
  
  // Selection States
  const [activeSession, setActiveSession] = useState<any>(null);
  const [learningMode, setLearningMode] = useState<string>('casual');
  const [loading, setLoading] = useState(false);
  
  // Chat History
  const [messages, setMessages] = useState<Message[]>([]);
  
  // WebSocket and Status States
  const wsRef = useRef<WebSocket | null>(null);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [coachStatus, setCoachStatus] = useState<string>('Ready to talk');
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Audio Playback
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Microphone Hook
  const { isRecording, recordingTime, audioLevel, startRecording, stopRecording } = useAudioRecorder();

  // Mode Options Details
  const modes = [
    { id: 'casual', title: 'Casual Talk', desc: 'Friendly conversation about hobbies, interests, and life.', icon: MessageSquare, gradient: 'from-blue-600 to-indigo-600' },
    { id: 'interview', title: 'Job Interview', desc: 'Structured professional questions to prepare for your career.', icon: Sparkles, gradient: 'from-amber-600 to-orange-600' },
    { id: 'ielts', title: 'IELTS Speaking', desc: 'Prepare for parts 1, 2, and 3 under rigorous scoring conditions.', icon: HelpCircle, gradient: 'from-emerald-600 to-teal-600' },
    { id: 'business', title: 'Business English', desc: 'Refine communication for meetings, emails, and deals.', icon: ChevronRight, gradient: 'from-violet-600 to-purple-600' },
    { id: 'daily', title: 'Daily Life', desc: 'Simulate routines like ordering food, hotels, or directions.', icon: Play, gradient: 'from-rose-600 to-pink-600' },
  ];

  // 1. Initialize Active Session
  const startSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/api/sessions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: learningMode })
      });
      if (!res.ok) throw new Error('Failed to create session');
      const sessionData = await res.json();
      setActiveSession(sessionData);
      setMessages([]);
    } catch (err: any) {
      setError(err.message || 'Error initializing conversation.');
    } finally {
      setLoading(false);
    }
  };

  // 2. Connect WebSockets with auto-reconnect
  useEffect(() => {
    if (!activeSession || !token) return;

    let reconnectAttempts = 0;
    const maxReconnects = 3;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let currentWs: WebSocket | null = null;

    const connect = () => {
      setWsStatus('connecting');
      
      let wsUrl = '';
      const customWsUrl = import.meta.env.VITE_WS_URL;
      const customApiUrl = import.meta.env.VITE_API_URL;
      
      if (customWsUrl) {
        // Explicitly configured WS endpoint (e.g. wss://space.hf.space)
        wsUrl = `${customWsUrl.replace(/\/$/, '')}/api/ws/chat/${activeSession.id}?token=${token}`;
      } else if (customApiUrl) {
        // Derive WS protocol and host from VITE_API_URL
        const wsProtocol = customApiUrl.startsWith('https:') ? 'wss:' : 'ws:';
        const hostPath = customApiUrl.replace(/^https?:\/\//i, '').replace(/\/$/, '');
        wsUrl = `${wsProtocol}//${hostPath}/api/ws/chat/${activeSession.id}?token=${token}`;
      } else {
        // Fallback relative resolution
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${wsProtocol}//${window.location.host}/api/ws/chat/${activeSession.id}?token=${token}`;
      }

      const ws = new WebSocket(wsUrl);
      currentWs = ws;
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus('connected');
        setCoachStatus('Ready to record');
        setError(null);
        reconnectAttempts = 0; // Reset on successful connection

        // Load existing session messages if resuming
        loadSessionMessages(activeSession.id);
      };

      ws.onclose = (event) => {
        setWsStatus('disconnected');
        setCoachStatus('Coach disconnected');

        // Auto-reconnect if not intentionally closed (code 1000 = normal close)
        if (event.code !== 1000 && reconnectAttempts < maxReconnects) {
          reconnectAttempts++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts - 1), 8000);
          setCoachStatus(`Reconnecting in ${delay / 1000}s... (${reconnectAttempts}/${maxReconnects})`);
          reconnectTimer = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        setError('Connection to speaking coach failed.');
      };

      ws.onmessage = async (event) => {
        if (typeof event.data === 'string') {
          // Text Message: Logs, Status, or JSON Feedback
          try {
            const data = JSON.parse(event.data);
            if (data.event === 'status') {
              setCoachStatus(data.message);
            } else if (data.event === 'error') {
              setError(data.message);
              setProcessing(false);
              setCoachStatus('Ready to record');
            } else if (data.event === 'feedback') {
              // LLM Text response
              const feedback: FeedbackData = {
                original_text: data.original_text,
                corrected_text: data.corrected_text,
                explanation: data.explanation,
                suggestions: data.suggestions,
                response_text: data.response_text,
                follow_up_question: data.follow_up_question,
                scores: data.scores
              };

              // Append User Speech message
              const userMsg: Message = {
                id: `u-${Date.now()}`,
                role: 'user',
                content: data.original_text,
                feedback: feedback,
                created_at: new Date().toISOString()
              };

              // Append Assistant Response message
              const assistantMsg: Message = {
                id: `a-${Date.now()}`,
                role: 'assistant',
                content: `${data.response_text} ${data.follow_up_question}`,
                created_at: new Date().toISOString()
              };

              setMessages(prev => [...prev, userMsg, assistantMsg]);
              setProcessing(false);
              setCoachStatus('Ready to record');
            }
          } catch (parseErr) {
            console.error('Failed to parse WS message:', parseErr);
          }
        } else if (event.data instanceof Blob) {
          // Binary Message: Autoplay TTS WAV response
          try {
            const audioUrl = URL.createObjectURL(event.data);
            if (audioRef.current) {
              // Revoke previous blob URL to prevent memory leak
              if (audioRef.current.src && audioRef.current.src.startsWith('blob:')) {
                URL.revokeObjectURL(audioRef.current.src);
              }
              audioRef.current.src = audioUrl;
              audioRef.current.play();
            }
          } catch (e) {
            console.error('Failed to play TTS feedback audio:', e);
          }
        }
      };
    };

    connect();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (currentWs) currentWs.close(1000); // Normal close — prevents auto-reconnect
      wsRef.current = null;
    };
  }, [activeSession, token]);

  // Auto-scroll chat to bottom on new messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, processing]);

  const loadSessionMessages = async (sessionId: number) => {
    try {
      const res = await apiFetch(`/api/sessions/${sessionId}`);
      if (res.ok) {
        const sessionDetail = await res.json();
        const formattedMsgs: Message[] = [];
        
        sessionDetail.messages.forEach((m: any) => {
          formattedMsgs.push({
            id: `u-${m.id}`,
            role: 'user',
            content: m.original_text,
            feedback: {
              original_text: m.original_text,
              corrected_text: m.corrected_text,
              explanation: m.explanation,
              suggestions: m.suggestions,
              response_text: m.response_text,
              follow_up_question: '',
              scores: {
                grammar: m.grammar_score,
                vocabulary: m.vocabulary_score,
                fluency: m.fluency_score
              }
            },
            created_at: m.created_at
          });
          formattedMsgs.push({
            id: `a-${m.id}`,
            role: 'assistant',
            content: m.response_text,
            created_at: m.created_at
          });
        });
        setMessages(formattedMsgs);
      }
    } catch (err) {
      console.error('Failed to load session history:', err);
    }
  };

  // 3. Audio Streaming Controls
  const toggleRecording = async () => {
    if (isRecording) {
      setProcessing(true);
      setCoachStatus('Wrapping up speech...');
      stopRecording();
      
      // Let backend know audio stream has finished
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ event: 'stop_audio' }));
      }
    } else {
      setError(null);
      
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setError('Coach is not connected. Re-establishing session...');
        return;
      }
      
      // Let backend know raw audio is coming
      wsRef.current.send(JSON.stringify({ event: 'start_audio' }));

      // Callback streams chunks over WS as they are gathered
      await startRecording((blobChunk) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          // Convert Blob chunk directly to ArrayBuffer and send as binary
          blobChunk.arrayBuffer().then((buffer) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(buffer);
            }
          });
        }
      });
      setCoachStatus('Listening...');
    }
  };

  // Helper formatting for duration timer
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!activeSession) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-extrabold tracking-tight text-white mb-2 bg-gradient-to-r from-white via-slate-200 to-violet-400 bg-clip-text text-transparent">
            Choose Your Speaking Mode
          </h1>
          <p className="text-slate-400 max-w-xl mx-auto font-medium">
            Select a tailored learning mode to begin conversation practice with your AI coach.
          </p>
        </div>

        {error && (
          <div className="mb-6 flex items-start gap-3 p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-200 text-sm max-w-xl mx-auto">
            <AlertCircle className="w-5 h-5 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
          {modes.map((mode) => {
            const Icon = mode.icon;
            return (
              <button
                key={mode.id}
                onClick={() => setLearningMode(mode.id)}
                className={`glass-card p-6 rounded-3xl text-left flex flex-col items-start gap-4 transition-all duration-300 relative overflow-hidden group border ${
                  learningMode === mode.id 
                    ? 'border-violet-500/60 bg-violet-600/5 shadow-lg shadow-violet-500/5' 
                    : 'border-white/5'
                }`}
              >
                <div className={`w-12 h-12 rounded-2xl bg-gradient-to-tr ${mode.gradient} flex items-center justify-center shadow-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white mb-1.5">{mode.title}</h3>
                  <p className="text-sm text-slate-400 font-medium leading-relaxed">{mode.desc}</p>
                </div>
                {learningMode === mode.id && (
                  <div className="absolute top-4 right-4 w-2.5 h-2.5 rounded-full bg-violet-500 shadow-md shadow-violet-500/50" />
                )}
              </button>
            );
          })}
        </div>

        <div className="text-center">
          <button
            onClick={startSession}
            disabled={loading}
            className="px-8 py-4 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold rounded-2xl transition-all duration-200 shadow-xl shadow-violet-500/20 hover:shadow-violet-500/25 px-12 disabled:opacity-50"
          >
            {loading ? 'Starting Session...' : 'Start Coaching Session'}
          </button>
        </div>
      </div>
    );
  }

  // Active training layout
  return (
    <div className="max-w-5xl mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-12 gap-8 h-[calc(100vh-100px)]">
      {/* Hidden Audio element for autoplaying binary streams */}
      <audio ref={audioRef} className="hidden" />

      {/* Left Column: Chat log / dialogue */}
      <div className="lg:col-span-7 flex flex-col h-full bg-slate-900/35 border border-white/5 rounded-3xl overflow-hidden glass-panel">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between bg-slate-950/20">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setActiveSession(null)}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 transition-all"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <span className="text-sm font-bold text-white block capitalize">{learningMode} Coaching</span>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className={`w-2 h-2 rounded-full ${wsStatus === 'connected' ? 'bg-emerald-500 shadow-md shadow-emerald-500/50' : 'bg-amber-500'}`} />
                <span className="text-xs text-slate-400 font-semibold">{wsStatus === 'connected' ? 'Online' : 'Reconnecting...'}</span>
              </div>
            </div>
          </div>
          
          <div className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-violet-600/10 text-violet-400 border border-violet-500/10">
            {coachStatus}
          </div>
        </div>

        {/* Message logs */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center px-6">
              <div className="w-14 h-14 rounded-2xl bg-violet-600/5 flex items-center justify-center text-violet-400 border border-violet-500/10 mb-4 animate-bounce">
                <Mic className="w-6 h-6" />
              </div>
              <h4 className="text-base font-bold text-slate-200">Start the conversation</h4>
              <p className="text-xs text-slate-500 max-w-sm mt-1 font-semibold leading-relaxed">
                Click the microphone button below, say anything in English, and press stop. Your coach will respond instantly.
              </p>
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div key={msg.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl p-4 leading-relaxed text-sm ${
                    isUser 
                      ? 'bg-violet-600 text-white rounded-br-none shadow-md shadow-violet-500/5' 
                      : 'bg-slate-900 border border-white/5 text-slate-200 rounded-bl-none'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              );
            })
          )}
          {processing && (
            <div className="flex justify-start">
              <div className="bg-slate-900 border border-white/5 rounded-2xl rounded-bl-none p-4 text-slate-400 flex items-center gap-2 text-sm">
                <span className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                <span className="text-xs font-semibold ml-1">{coachStatus}</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Microphone action bar */}
        <div className="p-6 border-t border-white/5 bg-slate-950/20">
          {error && (
            <div className="mb-4 flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex flex-col items-center justify-center gap-3">
            {/* Visualizer volume animation */}
            {isRecording && (
              <div className="flex items-center gap-1 h-6">
                {[...Array(6)].map((_, i) => {
                  const scale = 0.2 + (audioLevel / 100) * (0.8 * (i % 2 === 0 ? 0.9 : 1.2));
                  return (
                    <div 
                      key={i} 
                      className="w-1 bg-violet-500 rounded-full origin-center transition-all duration-75"
                      style={{ height: '24px', transform: `scaleY(${scale})` }}
                    />
                  );
                })}
              </div>
            )}

            <div className="flex items-center gap-4">
              <button
                onClick={toggleRecording}
                disabled={processing || wsStatus !== 'connected'}
                className={`w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 relative shadow-lg ${
                  isRecording 
                    ? 'bg-red-500 hover:bg-red-400 shadow-red-500/20 scale-105' 
                    : 'bg-violet-600 hover:bg-violet-500 shadow-violet-500/20'
                } disabled:opacity-50 disabled:pointer-events-none`}
              >
                {isRecording ? <Square className="w-6 h-6 text-white" /> : <Mic className="w-7 h-7 text-white" />}
                
                {isRecording && (
                  <span className="absolute -inset-2.5 rounded-full border border-red-500/30 animate-ping pointer-events-none" />
                )}
              </button>

              {isRecording && (
                <span className="text-sm font-bold text-red-400 tracking-wider">
                  {formatTime(recordingTime)}
                </span>
              )}
            </div>
            
            <span className="text-[11px] text-slate-500 font-semibold tracking-wide uppercase">
              {isRecording ? 'Click to submit speaking' : 'Click microphone to speak'}
            </span>
          </div>
        </div>
      </div>

      {/* Right Column: Real-time grammar & score feedback */}
      <div className="lg:col-span-5 flex flex-col h-full space-y-6">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          <Volume2 className="w-5 h-5 text-violet-400" />
          Speech Evaluations
        </h3>

        <div className="flex-1 overflow-y-auto space-y-6 pr-1">
          {/* Loop messages to find the latest user message containing feedback */}
          {(() => {
            const feedbackMsgs = messages.filter(m => m.role === 'user' && m.feedback);
            const latestMsg = feedbackMsgs[feedbackMsgs.length - 1];

            if (!latestMsg || !latestMsg.feedback) {
              return (
                <div className="glass-card rounded-3xl p-6 border border-white/5 text-center flex flex-col items-center justify-center h-48">
                  <p className="text-slate-400 text-sm font-medium">No evaluations yet.</p>
                  <p className="text-xs text-slate-500 mt-1">Speak to see real-time grammar corrections, vocabulary suggestions, and scoring metrics here.</p>
                </div>
              );
            }

            const feedback = latestMsg.feedback;
            const hasCorrections = feedback.corrected_text.toLowerCase() !== 'no correction needed.' && 
                                   feedback.corrected_text !== 'N/A';

            return (
              <div className="space-y-5">
                {/* Score Panel */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="glass-card rounded-2xl p-4 border border-white/5 text-center">
                    <span className="text-xs text-slate-400 font-semibold block mb-1">Grammar</span>
                    <span className="text-2xl font-black text-violet-400">{feedback.scores.grammar}</span>
                  </div>
                  <div className="glass-card rounded-2xl p-4 border border-white/5 text-center">
                    <span className="text-xs text-slate-400 font-semibold block mb-1">Vocabulary</span>
                    <span className="text-2xl font-black text-indigo-400">{feedback.scores.vocabulary}</span>
                  </div>
                  <div className="glass-card rounded-2xl p-4 border border-white/5 text-center">
                    <span className="text-xs text-slate-400 font-semibold block mb-1">Fluency</span>
                    <span className="text-2xl font-black text-emerald-400">{feedback.scores.fluency}</span>
                  </div>
                </div>

                {/* Correction Panel */}
                <div className="glass-card rounded-3xl p-6 border border-white/5 space-y-4">
                  <div>
                    <span className="text-xs text-slate-400 font-bold tracking-wider uppercase block mb-1.5">You Said:</span>
                    <p className="text-sm text-slate-300 italic">"{feedback.original_text}"</p>
                  </div>
                  
                  <div className="border-t border-white/5 pt-4">
                    <span className="text-xs text-slate-400 font-bold tracking-wider uppercase block mb-1.5">Corrected:</span>
                    <p className={`text-sm ${hasCorrections ? 'text-emerald-400 font-medium' : 'text-slate-300'}`}>
                      {hasCorrections ? `"${feedback.corrected_text}"` : 'No grammar corrections needed!'}
                    </p>
                  </div>
                </div>

                {/* Explanation / Notes Panel */}
                <div className="glass-card rounded-3xl p-6 border border-white/5 space-y-4">
                  <div>
                    <span className="text-xs text-violet-400 font-bold tracking-wider uppercase block mb-1.5">Grammar Explanation:</span>
                    <p className="text-xs text-slate-400 font-medium leading-relaxed">{feedback.explanation}</p>
                  </div>
                  
                  <div className="border-t border-white/5 pt-4">
                    <span className="text-xs text-indigo-400 font-bold tracking-wider uppercase block mb-1.5">Vocabulary Suggestions:</span>
                    <p className="text-xs text-slate-400 font-medium leading-relaxed">{feedback.suggestions}</p>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
};
