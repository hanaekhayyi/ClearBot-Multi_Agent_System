import React from 'react';

const NavigationNotice = ({ label }) => {
  if (!label) return null;

  return (
    <div className="fixed inset-0 z-[9997] bg-black/10 backdrop-blur-[1px] flex items-center justify-center">
      <div className="bg-white border border-[#E8E8E8] shadow-lg px-5 py-4 min-w-[320px]">
        <div className="flex items-center gap-3">
          <span className="h-5 w-5 rounded-full border-2 border-[#F5A623] border-t-transparent animate-spin" />
          <div>
            <p className="text-[13px] font-semibold text-[#424242]">
              Redirection en cours
            </p>
            <p className="text-[11px] text-[#757575] mt-0.5">
              Ouverture de la fiche {label}...
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NavigationNotice;
