import React from 'react';
import { Bell, LogOut, User, Globe } from 'lucide-react';

const PORTAL_URL = process.env.REACT_APP_PUBLIC_PORTAL_URL || "http://localhost:5173";

const Header = ({ userName = "Utilisateur", role = "Affilie", onLogout }) => {
  return (
    <header className="h-12 bg-mc-header-bg flex items-center justify-between px-6 fixed top-0 left-[240px] right-0 z-40 border-b border-mc-gray-border">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-orange-500 flex items-center justify-center shadow-sm">
          <User size={16} className="text-white" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold text-mc-dark-text">
            {userName}
          </span>
          <span className="text-xs text-mc-gray-text">
            {role}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <a
          href={PORTAL_URL}
          title="Retour au portail public"
          className="p-1.5 hover:bg-gray-200 rounded-full transition-colors"
        >
          <Globe size={16} className="text-mc-gray-text" />
        </a>
        <button className="relative p-1.5 hover:bg-gray-200 rounded-full transition-colors">
          <Bell size={16} className="text-mc-gray-text" />
          <span className="absolute top-0.5 right-0.5 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>
        <button
          onClick={onLogout}
          title="Deconnexion"
          className="p-1.5 hover:bg-gray-200 rounded-full transition-colors"
        >
          <LogOut size={16} className="text-mc-gray-text" />
        </button>
      </div>
    </header>
  );
};

export default Header;
