<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useAthleteStore, type RosterItem } from '../stores/athleteStore';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../firebase/config';

const athleteStore = useAthleteStore();

const showAddMenu = ref(false);
const showCsvModal = ref(false);

// --- Bookeo Sync ---
const bookeoSyncing = ref(false);
const bookeoResult = ref<any>(null);
const bookeoError = ref('');

const handleBookeoSync = async () => {
  bookeoSyncing.value = true;
  bookeoResult.value = null;
  bookeoError.value = '';
  try {
    const syncFn = httpsCallable(functions, 'sync_bookeo_roster');
    const result = await syncFn({});
    const data = result.data as any;
    if (data.status === 'success') {
      bookeoResult.value = data;
      await athleteStore.forceRefreshRoster();
      await fetchValor();
    } else {
      bookeoError.value = data.message || 'Sync failed';
    }
  } catch (err: any) {
    bookeoError.value = err.message || 'Sync failed';
  } finally {
    bookeoSyncing.value = false;
  }
};

// --- Athlete Sync (force refresh) ---
const syncing = ref(false);
const handleAthleteSync = async () => {
  syncing.value = true;
  try {
    await athleteStore.forceRefreshRoster();
    valorAthletes.value = [];
    await fetchValor();
  } catch { /* ignore */ }
  finally { syncing.value = false; }
};

// --- Valor Matching ---
const valorAthletes = ref<{ ValorID: string; Name: string; assigned: boolean }[]>([]);
const valorLoading = ref(false);
const saving = ref<Record<string, boolean>>({});
const toast = ref('');

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

onMounted(async () => {
  athleteStore.fetchRoster();
  await fetchValor();
});

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

const openDropdown = ref<string | null>(null);
const closeDrop = () => { setTimeout(() => { openDropdown.value = null; }, 200); };
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
    }
  } catch { /* ignore */ }
  finally { delete saving.value[athlete.athlete_uid!]; }
};

const valorNameById = (id: string | null | undefined) => {
  if (!id) return '';
  return valorAthletes.value.find(v => v.ValorID === String(id))?.Name || id;
};

// --- Cross-source mismatches ---
const mismatchedAthletes = computed(() => {
  return athleteStore.roster.filter(a => {
    if (!a.athlete_uid) return false;
    const hasHD = !!a.HawkinID;
    const hasValor = !!a.ValorID;
    return !hasHD || !hasValor;
  });
});

// --- Add Single Athlete (modal) ---
const showAddModal = ref(false);
const singleAthleteName = ref('');
const singleAthleteEmail = ref('');
const singleAthleteBirthDate = ref('');
const singleAthleteGender = ref('');
const singleAthleteGradYear = ref('');
const singleAthleteSchoolGrade = ref('');
const singleAthleteHeight = ref('');
const singleAthleteLimbDominance = ref('');
const singleAthleteSports = ref('');
const singleAthletePositions = ref('');
const singleAthleteSchool = ref('');
const isSingleLoading = ref(false);
const singleStatusMsg = ref('');
const singleIsError = ref(false);

