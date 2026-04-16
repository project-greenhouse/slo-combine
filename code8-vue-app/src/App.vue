<script setup lang="ts">
import { ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from './stores/authStore';

const isCollapsed = ref(false);
const mobileOpen = ref(false);
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const isStaff = () => authStore.isAuthenticated && (authStore.userRole === 'admin' || authStore.userRole === 'coach');

watch(route, () => { mobileOpen.value = false; });

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

    <!-- Mobile top bar -->
    <div class="fixed top-0 left-0 right-0 h-14 bg-code8-dark text-white flex items-center px-4 z-30 md:hidden print:hidden">
      <button @click="mobileOpen = !mobileOpen" class="p-2 -ml-2 text-gray-300 hover:text-white">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" /></svg>
      </button>
      <img src="/code8perf_logo.png" alt="Code 8 Performance" class="h-8 ml-2" />
    </div>

    <!-- Mobile backdrop -->
    <div v-if="mobileOpen" class="fixed inset-0 bg-black/50 z-30 md:hidden" @click="mobileOpen = false" />

    <!-- Sidebar: overlay on mobile, persistent on md+ -->
    <aside :class="[
      'bg-code8-dark text-white flex flex-col shadow-xl transition-all duration-300 print:hidden',
      'fixed inset-y-0 left-0 z-40 w-64',
      'md:static md:z-10',
      mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
      { 'md:w-20': isCollapsed, 'md:w-64': !isCollapsed }
    ]">

      <!-- Header / Logo & Toggle Area -->
      <div class="h-20 p-4 border-b border-gray-700 flex items-center justify-between">
        <div class="flex items-center overflow-hidden whitespace-nowrap" v-show="!isCollapsed">
          <img src="/code8perf_logo.png" alt="Code 8 Performance" class="h-10 w-auto object-contain" />
        </div>
        <button @click="isCollapsed = !isCollapsed" class="p-2 text-gray-400 hover:text-white transition-colors flex-shrink-0 hidden md:block" :class="isCollapsed ? 'mx-auto' : ''">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
        <button @click="mobileOpen = false" class="p-2 text-gray-400 hover:text-white md:hidden">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-2 overflow-y-auto">
        <router-link v-if="isStaff()" to="/dashboard" active-class="bg-gray-800 text-code8-gold border-r-4 border-code8-gold" class="flex items-center gap-3 px-4 py-3 rounded text-base md:text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors" :title="isCollapsed ? 'Dashboard' : ''">
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>
          <span v-if="!isCollapsed || mobileOpen">Dashboard</span>
        </router-link>
        <router-link to="/presentation" active-class="bg-gray-800 text-code8-gold border-r-4 border-code8-gold" class="flex items-center gap-3 px-4 py-3 rounded text-base md:text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors" :title="isCollapsed ? 'Presentation Sheet' : ''">
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          <span v-if="!isCollapsed || mobileOpen">Presentation Sheet</span>
        </router-link>
        <router-link v-if="isStaff()" to="/evaluation" active-class="bg-gray-800 text-code8-gold border-r-4 border-code8-gold" class="flex items-center gap-3 px-4 py-3 rounded text-base md:text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors" :title="isCollapsed ? 'Evaluation Hub' : ''">
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
          <span v-if="!isCollapsed || mobileOpen">Evaluation Hub</span>
        </router-link>

        <!-- Data Entry section (admin/coach only) -->
        <div v-if="isStaff()" class="pt-4 mt-4 border-t border-gray-700">
          <p class="px-4 mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500" v-if="!isCollapsed || mobileOpen">Testing Stations</p>
          <router-link to="/entry/standing-reach" active-class="bg-gray-800 text-code8-gold border-r-4 border-code8-gold" class="flex items-center gap-3 px-4 py-3 rounded text-base md:text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors">
            <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 11l5-5m0 0l5 5m-5-5v12" /></svg>
            <span v-if="!isCollapsed || mobileOpen">Standing Reach</span>
          </router-link>
          <router-link to="/entry/vertical" active-class="bg-gray-800 text-code8-gold border-r-4 border-code8-gold" class="flex items-center gap-3 px-4 py-3 rounded text-base md:text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors">
            <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
            <span v-if="!isCollapsed || mobileOpen">Vertical Jump</span>
          </router-link>
          <router-link to="/entry/broad-jump" active-class="bg-gray-800 text-code8-gold border-r-4 border-code8-gold" class="flex items-center gap-3 px-4 py-3 rounded text-base md:text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors">
            <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" /></svg>
            <span v-if="!isCollapsed || mobileOpen">Broad Jump</span>
          </router-link>
        </div>

        <router-link v-if="authStore.isAuthenticated && authStore.userRole === 'admin'" to="/admin" active-class="bg-gray-800 text-code8-gold border-r-4 border-code8-gold" class="flex items-center gap-3 px-4 py-3 rounded text-base md:text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors" :title="isCollapsed ? 'Admin Portal' : ''">
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          <span v-if="!isCollapsed || mobileOpen">Admin Portal</span>
        </router-link>
      </nav>

      <!-- User Profile -->
      <div class="border-t border-gray-700">
        <div v-if="authStore.isAuthenticated" class="p-4 flex items-center justify-between bg-gray-900/50 overflow-hidden whitespace-nowrap">
          <div class="flex flex-col" v-show="!isCollapsed || mobileOpen">
            <span class="text-sm font-bold text-white truncate max-w-[150px]" :title="authStore.user?.displayName || authStore.user?.email || ''">{{ authStore.user?.displayName || authStore.user?.email }}</span>
            <span class="text-xs text-code8-gold font-medium uppercase tracking-wider">{{ authStore.userRole }} Access</span>
          </div>
          <button @click="handleLogout" class="p-2 text-gray-400 hover:text-red-400 transition-colors" title="Log Out">
            <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
          </button>
        </div>
        <div v-else class="p-4 text-center text-sm text-gray-500 bg-gray-900/50 overflow-hidden whitespace-nowrap">
          <span v-if="!isCollapsed || mobileOpen">Athlete Viewer</span>
          <span v-else>AV</span>
        </div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <main class="flex-1 overflow-y-auto pt-14 md:pt-0 print:overflow-visible print:bg-white">
      <div class="p-4 md:p-8 max-w-7xl mx-auto print:p-0 print:max-w-none print:w-full">
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
