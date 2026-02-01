import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage, Dashboard, TelegramLogin } from '@/pages';
import { Layout } from '@/components';
import { isAuthenticated } from '@/api';
import { useState } from 'react';



function App() {
  const [auth, setAuth] = useState(isAuthenticated());

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            auth ? <Navigate to="/dashboard" replace /> : <LoginPage onLogin={() => setAuth(true)} />
          }
        />

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
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard onLogout={() => setAuth(false)} />} />
          <Route path="telegram" element={<TelegramLogin />} />
          <Route path="rules" element={<div className="p-4">Rules Management Coming Soon</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
