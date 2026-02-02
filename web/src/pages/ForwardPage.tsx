/**
 * Forward Page - One-time Message Forwarding
 * 
 * Features:
 * - Input multiple message links (one per line)
 * - Select destination chat
 * - Forward with clone or direct mode
 * - Show results with success/failure status
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  ArrowRight,
  Send,
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  RefreshCw,
} from 'lucide-react';
import {
  forwardMessages,
  getChats,
  type ForwardRequest,
  type ForwardResponse,
  type ChatInfo,
} from '@/api';
import { toast } from 'sonner';


export function ForwardPage() {
  // State
  const [links, setLinks] = useState('');
  const [dest, setDest] = useState('me');
  const [customDest, setCustomDest] = useState('');
  const [mode, setMode] = useState<'clone' | 'direct'>('clone');
  const [detectAlbum, setDetectAlbum] = useState(true);

  const [chats, setChats] = useState<ChatInfo[]>([]);

  const [forwarding, setForwarding] = useState(false);
  const [result, setResult] = useState<ForwardResponse | null>(null);
  const [error, setError] = useState('');

  // Load chats for destination selection
  const fetchChats = async () => {
    try {
      const res = await getChats(100, 'all');
      setChats(res.chats);
    } catch (err) {
      console.error('Failed to load chats:', err);
    }
  };

  useEffect(() => {
    fetchChats();
  }, []);

  // Parse links from textarea
  const parseLinks = (): string[] => {
    return links
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0 && line.startsWith('http'));
  };

  // Get destination value
  const getDestination = (): string => {
    if (dest === 'custom') {
      return customDest.trim() || 'me';
    }
    return dest;
  };

  // Execute forward
  const handleForward = async () => {
    const linkList = parseLinks();
    if (linkList.length === 0) {
      setError('请输入至少一个有效的消息链接');
      return;
    }

    setForwarding(true);
    setResult(null);
    setError('');

    try {
      const request: ForwardRequest = {
        links: linkList,
        dest: getDestination(),
        mode: mode,
        detect_album: detectAlbum,
      };

      const res = await forwardMessages(request);
      setResult(res);

      if (res.success) {
        toast.success(`转发完成`, {
          description: `成功: ${res.succeeded}, 失败: ${res.failed}`,
        });
        setLinks('');
      } else {
        toast.error(`转发完成，但有错误`, {
          description: `成功: ${res.succeeded}, 失败: ${res.failed}`,
        });
        // Don't clear links if failed, user might want to retry
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '转发失败';
      setError(msg);
      toast.error(msg);
    } finally {
      setForwarding(false);
    }
  };

  // Get link count
  const linkCount = parseLinks().length;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-semibold tracking-tight">消息转发</h2>
        <p className="text-muted-foreground">批量转发消息到目标对话</p>
      </div>

      {/* Main Card */}
      <Card>
        <CardHeader>
          <CardTitle>转发设置</CardTitle>
          <CardDescription>输入消息链接，选择目标对话</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Source and Destination Row */}
          <div className="flex items-center gap-4">
            {/* Source indicator */}
            <div className="flex-1">
              <div className="flex items-center gap-2 p-4 border rounded-lg bg-muted/30">
                <span className="text-sm font-medium">来源</span>
                <Badge variant="secondary">{linkCount} 条链接</Badge>
              </div>
            </div>

            {/* Arrow */}
            <ArrowRight className="h-6 w-6 text-muted-foreground flex-shrink-0" />

            {/* Destination selector */}
            <div className="flex-1">
              <Select value={dest} onValueChange={setDest}>
                <SelectTrigger>
                  <SelectValue placeholder="选择目标对话" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="me">📌 Saved Messages (自己)</SelectItem>
                  <SelectItem value="custom">✏️ 自定义输入...</SelectItem>
                  {chats.slice(0, 20).map((chat) => (
                    <SelectItem key={chat.id} value={chat.id.toString()}>
                      {chat.type === 'channel' ? '📢' : chat.type === 'group' ? '👥' : '👤'}{' '}
                      {chat.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Custom destination input */}
          {dest === 'custom' && (
            <div className="space-y-2">
              <Label>自定义目标</Label>
              <Input
                placeholder="输入 @username 或 chat_id"
                value={customDest}
                onChange={(e) => setCustomDest(e.target.value)}
              />
            </div>
          )}

          {/* Links input */}
          <div className="space-y-2">
            <Label>需要转发的链接（一行一个）</Label>
            <Textarea
              placeholder={`https://t.me/channel/123\nhttps://t.me/channel/124\nhttps://t.me/c/1234567890/456`}
              value={links}
              onChange={(e) => setLinks(e.target.value)}
              className="min-h-[200px] font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              支持公开链接 (https://t.me/channel/123) 和私有链接 (https://t.me/c/xxx/123)
            </p>
          </div>

          {/* Options */}
          <div className="flex flex-wrap gap-6">
            {/* Mode */}
            <div className="space-y-2">
              <Label>转发模式</Label>
              <Select value={mode} onValueChange={(v) => setMode(v as 'clone' | 'direct')}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="clone">克隆 (无转发头)</SelectItem>
                  <SelectItem value="direct">直转 (有转发头)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Album detection */}
            <div className="flex items-center space-x-2">
              <Switch
                id="detect-album"
                checked={detectAlbum}
                onCheckedChange={setDetectAlbum}
              />
              <Label htmlFor="detect-album">自动检测相册</Label>
            </div>
          </div>

          {/* Error display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="ml-2">{error}</AlertDescription>
            </Alert>
          )}

          {/* Forward button */}
          <Button
            onClick={handleForward}
            disabled={forwarding || linkCount === 0}
            className="w-full"
            size="lg"
          >
            {forwarding ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                转发中...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                开始转发 ({linkCount} 条)
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {result.success ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <AlertCircle className="h-5 w-5 text-yellow-500" />
              )}
              转发结果
            </CardTitle>
            <CardDescription>
              共 {result.total} 条，成功 {result.succeeded} 条，失败 {result.failed} 条
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {result.results.map((item, index) => (
                <div
                  key={index}
                  className={`flex items-center justify-between p-2 rounded border ${item.success ? 'bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-900' : 'bg-red-50 border-red-200 dark:bg-red-950/20 dark:border-red-900'
                    }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {item.success ? (
                      <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                    )}
                    <span className="text-sm font-mono truncate">{item.link}</span>
                  </div>
                  {item.error && (
                    <span className="text-xs text-red-500 flex-shrink-0 ml-2">{item.error}</span>
                  )}
                </div>
              ))}
            </div>

            {/* Reset button */}
            <Button
              variant="outline"
              onClick={() => {
                setResult(null);
                setLinks('');
              }}
              className="mt-4"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              重新开始
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
