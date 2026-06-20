import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Login } from './components/Login';
import { Register } from './components/Register';
import { VoiceCoach } from './components/VoiceCoach';
import { Dashboard } from './components/Dashboard';
import { Loader2 } from 'lucide-react';

const MainApp: React.FC = () => {
  const { token, loading } = useAuth();
  const [currentTab, setCurrentTab] = useState<'coach' | 'dashboard'>('coach');
  const [authScreen, setAuthScreen] = useState<'login' | 'register'>('login');

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center">
        <Loader2 className="w-10 h-10 text-violet-600 animate-spin mb-4" />
        <span className="text-slate-400 text-sm font-semibold tracking-wide">
          Connecting to TalkBuddy...
        </span>
      </div>
    );
  }

  if (!token) {
    return authScreen === 'login' ? (
      <Login onRegisterClick={() => setAuthScreen('register')} />
    ) : (
      <Register onLoginClick={() => setAuthScreen('login')} />
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar currentTab={currentTab} setCurrentTab={setCurrentTab} />
      
      <main className="flex-1 bg-slate-950 relative overflow-hidden">
        {/* Background visual graphics */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-violet-600/5 rounded-full blur-[120px] pointer-events-none" />
        
        <div className="relative z-10 w-full h-full">
          {currentTab === 'coach' ? <VoiceCoach /> : <Dashboard />}
        </div>
      </main>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;
