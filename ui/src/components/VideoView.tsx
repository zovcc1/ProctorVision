import { useSession } from '@/contexts/SessionContext';
import { Camera, CameraOff } from 'lucide-react';

export function VideoView() {
  const { frameSrc, isActive } = useSession();

  return (
    <div className="relative flex items-center justify-center bg-black rounded-xl overflow-hidden aspect-video w-full max-w-3xl shadow-lg border border-gray-800">
      {isActive && frameSrc ? (
        <img
          src={frameSrc}
          alt="Live stream"
          className="w-full h-full object-contain"
        />
      ) : (
        <div className="flex flex-col items-center gap-3 text-gray-500">
          {isActive ? (
            <>
              <Camera className="w-12 h-12 animate-pulse" />
              <p className="text-lg font-medium">Waiting for camera feed...</p>
            </>
          ) : (
            <>
              <CameraOff className="w-12 h-12" />
              <p className="text-lg font-medium">Camera is off</p>
            </>
          )}
        </div>
      )}
      {isActive && (
        <div className="absolute top-3 right-3 flex items-center gap-2 bg-red-600/90 text-white px-3 py-1 rounded-full text-sm font-semibold animate-pulse">
          <span className="w-2 h-2 bg-white rounded-full" />
          LIVE
        </div>
      )}
    </div>
  );
}
