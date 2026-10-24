export const AUTO_FILL_DATA = {
    // Détails du rapporteur
    reporterName: "Asmar HIDRA",
    reporterActivity: "Utilisatrice",
    institution: "HIDRA Asmae (ATTIJARIWAFA BANK) - Banque Dépositaire",
    reporterEmail: "Nom.Prenom23@gl.com",
    reporterPhone: "+212000000000000000",
    
    // Détails de l'incident
    service: "OST",                    // OST | SWIFT | API | PORTAL
    system: "My Maroclear",            // My Maroclear | Portal | API Gateway
    subject: "Test incidents",
    description: "Bonjour,\n\nTest incident.\n\nCdt"
};

// ===== OPTIONS DISPONIBLES =====
export const OPTIONS = {
    services: [
        { value: "OST", label: "OST" },
        { value: "SWIFT", label: "SWIFT" },
        { value: "API", label: "API" },
        { value: "PORTAL", label: "Portail" }
    ],
    systems: [
        { value: "My Maroclear", label: "My Maroclear" },
        { value: "Portal", label: "Portal" },
        { value: "API Gateway", label: "API Gateway" }
    ]
};

// ===== PROFILS PRÉ-CONFIGURÉS =====
export const PROFILES = {
    // Profil par défaut
    default: AUTO_FILL_DATA,
    
    // Profil test 1
    test1: {
        reporterName: "Mohammed ALAOUI",
        reporterActivity: "Responsable OST",
        institution: "ALAOUI BANK - Banque Dépositaire",
        reporterEmail: "m.alaoui@bank.com",
        reporterPhone: "+212612345678",
        service: "SWIFT",
        system: "Portal",
        subject: "Problème de connectivité SWIFT",
        description: "Le système SWIFT rencontre des problèmes de connexion depuis hier matin."
    },
    
    // Profil test 2
    test2: {
        reporterName: "Fatima BENNANI",
        reporterActivity: "Administratrice Système",
        institution: "BENNANI BANK - Banque Dépositaire",
        reporterEmail: "f.bennani@bank.com",
        reporterPhone: "+212623456789",
        service: "API",
        system: "API Gateway",
        subject: "Erreur 500 sur l'API Gateway",
        description: "L'API Gateway retourne une erreur 500 pour les requêtes d'intégration."
    },
    
    // Profil test 3
    test3: {
        reporterName: "Omar FADILI",
        reporterActivity: "Opérateur",
        institution: "FADILI BANK - Banque Dépositaire",
        reporterEmail: "o.fadili@bank.com",
        reporterPhone: "+212634567890",
        service: "OST",
        system: "My Maroclear",
        subject: "Impossibilité de télécharger les rapports",
        description: "Les utilisateurs ne peuvent pas télécharger les rapports journaliers."
    }
};

// ===== TEMPLATES D'INCIDENTS =====
export const INCIDENT_TEMPLATES = {
    connectivityIssue: {
        subject: "Problème de connectivité",
        description: "Nous rencontrons un problème de connectivité avec le système. Les utilisateurs ne peuvent pas accéder à la plateforme."
    },
    
    performanceIssue: {
        subject: "Problème de performance",
        description: "Le système fonctionne très lentement. Les temps de réponse ont augmenté significativement."
    },
    
    dataIssue: {
        subject: "Incohérence des données",
        description: "Les données affichées ne correspondent pas aux dernières mises à jour. Veuillez vérifier la synchronisation."
    },
    
    authenticationIssue: {
        subject: "Problème d'authentification",
        description: "Les utilisateurs reçoivent une erreur lors de la connexion avec leurs identifiants valides."
    },
    
    downloadIssue: {
        subject: "Impossibilité de télécharger les fichiers",
        description: "La fonction de téléchargement ne fonctionne pas correctement. Veuillez investiguer."
    }
};

// ===== NIVEAUX DE SÉVÉRITÉ =====
export const SEVERITY_LEVELS = {
    critical: { value: "critical", label: "Critique", color: "#E74C3C" },
    high: { value: "high", label: "Élevée", color: "#E67E22" },
    medium: { value: "medium", label: "Moyenne", color: "#F39C12" },
    low: { value: "low", label: "Basse", color: "#2ECC71" }
};

