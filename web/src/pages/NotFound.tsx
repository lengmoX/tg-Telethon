/**
 * NotFound Page - 404 Error Page
 * 
 * Displayed when authenticated users navigate to non-existent routes.
 * Features a modern design with navigation back to dashboard.
 */

import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Home, ArrowLeft, SearchX } from 'lucide-react';

export function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      {/* Icon */}
      <div className="mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-muted">
        <SearchX className="h-12 w-12 text-muted-foreground" />
      </div>

      {/* Error Code */}
      <h1 className="mb-2 text-6xl font-bold tracking-tighter text-foreground">
        404
      </h1>

      {/* Error Message */}
      <h2 className="mb-2 text-xl font-semibold text-foreground">
        页面未找到
      </h2>
      <p className="mb-8 max-w-md text-sm text-muted-foreground">
        抱歉，您访问的页面不存在或已被移除。请检查 URL 是否正确，或返回首页。
      </p>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <Button variant="outline" size="sm" asChild>
          <Link to="/" onClick={() => window.history.back()}>
            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
            返回上页
          </Link>
        </Button>
        <Button size="sm" asChild>
          <Link to="/dashboard">
            <Home className="mr-1.5 h-3.5 w-3.5" />
            返回首页
          </Link>
        </Button>
      </div>
    </div>
  );
}
