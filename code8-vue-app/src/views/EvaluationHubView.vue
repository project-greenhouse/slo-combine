<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue';
import { collection, query, where, onSnapshot, addDoc, serverTimestamp, deleteDoc, doc, updateDoc } from 'firebase/firestore';
import { db } from '../firebase/config';
import { QuillEditor } from '@vueup/vue-quill';
import '@vueup/vue-quill/dist/vue-quill.snow.css';
import { useAthleteStore } from '../stores/athleteStore';
import { useAuthStore } from '../stores/authStore';

const store = useAthleteStore();
const authStore = useAuthStore();

onMounted(() => {
  store.fetchRoster();
});

// Computed properties to safely extract arrays from the Firestore metrics
const vertData = computed(() => store.metrics?.standing_vert || []);
const broadData = computed(() => store.metrics?.broad_jump || []);
const fpCmjData = computed(() => store.metrics?.force_plate_cmj || []);
const fpMrData = computed(() => store.metrics?.force_plate_mr || []);

// Process Sprint Data: Group by ActivityIdentifier to form discrete trials
const processedSprints = computed(() => {
  const raw = store.metrics?.sprint40 || [];
  const trialsMap: Record<string, any> = {};
  
  raw.forEach((row: any) => {
    if (!row.Distance) return; // Skip 0 distance rows (warmup/init)
    const id = row.ActivityIdentifier;
    if (!trialsMap[id]) trialsMap[id] = { timestamp: row.ActivityTimestamp };
    trialsMap[id][row.Distance] = row.Total;
  });

  return Object.values(trialsMap).map((t, idx) => ({
    name: `Trial ${idx + 1}`,
    split10: t[10] ? Number(t[10]).toFixed(2) : '--',
    total40: t[40] ? Number(t[40]).toFixed(2) : '--'
  }));
});

// Process Pro Agility Data: Group by ActivityIdentifier to form discrete trials
const processedAgility = computed(() => {
  const raw = store.metrics?.pro_agility || [];
  const trialsMap: Record<string, any> = {};
  
  raw.forEach((row: any) => {
    if (!row.Distance) return; // Skip 0 distance rows
    const id = row.ActivityIdentifier;
    if (!trialsMap[id]) trialsMap[id] = { timestamp: row.ActivityTimestamp };
    trialsMap[id][row.Distance] = row.Total;
  });

  return Object.values(trialsMap).map((t, idx) => ({
    name: `Trial ${idx + 1}`,
    split5: t[5] ? Number(t[5]).toFixed(2) : '--',
    split10: t[10] ? Number(t[10]).toFixed(2) : '--',
    split15: t[15] ? Number(t[15]).toFixed(2) : '--',
    total20: t[20] ? Number(t[20]).toFixed(2) : '--'
  }));
});

// Rank Coloring Helper
const getRankClass = (val: number | null | undefined) => {
  if (!val) return 'hidden';
  if (val >= 75) return 'bg-code8-green/10 text-code8-green border-code8-green';
  if (val >= 25) return 'bg-code8-amber/10 text-yellow-600 border-code8-amber';
  return 'bg-code8-red/10 text-code8-red border-code8-red';
};

// Valor Specific Score Coloring
const getValorClass = (val: number | null | undefined) => {
  if (!val) return 'hidden';
  if (val >= 85) return 'bg-code8-green/10 text-code8-green border-code8-green';
  if (val >= 70) return 'bg-code8-amber/10 text-yellow-600 border-code8-amber';
  return 'bg-code8-red/10 text-code8-red border-code8-red';
};

const handleAthleteChange = (event: Event) => {
  const selectElement = event.target as HTMLSelectElement;
  const athleteName = selectElement.value;
  const athlete = store.roster.find(a => a.Name === athleteName);
  if (athlete) {
    store.selectAthlete(athlete);
  }
};

// --- Diary Entry / Commentary Logic ---
const newComment = ref('');
const previousComments = ref<any[]>([]);
const isSaving = ref(false);
let unsubscribeComments: (() => void) | null = null;
const editingEntryId = ref<string | null>(null);

