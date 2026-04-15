import { initializeApp, getApps, getApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';
import { getFunctions, connectFunctionsEmulator } from 'firebase/functions';

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyBHGLdkApH3PxIAmGhGIQ1TGNv9Hpv_yQo",
  authDomain: "code-8-performance.firebaseapp.com",
  projectId: "code-8-performance",
  storageBucket: "code-8-performance.firebasestorage.app",
  messagingSenderId: "713325041915",
  appId: "1:713325041915:web:d4eda0d9fb6fe60400785e",
  measurementId: "G-2NX15X7YXY"
};

// Initialize Firebase
const isNewApp = getApps().length === 0;
const app = isNewApp ? initializeApp(firebaseConfig) : getApp();
export const auth = getAuth(app);
export const db = getFirestore(app);
export const functions = getFunctions(app);

// Connect to the local emulator when running in development mode
if (import.meta.env.DEV && isNewApp) {
  connectFunctionsEmulator(functions, "localhost", 5001);
  // connectAuthEmulator(auth, "http://localhost:9099", { disableWarnings: true });
}