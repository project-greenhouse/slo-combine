<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useAthleteStore } from '../stores/athleteStore';
import { useAuthStore } from '../stores/authStore';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../firebase/config';

const store = useAthleteStore();
const authStore = useAuthStore();
const saving = ref(false);
const toast = ref('');
const error = ref('');

const editName = ref('');
const editEmail = ref('');
const editBirthDate = ref('');
const editGender = ref('');
const editHeight = ref('');
const editSchool = ref('');
const editSports = ref('');
const editPositions = ref('');

const isStaff = computed(() => authStore.userRole === 'admin' || authStore.userRole === 'coach');

onMounted(async () => {
  await store.fetchRoster();
  // Auto-select athlete's own profile
  if (authStore.athleteName) {
    const me = store.roster.find(a => a.Name === authStore.athleteName);
    if (me) {
      store.selectAthlete(me);
      loadForm();
    }
  } else if (isStaff.value && store.selectedAthlete) {
    loadForm();
  }
});

const loadForm = () => {
  const a = store.selectedAthlete;
  if (!a) return;
  editName.value = a.Name || '';
  editEmail.value = a.Email || '';
  editBirthDate.value = a.BirthDate || '';
  editGender.value = a.Gender || '';
  editHeight.value = a.HeightInches ? String(a.HeightInches) : '';
  editSchool.value = a.CurrentSchool || '';
  editSports.value = a.Sports || '';
  editPositions.value = a.Positions || '';
};

const saveProfile = async () => {
  if (!store.selectedAthlete?.athlete_uid) return;
  saving.value = true; error.value = ''; toast.value = '';
  try {
    const fn = httpsCallable(functions, 'update_athlete_info');
    const res = await fn({
      athlete_uid: store.selectedAthlete.athlete_uid,
      Name: editName.value,
      Email: editEmail.value,
      BirthDate: editBirthDate.value,
      Gender: editGender.value,
      HeightInches: editHeight.value ? Number(editHeight.value) : null,
      CurrentSchool: editSchool.value,
      Sports: editSports.value,
      Positions: editPositions.value,
    });
    const data = res.data as any;
    if (data.status === 'success') {
      const idx = store.roster.findIndex(a => a.athlete_uid === store.selectedAthlete!.athlete_uid);
      if (idx !== -1) {
        store.roster[idx] = { ...store.roster[idx], Name: editName.value, Email: editEmail.value, BirthDate: editBirthDate.value, Gender: editGender.value, HeightInches: editHeight.value ? Number(editHeight.value) : null, CurrentSchool: editSchool.value, Sports: editSports.value, Positions: editPositions.value };
        store.selectedAthlete = store.roster[idx];
      }
      toast.value = 'Profile updated';
      setTimeout(() => { toast.value = ''; }, 3000);
    } else {
      error.value = data.message || 'Failed to save';
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to save';
  } finally {
    saving.value = false;
  }
};
</script>

<template>
  <div class="max-w-lg mx-auto">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">My Profile</h1>

    <div v-if="!store.selectedAthlete" class="text-center py-12 text-gray-400">
      <p>Your profile could not be found. Please contact your coach.</p>
    </div>

    <template v-else>
      <div v-if="toast" class="mb-4 p-3 rounded-lg bg-green-100 text-green-800 text-sm font-medium">{{ toast }}</div>
      <div v-if="error" class="mb-4 p-3 rounded-lg bg-red-100 text-red-800 text-sm font-medium">{{ error }}</div>

      <form @submit.prevent="saveProfile" class="space-y-4">
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Full Name</label>
          <input v-model="editName" type="text" required class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" />
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Email</label>
          <input v-model="editEmail" type="email" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1">Birth Date</label>
            <input v-model="editBirthDate" type="date" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1">Gender</label>
            <select v-model="editGender" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none">
              <option value="">--</option>
              <option value="M">Male</option>
              <option value="F">Female</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1">Height (inches)</label>
            <input v-model="editHeight" type="number" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1">School</label>
            <input v-model="editSchool" type="text" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Sport(s)</label>
          <input v-model="editSports" type="text" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" />
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Position(s)</label>
          <input v-model="editPositions" type="text" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-base focus:border-code8-gold focus:ring-1 focus:ring-code8-gold outline-none" />
        </div>

        <button type="submit" :disabled="saving"
          class="w-full py-4 rounded-lg text-lg font-bold text-white transition-colors disabled:opacity-50"
          :class="saving ? 'bg-gray-400' : 'bg-code8-gold hover:bg-yellow-600 active:bg-yellow-700'">
          {{ saving ? 'Saving...' : 'Save Profile' }}
        </button>
      </form>
    </template>
  </div>
</template>
