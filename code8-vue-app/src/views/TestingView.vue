<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useAthleteStore, type RosterItem } from '../stores/athleteStore';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../firebase/config';

const athleteStore = useAthleteStore();
onMounted(() => { athleteStore.fetchRoster(); });

const activeTab = ref<'standing-reach' | 'vertical' | 'broad-jump' | 'sprint-upload'>('standing-reach');

const tabs = [
  { key: 'standing-reach' as const, label: 'Standing Reach' },
  { key: 'vertical' as const, label: 'Vertical Jump' },
  { key: 'broad-jump' as const, label: 'Broad Jump' },
  { key: 'sprint-upload' as const, label: 'Sprint Upload' },
];

// --- Shared athlete picker state ---
const search = ref('');
const dropdownOpen = ref(false);
const selected = ref<RosterItem | null>(null);
const toast = ref<{ message: string; type: 'success' | 'error' } | null>(null);
const savedAthletes = ref<Set<string>>(new Set());
const saving = ref(false);

const filtered = computed(() => {
  const q = search.value.toLowerCase();
  if (!q) return athleteStore.roster;
  return athleteStore.roster.filter(a => a.Name.toLowerCase().includes(q));
});

const openDrop = () => { dropdownOpen.value = true; };
const closeDrop = () => { setTimeout(() => { dropdownOpen.value = false; }, 200); };

const pick = (athlete: RosterItem) => {
  selected.value = athlete;
  search.value = '';
  dropdownOpen.value = false;
  // Reset station-specific inputs
  reachInches.value = null;
  maxTouch.value = null;
  standingReach.value = null;
  attempt1.value = null;
  attempt2.value = null;
  // Fetch standing reach for vertical tab
  if (activeTab.value === 'vertical' && athlete.athlete_uid) fetchReach(athlete.athlete_uid);
};

const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
  toast.value = { message: msg, type };
  setTimeout(() => { toast.value = null; }, 3000);
};

const advanceToNext = () => {
  const unsaved = athleteStore.roster.filter(a => a.athlete_uid && !savedAthletes.value.has(a.athlete_uid));
  if (unsaved.length > 0) pick(unsaved[0]);
  else { selected.value = null; }
};

// --- Standing Reach ---
const reachInches = ref<number | null>(null);

const saveReach = async () => {
  if (!selected.value?.athlete_uid || reachInches.value == null) return;
  saving.value = true;
  try {
    const fn = httpsCallable(functions, 'submit_standing_reach');
    const res = await fn({ athlete_uid: selected.value.athlete_uid, inches: reachInches.value });
    const data = res.data as any;
    if (data.status === 'success') {
      showToast(`Saved ${selected.value.Name}: ${reachInches.value}"`);
      savedAthletes.value.add(selected.value.athlete_uid);
      advanceToNext();
    } else showToast(data.message || 'Failed', 'error');
  } catch (e: any) { showToast(e.message || 'Failed', 'error'); }
  finally { saving.value = false; }
};

// --- Vertical Jump ---
const maxTouch = ref<number | null>(null);
const standingReach = ref<number | null>(null);
const reachLoading = ref(false);

const vertical = computed(() => {
  if (maxTouch.value != null && standingReach.value != null)
    return Math.round((maxTouch.value - standingReach.value) * 10) / 10;
  return null;
});

const fetchReach = async (uid: string) => {
  reachLoading.value = true;
  try {
    const fn = httpsCallable(functions, 'get_standing_reach');
    const res = await fn({ athlete_uid: uid });
    const data = res.data as any;
    if (data.status === 'success' && data.inches != null) standingReach.value = data.inches;
  } catch { /* */ }
  finally { reachLoading.value = false; }
};

const saveVertical = async () => {
  if (!selected.value?.athlete_uid || maxTouch.value == null) return;
  saving.value = true;
  try {
    const fn = httpsCallable(functions, 'submit_vertical_jump');
    const res = await fn({ athlete_uid: selected.value.athlete_uid, max_touch_inches: maxTouch.value });
    const data = res.data as any;
    if (data.status === 'success') {
      showToast(`Saved ${selected.value.Name}: ${data.vert_inches}" vertical`);
      savedAthletes.value.add(selected.value.athlete_uid);
      advanceToNext();
    } else showToast(data.message || 'Failed', 'error');
  } catch (e: any) { showToast(e.message || 'Failed', 'error'); }
  finally { saving.value = false; }
};

