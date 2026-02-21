import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchKeywords, addKeyword, selectAllKeywords } from './store/keywordsSlice';
import { supabase, TABLE_NAME } from './supabaseClient';
import KeywordCard from './components/KeywordCard';
import './App.css';

function App() {
  const dispatch = useDispatch();
  const keywords = useSelector(selectAllKeywords);
  const { loading, error } = useSelector((state) => state.keywords);

  useEffect(() => {
    // Initial fetch — load all existing rows
    dispatch(fetchKeywords());

    // Real-time subscription — fires on every new INSERT in the table
    const channel = supabase
      .channel('keywords-realtime')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: TABLE_NAME },
        (payload) => {
          dispatch(addKeyword(payload.new));
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [dispatch]);

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">Keyword Reference</h1>
        <p className="app__subtitle">Latest entries at the top</p>
      </header>

      <main className="app__main">
        {loading && <p className="app__status">Loading...</p>}

        {error && (
          <p className="app__status app__status--error">
            Error: {error}
          </p>
        )}

        {!loading && !error && keywords.length === 0 && (
          <p className="app__status">No entries found.</p>
        )}

        <div className="keyword-list">
          {keywords.map((kw) => (
            <KeywordCard
              key={kw.id}
              keyword={kw.keyword}
              description={kw.description}
              url={kw.url}
              timestamp={kw.timestamp}
            />
          ))}
        </div>
      </main>
    </div>
  );
}

export default App;
