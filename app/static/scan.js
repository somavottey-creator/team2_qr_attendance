/**
 * scan.js — Attendance scan page logic
 * - Name autocomplete with ID auto-fill registry connections
 * - Relies on native HTML form processing for unbreakable mobile connection routing
 */

const nameInput   = document.getElementById("studentName");
const idInput     = document.getElementById("studentId");
const idHint      = document.getElementById("idHint");
const suggestions = document.getElementById("nameSuggestions");
const submitBtn   = document.getElementById("submitBtn");

let debounceTimer = null;
let selectedFromSuggestion = false;

// ── Name Autocomplete Logic ──────────────────────────────────────────────────

if (nameInput) {
  nameInput.addEventListener("input", () => {
    selectedFromSuggestion = false;
    if (idHint) idHint.textContent = "";
    
    // Unlock field if user decides to rewrite the text contents manually
    if (idInput) idInput.readOnly = false; 
    if (idHint) idHint.className = "";

    const q = nameInput.value.trim();
    clearTimeout(debounceTimer);

    if (q.length < 1) {
      hideSuggestions();
      return;
    }

    // 300ms optimal user typing response debounce delay execution
    debounceTimer = setTimeout(() => fetchSuggestions(q), 300);
  });
}

async function fetchSuggestions(query) {
  try {
    const res = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
    const students = await res.json();

    if (!students || !students.length) { 
      hideSuggestions(); 
      return; 
    }

    if (!suggestions) return;
    suggestions.innerHTML = "";
    
    students.forEach(s => {
      const studentIdentifier = s.student_id || s.id;
      const li = document.createElement("div"); 
      li.style.padding = "0.75rem";
      li.style.cursor = "pointer";
      li.innerHTML = `<span>${s.name}</span> <small style="color:#6c757d;">(${studentIdentifier})</small>`;
      
      li.addEventListener("mousedown", (e) => {
        e.preventDefault(); // Prevents layout blur disruptions from closing selection menus
        selectStudent(s);
      });
      suggestions.appendChild(li);
    });
    suggestions.style.display = "block";
  } catch (err) {
    console.error(err);
    hideSuggestions();
  }
}

function selectStudent(student) {
  selectedFromSuggestion = true;
  const actualId = student.student_id || student.id;

  if (nameInput) nameInput.value = student.name;
  if (idInput) {
    idInput.value = actualId;
    idInput.readOnly = true; // Lock ID to verify validation security consistency
  }
  
  if (idHint) {
    idHint.textContent = "✓ Verified ID auto-filled from registry";
    idHint.style.color = "#28a745";
  }
  
  hideSuggestions();
  if (submitBtn) submitBtn.focus();
}

function hideSuggestions() {
  if (suggestions) {
    suggestions.style.display = "none";
    suggestions.innerHTML = "";
  }
}

// Close suggestion box elements dynamically when clicking safely outside form vectors
document.addEventListener("click", (e) => {
  if (nameInput && !nameInput.contains(e.target) && suggestions && !suggestions.contains(e.target)) {
    hideSuggestions();
  }
});