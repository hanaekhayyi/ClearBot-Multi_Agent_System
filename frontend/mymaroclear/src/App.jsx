import { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import Reclamation from './Reclamation';
import Demande from './Demande';
import Incident from './Incident';
import ClearBotController from './ClearBotController';
import { AuthContext } from './AuthContext';
import { getCurrentUser, logout, redirectToLogin } from './authApi';

const Placeholder = ({ title }) => (
  <div className="p-6 text-mc-gray-text">
    <div className="bg-white border border-[#E8E8E8] rounded-sm p-6 shadow-sm">
      <h1 className="text-lg font-semibold text-mc-dark-text">{title}</h1>
      <p className="mt-3 text-sm text-[#616161]">Cette page est en cours d'integration.</p>
    </div>
  </div>
);

function App() {
  const [user, setUser] = useState(null);
  const [loadingAuth, setLoadingAuth] = useState(true);

  useEffect(() => {
    getCurrentUser()
      .then(({ user }) => setUser(user))
      .catch(() => redirectToLogin())
      .finally(() => setLoadingAuth(false));
  }, []);

  const handleLogout = async () => {
    // Nettoyer la conversation privee (ne doit pas etre visible dans le public)
    localStorage.removeItem("clearbot_public_conversation");
    window.sessionStorage.removeItem("maroclear-clearbot-session");
    await logout();
    redirectToLogin();
  };

  if (loadingAuth) {
    return (
      <div className="min-h-screen bg-mc-gray-bg flex items-center justify-center text-sm text-mc-gray-text">
        Verification de la session...
      </div>
    );
  }

  if (!user) return null;

  return (
    <AuthContext.Provider value={{ user }}>
      <div className="flex min-h-screen bg-mc-gray-bg">
        <Sidebar />
        <div className="flex-1 ml-[240px]">
          <Header
            userName={user.reporterName}
            role={`${user.role} | ${user.institution}`}
            onLogout={handleLogout}
          />
          <main className="pt-12">
            <Routes>
              <Route path="/" element={<Navigate to="/reclamations/nouvelle" replace />} />
              <Route path="/dashboard" element={<Placeholder title="Dashboard" />} />
              <Route path="/documents" element={<Placeholder title="Espace documents" />} />
              <Route path="/adresses-ip" element={<Placeholder title="Adresses IP" />} />
              <Route path="/token" element={<Placeholder title="Token" />} />
              <Route path="/regles-pin" element={<Placeholder title="Regles code PIN" />} />
              <Route path="/retransmission" element={<Placeholder title="Retransmission de documents" />} />
              <Route path="/reclamations/nouvelle" element={<Reclamation />} />
              <Route path="/incidents" element={<Incident />} />
              <Route path="/demandes/nouvelle" element={<Demande />} />
              <Route path="/gestion-valeurs" element={<Placeholder title="Gestion des valeurs" />} />
              <Route path="/gestion-affilies" element={<Placeholder title="Gestion des affilies" />} />
              <Route path="/gerer-equipe" element={<Placeholder title="Gerer mon equipe" />} />
              <Route path="/gerer-affiliation" element={<Placeholder title="Gerer l'affiliation" />} />
              <Route path="*" element={<Navigate to="/reclamations/nouvelle" replace />} />
            </Routes>
          </main>
          <ClearBotController userProfile={user} />
        </div>
      </div>
    </AuthContext.Provider>
  );
}

export default App;
