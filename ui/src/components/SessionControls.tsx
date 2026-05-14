import { useSession } from '@/contexts/SessionContext';
import { Button } from '@/components/ui/button';
import { Play, Square, Loader2 } from 'lucide-react';

export function SessionControls() {
  const { isActive, status, startSession, stopSession } = useSession();

  const isLoading = status === 'starting' || status === 'stopping';

  return (
    <div className="flex items-center gap-4">
      {!isActive ? (
        <Button
          size="lg"
          onClick={startSession}
          disabled={isLoading}
          className="bg-green-600 hover:bg-green-700 text-white gap-2 min-w-[160px]"
        >
          {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
          {isLoading ? 'Starting...' : 'Start Session'}
        </Button>
      ) : (
        <Button
          size="lg"
          onClick={() => stopSession()}
          disabled={isLoading}
          variant="destructive"
          className="gap-2 min-w-[160px]"
        >
          {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Square className="w-5 h-5" />}
          {isLoading ? 'Stopping...' : 'Stop Session'}
        </Button>
      )}
    </div>
  );
}
