import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import MaroclearWidget from './MaroclearWidget';
import NavigationNotice from './NavigationNotice';
import {
  getRequestType,
  getRequestTypeLabel,
  getTargetPath,
} from './widgetFormUtils';

const pageTypesByPath = {
  '/incidents': 'incident',
  '/demandes/nouvelle': 'demande',
  '/reclamations/nouvelle': 'reclamation',
};

const ClearBotController = ({ userProfile }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [navigationLabel, setNavigationLabel] = useState('');

  const handleDataExtracted = (data) => {
    const requestType = getRequestType(data);
    const targetPath = getTargetPath(data);
    const currentType = pageTypesByPath[location.pathname];

    if (currentType !== requestType || location.pathname !== targetPath) {
      setNavigationLabel(getRequestTypeLabel(requestType));
      setTimeout(() => {
        setNavigationLabel('');
        navigate(targetPath, { state: { widgetData: data } });
      }, 1100);
      return;
    }

    navigate(location.pathname, {
      replace: true,
      state: { widgetData: data, updatedAt: Date.now() },
    });
  };

  const handleDispatch = (fullData) => {
    console.info('[Dispatcher Maroclear]', fullData);
    // Envoyer au backend pour dispatch email
    fetch('http://localhost:8000/dispatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ ticket_data: fullData }),
    })
      .then(res => res.json())
      .then(data => {
        if (data.email_sent) {
          console.info('[Dispatcher] Email envoyé avec succès');
        } else {
          console.warn('[Dispatcher] Email non envoyé:', data.error);
        }
      })
      .catch(err => console.error('[Dispatcher] Erreur:', err));
  };

  return (
    <>
      <NavigationNotice label={navigationLabel} />
      <MaroclearWidget
        userProfile={userProfile}
        onDataExtracted={handleDataExtracted}
        onDispatch={handleDispatch}
      />
    </>
  );
};

export default ClearBotController;
