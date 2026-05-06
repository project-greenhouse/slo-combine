<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useAthleteStore, type RosterItem } from '../stores/athleteStore';
import { useAuthStore } from '../stores/authStore';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../firebase/config';

const store = useAthleteStore();
const authStore = useAuthStore();

const searchQuery = ref('');
const rightTab = ref<'profile' | 'manage'>('profile');
const isStaff = computed(() => authStore.userRole === 'admin' || authStore.userRole === 'coach');

onMounted(async () => {
  store.fetchRoster();
  if (isStaff.value) await fetchValor();
});

const filteredRoster = computed(() => {
  if (!searchQuery.value) return store.roster;
  const lower = searchQuery.value.toLowerCase();
  return store.roster.filter(a => a.Name.toLowerCase().includes(lower));
});

const handleAthleteClick = (a: RosterItem) => {
  store.selectAthlete(a);
  rightTab.value = 'profile';
};

// ── Metrics computeds ──
const bestSprint = computed(() => {
  const raw = store.metrics?.sprint40 || [];
  let best = Infinity;
  raw.forEach((r: any) => { if ((r.Distance == 40 || r.Distance == '40') && Number(r.Total) > 0 && Number(r.Total) < best) best = Number(r.Total); });
  return best === Infinity ? '--' : best.toFixed(2) + 's';
});
const bestAgility = computed(() => {
  const raw = store.metrics?.pro_agility || [];
  let best = Infinity;
  raw.forEach((r: any) => { if ((r.Distance == 20 || r.Distance == '20') && Number(r.Total) > 0 && Number(r.Total) < best) best = Number(r.Total); });
  return best === Infinity ? '--' : best.toFixed(2) + 's';
});
const bestVert = computed(() => { const r = store.metrics?.standing_vert || []; return r.length && r[0].VerticalJump ? r[0].VerticalJump + '"' : '--'; });
const bestBroad = computed(() => { const r = store.metrics?.broad_jump || []; return r.length && r[0].BestBroadJump ? r[0].BestBroadJump + '"' : '--'; });

// ── Edit Modal ──
const showEditModal = ref(false);
const isSaving = ref(false);
const saveError = ref('');
const editForm = ref<Partial<RosterItem>>({});
const openEditModal = () => { if (store.selectedAthlete) { editForm.value = { ...store.selectedAthlete }; saveError.value = ''; showEditModal.value = true; } };
const saveAthleteInfo = async () => {
  if (!store.selectedAthlete) return;
  isSaving.value = true; saveError.value = '';
  try {
    const fn = httpsCallable(functions, 'update_athlete_info');
    const res = await fn({ ...editForm.value, athlete_uid: store.selectedAthlete.athlete_uid || null });
    const data = res.data as any;
    if (data.status === 'success') {
      const idx = store.roster.findIndex(a => a.Name === store.selectedAthlete!.Name);
      if (idx !== -1) { store.roster[idx] = { ...store.roster[idx], ...editForm.value, athlete_uid: data.athlete_uid || store.selectedAthlete.athlete_uid }; store.selectedAthlete = store.roster[idx]; }
      showEditModal.value = false;
    } else saveError.value = data.message;
  } catch (e: any) { saveError.value = e.message || 'Failed'; }
  finally { isSaving.value = false; }
};

// ── Valor linking (per-athlete on profile) ──
const valorAthletes = ref<{ ValorID: string; Name: string; assigned: boolean }[]>([]);
const valorLoading = ref(false);
const valorSearch = ref('');
const valorDropdownOpen = ref(false);
const valorSaving = ref(false);
const valorToast = ref('');

const filteredValorAthletes = computed(() => {
  const q = valorSearch.value.toLowerCase();
  const list = valorAthletes.value.filter(a => !a.assigned);
  return q ? list.filter(a => a.Name.toLowerCase().includes(q)) : list;
});

const fetchValor = async () => {
  valorLoading.value = true;
  try { const res = await httpsCallable(functions, 'get_valor_athletes')({}); const d = (res.data as any); if (d.status === 'success') valorAthletes.value = d.data; } catch {}
  finally { valorLoading.value = false; }
};