// --- Broad Jump ---
const attempt1 = ref<number | null>(null);
const attempt2 = ref<number | null>(null);

const best = computed(() => {
  const a = attempt1.value, b = attempt2.value;
  if (a != null && b != null) return Math.max(a, b);
  return a ?? b ?? null;
});

const saveBroad = async () => {
  if (!selected.value?.athlete_uid || (attempt1.value == null && attempt2.value == null)) return;
  saving.value = true;
  try {
    const fn = httpsCallable(functions, 'submit_broad_jump');
    const res = await fn({ athlete_uid: selected.value.athlete_uid, attempt1: attempt1.value, attempt2: attempt2.value });
    const data = res.data as any;
    if (data.status === 'success') {
      showToast(`Saved ${selected.value.Name}: Best ${data.best_inches}"`);
      savedAthletes.value.add(selected.value.athlete_uid);
      advanceToNext();
    } else showToast(data.message || 'Failed', 'error');
  } catch (e: any) { showToast(e.message || 'Failed', 'error'); }
  finally { saving.value = false; }
};

// --- Sprint CSV Upload ---
const sprintFile = ref<File | null>(null);
const sprintMsg = ref('');
const sprintIsError = ref(false);
const sprintLoading = ref(false);

const handleSprintFileChange = (e: Event) => {
  const t = e.target as HTMLInputElement;
  if (t.files?.length) sprintFile.value = t.files[0];
};

