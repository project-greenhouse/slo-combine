<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAthleteStore, type RosterItem } from '../stores/athleteStore';
import { useAuthStore } from '../stores/authStore';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../firebase/config';

const store = useAthleteStore();
const authStore = useAuthStore();
const router = useRouter();

const searchQuery = ref('');
const filteredRoster = computed(() => {
  if (!searchQuery.value) return store.roster;
  const lower = searchQuery.value.toLowerCase();
  return store.roster.filter(a => a.Name.toLowerCase().includes(lower));
});

onMounted(() => {
  store.fetchRoster();
});

const handleAthleteClick = (athlete: RosterItem) => {
  store.selectAthlete(athlete);
};

// Quick Stats parsing from the currently loaded metrics
const bestSprint = computed(() => {
  const raw = store.metrics?.sprint40 || [];
  let best = Infinity;
  raw.forEach((r: any) => {
    if (r.Distance == 40 || r.Distance == '40') {
      const val = Number(r.Total);
      if (val > 0 && val < best) best = val;
    }
  });
  return best === Infinity ? '--' : best.toFixed(2) + 's';
});

const bestAgility = computed(() => {
  const raw = store.metrics?.pro_agility || [];
  let best = Infinity;
  raw.forEach((r: any) => {
    if (r.Distance == 20 || r.Distance == '20') {
      const val = Number(r.Total);
      if (val > 0 && val < best) best = val;
    }
  });
  return best === Infinity ? '--' : best.toFixed(2) + 's';
});

const bestVert = computed(() => {
  const raw = store.metrics?.standing_vert || [];
  if (raw.length > 0 && raw[0].VerticalJump) return raw[0].VerticalJump + '"';
  return '--';
});

const bestBroad = computed(() => {
  const raw = store.metrics?.broad_jump || [];
  if (raw.length > 0 && raw[0].BestBroadJump) return raw[0].BestBroadJump + '"';
  return '--';
});

const lastTestedDate = computed(() => {
  if (!store.metrics) return '--';
  
  const dates: number[] = [];
  
  const extractDates = (arr: any[], dateField: string) => {
    if (Array.isArray(arr)) {
      arr.forEach(item => {
        if (item && item[dateField]) {
          const dateStr = String(item[dateField]);
          const d = new Date(dateStr);
          if (!isNaN(d.getTime())) {
            dates.push(d.getTime());
          } else {
            // Handle DD/MM/YYYY format found in Swift/Hawkin exports
            const match = dateStr.match(/(\d{2})\/(\d{2})\/(\d{4})/);
            if (match) dates.push(new Date(`${match[3]}-${match[2]}-${match[1]}`).getTime());
          }
        }
      });
    }
  };

  extractDates(store.metrics.sprint40, 'ActivityTimestamp');
  extractDates(store.metrics.pro_agility, 'ActivityTimestamp');
  extractDates(store.metrics.standing_vert, 'ActivityTimestamp');
  extractDates(store.metrics.broad_jump, 'ActivityTimestamp');
  
  if (dates.length === 0) return 'No tests recorded';
  
  const maxDate = new Date(Math.max(...dates));
  return maxDate.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
});

// Edit Modal State
const showEditModal = ref(false);
const isSaving = ref(false);
const saveError = ref('');
const editForm = ref<Partial<RosterItem>>({});

const openEditModal = () => {
  if (store.selectedAthlete) {
    editForm.value = { ...store.selectedAthlete };
    saveError.value = '';
    showEditModal.value = true;
  }
};

