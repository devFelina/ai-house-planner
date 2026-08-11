import { signInWithEmailAndPassword, signOut as firebaseSignOut, type UserCredential } from 'firebase/auth';
import { auth } from '../../services/firebase';
import apiClient, { setInMemoryToken } from '../../services/apiClient';
import type { UserProfile } from '../../types/auth.types';

/**
 * Service to manage Firebase Authentication and backend token exchange.
 */
const authService = {
  /**
   * Signs in user using Firebase, retrieves the token, verifies it with the backend,
   * and returns the user's role/details.
   */
  login: async (email: string, password: string): Promise<{ user: UserProfile; token: string }> => {
    // 1. Authenticate with Firebase Authentication (Production mode)
    const credential: UserCredential = await signInWithEmailAndPassword(auth, email, password);
    const fbUser = credential.user;

    if (!fbUser) {
      throw new Error('Failed to retrieve user from Firebase Authentication.');
    }

    // 2. Fetch the ID token
    const token = await fbUser.getIdToken();

    // 3. Set token in memory for Axios requests
    setInMemoryToken(token);

    // 4. Verify token with backend database
    const response = await apiClient.post<{ uid: string; email: string; role: 'Architect' | 'Contractor' }>(
      '/auth/verify',
      { token }
    );

    // Return the authenticated details
    return {
      user: {
        uid: response.data.uid,
        email: response.data.email,
        role: response.data.role,
      },
      token,
    };
  },

  /**
   * Signs out of Firebase and clears the in-memory token.
   */
  logout: async (): Promise<void> => {
    await firebaseSignOut(auth);
    setInMemoryToken(null);
  },
};

export default authService;
