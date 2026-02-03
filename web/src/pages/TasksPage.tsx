
import { useState, useEffect, type ChangeEvent } from 'react';
import {
  getTasks,
  retryTask,
  cancelTask,
  deleteTask,
  getUploadSettings,
  updateUploadSettings,
  type Task
} from '@/api/client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import {
  Loader2,
  RefreshCw,
  Trash2,
  XOctagon
} from 'lucide-react';
import { toast } from 'sonner';

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [settingsLoading, setSettingsLoading] = useState(true);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsForm, setSettingsForm] = useState({
    threads: '',
    limit: '',
    part_size_kb: ''
  });

  const fetchTasks = async () => {
    try {
      const response = await getTasks();
      const responseTasks = (response as { tasks?: Task[] }).tasks;
      const normalizedTasks = Array.isArray(responseTasks)
        ? responseTasks
        : (Array.isArray(response) ? response : []);
      setTasks(normalizedTasks);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
      setTasks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchUploadConfig = async () => {
    try {
      const settings = await getUploadSettings();
      setSettingsForm({
        threads: String(settings.threads),
        limit: String(settings.limit),
        part_size_kb: String(settings.part_size_kb)
      });
    } catch (error) {
      console.error('Failed to fetch upload settings:', error);
      toast.error('Failed to load upload settings');
    } finally {
      setSettingsLoading(false);
    }
  };

  useEffect(() => {
    fetchUploadConfig();
  }, []);

  const handleRetry = async (taskId: number) => {
    try {
      await retryTask(taskId);
      toast.success('Task retried');
      fetchTasks();
    } catch (error) {
      toast.error('Failed to retry task');
    }
  };

  const handleCancel = async (taskId: number) => {
    try {
      await cancelTask(taskId);
      toast.success('Task cancelled');
      fetchTasks();
    } catch (error) {
      toast.error('Failed to cancel task');
    }
  };

  const handleDelete = async (taskId: number) => {
    try {
      await deleteTask(taskId);
      toast.success('Task deleted');
      fetchTasks();
    } catch (error) {
      toast.error('Failed to delete task');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-500';
      case 'failed': return 'text-red-500';
      case 'running': return 'text-blue-500';
      case 'cancelled': return 'text-gray-500';
      default: return 'text-yellow-500';
    }
  };

  const parseDetails = (details?: string | null | Record<string, unknown>) => {
    if (!details) return {};
    if (typeof details === 'object') return details;
    try {
      return JSON.parse(details);
    } catch {
      return {};
    }
  };

  const normalizeProgress = (value: unknown) => {
    const numeric = typeof value === 'number' ? value : Number(value);
    if (!Number.isFinite(numeric)) return 0;
    return Math.min(Math.max(numeric, 0), 100);
  };

  const updateSettingsField = (field: 'threads' | 'limit' | 'part_size_kb') => (
    event: ChangeEvent<HTMLInputElement>
  ) => {
    setSettingsForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const handleSaveSettings = async () => {
    const threads = Number.parseInt(settingsForm.threads, 10);
    const limit = Number.parseInt(settingsForm.limit, 10);
    const partSize = Number.parseInt(settingsForm.part_size_kb, 10);

    if (!Number.isFinite(threads) || !Number.isFinite(limit) || !Number.isFinite(partSize)) {
      toast.error('All upload settings must be valid numbers');
      return;
    }

    setSettingsSaving(true);
    try {
      const updated = await updateUploadSettings({
        threads,
        limit,
        part_size_kb: partSize
      });
      setSettingsForm({
        threads: String(updated.threads),
        limit: String(updated.limit),
        part_size_kb: String(updated.part_size_kb)
      });
      toast.success('Upload settings updated');
    } catch (error) {
      console.error('Failed to update upload settings:', error);
      toast.error('Failed to update upload settings');
    } finally {
      setSettingsSaving(false);
    }
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-semibold">上传设置</CardTitle>
          <CardDescription>
            调整大文件上传速度，数值越高占用带宽越多。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {settingsLoading ? (
            <div className="flex justify-center p-4">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="upload-threads">单任务线程数</Label>
                  <Input
                    id="upload-threads"
                    type="number"
                    min={1}
                    max={32}
                    value={settingsForm.threads}
                    onChange={updateSettingsField('threads')}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="upload-limit">并发上传数</Label>
                  <Input
                    id="upload-limit"
                    type="number"
                    min={1}
                    max={8}
                    value={settingsForm.limit}
                    onChange={updateSettingsField('limit')}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="upload-part-size">分片大小 (KB)</Label>
                  <Input
                    id="upload-part-size"
                    type="number"
                    min={1}
                    max={512}
                    value={settingsForm.part_size_kb}
                    onChange={updateSettingsField('part_size_kb')}
                  />
                </div>
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>线程数作用于单任务；并发数限制同时上传的任务数。</span>
                <span>分片大小上限：512 KB</span>
              </div>
              <div className="flex justify-end">
                <Button onClick={handleSaveSettings} disabled={settingsSaving}>
                  {settingsSaving ? '保存中...' : '保存设置'}
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold flex items-center gap-2">
            <RefreshCw className="w-6 h-6" />
            任务管理
          </CardTitle>
          <CardDescription>
            管理后台任务（M3U8 下载等）
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading && tasks.length === 0 ? (
            <div className="flex justify-center p-8">
              <Loader2 className="w-8 h-8 animate-spin" />
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>类型</TableHead>
                    <TableHead>详情</TableHead>
                    <TableHead>进度</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tasks.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center h-24 text-muted-foreground">
                        暂无任务
                      </TableCell>
                    </TableRow>
                  ) : (
                    tasks.map((task) => {
                      const details = parseDetails(task.details);
                      const progressValue = normalizeProgress(task.progress);
                      const stageLabel = task.stage && task.stage.trim() ? task.stage : 'unknown';
                      return (
                        <TableRow key={task.id}>
                          <TableCell className="font-medium uppercase">{task.type}</TableCell>
                          <TableCell className="max-w-[300px]">
                            <div className="flex flex-col gap-1">
                              <span className="font-semibold truncate">{details.filename || '未知文件'}</span>
                              <span className="text-xs text-muted-foreground truncate">{details.url}</span>
                              {details.dest && <span className="text-xs text-muted-foreground">目标: {details.dest}</span>}
                            </div>
                          </TableCell>
                          <TableCell className="w-[200px]">
                            <div className="space-y-1">
                              <Progress value={progressValue} className="h-2" />
                              <div className="flex justify-between text-xs text-muted-foreground">
                                <span>{stageLabel}</span>
                                <span>{progressValue.toFixed(1)}%</span>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className={`flex items-center gap-1 font-medium ${getStatusColor(task.status)}`}>
                              {task.status}
                            </div>
                            {task.error && (
                              <div className="text-xs text-red-500 max-w-[200px] truncate" title={task.error}>
                                {task.error}
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2">
                              {(task.status === 'running' || task.status === 'pending') && (
                                <Button variant="ghost" size="icon" onClick={() => handleCancel(task.id)} title="取消">
                                  <XOctagon className="w-4 h-4 text-orange-500" />
                                </Button>
                              )}
                              {(task.status === 'failed' || task.status === 'cancelled') && (
                                <Button variant="ghost" size="icon" onClick={() => handleRetry(task.id)} title="重试">
                                  <RefreshCw className="w-4 h-4 text-blue-500" />
                                </Button>
                              )}
                              <Button variant="ghost" size="icon" onClick={() => handleDelete(task.id)} title="删除">
                                <Trash2 className="w-4 h-4 text-red-500" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
