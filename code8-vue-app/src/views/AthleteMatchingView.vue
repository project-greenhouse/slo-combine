<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useAthleteStore, type RosterItem } from '../stores/athleteStore';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../firebase/config';

const athleteStore = useAthleteStore();
const valorAthletes = ref<{ ValorID: string; Name: string; assigned: boolean }[]>([]);
const valorLoading = ref(false);
const saving = ref<Record<string, boolean>>({});
const toast = ref('');

onMounted(async () => {
  athleteStore.fetchRoster();
  await fetchValor();
});

const fetchValor = async () => {
  valorLoading.value = true;
  try {
    const fn = httpsCallable(functions, 'get_valor_athletes');
    const res = await fn({});
    const data = res.data as any;
    if (data.status === 'success') valorAthletes.value = data.data;
  } catch { /* ignore */ }
  finally { valorLoading.value = false; }
};

const unmatchedRoster = computed(() =>
  athleteStore.roster.filter(a => a.athlete_uid && !a.ValorID)
);

const matchedRoster = computed(() =>
  athleteStore.roster.filter(a => a.athlete_uid && a.ValorID)
);

const availableValor = computed(() =>
  valorAthletes.value.filter(v => !v.assigned)
);

function normalize(name: string): string {
  return name.toLowerCase().replace(/[.\-']/g, '').replace(/\s+/g, ' ').trim();
}

function suggestedMatch(athlete: RosterItem) {
  const norm = normalize(athlete.Name);
  return availableValor.value.find(v => normalize(v.Name) === norm) || null;
}

// Per-athlete dropdown state
const openDropdown = ref<string | null>(null);
const searchTerms = ref<Record<string, string>>({});

const filteredValorFor = (uid: string) => {
  const q = (searchTerms.value[uid] || '').toLowerCase();
  if (!q) return availableValor.value;
  return availableValor.value.filter(v => v.Name.toLowerCase().includes(q));
};

const assign = async (athlete: RosterItem, valorId: string, valorName: string) => {
  if (!athlete.athlete_uid) return;
  saving.value[athlete.athlete_uid] = true;
  openDropdown.value = null;
  searchTerms.value[athlete.athlete_uid] = '';
  try {
    const fn = httpsCallable(functions, 'update_athlete_info');
    const res = await fn({ athlete_uid: athlete.athlete_uid, ValorID: valorId });
    const data = res.data as any;
    if (data.status === 'success') {
      const idx = athleteStore.roster.findIndex(a => a.athlete_uid === athlete.athlete_uid);
      if (idx !== -1) athleteStore.roster[idx] = { ...athleteStore.roster[idx], ValorID: valorId };
      const va = valorAthletes.value.find(a => a.ValorID === valorId);
      if (va) va.assigned = true;
      toast.value = `Linked ${athlete.Name} → ${valorName}`;
      setTimeout(() => { toast.value = ''; }, 3000);
    }
  } catch { /* ignore */ }
  finally { delete saving.value[athlete.athlete_uid!]; }
};

const unlink = async (athlete: RosterItem) => {
  if (!athlete.athlete_uid) return;
  saving.value[athlete.athlete_uid] = true;
  try {
    const fn = httpsCallable(functions, 'update_athlete_info');
    const res = await fn({ athlete_uid: athlete.athlete_uid, ValorID: '' });
    const data = res.data as any;
    if (data.status === 'success') {
      const oldId = athlete.ValorID;
      const idx = athleteStore.roster.findIndex(a => a.athlete_uid === athlete.athlete_uid);
      if (idx !== -1) athleteStore.roster[idx] = { ...athleteStore.roster[idx], ValorID: null };
      if (oldId) {
        const va = valorAthletes.value.find(a => a.ValorID === String(oldId));
        if (va) va.assigned = false;
      }
      toast.value = `Unlinked ${athlete.Name}`;
      setTimeout(() => { toast.value = ''; }, 3000);
    }
  } catch { /* ignore */ }
  finally { delete saving.value[athlete.athlete_uid!]; }
};

const valorNameById = (id: string | null | undefined) => {
  if (!id) return '';
  const match = valorAthletes.value.find(v => v.ValorID === String(id));
  return match?.Name || id;
};
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Athlete Matching</h1>
    <p class="text-sm text-gray-500 mb-6">Link roster athletes to their Valor profiles. Suggested matches (by name) are shown first.</p>

    <div v-if="toast" class="mb-4 p-3 rounded-lg bg-green-100 text-green-800 text-sm font-medium">{{ toast }}</div>

    <div v-if="valorLoading || athleteStore.loading" class="text-center py-12 text-gray-400 animate-pulse">
      Loading athletes...
    </div>

    <template v-else>
      <!-- Stats bar -->
      <div class="grid grid-cols-3 gap-3 mb-6">
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-center">
          <p class="text-2xl font-bold text-yellow-700">{{ unmatchedRoster.length }}</p>
          <p class="text-xs text-yellow-600">Unmatched</p>
        </div>
        <div class="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
          <p class="text-2xl font-bold text-green-700">{{ matchedRoster.length }}</p>
          <p class="text-xs text-green-600">Matched</p>
        </div>
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
          <p class="text-2xl font-bold text-blue-700">{{ availableValor.length }}</p>
          <p class="text-xs text-blue-600">Valor Unassigned</p>
        </div>
      </div>

      <!-- Unmatched athletes -->
      <div v-if="unmatchedRoster.length" class="mb-8">
        <h2 class="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Unmatched Athletes</h2>
        <div class="space-y-2">
          <div v-for="athlete in unmatchedRoster" :key="athlete.athlete_uid!"
            class="bg-white border border-gray-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center gap-3"
          >
            <!-- Athlete info -->
            <div class="flex-1 min-w-0">
              <p class="font-bold text-gray-900 truncate">{{ athlete.Name }}</p>
              <p class="text-xs text-gray-500">{{ athlete.CurrentSchool || 'No school' }}</p>
            </div>

            <!-- Suggested match or dropdown -->
            <div class="w-full sm:w-64 flex-shrink-0">
              <!-- Auto-suggestion -->
              <div v-if="suggestedMatch(athlete) && !saving[athlete.athlete_uid!]" class="flex items-center gap-2">
                <button
                  @click="assign(athlete, suggestedMatch(athlete)!.ValorID, suggestedMatch(athlete)!.Name)"
                  class="flex-1 bg-code8-gold/10 border border-code8-gold/30 text-code8-dark rounded-lg px-3 py-2 text-sm font-medium hover:bg-code8-gold/20 active:bg-code8-gold/30 transition-colors text-left truncate"
                >
                  Link: {{ suggestedMatch(athlete)!.Name }}
                </button>
                <button
                  @click="openDropdown = athlete.athlete_uid!"
                  class="p-2 text-gray-400 hover:text-gray-600"
                  title="Pick a different match"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                </button>
              </div>

              <!-- Manual dropdown -->
              <div v-else-if="!saving[athlete.athlete_uid!]" class="relative">
                <input
                  v-model="searchTerms[athlete.athlete_uid!]"
                  type="text"
                  placeholder="Search Valor..."
                  class="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none"
                  @focus="openDropdown = athlete.athlete_uid!"
                  @blur="setTimeout(() => { if (openDropdown === athlete.athlete_uid) openDropdown = null; }, 200)"
                />
                <div v-if="openDropdown === athlete.athlete_uid" class="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto overscroll-contain">
                  <button
                    v-for="va in filteredValorFor(athlete.athlete_uid!)" :key="va.ValorID"
                    @mousedown.prevent="assign(athlete, va.ValorID, va.Name)"
                    class="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 active:bg-gray-200 border-b border-gray-50 last:border-0"
                  >
                    {{ va.Name }}
                  </button>
                  <div v-if="filteredValorFor(athlete.athlete_uid!).length === 0" class="px-3 py-2 text-sm text-gray-400">No matches</div>
                </div>
              </div>

              <!-- Saving spinner -->
              <div v-else class="text-sm text-gray-400 animate-pulse">Saving...</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Matched athletes -->
      <div v-if="matchedRoster.length">
        <h2 class="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Matched Athletes</h2>
        <div class="space-y-2">
          <div v-for="athlete in matchedRoster" :key="athlete.athlete_uid!"
            class="bg-white border border-green-100 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center gap-3"
          >
            <div class="flex-1 min-w-0">
              <p class="font-bold text-gray-900 truncate">{{ athlete.Name }}</p>
              <p class="text-xs text-gray-500">{{ athlete.CurrentSchool || 'No school' }}</p>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <span class="inline-block w-2 h-2 rounded-full bg-green-500"></span>
              <span class="text-sm text-gray-700 truncate max-w-[180px]">{{ valorNameById(athlete.ValorID) }}</span>
              <button
                @click="unlink(athlete)"
                :disabled="!!saving[athlete.athlete_uid!]"
                class="text-xs text-red-500 hover:text-red-700 font-medium ml-2"
              >
                {{ saving[athlete.athlete_uid!] ? '...' : 'Unlink' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="unmatchedRoster.length === 0 && matchedRoster.length === 0" class="text-center py-12 text-gray-400">
        No athletes in roster yet.
      </div>
    </template>
  </div>
</template>
