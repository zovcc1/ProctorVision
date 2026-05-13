import { useState } from 'react';
import { useSession } from '@/contexts/SessionContext';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Settings, Save } from 'lucide-react';

export function SettingsModal() {
  const { settings, updateSettings, fetchSettings } = useSession();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<Record<string, any>>({});

  const handleOpen = () => {
    fetchSettings();
    setForm(settings);
    setOpen(true);
  };

  const handleSave = async () => {
    await updateSettings(form);
    setOpen(false);
  };

  const setNested = (key: string, value: any) => {
    setForm(prev => {
      const next = { ...prev };
      const keys = key.split('.');
      let obj = next;
      for (let i = 0; i < keys.length - 1; i++) {
        if (!obj[keys[i]]) obj[keys[i]] = {};
        obj = obj[keys[i]];
      }
      obj[keys[keys.length - 1]] = value;
      return next;
    });
  };

  const getNested = (key: string, def: any = '') => {
    const keys = key.split('.');
    let val = form;
    for (const k of keys) {
      val = val?.[k];
      if (val === undefined) return def;
    }
    return val;
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="lg" className="gap-2" onClick={handleOpen}>
          <Settings className="w-5 h-5" /> Settings
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>System Settings</DialogTitle>
        </DialogHeader>
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Yaw Threshold (deg)</Label>
              <Input
                type="number"
                value={getNested('thresholds.yaw_threshold', 30)}
                onChange={e => setNested('thresholds.yaw_threshold', Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Pitch Threshold (deg)</Label>
              <Input
                type="number"
                value={getNested('thresholds.pitch_threshold', 20)}
                onChange={e => setNested('thresholds.pitch_threshold', Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Mouth Open Ratio</Label>
              <Input
                type="number"
                step="0.01"
                value={getNested('thresholds.mouth_open_ratio', 0.2)}
                onChange={e => setNested('thresholds.mouth_open_ratio', Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Hand Proximity Factor</Label>
              <Input
                type="number"
                step="0.1"
                value={getNested('thresholds.hand_face_proximity_factor', 1.5)}
                onChange={e => setNested('thresholds.hand_face_proximity_factor', Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Alert Tolerance (ms)</Label>
              <Input
                type="number"
                value={getNested('thresholds.alert_tolerance_ms', 500)}
                onChange={e => setNested('thresholds.alert_tolerance_ms', Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Warning Duration (s)</Label>
              <Input
                type="number"
                step="0.5"
                value={getNested('thresholds.warning_duration_s', 3.0)}
                onChange={e => setNested('thresholds.warning_duration_s', Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>YOLO Confidence</Label>
              <Input
                type="number"
                step="0.05"
                value={getNested('yolo.confidence', 0.7)}
                onChange={e => setNested('yolo.confidence', Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Target FPS</Label>
              <Input
                type="number"
                value={getNested('target_fps', 20)}
                onChange={e => setNested('target_fps', Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>JPEG Quality</Label>
              <Input
                type="number"
                value={getNested('output.jpeg_quality', 60)}
                onChange={e => setNested('output.jpeg_quality', Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Camera Resolution (WxH)</Label>
              <div className="flex gap-2">
                <Input
                  type="number"
                  value={getNested('camera.resolution.0', 640)}
                  onChange={e => {
                    const arr = getNested('camera.resolution', [640, 480]);
                    arr[0] = Number(e.target.value);
                    setNested('camera.resolution', [...arr]);
                  }}
                />
                <Input
                  type="number"
                  value={getNested('camera.resolution.1', 480)}
                  onChange={e => {
                    const arr = getNested('camera.resolution', [640, 480]);
                    arr[1] = Number(e.target.value);
                    setNested('camera.resolution', [...arr]);
                  }}
                />
              </div>
            </div>
          </div>
          <Button onClick={handleSave} className="w-full gap-2">
            <Save className="w-4 h-4" /> Save Settings
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
