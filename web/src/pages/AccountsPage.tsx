import { useState, useEffect } from 'react';
import QRCode from 'react-qr-code';
import {
  getAccounts,
  initLogin,
  checkLoginStatus,
  verify2FA,
  confirmLogin,
  activateAccount,
  deleteAccount,
  type AccountInfo
} from '@/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
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
  Loader2,
  Plus,
  Trash2,
  CheckCircle2,
  Smartphone,
  RefreshCw,
} from 'lucide-react';
import { toast } from 'sonner';

export function AccountsPage() {
  const [accounts, setAccounts] = useState<AccountInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

  const fetchAccounts = async () => {
    try {
      const data = await getAccounts();
      setAccounts(data);
    } catch (err) {
      toast.error('加载账号列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleActivate = async (id: number) => {
    try {
      await activateAccount(id);
      toast.success('已切换当前账号');
      fetchAccounts();
    } catch (err) {
      toast.error('切换账号失败');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要移除此账号吗？这也将删除会话文件。')) return;
    try {
      await deleteAccount(id);
      toast.success('账号已移除');
      fetchAccounts();
    } catch (err) {
      toast.error('移除账号失败');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Telegram 账号管理</h2>
          <p className="text-sm text-muted-foreground">管理您已连接的 Telegram 账号</p>
        </div>
        <Button onClick={() => setIsAddDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          添加账号
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : accounts.length === 0 ? (
        <Card className="text-center py-12">
          <CardContent>
            <div className="flex justify-center mb-4">
              <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
                <Smartphone className="h-8 w-8 text-muted-foreground" />
              </div>
            </div>
            <h3 className="text-lg font-medium">暂无已连接账号</h3>
            <p className="text-sm text-muted-foreground mt-1 mb-6">
              连接一个 Telegram 账号以开始使用。
            </p>
            <Button onClick={() => setIsAddDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              添加账号
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {accounts.map((account) => (
            <AccountCard
              key={account.id}
              account={account}
              onActivate={() => handleActivate(account.id)}
              onDelete={() => handleDelete(account.id)}
            />
          ))}
        </div>
      )
      }

      <AddAccountDialog
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        onSuccess={() => {
          setIsAddDialogOpen(false);
          fetchAccounts();
        }}
      />
    </div >
  );
}

function AccountCard({
  account,
  onActivate,
  onDelete
}: {
  account: AccountInfo;
  onActivate: () => void;
  onDelete: () => void;
}) {
  return (
    <Card className={account.is_active ? "border-primary shadow-sm" : ""}>
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-full ${account.is_active
              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
              : "bg-muted text-muted-foreground"
              }`}>
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-base truncate max-w-[150px]">
                {account.first_name || account.phone || "Unknown"}
              </CardTitle>
              <CardDescription className="text-xs truncate max-w-[150px]">
                {account.username ? `@${account.username}` : account.session_name}
              </CardDescription>
            </div>
          </div>
          {account.is_active && (
            <Badge variant="secondary" className="bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400">
              Active
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="pb-3">
        <div className="text-xs text-muted-foreground grid grid-cols-2 gap-2 mt-2">
          <div>
            <span className="opacity-70">手机号:</span>
            <div className="font-medium">{account.phone || "-"}</div>
          </div>
          <div>
            <span className="opacity-70">添加时间:</span>
            <div className="font-medium">
              {account.created_at ? new Date(account.created_at).toLocaleDateString() : "-"}
            </div>
          </div>
        </div>
      </CardContent>
      <CardFooter className="flex justify-between border-t pt-3">
        {!account.is_active ? (
          <Button variant="ghost" size="sm" onClick={onActivate} className="text-xs">
            切换至此账号
          </Button>
        ) : (
          <div className="text-xs font-medium text-green-600 dark:text-green-400 flex items-center">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            当前使用中
          </div>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={onDelete}
          className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8 w-8 p-0"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}

function AddAccountDialog({
  open,
  onOpenChange,
  onSuccess
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}) {
  const [step, setStep] = useState<'credentials' | 'qr' | '2fa'>('credentials');
  const [apiId, setApiId] = useState('');
  const [apiHash, setApiHash] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [qrUrl, setQrUrl] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Reset state when closed
  useEffect(() => {
    if (!open) {
      setTimeout(() => {
        setStep('credentials');
        setApiId('');
        setApiHash('');
        setSessionId('');
        setQrUrl('');
        setError('');
        setPassword('');
      }, 300);
    }
  }, [open]);

  // Poll for login status when in QR mode
  useEffect(() => {
    let interval: any;
    if (step === 'qr' && sessionId) {
      interval = setInterval(async () => {
        try {
          const status = await checkLoginStatus(sessionId);
          if (status.status === 'logged_in') {
            await finalizeLogin();
          } else if (status.status === '2fa_required') {
            setStep('2fa');
            clearInterval(interval);
          } else if (status.status === 'error') {
            setError(status.error || '登录失败');
            clearInterval(interval);
          }
        } catch (err) {
          console.error("Poll failed", err);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [step, sessionId]);

  const handleInit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const resp = await initLogin(parseInt(apiId), apiHash);
      if (resp.error) {
        setError(resp.error);
      } else {
        setSessionId(resp.session_id);
        if (resp.qr_url) {
          setQrUrl(resp.qr_url);
          setStep('qr');
        } else {
          // Should usually have QR url if status is waiting_qr or connecting
          // Wait for poll to pick it up?
          const pollResp = await checkLoginStatus(resp.session_id);
          if (pollResp.qr_url) {
            setQrUrl(pollResp.qr_url);
            setStep('qr');
          } else {
            // Maybe still initializing?
            setStep('qr'); // Let poll handle it
          }
        }
      }
    } catch (err) {
      setError('初始化登录失败，请检查网络或配置');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const resp = await verify2FA(sessionId, password);
      if (resp.error) {
        setError(resp.error);
      } else if (resp.status === 'logged_in') {
        await finalizeLogin();
      }
    } catch (err) {
      setError('两步验证密码错误或失效');
    } finally {
      setLoading(false);
    }
  };

  const finalizeLogin = async () => {
    try {
      await confirmLogin(sessionId);
      toast.success('账号添加成功');
      onSuccess();
    } catch (err) {
      setError('保存账号信息失败');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>添加 Telegram 账号</DialogTitle>
          <DialogDescription>
            {step === 'credentials' && "输入您的 Telegram API 凭证 (API ID & Hash)。"}
            {step === 'qr' && "请使用 Telegram 手机端扫描二维码登录。"}
            {step === '2fa' && "请输入您的两步验证 (Cloud Password) 密码。"}
          </DialogDescription>
        </DialogHeader>

        {step === 'credentials' && (
          <form onSubmit={handleInit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="apiId">API ID</Label>
              <Input
                id="apiId"
                value={apiId}
                onChange={e => setApiId(e.target.value)}
                placeholder="123456"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="apiHash">API Hash</Label>
              <Input
                id="apiHash"
                value={apiHash}
                onChange={e => setApiHash(e.target.value)}
                placeholder="abcdef..."
                required
              />
              <p className="text-xs text-muted-foreground">
                Get these from <a href="https://my.telegram.org" target="_blank" rel="noreferrer" className="text-primary hover:underline">my.telegram.org</a>
              </p>
            </div>
            {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
            <DialogFooter>
              <Button type="submit" disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                下一步
              </Button>
            </DialogFooter>
          </form>
        )}

        {step === 'qr' && (
          <div className="flex flex-col items-center space-y-4 py-4">
            {qrUrl ? (
              <div className="bg-white p-2 rounded border">
                <QRCode value={qrUrl} size={200} />
              </div>
            ) : (
              <div className="h-[200px] w-[200px] flex items-center justify-center bg-muted rounded">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            )}
            <p className="text-sm text-center text-muted-foreground">
              打开 Telegram &gt; 设置 &gt; 设备 &gt; 连接桌面设备
            </p>

            <div className="flex justify-center">
              <Button variant="outline" size="sm" onClick={() => handleInit()} disabled={loading}>
                <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                刷新二维码
              </Button>
            </div>

            {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
          </div>
        )}

        {step === '2fa' && (
          <form onSubmit={handleVerify2FA} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">云密码 (2FA)</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoFocus
              />
            </div>
            {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
            <DialogFooter>
              <Button type="submit" disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                验证登录
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
