import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { supabase, TABLE_NAME } from '../supabaseClient';

function parseKeywordColumn(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return { keyword: raw, description: '', url: '' };
  }
}

function mockUrl(keyword) {
  return `https://en.wikipedia.org/wiki/${encodeURIComponent(keyword)}`;
}

export const fetchKeywords = createAsyncThunk('keywords/fetchAll', async () => {
  const { data, error } = await supabase
    .from(TABLE_NAME)
    .select('*')
    .order('created_at', { ascending: false });

  if (error) throw new Error(error.message);
  return data;
});

const keywordsSlice = createSlice({
  name: 'keywords',
  initialState: {
    items: [],
    loading: false,
    error: null,
  },
  reducers: {
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

// Returns all rows sorted latest-first
export const selectAllKeywords = (state) => {
  const { items } = state.keywords;
  if (!items || items.length === 0) return [];

  const INVALID_PATTERN = /\b(na|no|none|n\/a)\b/;

  return [...items]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .map((row) => {
      const parsed = parseKeywordColumn(row.keyword);
      const keywordLower = (parsed.keyword ?? '').trim().toLowerCase();
      return {
        id: row.id,
        timestamp: row.created_at,
        keyword: keywordLower,
        description: parsed.description ?? '',
        url: parsed.url || mockUrl(keywordLower),
      };
    })
    .filter((kw) => kw.keyword && !INVALID_PATTERN.test(kw.keyword));
};

export default keywordsSlice.reducer;
