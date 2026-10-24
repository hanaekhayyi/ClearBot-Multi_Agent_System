const normalize = (value = '') =>
  value
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();

const includesAny = (value, words) => words.some((word) => value.includes(word));

export const getRequestType = (data = {}) => {
  const explicit = normalize(data.requestType || data.type || data.category);

  // Si le backend a explicitement défini le type, l'utiliser directement
  if (explicit.includes('incident')) return 'incident';
  if (explicit.includes('reclamation')) return 'reclamation';
  if (explicit.includes('demande')) return 'demande';

  // Fallback textuel uniquement si aucun type explicite
  const text = normalize(
    [
      data.businessCase,
      data.subject,
      data.description,
      data.service,
      data.system,
    ].join(' ')
  );

  if (includesAny(text, ['reclamation', 'plainte', 'insatisfait', 'mecontent', 'retard de traitement'])) {
    return 'reclamation';
  }

  if (includesAny(text, ['demande', 'assistance', 'reinitialisation', 'creation', 'modification', 'besoin de'])) {
    return 'demande';
  }

  return 'incident';
};

export const getTargetPath = (data = {}) => {
  const type = getRequestType(data);
  if (type === 'reclamation') return '/reclamations/nouvelle';
  if (type === 'demande') return '/demandes/nouvelle';
  return '/incidents';
};

export const getRequestTypeLabel = (type) => {
  if (type === 'reclamation') return 'réclamation';
  if (type === 'demande') return 'demande';
  return 'incident';
};

const serviceMaps = {
  incident: [
    ['technique', 'technique'],
    ['post marche bourse', 'post-marche-bourse'],
    ['bourse', 'post-marche-bourse'],
    ['post marche otc', 'post-marche-otc'],
    ['otc', 'post-marche-otc'],
    ['repo', 'post-marche-repos'],
    ['referentiel titres', 'referentiel-titres'],
    ['referentiel affilies', 'referentiel-affilies'],
    ['ost', 'ost'],
    ['autre', 'autre'],
  ],
  reclamation: [
    ['releve comptable', 'releve-comptable'],
    ['denouement', 'denouement-operations'],
    ['operation sur titre', 'operations-titres'],
    ['ost', 'operations-titres'],
    ['reporting', 'reporting'],
    ['codification', 'codification-admission'],
    ['admission', 'codification-admission'],
    ['facturation', 'facturation'],
    ['acces plateforme', 'acces-plateforme'],
    ['my maroclear', 'acces-plateforme'],
    ['affiliation', 'affiliation'],
    ['service bureau', 'service-bureau'],
    ['autre', 'autres'],
  ],
  demande: [
    ['information', 'information'],
    ['assistance', 'assistance'],
    ['reinitialisation', 'reinitialisation-mdp'],
    ['mot de passe', 'reinitialisation-mdp'],
    ['autre', 'autres'],
  ],
};

const mapService = (requestType, service) => {
  const normalized = normalize(service);
  const match = serviceMaps[requestType]?.find(([label]) => normalized.includes(label));
  return match?.[1] || '';
};

const mapSystem = (system) => {
  const normalized = normalize(system);
  if (normalized.includes('my maroclear') || normalized.includes('mymaroclear')) return 'my-maroclear';
  if (normalized.includes('tcs') || normalized.includes('bancs')) return 'tcs-bancs';
  return '';
};

export const mapExtractedToFormData = (data = {}, requestType = getRequestType(data)) => {
  const common = {
    serviceConcerne: mapService(requestType, data.service || data.businessCase || ''),
    description: data.description || '',
    documents: data.attachments || null,
  };

  if (requestType === 'incident') {
    return {
      ...common,
      systemeImpacte: mapSystem(data.system),
      objet: data.subject || data.businessCase || '',
    };
  }

  return {
    ...common,
    dateOccurrence: data.dateOccurrence || '',
    frequenceOccurrence: data.frequenceOccurrence || '',
    solution: data.solution || data.subject || data.businessCase || '',
  };
};
