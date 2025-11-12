/**
 * Utilitaires de formatage pour données financières
 * Standardise l'affichage des pourcentages, devises, et timestamps
 */

// Formatters configurés pour le français canadien
const percentFormatter = new Intl.NumberFormat('fr-CA', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const currencyFormatterCAD = new Intl.NumberFormat('fr-CA', {
  style: 'currency',
  currency: 'CAD',
});

const currencyFormatterUSD = new Intl.NumberFormat('fr-CA', {
  style: 'currency',
  currency: 'USD',
});

const numberFormatter = new Intl.NumberFormat('fr-CA', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

/**
 * Formate un pourcentage avec gestion des valeurs nulles/undefined
 */
export function formatPercent(value: number | null | undefined, precision: number = 2): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'N/A';
  }
  
  // Si la valeur est déjà en pourcentage (> 1), la diviser par 100
  const normalizedValue = Math.abs(value) > 1 ? value / 100 : value;
  
  return new Intl.NumberFormat('fr-CA', {
    style: 'percent',
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  }).format(normalizedValue);
}

/**
 * Formate un montant en devise
 */
export function formatCurrency(
  value: number | null | undefined, 
  currency: 'CAD' | 'USD' = 'CAD',
  compact: boolean = false
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'N/A';
  }

  if (compact && Math.abs(value) >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}G ${currency}`;
  }
  if (compact && Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M ${currency}`;
  }
  if (compact && Math.abs(value) >= 1_000) {
    return `${(value / 1_000).toFixed(1)}k ${currency}`;
  }

  const formatter = currency === 'USD' ? currencyFormatterUSD : currencyFormatterCAD;
  return formatter.format(value);
}

/**
 * Formate un nombre avec gestion des valeurs nulles
 */
export function formatNumber(value: number | null | undefined, precision: number = 2): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'N/A';
  }

  return new Intl.NumberFormat('fr-CA', {
    minimumFractionDigits: 0,
    maximumFractionDigits: precision,
  }).format(value);
}

/**
 * Formate un timestamp en temps relatif
 */
export function formatRelativeTime(timestamp: string | null | undefined): string {
  if (!timestamp) return 'Inconnue';
  
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffMinutes < 1) return 'À l\'instant';
    if (diffMinutes < 60) return `${diffMinutes} min`;
    if (diffMinutes < 24 * 60) return `${Math.floor(diffMinutes / 60)}h`;
    if (diffMinutes < 7 * 24 * 60) return `${Math.floor(diffMinutes / (24 * 60))}j`;
    
    return date.toLocaleDateString('fr-CA');
  } catch {
    return 'Invalide';
  }
}

/**
 * Formate une heure en format français
 */
export function formatTime(timestamp: string | null | undefined): string {
  if (!timestamp) return 'N/A';
  
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('fr-CA', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  } catch {
    return 'N/A';
  }
}

/**
 * Formate une date complète
 */
export function formatDateTime(timestamp: string | null | undefined): string {
  if (!timestamp) return 'N/A';
  
  try {
    const date = new Date(timestamp);
    return date.toLocaleString('fr-CA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return 'N/A';
  }
}

/**
 * Détermine la couleur CSS pour un pourcentage de variation
 */
export function getChangeColor(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'text-gray-400';
  }
  
  if (value > 0) return 'text-green-400';
  if (value < 0) return 'text-red-400';
  return 'text-gray-400';
}

/**
 * Formate un niveau de confiance (0-1 ou 0-100)
 */
export function formatConfidence(confidence: number | null | undefined): string {
  if (confidence === null || confidence === undefined || isNaN(confidence)) {
    return 'N/A';
  }
  
  // Normaliser à 0-100
  const normalized = confidence > 1 ? confidence : confidence * 100;
  return `${Math.round(normalized)}%`;
}

/**
 * Détermine la couleur pour un niveau de confiance
 */
export function getConfidenceColor(confidence: number | null | undefined): string {
  if (confidence === null || confidence === undefined || isNaN(confidence)) {
    return 'text-gray-400';
  }
  
  const normalized = confidence > 1 ? confidence : confidence * 100;
  
  if (normalized >= 80) return 'text-green-400';
  if (normalized >= 60) return 'text-yellow-400';
  if (normalized >= 40) return 'text-orange-400';
  return 'text-red-400';
}