import { useSession, SessionProvider } from '@/contexts/SessionContext';
import { useSocket } from '@/hooks/useSocket';
import { VideoView } from '@/components/VideoView';
import { SessionControls } from '@/components/SessionControls';
import { StatsPanel } from '@/components/StatsPanel';
import { AlertsPanel } from '@/components/AlertsPanel';
import { SettingsModal } from '@/components/SettingsModal';
import { ReportsPanel } from '@/components/ReportsPanel';
import { Button } from '@/components/ui/button';
import { AlertCircle, X } from 'lucide-react';

function AppContent() {
  const { error, dismissError, isActive } = useSession();
  useSocket();

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center font-bold text-lg">
              PV
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">ProctorVision</h1>
              <p className="text-xs text-gray-400">Student Attention Monitoring System</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <SettingsModal />
            <SessionControls />
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6 space-y-6">
        {error && (
          <div className="flex items-center justify-between bg-red-900/30 border border-red-700 text-red-200 px-4 py-3 rounded-lg">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={dismissError} className="text-red-200 hover:text-white hover:bg-red-800">
              <X className="w-4 h-4" />
            </Button>
          </div>
        )}

        <div className="flex flex-col lg:flex-row gap-6">
          <div className="flex-1 flex flex-col items-center gap-4">
            <VideoView />
            {isActive && (
              <div className="text-sm text-gray-400 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                Session in progress
              </div>
            )}
          </div>

          <div className="w-full lg:w-96 space-y-4">
            <AlertsPanel />
            <ReportsPanel />
          </div>
        </div>

        <StatsPanel />
      </main>

      <footer className="border-t border-gray-800 bg-gray-900/30 py-4 text-center text-xs text-gray-500">
        ProctorVision Desktop Edition — Local processing. No data leaves your device.
      </footer>
    </div>
  );
}

function App() {
  return (
    <SessionProvider>
      <AppContent />
    </SessionProvider>
  );
}

export default App;
