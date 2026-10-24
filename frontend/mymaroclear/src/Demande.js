import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { ChevronDown, Paperclip } from 'lucide-react';
import { mapExtractedToFormData } from './widgetFormUtils';
import { useAuth } from './AuthContext';

const Demande = () => {
  const location = useLocation();
  const { user } = useAuth();
  const [formData, setFormData] = useState({
    serviceConcerne: '',
    dateOccurrence: '',
    frequenceOccurrence: '',
    description: '',
    solution: '',
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
        ...mapExtractedToFormData(location.state.widgetData, 'demande'),
        documents: window.__clearbot_attachments || location.state.widgetData.attachments || null,
      }));
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
            Nouvelle demande
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
        • Description du produit / service
      </div>

      <div className="bg-white border border-[#EEEEEE] px-5 py-4 mb-5">
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
                <option value="information">Information</option>
                <option value="autres">Autres</option>
                <option value="assistance">Assistance</option>
                <option value="reinitialisation-mdp">Réinitialisation mot de passe TCS</option>
              </select>
              <ChevronDown
                size={14}
                className="absolute right-0 top-1/2 -translate-y-1/2 text-[#9E9E9E]"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="mb-1.5 px-1 text-[11px] font-medium text-[#616161]">
        • Problème rencontré
      </div>

      <div className="bg-white border border-[#EEEEEE] px-5 py-4 mb-5 space-y-3">
        {[
          "Date d'occurrence",
          "Fréquence d'occurrence"
        ].map((label, i) => (
          <div key={i} className="flex gap-6 items-center">
            <label className="w-[280px] text-[11px] text-[#9E9E9E]">
              {label} <span className="text-red-500">*</span>
            </label>
            <div className="flex-1">
              <div className="mx-auto max-w-[650px]">
                <input
                  type="text"
                  name={i === 0 ? 'dateOccurrence' : 'frequenceOccurrence'}
                  value={i === 0 ? formData.dateOccurrence : formData.frequenceOccurrence}
                  onChange={handleChange}
                  placeholder="Saisir..."
                  className="w-full h-[28px] px-1 text-[11px] text-[#424242] placeholder:text-[#BDBDBD] bg-transparent border-0 border-b border-[#E6E6E6] focus:outline-none"
                />
              </div>
            </div>
          </div>
        ))}

        <div className="flex gap-6 items-start">
          <label className="w-[280px] text-[11px] text-[#9E9E9E] pt-2">
            Description <span className="text-red-500">*</span>
          </label>
          <div className="flex-1">
            <div className="mx-auto max-w-[650px]">
              <textarea
                rows={5}
                name="description"
                value={formData.description}
                onChange={handleChange}
                className="w-full border border-[#EEEEEE] px-3 py-2 text-[11px] resize-none focus:outline-none"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-6 items-start">
          <label className="w-[280px] text-[11px] text-[#9E9E9E] pt-2">
            Comment pouvons-nous solutionner votre problème? <span className="text-red-500">*</span>
          </label>
          <div className="flex-1">
            <div className="mx-auto max-w-[650px]">
              <textarea
                rows={4}
                name="solution"
                value={formData.solution}
                onChange={handleChange}
                className="w-full border border-[#EEEEEE] px-3 py-2 text-[11px] resize-none focus:outline-none"
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

export default Demande;
