<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useAthleteStore, type RosterItem } from '../../stores/athleteStore';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../../firebase/config';

const athleteStore = useAthleteStore();
const search = ref('');
const selected = ref<RosterItem | null>(null);
const inches = ref<number | null>(null);
const saving = ref(false);
const toast = ref<{ message: string; type: 'success' | 'error' } | null>(null);
const savedAthletes = ref<Set<string>>(new Set());

onMounted(() => { athleteStore.fetchRoster(); });

const filtered = computed(() => {
  const q = search.value.toLowerCase();
  return athleteStore.roster.filter(a => a.Name.toLowerCase().includes(q));
});

const pick = (athlete: RosterItem) => {
  selected.value = athlete;
  search.value = '';
  inches.value = null;
};

const save = async () => {
  if (!selected.value?.athlete_uid || inches.value == null) return;
  saving.value = true;
  try {
    const fn = httpsCallable(functions, 'submit_standing_reach');
    const res = await fn({ athlete_uid: selected.value.athlete_uid, inches: inches.value });
    const data = res.data as any;
    if (data.status === 'success') {
      toast.value = { message: `Saved ${selected.value.Name}: ${inches.value}"`, type: 'success' };
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
    inches.value = null;
  }
};
</script>

<template>
  <div class="max-w-lg mx-auto">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">Standing Reach</h1>

    <!-- Toast -->
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

    <!-- Input -->
    <div v-if="selected" class="space-y-4">
      <div class="p-4 bg-code8-dark/5 rounded-lg">
        <p class="text-lg font-semibold text-gray-800">{{ selected.Name }}</p>
        <p v-if="selected.CurrentSchool" class="text-sm text-gray-500">{{ selected.CurrentSchool }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Standing Reach (inches)</label>
        <input
          v-model.number="inches"
          type="number"
          inputmode="decimal"
          step="0.5"
          min="0"
          max="150"
          placeholder="e.g. 85.5"
          class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none"
          @keyup.enter="save"
        />
      </div>

      <button
        @click="save"
        :disabled="saving || inches == null"
        class="w-full py-4 rounded-lg text-lg font-bold text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        :class="saving ? 'bg-gray-400' : 'bg-code8-gold hover:bg-yellow-600 active:bg-yellow-700'"
      >
        {{ saving ? 'Saving...' : 'Save' }}
      </button>
    </div>
  </div>
</template>
