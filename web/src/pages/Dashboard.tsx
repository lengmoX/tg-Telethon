import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Activity,
  RefreshCw,
  Play,
  Square,
  Loader2,
  AlertCircle,
  ArrowRight,
  Shield,
  MessageSquare
} from 'lucide-react';
import {
  getWatcherStatus,
  startWatcher,
  stopWatcher,
  getRules,
  getStates,
  enableRule,
  disableRule,
  type WatcherStatus,
  type Rule,
  type State,
} from '@/api';

interface DashboardProps {
  onLogout: () => void;
}

export function Dashboard({ onLogout: _onLogout }: DashboardProps) {
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

  const getStateForRule = (ruleId: number): State | undefined => {
    return states.find((s) => s.rule_id === ruleId);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const totalForwarded = states.reduce((sum, s) => sum + s.total_forwarded, 0);
  const enabledRules = rules.filter((r) => r.enabled).length;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">概览</h2>
          <p className="text-muted-foreground">监控转发服务状态和规则</p>
        </div>
        <Button variant="outline" onClick={fetchData}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="py-3">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-sm ml-2">{error}</AlertDescription>
        </Alert>
      )}

      {/* Stats Cards */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Watcher Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="font-medium text-muted-foreground">服务状态</CardTitle>
            <Activity className="h-6 w-6 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`h-3 w-3 rounded-full ${watcherStatus?.running ? 'bg-green-500' : 'bg-gray-300'}`} />
                <span className="text-3xl font-bold">
                  {watcherStatus?.running ? '运行中' : '已停止'}
                </span>
              </div>
              <Button
                variant={watcherStatus?.running ? 'outline' : 'default'}
                size="sm"
                onClick={handleStartStop}
                disabled={actionLoading}
              >
                {actionLoading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : watcherStatus?.running ? (
                  <>
                    <Square className="mr-1 h-3 w-3" />
                    停止
                  </>
                ) : (
                  <>
                    <Play className="mr-1 h-3 w-3" />
                    启动
                  </>
                )}
              </Button>
            </div>
            {watcherStatus?.pid && (
              <p className="text-sm text-muted-foreground mt-2">PID: {watcherStatus.pid}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="font-medium text-muted-foreground">转发规则</CardTitle>
            <Shield className="h-6 w-6 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{rules.length}</div>
            <p className="text-muted-foreground mt-1">
              {enabledRules} 个已启用
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="font-medium text-muted-foreground">已转发消息</CardTitle>
            <MessageSquare className="h-6 w-6 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{totalForwarded.toLocaleString()}</div>
            <p className="text-muted-foreground mt-1">总计</p>
          </CardContent>
        </Card>
      </div>

      {/* Rules Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">转发规则</CardTitle>
          <CardDescription>管理消息转发规则配置</CardDescription>
        </CardHeader>
        <CardContent>
          {rules.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              暂无规则，请通过 CLI 添加: <code className="bg-muted px-1.5 py-1 rounded text-sm">tgf rule add</code>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>路由</TableHead>
                    <TableHead>模式</TableHead>
                    <TableHead>间隔</TableHead>
                    <TableHead>已转发</TableHead>
                    <TableHead>最后同步</TableHead>
                    <TableHead className="text-xs w-16">启用</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rules.map((rule) => {
                    const state = getStateForRule(rule.id);
                    return (
                      <TableRow key={rule.id}>
                        <TableCell className="font-medium text-sm">{rule.name}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <span className="truncate max-w-[100px]" title={rule.source_chat}>
                              {rule.source_chat}
                            </span>
                            <ArrowRight className="h-3 w-3 shrink-0" />
                            <span className="truncate max-w-[100px]" title={rule.target_chat}>
                              {rule.target_chat}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={rule.mode === 'clone' ? 'default' : 'secondary'} className="text-xs px-2 py-0.5">
                            {rule.mode}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{rule.interval_min}m</TableCell>
                        <TableCell>{state?.total_forwarded || 0}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {state?.last_sync_at
                            ? new Date(state.last_sync_at).toLocaleString('zh-CN', {
                              month: 'numeric',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })
                            : '-'}
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
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
