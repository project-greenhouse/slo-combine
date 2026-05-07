<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAthleteStore, type RosterItem } from '../../stores/athleteStore';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../../firebase/config';

const router = useRouter();
const athleteStore = useAthleteStore();
const search = ref('');
const dropdownOpen = ref(false);
const selected = ref<RosterItem | null>(null);
const attempt1 = ref<number | null>(null);
const attempt2 = ref<number | null>(null);
const saving = ref(false);
const toast = ref<{ message: string; type: 'success' | 'error' } | null>(null);
const savedAthletes = ref<Set<string>>(new Set());

onMounted(() => { athleteStore.fetchRoster(); });

const filtered = computed(() => {
  const q = search.value.toLowerCase();
  if (!q) return athleteStore.roster;
  return athleteStore.roster.filter(a => a.Name.toLowerCase().includes(q));
});

const openDropdown = () => { dropdownOpen.value = true; };
const closeDropdown = () => { setTimeout(() => { dropdownOpen.value = false; }, 200); };

const best = computed(() => {
  const a = attempt1.value;
  const b = attempt2.value;
  if (a != null && b != null) return Math.max(a, b);
  return a ?? b ?? null;
});

const pick = (athlete: RosterItem) => {
  selected.value = athlete;
  search.value = '';
  dropdownOpen.value = false;
  attempt1.value = null;
  attempt2.value = null;
};

const save = async () => {
  if (!selected.value?.athlete_uid || (attempt1.value == null && attempt2.value == null)) return;
  saving.value = true;
  try {
    const fn = httpsCallable(functions, 'submit_broad_jump');
    const res = await fn({
      athlete_uid: selected.value.athlete_uid,
      attempt1: attempt1.value,
      attempt2: attempt2.value,
    });
    const data = res.data as any;
    if (data.status === 'success') {
      toast.value = { message: `Saved ${selected.value.Name}: Best ${data.best_inches}"`, type: 'success' };
      savedAthletes.value.add(selected.value.athlete_uid);
      advanceToNext();
    } else {
      toast.value = { message: data.message || 'Save failed', type: 'error' };
    }
  } catch (e: any) {
    toast.value = { message: e.message || 'Save failed', type: 'error' };
  } finally {
    saving.value = false;
    setTimeout(() => { toast.value = null; }, 3000);
  }
};

const advanceToNext = () => {
  const unsaved = athleteStore.roster.filter(a => a.athlete_uid && !savedAthletes.value.has(a.athlete_uid));
  if (unsaved.length > 0) {
    pick(unsaved[0]);
  } else {
    selected.value = null;
    attempt1.value = null;
    attempt2.value = null;
  }
};
</script>

<template>
  <div class="max-w-lg mx-auto">
    <button @click="router.push('/testing')" class="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
      Back to Testing
    </button>
    <div class="bg-purple-50 border border-purple-200 rounded-xl p-4 mb-6">
      <h1 class="text-2xl font-bold text-purple-900">Broad Jump</h1>
      <p class="text-sm text-purple-700">Record 2 attempts. Best distance is highlighted automatically.</p>
    </div>

    <div v-if="toast" :class="['mb-4 p-3 rounded-lg text-sm font-medium', toast.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800']">
      {{ toast.message }}
    </div>

    <!-- Athlete picker -->
    <label class="block text-sm font-medium text-gray-700 mb-1">Athlete</label>
    <div class="relative mb-4">
      <input
        v-model="search"
        type="text"
        :placeholder="selected ? selected.Name : 'Search or scroll to select...'"
        class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none"
        @focus="openDropdown"
        @blur="closeDropdown"
      />
      <div v-if="dropdownOpen && filtered.length" class="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-72 overflow-y-auto overscroll-contain">
        <button
          v-for="a in filtered" :key="a.Name"
          @mousedown.prevent="pick(a)"
          class="w-full text-left px-4 py-3 text-base hover:bg-gray-100 active:bg-gray-200 flex justify-between items-center border-b border-gray-50 last:border-0"
        >
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

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Attempt 1 (in)</label>
          <input
            v-model.number="attempt1"
            type="number"
            inputmode="decimal"
            step="0.5"
            min="0"
            max="200"
            placeholder="e.g. 96"
            :class="[
              'w-full bg-gray-50 border rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none',
              best != null && attempt1 === best ? 'border-code8-gold bg-yellow-50' : 'border-gray-300'
            ]"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Attempt 2 (in)</label>
          <input
            v-model.number="attempt2"
            type="number"
            inputmode="decimal"
            step="0.5"
            min="0"
            max="200"
            placeholder="e.g. 102"
            :class="[
              'w-full bg-gray-50 border rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none',
              best != null && attempt2 === best ? 'border-code8-gold bg-yellow-50' : 'border-gray-300'
            ]"
            @keyup.enter="save"
          />
        </div>
      </div>

      <!-- Best highlight -->
      <div v-if="best != null" class="p-4 bg-code8-dark rounded-lg text-center">
        <p class="text-sm text-gray-400 uppercase tracking-wider">Best</p>
        <p class="text-4xl font-bold text-code8-gold">{{ best }}"</p>
      </div>

      <button
        @click="save"
        :disabled="saving || (attempt1 == null && attempt2 == null)"
        class="w-full py-4 rounded-lg text-lg font-bold text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        :class="saving ? 'bg-gray-400' : 'bg-code8-gold hover:bg-yellow-600 active:bg-yellow-700'"
      >
        {{ saving ? 'Saving...' : 'Save' }}
      </button>
    </div>
  </div>
</template>
