/**
 * Chats Page - Dialog List and Message Export
 * 
 * Features:
 * - List all Telegram dialogs (chats, groups, channels)
 * - Filter by type
 * - Export messages from selected chat
 * - Download exported files
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  MessageSquare,
  Users,
  Radio,
  RefreshCw,
  Download,
  FileJson,
  Loader2,
  AlertCircle,
  Search,
  User,
} from 'lucide-react';
import {
  getChats,
  exportChat,
  listExports,
  getExportDownloadUrl,
  type ChatInfo,
  type ExportRequest,
  type ExportFile,
} from '@/api';


export function ChatsPage() {
  // State
  const [chats, setChats] = useState<ChatInfo[]>([]);
  const [filteredChats, setFilteredChats] = useState<ChatInfo[]>([]);
  const [exports, setExports] = useState<ExportFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');

  // Export dialog state
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [selectedChat, setSelectedChat] = useState<ChatInfo | null>(null);
  const [exportOptions, setExportOptions] = useState<ExportRequest>({
    chat: '',
    limit: 1000,
    msg_type: 'all',
    with_content: false,
  });
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<{ success: boolean; message: string } | null>(null);

  // Fetch data
  const fetchData = async () => {
    setLoading(true);
    try {
      const [chatsRes, exportsRes] = await Promise.all([
        getChats(200, 'all'),
        listExports(),
      ]);
      setChats(chatsRes.chats);
      setFilteredChats(chatsRes.chats);
      setExports(exportsRes.exports);
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

  // Filter chats
  useEffect(() => {
    let result = chats;

    // Type filter
    if (typeFilter !== 'all') {
      result = result.filter(c => c.type === typeFilter);
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(c =>
        c.name.toLowerCase().includes(query) ||
        (c.username && c.username.toLowerCase().includes(query)) ||
        c.id.toString().includes(query)
      );
    }

    setFilteredChats(result);
  }, [chats, typeFilter, searchQuery]);

  // Open export dialog
  const handleExportClick = (chat: ChatInfo) => {
    setSelectedChat(chat);
    setExportOptions({
      chat: chat.id.toString(),
      limit: 1000,
      msg_type: 'all',
      with_content: false,
    });
    setExportResult(null);
    setExportDialogOpen(true);
  };

  // Execute export
  const handleExport = async () => {
    if (!selectedChat) return;

    setExporting(true);
    setExportResult(null);

    try {
      const result = await exportChat(exportOptions);
      setExportResult({
        success: true,
        message: `导出成功！共 ${result.message_count} 条消息，文件: ${result.filename}`,
      });
      // Refresh exports list
      const exportsRes = await listExports();
      setExports(exportsRes.exports);
    } catch (err) {
      setExportResult({
        success: false,
        message: err instanceof Error ? err.message : '导出失败',
      });
    } finally {
      setExporting(false);
    }
  };

  // Download export file
  const handleDownload = (filename: string) => {
    window.open(getExportDownloadUrl(filename), '_blank');
  };

  // Get type icon
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'channel': return <Radio className="h-4 w-4" />;
      case 'group': return <Users className="h-4 w-4" />;
      case 'user': return <User className="h-4 w-4" />;
      default: return <MessageSquare className="h-4 w-4" />;
    }
  };

  // Get type badge variant
  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'channel': return <Badge variant="default">{type}</Badge>;
      case 'group': return <Badge variant="secondary">{type}</Badge>;
      case 'user': return <Badge variant="outline">{type}</Badge>;
      default: return <Badge variant="outline">{type}</Badge>;
    }
  };

  // Format file size
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">对话管理</h2>
          <p className="text-muted-foreground">查看对话列表并导出消息</p>
        </div>
        <Button variant="outline" onClick={fetchData}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="ml-2">{error}</AlertDescription>
        </Alert>
      )}

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索对话..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="类型筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="channel">频道</SelectItem>
            <SelectItem value="group">群组</SelectItem>
            <SelectItem value="user">私聊</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Chats Table */}
      <Card>
        <CardHeader>
          <CardTitle>对话列表</CardTitle>
          <CardDescription>共 {filteredChats.length} 个对话</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>名称</TableHead>
                  <TableHead>用户名</TableHead>
                  <TableHead className="text-right">未读</TableHead>
                  <TableHead className="w-24">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredChats.map((chat) => (
                  <TableRow key={chat.id}>
                    <TableCell className="font-mono text-muted-foreground">
                      {chat.id}
                    </TableCell>
                    <TableCell>{getTypeBadge(chat.type)}</TableCell>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        {getTypeIcon(chat.type)}
                        <span className="truncate max-w-[200px]">{chat.name || '[无名称]'}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {chat.username ? `@${chat.username}` : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      {chat.unread_count > 0 && (
                        <Badge variant="secondary">{chat.unread_count}</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleExportClick(chat)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Exports List */}
      {exports.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>已导出文件</CardTitle>
            <CardDescription>点击下载导出的 JSON 文件</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {exports.map((file) => (
                <div
                  key={file.filename}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent cursor-pointer"
                  onClick={() => handleDownload(file.filename)}
                >
                  <div className="flex items-center gap-3">
                    <FileJson className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{file.filename}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatSize(file.size)} · {new Date(file.created_at).toLocaleString('zh-CN')}
                      </p>
                    </div>
                  </div>
                  <Download className="h-4 w-4 text-muted-foreground" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Export Dialog */}
      <Dialog open={exportDialogOpen} onOpenChange={setExportDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>导出消息</DialogTitle>
            <DialogDescription>
              从 {selectedChat?.name || '选中的对话'} 导出消息到 JSON 文件
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Limit */}
            <div className="space-y-2">
              <Label>消息数量限制</Label>
              <Input
                type="number"
                value={exportOptions.limit || ''}
                onChange={(e) => setExportOptions({
                  ...exportOptions,
                  limit: e.target.value ? parseInt(e.target.value) : undefined,
                })}
                placeholder="不限制"
              />
            </div>

            {/* Message Type */}
            <div className="space-y-2">
              <Label>消息类型</Label>
              <Select
                value={exportOptions.msg_type}
                onValueChange={(v) => setExportOptions({
                  ...exportOptions,
                  msg_type: v as ExportRequest['msg_type'],
                })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部消息</SelectItem>
                  <SelectItem value="media">仅媒体</SelectItem>
                  <SelectItem value="text">仅文本</SelectItem>
                  <SelectItem value="photo">仅图片</SelectItem>
                  <SelectItem value="video">仅视频</SelectItem>
                  <SelectItem value="document">仅文档</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* With Content */}
            <div className="flex items-center justify-between">
              <div>
                <Label>包含消息内容</Label>
                <p className="text-sm text-muted-foreground">导出消息文本内容</p>
              </div>
              <Switch
                checked={exportOptions.with_content}
                onCheckedChange={(v) => setExportOptions({
                  ...exportOptions,
                  with_content: v,
                })}
              />
            </div>

            {/* Result */}
            {exportResult && (
              <Alert variant={exportResult.success ? 'default' : 'destructive'}>
                <AlertDescription>{exportResult.message}</AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setExportDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleExport} disabled={exporting}>
              {exporting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  导出中...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  开始导出
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
