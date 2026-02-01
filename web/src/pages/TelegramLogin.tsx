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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Loader2, RefreshCw, Smartphone, ShieldCheck, LogOut } from 'lucide-react';

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
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll status every 2 seconds
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
    if (!confirm('Are you sure you want to logout from Telegram?')) return;
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
      <div className="flex justify-center py-10">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  // State: Logged In
  if (status.logged_in && status.user) {
    return (
      <div className="max-w-md mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-6 w-6 text-green-500" />
              Telegram 已连接
            </CardTitle>
            <CardDescription>当前账号状态正常</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex flex-col items-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="h-20 w-20 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center text-2xl font-bold text-blue-600 dark:text-blue-300 mb-4">
                {status.user.first_name?.[0]}
              </div>
              <h3 className="text-xl font-bold">
                {status.user.first_name} {status.user.last_name}
              </h3>
              <p className="text-gray-500">@{status.user.username}</p>
              {status.user.is_premium && (
                <Badge variant="secondary" className="mt-2 text-yellow-600 bg-yellow-50 border-yellow-200">
                  Premium Account
                </Badge>
              )}
              <div className="mt-2 text-xs text-gray-400">ID: {status.user.id}</div>
            </div>

            <Button
              variant="destructive"
              className="w-full"
              onClick={handleLogout}
              disabled={loading}
            >
              <LogOut className="mr-2 h-4 w-4" />
              退出登录
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // State: Waiting for Password (2FA)
  if (status.state === 'WAITING_PASSWORD') {
    return (
      <div className="max-w-md mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>两步验证</CardTitle>
            <CardDescription>您的账号开启了云密码保护，请输入密码继续</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmitPassword} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="2fa-password">云密码</Label>
                <Input
                  id="2fa-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="输入您的 Telegram 云密码"
                  required
                />
              </div>
              {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                提交密码
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  // State: QR Code
  return (
    <div className="max-w-md mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>登录 Telegram</CardTitle>
          <CardDescription>扫码登录您的 Telegram 账号</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

          {status.state === 'QR_READY' && status.qr_url ? (
            <div className="flex flex-col items-center space-y-4">
              <div className="p-4 bg-white rounded-lg shadow-sm border">
                <QRCode value={status.qr_url} size={200} />
              </div>
              <div className="text-center text-sm text-gray-500">
                <p>请使用 Telegram 手机端扫码</p>
                <p className="mt-1">设置 → 设备 → 连接桌面设备</p>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <Smartphone className="h-4 w-4" />
                正在等待扫码...
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <Smartphone className="h-16 w-16 mx-auto text-gray-300 mb-4" />
              <p className="text-gray-500 mb-6">点击下方按钮开始登录流程</p>
              <Button onClick={handleStartLogin} disabled={loading} className="w-full">
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                获取登录二维码
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
