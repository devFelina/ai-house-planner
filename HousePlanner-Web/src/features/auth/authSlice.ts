import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import type { AuthState, UserProfile } from '../../types/auth.types';
import authService from './authService';

const savedUser = localStorage.getItem('mockUser');
const savedToken = localStorage.getItem('mockToken');

const initialState: AuthState = {
  user: savedUser ? JSON.parse(savedUser) : null,
  token: savedToken || null,
  status: savedUser ? 'succeeded' : 'idle',
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

// Async Thunk for Initial Session Verification
export const verifySessionAsync = createAsyncThunk(
  'auth/verifySession',
  async (_, { rejectWithValue }) => {
    try {
      return await authService.verifySession();
    } catch (error: any) {
      return rejectWithValue(error.message || 'Session verification failed');
    }
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearAuth: (state) => {
      state.user = null;
      state.token = null;
      state.status = 'idle';
      state.error = null;
      localStorage.removeItem('mockUser');
      localStorage.removeItem('mockToken');
    },
    setMockAuth: (state, action: PayloadAction<UserProfile>) => {
      state.user = action.payload;
      state.token = 'mock_token';
      state.status = 'succeeded';
      state.error = null;
      localStorage.setItem('mockUser', JSON.stringify(action.payload));
      localStorage.setItem('mockToken', 'mock_token');
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
        localStorage.removeItem('mockUser');
        localStorage.removeItem('mockToken');
      })
      // Session Verification
      .addCase(verifySessionAsync.pending, (state) => {
        state.status = 'loading';
      })
      .addCase(verifySessionAsync.fulfilled, (state, action: PayloadAction<{ user: UserProfile; token: string }>) => {
        state.status = 'succeeded';
        state.user = action.payload.user;
        state.token = action.payload.token;
        state.error = null;
      })
      .addCase(verifySessionAsync.rejected, (state, action) => {
        state.status = 'failed';
        // We do not set error state here as a failed session verify just means the user isn't logged in.
        state.user = null;
        state.token = null;
      });
  },
});

export const { clearAuth, setMockAuth } = authSlice.actions;
export default authSlice.reducer;
