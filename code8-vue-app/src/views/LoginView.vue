<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/authStore';

type Mode = 'login' | 'verify' | 'request-admin' | 'verify-success' | 'request-success';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const mode = ref<Mode>('login');
const errorMsg = ref('');
const isLoading = ref(false);

// Login fields
const email = ref('');
const password = ref('');

// Verify fields (first-time athlete)
const verifyEmail = ref('');
const verifyBirthDate = ref('');
const verifyAthleteName = ref('');

// Request admin verification fields
const requestName = ref('');
const requestEmail = ref('');
const requestBirthDate = ref('');
const requestMessage = ref('');

const handleLogin = async () => {
  errorMsg.value = '';
  isLoading.value = true;
  try {
    await authStore.login(email.value, password.value);
    router.push('/dashboard');
  } catch (err: any) {
    errorMsg.value = err.message || 'Login failed.';
  } finally {
    isLoading.value = false;
  }
};

// Auto-format MM/DD/YYYY as user types — inserts slashes after MM and DD
const formatDateInput = (e: Event, field: 'verifyBirthDate' | 'requestBirthDate') => {
  const input = e.target as HTMLInputElement;
  let v = input.value.replace(/\D/g, '');
  if (v.length > 8) v = v.slice(0, 8);
  let formatted = v;
  if (v.length >= 3 && v.length <= 4) formatted = `${v.slice(0, 2)}/${v.slice(2)}`;
  else if (v.length >= 5) formatted = `${v.slice(0, 2)}/${v.slice(2, 4)}/${v.slice(4)}`;
  if (field === 'verifyBirthDate') verifyBirthDate.value = formatted;
  else requestBirthDate.value = formatted;
};

const isValidDate = (s: string): boolean => /^\d{2}\/\d{2}\/\d{4}$/.test(s);

const handleVerify = async () => {
  errorMsg.value = '';
  if (!isValidDate(verifyBirthDate.value)) {
    errorMsg.value = 'Birth date must be in MM/DD/YYYY format.';
    return;
  }
  isLoading.value = true;
  try {
    const res = await authStore.verifyAthleteIdentity(verifyEmail.value, verifyBirthDate.value);
    if (res.status === 'success' || res.status === 'exists') {
      // Trigger Firebase password reset email so they can set their own password
      try {
        await authStore.sendPasswordReset(verifyEmail.value);
      } catch { /* still show success — fn-side email is the source of truth */ }
      verifyAthleteName.value = res.athlete_name || '';
      mode.value = 'verify-success';
    } else if (res.code === 'email_not_found') {
      errorMsg.value = '';
      // Auto-redirect to admin request flow with prefilled email
      requestEmail.value = verifyEmail.value;
      requestBirthDate.value = verifyBirthDate.value;
      mode.value = 'request-admin';
    } else {
      errorMsg.value = res.message || 'Verification failed.';
    }
  } catch (err: any) {
    errorMsg.value = err.message || 'Verification failed.';
  } finally {
    isLoading.value = false;
  }
};

const handleRequestAdmin = async () => {
  errorMsg.value = '';
  isLoading.value = true;
  try {
    const res = await authStore.requestAdminVerification(
      requestName.value, requestEmail.value, requestBirthDate.value, requestMessage.value
    );
    if (res.status === 'success') {
      mode.value = 'request-success';
    } else {
      errorMsg.value = res.message || 'Request failed.';
    }
  } catch (err: any) {
    errorMsg.value = err.message || 'Request failed.';
  } finally {
    isLoading.value = false;
  }
};

const switchMode = (m: Mode) => {
  mode.value = m;
  errorMsg.value = '';
};

onMounted(() => {
  if (route.query.signup === 'true' || route.query.verify === 'true') {
    mode.value = 'verify';
  }
});
</script>

