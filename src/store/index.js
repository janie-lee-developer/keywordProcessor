import { configureStore } from '@reduxjs/toolkit';
import keywordsReducer from './keywordsSlice';

export const store = configureStore({
  reducer: {
    keywords: keywordsReducer,
  },
});
