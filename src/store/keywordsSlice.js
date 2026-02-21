import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { supabase, TABLE_NAME } from '../supabaseClient';

// Parses the `text` column (JSON string) into { keyword, description, url }
export function parseTextColumn(text) {
  try {
    return JSON.parse(text);
  } catch {
    return { keyword: text, description: '', url: '' };
  }
}

export const fetchKeywords = createAsyncThunk('keywords/fetchAll', async () => {
  const { data, error } = await supabase
    .from(TABLE_NAME)
    .select('*')
    .order('timestamp', { ascending: false });

  if (error) throw new Error(error.message);
  return data;
});

const keywordsSlice = createSlice({
  name: 'keywords',
  initialState: {
    items: [],    // raw rows from Supabase: [{ id, timestamp, text }, ...]
    loading: false,
    error: null,
  },
  reducers: {
    // Called when a real-time INSERT arrives
    addKeyword: (state, action) => {
      state.items.unshift(action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchKeywords.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchKeywords.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload;
      })
      .addCase(fetchKeywords.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      });
  },
});

export const { addKeyword } = keywordsSlice.actions;

// Returns all rows sorted latest-first, with text parsed into keyword/description/url
export const selectAllKeywords = (state) => {
  const { items } = state.keywords;
  if (!items || items.length === 0) return [];

  return [...items]
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .map((row) => {
      const parsed = parseTextColumn(row.text);
      return {
        id: row.id,
        timestamp: row.timestamp,
        keyword: parsed.keyword ?? '',
        description: parsed.description ?? '',
        url: parsed.url ?? '',
      };
    });
};

export default keywordsSlice.reducer;
