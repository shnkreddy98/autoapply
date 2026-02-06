/**
 * Formats an ISO date string or Date object to a local datetime string.
 * Used for fields that include time (e.g., date_applied).
 */
export const formatLocalDateTime = (dateInput: string | Date | undefined): string => {
  if (!dateInput) return '';
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * Formats an ISO date string (YYYY-MM-DD) to a local date string.
 * For simple date fields, we want to avoid timezone shifts that might move the date to the previous day.
 */
export const formatLocalDate = (dateInput: string | Date | undefined): string => {
  if (!dateInput) return '';
  
  if (typeof dateInput === 'string' && dateInput.length === 10) {
    // If it's exactly YYYY-MM-DD, parse it as a local date by replacing - with /
    // or by manually parsing to avoid UTC shift.
    const [year, month, day] = dateInput.split('-').map(Number);
    return new Date(year, month - 1, day).toLocaleDateString();
  }
  
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  return date.toLocaleDateString();
};

/**
 * Returns the local date in YYYY-MM-DD format.
 */
export const toLocalISODate = (dateInput: string | Date | undefined): string => {
  if (!dateInput) return '';
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  
  return `${year}-${month}-${day}`;
};
