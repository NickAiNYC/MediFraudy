export const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

export const formatDate = (date: string | Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(date));
};

export const formatDateTime = (date: string | Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
};

export const formatNPI = (npi: string): string => {
  // Format as XXX-XX-XXXX
  return npi.replace(/(\d{3})(\d{2})(\d{4})/, '$1-$2-$3');
};

export const formatRiskScore = (score: number, level?: string): { text: string; color: string } => {
  if (score >= 70) {
    return { text: `High (${score})`, color: 'error' };
  } else if (score >= 40) {
    return { text: `Medium (${score})`, color: 'warning' };
  } else {
    return { text: `Low (${score})`, color: 'success' };
  }
};

export const truncateText = (text: string, maxLength: number = 50): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};