const saveAthleteInfo = async () => {
  if (!store.selectedAthlete) return;
  isSaving.value = true;
  saveError.value = '';
  
  try {
    const updateFn = httpsCallable(functions, 'update_athlete_info');
    const payload = {
      ...editForm.value,
      athlete_uid: store.selectedAthlete.athlete_uid || null
    };
    const result = await updateFn(payload);
    const data = result.data as any;
    
    if (data.status === 'success') {
      // Immediately update local store UI
      const idx = store.roster.findIndex(a => a.Name === store.selectedAthlete!.Name);
      if (idx !== -1) {
        store.roster[idx] = { 
          ...store.roster[idx], 
          ...editForm.value, 
          athlete_uid: data.athlete_uid || store.selectedAthlete.athlete_uid 
        };
        store.selectedAthlete = store.roster[idx];
      }
      showEditModal.value = false;
    } else {
      saveError.value = data.message;
    }
  } catch (e: any) {
    saveError.value = e.message || "Failed to update.";
  } finally {
    isSaving.value = false;
  }
};
</script>

<template>
  <div class="h-full flex flex-col max-w-7xl mx-auto">
    <h1 class="text-3xl font-bold text-gray-900 mb-6 flex-shrink-0">Athlete Roster</h1>
    
    <div class="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
      
      <!-- Roster Sidebar -->
      <div class="w-full lg:w-1/3 bg-white border border-gray-200 rounded-xl shadow-sm flex flex-col overflow-hidden h-[600px] lg:h-[calc(100vh-10rem)]">
        <div class="p-4 border-b border-gray-100 bg-gray-50">
          <input v-model="searchQuery" type="text" placeholder="Search athletes by name..." class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-code8-gold focus:border-code8-gold text-sm shadow-sm transition-colors" />
        </div>
        
        <div v-if="store.loading" class="flex-1 flex items-center justify-center text-code8-gold font-semibold animate-pulse">
          Loading roster...
        </div>
        <div v-else-if="store.error" class="flex-1 p-6 text-center text-red-500 font-medium">
          {{ store.error }}
        </div>
        <div v-else class="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
          <button v-for="athlete in filteredRoster" :key="athlete.Name" 
                  @click="handleAthleteClick(athlete)"
                  :class="['w-full text-left px-4 py-3 rounded-lg transition-all border', 
                           store.selectedAthlete?.Name === athlete.Name ? 'bg-code8-gold/10 border-code8-gold shadow-sm' : 'border-transparent hover:bg-gray-50 hover:border-gray-200']">
            <div class="font-bold" :class="store.selectedAthlete?.Name === athlete.Name ? 'text-code8-dark' : 'text-gray-800'">{{ athlete.Name }}</div>
            <div class="text-xs text-gray-500 mt-1 flex justify-between">
              <span class="truncate pr-2">{{ athlete.CurrentSchool || 'No School listed' }}</span>
              <span v-if="athlete.GradYear" class="font-medium whitespace-nowrap">'{{ String(athlete.GradYear).slice(-2) }}</span>
            </div>
          </button>
          <div v-if="filteredRoster.length === 0" class="text-center py-8 text-gray-400 text-sm">
            No athletes found matching "{{ searchQuery }}".
          </div>
        </div>
      </div>
      
      <!-- Athlete Details Panel -->
      <div class="w-full lg:w-2/3 bg-white border border-gray-200 rounded-xl shadow-sm flex flex-col overflow-y-auto custom-scrollbar h-[600px] lg:h-[calc(100vh-10rem)]">
        <template v-if="store.selectedAthlete">
          
          <!-- Banner Header -->
          <div class="bg-gray-900 p-8 relative overflow-hidden flex-shrink-0">
            <div class="absolute top-[-10%] left-[-5%] w-[40%] h-[150%] bg-code8-gold/20 rounded-full blur-[80px] pointer-events-none"></div>
            <div class="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
              <div>
                <h2 class="text-3xl font-black text-white tracking-tight uppercase">{{ store.selectedAthlete.Name }}</h2>
                <p class="text-gray-400 font-medium mt-1 flex items-center gap-2">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                  {{ store.selectedAthlete.Email || 'No email provided' }}
                </p>
              </div>
              <div class="flex gap-3">
                <button v-if="authStore.userRole === 'admin' || authStore.userRole === 'coach'" @click="openEditModal" class="px-4 py-2 bg-white/10 hover:bg-white/20 text-white border border-white/20 rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 backdrop-blur-sm">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
                  Edit Profile
                </button>
              </div>
            </div>
          </div>

          <!-- Content Body -->
          <div class="p-8 space-y-8 flex-1">
            
            <!-- Quick Navigation -->
            <div class="flex flex-col sm:flex-row gap-4 pb-6 border-b border-gray-100">
              <button @click="router.push('/evaluation')" class="flex-1 bg-code8-dark text-white px-6 py-3 rounded-xl font-bold hover:bg-gray-800 transition-all text-center shadow-sm flex items-center justify-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
                Go to Evaluation Hub
              </button>
              <button @click="router.push('/presentation')" class="flex-1 bg-gradient-to-r from-code8-gold to-yellow-500 text-code8-dark px-6 py-3 rounded-xl font-bold hover:shadow-[0_0_20px_rgba(225,193,115,0.3)] transition-all text-center flex items-center justify-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                View Presentation Sheet
              </button>
            </div>

            <!-- Info Grid -->
            <div>
              <h3 class="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">Athlete Information</h3>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <p class="text-xs text-gray-500 font-medium mb-1">Current School</p>
                  <p class="font-bold text-gray-900 truncate" :title="store.selectedAthlete.CurrentSchool || ''">{{ store.selectedAthlete.CurrentSchool || '--' }}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <p class="text-xs text-gray-500 font-medium mb-1">Grad Year</p>
                  <p class="font-bold text-gray-900">{{ store.selectedAthlete.GradYear || '--' }}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <p class="text-xs text-gray-500 font-medium mb-1">Sport(s)</p>
                  <p class="font-bold text-gray-900 truncate" :title="store.selectedAthlete.Sports || ''">{{ store.selectedAthlete.Sports || '--' }}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <p class="text-xs text-gray-500 font-medium mb-1">Positions</p>
                  <p class="font-bold text-gray-900 truncate" :title="store.selectedAthlete.Positions || ''">{{ store.selectedAthlete.Positions || '--' }}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <p class="text-xs text-gray-500 font-medium mb-1">Height (inches)</p>
                  <p class="font-bold text-gray-900">{{ store.selectedAthlete.HeightInches || '--' }}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <p class="text-xs text-gray-500 font-medium mb-1">Birth Date</p>
                  <p class="font-bold text-gray-900">{{ store.selectedAthlete.BirthDate || '--' }}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <p class="text-xs text-gray-500 font-medium mb-1">Gender</p>
                  <p class="font-bold text-gray-900">{{ store.selectedAthlete.Gender || '--' }}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <p class="text-xs text-gray-500 font-medium mb-1">Limb Dominance</p>
                  <p class="font-bold text-gray-900">{{ store.selectedAthlete.LimbDominance || '--' }}</p>
                </div>
              </div>
            </div>

            <!-- Test History Highlights -->
            <div>
              <div class="flex justify-between items-center mb-4">
                <h3 class="text-sm font-bold text-gray-400 uppercase tracking-wider">Testing Highlights</h3>
                <div class="flex items-center gap-4">
                  <span v-if="lastTestedDate !== '--' && lastTestedDate !== 'No tests recorded' && !store.metricsLoading" class="text-xs font-semibold text-gray-500 bg-gray-100 px-3 py-1 rounded-full border border-gray-200">
                    Last Tested: {{ lastTestedDate }}
                  </span>
                  <div v-if="store.metricsLoading" class="text-xs font-semibold text-code8-gold animate-pulse flex items-center">
                    <svg class="animate-spin h-3 w-3 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    Loading metrics...
                  </div>
                </div>
              </div>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="border border-gray-200 p-5 rounded-2xl flex flex-col items-center justify-center text-center">
                  <span class="text-xs font-bold text-gray-400 uppercase mb-2">40yd Dash</span>
                  <span class="text-3xl font-black text-gray-900">{{ bestSprint }}</span>
                </div>
                <div class="border border-gray-200 p-5 rounded-2xl flex flex-col items-center justify-center text-center">
                  <span class="text-xs font-bold text-gray-400 uppercase mb-2">Pro Agility</span>
                  <span class="text-3xl font-black text-gray-900">{{ bestAgility }}</span>
                </div>
                <div class="border border-gray-200 p-5 rounded-2xl flex flex-col items-center justify-center text-center">
                  <span class="text-xs font-bold text-gray-400 uppercase mb-2">Vertical Jump</span>
                  <span class="text-3xl font-black text-gray-900">{{ bestVert }}</span>
                </div>
                <div class="border border-gray-200 p-5 rounded-2xl flex flex-col items-center justify-center text-center">
                  <span class="text-xs font-bold text-gray-400 uppercase mb-2">Broad Jump</span>
                  <span class="text-3xl font-black text-gray-900">{{ bestBroad }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
        
        <div v-else class="flex-1 flex flex-col items-center justify-center text-center p-8">
          <div class="w-24 h-24 bg-gray-50 rounded-full flex items-center justify-center mb-6 border border-gray-100">
            <svg class="w-12 h-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
          </div>
          <h3 class="text-2xl font-bold text-gray-900 mb-2">Select an Athlete</h3>
          <p class="text-gray-500 max-w-sm">Choose an athlete from the roster on the left to view their complete demographic profile and testing highlights.</p>
        </div>
      </div>
    </div>

    <!-- Edit Profile Modal -->
    <div v-if="showEditModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-fade-in-up">
        <div class="p-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/80">
          <h2 class="text-lg font-bold text-gray-900">Edit Athlete Profile</h2>
          <button @click="showEditModal = false" class="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded-md hover:bg-gray-200">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>
        
        <div class="p-6 overflow-y-auto custom-scrollbar flex-1">
          <form id="editAthleteForm" @submit.prevent="saveAthleteInfo" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Full Name *</label>
                <input v-model="editForm.Name" type="text" required class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Email Address</label>
                <input v-model="editForm.Email" type="email" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Birth Date</label>
                <input v-model="editForm.BirthDate" type="date" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Gender</label>
                <select v-model="editForm.Gender" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors">
                  <option value="">-- Select --</option>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Grad Year</label>
                <input v-model="editForm.GradYear" type="number" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">School Grade</label>
                <input v-model="editForm.SchoolGrade" type="number" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Height (inches)</label>
                <input v-model="editForm.HeightInches" type="number" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Limb Dominance</label>
                <select v-model="editForm.LimbDominance" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors">
                  <option value="">-- Select --</option>
                  <option value="Right">Right</option>
                  <option value="Left">Left</option>
                </select>
              </div>
              <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-gray-700 mb-1">Sport(s)</label>
                <input v-model="editForm.Sports" type="text" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" />
              </div>
              <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-gray-700 mb-1">Positions</label>
                <input v-model="editForm.Positions" type="text" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" />
              </div>
              <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-gray-700 mb-1">Current School</label>
                <input v-model="editForm.CurrentSchool" type="text" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" />
              </div>
            </div>
          </form>
          
          <div v-if="saveError" class="mt-4 text-sm font-medium p-3 rounded-lg bg-red-50 text-red-600 border border-red-100">{{ saveError }}</div>
        </div>
        
        <div class="p-5 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
          <button @click="showEditModal = false" type="button" class="px-5 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-200 rounded-lg transition-colors">Cancel</button>
          <button type="submit" form="editAthleteForm" :disabled="isSaving || !editForm.Name" class="px-5 py-2 text-sm font-bold bg-code8-dark text-white rounded-lg hover:bg-gray-800 transition-all flex items-center shadow-sm disabled:opacity-50">
            <span v-if="isSaving" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
            {{ isSaving ? 'Saving...' : 'Save Profile' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.animate-fade-in-up {
  animation: fadeInUp 0.2s ease-out forwards;
}
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent; 
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(209, 213, 219, 0.8); 
  border-radius: 4px;
}
</style>