const cancelEdit = () => {
  editingEntryId.value = null;
  newComment.value = '';
  const quillInstance = document.querySelector('.ql-editor') as HTMLElement;
  if (quillInstance) quillInstance.innerHTML = '';
};

const editEntry = (entry: any) => {
  editingEntryId.value = entry.id;
  newComment.value = entry.summary_html;
  const quillInstance = document.querySelector('.ql-editor') as HTMLElement;
  if (quillInstance) quillInstance.innerHTML = entry.summary_html;
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

const fetchComments = () => {
  if (unsubscribeComments) {
    unsubscribeComments();
    unsubscribeComments = null;
  }
  previousComments.value = [];
  cancelEdit(); // Reset edit state if user switches athletes

  if (store.selectedAthlete?.Name) {
    // We query by Name to ensure compatibility with your legacy Supabase imports
    const q = query(
      collection(db, 'athlete_summaries'),
      where('athlete_name', '==', store.selectedAthlete.Name)
    );

    unsubscribeComments = onSnapshot(q, (snap) => {
      const comments = snap.docs.map(doc => ({ id: doc.id, ...doc.data() } as any));
      // Sort locally descending (newest first)
      comments.sort((a, b) => {
        const timeA = a.created_at?.toMillis ? a.created_at.toMillis() : new Date(a.created_at || 0).getTime();
        const timeB = b.created_at?.toMillis ? b.created_at.toMillis() : new Date(b.created_at || 0).getTime();
        return timeB - timeA; 
      });
      previousComments.value = comments;
    }, (error) => {
      console.error("Evaluation Hub Snapshot Error:", error);
    });
  }
};

watch(() => store.selectedAthlete, fetchComments, { immediate: true });

onUnmounted(() => {
  if (unsubscribeComments) unsubscribeComments();
});

const saveComment = async () => {
  if (!newComment.value || newComment.value === '<p><br></p>') return;
  if (!store.selectedAthlete) return;

  isSaving.value = true;
  try {
    if (editingEntryId.value) {
      await updateDoc(doc(db, 'athlete_summaries', editingEntryId.value), {
        summary_html: newComment.value,
        updated_at: serverTimestamp()
      });
    } else {
      await addDoc(collection(db, 'athlete_summaries'), {
        athlete_uid: store.selectedAthlete.athlete_uid || null,
        athlete_name: store.selectedAthlete.Name,
        author: authStore.user?.displayName || authStore.user?.email || 'Coach',
        summary_html: newComment.value,
        created_at: serverTimestamp()
      });
    }
    
    cancelEdit();
  } catch (e) {
    console.error("Error saving comment:", e);
  } finally {
    isSaving.value = false;
  }
};

const deleteEntry = async (id: string) => {
  if (!confirm("Are you sure you want to delete this evaluation note? This cannot be undone.")) return;
  try {
    await deleteDoc(doc(db, 'athlete_summaries', id));
  } catch (err) {
    console.error("Error deleting entry:", err);
  }
};

const formatDate = (timestamp: any) => {
  if (!timestamp) return 'Just now';
  const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
  return date.toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
};
</script>

<template>
  <div>
    <div class="flex flex-col md:flex-row md:justify-between md:items-center mb-6 gap-4">
      <h1 class="text-3xl font-bold text-gray-900">Coach's Evaluation Hub</h1>
      
      <!-- Athlete Selector -->
      <div v-if="store.roster.length > 0" class="flex items-center gap-3">
        <label for="athlete-select" class="text-sm font-medium text-gray-700 whitespace-nowrap">Select Athlete:</label>
        <select 
          id="athlete-select"
          class="block w-full md:w-64 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-code8-gold focus:border-code8-gold sm:text-sm rounded-md shadow-sm bg-white border"
          :value="store.selectedAthlete?.Name || ''"
          @change="handleAthleteChange"
        >
          <option value="" disabled>-- Choose an Athlete --</option>
          <option v-for="athlete in store.roster" :key="athlete.Name" :value="athlete.Name">
            {{ athlete.Name }}
          </option>
        </select>
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-if="!store.selectedAthlete" class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col items-center justify-center h-64 text-center">
      <div class="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
        <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
      </div>
      <p class="text-gray-600 font-medium">Please select an athlete from the Dashboard to begin evaluation.</p>
      <router-link to="/" class="mt-4 text-code8-gold hover:text-yellow-600 font-semibold transition-colors">
        &larr; Back to Dashboard
      </router-link>
    </div>

    <!-- Active Evaluation View -->
    <div v-else class="flex flex-col gap-8 pb-12">
      
      <!-- Top Section: Data Grids (Full Width) -->
      <div class="w-full">
        <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div class="flex justify-between items-center mb-4 pb-4 border-b border-gray-100">
            <h2 class="text-xl font-bold text-gray-900">{{ store.selectedAthlete.Name }}'s Metrics</h2>
            <span class="px-3 py-1 bg-code8-gold/10 text-code8-dark text-xs font-bold rounded-full border border-code8-gold/20">
              {{ store.selectedAthlete.athlete_uid ? 'Database Linked' : 'No UID Found' }}
            </span>
          </div>
          
          <div v-if="store.metricsLoading" class="flex items-center gap-2 text-code8-gold font-semibold animate-pulse py-8">
            <svg class="animate-spin h-5 w-5 text-code8-gold" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Fetching metrics from Firestore...
          </div>
          
          <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Sprint 40 Table -->
            <div class="border border-gray-200 rounded-lg overflow-hidden">
              <div class="bg-gray-50 px-4 py-2 border-b border-gray-200 flex justify-between items-center">
                <span class="font-semibold text-sm text-gray-700">Sprint 40</span>
                <span :class="getRankClass(store.metrics?.ranks?.sprint40)" class="text-[10px] px-2 py-0.5 rounded border font-bold">{{ store.metrics?.ranks?.sprint40 }}th Pct</span>
              </div>
              <div class="p-4" v-if="processedSprints.length === 0"><p class="text-sm text-gray-500 italic">No data available.</p></div>
              <table class="w-full text-sm text-left text-gray-600" v-else>
                <thead class="text-xs text-gray-400 uppercase bg-white border-b border-gray-100">
                  <tr>
                    <th class="px-4 py-2 font-medium">Trial</th>
                    <th class="px-4 py-2 font-medium text-right">10yd Split</th>
                    <th class="px-4 py-2 font-medium text-right">40yd Total</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in processedSprints" :key="'sprint-'+idx" class="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors">
                    <td class="px-4 py-2 font-medium text-gray-800">{{ row.name }}</td>
                    <td class="px-4 py-2 font-mono text-gray-500 text-right">{{ row.split10 }}s</td>
                    <td class="px-4 py-2 font-mono text-gray-900 font-bold text-right">{{ row.total40 }}s</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Pro Agility Table -->
            <div class="border border-gray-200 rounded-lg overflow-hidden">
              <div class="bg-gray-50 px-4 py-2 border-b border-gray-200 flex justify-between items-center">
                <span class="font-semibold text-sm text-gray-700">Pro Agility (5-10-5)</span>
                <span :class="getRankClass(store.metrics?.ranks?.proAgility)" class="text-[10px] px-2 py-0.5 rounded border font-bold">{{ store.metrics?.ranks?.proAgility }}th Pct</span>
              </div>
              <div class="p-4" v-if="processedAgility.length === 0"><p class="text-sm text-gray-500 italic">No data available.</p></div>
              <table class="w-full text-sm text-left text-gray-600" v-else>
                <thead class="text-xs text-gray-400 uppercase bg-white border-b border-gray-100">
                  <tr>
                    <th class="px-4 py-2 font-medium">Trial</th>
                    <th class="px-2 py-2 font-medium text-right">5yd</th>
                    <th class="px-2 py-2 font-medium text-right">10yd</th>
                    <th class="px-2 py-2 font-medium text-right">15yd</th>
                    <th class="px-4 py-2 font-medium text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in processedAgility" :key="'agil-'+idx" class="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors">
                    <td class="px-4 py-2 font-medium text-gray-800">{{ row.name }}</td>
                    <td class="px-2 py-2 font-mono text-gray-500 text-right">{{ row.split5 }}</td>
                    <td class="px-2 py-2 font-mono text-gray-500 text-right">{{ row.split10 }}</td>
                    <td class="px-2 py-2 font-mono text-gray-500 text-right">{{ row.split15 }}</td>
                    <td class="px-4 py-2 font-mono text-gray-900 font-bold text-right">{{ row.total20 }}s</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Vertical Jump Display -->
            <div class="border border-gray-200 rounded-lg overflow-hidden flex flex-col">
              <div class="bg-gray-50 px-4 py-2 border-b border-gray-200 flex justify-between items-center">
                <span class="font-semibold text-sm text-gray-700">Standing Vertical</span>
                <span :class="getRankClass(store.metrics?.ranks?.verticalJump)" class="text-[10px] px-2 py-0.5 rounded border font-bold">{{ store.metrics?.ranks?.verticalJump }}th Pct</span>
              </div>
              <div class="p-4 flex-1 flex items-center justify-center" v-if="vertData.length === 0"><p class="text-sm text-gray-500 italic">No data available.</p></div>
              <div class="flex-1 flex flex-col items-center justify-center p-6 bg-white" v-else>
                <div class="flex items-baseline">
                  <span class="text-4xl font-black text-gray-900">{{ vertData[0].VerticalJump || '--' }}</span>
                  <span class="text-gray-400 ml-1 font-medium pb-1">in</span>
                </div>
                <div class="text-xs text-gray-400 mt-2 font-medium">
                  T1: {{ vertData[0].JumpHeight_1 || '-' }}" &bull; T2: {{ vertData[0].JumpHeight_2 || '-' }}" &bull; T3: {{ vertData[0].JumpHeight_3 || '-' }}"
                </div>
              </div>
            </div>

            <!-- Broad Jump Display -->
            <div class="border border-gray-200 rounded-lg overflow-hidden flex flex-col">
              <div class="bg-gray-50 px-4 py-2 border-b border-gray-200 flex justify-between items-center">
                <span class="font-semibold text-sm text-gray-700">Broad Jump</span>
                <span :class="getRankClass(store.metrics?.ranks?.broadJump)" class="text-[10px] px-2 py-0.5 rounded border font-bold">{{ store.metrics?.ranks?.broadJump }}th Pct</span>
              </div>
              <div class="p-4 flex-1 flex items-center justify-center" v-if="broadData.length === 0"><p class="text-sm text-gray-500 italic">No data available.</p></div>
              <div class="flex-1 flex flex-col items-center justify-center p-6 bg-white" v-else>
                <div class="flex items-baseline">
                  <span class="text-4xl font-black text-gray-900">{{ broadData[0].BestBroadJump || '--' }}</span>
                  <span class="text-gray-400 ml-1 font-medium pb-1">in</span>
                </div>
                <div class="text-xs text-gray-400 mt-2 font-medium">
                  T1: {{ broadData[0].BroadJump_1 || '-' }}" &bull; T2: {{ broadData[0].BroadJump_2 || '-' }}"
                </div>
              </div>
            </div>

            <!-- Valor Metrics -->
            <div class="border border-gray-200 rounded-lg overflow-hidden md:col-span-2">
              <div class="bg-gray-50 px-4 py-2 border-b border-gray-200 font-semibold text-sm text-gray-700">Movement Quality (Valor)</div>
              <div class="p-4" v-if="!store.metrics?.valor || (store.metrics.valor.Shoulder === 0 && store.metrics.valor.Ankle === 0)"><p class="text-sm text-gray-500 italic">No movement data available.</p></div>
              <div class="grid grid-cols-3 gap-4 p-4 bg-white" v-else>
                <div class="flex flex-col items-center">
                  <span class="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">Shoulder</span>
                  <span :class="getValorClass(store.metrics.valor.Shoulder)" class="text-xl font-black px-3 py-1 rounded border">{{ store.metrics.valor.Shoulder || '--' }}</span>
                </div>
                <div class="flex flex-col items-center border-l border-r border-gray-100">
                  <span class="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">Hip Hinge</span>
                  <span :class="getValorClass(store.metrics.valor.Hip)" class="text-xl font-black px-3 py-1 rounded border">{{ store.metrics.valor.Hip || '--' }}</span>
                </div>
                <div class="flex flex-col items-center">
                  <span class="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">Ankle</span>
                  <span :class="getValorClass(store.metrics.valor.Ankle)" class="text-xl font-black px-3 py-1 rounded border">{{ store.metrics.valor.Ankle || '--' }}</span>
                </div>
              </div>
            </div>

            <!-- Force Plate CMJ Table -->
            <div class="border border-gray-200 rounded-lg overflow-hidden md:col-span-2">
              <div class="bg-gray-50 px-4 py-2 border-b border-gray-200 flex justify-between items-center">
                <span class="font-semibold text-sm text-gray-700">Force Plate: Countermovement Jump (CMJ)</span>
                <span :class="getRankClass(store.metrics?.ranks?.fp_jump_height)" class="text-[10px] px-2 py-0.5 rounded border font-bold">Elite Rank (Jump Ht): {{ store.metrics?.ranks?.fp_jump_height }}th Pct</span>
              </div>
              <div class="p-4" v-if="fpCmjData.length === 0"><p class="text-sm text-gray-500 italic">No CMJ data available.</p></div>
              <table class="w-full text-sm text-left text-gray-600" v-else>
                <thead class="text-xs text-gray-400 uppercase bg-white border-b border-gray-100">
                  <tr>
                    <th class="px-4 py-2 font-medium">Jump Height</th>
                    <th class="px-4 py-2 font-medium">mRSI</th>
                    <th class="px-4 py-2 font-medium">Peak Rel. Power</th>
                    <th class="px-4 py-2 font-medium">Braking Asymmetry</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in fpCmjData" :key="'cmj-'+idx" class="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors">
                    <td class="px-4 py-2 font-mono text-gray-900 font-bold">{{ row['Jump Height (in)'] ? Number(row['Jump Height (in)']).toFixed(2) + '"' : '--' }}</td>
                    <td class="px-4 py-2 font-mono text-gray-900">{{ row['mRSI'] ? Number(row['mRSI']).toFixed(2) : '--' }}</td>
                    <td class="px-4 py-2 font-mono text-gray-900">{{ row['Peak Rel Prop Power (W/kg)'] ? Number(row['Peak Rel Prop Power (W/kg)']).toFixed(2) + ' W/kg' : '--' }}</td>
                    <td class="px-4 py-2 font-mono text-gray-900">
                      {{ row['Braking Asymmetry'] !== null ? Math.abs(row['Braking Asymmetry']) + '% ' + (row['Braking Asymmetry'] < 0 ? 'Left' : 'Right') : '--' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Force Plate MR Table -->
            <div class="border border-gray-200 rounded-lg overflow-hidden md:col-span-2">
              <div class="bg-gray-50 px-4 py-2 border-b border-gray-200 font-semibold text-sm text-gray-700">Force Plate: Multi-Rebound (MR)</div>
              <div class="p-4" v-if="fpMrData.length === 0"><p class="text-sm text-gray-500 italic">No MR data available.</p></div>
              <table class="w-full text-sm text-left text-gray-600" v-else>
                <thead class="text-xs text-gray-400 uppercase bg-white border-b border-gray-100">
                  <tr>
                    <th class="px-4 py-2 font-medium">Jumps</th>
                    <th class="px-4 py-2 font-medium">Avg Jump Height</th>
                    <th class="px-4 py-2 font-medium">Peak Jump Height</th>
                    <th class="px-4 py-2 font-medium">Avg RSI</th>
                    <th class="px-4 py-2 font-medium">Peak RSI</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in fpMrData" :key="'mr-'+idx" class="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors">
                    <td class="px-4 py-2 font-mono text-gray-900">{{ row['Number of Jumps'] || '--' }}</td>
                    <td class="px-4 py-2 font-mono text-gray-900">{{ row['Avg Jump Height (in)'] ? Number(row['Avg Jump Height (in)']).toFixed(2) + '"' : '--' }}</td>
                    <td class="px-4 py-2 font-mono text-gray-900 font-bold">{{ row['Peak Jump Height (in)'] ? Number(row['Peak Jump Height (in)']).toFixed(2) + '"' : '--' }}</td>
                    <td class="px-4 py-2 font-mono text-gray-900">{{ row['Avg RSI'] ? Number(row['Avg RSI']).toFixed(2) : '--' }}</td>
                    <td class="px-4 py-2 font-mono text-gray-900 font-bold">{{ row['Peak RSI'] ? Number(row['Peak RSI']).toFixed(2) : '--' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Bottom Section: Commentary Area (Full Width) -->
      <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col w-full">
        <h2 class="text-xl font-bold text-gray-900 mb-2">Evaluation History</h2>
        <p class="text-xs text-gray-500 mb-4 pb-4 border-b border-gray-100">Add new diary entries and review past notes below.</p>
        
        <!-- New Entry Editor -->
        <div class="flex flex-col mb-6">
          <div class="mb-3 border border-gray-300 rounded-lg overflow-hidden">
            <QuillEditor theme="snow" v-model:content="newComment" contentType="html" :placeholder="editingEntryId ? 'Edit evaluation entry...' : 'Write a new evaluation entry...'" />
          </div>
          <div class="flex justify-end gap-3">
            <button v-if="editingEntryId" @click="cancelEdit" :disabled="isSaving" 
                    class="px-5 py-2 rounded-md font-medium text-gray-600 hover:bg-gray-100 border border-gray-200 disabled:opacity-50 transition-colors text-sm shadow-sm">
              Cancel
            </button>
            <button @click="saveComment" :disabled="isSaving || !newComment || newComment === '<p><br></p>'" 
                    class="bg-code8-dark text-white px-5 py-2 rounded-md font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm shadow-sm">
              {{ isSaving ? 'Saving...' : (editingEntryId ? 'Update Entry' : 'Save Entry') }}
            </button>
          </div>
        </div>

        <!-- Previous Comments List -->
        <div class="flex-1 overflow-y-auto space-y-4 pr-2 border-t border-gray-200 pt-4">
          <div v-for="entry in previousComments" :key="entry.id" class="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <div class="flex justify-between items-center mb-2 pb-2 border-b border-gray-200/60">
              <div class="flex items-center gap-3">
                <span class="font-bold text-sm text-gray-900">{{ entry.author || 'Coach' }}</span>
                <span class="text-xs text-gray-500">
                  {{ formatDate(entry.created_at) }}
                  <span v-if="entry.updated_at" class="italic ml-1">(edited)</span>
                </span>
              </div>
              <div class="flex items-center gap-1">
                <button @click="editEntry(entry)" class="text-gray-400 hover:text-code8-gold transition-colors p-1" title="Edit Entry">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
                </button>
                <button @click="deleteEntry(entry.id)" class="text-gray-400 hover:text-red-500 transition-colors p-1" title="Delete Entry">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
              </div>
            </div>
            <div class="text-sm text-gray-700 prose prose-sm max-w-none leading-relaxed" v-html="entry.summary_html"></div>
          </div>
          <div v-if="previousComments.length === 0" class="text-sm text-gray-500 italic text-center py-8">
            No previous entries found for this athlete.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* Force Quill editor to fill remaining vertical space cleanly */
.ql-toolbar {
  background-color: #f9fafb;
  border-bottom: 1px solid #e5e7eb !important;
  border-top: none !important;
  border-left: none !important;
  border-right: none !important;
}
.ql-container {
  border: none !important;
}
.ql-editor {
  min-height: 120px;
  max-height: 200px;
  font-size: 0.875rem;
  color: #374151;
}
</style>