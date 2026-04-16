<script setup lang="ts">
import { ref } from 'vue';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../firebase/config';

const showAddAthleteModal = ref(false);

const targetEmail = ref('');
const targetRole = ref('athlete');
const athleteName = ref('');
const statusMsg = ref('');
const isError = ref(false);
const isLoading = ref(false);

// Create User State
const createEmail = ref('');
const createPassword = ref('');
const createRole = ref('coach');
const createStatusMsg = ref('');
const createIsError = ref(false);
const createIsLoading = ref(false);

// Add Single Athlete State
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

// CSV Upload State
const csvFile = ref<File | null>(null);
const csvStatusMsg = ref('');
const csvIsError = ref(false);
const csvIsLoading = ref(false);

// Bookeo Sync State
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
    } else {
      bookeoError.value = data.message || 'Sync failed';
    }
  } catch (err: any) {
    bookeoError.value = err.message || 'Sync failed';
  } finally {
    bookeoSyncing.value = false;
  }
};

const setUserRole = async () => {
  if (!targetEmail.value) return;
  
  isLoading.value = true;
  statusMsg.value = '';
  isError.value = false;
  
  try {
    const setRoleFn = httpsCallable(functions, 'set_user_role');
    const result = await setRoleFn({
      email: targetEmail.value,
      role: targetRole.value,
      athlete_name: targetRole.value === 'athlete' ? athleteName.value : null
    });
    
    const data = result.data as any;
    if (data.status === 'success') {
      statusMsg.value = data.message;
      targetEmail.value = '';
      athleteName.value = '';
    } else {
      isError.value = true;
      statusMsg.value = data.message;
    }
  } catch (err: any) {
    isError.value = true;
    statusMsg.value = err.message || 'An error occurred. Check emulator connection.';
  } finally {
    isLoading.value = false;
  }
};

const handleCreateUser = async () => {
  if (!createEmail.value || !createPassword.value) return;
  
  createIsLoading.value = true;
  createStatusMsg.value = '';
  createIsError.value = false;
  
  try {
    const createFn = httpsCallable(functions, 'admin_create_user');
    const result = await createFn({
      email: createEmail.value,
      password: createPassword.value,
      role: createRole.value,
      athlete_name: null // Athletes no longer created here
    });
    
    const data = result.data as any;
    if (data.status === 'success') {
      createStatusMsg.value = data.message;
      createEmail.value = '';
      createPassword.value = '';
    } else {
      createIsError.value = true;
      createStatusMsg.value = data.message;
    }
  } catch (err: any) {
    createIsError.value = true;
    createStatusMsg.value = err.message || 'An error occurred. Check emulator connection.';
  } finally {
    createIsLoading.value = false;
  }
};

const handleSingleAthlete = async () => {
  if (!singleAthleteName.value || !singleAthleteEmail.value) return;
  
  isSingleLoading.value = true;
  singleStatusMsg.value = '';
  singleIsError.value = false;
  
  const bDate = singleAthleteBirthDate.value;
  const bYear = bDate ? bDate.split('-')[0] : '';
  const bMonth = bDate ? bDate.split('-')[1] : '';
  const escapeCsv = (str: string) => str ? `"${str.replace(/"/g, '""')}"` : '';

  // Reuse the robust CSV uploader endpoint by passing a 1-row CSV!
  const csvData = `Name,Email,BirthDate,BirthYear,BirthMonth,Gender,GradYear,SchoolGrade,HeightInches,LimbDominance,Sports,Positions,CurrentSchool\n` +
    `${escapeCsv(singleAthleteName.value)},${escapeCsv(singleAthleteEmail.value)},${bDate},${bYear},${bMonth},${singleAthleteGender.value},${singleAthleteGradYear.value},${singleAthleteSchoolGrade.value},${singleAthleteHeight.value},${singleAthleteLimbDominance.value},${escapeCsv(singleAthleteSports.value)},${escapeCsv(singleAthletePositions.value)},${escapeCsv(singleAthleteSchool.value)}`;
    
  try {
    const uploadFn = httpsCallable(functions, 'upload_roster_csv');
    const result = await uploadFn({ csv_data: csvData });
    const data = result.data as any;
    
    if (data.status === 'success') {
      singleStatusMsg.value = `Successfully added ${singleAthleteName.value} to the roster.`;
      singleAthleteName.value = '';
      singleAthleteEmail.value = '';
      singleAthleteBirthDate.value = '';
      singleAthleteGender.value = '';
      singleAthleteGradYear.value = '';
      singleAthleteSchoolGrade.value = '';
      singleAthleteHeight.value = '';
      singleAthleteLimbDominance.value = '';
      singleAthleteSports.value = '';
      singleAthletePositions.value = '';
      singleAthleteSchool.value = '';
      
      setTimeout(() => {
        showAddAthleteModal.value = false;
        singleStatusMsg.value = '';
      }, 1500);
    } else {
      singleIsError.value = true;
      singleStatusMsg.value = data.message;
    }
  } catch (err: any) {
    singleIsError.value = true;
    singleStatusMsg.value = err.message || 'Error adding athlete. Check emulator connection.';
  } finally {
    isSingleLoading.value = false;
  }
};

const handleFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    csvFile.value = target.files[0];
  }
};

const handleCsvUpload = async () => {
  if (!csvFile.value) return;
  
  csvIsLoading.value = true;
  csvStatusMsg.value = '';
  csvIsError.value = false;
  
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
        const fileInput = document.getElementById('csvFileInput') as HTMLInputElement;
        if (fileInput) fileInput.value = ''; // Reset UI
      } else {
        csvIsError.value = true;
        csvStatusMsg.value = data.message;
      }
    } catch (err: any) {
      csvIsError.value = true;
      csvStatusMsg.value = err.message || 'Error uploading CSV. Check emulator connection.';
    } finally {
      csvIsLoading.value = false;
    }
  };
  reader.readAsText(csvFile.value);
};
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-3xl font-bold text-gray-900 mb-6">Admin Portal</h1>
    
    <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
      <h2 class="text-xl font-bold text-gray-900 mb-2">Manage User Roles</h2>
      <p class="text-sm text-gray-500 mb-6 pb-4 border-b border-gray-100">
        Assign roles to existing user accounts. If assigning the "athlete" role, you must provide their exact roster name so their data automatically links to their dashboard.
      </p>
      
      <form @submit.prevent="setUserRole" class="space-y-5">
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">User's Email</label>
          <input v-model="targetEmail" type="email" required class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="user@example.com" />
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Account Role</label>
          <select v-model="targetRole" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors">
            <option value="athlete">Athlete</option>
            <option value="coach">Coach</option>
            <option value="admin">Administrator</option>
          </select>
        </div>
        <div v-if="targetRole === 'athlete'">
          <label class="block text-sm font-semibold text-gray-700 mb-1">Exact Roster Name</label>
          <input v-model="athleteName" type="text" required class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="e.g. Colbin Garrison" />
        </div>
        
        <div v-if="statusMsg" :class="['text-sm font-medium p-3 rounded-lg', isError ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-green-50 text-green-700 border border-green-100']">{{ statusMsg }}</div>
        
        <button type="submit" :disabled="isLoading" class="w-full bg-code8-dark text-white font-bold text-base px-4 py-3 rounded-lg hover:bg-gray-800 transition-all flex justify-center items-center">
          <span v-if="isLoading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span><span v-else>Update Permissions</span>
        </button>
      </form>
    </div>

    <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mt-8">
      <h2 class="text-xl font-bold text-gray-900 mb-2">Create New User</h2>
      <p class="text-sm text-gray-500 mb-6 pb-4 border-b border-gray-100">
        Directly create a new Coach, Admin, or Athlete account. This avoids the need to share registration links with staff.
      </p>
      
      <form @submit.prevent="handleCreateUser" class="space-y-5">
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Email</label>
          <input v-model="createEmail" type="email" required class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="newuser@example.com" />
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Temporary Password</label>
          <input v-model="createPassword" type="password" required class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="••••••••" minlength="6" />
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Account Role</label>
          <select v-model="createRole" class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors">
            <option value="coach">Coach</option>
            <option value="admin">Administrator</option>
          </select>
        </div>
        
        <div v-if="createStatusMsg" :class="['text-sm font-medium p-3 rounded-lg', createIsError ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-green-50 text-green-700 border border-green-100']">{{ createStatusMsg }}</div>
        
        <button type="submit" :disabled="createIsLoading" class="w-full bg-code8-dark text-white font-bold text-base px-4 py-3 rounded-lg hover:bg-gray-800 transition-all flex justify-center items-center">
          <span v-if="createIsLoading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span><span v-else>Create Account</span>
        </button>
      </form>
    </div>

    <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mt-8 flex flex-col md:flex-row md:justify-between md:items-center gap-4">
      <div>
        <h2 class="text-xl font-bold text-gray-900 mb-1">Add Single Athlete to Roster</h2>
        <p class="text-sm text-gray-500">
          Add an athlete to the database so they can sign up using their matching email.
        </p>
      </div>
      <button @click="showAddAthleteModal = true" class="whitespace-nowrap bg-code8-dark text-white font-bold text-sm px-5 py-2.5 rounded-lg hover:bg-gray-800 transition-all shadow-sm">
        + Add Athlete
      </button>
    </div>

    <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mt-8">
      <h2 class="text-xl font-bold text-gray-900 mb-2">Upload Roster CSV</h2>
      <div class="flex flex-col md:flex-row md:justify-between md:items-center mb-6 pb-4 border-b border-gray-100 gap-4">
        <p class="text-sm text-gray-500">
          Upload a CSV file containing athlete information to update the system roster. If an athlete's name already exists, their information will be updated safely.
        </p>
        <a href="data:text/csv;charset=utf-8,Name,Email,BirthDate,BirthYear,BirthMonth,Gender,GradYear,SchoolGrade,HeightInches,LimbDominance,Sports,Positions,CurrentSchool%0AJohn%20Doe,john@example.com,2005-08-15,2005,08,M,2024,12,72,Right,Football,QB,SLO%20High" download="athlete_template.csv" class="whitespace-nowrap bg-code8-gold/10 text-code8-gold border border-code8-gold/20 px-4 py-2 rounded-lg font-semibold text-sm hover:bg-code8-gold/20 transition-colors">
          Download Template
        </a>
      </div>
      
      <form @submit.prevent="handleCsvUpload" class="space-y-5">
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">CSV File</label>
          <input id="csvFileInput" type="file" accept=".csv" @change="handleFileChange" required class="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" />
        </div>
        
        <div v-if="csvStatusMsg" :class="['text-sm font-medium p-3 rounded-lg', csvIsError ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-green-50 text-green-700 border border-green-100']">{{ csvStatusMsg }}</div>
        
        <button type="submit" :disabled="csvIsLoading || !csvFile" class="w-full bg-code8-dark text-white font-bold text-base px-4 py-3 rounded-lg hover:bg-gray-800 transition-all flex justify-center items-center disabled:opacity-50 disabled:cursor-not-allowed">
          <span v-if="csvIsLoading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span><span v-else>Upload Roster</span>
        </button>
      </form>
    </div>

    <!-- Bookeo Sync -->
    <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mt-8">
      <h2 class="text-xl font-bold text-gray-900 mb-2">Sync from Bookeo</h2>
      <p class="text-sm text-gray-500 mb-6 pb-4 border-b border-gray-100">
        Pull registered athletes from Bookeo and sync into the roster. Cross-references Hawkin Dynamics and Valor to identify missing athletes.
      </p>

      <button @click="handleBookeoSync" :disabled="bookeoSyncing" class="w-full bg-code8-gold text-white font-bold text-base px-4 py-3 rounded-lg hover:bg-yellow-600 transition-all flex justify-center items-center disabled:opacity-50">
        <span v-if="bookeoSyncing" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
        {{ bookeoSyncing ? 'Syncing...' : 'Sync Bookeo Roster' }}
      </button>

      <div v-if="bookeoError" class="mt-4 text-sm font-medium p-3 rounded-lg bg-red-50 text-red-600 border border-red-100">{{ bookeoError }}</div>

      <div v-if="bookeoResult" class="mt-4 space-y-3">
        <div class="grid grid-cols-2 gap-3">
          <div class="p-3 rounded-lg bg-green-50 border border-green-200 text-center">
            <p class="text-2xl font-bold text-green-700">{{ bookeoResult.created }}</p>
            <p class="text-xs text-green-600">New Athletes</p>
          </div>
          <div class="p-3 rounded-lg bg-blue-50 border border-blue-200 text-center">
            <p class="text-2xl font-bold text-blue-700">{{ bookeoResult.matched }}</p>
            <p class="text-xs text-blue-600">Updated Existing</p>
          </div>
        </div>

        <div v-if="bookeoResult.missing_valor?.length" class="p-4 rounded-lg bg-yellow-50 border border-yellow-200">
          <p class="text-sm font-semibold text-yellow-800 mb-2">Missing in Valor (create manually):</p>
          <ul class="text-sm text-yellow-700 space-y-1">
            <li v-for="name in bookeoResult.missing_valor" :key="name">{{ name }}</li>
          </ul>
        </div>

        <div v-if="bookeoResult.missing_hd?.length" class="p-4 rounded-lg bg-orange-50 border border-orange-200">
          <p class="text-sm font-semibold text-orange-800 mb-2">Missing in Hawkin Dynamics:</p>
          <ul class="text-sm text-orange-700 space-y-1">
            <li v-for="name in bookeoResult.missing_hd" :key="name">{{ name }}</li>
          </ul>
        </div>

        <div v-if="bookeoResult.errors?.length" class="p-4 rounded-lg bg-red-50 border border-red-200">
          <p class="text-sm font-semibold text-red-800 mb-2">Errors:</p>
          <ul class="text-sm text-red-700 space-y-1">
            <li v-for="e in bookeoResult.errors" :key="e">{{ e }}</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Add Athlete Modal -->
    <div v-if="showAddAthleteModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-fade-in-up">
        <div class="p-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/80">
          <h2 class="text-lg font-bold text-gray-900">Add Athlete to Roster</h2>
          <button @click="showAddAthleteModal = false" class="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded-md hover:bg-gray-200">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>
        
        <div class="p-6 overflow-y-auto custom-scrollbar flex-1">
          <form id="addAthleteForm" @submit.prevent="handleSingleAthlete" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Full Name *</label>
                <input v-model="singleAthleteName" type="text" required class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="e.g. Colbin Garrison" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Email Address *</label>
                <input v-model="singleAthleteEmail" type="email" required class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="athlete@example.com" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Birth Date</label>
                <input v-model="singleAthleteBirthDate" type="date" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Gender</label>
                <select v-model="singleAthleteGender" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors">
                  <option value="">-- Select --</option>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Grad Year</label>
                <input v-model="singleAthleteGradYear" type="number" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="2025" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">School Grade</label>
                <input v-model="singleAthleteSchoolGrade" type="number" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="12" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Height (inches)</label>
                <input v-model="singleAthleteHeight" type="number" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="72" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Limb Dominance</label>
                <select v-model="singleAthleteLimbDominance" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors">
                  <option value="">-- Select --</option>
                  <option value="Right">Right</option>
                  <option value="Left">Left</option>
                </select>
              </div>
              <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-gray-700 mb-1">Sport(s)</label>
                <input v-model="singleAthleteSports" type="text" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="Football, Track" />
              </div>
              <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-gray-700 mb-1">Positions</label>
                <input v-model="singleAthletePositions" type="text" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="Football: QB" />
              </div>
              <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-gray-700 mb-1">Current School</label>
                <input v-model="singleAthleteSchool" type="text" class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-code8-gold focus:ring-1 focus:ring-code8-gold transition-colors" placeholder="SLO High School" />
              </div>
            </div>
          </form>
          
          <div v-if="singleStatusMsg" :class="['mt-4 text-sm font-medium p-3 rounded-lg', singleIsError ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-green-50 text-green-700 border border-green-100']">{{ singleStatusMsg }}</div>
        </div>
        
        <div class="p-5 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
          <button @click="showAddAthleteModal = false" type="button" class="px-5 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-200 rounded-lg transition-colors">Cancel</button>
          <button type="submit" form="addAthleteForm" :disabled="isSingleLoading" class="px-5 py-2 text-sm font-bold bg-code8-dark text-white rounded-lg hover:bg-gray-800 transition-all flex items-center shadow-sm">
            <span v-if="isSingleLoading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
            {{ isSingleLoading ? 'Saving...' : 'Save Athlete' }}
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
  background: rgba(243, 244, 246, 0.5); 
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(209, 213, 219, 0.8); 
  border-radius: 4px;
}
</style>