import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileText, Download, RefreshCw } from 'lucide-react';

export function ReportsPanel() {
  const [reports, setReports] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/reports');
      const data = await res.json();
      setReports(data.reports || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  return (
    <Card className="w-full">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
          <FileText className="w-4 h-4" /> Generated Reports
        </CardTitle>
        <Button variant="ghost" size="sm" onClick={fetchReports} disabled={loading} className="h-8 gap-1">
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </CardHeader>
      <CardContent>
        {reports.length === 0 ? (
          <p className="text-sm text-gray-400">No reports yet. Start and stop a session to generate reports.</p>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {reports.map((name) => (
              <div key={name} className="flex items-center justify-between p-2 rounded-lg border hover:bg-gray-50">
                <span className="text-sm font-medium truncate max-w-[200px]" title={name}>{name}</span>
                <Button variant="ghost" size="sm" asChild className="h-8 gap-1">
                  <a href={`/api/v1/reports/${encodeURIComponent(name)}`} download>
                    <Download className="w-4 h-4" />
                  </a>
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
