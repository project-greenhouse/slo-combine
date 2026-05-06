<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/authStore';

const router = useRouter();
const authStore = useAuthStore();

const isStaff = computed(() => authStore.userRole === 'admin' || authStore.userRole === 'coach');
const isAdmin = computed(() => authStore.userRole === 'admin');

const greeting = computed(() => {
  const name = authStore.user?.displayName || authStore.user?.email?.split('@')[0] || '';
  const hour = new Date().getHours();
  const timeGreeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  return name ? `${timeGreeting}, ${name}` : timeGreeting;
});
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-gray-900">{{ greeting }}</h1>
      <p class="text-gray-500 mt-1">SLO County Combine Dashboard</p>
    </div>

    <!-- Primary nav cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
      <button @click="router.push('/athletes')" class="bg-white border border-gray-200 rounded-xl p-6 text-left hover:border-code8-gold hover:shadow-md transition-all group">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-lg bg-code8-gold/10 flex items-center justify-center group-hover:bg-code8-gold/20 transition-colors">
            <svg class="w-6 h-6 text-code8-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
          </div>
          <div>
            <h2 class="text-lg font-bold text-gray-900">Athletes</h2>
            <p class="text-sm text-gray-500">Roster, profiles, sync, and system matching</p>
          </div>
        </div>
      </button>

      <button @click="router.push('/presentation')" class="bg-white border border-gray-200 rounded-xl p-6 text-left hover:border-code8-gold hover:shadow-md transition-all group">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center group-hover:bg-blue-100 transition-colors">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
          </div>
          <div>
            <h2 class="text-lg font-bold text-gray-900">Presentation Sheet</h2>
            <p class="text-sm text-gray-500">Athlete-facing data view</p>
          </div>
        </div>
      </button>

      <button v-if="isStaff" @click="router.push('/testing')" class="bg-white border border-gray-200 rounded-xl p-6 text-left hover:border-code8-gold hover:shadow-md transition-all group">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-lg bg-green-50 flex items-center justify-center group-hover:bg-green-100 transition-colors">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>
          </div>
          <div>
            <h2 class="text-lg font-bold text-gray-900">Testing Stations</h2>
            <p class="text-sm text-gray-500">Standing reach, vertical, broad jump, sprint upload</p>
          </div>
        </div>
      </button>

      <button v-if="isStaff" @click="router.push('/evaluation')" class="bg-white border border-gray-200 rounded-xl p-6 text-left hover:border-code8-gold hover:shadow-md transition-all group">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-lg bg-purple-50 flex items-center justify-center group-hover:bg-purple-100 transition-colors">
            <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
          </div>
          <div>
            <h2 class="text-lg font-bold text-gray-900">Evaluation Hub</h2>
            <p class="text-sm text-gray-500">Coach notes and rich-text evaluations</p>
          </div>
        </div>
      </button>
    </div>

    <!-- Admin section -->
    <div v-if="isAdmin" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <button @click="router.push('/admin')" class="bg-white border border-gray-200 rounded-xl p-6 text-left hover:border-code8-gold hover:shadow-md transition-all group">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-lg bg-red-50 flex items-center justify-center group-hover:bg-red-100 transition-colors">
            <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
          </div>
          <div>
            <h2 class="text-lg font-bold text-gray-900">Admin Portal</h2>
            <p class="text-sm text-gray-500">User roles, account management</p>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>
