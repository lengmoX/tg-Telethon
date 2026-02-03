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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  Video
} from 'lucide-react';
import {
  forwardMessages,
  forwardM3u8,
  getChats,
  type ForwardRequest,
  type ForwardResponse,
  type ChatInfo,
  type M3u8ForwardRequest,
  type M3u8ForwardResponse
} from '@/api';
import { toast } from 'sonner';


export function ForwardPage() {
  // Common State
  const [chats, setChats] = useState<ChatInfo[]>([]);
  const [activeTab, setActiveTab] = useState("message");

  // Message Forward State
  const [links, setLinks] = useState('');
  const [dest, setDest] = useState('me');
  const [customDest, setCustomDest] = useState('');
  const [mode, setMode] = useState<'clone' | 'direct'>('clone');
  const [detectAlbum, setDetectAlbum] = useState(true);
  const [forwarding, setForwarding] = useState(false);
  const [result, setResult] = useState<ForwardResponse | null>(null);
  const [error, setError] = useState('');

  // M3U8 State
  const [m3u8Url, setM3u8Url] = useState('');
  const [m3u8Filename, setM3u8Filename] = useState('');
  const [m3u8Caption, setM3u8Caption] = useState('');
  const [m3u8Dest, setM3u8Dest] = useState('me');
  const [m3u8CustomDest, setM3u8CustomDest] = useState('');
  const [m3u8Forwarding, setM3u8Forwarding] = useState(false);
  const [m3u8Result, setM3u8Result] = useState<M3u8ForwardResponse | null>(null);

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

  // --- Message Forwarding Logic ---

  // Parse links from textarea
  const parseLinks = (): string[] => {
    return links
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0 && line.startsWith('http'));
  };

  // Get destination value
  const getDestination = (d: string, custom: string): string => {
    if (d === 'custom') {
      return custom.trim() || 'me';
    }
    return d;
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
        dest: getDestination(dest, customDest),
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
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '转发失败';
      setError(msg);
      toast.error(msg);
    } finally {
      setForwarding(false);
    }
  };

  // --- M3U8 Logic ---

  const handleM3u8Forward = async () => {
    if (!m3u8Url.startsWith('http')) {
      toast.error('请输入有效的 HTTP/HTTPS URL');
      return;
    }

    setM3u8Forwarding(true);
    setM3u8Result(null);

    try {
      const destValue = getDestination(m3u8Dest, m3u8CustomDest);
      const req: M3u8ForwardRequest = {
        url: m3u8Url.trim(),
        dest: destValue,
        filename: m3u8Filename.trim() || undefined,
        caption: m3u8Caption.trim() || undefined
      };

      const res = await forwardM3u8(req);
      setM3u8Result(res);

      if (res.success) {
        toast.success('M3U8 任务已提交', {
          description: '下载和转发已在后台开始，请到任务管理页面查看进度。',
          action: {
            label: '查看任务',
            onClick: () => window.location.href = '/tasks'
          }
        });
        setM3u8Url('');
        setM3u8Filename('');
        setM3u8Caption('');
      } else {
        toast.error(`失败: ${res.error}`);
      }

    } catch (err) {
      const msg = err instanceof Error ? err.message : '操作失败';
      toast.error(msg);
    } finally {
      setM3u8Forwarding(false);
    }
  };

  // Get link count
  const linkCount = parseLinks().length;

  // Reusable Destination Selector
  const DestinationSelector = ({
    val,
    setVal,
    customVal,
    setCustomVal
  }: {
    val: string,
    setVal: (v: string) => void,
    customVal: string,
    setCustomVal: (v: string) => void
  }) => (
    <div className="space-y-4">
      <Label>目标对话</Label>
      <div className="flex gap-4">
        <div className="flex-1">
          <Select value={val} onValueChange={setVal}>
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

      {val === 'custom' && (
        <div className="space-y-2">
          <Input
            placeholder="输入 @username 或 chat_id"
            value={customVal}
            onChange={(e) => setCustomVal(e.target.value)}
          />
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-semibold tracking-tight">消息转发</h2>
        <p className="text-muted-foreground">批量转发消息或下载媒体到目标对话</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
          <TabsTrigger value="message">普通消息转发</TabsTrigger>
          <TabsTrigger value="m3u8">M3U8 下载转发</TabsTrigger>
        </TabsList>

        {/* ============ Message Forward Tab ============ */}
        <TabsContent value="message">
          <Card>
            <CardHeader>
              <CardTitle>普通消息</CardTitle>
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
                  <DestinationSelector
                    val={dest}
                    setVal={setDest}
                    customVal={customDest}
                    setCustomVal={setCustomDest}
                  />
                </div>
              </div>

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
                <div className="flex items-center space-x-2 pt-8">
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

              {/* Results */}
              {result && (
                <div className="mt-8 border-t pt-6">
                  <div className="flex items-center gap-2 mb-4">
                    {result.success ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-yellow-500" />
                    )}
                    <h3 className="font-semibold">转发结果</h3>
                    <span className="text-sm text-muted-foreground ml-auto">
                      成功 {result.succeeded} / 失败 {result.failed}
                    </span>
                  </div>

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

                  <Button
                    variant="outline"
                    onClick={() => {
                      setResult(null);
                      setLinks('');
                    }}
                    className="mt-4 w-full"
                  >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    清空结果
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ============ M3U8 Tab ============ */}
        <TabsContent value="m3u8">
          <Card>
            <CardHeader>
              <CardTitle>M3U8 视频下载</CardTitle>
              <CardDescription>输入 M3U8 链接，下载并上传到 Telegram</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label>M3U8 链接 URL</Label>
                <Input
                  placeholder="https://example.com/video/playlist.m3u8"
                  value={m3u8Url}
                  onChange={e => setM3u8Url(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>文件名 (可选)</Label>
                  <Input
                    placeholder="my_video"
                    value={m3u8Filename}
                    onChange={e => setM3u8Filename(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">不带后缀名</p>
                </div>
                <div className="space-y-2">
                  <Label>标题 Caption (可选)</Label>
                  <Input
                    placeholder="视频描述..."
                    value={m3u8Caption}
                    onChange={e => setM3u8Caption(e.target.value)}
                  />
                </div>
              </div>

              <DestinationSelector
                val={m3u8Dest}
                setVal={setM3u8Dest}
                customVal={m3u8CustomDest}
                setCustomVal={setM3u8CustomDest}
              />

              {/* Status Display */}
              {m3u8Result && (
                <Alert variant={m3u8Result.success ? "default" : "destructive"} className={m3u8Result.success ? "border-green-500 text-green-600" : ""}>
                  {m3u8Result.success ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                  <AlertDescription className="ml-2">
                    {m3u8Result.success ? "下载并发送成功！" : `失败: ${m3u8Result.error}`}
                  </AlertDescription>
                </Alert>
              )}

              <Button
                onClick={handleM3u8Forward}
                disabled={m3u8Forwarding || !m3u8Url}
                className="w-full"
                size="lg"
              >
                {m3u8Forwarding ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    下载处理中 (可能较久)...
                  </>
                ) : (
                  <>
                    <Video className="mr-2 h-4 w-4" />
                    开始下载并转发
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

      </Tabs>
    </div>
  );
}
