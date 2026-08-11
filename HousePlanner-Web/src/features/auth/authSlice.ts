import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import type { AuthState, UserProfile } from '../../types/auth.types';
import authService from './authService';

const initialState: AuthState = {
  user: null,
  token: null,
  status: 'idle',
  error: null,
};

// Async Thunk for User Login
export const loginAsync = createAsyncThunk(
  'auth/login',
  async ({ email, password }: any, { rejectWithValue }) => {
    try {
      return await authService.login(email, password);
    } catch (error: any) {
      console.log('DEBUG [Login Error Details]:', error);
      // Map Firebase errors to user friendly messages
      let message = 'An error occurred during authentication.';
      if (error.code) {
        switch (error.code) {
          case 'auth/invalid-email':
            message = 'Invalid email address format.';
            break;
          case 'auth/user-disabled':
            message = 'This user account has been disabled.';
            break;
          case 'auth/user-not-found':
          case 'auth/invalid-credential':
            message = 'Incorrect email or password.';
            break;
          case 'auth/wrong-password':
            message = 'Incorrect password. Please try again.';
            break;
          case 'auth/network-request-failed':
            message = 'Network error. Please check your internet connection.';
            break;
          default:
            message = error.message || message;
        }
      } else if (error.response?.data?.error) {
        message = error.response.data.error;
      } else if (error.message) {
        message = error.message;
      }
      return rejectWithValue(message);
    }
  }
);

// Async Thunk for User Logout
export const logoutAsync = createAsyncThunk('auth/logout', async (_, { rejectWithValue }) => {
  try {
    await authService.logout();
  } catch (error: any) {
    return rejectWithValue(error.message || 'Logout failed.');
  }
});

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearAuth: (state) => {
      state.user = null;
      state.token = null;
      state.status = 'idle';
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Login flows
      .addCase(loginAsync.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(loginAsync.fulfilled, (state, action: PayloadAction<{ user: UserProfile; token: string }>) => {
        state.status = 'succeeded';
        state.user = action.payload.user;
        state.token = action.payload.token;
        state.error = null;
      })
      .addCase(loginAsync.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload as string;
      })
      // Logout flows
      .addCase(logoutAsync.fulfilled, (state) => {
        state.user = null;
        state.token = null;
        state.status = 'idle';
        state.error = null;
      });
  },
});

export const { clearAuth } = authSlice.actions;
export default authSlice.reducer;
