export type UserRole = 'Architect' | 'Contractor';

export interface UserProfile {
  uid: string;
  email: string;
  role: UserRole;
}

export interface AuthState {
  user: UserProfile | null;
  token: string | null; // In-memory Firebase ID Token
  status: 'idle' | 'loading' | 'succeeded' | 'failed';
  error: string | null;
}
