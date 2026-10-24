import React, { useState } from 'react';
import MaroclearWidget from './MaroclearWidget';
import './MaroclearSimulator_Professional.css';

// Profil simulant la session affilié connecté
// En production : remplacer par les données du store d'authentification (ex: useAuth())
const SESSION_PROFILE = {
  reporterName:     'HIDRA Asmae',
  reporterActivity: 'Banque Dépositaire',
  institution:      'ATTIJARIWAFA BANK',
  reporterEmail:    'Nom.Prenom29@lg.com',
  reporterPhone:    '+212600000000',
};

export default function MaroclearSimulator() {
  const [formData, setFormData] = useState({
    // Pré-rempli depuis la session dès le chargement
    reporterName:     SESSION_PROFILE.reporterName,
    reporterActivity: SESSION_PROFILE.reporterActivity,
    institution:      SESSION_PROFILE.institution,
    reporterEmail:    SESSION_PROFILE.reporterEmail,
    reporterPhone:    SESSION_PROFILE.reporterPhone,
    // Champs incident — vides initialement, remplis par ClearBot
    service:          '',
    system:           '',
    subject:          '',
    description:      '',
    businessCase:     '',
    attachments:      [],
    // Champs internes (reçus mais jamais affichés à l'affilié)
    // urgency, impact, priority → gérés par handleDispatch uniquement
  });

  // Reçoit les données publiques extraites par ClearBot (sans priorité)
  const handleDataExtracted = (data) => {
    setFormData(prev => ({
      ...prev,
      ...data,
      // Garantir que les données du compte ne sont pas écrasées par l'IA
      reporterName:     SESSION_PROFILE.reporterName,
      reporterActivity: SESSION_PROFILE.reporterActivity,
      institution:      SESSION_PROFILE.institution,
      reporterEmail:    SESSION_PROFILE.reporterEmail,
      reporterPhone:    SESSION_PROFILE.reporterPhone,
    }));
  };

  // Reçoit les données complètes (avec priorité) pour le dispatcher
  // En production : envoyer par API/mail au service concerné
  const handleDispatch = (fullData) => {
    console.info('[Dispatcher Maroclear] Données de qualification (confidentielles) :', {
      priority:     fullData.priority,
      urgency:      fullData.urgency,
      impact:       fullData.impact,
      businessCase: fullData.businessCase,
      reporter:     fullData.reporterName,
      service:      fullData.service,
      system:       fullData.system,
      subject:      fullData.subject,
    });
    // TODO : Appel API email/ticketing vers le dispatcher interne
    // await sendDispatchEmail(fullData);
  };

  return (
    <div className="maroclear-container">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span style={{ color: '#f5821f', fontWeight: 'bold' }}>MARO</span>CLEAR
        </div>

        <div className="sidebar-title">Accès</div>
        <div className="sidebar-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
          </svg>
          <span>Dashboard</span>
        </div>
        <div className="sidebar-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <span>Espace documents</span>
        </div>

        <div className="sidebar-title">Assistance et support</div>
        <div className="sidebar-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <span>Réclamations</span>
        </div>
        <div className="sidebar-item active">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <span>Incidents</span>
        </div>
      </aside>

      {/* CONTENU PRINCIPAL */}
      <main className="main-content">
        <div className="breadcrumb">
          Dashboard / <span>Incidents</span> / Nouvel incident
        </div>

        <div className="page-header">
          <h1 className="page-title">+ Nouvel incident</h1>
          <div className="button-group">
            <button className="btn-save">Enregistrer</button>
            <button className="btn-back">Retour</button>
          </div>
        </div>

        <div className="alert-box">
          <span className="info-icon">ⓘ</span>
          La présente section concerne uniquement la déclaration d'incidents.
          Pour toute réclamation, veuillez utiliser <a href="#">la rubrique dédiée</a>.
        </div>

        {/* SECTION 1 : RAPPORTEUR — pré-rempli depuis la session, non éditable */}
        <section className="form-section">
          <h2 className="section-header">• Détails du rapporteur</h2>
          <div className="info-grid">
            <div className="info-col">
              <div className="info-row">
                <label>Nom et Prénom</label>
                <span>{formData.reporterName}</span>
              </div>
              <div className="info-row">
                <label>Activité</label>
                <span>{formData.reporterActivity}</span>
              </div>
              <div className="info-row">
                <label>Institution</label>
                <span>{formData.institution}</span>
              </div>
            </div>
            <div className="info-col">
              <div className="info-row">
                <label>Email</label>
                <span>{formData.reporterEmail}</span>
              </div>
              <div className="info-row">
                <label>Téléphone</label>
                <span>{formData.reporterPhone}</span>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 2 : DESCRIPTION — remplie par ClearBot */}
        <section className="form-section">
          <h2 className="section-header">• Description de l'incident</h2>

          <div className="input-line">
            <label>Service concerné <span className="star">*</span></label>
            <select
              value={formData.service}
              onChange={(e) => setFormData({ ...formData, service: e.target.value })}
            >
              <option value="">— Sélectionnez —</option>
              <option value="OST">OST</option>
              <option value="Post-marché Bourse">Post-marché Bourse</option>
              <option value="Technique">Technique</option>
              <option value="Référentiel Titres">Référentiel Titres</option>
              <option value="Référentiel Affiliés">Référentiel Affiliés</option>
            </select>
          </div>

          <div className="input-line">
            <label>Système impacté</label>
            <select
              value={formData.system}
              onChange={(e) => setFormData({ ...formData, system: e.target.value })}
            >
              <option value="">— Sélectionnez —</option>
              <option value="MyMaroclear">MyMaroclear</option>
              <option value="TCS BaNCS">TCS BaNCS</option>
            </select>
          </div>

          <div className="input-line">
            <label>Objet <span className="star">*</span></label>
            <input
              type="text"
              value={formData.subject}
              placeholder="Objet de l'incident..."
              onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
            />
          </div>

          <div className="input-line">
            <label>Description <span className="star">*</span></label>
            <div className="editor-box">
              <div className="editor-tools"><b>B</b> <i>I</i> <u>U</u></div>
              <textarea
                value={formData.description}
                placeholder="Décrivez l'incident en détail..."
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
          </div>

          {/* SECTION PIÈCES JOINTES */}
          <div className="input-line" style={{ alignItems: 'flex-start' }}>
            <label>Pièces jointes</label>
            <div style={{ flex: 1, maxWidth: 500 }}>
              {formData.attachments && formData.attachments.length > 0 ? (
                <div style={{
                  display: 'flex', flexWrap: 'wrap', gap: 8,
                  padding: '10px', background: '#f9f9f9',
                  border: '1px solid #ddd', borderRadius: 4,
                }}>
                  {formData.attachments.map((f, i) => (
                    <div key={i} style={{
                      background: '#fde6d2', border: '1px solid #f5821f30',
                      borderRadius: 6, padding: '4px 10px',
                      fontSize: 12, color: '#c46819',
                      display: 'flex', alignItems: 'center', gap: 6,
                    }}>
                      {/* Icône pièce jointe SVG */}
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                        stroke="#c46819" strokeWidth="2" strokeLinecap="round">
                        <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                      </svg>
                      {typeof f === 'string' ? f : f.name}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{
                  padding: '10px', background: '#f9f9f9',
                  border: '1px dashed #ddd', borderRadius: 4,
                  fontSize: 12, color: '#999',
                }}>
                  Les captures d'écran jointes via ClearBot apparaîtront ici.
                </div>
              )}
            </div>
          </div>

          {/* Aucun badge priorité affiché ici — information confidentielle dispatcher uniquement */}
        </section>
      </main>

      {/* WIDGET CLEARBOT */}
      <MaroclearWidget
        userProfile={SESSION_PROFILE}
        onDataExtracted={handleDataExtracted}
        onDispatch={handleDispatch}
      />
    </div>
  );
}