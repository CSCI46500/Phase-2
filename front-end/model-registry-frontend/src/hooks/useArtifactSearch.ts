import { useState, useEffect } from 'react';
import { modelRegistryAPI } from '../services/api';
import type { SearchResponse, Artifact, ApiError, SearchType } from '../types';

type SearchResult = SearchResponse | Artifact | null;

interface UseArtifactSearchReturn {
  data: SearchResult;
  loading: boolean;
  error: ApiError | null;
  refetch: () => void;
}

export const useArtifactSearch = (
  searchTerm: string, 
  searchType: SearchType = 'regex'
): UseArtifactSearchReturn => {
  const [data, setData] = useState<SearchResult>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState<number>(0);

  useEffect(() => {
    if (!searchTerm && searchType !== 'all') {
      setData(null);
      return;
    }

    const fetchData = async (): Promise<void> => {
      setLoading(true);
      setError(null);

      try {
        let result: SearchResult;

        switch (searchType) {
          case 'regex':
            result = await modelRegistryAPI.searchPackages(undefined, undefined, searchTerm);
            break;
          case 'id':
            result = await modelRegistryAPI.getPackageById(searchTerm);
            break;
          case 'all':
            result = await modelRegistryAPI.getAllPackages();
            break;
          default:
            throw new Error('Invalid search type');
        }

        setData(result);
      } catch (err) {
        setError(err as ApiError);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [searchTerm, searchType, refetchTrigger]);

  const refetch = (): void => {
    setRefetchTrigger(prev => prev + 1);
  };

  return { data, loading, error, refetch };
};
