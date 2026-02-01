import { useState } from 'react';
import { LoginPage, Dashboard } from '@/pages';
import { isAuthenticated } from '@/api';

function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated());

  if (!authenticated) {
    return <LoginPage onLogin={() => setAuthenticated(true)} />;
  }

  return <Dashboard onLogout={() => setAuthenticated(false)} />;
}

export default App;
