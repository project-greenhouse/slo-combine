<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { useAthleteStore, type RosterItem } from '../../stores/athleteStore';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../../firebase/config';

const athleteStore = useAthleteStore();
const search = ref('');
const selected = ref<RosterItem | null>(null);
const maxTouch = ref<number | null>(null);
const standingReach = ref<number | null>(null);
const reachLoading = ref(false);
const saving = ref(false);
const toast = ref<{ message: string; type: 'success' | 'error' } | null>(null);
const savedAthletes = ref<Set<string>>(new Set());

onMounted(() => { athleteStore.fetchRoster(); });

const filtered = computed(() => {
  const q = search.value.toLowerCase();
  return athleteStore.roster.filter(a => a.Name.toLowerCase().includes(q));
});

const vertical = computed(() => {
  if (maxTouch.value != null && standingReach.value != null) {
    return Math.round((maxTouch.value - standingReach.value) * 10) / 10;
  }
  return null;
});

const pick = async (athlete: RosterItem) => {
  selected.value = athlete;
  search.value = '';
  maxTouch.value = null;
  standingReach.value = null;

  if (!athlete.athlete_uid) return;
  reachLoading.value = true;
  try {
    const fn = httpsCallable(functions, 'get_standing_reach');
    const res = await fn({ athlete_uid: athlete.athlete_uid });
    const data = res.data as any;
    if (data.status === 'success' && data.inches != null) {
      standingReach.value = data.inches;
    }
  } catch { /* athlete may not have a standing reach yet */ }
  finally { reachLoading.value = false; }
};

const save = async () => {
  if (!selected.value?.athlete_uid || maxTouch.value == null) return;
  saving.value = true;
  try {
    const fn = httpsCallable(functions, 'submit_vertical_jump');
    const res = await fn({ athlete_uid: selected.value.athlete_uid, max_touch_inches: maxTouch.value });
    const data = res.data as any;
    if (data.status === 'success') {
      toast.value = { message: `Saved ${selected.value.Name}: ${data.vert_inches}" vertical`, type: 'success' };
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
    maxTouch.value = null;
  }
};
</script>

<template>
  <div class="max-w-lg mx-auto">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">Vertical Jump</h1>

    <div v-if="toast" :class="['mb-4 p-3 rounded-lg text-sm font-medium', toast.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800']">
      {{ toast.message }}
    </div>

    <!-- Athlete picker -->
    <label class="block text-sm font-medium text-gray-700 mb-1">Athlete</label>
    <div class="relative mb-4">
      <input
        v-model="search"
        type="text"
        :placeholder="selected ? selected.Name : 'Search athlete...'"
        class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none"
        @focus="search = ''"
      />
      <div v-if="search && filtered.length" class="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
        <button
          v-for="a in filtered" :key="a.Name"
          @click="pick(a)"
          class="w-full text-left px-4 py-3 text-base hover:bg-gray-100 flex justify-between items-center"
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

      <!-- Standing reach display -->
      <div class="p-3 rounded-lg" :class="standingReach != null ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'">
        <p v-if="reachLoading" class="text-sm text-gray-500">Loading standing reach...</p>
        <p v-else-if="standingReach != null" class="text-sm text-green-800">Standing Reach: <strong>{{ standingReach }}"</strong></p>
        <p v-else class="text-sm text-yellow-800">No standing reach recorded. Vertical cannot be computed until standing reach is entered.</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Max Touch Height (inches)</label>
        <input
          v-model.number="maxTouch"
          type="number"
          inputmode="decimal"
          step="0.5"
          min="0"
          max="200"
          placeholder="e.g. 110"
          class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none"
          @keyup.enter="save"
        />
      </div>

      <!-- Live vertical calc -->
      <div v-if="vertical != null" class="p-4 bg-code8-dark rounded-lg text-center">
        <p class="text-sm text-gray-400 uppercase tracking-wider">Vertical</p>
        <p class="text-4xl font-bold text-code8-gold">{{ vertical }}"</p>
      </div>

      <button
        @click="save"
        :disabled="saving || maxTouch == null || standingReach == null"
        class="w-full py-4 rounded-lg text-lg font-bold text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        :class="saving ? 'bg-gray-400' : 'bg-code8-gold hover:bg-yellow-600 active:bg-yellow-700'"
      >
        {{ saving ? 'Saving...' : 'Save' }}
      </button>
    </div>
  </div>
</template>
