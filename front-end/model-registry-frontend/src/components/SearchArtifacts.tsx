import { useState, FormEvent, ChangeEvent } from 'react';
import { useArtifactSearch } from '../hooks/useArtifactSearch';
import ArtifactCard from './ArtifactCard';
import type { SearchType, Artifact, SearchResponse } from '../types';

const SearchArtifacts: React.FC = () => {
  const [searchInput, setSearchInput] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchType, setSearchType] = useState<SearchType>('regex');

  const { data, loading, error } = useArtifactSearch(searchQuery, searchType);

  const handleSearch = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    setSearchQuery(searchInput);
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setSearchInput(e.target.value);
  };

  const handleSearchTypeChange = (e: ChangeEvent<HTMLSelectElement>): void => {
    setSearchType(e.target.value as SearchType);
  };

  const getArtifacts = (): Artifact[] => {
    if (!data) return [];
    if ('artifacts' in data) return (data as SearchResponse).artifacts;
    return [data as Artifact];
  };

  const artifacts = getArtifacts();
  const totalResults = data && 'total' in data ? (data as SearchResponse).total : artifacts.length;

  return (
    <div className="search-container">
      <h2>Search Artifacts</h2>

      <form onSubmit={handleSearch}>
        <div className="search-controls">
          <select 
            value={searchType} 
            onChange={handleSearchTypeChange}
            className="search-type-select"
          >
            <option value="regex">Regex Search</option>
            <option value="id">Search by ID</option>
            <option value="all">All Artifacts</option>
          </select>

          <input
            type="text"
            value={searchInput}
            onChange={handleInputChange}
            placeholder={
              searchType === 'regex' 
                ? 'Enter pattern (e.g., bert.*)'
                : searchType === 'id'
                ? 'Enter artifact ID'
                : 'Leave empty for all'
            }
            disabled={searchType === 'all'}
          />

          <button type="submit" disabled={loading}>
            Search
          </button>
        </div>
      </form>

      {loading && <div className="spinner">Searching...</div>}

      {error && <div className="error-message"><p>{error.message}</p></div>}

      {data && !loading && (
        <div className="results-container">
          <p className="result-count">Found {totalResults} result(s)</p>
          
          {artifacts.length === 0 ? (
            <p>No artifacts found.</p>
          ) : (
            <div className="results-grid">
              {artifacts.map((artifact) => (
                <ArtifactCard key={artifact.id} artifact={artifact} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchArtifacts;
