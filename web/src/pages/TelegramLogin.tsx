import { useState, useEffect, useRef } from 'react';
import QRCode from 'react-qr-code';
import {
  getTelegramStatus,
  loginTelegram,
  submitTelegramPassword,
  logoutTelegram,
  type TelegramAuthStatus
} from '@/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Loader2, RefreshCw, Smartphone, ShieldCheck, LogOut, CheckCircle2, AlertCircle, KeyRound, QrCode } from 'lucide-react';


export function TelegramLogin() {
  const [status, setStatus] = useState<TelegramAuthStatus | null>(null);
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const pollInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = async () => {
    try {
      const data = await getTelegramStatus();
      setStatus(data);
      if (data.error) setError(data.error);
    } catch (err) {
      console.error(err);
      // Don't show error on first fetch if it's just 404 (backwards compat)
      // but here we expect 200.
    }
  };

  useEffect(() => {
    fetchStatus();
    pollInterval.current = setInterval(fetchStatus, 2000);
    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, []);

  const handleStartLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await loginTelegram();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start login');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await submitTelegramPassword(password);
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit password');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    if (!confirm('Are you sure you want to logout?')) return;
    setLoading(true);
    try {
      await logoutTelegram();
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to logout');
    } finally {
      setLoading(false);
    }
  };

  if (!status) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p className="text-muted-foreground animate-pulse">连接服务器中...</p>
      </div>
    );
  }

  // State: Logged In
  if (status.logged_in && status.user) {
    return (
      <div className="flex flex-col items-center justify-center py-10 fade-in animate-in zoom-in-95 duration-500">
        <Card className="w-full max-w-md shadow-xl border-t-4 border-t-green-500">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mb-4 ring-4 ring-green-50">
              <CheckCircle2 className="h-8 w-8 text-green-600" />
            </div>
            <CardTitle className="text-2xl">已连接 Telegram</CardTitle>
            <CardDescription>您的账号正如预期般运行</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-slate-900 to-slate-800 p-6 text-white shadow-lg">
              <div className="absolute top-0 right-0 -mr-4 -mt-4 h-24 w-24 rounded-full bg-white/5 blur-xl" />
              <div className="relative flex items-center gap-4">
                <div className="h-16 w-16 rounded-full bg-blue-500/20 flex items-center justify-center text-xl font-bold border-2 border-white/10 shadow-inner backdrop-blur-sm">
                  {status.user.first_name?.[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold truncate">
                      {status.user.first_name} {status.user.last_name}
                    </h3>
                    {status.user.is_premium && (
                      <Badge variant="secondary" className="bg-gradient-to-r from-purple-500 to-pink-500 text-white border-none py-0 px-1.5 h-5 text-[10px]">
                        PREMIUM
                      </Badge>
                    )}
                  </div>
                  <p className="text-slate-400 text-sm truncate">@{status.user.username || 'No Username'}</p>
                  <p className="text-slate-500 text-xs mt-1 font-mono">ID: {status.user.id}</p>
                </div>
              </div>
            </div>

            <Button
              variant="outline"
              className="w-full text-red-500 hover:text-red-600 hover:bg-red-50 border-red-100 dark:border-red-900/30 dark:hover:bg-red-950/20"
              onClick={handleLogout}
              disabled={loading}
            >
              <LogOut className="mr-2 h-4 w-4" />
              断开连接
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // State: Waiting for Password (2FA)
  if (status.state === 'WAITING_PASSWORD') {
    return (
      <div className="flex justify-center py-10 animate-in slide-in-from-bottom-4 duration-500">
        <Card className="w-full max-w-md shadow-lg border-t-4 border-t-orange-500">
          <CardHeader className="text-center">
            <div className="mx-auto h-12 w-12 bg-orange-100 rounded-full flex items-center justify-center mb-4">
              <KeyRound className="h-6 w-6 text-orange-600" />
            </div>
            <CardTitle>两步验证</CardTitle>
            <CardDescription>您的账号受云密码保护，请验证身份</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmitPassword} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="2fa-password">云密码</Label>
                <div className="relative">
                  <Input
                    id="2fa-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your Global Password"
                    className="pl-10"
                    autoFocus
                    required
                  />
                  <ShieldCheck className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                </div>
                <p className="text-xs text-muted-foreground">如果您忘记了密码，请在手机端重置。</p>
              </div>

              {error && (
                <Alert variant="destructive" className="animate-in fade-in slide-in-from-top-2">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>验证失败</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" className="w-full bg-orange-600 hover:bg-orange-700" disabled={loading}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <KeyRound className="mr-2 h-4 w-4" />}
                提交验证
              </Button>
            </form>
          </CardContent>
          <CardFooter className="justify-center border-t py-4 bg-gray-50 dark:bg-gray-900/50">
            <Button variant="link" size="sm" onClick={() => window.location.reload()} className="text-muted-foreground">
              取消并重试
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  // State: QR Code
  return (
    <div className="flex justify-center py-10 animate-in fade-in duration-700">
      <Card className="w-full max-w-md shadow-xl border-t-4 border-t-blue-500">
        <CardHeader className="text-center pb-2">
          <CardTitle className="text-2xl flex items-center justify-center gap-2">
            <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" alt="TG" className="h-8 w-8" />
            登录 Telegram
          </CardTitle>
          <CardDescription>连接您的账号以管理转发规则</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {status.state === 'QR_READY' && status.qr_url ? (
            <div className="flex flex-col items-center space-y-6 animate-in zoom-in-95 duration-300">
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-lg blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
                <div className="relative p-4 bg-white rounded-lg shadow-sm border ring-1 ring-gray-900/5">
                  <QRCode value={status.qr_url} size={220} />
                </div>
              </div>

              <div className="text-center space-y-2">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">请使用 Telegram 手机端扫码</h3>
                <ol className="text-sm text-gray-500 text-left inline-block space-y-1 bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg border">
                  <li>1. 打开 Telegram 设置 (Settings)</li>
                  <li>2. 点击 设备 (Devices)</li>
                  <li>3. 点击 连接桌面设备 (Link Desktop Device)</li>
                </ol>
              </div>

              <div className="flex items-center gap-2 text-xs text-blue-500 bg-blue-50 dark:bg-blue-900/20 px-3 py-1.5 rounded-full animate-pulse">
                <Smartphone className="h-3 w-3" />
                等待扫码确认...
              </div>
            </div>
          ) : (
            <div className="text-center py-10 space-y-6">
              <div className="mx-auto h-24 w-24 bg-blue-50 dark:bg-blue-900/20 rounded-full flex items-center justify-center">
                <QrCode className="h-12 w-12 text-blue-500" />
              </div>
              <p className="text-gray-500 px-6">
                点击下方按钮生成登录二维码。您需要使用手机端 Telegram App 进行扫码授权。
              </p>
              <Button onClick={handleStartLogin} disabled={loading} size="lg" className="w-full bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-600/20">
                {loading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <RefreshCw className="mr-2 h-5 w-5" />}
                生成二维码
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