const handleSprintUpload = async () => {
  if (!sprintFile.value) return;
  sprintLoading.value = true; sprintMsg.value = ''; sprintIsError.value = false;
  const reader = new FileReader();
  reader.onload = async (e) => {
    const text = e.target?.result as string;
    try {
      const fn = httpsCallable(functions, 'upload_roster_csv');
      const result = await fn({ csv_data: text });
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
  <div class="max-w-lg mx-auto">
    <h1 class="text-2xl font-bold text-gray-800 mb-4">Testing Stations</h1>

    <!-- Tab bar -->
    <div class="flex overflow-x-auto gap-1 bg-gray-100 rounded-lg p-1 mb-6">
      <button v-for="tab in tabs" :key="tab.key"
        @click="activeTab = tab.key; selected = null; savedAthletes.clear();"
        :class="['flex-1 min-w-0 px-3 py-2 text-sm font-semibold rounded-md transition-colors whitespace-nowrap',
          activeTab === tab.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700']"
      >{{ tab.label }}</button>
    </div>

    <!-- Toast -->
    <div v-if="toast" :class="['mb-4 p-3 rounded-lg text-sm font-medium', toast.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800']">
      {{ toast.message }}
    </div>

    <!-- Sprint Upload tab -->
    <div v-if="activeTab === 'sprint-upload'" class="space-y-4">
      <p class="text-sm text-gray-500">Upload a CSV file with sprint timing data (Swift export).</p>
      <form @submit.prevent="handleSprintUpload" class="space-y-4">
        <input id="sprintFileInput" type="file" accept=".csv" @change="handleSprintFileChange"
          class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base" />
        <div v-if="sprintMsg" :class="['text-sm font-medium p-3 rounded-lg', sprintIsError ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800']">{{ sprintMsg }}</div>
        <button type="submit" :disabled="sprintLoading || !sprintFile"
          class="w-full py-4 rounded-lg text-lg font-bold text-white bg-code8-gold hover:bg-yellow-600 active:bg-yellow-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
          {{ sprintLoading ? 'Uploading...' : 'Upload Sprint Data' }}
        </button>
      </form>
    </div>

    <!-- Measurement tabs (standing reach, vertical, broad) share the athlete picker -->
    <template v-if="activeTab !== 'sprint-upload'">
      <!-- Athlete picker -->
      <label class="block text-sm font-medium text-gray-700 mb-1">Athlete</label>
      <div class="relative mb-4">
        <input v-model="search" type="text"
          :placeholder="selected ? selected.Name : 'Search or scroll to select...'"
          class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none"
          @focus="openDrop" @blur="closeDrop" />
        <div v-if="dropdownOpen && filtered.length" class="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-72 overflow-y-auto overscroll-contain">
          <button v-for="a in filtered" :key="a.Name" @mousedown.prevent="pick(a)"
            class="w-full text-left px-4 py-3 text-base hover:bg-gray-100 active:bg-gray-200 flex justify-between items-center border-b border-gray-50 last:border-0">
            <span>{{ a.Name }}</span>
            <span v-if="a.athlete_uid && savedAthletes.has(a.athlete_uid)" class="text-xs text-green-600 font-medium">Done</span>
          </button>
        </div>
      </div>

      <div v-if="selected" class="space-y-4">
        <div class="p-4 bg-code8-dark/5 rounded-lg">
          <p class="text-lg font-semibold text-gray-800">{{ selected.Name }}</p>
          <p v-if="selected.CurrentSchool" class="text-sm text-gray-500">{{ selected.CurrentSchool }}</p>
        </div>

        <!-- Standing Reach -->
        <template v-if="activeTab === 'standing-reach'">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Standing Reach (inches)</label>
            <input v-model.number="reachInches" type="number" inputmode="decimal" step="0.5" min="0" max="150" placeholder="e.g. 85.5"
              class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" @keyup.enter="saveReach" />
          </div>
          <button @click="saveReach" :disabled="saving || reachInches == null"
            class="w-full py-4 rounded-lg text-lg font-bold text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :class="saving ? 'bg-gray-400' : 'bg-code8-gold hover:bg-yellow-600 active:bg-yellow-700'">
            {{ saving ? 'Saving...' : 'Save' }}
          </button>
        </template>

        <!-- Vertical Jump -->
        <template v-if="activeTab === 'vertical'">
          <div class="p-3 rounded-lg" :class="standingReach != null ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'">
            <p v-if="reachLoading" class="text-sm text-gray-500">Loading standing reach...</p>
            <p v-else-if="standingReach != null" class="text-sm text-green-800">Standing Reach: <strong>{{ standingReach }}"</strong></p>
            <p v-else class="text-sm text-yellow-800">No standing reach recorded. Enter standing reach first.</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Max Touch Height (inches)</label>
            <input v-model.number="maxTouch" type="number" inputmode="decimal" step="0.5" min="0" max="200" placeholder="e.g. 110"
              class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" @keyup.enter="saveVertical" />
          </div>
          <div v-if="vertical != null" class="p-4 bg-code8-dark rounded-lg text-center">
            <p class="text-sm text-gray-400 uppercase tracking-wider">Vertical</p>
            <p class="text-4xl font-bold text-code8-gold">{{ vertical }}"</p>
          </div>
          <button @click="saveVertical" :disabled="saving || maxTouch == null || standingReach == null"
            class="w-full py-4 rounded-lg text-lg font-bold text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :class="saving ? 'bg-gray-400' : 'bg-code8-gold hover:bg-yellow-600 active:bg-yellow-700'">
            {{ saving ? 'Saving...' : 'Save' }}
          </button>
        </template>

        <!-- Broad Jump -->
        <template v-if="activeTab === 'broad-jump'">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Attempt 1 (in)</label>
              <input v-model.number="attempt1" type="number" inputmode="decimal" step="0.5" min="0" max="200" placeholder="e.g. 96"
                :class="['w-full bg-gray-50 border rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none', best != null && attempt1 === best ? 'border-code8-gold bg-yellow-50' : 'border-gray-300']" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Attempt 2 (in)</label>
              <input v-model.number="attempt2" type="number" inputmode="decimal" step="0.5" min="0" max="200" placeholder="e.g. 102"
                :class="['w-full bg-gray-50 border rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none', best != null && attempt2 === best ? 'border-code8-gold bg-yellow-50' : 'border-gray-300']"
                @keyup.enter="saveBroad" />
            </div>
          </div>
          <div v-if="best != null" class="p-4 bg-code8-dark rounded-lg text-center">
            <p class="text-sm text-gray-400 uppercase tracking-wider">Best</p>
            <p class="text-4xl font-bold text-code8-gold">{{ best }}"</p>
          </div>
          <button @click="saveBroad" :disabled="saving || (attempt1 == null && attempt2 == null)"
            class="w-full py-4 rounded-lg text-lg font-bold text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :class="saving ? 'bg-gray-400' : 'bg-code8-gold hover:bg-yellow-600 active:bg-yellow-700'">
            {{ saving ? 'Saving...' : 'Save' }}
          </button>
        </template>
      </div>
    </template>
  </div>
</template>
