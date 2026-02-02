/**
 * Chats Page - Dialog List and Message Export
 * 
 * Features:
 * - List all Telegram dialogs (chats, groups, channels)
 * - Click to copy ID, name, or username
 * - Export messages and display links inline
 * - Download links as text file
 */

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
  Loader2,
  AlertCircle,
  Search,
  User,
  Copy,
  Check,
} from 'lucide-react';
import {
  getChats,
  exportChat,
  type ChatInfo,
  type ExportRequest,
  type ExportResponse,
} from '@/api';


// Toast-like copy feedback
function useCopyFeedback() {
  const [copiedValue, setCopiedValue] = useState<string | null>(null);

  const copy = useCallback(async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedValue(value);
      setTimeout(() => setCopiedValue(null), 1500);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, []);

  return { copiedValue, copy };
}


export function ChatsPage() {
  // State
  const [chats, setChats] = useState<ChatInfo[]>([]);
  const [filteredChats, setFilteredChats] = useState<ChatInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');

  // Copy functionality
  const { copiedValue, copy } = useCopyFeedback();

  // Export dialog state
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [selectedChat, setSelectedChat] = useState<ChatInfo | null>(null);
  const [exportOptions, setExportOptions] = useState<ExportRequest>({
    chat: '',
    limit: 100,
    msg_type: 'all',
    with_content: false,
  });
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<ExportResponse | null>(null);

  // Fetch data
  const fetchData = async () => {
    setLoading(true);
    try {
      const chatsRes = await getChats(200, 'all');
      setChats(chatsRes.chats);
      setFilteredChats(chatsRes.chats);
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
      limit: 100,
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
      setExportResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : '导出失败');
    } finally {
      setExporting(false);
    }
  };

  // Download links as text file
  const handleDownloadLinks = () => {
    if (!exportResult) return;

    const content = exportResult.links.join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${exportResult.chat_name}_links.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Copy all links
  const handleCopyAllLinks = async () => {
    if (!exportResult) return;
    const content = exportResult.links.join('\n');
    await copy(content);
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

  // Clickable cell with copy
  const CopyableCell = ({ value, className = '' }: { value: string; className?: string }) => (
    <button
      onClick={() => copy(value)}
      className={`text-left hover:bg-accent px-2 py-1 -mx-2 -my-1 rounded transition-colors cursor-pointer flex items-center gap-1 ${className}`}
      title="点击复制"
    >
      <span className="truncate">{value}</span>
      {copiedValue === value ? (
        <Check className="h-3 w-3 text-green-500 flex-shrink-0" />
      ) : (
        <Copy className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 flex-shrink-0" />
      )}
    </button>
  );

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
          <p className="text-muted-foreground">查看对话列表并导出消息链接</p>
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
          <CardDescription>共 {filteredChats.length} 个对话 · 点击 ID/名称/用户名 可复制</CardDescription>
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
                  <TableRow key={chat.id} className="group">
                    <TableCell className="font-mono text-muted-foreground">
                      <CopyableCell value={chat.id.toString()} />
                    </TableCell>
                    <TableCell>{getTypeBadge(chat.type)}</TableCell>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        {getTypeIcon(chat.type)}
                        <CopyableCell
                          value={chat.name || '[无名称]'}
                          className="max-w-[200px]"
                        />
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {chat.username ? (
                        <CopyableCell value={`@${chat.username}`} />
                      ) : (
                        '-'
                      )}
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
                        title="导出消息链接"
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

      {/* Export Dialog */}
      <Dialog open={exportDialogOpen} onOpenChange={setExportDialogOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>导出消息链接</DialogTitle>
            <DialogDescription>
              从 {selectedChat?.name || '选中的对话'} 导出消息链接
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4 flex-1 overflow-hidden flex flex-col">
            {/* Export Options - only show before export */}
            {!exportResult && (
              <>
                {/* Limit */}
                <div className="space-y-2">
                  <Label>消息数量</Label>
                  <Input
                    type="number"
                    value={exportOptions.limit || ''}
                    onChange={(e) => setExportOptions({
                      ...exportOptions,
                      limit: e.target.value ? parseInt(e.target.value) : undefined,
                    })}
                    placeholder="100"
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
              </>
            )}

            {/* Export Result */}
            {exportResult && (
              <div className="flex-1 overflow-hidden flex flex-col space-y-3">
                <div className="flex items-center justify-between">
                  <Alert className="flex-1">
                    <AlertDescription>
                      导出成功！共 {exportResult.message_count} 条消息
                    </AlertDescription>
                  </Alert>
                </div>

                {/* Links display */}
                <div className="flex-1 overflow-hidden">
                  <Textarea
                    readOnly
                    value={exportResult.links.join('\n')}
                    className="h-full min-h-[200px] max-h-[400px] font-mono text-sm resize-none overflow-y-scroll"
                    placeholder="消息链接将显示在这里..."
                  />
                </div>

                {/* Action buttons */}
                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleCopyAllLinks} className="flex-1">
                    <Copy className="mr-2 h-4 w-4" />
                    复制全部链接
                  </Button>
                  <Button onClick={handleDownloadLinks} className="flex-1">
                    <Download className="mr-2 h-4 w-4" />
                    下载 TXT 文件
                  </Button>
                </div>
              </div>
            )}

            {/* Error display */}
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter>
            {!exportResult ? (
              <>
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
              </>
            ) : (
              <Button variant="outline" onClick={() => {
                setExportResult(null);
                setExportDialogOpen(false);
              }}>
                关闭
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
