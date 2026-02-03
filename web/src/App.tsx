/**
 * TGF Web - Main Application Component
 * 
 * This is the root component that handles:
 * - Application-wide authentication state
 * - Route definitions and protection
 * - Layout structure with sidebar navigation
 * 
 * Route Structure:
 * - /login - Public login page (redirects to /dashboard if authenticated)
 * - / - Protected routes (requires authentication)
 *   - /dashboard - Main dashboard with watcher status and rules overview
 *   - /rules - Rule management with CRUD operations
 *   - /telegram - Telegram account connection (QR login)
 *   - /* - 404 catch-all for unknown routes
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage, Dashboard, RulesPage, ChatsPage, ForwardPage, NotFound, AccountsPage, TasksPage } from '@/pages';
import { Layout } from '@/components';
import { Toaster } from '@/components/ui/sonner';
import { isAuthenticated } from '@/api';
import { useState } from 'react';


/**
 * Main App Component
 * 
 * Manages authentication state and renders appropriate routes.
 * Uses react-router-dom for client-side routing.
 */
function App() {
  // Authentication state - persisted in localStorage via API client
  const [auth, setAuth] = useState(isAuthenticated());

  return (
    <BrowserRouter>
      <Routes>
        {/* 
          Public Route: Login Page
          - Accessible only when not authenticated
          - Redirects to dashboard if already logged in
        */}
        <Route
          path="/login"
          element={
            auth ? <Navigate to="/dashboard" replace /> : <LoginPage onLogin={() => setAuth(true)} />
          }
        />

        {/* 
          Protected Routes: Requires Authentication
          - All child routes are wrapped in Layout component
          - Redirects to /login if not authenticated
        */}
        <Route
          path="/"
          element={
            auth ? (
              <Layout onLogout={() => setAuth(false)} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        >
          {/* Default redirect to dashboard */}
          <Route index element={<Navigate to="/dashboard" replace />} />

          {/* Dashboard - System overview and watcher control */}
          <Route path="dashboard" element={<Dashboard onLogout={() => setAuth(false)} />} />

          {/* Telegram - Account connection via QR code */}
          <Route path="telegram" element={<AccountsPage />} />

          {/* Rules - CRUD management for forwarding rules */}
          <Route path="rules" element={<RulesPage />} />

          {/* Chats - Dialog list and message export */}
          <Route path="chats" element={<ChatsPage />} />

          {/* Forward - One-time message forwarding */}
          <Route path="forward" element={<ForwardPage />} />

          {/* Tasks - Background task management */}
          <Route path="tasks" element={<TasksPage />} />

          {/* 404 Catch-all - Handle unknown routes */}
          <Route path="*" element={<NotFound />} />
        </Route>

        {/* 
          Global 404 - For unauthenticated users accessing unknown routes
          Redirects to login page
        */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
      <Toaster />
    </BrowserRouter>
  );
}

export default App;
