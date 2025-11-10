import { useState, useEffect } from 'react';

export interface ApiResult<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useApi<T>(url: string): ApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const jsonData = await response.json();
      // Handle differently based on the response format
      if (jsonData && typeof jsonData === 'object') {
        if ('data' in jsonData) {
          // Response format: { ok: true, data: {...} }
          setData(jsonData.data);
        } else {
          // Direct data response
          setData(jsonData);
        }
      } else {
        setData(jsonData);
      }
    } catch (err: any) {
      // Format user-friendly error messages
      let errorMessage = 'Une erreur est survenue lors du chargement des données';
      
      if (err.message) {
        if (err.message.includes('404')) {
          errorMessage = 'Ressource non trouvée. Le service peut être temporairement indisponible.';
        } else if (err.message.includes('500')) {
          errorMessage = 'Erreur serveur. Veuillez réessayer plus tard.';
        } else if (err.message.includes('timeout') || err.message.includes('Failed to fetch')) {
          errorMessage = 'Connexion au serveur impossible. Vérifiez votre connexion réseau.';
        } else if (err.message.includes('HTTP error')) {
          errorMessage = `Erreur de communication avec le serveur (${err.message.match(/\d+/)?.[0] || 'inconnue'})`;
        } else {
          errorMessage = err.message;
        }
      }
      
      setError(errorMessage);
      console.error('API error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [url]);

  return { data, isLoading, error, refetch: fetchData };
}