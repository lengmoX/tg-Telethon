import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Plus,
  Pencil,
  Trash2,
  RefreshCw,
  Loader2,
  AlertCircle,
  ArrowRight,
  Search,
  Shield
} from 'lucide-react';
import {
  getRules,
  createRule,
  updateRule,
  deleteRule,
  enableRule,
  disableRule,
  type Rule,
  type RuleCreate,
} from '@/api';

type RuleFormData = {
  name: string;
  source_chat: string;
  target_chat: string;
  mode: string;
  interval_min: number;
  filter_text: string;
  enabled: boolean;
};

const defaultFormData: RuleFormData = {
  name: '',
  source_chat: '',
  target_chat: '',
  mode: 'clone',
  interval_min: 30,
  filter_text: '',
  enabled: true,
};

export function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedRule, setSelectedRule] = useState<Rule | null>(null);
  const [formData, setFormData] = useState<RuleFormData>(defaultFormData);
  const [submitting, setSubmitting] = useState(false);

  const fetchRules = async () => {
    try {
      const data = await getRules();
      setRules(data);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load rules');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const filteredRules = rules.filter(rule =>
    rule.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    rule.source_chat.toLowerCase().includes(searchQuery.toLowerCase()) ||
    rule.target_chat.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreate = async () => {
    setSubmitting(true);
    try {
      const ruleData: RuleCreate = {
        name: formData.name,
        source_chat: formData.source_chat,
        target_chat: formData.target_chat,
        mode: formData.mode,
        interval_min: formData.interval_min,
        filter_text: formData.filter_text || undefined,
        enabled: formData.enabled,
      };
      await createRule(ruleData);
      await fetchRules();
      setCreateDialogOpen(false);
      setFormData(defaultFormData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create rule');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async () => {
    if (!selectedRule) return;
    setSubmitting(true);
    try {
      await updateRule(selectedRule.id, {
        name: formData.name,
        source_chat: formData.source_chat,
        target_chat: formData.target_chat,
        mode: formData.mode,
        interval_min: formData.interval_min,
        filter_text: formData.filter_text || undefined,
        enabled: formData.enabled,
      });
      await fetchRules();
      setEditDialogOpen(false);
      setSelectedRule(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update rule');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedRule) return;
    setSubmitting(true);
    try {
      await deleteRule(selectedRule.id);
      await fetchRules();
      setDeleteDialogOpen(false);
      setSelectedRule(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete rule');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggle = async (rule: Rule) => {
    try {
      if (rule.enabled) {
        await disableRule(rule.id);
      } else {
        await enableRule(rule.id);
      }
      await fetchRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle rule');
    }
  };

  const openEditDialog = (rule: Rule) => {
    setSelectedRule(rule);
    setFormData({
      name: rule.name,
      source_chat: rule.source_chat,
      target_chat: rule.target_chat,
      mode: rule.mode,
      interval_min: rule.interval_min,
      filter_text: rule.filter_text || '',
      enabled: rule.enabled,
    });
    setEditDialogOpen(true);
  };

  const openDeleteDialog = (rule: Rule) => {
    setSelectedRule(rule);
    setDeleteDialogOpen(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">规则管理</h2>
          <p className="text-sm text-muted-foreground">配置消息转发规则</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchRules}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            刷新
          </Button>
          <Button size="sm" onClick={() => { setFormData(defaultFormData); setCreateDialogOpen(true); }}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            新建规则
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="py-2">
          <AlertCircle className="h-3.5 w-3.5" />
          <AlertDescription className="text-xs ml-2">{error}</AlertDescription>
        </Alert>
      )}

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="搜索规则..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9 h-9 text-sm"
        />
      </div>

      {/* Rules Table */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10">
              <Shield className="h-4 w-4 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base">转发规则</CardTitle>
              <CardDescription className="text-xs">共 {rules.length} 条规则</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredRules.length === 0 ? (
            <div className="text-center py-8 text-sm text-muted-foreground">
              {searchQuery ? '未找到匹配的规则' : '暂无规则，点击"新建规则"开始'}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">名称</TableHead>
                    <TableHead className="text-xs">路由</TableHead>
                    <TableHead className="text-xs">模式</TableHead>
                    <TableHead className="text-xs">间隔</TableHead>
                    <TableHead className="text-xs">过滤</TableHead>
                    <TableHead className="text-xs w-16">启用</TableHead>
                    <TableHead className="text-xs w-20">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRules.map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell className="font-medium text-sm">{rule.name}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <span className="truncate max-w-[80px]" title={rule.source_chat}>
                            {rule.source_chat}
                          </span>
                          <ArrowRight className="h-3 w-3 shrink-0" />
                          <span className="truncate max-w-[80px]" title={rule.target_chat}>
                            {rule.target_chat}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={rule.mode === 'clone' ? 'default' : 'secondary'} className="text-[10px] px-1.5 py-0">
                          {rule.mode}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">{rule.interval_min}m</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {rule.filter_text ? (
                          <span className="truncate max-w-[60px] block" title={rule.filter_text}>
                            {rule.filter_text}
                          </span>
                        ) : '-'}
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={rule.enabled}
                          onCheckedChange={() => handleToggle(rule)}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEditDialog(rule)}>
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:text-destructive" onClick={() => openDeleteDialog(rule)}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base">新建规则</DialogTitle>
            <DialogDescription className="text-xs">
              创建新的消息转发规则
            </DialogDescription>
          </DialogHeader>
          <RuleForm formData={formData} setFormData={setFormData} />
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setCreateDialogOpen(false)}>
              取消
            </Button>
            <Button size="sm" onClick={handleCreate} disabled={submitting || !formData.name || !formData.source_chat || !formData.target_chat}>
              {submitting && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base">编辑规则</DialogTitle>
            <DialogDescription className="text-xs">
              修改规则 "{selectedRule?.name}"
            </DialogDescription>
          </DialogHeader>
          <RuleForm formData={formData} setFormData={setFormData} />
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setEditDialogOpen(false)}>
              取消
            </Button>
            <Button size="sm" onClick={handleUpdate} disabled={submitting}>
              {submitting && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">确认删除</DialogTitle>
            <DialogDescription className="text-xs">
              确定要删除规则 "{selectedRule?.name}" 吗？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setDeleteDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" size="sm" onClick={handleDelete} disabled={submitting}>
              {submitting && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Form Component
function RuleForm({ formData, setFormData }: {
  formData: RuleFormData;
  setFormData: (data: RuleFormData) => void;
}) {
  return (
    <div className="grid gap-4 py-4">
      <div className="grid gap-2">
        <Label htmlFor="name" className="text-xs">规则名称 *</Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="例如: news_forward"
          className="h-9 text-sm"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label htmlFor="source" className="text-xs">来源频道 *</Label>
          <Input
            id="source"
            value={formData.source_chat}
            onChange={(e) => setFormData({ ...formData, source_chat: e.target.value })}
            placeholder="@channel 或 ID"
            className="h-9 text-sm"
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="target" className="text-xs">目标频道 *</Label>
          <Input
            id="target"
            value={formData.target_chat}
            onChange={(e) => setFormData({ ...formData, target_chat: e.target.value })}
            placeholder="@channel 或 me"
            className="h-9 text-sm"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label htmlFor="mode" className="text-xs">转发模式</Label>
          <Select value={formData.mode} onValueChange={(v: string) => setFormData({ ...formData, mode: v })}>
            <SelectTrigger className="h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="clone">clone (复制转发)</SelectItem>
              <SelectItem value="direct">direct (直接转发)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="interval" className="text-xs">同步间隔 (分钟)</Label>
          <Input
            id="interval"
            type="number"
            value={formData.interval_min}
            onChange={(e) => setFormData({ ...formData, interval_min: parseInt(e.target.value) || 30 })}
            min={1}
            max={1440}
            className="h-9 text-sm"
          />
        </div>
      </div>
      <div className="grid gap-2">
        <Label htmlFor="filter" className="text-xs">过滤规则 (可选)</Label>
        <Input
          id="filter"
          value={formData.filter_text}
          onChange={(e) => setFormData({ ...formData, filter_text: e.target.value })}
          placeholder="例如: 广告;推广;!重要"
          className="h-9 text-sm"
        />
        <p className="text-[10px] text-muted-foreground">用分号分隔关键词，!开头表示排除</p>
      </div>
    </div>
  );
}
