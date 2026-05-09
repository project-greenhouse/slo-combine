import { defineStore } from 'pinia';
import { ref } from 'vue';
import { httpsCallable } from 'firebase/functions';
import { signInWithEmailAndPassword, signOut, onAuthStateChanged, sendPasswordResetEmail, type User } from 'firebase/auth';
import { auth, functions } from '../firebase/config';

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null);
  const userRole = ref<string | null>(null);
  const athleteName = ref<string | null>(null);
  const isAuthenticated = ref(false);
  const isAuthReady = ref(false);

  // Listen for Firebase Auth state changes
  onAuthStateChanged(auth, async (currentUser) => {
    user.value = currentUser;
    isAuthenticated.value = !!currentUser;
    
    if (currentUser) {
      const token = await currentUser.getIdTokenResult();
      userRole.value = (token.claims.role as string) || 'athlete'; // Default to athlete
      athleteName.value = (token.claims.athlete_name as string) || null;
    } else {
      userRole.value = null;
      athleteName.value = null;
    }

    isAuthReady.value = true;
  });

  const login = async (email: string, password: string) => {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return userCredential.user;
  };

  /**
   * Athlete identity verification: matches email + birthDate against athlete_info,
   * creates Firebase Auth account if matched, returns success/error/exists status.
   * Caller is responsible for triggering password reset email after success.
   */
  const verifyAthleteIdentity = async (email: string, birthDate: string) => {
    const fn = httpsCallable(functions, 'register_athlete');
    const result = await fn({ email, birthDate });
    return result.data as { status: string; code?: string; message?: string; athlete_name?: string };
  };

  const sendPasswordReset = async (email: string) => {
    await sendPasswordResetEmail(auth, email);
  };

  const requestAdminVerification = async (name: string, email: string, birthDate: string, message: string) => {
    const fn = httpsCallable(functions, 'request_admin_verification');
    const result = await fn({ name, email, birthDate, message });
    return result.data as { status: string; message?: string };
  };

  const logout = async () => {
    await signOut(auth);
  };

  return {
    user, userRole, athleteName, isAuthenticated, isAuthReady,
    login, logout, verifyAthleteIdentity, sendPasswordReset, requestAdminVerification,
  };
});