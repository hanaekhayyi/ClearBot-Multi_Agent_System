import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';

const Sidebar = () => {
  const [expandedMenus, setExpandedMenus] = useState({
    acces: true,
    assistance: true,
    operations: true,
    affilies: true
  });

  const toggleMenu = (menu) => {
    setExpandedMenus(prev => ({ ...prev, [menu]: !prev[menu] }));
  };

  const Icons = {
    dashboard: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
      </svg>
    ),
    folder: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
      </svg>
    ),
    globe: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="2" y1="12" x2="22" y2="12"/>
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
      </svg>
    ),
    key: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
      </svg>
    ),
    lock: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
        <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
      </svg>
    ),
    fileText: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <path d="M14 2v6h6"/>
        <path d="M16 13H8"/>
        <path d="M16 17H8"/>
        <path d="M10 9H8"/>
      </svg>
    ),
    message: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
    ),
    alert: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
    ),
    clipboard: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
        <rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>
      </svg>
    ),
    settings: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
      </svg>
    ),
    userCog: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="8.5" cy="7" r="4"/>
        <line x1="20" y1="8" x2="20" y2="14"/>
        <line x1="23" y1="11" x2="17" y2="11"/>
      </svg>
    ),
    users: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
    ),
    network: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="5" r="3"/>
        <circle cx="19" cy="8" r="3"/>
        <circle cx="5" cy="8" r="3"/>
        <circle cx="12" cy="19" r="3"/>
        <line x1="12" y1="8" x2="12" y2="16"/>
        <line x1="8.5" y1="9" x2="5.5" y2="16"/>
        <line x1="15.5" y1="9" x2="18.5" y2="16"/>
      </svg>
    )
  };

  return (
    <aside className="w-[240px] min-h-screen bg-white border-r border-[#E8E8E8] flex flex-col fixed left-0 top-0 z-50">
      <div className="h-[50px] flex items-center px-5 bg-white">
        <img 
          src="/logo-maroclear.png" 
          alt="MAROCLEAR" 
          className="h-7 w-auto object-contain"
        />
      </div>

      <nav className="flex-1 py-0 overflow-y-auto">
        <NavLink 
          to="/dashboard" 
          className={({ isActive }) => 
            `flex items-center gap-3 px-5 py-3 text-[13px] transition-colors ${
              isActive 
                ? 'bg-[#FF9800] text-white' 
                : 'text-[#666666] hover:bg-[#F9F9F9]'
            }`
          }
        >
          {Icons.dashboard}
          <span>Dashboard</span>
        </NavLink>

        <NavLink 
          to="/documents" 
          className={({ isActive }) => 
            `flex items-center gap-3 px-5 py-3 text-[13px] transition-colors ${
              isActive 
                ? 'bg-[#FF9800] text-white' 
                : 'text-[#666666] hover:bg-[#F9F9F9]'
            }`
          }
        >
          {Icons.folder}
          <span>Espace documents</span>
        </NavLink>

        <button 
          onClick={() => toggleMenu('acces')}
          className="w-full flex items-center px-5 py-3 text-[13px] text-[#FF9800] hover:bg-[#F9F9F9] transition-colors text-left"
        >
          <span className="font-medium">Accès</span>
        </button>
        {expandedMenus.acces && (
          <div className="bg-white">
            <NavLink 
              to="/adresses-ip" 
              className={({ isActive }) => 
                `flex items-center gap-3 pl-10 pr-5 py-2.5 text-[12px] transition-colors ${
                  isActive 
                    ? 'bg-[#FF9800] text-white' 
                    : 'text-[#888888] hover:bg-[#F9F9F9]'
                }`
              }
            >
              {Icons.globe}
              <span>Adresses IP</span>
            </NavLink>
            <NavLink 
              to="/token" 
              className={({ isActive }) => 
                `flex items-center gap-3 pl-10 pr-5 py-2.5 text-[12px] transition-colors ${
                  isActive 
                    ? 'bg-[#FF9800] text-white' 
                    : 'text-[#888888] hover:bg-[#F9F9F9]'
                }`
              }
            >
              {Icons.key}
              <span>Token</span>
            </NavLink>
            <NavLink 
              to="/regles-pin" 
              className={({ isActive }) => 
                `flex items-center gap-3 pl-10 pr-5 py-2.5 text-[12px] transition-colors ${
                  isActive 
                    ? 'bg-[#FF9800] text-white' 
                    : 'text-[#888888] hover:bg-[#F9F9F9]'
                }`
              }
            >
              {Icons.lock}
              <span>Règles code PIN</span>
            </NavLink>
          </div>
        )}

        <button 
          onClick={() => toggleMenu('assistance')}
          className="w-full flex items-center px-5 py-3 text-[13px] text-[#FF9800] hover:bg-[#F9F9F9] transition-colors text-left"
        >
          <span className="font-medium">Assistance et support</span>
        </button>
        {expandedMenus.assistance && (
          <div className="bg-white">
            <NavLink 
              to="/retransmission" 
              className={({ isActive }) => 
                `flex items-center gap-3 pl-10 pr-5 py-2.5 text-[12px] transition-colors ${
                  isActive 
                    ? 'bg-[#FF9800] text-white' 
                    : 'text-[#888888] hover:bg-[#F9F9F9]'
                }`
              }
            >
              {Icons.fileText}
              <span>Retransmission de documents</span>
            </NavLink>
            <NavLink 
              to="/reclamations/nouvelle" 
              className={({ isActive }) => 
                `flex items-center gap-3 pl-10 pr-5 py-2.5 text-[12px] transition-colors ${
                  isActive 
                    ? 'bg-[#FF9800] text-white' 
                    : 'text-[#888888] hover:bg-[#F9F9F9]'
                }`
              }
            >
              {Icons.message}
              <span>Réclamations</span>
            </NavLink>
            <NavLink 
              to="/incidents" 
              className={({ isActive }) => 
                `flex items-center gap-3 pl-10 pr-5 py-2.5 text-[12px] transition-colors ${
                  isActive 
                    ? 'bg-[#FF9800] text-white' 
                    : 'text-[#888888] hover:bg-[#F9F9F9]'
                }`
              }
            >
              {Icons.alert}
              <span>Incidents</span>
            </NavLink>
            <NavLink 
              to="/demandes/nouvelle" 
              className={({ isActive }) => 
                `flex items-center gap-3 pl-10 pr-5 py-2.5 text-[12px] transition-colors ${
                  isActive 
                    ? 'bg-[#FF9800] text-white' 
                    : 'text-[#888888] hover:bg-[#F9F9F9]'
                }`
              }
            >
              {Icons.clipboard}
              <span>Demandes</span>
            </NavLink>
          </div>
        )}

        <button 
          onClick={() => toggleMenu('operations')}
          className="w-full flex items-center px-5 py-3 text-[13px] text-[#FF9800] hover:bg-[#F9F9F9] transition-colors text-left"
        >
          <span className="font-medium">Opérations</span>
        </button>
        {expandedMenus.operations && (
          <div className="bg-white">
            <NavLink 
              to="/gestion-valeurs" 
              className={({ isActive }) => 
                `flex items-center gap-3 pl-10 pr-5 py-2.5 text-[12px] transition-colors ${
                  isActive 
                    ? 'bg-[#FF9800] text-white' 
                    : 'text-[#888888] hover:bg-[#F9F9F9]'
                }`
              }
            >
              {Icons.settings}
              <span>Gestion des valeurs</span>
            </NavLink>
          </div>
        )}

        <button 
          onClick={() => toggleMenu('affilies')}
          className="w-full flex items-center px-5 py-3 text-[13px] text-[#FF9800] hover:bg-[#F9F9F9] transition-colors text-left"
        >
          <span className="font-medium">Affiliés</span>
        </button>
        {expandedMenus.affilies && (
          <div className="bg-white">
            <NavLink 
              to="/gestion-affilies" 
              className={({ isActive }) => 
                `flex items-center gap-3 pl-10 pr-5 py-2.5 text-[12px] transition-colors ${
                  isActive 
                    ? 'bg-[#FF9800] text-white' 
                    : 'text-[#888888] hover:bg-[#F9F9F9]'
                }`
              }
            >
              {Icons.userCog}
              <span>Gestion des affiliés</span>
            </NavLink>
            <NavLink 
              to="/gerer-equipe" 
              className={({ isActive }) => 
                `flex items-center gap-3 pl-10 pr-5 py-2.5 text-[12px] transition-colors ${
                  isActive 
                    ? 'bg-[#FF9800] text-white' 
                    : 'text-[#888888] hover:bg-[#F9F9F9]'
                }`
              }
            >
              {Icons.users}
              <span>Gérer mon équipe</span>
            </NavLink>
            <NavLink 
              to="/gerer-affiliation" 
              className={({ isActive }) => 
                `flex items-center gap-3 pl-10 pr-5 py-2.5 text-[12px] transition-colors ${
                  isActive 
                    ? 'bg-[#FF9800] text-white' 
                    : 'text-[#888888] hover:bg-[#F9F9F9]'
                }`
              }
            >
              {Icons.network}
              <span>Gérer l'affiliation</span>
            </NavLink>
          </div>
        )}
      </nav>
    </aside>
  );
};

export default Sidebar;
