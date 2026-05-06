<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../firebase/config';

const router = useRouter();

const stations = [
  { route: '/testing/standing-reach', label: 'Standing Reach', desc: 'Measure standing reach height (1 value per athlete)', icon: 'M7 11l5-5m0 0l5 5m-5-5v12', color: 'bg-blue-50 text-blue-600 group-hover:bg-blue-100' },
  { route: '/testing/vertical', label: 'Vertical Jump', desc: 'Max touch height — vertical auto-calculated from reach', icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6', color: 'bg-green-50 text-green-600 group-hover:bg-green-100' },
  { route: '/testing/broad-jump', label: 'Broad Jump', desc: '2 attempts — best highlighted automatically', icon: 'M13 5l7 7-7 7M5 5l7 7-7 7', color: 'bg-purple-50 text-purple-600 group-hover:bg-purple-100' },
];

// Swift upload
const sprintFile = ref<File | null>(null);
const sprintMsg = ref('');
const sprintIsError = ref(false);
const sprintLoading = ref(false);

const handleFileChange = (e: Event) => {
  const t = e.target as HTMLInputElement;
  if (t.files?.length) sprintFile.value = t.files[0];
};

const handleSprintUpload = async () => {
  if (!sprintFile.value) return;
  sprintLoading.value = true; sprintMsg.value = ''; sprintIsError.value = false;
  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      const fn = httpsCallable(functions, 'upload_roster_csv');
      const result = await fn({ csv_data: e.target?.result as string });
      const data = result.data as any;
      if (data.status === 'success') {
        sprintMsg.value = data.message || 'Upload successful';
        sprintFile.value = null;
        const fi = document.getElementById('sprintFileInput') as HTMLInputElement;
        if (fi) fi.value = '';
      } else { sprintIsError.value = true; sprintMsg.value = data.message; }
    } catch (err: any) { sprintIsError.value = true; sprintMsg.value = err.message || 'Error'; }
    finally { sprintLoading.value = false; }
  };
  reader.readAsText(sprintFile.value);
};
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-2xl md:text-3xl font-bold text-gray-900 mb-6">Testing Stations</h1>

    <!-- Station cards -->
    <div class="space-y-3 mb-8">
      <button v-for="s in stations" :key="s.route" @click="router.push(s.route)"
        class="w-full bg-white border border-gray-200 rounded-xl p-5 text-left hover:border-code8-gold hover:shadow-md transition-all group">
        <div class="flex items-center gap-4">
          <div :class="['w-12 h-12 rounded-lg flex items-center justify-center transition-colors flex-shrink-0', s.color]">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="s.icon" /></svg>
          </div>
          <div class="min-w-0">
            <h2 class="text-lg font-bold text-gray-900">{{ s.label }}</h2>
            <p class="text-sm text-gray-500">{{ s.desc }}</p>
          </div>
          <svg class="w-5 h-5 text-gray-300 group-hover:text-code8-gold flex-shrink-0 ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
        </div>
      </button>
    </div>

    <!-- Swift Sprint Upload -->
    <div class="bg-white border border-gray-200 rounded-xl p-6">
      <h2 class="text-lg font-bold text-gray-900 mb-1">Swift Sprint Upload</h2>
      <p class="text-sm text-gray-500 mb-4">Upload a CSV file from the Swift timing system with sprint and agility data.</p>

      <form @submit.prevent="handleSprintUpload" class="space-y-4">
        <input id="sprintFileInput" type="file" accept=".csv" @change="handleFileChange"
          class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200" />
        <div v-if="sprintMsg" :class="['text-sm font-medium p-3 rounded-lg', sprintIsError ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800']">{{ sprintMsg }}</div>
        <button type="submit" :disabled="sprintLoading || !sprintFile"
          class="w-full py-3 rounded-lg text-base font-bold text-white bg-code8-gold hover:bg-yellow-600 active:bg-yellow-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
          {{ sprintLoading ? 'Uploading...' : 'Upload Sprint Data' }}
        </button>
      </form>
    </div>
  </div>
</template>
