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
      <h2 id="search-heading">Search Artifacts</h2>

      <form onSubmit={handleSearch} aria-labelledby="search-heading">
        <div className="search-controls">
          <label htmlFor="search-type" className="visually-hidden">
            Search Type:
          </label>
          <select
            id="search-type"
            value={searchType}
            onChange={handleSearchTypeChange}
            className="search-type-select"
            aria-label="Select search type"
          >
            <option value="regex">Regex Search</option>
            <option value="id">Search by ID</option>
            <option value="all">All Artifacts</option>
          </select>

          <label htmlFor="search-input" className="visually-hidden">
            Search Query:
          </label>
          <input
            id="search-input"
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
            aria-label="Search query input"
            aria-describedby="search-help"
          />
          <span id="search-help" className="visually-hidden">
            {searchType === 'regex' && 'Enter a regular expression pattern to search for artifacts'}
            {searchType === 'id' && 'Enter the specific artifact ID to find'}
            {searchType === 'all' && 'Retrieve all available artifacts'}
          </span>

          <button
            type="submit"
            disabled={loading}
            aria-label={loading ? 'Searching...' : 'Search artifacts'}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {loading && (
        <div
          className="spinner"
          role="status"
          aria-live="polite"
          aria-busy="true"
        >
          <span aria-label="Loading search results">Searching...</span>
        </div>
      )}

      {error && (
        <div
          className="error-message"
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
        >
          <h3 id="error-heading">Search Error</h3>
          <p id="error-description">{error.message}</p>
          <p id="error-suggestion">Please check your search query and try again.</p>
        </div>
      )}

      {data && !loading && (
        <div className="results-container" role="region" aria-labelledby="results-heading">
          <h3 id="results-heading" className="visually-hidden">Search Results</h3>
          <p
            className="result-count"
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            Found {totalResults} result{totalResults !== 1 ? 's' : ''}
          </p>

          {artifacts.length === 0 ? (
            <p role="status" aria-live="polite">No artifacts found.</p>
          ) : (
            <div className="results-grid" role="list">
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
