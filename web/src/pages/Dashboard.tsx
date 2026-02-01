import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  getWatcherStatus,
  startWatcher,
  stopWatcher,
  getRules,
  getStates,
  enableRule,
  disableRule,
  clearToken,
  type WatcherStatus,
  type Rule,
  type State,
} from '@/api';

interface DashboardProps {
  onLogout: () => void;
}

export function Dashboard({ onLogout }: DashboardProps) {
  const [watcherStatus, setWatcherStatus] = useState<WatcherStatus | null>(null);
  const [rules, setRules] = useState<Rule[]>([]);
  const [states, setStates] = useState<State[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchData = async () => {
    try {
      const [status, rulesData, statesData] = await Promise.all([
        getWatcherStatus(),
        getRules(),
        getStates(),
      ]);
      setWatcherStatus(status);
      setRules(rulesData);
      setStates(statesData);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Auto refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleStartStop = async () => {
    setActionLoading(true);
    try {
      if (watcherStatus?.running) {
        await stopWatcher();
      } else {
        await startWatcher();
      }
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleRule = async (rule: Rule) => {
    try {
      if (rule.enabled) {
        await disableRule(rule.id);
      } else {
        await enableRule(rule.id);
      }
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle rule');
    }
  };

  const handleLogout = () => {
    clearToken();
    onLogout();
  };

  const getStateForRule = (ruleId: number): State | undefined => {
    return states.find((s) => s.rule_id === ruleId);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">加载中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            TGF 管理面板
          </h1>
          <Button variant="ghost" onClick={handleLogout}>
            退出登录
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 space-y-6">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Watcher Status */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">监听器状态</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-3 h-3 rounded-full ${watcherStatus?.running ? 'bg-green-500' : 'bg-gray-300'
                      }`}
                  />
                  <span className="text-2xl font-bold">
                    {watcherStatus?.running ? '运行中' : '已停止'}
                  </span>
                </div>
                <Button
                  variant={watcherStatus?.running ? 'destructive' : 'default'}
                  onClick={handleStartStop}
                  disabled={actionLoading}
                >
                  {actionLoading ? '...' : watcherStatus?.running ? '停止' : '启动'}
                </Button>
              </div>
              {watcherStatus?.pid && (
                <p className="text-xs text-gray-500 mt-2">PID: {watcherStatus.pid}</p>
              )}
            </CardContent>
          </Card>

          {/* Rules Count */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">规则数量</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{rules.length}</div>
              <p className="text-xs text-gray-500">
                {rules.filter((r) => r.enabled).length} 个启用
              </p>
            </CardContent>
          </Card>

          {/* Total Forwarded */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">已转发消息</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {states.reduce((sum, s) => sum + s.total_forwarded, 0)}
              </div>
              <p className="text-xs text-gray-500">总计</p>
            </CardContent>
          </Card>
        </div>

        {/* Rules Table */}
        <Card>
          <CardHeader>
            <CardTitle>转发规则</CardTitle>
            <CardDescription>管理消息转发规则</CardDescription>
          </CardHeader>
          <CardContent>
            {rules.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                暂无规则，请通过 CLI 添加: tgf rule add --name xxx -s source -t target
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>来源 → 目标</TableHead>
                    <TableHead>模式</TableHead>
                    <TableHead>间隔</TableHead>
                    <TableHead>已转发</TableHead>
                    <TableHead>最后同步</TableHead>
                    <TableHead>状态</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rules.map((rule) => {
                    const state = getStateForRule(rule.id);
                    return (
                      <TableRow key={rule.id}>
                        <TableCell className="font-medium">{rule.name}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {rule.source_chat} → {rule.target_chat}
                        </TableCell>
                        <TableCell>
                          <Badge variant={rule.mode === 'clone' ? 'default' : 'secondary'}>
                            {rule.mode}
                          </Badge>
                        </TableCell>
                        <TableCell>{rule.interval_min} 分钟</TableCell>
                        <TableCell>{state?.total_forwarded || 0}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {state?.last_sync_at
                            ? new Date(state.last_sync_at).toLocaleString('zh-CN')
                            : '从未'}
                        </TableCell>
                        <TableCell>
                          <Switch
                            checked={rule.enabled}
                            onCheckedChange={() => handleToggleRule(rule)}
                          />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