<template>
  <div class="min-h-screen bg-code8-dark flex flex-col justify-center items-center px-6 py-8 relative overflow-hidden">
    <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-code8-gold/10 rounded-full blur-[120px] pointer-events-none"></div>

    <div class="w-full max-w-md bg-gray-900/80 backdrop-blur-xl border border-gray-800 p-8 rounded-3xl shadow-2xl relative z-10">
      <div class="flex justify-center mb-6"><img src="/code8perf_logo.png" alt="Code 8" class="h-14 w-auto object-contain" /></div>

      <!-- ─── LOGIN ─── -->
      <template v-if="mode === 'login'">
        <h2 class="text-2xl font-black text-white text-center tracking-tight mb-6 uppercase">Login</h2>
        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-gray-400 mb-1">Email</label>
            <input v-model="email" type="email" required autocomplete="email" class="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-400 mb-1">Password</label>
            <input v-model="password" type="password" required autocomplete="current-password" class="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div v-if="errorMsg" class="text-red-400 text-sm font-medium text-center bg-red-500/10 py-2 rounded-lg border border-red-500/20">{{ errorMsg }}</div>
          <button type="submit" :disabled="isLoading" class="w-full bg-gradient-to-r from-code8-gold to-yellow-500 text-code8-dark font-black text-lg px-4 py-3 rounded-xl hover:shadow-[0_0_20px_rgba(225,193,115,0.3)] transition-all flex justify-center items-center mt-2 disabled:opacity-50">
            <span v-if="isLoading" class="w-6 h-6 border-2 border-code8-dark border-t-transparent rounded-full animate-spin"></span>
            <span v-else>Sign In</span>
          </button>
        </form>
        <div class="mt-6 text-center space-y-2">
          <button @click="switchMode('verify')" class="block w-full text-sm text-gray-400 hover:text-code8-gold transition-colors">First time? Verify your athlete account →</button>
        </div>
      </template>

      <!-- ─── VERIFY (First-time athlete) ─── -->
      <template v-if="mode === 'verify'">
        <h2 class="text-xl font-black text-white text-center tracking-tight mb-2 uppercase">Verify Your Account</h2>
        <p class="text-sm text-gray-400 text-center mb-6">Confirm your registration with your email and birth date. We'll send you a link to set your password.</p>
        <form @submit.prevent="handleVerify" class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-gray-400 mb-1">Email used at registration</label>
            <input v-model="verifyEmail" type="email" required autocomplete="email" class="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-400 mb-1">Birth Date <span class="text-gray-500 font-normal">(MM/DD/YYYY)</span></label>
            <input v-model="verifyBirthDate" type="text" required inputmode="numeric" placeholder="MM/DD/YYYY" pattern="\d{2}/\d{2}/\d{4}" maxlength="10" @input="formatDateInput($event, 'verifyBirthDate')" class="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
            <p class="text-xs text-gray-500 mt-1">Example: 08/15/2010</p>
          </div>
          <div v-if="errorMsg" class="text-red-400 text-sm font-medium text-center bg-red-500/10 py-2 rounded-lg border border-red-500/20">{{ errorMsg }}</div>
          <button type="submit" :disabled="isLoading" class="w-full bg-gradient-to-r from-code8-gold to-yellow-500 text-code8-dark font-black text-lg px-4 py-3 rounded-xl hover:shadow-[0_0_20px_rgba(225,193,115,0.3)] transition-all flex justify-center items-center mt-2 disabled:opacity-50">
            <span v-if="isLoading" class="w-6 h-6 border-2 border-code8-dark border-t-transparent rounded-full animate-spin"></span>
            <span v-else>Verify Identity</span>
          </button>
        </form>
        <div class="mt-6 text-center space-y-2">
          <button @click="switchMode('login')" class="block w-full text-sm text-gray-400 hover:text-code8-gold transition-colors">Already have a password? Sign in →</button>
          <button @click="switchMode('request-admin')" class="block w-full text-sm text-gray-400 hover:text-code8-gold transition-colors">No email on file? Request admin help →</button>
        </div>
      </template>

      <!-- ─── VERIFY SUCCESS ─── -->
      <template v-if="mode === 'verify-success'">
        <div class="text-center">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
            <svg class="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
          </div>
          <h2 class="text-xl font-black text-white tracking-tight mb-2 uppercase">Welcome{{ verifyAthleteName ? `, ${verifyAthleteName}` : '' }}!</h2>
          <p class="text-sm text-gray-400 mb-6">We've sent a password setup link to <strong class="text-white">{{ verifyEmail }}</strong>. Open the email and follow the link to set your password, then come back here to sign in.</p>
          <button @click="switchMode('login')" class="w-full bg-gray-800 hover:bg-gray-700 text-white font-bold px-4 py-3 rounded-xl transition-colors">Back to Sign In</button>
        </div>
      </template>

      <!-- ─── REQUEST ADMIN HELP ─── -->
      <template v-if="mode === 'request-admin'">
        <h2 class="text-xl font-black text-white text-center tracking-tight mb-2 uppercase">Request Admin Verification</h2>
        <p class="text-sm text-gray-400 text-center mb-6">If you don't have an email on file, send a request to admin. They'll add your email and you'll be able to verify.</p>
        <form @submit.prevent="handleRequestAdmin" class="space-y-3">
          <div>
            <label class="block text-xs font-semibold text-gray-400 mb-1">Full Name</label>
            <input v-model="requestName" type="text" required class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-400 mb-1">Email to add to your account</label>
            <input v-model="requestEmail" type="email" required class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-400 mb-1">Birth Date <span class="text-gray-500 font-normal">(MM/DD/YYYY)</span></label>
            <input v-model="requestBirthDate" type="text" inputmode="numeric" placeholder="MM/DD/YYYY" pattern="\d{2}/\d{2}/\d{4}" maxlength="10" @input="formatDateInput($event, 'requestBirthDate')" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-400 mb-1">Note (optional)</label>
            <textarea v-model="requestMessage" rows="3" placeholder="Any additional info to help identify you..." class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold"></textarea>
          </div>
          <div v-if="errorMsg" class="text-red-400 text-sm font-medium text-center bg-red-500/10 py-2 rounded-lg border border-red-500/20">{{ errorMsg }}</div>
          <button type="submit" :disabled="isLoading" class="w-full bg-gradient-to-r from-code8-gold to-yellow-500 text-code8-dark font-black px-4 py-2.5 rounded-xl hover:shadow-[0_0_20px_rgba(225,193,115,0.3)] transition-all flex justify-center items-center disabled:opacity-50">
            <span v-if="isLoading" class="w-5 h-5 border-2 border-code8-dark border-t-transparent rounded-full animate-spin"></span>
            <span v-else>Send Request</span>
          </button>
        </form>
        <div class="mt-4 text-center">
          <button @click="switchMode('verify')" class="text-sm text-gray-400 hover:text-code8-gold transition-colors">← Back</button>
        </div>
      </template>

      <!-- ─── REQUEST SUCCESS ─── -->
      <template v-if="mode === 'request-success'">
        <div class="text-center">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
            <svg class="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </div>
          <h2 class="text-xl font-black text-white tracking-tight mb-2 uppercase">Request Sent</h2>
          <p class="text-sm text-gray-400 mb-6">Your request has been delivered to admin. They'll review it and add your email so you can verify. You'll typically hear back within a day.</p>
          <button @click="switchMode('login')" class="w-full bg-gray-800 hover:bg-gray-700 text-white font-bold px-4 py-3 rounded-xl transition-colors">Back to Sign In</button>
        </div>
      </template>
    </div>
  </div>
</template>
