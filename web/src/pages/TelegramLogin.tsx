import { useState, useEffect } from 'react';
import QRCode from 'react-qr-code';
import {
  getTelegramStatus,
  loginTelegram,
  submitTelegramPassword,
  logoutTelegram,
  type TelegramAuthStatus
} from '@/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Loader2,
  RefreshCw,
  Smartphone,
  ShieldCheck,
  LogOut,
  CheckCircle2,
  AlertCircle,
  KeyRound,
  QrCode,
  User
} from 'lucide-react';

export function TelegramLogin() {
  const [status, setStatus] = useState<TelegramAuthStatus | null>(null);
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Fetch status only once on mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await getTelegramStatus();
        setStatus(data);
        if (data.error) setError(data.error);
      } catch (err) {
        console.error(err);
      }
    };
    fetchStatus();
  }, []);

  const handleStartLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await loginTelegram();
      setStatus(data);
      // Start polling only when QR is ready
      if (data.state === 'QR_READY') {
        pollForLogin();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start login');
    } finally {
      setLoading(false);
    }
  };

  const pollForLogin = () => {
    const interval = setInterval(async () => {
      try {
        const data = await getTelegramStatus();
        setStatus(data);
        if (data.state === 'SUCCESS' || data.state === 'WAITING_PASSWORD' || data.state === 'FAILED') {
          clearInterval(interval);
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
  };

  const handleSubmitPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await submitTelegramPassword(password);
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Password incorrect');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    if (!confirm('确定要断开连接吗？')) return;
    setLoading(true);
    try {
      await logoutTelegram();
      const data = await getTelegramStatus();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to logout');
    } finally {
      setLoading(false);
    }
  };

  const refreshStatus = async () => {
    setLoading(true);
    try {
      const data = await getTelegramStatus();
      setStatus(data);
    } catch (err) {
      setError('刷新失败');
    } finally {
      setLoading(false);
    }
  };

  if (!status) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Connected State
  if (status.logged_in && status.user) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">账号连接</h2>
          <p className="text-sm text-muted-foreground">管理您的 Telegram 账号连接状态</p>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <CardTitle className="text-base">已连接</CardTitle>
                <CardDescription className="text-xs">Telegram 账号已成功关联</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4 rounded-lg border bg-muted/30 p-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white font-semibold text-lg">
                {status.user.first_name?.[0] || <User className="h-5 w-5" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-sm truncate">
                    {status.user.first_name} {status.user.last_name}
                  </p>
                  {status.user.is_premium && (
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                      Premium
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-muted-foreground truncate">
                  @{status.user.username || 'No username'} · ID: {status.user.id}
                </p>
              </div>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={refreshStatus} disabled={loading}>
                <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                刷新
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/20"
                onClick={handleLogout}
                disabled={loading}
              >
                <LogOut className="mr-1.5 h-3.5 w-3.5" />
                断开连接
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // 2FA Password State
  if (status.state === 'WAITING_PASSWORD') {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">两步验证</h2>
          <p className="text-sm text-muted-foreground">您的账号已启用云密码保护</p>
        </div>

        <Card className="max-w-md">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-orange-100 dark:bg-orange-900/30">
                <KeyRound className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              </div>
              <div>
                <CardTitle className="text-base">输入云密码</CardTitle>
                <CardDescription className="text-xs">请输入您的 Telegram 两步验证密码</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmitPassword} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="password" className="text-xs">云密码</Label>
                <div className="relative">
                  <ShieldCheck className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="输入密码..."
                    className="pl-9 h-9 text-sm"
                    autoFocus
                    required
                  />
                </div>
              </div>

              {error && (
                <Alert variant="destructive" className="py-2">
                  <AlertCircle className="h-3.5 w-3.5" />
                  <AlertDescription className="text-xs ml-2">{error}</AlertDescription>
                </Alert>
              )}

              <div className="flex gap-2">
                <Button type="submit" size="sm" disabled={loading}>
                  {loading && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
                  验证
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => window.location.reload()}
                >
                  取消
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Login / QR Code State
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">账号连接</h2>
        <p className="text-sm text-muted-foreground">连接您的 Telegram 账号以启用消息转发</p>
      </div>

      <Card className="max-w-md">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/30">
              <Smartphone className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <CardTitle className="text-base">扫码登录</CardTitle>
              <CardDescription className="text-xs">使用 Telegram 手机端扫描二维码</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive" className="py-2">
              <AlertCircle className="h-3.5 w-3.5" />
              <AlertDescription className="text-xs ml-2">{error}</AlertDescription>
            </Alert>
          )}

          {status.state === 'QR_READY' && status.qr_url ? (
            <div className="space-y-4">
              <div className="flex justify-center p-4 bg-white rounded-lg border">
                <QRCode value={status.qr_url} size={180} />
              </div>

              <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground space-y-1">
                <p className="font-medium text-foreground">扫码步骤：</p>
                <ol className="list-decimal list-inside space-y-0.5">
                  <li>打开 Telegram 手机端</li>
                  <li>进入 设置 → 设备</li>
                  <li>点击 "连接桌面设备"</li>
                </ol>
              </div>

              <div className="flex items-center justify-center gap-2 text-xs text-blue-600 dark:text-blue-400">
                <Loader2 className="h-3 w-3 animate-spin" />
                等待扫码...
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex justify-center py-6">
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted">
                  <QrCode className="h-10 w-10 text-muted-foreground" />
                </div>
              </div>

              <p className="text-xs text-center text-muted-foreground">
                点击下方按钮生成登录二维码
              </p>

              <Button onClick={handleStartLogin} disabled={loading} className="w-full" size="sm">
                {loading ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <QrCode className="mr-1.5 h-3.5 w-3.5" />
                )}
                生成二维码
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
