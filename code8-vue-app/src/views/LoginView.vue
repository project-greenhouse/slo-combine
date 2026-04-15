<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/authStore';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const email = ref('');
const password = ref('');
const isSignup = ref(false);
const errorMsg = ref('');
const isLoading = ref(false);
const birthDate = ref('');
const gender = ref('');
const gradYear = ref('');
const schoolGrade = ref('');
const heightInches = ref('');
const limbDominance = ref('');
const sports = ref('');
const positions = ref('');
const currentSchool = ref('');

const handleSubmit = async () => {
  try {
    errorMsg.value = '';
    isLoading.value = true;
    if (isSignup.value) {
      await authStore.registerAthlete(email.value, password.value, {
        BirthDate: birthDate.value,
        BirthYear: birthDate.value ? birthDate.value.split('-')[0] : '',
        BirthMonth: birthDate.value ? birthDate.value.split('-')[1] : '',
        Gender: gender.value,
        GradYear: gradYear.value,
        SchoolGrade: schoolGrade.value,
        HeightInches: heightInches.value,
        LimbDominance: limbDominance.value,
        Sports: sports.value,
        Positions: positions.value,
        CurrentSchool: currentSchool.value
      });
    } else {
      await authStore.login(email.value, password.value);
    }
    router.push('/dashboard');
  } catch (err: any) {
    errorMsg.value = err.message || 'An error occurred. Please try again.';
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  if (route.query.signup === 'true') {
    isSignup.value = true;
  }
});
</script>

<template>
  <div class="min-h-screen bg-code8-dark flex flex-col justify-center items-center px-6 relative overflow-hidden">
    <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-code8-gold/10 rounded-full blur-[120px] pointer-events-none"></div>

    <div class="w-full max-w-md bg-gray-900/80 backdrop-blur-xl border border-gray-800 p-8 rounded-3xl shadow-2xl relative z-10">
      <div class="flex justify-center mb-8"><img src="/code8perf_logo.png" alt="Code 8" class="h-16 w-auto object-contain" /></div>
      <h2 class="text-2xl font-black text-white text-center tracking-tight mb-6 uppercase">{{ isSignup ? 'Athlete Registration' : 'Login' }}</h2>

      <form @submit.prevent="handleSubmit" class="space-y-4 max-h-[60vh] overflow-y-auto px-1 custom-scrollbar">
        <div>
          <label class="block text-sm font-semibold text-gray-400 mb-1">Email *</label>
          <input v-model="email" type="email" required class="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="athlete@example.com" />
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-400 mb-1">Password *</label>
          <input v-model="password" type="password" required class="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="••••••••" />
        </div>
        
        <!-- Extended Athlete Profile Fields -->
        <div class="grid grid-cols-2 gap-3 pt-2" v-if="isSignup">
          <div>
            <label class="block text-xs font-semibold text-gray-400 mb-1">Birth Date</label>
            <input v-model="birthDate" type="date" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-400 mb-1">Gender</label>
            <select v-model="gender" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold">
              <option value="">Select</option>
              <option value="M">Male</option>
              <option value="F">Female</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-400 mb-1">Grad Year</label>
            <input v-model="gradYear" type="number" placeholder="2025" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-400 mb-1">School Grade</label>
            <input v-model="schoolGrade" type="number" placeholder="12" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-400 mb-1">Height (in)</label>
            <input v-model="heightInches" type="number" placeholder="72" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-400 mb-1">Limb Dominance</label>
            <select v-model="limbDominance" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold">
              <option value="">Select</option>
              <option value="Right">Right</option>
              <option value="Left">Left</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="block text-xs font-semibold text-gray-400 mb-1">Sport(s)</label>
            <input v-model="sports" type="text" placeholder="Football, Track" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div class="col-span-2">
            <label class="block text-xs font-semibold text-gray-400 mb-1">Positions</label>
            <input v-model="positions" type="text" placeholder="Football: QB, Track: 100m" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div class="col-span-2">
            <label class="block text-xs font-semibold text-gray-400 mb-1">Current School</label>
            <input v-model="currentSchool" type="text" placeholder="SLO High School" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
        </div>

        <div v-if="errorMsg" class="text-red-500 text-sm font-medium text-center bg-red-500/10 py-2 rounded-lg border border-red-500/20">{{ errorMsg }}</div>
        <button type="submit" :disabled="isLoading" class="w-full bg-gradient-to-r from-code8-gold to-yellow-500 text-code8-dark font-black text-lg px-4 py-3 rounded-xl hover:shadow-[0_0_20px_rgba(225,193,115,0.3)] transition-all flex justify-center items-center mt-2">
          <span v-if="isLoading" class="w-6 h-6 border-2 border-code8-dark border-t-transparent rounded-full animate-spin"></span><span v-else>{{ isSignup ? 'Create Account' : 'Access Hub' }}</span>
        </button>
      </form>
      
      <div class="mt-6 text-center">
        <button @click="isSignup = !isSignup; errorMsg = ''" class="text-sm text-gray-400 hover:text-white transition-colors">
          {{ isSignup ? 'Already have an account? Log in' : 'Are you an Athlete? Sign up here' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(31, 41, 55, 0.5); 
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.5); 
  border-radius: 4px;
}
</style>