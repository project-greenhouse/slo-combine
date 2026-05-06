<script setup lang="ts">
import { ref } from 'vue';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../firebase/config';

const targetEmail = ref('');
const targetRole = ref('athlete');
const athleteName = ref('');
const statusMsg = ref('');
const isError = ref(false);
const isLoading = ref(false);

const createEmail = ref('');
const createPassword = ref('');
const createRole = ref('coach');
const createStatusMsg = ref('');
const createIsError = ref(false);
const createIsLoading = ref(false);

const setUserRole = async () => {
  if (!targetEmail.value) return;
  isLoading.value = true;
  statusMsg.value = '';
  isError.value = false;
  try {
    const setRoleFn = httpsCallable(functions, 'set_user_role');
    const result = await setRoleFn({
      email: targetEmail.value,
      role: targetRole.value,
      athlete_name: targetRole.value === 'athlete' ? athleteName.value : null
    });
    const data = result.data as any;
    if (data.status === 'success') {
      statusMsg.value = data.message;
      targetEmail.value = '';
      athleteName.value = '';
    } else {
      isError.value = true;
      statusMsg.value = data.message;
    }
  } catch (err: any) {
    isError.value = true;
    statusMsg.value = err.message || 'An error occurred.';
  } finally {
    isLoading.value = false;
  }
};

const handleCreateUser = async () => {
  if (!createEmail.value || !createPassword.value) return;
  createIsLoading.value = true;
  createStatusMsg.value = '';
  createIsError.value = false;
  try {
    const createFn = httpsCallable(functions, 'admin_create_user');
    const result = await createFn({
      email: createEmail.value,
      password: createPassword.value,
      role: createRole.value,
      athlete_name: null
    });
    const data = result.data as any;
    if (data.status === 'success') {
      createStatusMsg.value = data.message;
      createEmail.value = '';
      createPassword.value = '';
    } else {
      createIsError.value = true;
      createStatusMsg.value = data.message;
    }
  } catch (err: any) {
    createIsError.value = true;
    createStatusMsg.value = err.message || 'An error occurred.';
  } finally {
    createIsLoading.value = false;
  }
};
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-3xl font-bold text-gray-900 mb-6">Admin Portal</h1>

    <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
      <h2 class="text-xl font-bold text-gray-900 mb-2">Manage User Roles</h2>
      <p class="text-sm text-gray-500 mb-6 pb-4 border-b border-gray-100">
        Assign roles to existing user accounts. If assigning the "athlete" role, provide their exact roster name.
      </p>
      <form @submit.prevent="setUserRole" class="space-y-5">
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">User's Email</label>
          <input v-model="targetEmail" type="email" required class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="user@example.com" />
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Account Role</label>
          <select v-model="targetRole" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors">
            <option value="athlete">Athlete</option>
            <option value="coach">Coach</option>
            <option value="admin">Administrator</option>
          </select>
        </div>
        <div v-if="targetRole === 'athlete'">
          <label class="block text-sm font-semibold text-gray-700 mb-1">Exact Roster Name</label>
          <input v-model="athleteName" type="text" required class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="e.g. Colbin Garrison" />
        </div>
        <div v-if="statusMsg" :class="['text-sm font-medium p-3 rounded-lg', isError ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-green-50 text-green-700 border border-green-100']">{{ statusMsg }}</div>
        <button type="submit" :disabled="isLoading" class="w-full bg-code8-dark text-white font-bold text-base px-4 py-3 rounded-lg hover:bg-gray-800 transition-all flex justify-center items-center">
          <span v-if="isLoading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span><span v-else>Update Permissions</span>
        </button>
      </form>
    </div>

    <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mt-8">
      <h2 class="text-xl font-bold text-gray-900 mb-2">Create New User</h2>
      <p class="text-sm text-gray-500 mb-6 pb-4 border-b border-gray-100">
        Directly create a new Coach or Admin account.
      </p>
      <form @submit.prevent="handleCreateUser" class="space-y-5">
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Email</label>
          <input v-model="createEmail" type="email" required class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="newuser@example.com" />
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Temporary Password</label>
          <input v-model="createPassword" type="password" required class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="••••••••" minlength="6" />
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Account Role</label>
          <select v-model="createRole" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors">
            <option value="coach">Coach</option>
            <option value="admin">Administrator</option>
          </select>
        </div>
        <div v-if="createStatusMsg" :class="['text-sm font-medium p-3 rounded-lg', createIsError ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-green-50 text-green-700 border border-green-100']">{{ createStatusMsg }}</div>
        <button type="submit" :disabled="createIsLoading" class="w-full bg-code8-dark text-white font-bold text-base px-4 py-3 rounded-lg hover:bg-gray-800 transition-all flex justify-center items-center">
          <span v-if="createIsLoading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span><span v-else>Create Account</span>
        </button>
      </form>
    </div>
  </div>
</template>