// ===== STATUTS D'INCIDENTS =====
export const INCIDENT_STATUS = {
    pending: { value: "pending", label: "En attente", color: "#95A5A6" },
    open: { value: "open", label: "Ouvert", color: "#E74C3C" },
    inProgress: { value: "inProgress", label: "En cours de traitement", color: "#F39C12" },
    resolved: { value: "resolved", label: "Résolu", color: "#2ECC71" },
    closed: { value: "closed", label: "Fermé", color: "#7F8C8D" }
};

// ===== VALIDATIONS =====
export const VALIDATIONS = {
    email: {
        pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        message: "Veuillez entrer une adresse email valide"
    },
    phone: {
        pattern: /^\+?[1-9]\d{1,14}$/,
        message: "Veuillez entrer un numéro de téléphone valide"
    },
    required: {
        message: "Ce champ est obligatoire"
    }
};

// ===== FONCTION UTILITAIRE: OBTENIR UN PROFIL =====
export function getProfile(profileName = 'default') {
    return PROFILES[profileName] || PROFILES.default;
}

// ===== FONCTION UTILITAIRE: OBTENIR UN TEMPLATE =====
export function getTemplate(templateName) {
    return INCIDENT_TEMPLATES[templateName] || null;
}

// ===== FONCTION UTILITAIRE: VALIDER UN EMAIL =====
export function validateEmail(email) {
    return VALIDATIONS.email.pattern.test(email);
}

// ===== FONCTION UTILITAIRE: VALIDER UN TÉLÉPHONE =====
export function validatePhone(phone) {
    return VALIDATIONS.phone.pattern.test(phone);
}

// ===== FONCTION UTILITAIRE: FUSIONNER LES DONNÉES =====
export function mergeData(baseData, overrides = {}) {
    return {
        ...baseData,
        ...overrides
    };
}

// ===== FONCTION UTILITAIRE: EXPORTER LES DONNÉES =====
export function exportAsJSON(formData) {
    return JSON.stringify(formData, null, 2);
}

// ===== FONCTION UTILITAIRE: EXPORTER EN CSV =====
export function exportAsCSV(formData) {
    const headers = Object.keys(formData);
    const values = Object.values(formData);
    
    const headerRow = headers.join(',');
    const valueRow = values.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',');
    
    return `${headerRow}\n${valueRow}`;
}

// ===== EXEMPLE D'UTILISATION =====
/*

// HTML/Vanilla JS
import { AUTO_FILL_DATA, getProfile, getTemplate } from './DATA_CONFIG.js';

// Utiliser les données par défaut
function autoFill() {
    Object.entries(AUTO_FILL_DATA).forEach(([key, value]) => {
        const el = document.getElementById(key);
        if (el) el.value = value;
    });
}

// Utiliser un profil
function fillWithProfile(profileName) {
    const profile = getProfile(profileName);
    Object.entries(profile).forEach(([key, value]) => {
        const el = document.getElementById(key);
        if (el) el.value = value;
    });
}

// Utiliser un template
function useTemplate(templateName) {
    const template = getTemplate(templateName);
    if (template) {
        document.getElementById('subject').value = template.subject;
        document.getElementById('description').value = template.description;
    }
}

// ===== React =====

import { AUTO_FILL_DATA, getProfile, PROFILES } from './DATA_CONFIG.js';

function MyComponent() {
    const [formData, setFormData] = useState(AUTO_FILL_DATA);
    
    const handleLoadProfile = (profileName) => {
        const profile = getProfile(profileName);
        setFormData(profile);
    };
    
    return (
        <div>
            <select onChange={(e) => handleLoadProfile(e.target.value)}>
                {Object.keys(PROFILES).map(name => (
                    <option key={name} value={name}>{name}</option>
                ))}
            </select>
        </div>
    );
}

*/

// ===== EXPORT DÉFAUT =====
export default {
    AUTO_FILL_DATA,
    OPTIONS,
    PROFILES,
    INCIDENT_TEMPLATES,
    SEVERITY_LEVELS,
    INCIDENT_STATUS,
    VALIDATIONS,
    getProfile,
    getTemplate,
    validateEmail,
    validatePhone,
    mergeData,
    exportAsJSON,
    exportAsCSV
};