const handleSingleAthlete = async () => {
  if (!singleAthleteName.value || !singleAthleteEmail.value) return;
  isSingleLoading.value = true;
  singleStatusMsg.value = '';
  singleIsError.value = false;

  const bDate = singleAthleteBirthDate.value;
  const bYear = bDate ? bDate.split('-')[0] : '';
  const bMonth = bDate ? bDate.split('-')[1] : '';
  const esc = (s: string) => s ? `"${s.replace(/"/g, '""')}"` : '';
  const csvData = `Name,Email,BirthDate,BirthYear,BirthMonth,Gender,GradYear,SchoolGrade,HeightInches,LimbDominance,Sports,Positions,CurrentSchool\n` +
    `${esc(singleAthleteName.value)},${esc(singleAthleteEmail.value)},${bDate},${bYear},${bMonth},${singleAthleteGender.value},${singleAthleteGradYear.value},${singleAthleteSchoolGrade.value},${singleAthleteHeight.value},${singleAthleteLimbDominance.value},${esc(singleAthleteSports.value)},${esc(singleAthletePositions.value)},${esc(singleAthleteSchool.value)}`;

  try {
    const uploadFn = httpsCallable(functions, 'upload_roster_csv');
    const result = await uploadFn({ csv_data: csvData });
    const data = result.data as any;
    if (data.status === 'success') {
      singleStatusMsg.value = `Added ${singleAthleteName.value}`;
      singleAthleteName.value = ''; singleAthleteEmail.value = ''; singleAthleteBirthDate.value = '';
      singleAthleteGender.value = ''; singleAthleteGradYear.value = ''; singleAthleteSchoolGrade.value = '';
      singleAthleteHeight.value = ''; singleAthleteLimbDominance.value = ''; singleAthleteSports.value = '';
      singleAthletePositions.value = ''; singleAthleteSchool.value = '';
      await athleteStore.forceRefreshRoster();
      setTimeout(() => { showAddModal.value = false; singleStatusMsg.value = ''; }, 1500);
    } else { singleIsError.value = true; singleStatusMsg.value = data.message; }
  } catch (err: any) { singleIsError.value = true; singleStatusMsg.value = err.message || 'Error'; }
  finally { isSingleLoading.value = false; }
};

// --- CSV Upload ---
const csvFile = ref<File | null>(null);
const csvStatusMsg = ref('');
const csvIsError = ref(false);
const csvIsLoading = ref(false);

const handleFileChange = (e: Event) => {
  const t = e.target as HTMLInputElement;
  if (t.files?.length) csvFile.value = t.files[0];
};