const assignValor = async (vid: string, vname: string) => {
  if (!store.selectedAthlete?.athlete_uid) return;
  valorSaving.value = true; valorDropdownOpen.value = false; valorSearch.value = '';
  try {
    const res = await httpsCallable(functions, 'update_athlete_info')({ athlete_uid: store.selectedAthlete.athlete_uid, ValorID: vid });
    if ((res.data as any).status === 'success') {
      const idx = store.roster.findIndex(a => a.athlete_uid === store.selectedAthlete!.athlete_uid);
      if (idx !== -1) { store.roster[idx] = { ...store.roster[idx], ValorID: vid }; store.selectedAthlete = store.roster[idx]; }
      const va = valorAthletes.value.find(a => a.ValorID === vid); if (va) va.assigned = true;
      valorToast.value = `Linked: ${vname}`; setTimeout(() => { valorToast.value = ''; }, 3000);
    }
  } catch {} finally { valorSaving.value = false; }
};
const unlinkValor = async () => {
  if (!store.selectedAthlete?.athlete_uid) return;
  valorSaving.value = true;
  try {
    const res = await httpsCallable(functions, 'update_athlete_info')({ athlete_uid: store.selectedAthlete.athlete_uid, ValorID: '' });
    if ((res.data as any).status === 'success') {
      const old = store.selectedAthlete.ValorID;
      const idx = store.roster.findIndex(a => a.athlete_uid === store.selectedAthlete!.athlete_uid);
      if (idx !== -1) { store.roster[idx] = { ...store.roster[idx], ValorID: null }; store.selectedAthlete = store.roster[idx]; }
      if (old) { const va = valorAthletes.value.find(a => a.ValorID === String(old)); if (va) va.assigned = false; }
      valorToast.value = 'Unlinked'; setTimeout(() => { valorToast.value = ''; }, 3000);
    }
  } catch {} finally { valorSaving.value = false; }
};

// ── Manage tab: Bookeo sync ──
const bookeoSyncing = ref(false);
const bookeoResult = ref<any>(null);
const bookeoError = ref('');
const handleBookeoSync = async () => {
  bookeoSyncing.value = true; bookeoResult.value = null; bookeoError.value = '';
  try {
    const res = await httpsCallable(functions, 'sync_bookeo_roster')({});
    const d = res.data as any;
    if (d.status === 'success') { bookeoResult.value = d; await store.forceRefreshRoster(); valorAthletes.value = []; await fetchValor(); }
    else bookeoError.value = d.message || 'Failed';
  } catch (e: any) { bookeoError.value = e.message || 'Failed'; }
  finally { bookeoSyncing.value = false; }
};

// ── Manage tab: cross-source matching ──
const manageSaving = ref<Record<string, boolean>>({});
const manageToast = ref('');
const openManageDropdown = ref<string | null>(null);
const manageSearchTerms = ref<Record<string, string>>({});

