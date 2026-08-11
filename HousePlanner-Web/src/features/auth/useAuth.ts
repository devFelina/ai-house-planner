import { useCallback } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import type { RootState, AppDispatch } from '../../store';
import { loginAsync, logoutAsync } from './authSlice';

export const useAuth = () => {
  const dispatch = useDispatch<AppDispatch>();
  
  const user = useSelector((state: RootState) => state.auth.user);
  const token = useSelector((state: RootState) => state.auth.token);
  const status = useSelector((state: RootState) => state.auth.status);
  const error = useSelector((state: RootState) => state.auth.error);

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await dispatch(loginAsync({ email, password }));
      if (loginAsync.rejected.match(result)) {
        throw new Error(result.payload as string);
      }
      return result.payload;
    },
    [dispatch]
  );

  const logout = useCallback(() => {
    dispatch(logoutAsync());
  }, [dispatch]);

  return {
    user,
    token,
    isAuthenticated: !!user,
    isLoading: status === 'loading',
    error,
    login,
    logout,
  };
};

export default useAuth;
