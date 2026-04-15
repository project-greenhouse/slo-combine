import { defineStore } from 'pinia';
import { ref } from 'vue';
import { httpsCallable } from 'firebase/functions';
import { signInWithEmailAndPassword, signOut, onAuthStateChanged, type User } from 'firebase/auth';
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

  const registerAthlete = async (email: string, password: string, extraData: any = {}) => {
    const registerFn = httpsCallable(functions, 'register_athlete');
    const result = await registerFn({ email, password, ...extraData });
    const data = result.data as any;
    
    if (data.status === 'success') {
      return await login(email, password);
    } else {
      throw new Error(data.message || 'Registration failed');
    }
  };

  const logout = async () => {
    await signOut(auth);
  };

  return { user, userRole, athleteName, isAuthenticated, isAuthReady, login, registerAthlete, logout };
});