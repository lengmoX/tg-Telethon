import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { login, setupAdmin, getAuthStatus } from '@/api';
import { Loader2, UserPlus, LogIn } from 'lucide-react';

interface LoginPageProps {
  onLogin: () => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [checkingStatus, setCheckingStatus] = useState(true);
  const [isSetupMode, setIsSetupMode] = useState(false);

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const status = await getAuthStatus();
      if (status.need_setup) {
        setIsSetupMode(true);
        setUsername('admin'); // Default suggestion
      }
    } catch (err) {
      console.error('Failed to check auth status', err);
    } finally {
      setCheckingStatus(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isSetupMode) {
        await setupAdmin(username, password);
      } else {
        await login(password, username);
      }
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : (isSetupMode ? 'Setup failed' : 'Login failed'));
    } finally {
      setLoading(false);
    }
  };

  if (checkingStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4">
      <Card className="w-full max-w-md shadow-xl border-border/40">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-4">
            {isSetupMode ? (
              <UserPlus className="h-6 w-6 text-primary" />
            ) : (
              <LogIn className="h-6 w-6 text-primary" />
            )}
          </div>
          <CardTitle className="text-2xl font-bold">
            {isSetupMode ? '初始化系统' : '系统登录'}
          </CardTitle>
          <CardDescription>
            {isSetupMode
              ? '欢迎使用 TGF！请创建管理员账户以开始。'
              : 'Telegram Forwarder Web Panel'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">用户名</Label>
                <Input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">密码</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={isSetupMode ? "设置登录密码" : "输入登录密码"}
                  required
                  autoFocus={!isSetupMode}
                  minLength={4}
                />
              </div>
            </div>

            <Button type="submit" className="w-full mt-6" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isSetupMode ? '创建账户中...' : '登录中...'}
                </>
              ) : (
                isSetupMode ? '创建管理员账户' : '登录'
              )}
            </Button>
          </form>

          {!isSetupMode && (
            <p className="text-xs text-muted-foreground text-center mt-6">
              安全提示：请定期更换管理员密码
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
