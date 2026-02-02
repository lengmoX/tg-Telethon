import { Link, useLocation, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Shield,
  Menu,
  Settings,
  FileText,
  ChevronRight,
  Inbox,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { clearToken } from '@/api';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface LayoutProps {
  onLogout: () => void;
}

export function Layout({ onLogout }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = () => {
    clearToken();
    onLogout();
    navigate('/login');
  };

  const menuItems = [
    { title: '概览', icon: LayoutDashboard, path: '/dashboard' },
    { title: '规则管理', icon: Shield, path: '/rules' },
    { title: '对话管理', icon: Inbox, path: '/chats' },
    { title: '账号连接', icon: MessageSquare, path: '/telegram' },
    { title: '日志监控', icon: FileText, path: '/logs', disabled: true },
    { title: '系统设置', icon: Settings, path: '/settings', disabled: true }
  ];

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex h-16 items-center border-b px-4">
        <Link to="/dashboard" className="flex items-center gap-2.5 font-semibold">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Shield className="h-5 w-5" />
          </div>
          <span>TGF Admin</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-auto py-4 px-2">
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const isActive = location.pathname === item.path ||
              (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
            return (
              <li key={item.path}>
                <Link
                  to={item.disabled ? '#' : item.path}
                  onClick={(e) => {
                    if (item.disabled) e.preventDefault();
                    else setOpen(false);
                  }}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2.5 transition-colors",
                    isActive
                      ? "bg-accent text-accent-foreground font-medium"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    item.disabled && "opacity-50 cursor-not-allowed"
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  <span className="flex-1">{item.title}</span>
                  {item.disabled && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                      DEV
                    </span>
                  )}
                  {isActive && <ChevronRight className="h-4 w-4" />}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="border-t p-3">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start text-muted-foreground hover:text-destructive"
          onClick={handleLogout}
        >
          <LogOut className="mr-2 h-5 w-5" />
          <span>退出登录</span>
        </Button>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen">
      {/* Desktop Sidebar */}
      <aside className="hidden w-64 border-r bg-background md:block">
        <SidebarContent />
      </aside>

      {/* Mobile Header */}
      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center gap-4 border-b bg-background px-4 md:hidden">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="shrink-0">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0">
              <SidebarContent />
            </SheetContent>
          </Sheet>
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" />
            <span className="font-semibold">TGF Admin</span>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <div className="container max-w-7xl py-8 px-6 md:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
