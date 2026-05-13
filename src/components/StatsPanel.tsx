import { useSession } from '@/contexts/SessionContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Clock, Eye, Users, Smartphone, Hand } from 'lucide-react';

export function StatsPanel() {
  const { stats } = useSession();

  const stateColors: Record<string, string> = {
    Attentive: 'text-green-500',
    Distracted: 'text-orange-500',
    Warning: 'text-red-500',
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 w-full">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
            <Clock className="w-4 h-4" /> Duration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{stats.duration_seconds}s</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
            <Eye className="w-4 h-4" /> Attention
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className={`text-2xl font-bold ${stateColors[stats.current_state || 'Attentive']}`}>
            {stats.current_state || 'Idle'}
          </p>
        </CardContent>
      </Card>

      <Card className="md:col-span-2 xl:col-span-2">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-500">State Distribution</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span>Attentive</span>
              <span>{stats.attentive_pct}%</span>
            </div>
            <Progress value={stats.attentive_pct} className="h-2 bg-gray-200 [&>div]:bg-green-500" />
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span>Distracted</span>
              <span>{stats.distracted_pct}%</span>
            </div>
            <Progress value={stats.distracted_pct} className="h-2 bg-gray-200 [&>div]:bg-orange-500" />
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span>Warning</span>
              <span>{stats.warning_pct}%</span>
            </div>
            <Progress value={stats.warning_pct} className="h-2 bg-gray-200 [&>div]:bg-red-500" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
            <Smartphone className="w-4 h-4" /> Phone Events
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{stats.phone_events}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
            <Eye className="w-4 h-4" /> Gaze Outside
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{stats.gaze_outside_events}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
            <Users className="w-4 h-4" /> Extra Person
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{stats.extra_person_events}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
            <Hand className="w-4 h-4" /> Mouth Covered
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{stats.mouth_covered_events}</p>
        </CardContent>
      </Card>
    </div>
  );
}
