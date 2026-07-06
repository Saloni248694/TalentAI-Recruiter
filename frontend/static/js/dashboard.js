const API = "http://127.0.0.1:8000";
const token = localStorage.getItem("token");
if (!token) window.location.href = "/";
const headers = { "Authorization": `Bearer ${token}` };

// ── Page Load ─────────────────────────────────
window.addEventListener("load", () => {
  loadResumes();
  loadJobs();
  setupDropZone();
});

function logout() {
  localStorage.removeItem("token");
  window.location.href = "/";
}

// ── Tab Switching ─────────────────────────────
function showTab(tab) {
  document.getElementById("section-resumes").style.display = tab === "resumes" ? "block" : "none";
  document.getElementById("section-jobs").style.display   = tab === "jobs"    ? "block" : "none";
  document.getElementById("tab-resumes").classList.toggle("active", tab === "resumes");
  document.getElementById("tab-jobs").classList.toggle("active",    tab === "jobs");
}

// ── JD Tab (paste vs upload) ──────────────────
function switchJDTab(tab) {
  document.getElementById("jd-paste-area").style.display  = tab === "paste"  ? "block" : "none";
  document.getElementById("jd-upload-area").style.display = tab === "upload" ? "block" : "none";
  document.querySelectorAll(".jd-tab").forEach((b, i) => {
    b.classList.toggle("active", (i === 0 && tab === "paste") || (i === 1 && tab === "upload"));
  });
}

// ── Handle JD PDF ─────────────────────────────
let jdPdfText = "";
function handleJDFile(input) {
  const file = input.files[0];
  if (!file) return;
  document.getElementById("jd-file-name").textContent = `📄 ${file.name} selected`;
  jdPdfText = `[PDF: ${file.name}]`;
}

// ── Save Job ──────────────────────────────────
async function saveJob() {
  const title       = document.getElementById("jd-title").value.trim();
  const pasteText   = document.getElementById("jd-text").value.trim();
  const description = pasteText || jdPdfText;

  if (!title)       { showJDMsg("Please enter a job title", "error"); return; }
  if (!description) { showJDMsg("Please paste a job description", "error"); return; }

  const res = await fetch(`${API}/jobs/`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ title, description })
  });

  const data = await res.json();
  if (res.ok) {
    showJDMsg("✅ Job saved successfully!", "success");
    document.getElementById("jd-title").value = "";
    document.getElementById("jd-text").value  = "";
    jdPdfText = "";
    loadJobs();
  } else {
    showJDMsg(data.detail || "Failed to save", "error");
  }
}

function showJDMsg(text, type) {
  const el = document.getElementById("jd-msg");
  el.textContent = text;
  el.className = `msg ${type}`;
  setTimeout(() => { el.textContent = ""; el.className = "msg"; }, 3000);
}

// ── Load Jobs ─────────────────────────────────
async function loadJobs() {
  try {
    const container = document.getElementById("job-list");
    container.innerHTML = `<div class="empty-state">Loading...</div>`;

    const res  = await fetch(`${API}/jobs/`, { headers });

    if (!res.ok) {
      container.innerHTML = `<div class="empty-state">Failed to load jobs.</div>`;
      return;
    }

    const jobs = await res.json();
    document.getElementById("total-jobs").textContent = jobs.length;
    renderJobList(jobs);

  } catch (err) {
    console.error("loadJobs error:", err);
    document.getElementById("job-list").innerHTML =
      `<div class="empty-state">Error loading jobs. Is server running?</div>`;
  }
}

// ── Drop Zone ─────────────────────────────────
let selectedFiles = [];