function normalize(name: string): string { return name.toLowerCase().replace(/[.\-']/g, '').replace(/\s+/g, ' ').trim(); }

const fullySynced = computed(() => store.roster.filter(a => a.athlete_uid && a.HawkinID && a.ValorID));
const missingHD = computed(() => store.roster.filter(a => a.athlete_uid && !a.HawkinID));
const missingValor = computed(() => store.roster.filter(a => a.athlete_uid && !a.ValorID));
const availableValor = computed(() => valorAthletes.value.filter(v => !v.assigned));

function suggestedValorMatch(athlete: RosterItem) {
  const n = normalize(athlete.Name);
  return availableValor.value.find(v => normalize(v.Name) === n) || null;
}
const filteredValorFor = (uid: string) => {
  const q = (manageSearchTerms.value[uid] || '').toLowerCase();
  return q ? availableValor.value.filter(v => v.Name.toLowerCase().includes(q)) : availableValor.value;
};
const manageAssign = async (athlete: RosterItem, vid: string, vname: string) => {
  if (!athlete.athlete_uid) return;
  manageSaving.value[athlete.athlete_uid] = true; openManageDropdown.value = null;
  try {
    const res = await httpsCallable(functions, 'update_athlete_info')({ athlete_uid: athlete.athlete_uid, ValorID: vid });
    if ((res.data as any).status === 'success') {
      const idx = store.roster.findIndex(a => a.athlete_uid === athlete.athlete_uid);
      if (idx !== -1) store.roster[idx] = { ...store.roster[idx], ValorID: vid };
      const va = valorAthletes.value.find(a => a.ValorID === vid); if (va) va.assigned = true;
      manageToast.value = `Linked ${athlete.Name} → ${vname}`; setTimeout(() => { manageToast.value = ''; }, 3000);
    }
  } catch {} finally { delete manageSaving.value[athlete.athlete_uid!]; }
};
const valorNameById = (id: string | null | undefined) => { if (!id) return ''; return valorAthletes.value.find(v => v.ValorID === String(id))?.Name || id; };

// ── Add athlete / CSV ──
const showAddMenu = ref(false);
const showAddModal = ref(false);
const showCsvModal = ref(false);
const singleName = ref(''); const singleEmail = ref(''); const singleBirthDate = ref(''); const singleGender = ref('');
const singleGradYear = ref(''); const singleHeight = ref(''); const singleSchool = ref(''); const singleSports = ref('');
const isSingleLoading = ref(false); const singleMsg = ref(''); const singleIsError = ref(false);
const handleSingleAthlete = async () => {
  if (!singleName.value || !singleEmail.value) return;
  isSingleLoading.value = true; singleMsg.value = ''; singleIsError.value = false;
  const esc = (s: string) => s ? `"${s.replace(/"/g, '""')}"` : '';
  const bd = singleBirthDate.value;
  const csv = `Name,Email,BirthDate,BirthYear,BirthMonth,Gender,GradYear,HeightInches,Sports,CurrentSchool\n${esc(singleName.value)},${esc(singleEmail.value)},${bd},${bd?.split('-')[0]||''},${bd?.split('-')[1]||''},${singleGender.value},${singleGradYear.value},${singleHeight.value},${esc(singleSports.value)},${esc(singleSchool.value)}`;
  try {
    const res = await httpsCallable(functions, 'upload_roster_csv')({ csv_data: csv });
    if ((res.data as any).status === 'success') {
      singleMsg.value = `Added ${singleName.value}`; singleName.value = ''; singleEmail.value = '';
      await store.forceRefreshRoster();
      setTimeout(() => { showAddModal.value = false; singleMsg.value = ''; }, 1500);
    } else { singleIsError.value = true; singleMsg.value = (res.data as any).message; }
  } catch (e: any) { singleIsError.value = true; singleMsg.value = e.message || 'Error'; }
  finally { isSingleLoading.value = false; }
};

const csvFile = ref<File | null>(null); const csvMsg = ref(''); const csvIsError = ref(false); const csvLoading = ref(false);
const handleFileChange = (e: Event) => { const t = e.target as HTMLInputElement; if (t.files?.length) csvFile.value = t.files[0]; };
const handleCsvUpload = async () => {
  if (!csvFile.value) return;
  csvLoading.value = true; csvMsg.value = ''; csvIsError.value = false;
  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      const res = await httpsCallable(functions, 'upload_roster_csv')({ csv_data: e.target?.result as string });
      if ((res.data as any).status === 'success') { csvMsg.value = (res.data as any).message; csvFile.value = null; await store.forceRefreshRoster(); }
      else { csvIsError.value = true; csvMsg.value = (res.data as any).message; }
    } catch (err: any) { csvIsError.value = true; csvMsg.value = err.message || 'Error'; }
    finally { csvLoading.value = false; }
  };
  reader.readAsText(csvFile.value);
};
</script>

<template>
  <div class="h-full flex flex-col max-w-7xl mx-auto">
    <!-- Header bar -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4 flex-shrink-0">
      <h1 class="text-2xl md:text-3xl font-bold text-gray-900">Athletes</h1>
      <div v-if="isStaff" class="flex gap-2">
        <button @click="store.forceRefreshRoster()" :disabled="store.loading" class="flex items-center gap-2 px-3 py-2 text-sm font-semibold bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50">
          <svg :class="['w-4 h-4', store.loading ? 'animate-spin' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          {{ store.loading ? 'Syncing...' : 'Refresh' }}
        </button>
        <div class="relative">
          <button @click="showAddMenu = !showAddMenu" class="flex items-center gap-1 px-3 py-2 text-sm font-semibold bg-code8-dark text-white rounded-lg hover:bg-gray-800">
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

    <div class="flex flex-col lg:flex-row gap-4 flex-1 min-h-0">
      <!-- Roster sidebar -->
      <div class="w-full lg:w-1/3 bg-white border border-gray-200 rounded-xl shadow-sm flex flex-col overflow-hidden h-[400px] lg:h-[calc(100vh-10rem)]">
        <div class="p-3 border-b border-gray-100 bg-gray-50">
          <input v-model="searchQuery" type="text" placeholder="Search athletes..." class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-code8-gold focus:border-code8-gold text-sm" />
        </div>
        <div v-if="store.loading" class="flex-1 flex items-center justify-center text-code8-gold font-semibold animate-pulse text-sm">Loading...</div>
        <div v-else class="flex-1 overflow-y-auto p-2 space-y-1">
          <button v-for="athlete in filteredRoster" :key="athlete.Name" @click="handleAthleteClick(athlete)"
            :class="['w-full text-left px-3 py-2.5 rounded-lg transition-all border text-sm',
              store.selectedAthlete?.Name === athlete.Name ? 'bg-code8-gold/10 border-code8-gold shadow-sm' : 'border-transparent hover:bg-gray-50']">
            <div class="font-bold" :class="store.selectedAthlete?.Name === athlete.Name ? 'text-code8-dark' : 'text-gray-800'">{{ athlete.Name }}</div>
            <div class="text-xs text-gray-500 mt-0.5 flex justify-between">
              <span class="truncate pr-2">{{ athlete.CurrentSchool || '' }}</span>
              <div class="flex gap-1 flex-shrink-0">
                <span :class="athlete.HawkinID ? 'text-green-500' : 'text-gray-300'" title="Hawkin Dynamics">HD</span>
                <span :class="athlete.ValorID ? 'text-green-500' : 'text-gray-300'" title="Valor">V</span>
              </div>
            </div>
          </button>
          <div v-if="filteredRoster.length === 0" class="text-center py-6 text-gray-400 text-sm">No athletes found.</div>
        </div>
      </div>

      <!-- Right panel -->
      <div class="w-full lg:w-2/3 bg-white border border-gray-200 rounded-xl shadow-sm flex flex-col overflow-hidden h-[600px] lg:h-[calc(100vh-10rem)]">

        <!-- Tab bar (staff only) -->
        <div v-if="isStaff" class="flex border-b border-gray-200 flex-shrink-0">
          <button @click="rightTab = 'profile'" :class="['flex-1 py-3 text-sm font-semibold text-center transition-colors', rightTab === 'profile' ? 'text-code8-gold border-b-2 border-code8-gold' : 'text-gray-500 hover:text-gray-700']">Profile</button>
          <button @click="rightTab = 'manage'" :class="['flex-1 py-3 text-sm font-semibold text-center transition-colors', rightTab === 'manage' ? 'text-code8-gold border-b-2 border-code8-gold' : 'text-gray-500 hover:text-gray-700']">Manage</button>
        </div>

        <div class="flex-1 overflow-y-auto">
          <!-- ═══ PROFILE TAB ═══ -->
          <template v-if="rightTab === 'profile'">
            <template v-if="store.selectedAthlete">
              <div class="bg-gray-900 p-6 md:p-8 relative overflow-hidden flex-shrink-0">
                <div class="absolute top-[-10%] left-[-5%] w-[40%] h-[150%] bg-code8-gold/20 rounded-full blur-[80px] pointer-events-none"></div>
                <div class="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
                  <div>
                    <h2 class="text-2xl md:text-3xl font-black text-white tracking-tight uppercase">{{ store.selectedAthlete.Name }}</h2>
                    <p class="text-gray-400 text-sm mt-1">{{ store.selectedAthlete.Email || 'No email' }}</p>
                  </div>
                  <button v-if="isStaff" @click="openEditModal" class="px-4 py-2 bg-white/10 hover:bg-white/20 text-white border border-white/20 rounded-lg text-sm font-semibold flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                    Edit
                  </button>
                </div>
              </div>

              <div class="p-6 md:p-8 space-y-6">
                <!-- Info grid -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div class="bg-gray-50 p-3 rounded-xl border border-gray-100"><p class="text-xs text-gray-500 mb-0.5">School</p><p class="font-bold text-gray-900 text-sm truncate">{{ store.selectedAthlete.CurrentSchool || '--' }}</p></div>
                  <div class="bg-gray-50 p-3 rounded-xl border border-gray-100"><p class="text-xs text-gray-500 mb-0.5">Grad Year</p><p class="font-bold text-gray-900 text-sm">{{ store.selectedAthlete.GradYear || '--' }}</p></div>
                  <div class="bg-gray-50 p-3 rounded-xl border border-gray-100"><p class="text-xs text-gray-500 mb-0.5">Sport(s)</p><p class="font-bold text-gray-900 text-sm truncate">{{ store.selectedAthlete.Sports || '--' }}</p></div>
                  <div class="bg-gray-50 p-3 rounded-xl border border-gray-100"><p class="text-xs text-gray-500 mb-0.5">Height</p><p class="font-bold text-gray-900 text-sm">{{ store.selectedAthlete.HeightInches ? store.selectedAthlete.HeightInches + '"' : '--' }}</p></div>
                </div>

                <!-- System links -->
                <div v-if="isStaff">
                  <h3 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">System Links</h3>
                  <div v-if="valorToast" class="mb-2 p-2 rounded-lg bg-green-100 text-green-800 text-xs font-medium">{{ valorToast }}</div>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div class="bg-gray-50 p-3 rounded-xl border border-gray-100">
                      <p class="text-xs text-gray-500 mb-1">Hawkin Dynamics</p>
                      <div class="flex items-center gap-2">
                        <span :class="['w-2 h-2 rounded-full', store.selectedAthlete.HawkinID ? 'bg-green-500' : 'bg-gray-300']"></span>
                        <span class="text-sm" :class="store.selectedAthlete.HawkinID ? 'font-bold text-gray-900' : 'text-gray-500'">{{ store.selectedAthlete.HawkinID ? 'Linked' : 'Not linked' }}</span>
                      </div>
                    </div>
                    <div class="bg-gray-50 p-3 rounded-xl border border-gray-100">
                      <p class="text-xs text-gray-500 mb-1">Valor</p>
                      <div v-if="store.selectedAthlete.ValorID" class="flex items-center justify-between">
                        <div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-green-500"></span><span class="font-bold text-gray-900 text-sm truncate">{{ valorNameById(store.selectedAthlete.ValorID) }}</span></div>
                        <button @click="unlinkValor" :disabled="valorSaving" class="text-xs text-red-500 hover:text-red-700 font-medium">{{ valorSaving ? '...' : 'Unlink' }}</button>
                      </div>
                      <div v-else class="relative">
                        <input v-model="valorSearch" type="text" placeholder="Search Valor..." class="w-full bg-white border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" @focus="fetchValor(); valorDropdownOpen = true" @blur="setTimeout(() => valorDropdownOpen = false, 200)" />
                        <div v-if="valorDropdownOpen" class="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-40 overflow-y-auto overscroll-contain">
                          <div v-if="valorLoading" class="px-3 py-2 text-sm text-gray-400">Loading...</div>
                          <button v-else v-for="va in filteredValorAthletes" :key="va.ValorID" @mousedown.prevent="assignValor(va.ValorID, va.Name)" class="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 border-b border-gray-50 last:border-0">{{ va.Name }}</button>
                          <div v-if="!valorLoading && filteredValorAthletes.length === 0" class="px-3 py-2 text-sm text-gray-400">No matches</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Testing highlights -->
                <div>
                  <h3 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Testing Highlights</h3>
                  <div v-if="store.metricsLoading" class="text-xs text-code8-gold animate-pulse">Loading metrics...</div>
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div class="border border-gray-200 p-4 rounded-xl text-center"><span class="text-xs font-bold text-gray-400 uppercase block mb-1">40yd</span><span class="text-2xl font-black text-gray-900">{{ bestSprint }}</span></div>
                    <div class="border border-gray-200 p-4 rounded-xl text-center"><span class="text-xs font-bold text-gray-400 uppercase block mb-1">Pro Agility</span><span class="text-2xl font-black text-gray-900">{{ bestAgility }}</span></div>
                    <div class="border border-gray-200 p-4 rounded-xl text-center"><span class="text-xs font-bold text-gray-400 uppercase block mb-1">Vertical</span><span class="text-2xl font-black text-gray-900">{{ bestVert }}</span></div>
                    <div class="border border-gray-200 p-4 rounded-xl text-center"><span class="text-xs font-bold text-gray-400 uppercase block mb-1">Broad Jump</span><span class="text-2xl font-black text-gray-900">{{ bestBroad }}</span></div>
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="flex-1 flex flex-col items-center justify-center text-center p-8">
              <svg class="w-16 h-16 text-gray-200 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
              <h3 class="text-xl font-bold text-gray-900 mb-1">Select an Athlete</h3>
              <p class="text-sm text-gray-500">Choose from the roster to view their profile.</p>
            </div>
          </template>

          <!-- ═══ MANAGE TAB ═══ -->
          <template v-if="rightTab === 'manage'">
            <div class="p-6 space-y-6">
              <div v-if="manageToast" class="p-3 rounded-lg bg-green-100 text-green-800 text-sm font-medium">{{ manageToast }}</div>

              <!-- Bookeo Sync -->
              <div class="bg-gray-50 p-4 rounded-xl border border-gray-100">
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
                  <div><h3 class="font-bold text-gray-900">Sync from Bookeo</h3><p class="text-xs text-gray-500">Pull registered athletes. Cross-refs HD and Valor.</p></div>
                  <button @click="handleBookeoSync" :disabled="bookeoSyncing" class="flex-shrink-0 flex items-center gap-2 px-4 py-2 text-sm font-bold bg-code8-gold text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50">
                    <span v-if="bookeoSyncing" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    {{ bookeoSyncing ? 'Syncing...' : 'Sync Bookeo' }}
                  </button>
                </div>
                <div v-if="bookeoError" class="text-sm p-2 rounded bg-red-50 text-red-600">{{ bookeoError }}</div>
                <div v-if="bookeoResult" class="grid grid-cols-2 gap-2 mt-2">
                  <div class="p-2 rounded bg-green-50 border border-green-200 text-center"><p class="text-lg font-bold text-green-700">{{ bookeoResult.created }}</p><p class="text-xs text-green-600">New</p></div>
                  <div class="p-2 rounded bg-blue-50 border border-blue-200 text-center"><p class="text-lg font-bold text-blue-700">{{ bookeoResult.matched }}</p><p class="text-xs text-blue-600">Updated</p></div>
                </div>
              </div>

              <!-- Fully Synced -->
              <details v-if="fullySynced.length">
                <summary class="text-sm font-bold text-green-700 cursor-pointer hover:text-green-900 flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full bg-green-500"></span>
                  Fully Synced ({{ fullySynced.length }})
                </summary>
                <div class="mt-2 space-y-1 max-h-40 overflow-y-auto">
                  <div v-for="a in fullySynced" :key="a.athlete_uid!" class="text-sm text-gray-700 px-3 py-1.5 bg-green-50/50 rounded">{{ a.Name }}</div>
                </div>
              </details>

              <!-- Missing HD -->
              <div v-if="missingHD.length" class="bg-orange-50 p-4 rounded-xl border border-orange-200">
                <h3 class="text-sm font-bold text-orange-800 mb-2">Missing in Hawkin Dynamics ({{ missingHD.length }})</h3>
                <p class="text-xs text-orange-600 mb-3">These athletes need to be created or name-matched in HD. Bookeo name shown (source of truth).</p>
                <div class="space-y-1">
                  <div v-for="a in missingHD" :key="a.athlete_uid!" class="text-sm text-orange-900 px-3 py-1.5 bg-orange-100/50 rounded flex justify-between">
                    <span>{{ a.Name }}</span>
                  </div>
                </div>
              </div>

              <!-- Missing Valor (with matching UI) -->
              <div v-if="missingValor.length" class="bg-yellow-50 p-4 rounded-xl border border-yellow-200">
                <h3 class="text-sm font-bold text-yellow-800 mb-2">Missing in Valor ({{ missingValor.length }})</h3>
                <p class="text-xs text-yellow-600 mb-3">Link to existing Valor profiles, or create manually in Valor first.</p>
                <div class="space-y-2">
                  <div v-for="athlete in missingValor" :key="athlete.athlete_uid!" class="flex flex-col sm:flex-row sm:items-center gap-2 p-2 bg-yellow-100/50 rounded">
                    <span class="flex-1 text-sm font-medium text-yellow-900 truncate">{{ athlete.Name }}</span>
                    <div class="w-full sm:w-52 flex-shrink-0">
                      <div v-if="suggestedValorMatch(athlete) && !manageSaving[athlete.athlete_uid!]" class="flex items-center gap-1">
                        <button @click="manageAssign(athlete, suggestedValorMatch(athlete)!.ValorID, suggestedValorMatch(athlete)!.Name)" class="flex-1 bg-code8-gold/10 border border-code8-gold/30 text-code8-dark rounded-md px-2 py-1 text-xs font-medium hover:bg-code8-gold/20 truncate text-left">Link: {{ suggestedValorMatch(athlete)!.Name }}</button>
                        <button @click="openManageDropdown = athlete.athlete_uid!" class="p-1 text-gray-400 hover:text-gray-600"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg></button>
                      </div>
                      <div v-else-if="!manageSaving[athlete.athlete_uid!]" class="relative">
                        <input v-model="manageSearchTerms[athlete.athlete_uid!]" type="text" placeholder="Search Valor..." class="w-full bg-white border border-gray-300 rounded-md px-2 py-1 text-xs focus:border-code8-gold outline-none" @focus="openManageDropdown = athlete.athlete_uid!" @blur="setTimeout(() => { if (openManageDropdown === athlete.athlete_uid) openManageDropdown = null; }, 200)" />
                        <div v-if="openManageDropdown === athlete.athlete_uid" class="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-36 overflow-y-auto overscroll-contain">
                          <button v-for="va in filteredValorFor(athlete.athlete_uid!)" :key="va.ValorID" @mousedown.prevent="manageAssign(athlete, va.ValorID, va.Name)" class="w-full text-left px-2 py-1.5 text-xs hover:bg-gray-100 border-b border-gray-50 last:border-0">{{ va.Name }}</button>
                          <div v-if="filteredValorFor(athlete.athlete_uid!).length === 0" class="px-2 py-1.5 text-xs text-gray-400">No matches</div>
                        </div>
                      </div>
                      <div v-else class="text-xs text-gray-400 animate-pulse">Saving...</div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="!missingHD.length && !missingValor.length && fullySynced.length" class="text-center py-6 text-green-600 font-semibold text-sm">All athletes are fully synced across all sources.</div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="showEditModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        <div class="p-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/80">
          <h2 class="text-lg font-bold text-gray-900">Edit Athlete Profile</h2>
          <button @click="showEditModal = false" class="text-gray-400 hover:text-gray-600 p-1 rounded-md hover:bg-gray-200"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg></button>
        </div>
        <div class="p-6 overflow-y-auto flex-1">
          <form id="editForm" @submit.prevent="saveAthleteInfo" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Full Name *</label><input v-model="editForm.Name" type="text" required class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Email</label><input v-model="editForm.Email" type="email" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Birth Date</label><input v-model="editForm.BirthDate" type="date" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Gender</label><select v-model="editForm.Gender" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none"><option value="">--</option><option value="M">Male</option><option value="F">Female</option></select></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Grad Year</label><input v-model="editForm.GradYear" type="number" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Height (in)</label><input v-model="editForm.HeightInches" type="number" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div class="md:col-span-2"><label class="block text-sm font-semibold text-gray-700 mb-1">Sport(s)</label><input v-model="editForm.Sports" type="text" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div class="md:col-span-2"><label class="block text-sm font-semibold text-gray-700 mb-1">School</label><input v-model="editForm.CurrentSchool" type="text" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
          </form>
          <div v-if="saveError" class="mt-3 text-sm p-3 rounded-lg bg-red-50 text-red-600">{{ saveError }}</div>
        </div>
        <div class="p-5 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
          <button @click="showEditModal = false" class="px-5 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-200 rounded-lg">Cancel</button>
          <button type="submit" form="editForm" :disabled="isSaving" class="px-5 py-2 text-sm font-bold bg-code8-dark text-white rounded-lg hover:bg-gray-800 disabled:opacity-50">{{ isSaving ? 'Saving...' : 'Save' }}</button>
        </div>
      </div>
    </div>

    <!-- Add Athlete Modal -->
    <div v-if="showAddModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col overflow-hidden">
        <div class="p-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/80">
          <h2 class="text-lg font-bold text-gray-900">Add Athlete</h2>
          <button @click="showAddModal = false" class="text-gray-400 hover:text-gray-600 p-1 rounded-md hover:bg-gray-200"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg></button>
        </div>
        <div class="p-6 overflow-y-auto flex-1">
          <form id="addForm" @submit.prevent="handleSingleAthlete" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Name *</label><input v-model="singleName" type="text" required class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Email *</label><input v-model="singleEmail" type="email" required class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" /></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">Gender</label><select v-model="singleGender" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 focus:border-code8-gold outline-none"><option value="">--</option><option value="M">Male</option><option value="F">Female</option></select></div>
            <div><label class="block text-sm font-semibold text-gray-700 mb-1">School</label><input v-model="singleSchool" type="text" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 focus:border-code8-gold outline-none" /></div>
          </form>
          <div v-if="singleMsg" :class="['mt-3 text-sm p-3 rounded-lg', singleIsError ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700']">{{ singleMsg }}</div>
        </div>
        <div class="p-5 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
          <button @click="showAddModal = false" class="px-5 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-200 rounded-lg">Cancel</button>
          <button type="submit" form="addForm" :disabled="isSingleLoading" class="px-5 py-2 text-sm font-bold bg-code8-dark text-white rounded-lg hover:bg-gray-800 disabled:opacity-50">{{ isSingleLoading ? 'Saving...' : 'Save' }}</button>
        </div>
      </div>
    </div>

    <!-- CSV Modal -->
    <div v-if="showCsvModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg flex flex-col overflow-hidden">
        <div class="p-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/80">
          <h2 class="text-lg font-bold text-gray-900">Upload Roster CSV</h2>
          <button @click="showCsvModal = false" class="text-gray-400 hover:text-gray-600 p-1 rounded-md hover:bg-gray-200"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg></button>
        </div>
        <div class="p-6">
          <form @submit.prevent="handleCsvUpload" class="space-y-4">
            <input type="file" accept=".csv" @change="handleFileChange" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base" />
            <div v-if="csvMsg" :class="['text-sm p-3 rounded-lg', csvIsError ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700']">{{ csvMsg }}</div>
            <button type="submit" :disabled="csvLoading || !csvFile" class="w-full py-3 text-sm font-bold bg-code8-dark text-white rounded-lg hover:bg-gray-800 disabled:opacity-50">{{ csvLoading ? 'Uploading...' : 'Upload' }}</button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(209, 213, 219, 0.8); border-radius: 4px; }
</style>