const handleCsvUpload = async () => {
  if (!csvFile.value) return;
  csvIsLoading.value = true; csvStatusMsg.value = ''; csvIsError.value = false;
  const reader = new FileReader();
  reader.onload = async (e) => {
    const text = e.target?.result as string;
    try {
      const uploadFn = httpsCallable(functions, 'upload_roster_csv');
      const result = await uploadFn({ csv_data: text });
      const data = result.data as any;
      if (data.status === 'success') {
        csvStatusMsg.value = data.message;
        csvFile.value = null;
        const fi = document.getElementById('csvFileInput') as HTMLInputElement;
        if (fi) fi.value = '';
        await athleteStore.forceRefreshRoster();
      } else { csvIsError.value = true; csvStatusMsg.value = data.message; }
    } catch (err: any) { csvIsError.value = true; csvStatusMsg.value = err.message || 'Error'; }
    finally { csvIsLoading.value = false; }
  };
  reader.readAsText(csvFile.value);
};
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
      <h1 class="text-2xl md:text-3xl font-bold text-gray-900">Manage Athletes</h1>
      <div class="flex gap-2">
        <button @click="handleAthleteSync" :disabled="syncing" class="flex items-center gap-2 px-3 py-2 text-sm font-semibold bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50">
          <svg :class="['w-4 h-4', syncing ? 'animate-spin' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          {{ syncing ? 'Syncing...' : 'Refresh' }}
        </button>
        <!-- Add dropdown -->
        <div class="relative">
          <button @click="showAddMenu = !showAddMenu" class="flex items-center gap-1 px-3 py-2 text-sm font-semibold bg-code8-dark text-white rounded-lg hover:bg-gray-800 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
            Add
            <svg class="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
          </button>
          <div v-if="showAddMenu" class="absolute right-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
            <button @click="showAddModal = true; showAddMenu = false" class="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 rounded-t-lg">Add Single Athlete</button>
            <button @click="showCsvModal = true; showAddMenu = false" class="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 rounded-b-lg border-t border-gray-100">Upload Roster CSV</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="toast" class="mb-4 p-3 rounded-lg bg-green-100 text-green-800 text-sm font-medium">{{ toast }}</div>

    <!-- 1. Sync from Bookeo -->
    <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mb-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
        <div>
          <h2 class="text-lg font-bold text-gray-900">Sync from Bookeo</h2>
          <p class="text-sm text-gray-500">Pull registered athletes from Bookeo. Cross-references Hawkin Dynamics and Valor.</p>
        </div>
        <button @click="handleBookeoSync" :disabled="bookeoSyncing" class="flex-shrink-0 flex items-center gap-2 px-5 py-2.5 text-sm font-bold bg-code8-gold text-white rounded-lg hover:bg-yellow-600 transition-colors disabled:opacity-50">
          <span v-if="bookeoSyncing" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
          {{ bookeoSyncing ? 'Syncing...' : 'Sync Bookeo' }}
        </button>
      </div>

      <div v-if="bookeoError" class="text-sm font-medium p-3 rounded-lg bg-red-50 text-red-600 border border-red-100">{{ bookeoError }}</div>

      <div v-if="bookeoResult" class="space-y-3">
        <div class="grid grid-cols-2 gap-3">
          <div class="p-3 rounded-lg bg-green-50 border border-green-200 text-center">
            <p class="text-2xl font-bold text-green-700">{{ bookeoResult.created }}</p>
            <p class="text-xs text-green-600">New Athletes</p>
          </div>
          <div class="p-3 rounded-lg bg-blue-50 border border-blue-200 text-center">
            <p class="text-2xl font-bold text-blue-700">{{ bookeoResult.matched }}</p>
            <p class="text-xs text-blue-600">Updated</p>
          </div>
        </div>
        <div v-if="bookeoResult.missing_valor?.length" class="p-3 rounded-lg bg-yellow-50 border border-yellow-200">
          <p class="text-sm font-semibold text-yellow-800 mb-1">Missing in Valor:</p>
          <p class="text-sm text-yellow-700">{{ bookeoResult.missing_valor.join(', ') }}</p>
        </div>
        <div v-if="bookeoResult.missing_hd?.length" class="p-3 rounded-lg bg-orange-50 border border-orange-200">
          <p class="text-sm font-semibold text-orange-800 mb-1">Missing in Hawkin Dynamics:</p>
          <p class="text-sm text-orange-700">{{ bookeoResult.missing_hd.join(', ') }}</p>
        </div>
        <div v-if="bookeoResult.errors?.length" class="p-3 rounded-lg bg-red-50 border border-red-200">
          <p class="text-sm font-semibold text-red-800 mb-1">Errors:</p>
          <p class="text-sm text-red-700">{{ bookeoResult.errors.join(', ') }}</p>
        </div>
      </div>
    </div>

    <!-- 2. Cross-Source Mismatches -->
    <div v-if="mismatchedAthletes.length" class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mb-6">
      <h2 class="text-lg font-bold text-gray-900 mb-1">Incomplete Profiles</h2>
      <p class="text-sm text-gray-500 mb-4">Athletes missing links to Hawkin Dynamics or Valor.</p>

      <div class="space-y-2">
        <div v-for="a in mismatchedAthletes" :key="a.athlete_uid!" class="flex flex-col sm:flex-row sm:items-center gap-2 p-3 rounded-lg bg-gray-50 border border-gray-100">
          <div class="flex-1 min-w-0">
            <p class="font-semibold text-gray-900 text-sm truncate">{{ a.Name }}</p>
            <p class="text-xs text-gray-500">{{ a.CurrentSchool || '' }}</p>
          </div>
          <div class="flex gap-3 text-xs font-medium">
            <span :class="a.HawkinID ? 'text-green-600' : 'text-red-500'">
              HD: {{ a.HawkinID ? 'Linked' : 'Missing' }}
            </span>
            <span :class="a.ValorID ? 'text-green-600' : 'text-red-500'">
              Valor: {{ a.ValorID ? 'Linked' : 'Missing' }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. Valor Matching -->
    <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mb-6">
      <h2 class="text-lg font-bold text-gray-900 mb-1">Valor Matching</h2>
      <p class="text-sm text-gray-500 mb-4">Link roster athletes to their Valor profiles. Suggested matches shown first.</p>

      <div v-if="valorLoading || athleteStore.loading" class="text-center py-8 text-gray-400 animate-pulse text-sm">Loading...</div>

      <template v-else>
        <div class="grid grid-cols-3 gap-3 mb-4">
          <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-2 text-center">
            <p class="text-xl font-bold text-yellow-700">{{ unmatchedRoster.length }}</p>
            <p class="text-xs text-yellow-600">Unmatched</p>
          </div>
          <div class="bg-green-50 border border-green-200 rounded-lg p-2 text-center">
            <p class="text-xl font-bold text-green-700">{{ matchedRoster.length }}</p>
            <p class="text-xs text-green-600">Matched</p>
          </div>
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-2 text-center">
            <p class="text-xl font-bold text-blue-700">{{ availableValor.length }}</p>
            <p class="text-xs text-blue-600">Valor Free</p>
          </div>
        </div>

        <!-- Unmatched -->
        <div v-if="unmatchedRoster.length" class="space-y-2 mb-4">
          <div v-for="athlete in unmatchedRoster" :key="athlete.athlete_uid!" class="flex flex-col sm:flex-row sm:items-center gap-2 p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-gray-900 text-sm truncate">{{ athlete.Name }}</p>
            </div>
            <div class="w-full sm:w-56 flex-shrink-0">
              <div v-if="suggestedMatch(athlete) && !saving[athlete.athlete_uid!]" class="flex items-center gap-1">
                <button @click="assign(athlete, suggestedMatch(athlete)!.ValorID, suggestedMatch(athlete)!.Name)" class="flex-1 bg-code8-gold/10 border border-code8-gold/30 text-code8-dark rounded-md px-2 py-1.5 text-xs font-medium hover:bg-code8-gold/20 truncate text-left">
                  Link: {{ suggestedMatch(athlete)!.Name }}
                </button>
                <button @click="openDropdown = athlete.athlete_uid!" class="p-1 text-gray-400 hover:text-gray-600">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                </button>
              </div>
              <div v-else-if="!saving[athlete.athlete_uid!]" class="relative">
                <input v-model="searchTerms[athlete.athlete_uid!]" type="text" placeholder="Search Valor..." class="w-full bg-white border border-gray-300 rounded-md px-2 py-1.5 text-xs focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" @focus="openDropdown = athlete.athlete_uid!" @blur="closeDrop" />
                <div v-if="openDropdown === athlete.athlete_uid" class="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-40 overflow-y-auto overscroll-contain">
                  <button v-for="va in filteredValorFor(athlete.athlete_uid!)" :key="va.ValorID" @mousedown.prevent="assign(athlete, va.ValorID, va.Name)" class="w-full text-left px-2 py-1.5 text-xs hover:bg-gray-100 border-b border-gray-50 last:border-0">{{ va.Name }}</button>
                  <div v-if="filteredValorFor(athlete.athlete_uid!).length === 0" class="px-2 py-1.5 text-xs text-gray-400">No matches</div>
                </div>
              </div>
              <div v-else class="text-xs text-gray-400 animate-pulse">Saving...</div>
            </div>
          </div>
        </div>

        <!-- Matched -->
        <details v-if="matchedRoster.length" class="group">
          <summary class="text-sm font-semibold text-gray-500 cursor-pointer hover:text-gray-700 mb-2">Matched Athletes ({{ matchedRoster.length }})</summary>
          <div class="space-y-1">
            <div v-for="athlete in matchedRoster" :key="athlete.athlete_uid!" class="flex items-center justify-between p-2 rounded-lg bg-green-50/50 border border-green-100 text-sm">
              <div class="flex items-center gap-2 min-w-0">
                <span class="w-2 h-2 rounded-full bg-green-500 flex-shrink-0"></span>
                <span class="font-medium text-gray-900 truncate">{{ athlete.Name }}</span>
                <span class="text-xs text-gray-500 truncate hidden sm:inline">→ {{ valorNameById(athlete.ValorID) }}</span>
              </div>
              <button @click="unlink(athlete)" :disabled="!!saving[athlete.athlete_uid!]" class="text-xs text-red-500 hover:text-red-700 font-medium flex-shrink-0 ml-2">Unlink</button>
            </div>
          </div>
        </details>
      </template>
    </div>

    <!-- Add Athlete Modal -->
    <div v-if="showAddModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        <div class="p-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/80">
          <h2 class="text-lg font-bold text-gray-900">Add Athlete to Roster</h2>
          <button @click="showAddModal = false" class="text-gray-400 hover:text-gray-600 p-1 rounded-md hover:bg-gray-200">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>
        <div class="p-6 overflow-y-auto flex-1">
          <form id="addAthleteForm" @submit.prevent="handleSingleAthlete" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Full Name *</label><input v-model="singleAthleteName" type="text" required class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Email *</label><input v-model="singleAthleteEmail" type="email" required class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Birth Date</label><input v-model="singleAthleteBirthDate" type="date" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Gender</label><select v-model="singleAthleteGender" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none"><option value="">--</option><option value="M">Male</option><option value="F">Female</option></select></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Grad Year</label><input v-model="singleAthleteGradYear" type="number" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Height (in)</label><input v-model="singleAthleteHeight" type="number" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div class="md:col-span-2"><label class="block text-sm font-semibold text-gray-700 mb-1">School</label><input v-model="singleAthleteSchool" type="text" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div class="md:col-span-2"><label class="block text-sm font-semibold text-gray-700 mb-1">Sport(s)</label><input v-model="singleAthleteSports" type="text" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
          </form>
          <div v-if="singleStatusMsg" :class="['mt-4 text-sm font-medium p-3 rounded-lg', singleIsError ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700']">{{ singleStatusMsg }}</div>
        </div>
        <div class="p-5 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
          <button @click="showAddModal = false" class="px-5 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-200 rounded-lg">Cancel</button>
          <button type="submit" form="addAthleteForm" :disabled="isSingleLoading" class="px-5 py-2 text-sm font-bold bg-code8-dark text-white rounded-lg hover:bg-gray-800 disabled:opacity-50">
            {{ isSingleLoading ? 'Saving...' : 'Save Athlete' }}
          </button>
        </div>
      </div>
    </div>
    <!-- CSV Upload Modal -->
    <div v-if="showCsvModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg flex flex-col overflow-hidden">
        <div class="p-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/80">
          <h2 class="text-lg font-bold text-gray-900">Upload Roster CSV</h2>
          <button @click="showCsvModal = false" class="text-gray-400 hover:text-gray-600 p-1 rounded-md hover:bg-gray-200">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>
        <div class="p-6">
          <p class="text-sm text-gray-500 mb-4">Upload a CSV file to update the system roster. Existing athletes are updated safely by name.</p>
          <form @submit.prevent="handleCsvUpload" class="space-y-4">
            <input id="csvFileInput" type="file" accept=".csv" @change="handleFileChange" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base" />
            <div v-if="csvStatusMsg" :class="['text-sm font-medium p-3 rounded-lg', csvIsError ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700']">{{ csvStatusMsg }}</div>
            <div class="flex justify-between items-center">
              <a href="data:text/csv;charset=utf-8,Name,Email,BirthDate,BirthYear,BirthMonth,Gender,GradYear,SchoolGrade,HeightInches,LimbDominance,Sports,Positions,CurrentSchool%0AJohn%20Doe,john@example.com,2005-08-15,2005,08,M,2024,12,72,Right,Football,QB,SLO%20High" download="athlete_template.csv" class="text-xs text-code8-gold font-semibold hover:underline">Download Template</a>
              <button type="submit" :disabled="csvIsLoading || !csvFile" class="px-5 py-2 text-sm font-bold bg-code8-dark text-white rounded-lg hover:bg-gray-800 disabled:opacity-50">
                {{ csvIsLoading ? 'Uploading...' : 'Upload' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>
