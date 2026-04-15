<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/authStore';

const router = useRouter();
const authStore = useAuthStore();

const handleLogout = async () => {
  await authStore.logout();
};
</script>

<template>
  <div class="min-h-screen bg-code8-dark text-white selection:bg-code8-gold selection:text-code8-dark overflow-x-hidden relative">
    <!-- Dynamic Animated Background Glows -->
    <div class="fixed inset-0 pointer-events-none z-0">
      <div class="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] bg-code8-gold/20 rounded-full blur-[120px] mix-blend-screen animate-pulse" style="animation-duration: 7s;"></div>
      <div class="absolute top-[30%] right-[-10%] w-[45vw] h-[45vw] bg-red-700/20 rounded-full blur-[120px] mix-blend-screen animate-pulse" style="animation-duration: 9s; animation-delay: 1s;"></div>
      <div class="absolute bottom-[-20%] left-[10%] w-[60vw] h-[60vw] bg-blue-800/20 rounded-full blur-[120px] mix-blend-screen animate-pulse" style="animation-duration: 11s; animation-delay: 2s;"></div>
    </div>

    <!-- Navbar -->
    <nav class="container mx-auto px-6 py-6 flex items-center justify-between relative z-10">
      <div class="flex items-center">
        <img src="/code8perf_logo.png" alt="Code 8 Performance" class="h-14 w-auto object-contain" />
      </div>
      <div class="flex items-center gap-4">
        <template v-if="authStore.isAuthenticated">
          <button @click="router.push(authStore.userRole === 'athlete' ? '/presentation' : '/dashboard')" class="hidden md:block text-sm font-semibold hover:text-code8-gold transition-colors px-4 py-2 rounded-full border border-transparent hover:border-gray-800">
            Go to {{ authStore.userRole === 'athlete' ? 'Presentation' : 'Dashboard' }}
          </button>
          <button @click="handleLogout" class="bg-white/10 hover:bg-white/20 text-white border border-white/10 backdrop-blur-md px-6 py-2 rounded-full text-sm font-bold transition-all">
            Logout
          </button>
        </template>
        <template v-else>
          <button @click="router.push('/login')" class="hidden md:block text-sm font-semibold hover:text-code8-gold transition-colors px-4 py-2 rounded-full border border-transparent hover:border-gray-800">
            Login
          </button>
          <button @click="router.push('/login?signup=true')" class="bg-gradient-to-r from-code8-gold to-yellow-500 text-code8-dark hover:shadow-[0_0_20px_rgba(225,193,115,0.4)] px-6 py-2 rounded-full text-sm font-bold transition-all">
            Sign Up
          </button>
        </template>
      </div>
    </nav>

    <!-- Hero Section -->
    <main class="container mx-auto px-6 pt-12 pb-40 flex flex-col items-center relative z-10 text-center gap-16">
      
      <!-- Floating Hero Visual (No background box) -->
      <div class="w-full max-w-4xl mx-auto flex justify-center animate-float mt-8">
        <img src="/SLO-CC-TRANS.PNG" alt="SLO County Combine" class="w-11/12 md:w-full h-auto object-contain drop-shadow-[0_20px_50px_rgba(225,193,115,0.15)]" />
      </div>

      <!-- Text Content -->
      <div class="w-full max-w-3xl space-y-10 flex flex-col items-center">
        
        <h1 class="text-6xl md:text-7xl lg:text-8xl font-black leading-[1.05] tracking-tight">
          MEASURE.<br />
          ANALYZE.<br />
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-code8-gold to-yellow-200 drop-shadow-sm">ELEVATE.</span>
        </h1>
        
        <p class="text-gray-400 text-xl md:text-2xl leading-relaxed font-medium">
          The ultimate athletic testing experience. State-of-the-art laser timing, dual force plates, and professional biomechanical analysis.
        </p>
        
        <div class="pt-6">
          <button v-if="authStore.isAuthenticated" @click="router.push(authStore.userRole === 'athlete' ? '/presentation' : '/dashboard')" class="bg-gradient-to-r from-code8-gold to-yellow-500 text-code8-dark px-12 py-5 rounded-full font-black text-xl hover:shadow-[0_0_50px_rgba(225,193,115,0.5)] hover:-translate-y-2 transition-all duration-300">
            View Athlete Reports
          </button>
          <button v-else @click="router.push('/login?signup=true')" class="bg-gradient-to-r from-code8-gold to-yellow-500 text-code8-dark px-12 py-5 rounded-full font-black text-xl hover:shadow-[0_0_50px_rgba(225,193,115,0.5)] hover:-translate-y-2 transition-all duration-300">
            Athlete Sign Up
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
@keyframes float {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-25px); }
  100% { transform: translateY(0px); }
}
.animate-float {
  animation: float 8s ease-in-out infinite;
}
</style>