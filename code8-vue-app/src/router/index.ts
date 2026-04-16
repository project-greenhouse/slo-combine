import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';
import DashboardView from '../views/DashboardView.vue';
import EvaluationHubView from '../views/EvaluationHubView.vue';
import PresentationView from '../views/PresentationView.vue';
import LoginView from '../views/LoginView.vue';
import AdminView from '../views/AdminView.vue';
import AthleteMatchingView from '../views/AthleteMatchingView.vue';
import StandingReachEntry from '../views/entry/StandingReachEntry.vue';
import VerticalJumpEntry from '../views/entry/VerticalJumpEntry.vue';
import BroadJumpEntry from '../views/entry/BroadJumpEntry.vue';
import { auth } from '../firebase/config';
import { onAuthStateChanged, type User } from 'firebase/auth';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView,
      meta: { requiresAuth: true }
    },
    {
      path: '/presentation',
      name: 'presentation',
      component: PresentationView // Publicly accessible to athletes
    },
    {
      path: '/evaluation',
      name: 'evaluation',
      component: EvaluationHubView,
      meta: { requiresAuth: true }
    },
    {
      path: '/match-athletes',
      name: 'match-athletes',
      component: AthleteMatchingView,
      meta: { requiresAuth: true, requiresStaff: true }
    },
    {
      path: '/entry/standing-reach',
      name: 'standing-reach',
      component: StandingReachEntry,
      meta: { requiresAuth: true, requiresStaff: true }
    },
    {
      path: '/entry/vertical',
      name: 'vertical-jump',
      component: VerticalJumpEntry,
      meta: { requiresAuth: true, requiresStaff: true }
    },
    {
      path: '/entry/broad-jump',
      name: 'broad-jump',
      component: BroadJumpEntry,
      meta: { requiresAuth: true, requiresStaff: true }
    },
    {
      path: '/admin',
      name: 'admin',
      component: AdminView,
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView
    }
  ]
});

// Wait for Firebase Auth to initialize before routing
const getCurrentUser = (): Promise<User | null> => {
  return new Promise((resolve, reject) => {
    const unsubscribe = onAuthStateChanged(auth, user => {
      unsubscribe();
      resolve(user);
    }, reject);
  });
};

router.beforeEach(async (to, _from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin);
  const requiresStaff = to.matched.some(record => record.meta.requiresStaff);
  let currentUser = null;
  
  try {
    currentUser = await getCurrentUser();
  } catch (err) {
    console.error("Firebase Auth failed to initialize. Check your API keys in config.ts!", err);
  }

  if (requiresAuth && !currentUser) {
    next('/login');
  } else if (currentUser) {
    const token = await currentUser.getIdTokenResult();
    const role = token.claims.role || 'athlete';
    
    if (to.name === 'login') next(role === 'athlete' ? '/presentation' : '/dashboard');
    else if (requiresAdmin && role !== 'admin') next('/dashboard');
    else if (requiresStaff && role !== 'admin' && role !== 'coach') next('/presentation');
    else if (role === 'athlete' && (to.name === 'dashboard' || to.name === 'evaluation')) next('/presentation');
    else next();
  } else {
    next();
  }
});

export default router;