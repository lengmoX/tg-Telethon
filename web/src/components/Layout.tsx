import { Link, useLocation, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Shield,
  Menu,
  Settings,
  FileText
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { clearToken } from '@/api';
import { useState } from 'react';
import { cn } from '@/lib/utils';

// We need to create avatar component or just use div for now if not installed
// Assuming avatar is NOT installed, I will use a simple div or install it.
// Let's use simple div to avoid "component not found" errors unless I install it.

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
    {
      title: '概览',
      icon: LayoutDashboard,
      path: '/dashboard',
    },
    {
      title: '规则管理',
      icon: Shield,
      path: '/rules',
    },
    {
      title: '账号连接',
      icon: MessageSquare,
      path: '/telegram',
    },
    {
      title: '日志监控',
      icon: FileText,
      path: '/logs',
      disabled: true
    },
    {
      title: '系统设置',
      icon: Settings,
      path: '/settings',
      disabled: true
    }
  ];

  const SidebarContent = () => (
    <div className="flex flex-col h-full bg-slate-900 text-slate-100">
      <div className="p-6">
        <div className="flex items-center gap-2 font-bold text-xl text-white">
          <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Shield className="h-5 w-5 text-white" />
          </div>
          TGF Pro
        </div>
        <p className="text-xs text-slate-400 mt-2 pl-1">Telegram Forwarder</p>
      </div>

      <div className="flex-1 py-4 px-3 space-y-1">
        {menuItems.map((item) => {
          const isActive = location.pathname.startsWith(item.path);
          return (
            <Link
              key={item.path}
              to={item.disabled ? '#' : item.path}
              onClick={(e) => {
                if (item.disabled) e.preventDefault();
                else setOpen(false)
              }}
              className={cn(
                "block",
                item.disabled && "cursor-not-allowed opacity-50"
              )}
            >
              <div
                className={cn(
                  "flex items-center px-3 py-2.5 rounded-md transition-all duration-200 group font-medium text-sm",
                  isActive
                    ? "bg-blue-600 text-white shadow-md"
                    : "text-slate-300 hover:bg-white/10 hover:text-white"
                )}
              >
                <item.icon className={cn("mr-3 h-5 w-5", isActive ? "text-white" : "text-slate-400 group-hover:text-white")} />
                {item.title}
                {item.disabled && <span className="ml-auto text-xs bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">DEV</span>}
              </div>
            </Link>
          );
        })}
      </div>

      <div className="p-4 border-t border-slate-800 bg-slate-950/30">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center text-xs font-bold text-white">
            AD
          </div>
          <div className="flex-1 overflow-hidden">
            <p className="text-sm font-medium text-white truncate">Administrator</p>
            <p className="text-xs text-slate-400 truncate">System Admin</p>
          </div>
        </div>
        <Button
          variant="destructive"
          className="w-full justify-start pl-3 bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:text-red-300 border border-red-500/20"
          onClick={handleLogout}
        >
          <LogOut className="mr-2 h-4 w-4" />
          退出登录
        </Button>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-gray-50/50 dark:bg-gray-900">
      {/* Desktop Sidebar */}
      <div className="hidden md:block w-64 fixed h-full z-30 shadow-xl">
        <SidebarContent />
      </div>

      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-white dark:bg-slate-900 border-b flex items-center px-4 z-40 shadow-sm justify-between">
        <div className="flex items-center gap-2 font-bold text-lg text-slate-900 dark:text-white">
          <div className="h-7 w-7 bg-blue-600 rounded flex items-center justify-center">
            <Shield className="h-4 w-4 text-white" />
          </div>
          TGF Pro
        </div>
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="h-6 w-6" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-64 border-r-0">
            <SidebarContent />
          </SheetContent>
        </Sheet>
      </div>

      {/* Main Content */}
      <div className="flex-1 md:ml-64 pt-16 md:pt-0 min-h-screen transition-all duration-300">
        <main className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
          {/* Breadcrumb-ish header or Page Title area could go here, but generic Outlet for now */}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
