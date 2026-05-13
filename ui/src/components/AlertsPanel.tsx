import { useSession } from '@/contexts/SessionContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, X, EyeOff, Smartphone, Users, Hand } from 'lucide-react';

const eventIcons: Record<string, React.ReactNode> = {
  'gaze_outside': <EyeOff className="w-4 h-4" />,
  'phone_detected': <Smartphone className="w-4 h-4" />,
  'extra_person': <Users className="w-4 h-4" />,
  'mouth_covered': <Hand className="w-4 h-4" />,
  'hand_near_face': <Hand className="w-4 h-4" />,
};

const eventLabels: Record<string, string> = {
  'gaze_outside': 'Looking Away',
  'phone_detected': 'Phone Detected',
  'extra_person': 'Extra Person',
  'mouth_covered': 'Mouth Covered',
  'hand_near_face': 'Hand Near Face',
};

export function AlertsPanel() {
  const { alerts, clearAlerts, isActive } = useSession();

  if (!isActive && alerts.length === 0) return null;

  return (
    <Card className="w-full">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-500" /> Live Alerts
        </CardTitle>
        {alerts.length > 0 && (
          <Button variant="ghost" size="sm" onClick={clearAlerts} className="h-8 gap-1">
            <X className="w-3 h-3" /> Clear
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <p className="text-sm text-gray-400">No alerts yet</p>
        ) : (
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {alerts.map((alert, idx) => (
              <div
                key={idx}
                className={`flex items-center gap-3 p-2 rounded-lg border text-sm ${
                  alert.type === 'start'
                    ? 'bg-red-50 border-red-200 text-red-700'
                    : 'bg-green-50 border-green-200 text-green-700'
                }`}
              >
                {eventIcons[alert.event] || <AlertTriangle className="w-4 h-4" />}
                <span className="font-medium">
                  {alert.type === 'start' ? 'Started' : 'Ended'}: {eventLabels[alert.event] || alert.event}
                </span>
                {alert.duration !== undefined && (
                  <span className="text-xs opacity-70">({alert.duration}s)</span>
                )}
                <span className="ml-auto text-xs opacity-50">
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