function setupDropZone() {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  fileInput.addEventListener("change", () => handleFiles(fileInput.files));
  dropZone.addEventListener("dragover",  (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
  dropZone.addEventListener("dragleave", ()  => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    handleFiles(e.dataTransfer.files);
  });
}

function handleFiles(files) {
  selectedFiles = Array.from(files).filter(f => f.name.endsWith(".pdf"));
  if (!selectedFiles.length) { alert("PDF files only!"); return; }
  document.getElementById("selected-files").innerHTML = `
    <div class="selected-title">📎 ${selectedFiles.length} file(s) selected:</div>
    ${selectedFiles.map(f => `
      <div class="selected-item">📄 ${f.name}
        <span class="file-size">(${(f.size/1024).toFixed(1)} KB)</span>
      </div>`).join("")}`;
  document.getElementById("upload-btn").style.display = "block";
}

// ── Upload Resumes ────────────────────────────
async function uploadResumes() {
  if (!selectedFiles.length) return;
  const formData = new FormData();
  selectedFiles.forEach(f => formData.append("files", f));

  document.getElementById("upload-btn").style.display = "none";
  document.getElementById("progress-wrap").style.display = "block";
  document.getElementById("upload-results").innerHTML = "";

  const bar   = document.getElementById("progress-bar");
  const label = document.getElementById("progress-label");

  const steps = [
    [500,  "📤 Uploading files...", "20%"],
    [1500, "🔍 Extracting text...", "45%"],
    [3000, "🤖 Parsing resumes...", "70%"],
    [4500, "📊 Running ATS analysis...", "88%"],
  ];
  steps.forEach(([delay, text, width]) => {
    setTimeout(() => { label.textContent = text; bar.style.width = width; }, delay);
  });

  try {
    const res  = await fetch(`${API}/resumes/upload`, { method: "POST", headers, body: formData });
    bar.style.width = "100%";
    label.textContent = "✅ Done!";
    const data = await res.json();

    setTimeout(() => {
      document.getElementById("progress-wrap").style.display = "none";
      bar.style.width = "0%";
      showUploadResults(data.results);
      loadResumes();
      selectedFiles = [];
      document.getElementById("selected-files").innerHTML = "";
    }, 800);

  } catch (err) {
    label.textContent = "❌ Upload failed.";
    console.error(err);
  }
}

function showUploadResults(results) {
  const container = document.getElementById("upload-results");
  container.innerHTML = `<div class="results-title">Upload Results:</div>` +
    results.map(r => {
      if (r.error) return `<div class="result-item result-error">❌ ${r.filename} — ${r.error}</div>`;
      const cls = r.ats_score >= 70 ? "score-high" : r.ats_score >= 50 ? "score-mid" : "score-low";
      return `<div class="result-item ${cls}">
        ✅ <strong>${r.candidate_name || r.filename}</strong>
        — ATS: <strong>${r.ats_score}%</strong>
      </div>`;
    }).join("");
}

// ── Load Resumes ──────────────────────────────
async function loadResumes() {
  try {
    const container = document.getElementById("resume-list");
    container.innerHTML = `<div class="empty-state">Loading...</div>`;

    const res = await fetch(`${API}/resumes/`, { headers });

    if (!res.ok) {
      container.innerHTML = `<div class="empty-state">Failed to load.</div>`;
      return;
    }

    const resumes = await res.json();
    updateStats(resumes);
    renderResumeList(resumes);

  } catch (err) {
    console.error("loadResumes error:", err);
    document.getElementById("resume-list").innerHTML =
      `<div class="empty-state">Error. Is server running?</div>`;
  }
}

// ── View Resume Detail ────────────────────────
async function viewResume(id) {
  try {
    const res = await fetch(`${API}/resumes/${id}`, { headers });
    const r   = await res.json();
    const ats = r.ats_feedback || {};
    const cls = r.ats_score >= 70 ? "score-high" : r.ats_score >= 50 ? "score-mid" : "score-low";

    document.getElementById("modal-content").innerHTML = `
      <div class="modal-header">
        <div class="modal-avatar">${(r.candidate_name || "?")[0].toUpperCase()}</div>
        <div>
          <h2>${r.candidate_name || "Unknown"}</h2>
          <p>📧 ${r.email || "—"} &nbsp;|&nbsp; 📞 ${r.phone || "—"}</p>
        </div>
        <div class="ats-badge ${cls} big">${r.ats_score || 0}%</div>
      </div>

      ${r.summary ? `<div class="modal-section"><h3>📝 Summary</h3><p>${r.summary}</p></div>` : ""}

      <div class="modal-section">
        <h3>🛠 Skills</h3>
        <div class="skills-wrap">
          ${(r.skills || []).map(s => `<span class="skill-tag">${s}</span>`).join("") || "None"}
        </div>
      </div>

      <div class="modal-section">
        <h3>💼 Experience</h3>
        ${(r.experience || []).map(e => `
          <div class="exp-item">
            <strong>${e.role || "Role"}</strong> at ${e.company || "Company"}
            <span class="exp-duration">${e.duration || ""}</span>
            <p>${e.description || ""}</p>
          </div>`).join("") || "<p>No experience listed</p>"}
      </div>

      <div class="modal-section">
        <h3>🎓 Education</h3>
        ${(r.education || []).map(e => `
          <div class="exp-item">
            <strong>${e.degree || "Degree"}</strong> — ${e.institution || "Institution"}
            <span class="exp-duration">${e.year || ""}</span>
          </div>`).join("") || "<p>No education listed</p>"}
      </div>

      <div class="modal-section ats-section">
        <h3>📊 ATS Analysis</h3>
        <div class="ats-grid">
          <div class="ats-item">
            <div class="ats-num">${ats.keyword_score || 0}%</div><div>Keywords</div>
          </div>
          <div class="ats-item">
            <div class="ats-num">${ats.format_score || 0}%</div><div>Format</div>
          </div>
          <div class="ats-item">
            <div class="ats-num">${ats.experience_score || 0}%</div><div>Experience</div>
          </div>
        </div>
        <div class="ats-lists">
          <div>
            <h4>✅ Strengths</h4>
            <ul>${(ats.strengths || []).map(s => `<li>${s}</li>`).join("")}</ul>
          </div>
          <div>
            <h4>⚠️ Improvements</h4>
            <ul>${(ats.improvements || []).map(i => `<li>${i}</li>`).join("")}</ul>
          </div>
        </div>
        ${ats.optimized_summary ? `
          <div class="optimized-summary">
            <h4>🤖 AI Summary</h4>
            <p>${ats.optimized_summary}</p>
          </div>` : ""}
      </div>`;

    document.getElementById("modal-overlay").style.display = "flex";
  } catch (err) { console.error(err); }
}

function closeModal() {
  document.getElementById("modal-overlay").style.display = "none";
}

async function deleteResume(id) {
  if (!confirm("Delete this resume?")) return;
  await fetch(`${API}/resumes/${id}`, { method: "DELETE", headers });
  loadResumes();
}

function renderResumeList(resumes) {
  const container = document.getElementById("resume-list");
  if (!resumes.length) {
    container.innerHTML = `<div class="empty-state">No resumes uploaded yet!</div>`;
    return;
  }

  container.innerHTML = resumes.map(r => {
    const cls = r.ats_score >= 70 ? "score-high" : r.ats_score >= 50 ? "score-mid" : "score-low";

    // Safely handle skills — could be array OR string
    let skillsArr = [];
    if (Array.isArray(r.skills)) {
      skillsArr = r.skills;
    } else if (typeof r.skills === "string" && r.skills.length) {
      try { skillsArr = JSON.parse(r.skills); } catch { skillsArr = []; }
    }
    const skills = skillsArr.slice(0, 4).join(", ");

    const name = r.candidate_name || "Unknown";

    return `
      <div class="resume-card" onclick="viewResume(${r.id})">
        <div class="resume-left">
          <div class="resume-avatar">${name[0].toUpperCase()}</div>
          <div class="resume-info">
            <div class="resume-name">${name}</div>
            <div class="resume-email">📧 ${r.email || "No email"}</div>
            <div class="resume-skills">🛠 ${skills || "No skills listed"}</div>
          </div>
        </div>
        <div class="resume-right">
          <div class="ats-badge ${cls}">${r.ats_score || 0}%</div>
          <div class="ats-label">ATS Score</div>
          <button class="delete-btn"
            onclick="event.stopPropagation(); deleteResume(${r.id})">🗑</button>
        </div>
      </div>`;
  }).join("");
}

function updateStats(resumes) {
  const totalEl = document.getElementById("total-resumes");
  const avgEl   = document.getElementById("avg-ats");
  const highEl  = document.getElementById("high-scorers");

  if (totalEl) totalEl.textContent = resumes.length;

  if (resumes.length > 0) {
    const avg  = resumes.reduce((s, r) => s + (Number(r.ats_score) || 0), 0) / resumes.length;
    const high = resumes.filter(r => Number(r.ats_score) >= 70).length;
    if (avgEl)  avgEl.textContent  = avg.toFixed(1) + "%";
    if (highEl) highEl.textContent = high;
  }
}