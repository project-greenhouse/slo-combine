<script setup lang="ts">
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from './stores/authStore';

const isCollapsed = ref(false);
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const handleLogout = async () => {
  await authStore.logout();
  router.push('/login');
};
</script>

<template>
  <div v-if="route.name === 'home' || route.name === 'login'">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
  <div v-else class="flex h-screen bg-gray-50 font-sans print:block print:h-auto print:bg-white">
    
    <!-- Sidebar -->
    <aside :class="['bg-code8-dark text-white flex flex-col shadow-xl z-10 transition-all duration-300 print:hidden', isCollapsed ? 'w-20' : 'w-64']">
      
      <!-- Header / Logo & Toggle Area -->
      <div class="h-20 p-4 border-b border-gray-700 flex items-center justify-between">
        <div class="flex items-center overflow-hidden whitespace-nowrap" v-show="!isCollapsed">
          <img src="/code8perf_logo.png" alt="Code 8 Performance" class="h-10 w-auto object-contain" />
        </div>
        <button @click="isCollapsed = !isCollapsed" class="p-2 text-gray-400 hover:text-white transition-colors flex-shrink-0" :class="isCollapsed ? 'mx-auto' : ''">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-2 overflow-hidden">
        <router-link v-if="authStore.isAuthenticated && authStore.userRole !== 'athlete'" to="/dashboard" active-class="bg-gray-800 text-code8-gold border-r-4 border-code8-gold" class="flex items-center gap-3 px-4 py-3 rounded text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors" :title="isCollapsed ? 'Dashboard' : ''">
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>
          <span v-if="!isCollapsed">Dashboard</span>
        </router-link>
        <router-link to="/presentation" active-class="bg-gray-800 text-code8-gold border-r-4 border-code8-gold" class="flex items-center gap-3 px-4 py-3 rounded text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors" :title="isCollapsed ? 'Presentation Sheet' : ''">
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          <span v-if="!isCollapsed">Presentation Sheet</span>
        </router-link>
        <router-link v-if="authStore.isAuthenticated && authStore.userRole !== 'athlete'" to="/evaluation" active-class="bg-gray-800 text-code8-gold border-r-4 border-code8-gold" class="flex items-center gap-3 px-4 py-3 rounded text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors" :title="isCollapsed ? 'Evaluation Hub' : ''">
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
          <span v-if="!isCollapsed">Evaluation Hub</span>
        </router-link>
        <router-link v-if="authStore.isAuthenticated && authStore.userRole === 'admin'" to="/admin" active-class="bg-gray-800 text-code8-gold border-r-4 border-code8-gold" class="flex items-center gap-3 px-4 py-3 rounded text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors" :title="isCollapsed ? 'Admin Portal' : ''">
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          <span v-if="!isCollapsed">Admin Portal</span>
        </router-link>
      </nav>

      <!-- User Profile -->
      <div class="border-t border-gray-700">
        <div v-if="authStore.isAuthenticated" class="p-4 flex items-center justify-between bg-gray-900/50 overflow-hidden whitespace-nowrap">
          <div class="flex flex-col" v-show="!isCollapsed">
            <span class="text-sm font-bold text-white truncate max-w-[150px]" :title="authStore.user?.displayName || authStore.user?.email || ''">{{ authStore.user?.displayName || authStore.user?.email }}</span>
            <span class="text-xs text-code8-gold font-medium uppercase tracking-wider">{{ authStore.userRole }} Access</span>
          </div>
          <button @click="handleLogout" class="p-2 text-gray-400 hover:text-red-400 transition-colors" title="Log Out">
            <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
          </button>
        </div>
        <div v-else class="p-4 text-center text-sm text-gray-500 bg-gray-900/50 overflow-hidden whitespace-nowrap">
          <span v-if="!isCollapsed">Athlete Viewer</span>
          <span v-else>AV</span>
        </div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <main class="flex-1 overflow-y-auto print:overflow-visible print:bg-white">
      <div class="p-8 max-w-7xl mx-auto print:p-0 print:max-w-none print:w-full">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

  </div>
</template>

<style>
/* Simple page transition animation */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media print {
  @page {
    size: auto;
    margin: 0.5in;
  }
  body {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
    background-color: white !important;
  }
}
</style>
