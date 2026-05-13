import { useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { useSession } from '@/contexts/SessionContext';

export function useSocket() {
  const {
    sessionId,
    isActive,
    addFrame,
    addStats,
    addAlert,
    setError,
  } = useSession();

  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    if (!isActive || !sessionId) {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
      return;
    }

    const socket = io(window.location.origin, {
      transports: ['websocket', 'polling'],
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      socket.emit('join', { session_id: sessionId });
    });

    socket.on('frame', (data: { image: string; session_id: string }) => {
      if (data.session_id === sessionId) {
        addFrame(`data:image/jpeg;base64,${data.image}`);
      }
    });

    socket.on('stats', (data: any) => {
      if (data.session_id === sessionId) {
        addStats(data);
      }
    });

    socket.on('alert', (data: any) => {
      if (data.session_id === sessionId) {
        addAlert({
          type: data.type,
          event: data.event,
          session_id: data.session_id,
          timestamp: Date.now(),
          duration: data.duration,
        });
      }
    });

    socket.on('connect_error', (err: Error) => {
      setError(`WebSocket error: ${err.message}`);
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [isActive, sessionId, addFrame, addStats, addAlert, setError]);
}
