import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { ChevronDown, Paperclip } from 'lucide-react';
import { mapExtractedToFormData } from './widgetFormUtils';
import { useAuth } from './AuthContext';

const Incident = () => {
  const location = useLocation();
  const { user } = useAuth();
  const [formData, setFormData] = useState({
    serviceConcerne: '',
    systemeImpacte: '',
    objet: '',
    description: '',
    documents: null
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e) => {
    setFormData(prev => ({ ...prev, documents: e.target.files }));
  };

  useEffect(() => {
    if (location.state?.widgetData) {
      setFormData(prev => ({
        ...prev,
        ...mapExtractedToFormData(location.state.widgetData, 'incident'),
        // Récupérer les fichiers depuis le store global (les File objects ne survivent pas à navigate)
        documents: window.__clearbot_attachments || location.state.widgetData.attachments || null,
      }));
      // Nettoyer le store global après récupération
      if (window.__clearbot_attachments) {
        window.__clearbot_attachments = null;
      }
    }
  }, [location.state]);

  return (
    <div className="bg-[#F7F7F7] min-h-screen p-6">
      <div className="flex justify-between items-center bg-white border border-[#EEEEEE] px-5 py-3 mb-5">
        <div className="flex items-center gap-2">
          <span className="text-[#8BC34A] text-sm">+</span>
          <h1 className="text-sm font-semibold text-[#8BC34A]">
            Nouvel incident
          </h1>
        </div>

        <div className="flex gap-2">
          <button className="px-4 py-1 bg-[#8BC34A] text-white text-xs rounded-sm">
            Enregistrer
          </button>
          <button className="px-4 py-1 border border-[#E0E0E0] text-[#757575] text-xs bg-white rounded-sm">
            Retour
          </button>
        </div>
      </div>

      <div className="bg-[#FFF8E1] border border-[#FFE082] px-4 py-3 mb-5 flex items-start gap-2">
        <span className="text-[#FF9800] text-sm mt-0.5">ℹ</span>
        <p className="text-[11px] text-[#616161]">
          La présente section concerne uniquement la déclaration d'incidents. Pour toute réclamation, veuillez utiliser 
          <span className="text-[#FF9800] underline cursor-pointer"> la rubrique dédiée</span>.
        </p>
      </div>

      <div className="mb-2 px-1 text-[11px] font-medium text-[#616161]">
        • Détails de l'affilié
      </div>

      <div className="bg-white border border-[#E0E0E0] px-6 py-3 mb-5 text-[11px]">
        <div className="flex items-start">
          <div className="w-1/2 pr-10">
            <div className="space-y-2.5">
              <div className="flex items-center">
                <span className="w-[150px] text-[#9E9E9E]">Nom affilié</span>
                <span className="text-[#424242] font-medium">
                  {user.institution}
                </span>
              </div>
              <div className="flex items-center">
                <span className="w-[150px] text-[#9E9E9E]">Nom Prénom</span>
                <span className="text-[#424242]">{user.reporterName}</span>
              </div>
              <div className="flex items-center">
                <span className="w-[150px] text-[#9E9E9E]">Email</span>
                <span className="text-[#424242]">{user.reporterEmail}</span>
              </div>
            </div>
          </div>
          <div className="w-px bg-[#E0E0E0] self-stretch" />
          <div className="w-1/2 pl-10 flex justify-between">
            <div className="space-y-2.5">
              <div className="flex items-center">
                <span className="w-[150px] text-[#9E9E9E]">
                  Activité affilié
                </span>
              </div>
              <div className="flex items-center">
                <span className="w-[150px] text-[#9E9E9E]">
                  Téléphone
                </span>
                <span className="text-[#424242]">{user.reporterPhone}</span>
              </div>
            </div>
            <div className="text-right flex flex-col justify-start">
              <span className="text-[#424242]">
                {user.reporterActivity}
              </span>
              <span className="text-[#424242] font-medium mt-1">
                {user.role}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="mb-1.5 px-1 text-[11px] font-medium text-[#616161]">
        • Description de l'incident
      </div>

      <div className="bg-white border border-[#EEEEEE] px-5 py-4 mb-5 space-y-3">
        <div className="flex items-center gap-6">
          <label className="w-[280px] text-[11px] text-[#9E9E9E]">
            Service concerné <span className="text-red-500">*</span>
          </label>
          <div className="flex-1">
            <div className="mx-auto max-w-[650px] relative">
              <select
                name="serviceConcerne"
                value={formData.serviceConcerne}
                onChange={handleChange}
                className="w-full pr-8 pb-1 text-[11px] text-[#424242] bg-transparent border-0 border-b border-[#E6E6E6] focus:outline-none"
              >
                <option value="">Service concerné</option>
                <option value="technique">Technique</option>
                <option value="post-marche-bourse">Post-marché-Bourse</option>
                <option value="post-marche-otc">Post-marché-OTC</option>
                <option value="post-marche-repos">Post-marché-Repo's</option>
                <option value="referentiel-titres">Référentiel- Titres</option>
                <option value="referentiel-affilies">Référentiel- Affiliés</option>
                <option value="ost">OST</option>
                <option value="autre">Autre</option>
              </select>
              <ChevronDown
                size={14}
                className="absolute right-0 top-1/2 -translate-y-1/2 text-[#9E9E9E]"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-6 items-center">
          <label className="w-[280px] text-[11px] text-[#9E9E9E]">
            Système impacté <span className="text-red-500">*</span>
          </label>
          <div className="flex-1">
            <div className="mx-auto max-w-[650px] relative">
              <select
                name="systemeImpacte"
                value={formData.systemeImpacte}
                onChange={handleChange}
                className="w-full pr-8 pb-1 text-[11px] text-[#424242] bg-transparent border-0 border-b border-[#E6E6E6] focus:outline-none"
              >
                <option value="">Système impacté</option>
                <option value="my-maroclear">My Maroclear</option>
                <option value="tcs-bancs">TCS BaNCS</option>
              </select>
              <ChevronDown
                size={14}
                className="absolute right-0 top-1/2 -translate-y-1/2 text-[#9E9E9E]"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-6 items-center">
          <label className="w-[280px] text-[11px] text-[#9E9E9E]">
            Objet <span className="text-red-500">*</span>
          </label>
          <div className="flex-1">
            <div className="mx-auto max-w-[650px]">
              <input
                type="text"
                name="objet"
                value={formData.objet}
                onChange={handleChange}
                placeholder="Saisir..."
                className="w-full h-[28px] px-1 text-[11px] text-[#424242] placeholder:text-[#BDBDBD] bg-transparent border-0 border-b border-[#E6E6E6] focus:outline-none"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-6 items-start">
          <label className="w-[280px] text-[11px] text-[#9E9E9E] pt-2">
            Description <span className="text-red-500">*</span>
          </label>
          <div className="flex-1">
            <div className="mx-auto max-w-[650px]">
              <textarea
                rows={5}
                className="w-full border border-[#EEEEEE] px-3 py-2 text-[11px] resize-none focus:outline-none"
                name="description"
                value={formData.description}
                onChange={handleChange}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="mb-1.5 px-1 text-[11px] font-medium text-[#616161]">
        • Document joints
      </div>

      <div className="bg-white border border-[#EEEEEE] px-5 py-4">
        <div className="flex gap-6 items-center">
          <label className="w-[280px] text-[11px] text-[#9E9E9E]">
            Liste des documents joints
          </label>
          <div className="flex-1">
            <div className="mx-auto max-w-[650px]">
              <input
                type="file"
                id="file-upload"
                multiple
                onChange={handleFileChange}
                className="hidden"
              />
              <label
                htmlFor="file-upload"
                className="flex items-center border border-[#F5A623] px-3 py-[6px] text-[11px] cursor-pointer"
              >
                <span className="flex-1 text-[#BDBDBD]">Parcourir...</span>
                <Paperclip size={14} className="text-[#F5A623]" />
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Incident;
