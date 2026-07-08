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

    const token = localStorage.getItem("token");
    if (!token) { window.location.href = "/"; return; }

    // ── Build query params from filters ──
    const params = new URLSearchParams();

    const search = document.getElementById("search-input")?.value.trim();
    if (search) params.append("search", search);

    const scoreVal = document.getElementById("score-filter")?.value;
    if (scoreVal === "low") {
      params.append("max_score", "49.9");
    } else if (scoreVal) {
      params.append("min_score", scoreVal);
    }

    const sortVal = document.getElementById("sort-filter")?.value;
    if (sortVal) params.append("sort_by", sortVal);

    const url = `${API}/resumes/${params.toString() ? "?" + params.toString() : ""}`;

    const res = await fetch(url, {
      headers: { "Authorization": `Bearer ${token}` }
    });

    if (res.status === 401) { window.location.href = "/"; return; }

    if (!res.ok) {
      container.innerHTML = `<div class="empty-state">Failed to load resumes (${res.status})</div>`;
      return;
    }

    const resumes = await res.json();
    updateStats(resumes);
    renderResumeList(resumes);

  } catch (err) {
    console.error("loadResumes error:", err);
    document.getElementById("resume-list").innerHTML =
      `<div class="empty-state">❌ ${err.message}</div>`;
  }
}

// ── Debounced search (waits 400ms after typing stops) ──
let searchTimer = null;
function debouncedSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadResumes, 400);
}

// ── Clear all filters ──
function clearFilters() {
  const s = document.getElementById("search-input");
  const sc = document.getElementById("score-filter");
  const so = document.getElementById("sort-filter");
  if (s) s.value = "";
  if (sc) sc.value = "";
  if (so) so.value = "newest";
  loadResumes();
}

// ── View Resume Detail ────────────────────────
currentAuditResumeId = id;

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

// ══════════ DAY 3: MATCHING ══════════

// Update showTab to handle matches
function showTab(tab) {
  document.getElementById("section-resumes").style.display = tab === "resumes" ? "block" : "none";
  document.getElementById("section-jobs").style.display    = tab === "jobs"    ? "block" : "none";
  document.getElementById("section-matches").style.display = tab === "matches" ? "block" : "none";
  document.getElementById("section-reports").style.display = tab === "reports" ? "block" : "none";
  document.getElementById("tab-resumes")?.classList.toggle("active", tab === "resumes");
  document.getElementById("tab-jobs")?.classList.toggle("active",    tab === "jobs");
  document.getElementById("tab-matches")?.classList.toggle("active", tab === "matches");
  document.getElementById("tab-reports")?.classList.toggle("active", tab === "reports");

  if (tab === "matches") populateJobSelect();
  if (tab === "reports") populateReportJobSelect();
}

// Fill the job dropdown
async function populateJobSelect() {
  try {
    const res = await fetch(`${API}/jobs/`, { headers });
    const jobs = await res.json();
    const select = document.getElementById("match-job-select");
    select.innerHTML = `<option value="">Select a job description...</option>` +
      jobs.map(j => `<option value="${j.id}">${j.title}</option>`).join("");
  } catch (err) { console.error(err); }
}

// Run the matching
async function runMatch() {
  const jobId = document.getElementById("match-job-select").value;
  const topK  = document.getElementById("match-top-k").value;

  if (!jobId) { alert("Please select a job first!"); return; }

  document.getElementById("match-progress").style.display = "block";
  document.getElementById("match-results").innerHTML = "";

  try {
    const res = await fetch(`${API}/jobs/${jobId}/match?top_k=${topK}`, {
      method: "POST",
      headers
    });

    document.getElementById("match-progress").style.display = "none";

    if (!res.ok) {
      const err = await res.json();
      document.getElementById("match-results").innerHTML =
        `<div class="empty-state">❌ ${err.detail || "Matching failed"}</div>`;
      return;
    }

    const data = await res.json();
    document.getElementById("match-results-title").textContent =
      `🏆 Top ${data.total_matches} Candidates for: ${data.job_title}`;
    renderMatchResults(data.candidates);

  } catch (err) {
    document.getElementById("match-progress").style.display = "none";
    document.getElementById("match-results").innerHTML =
      `<div class="empty-state">❌ Error: ${err.message}</div>`;
  }
}

function renderMatchResults(candidates) {
  const container = document.getElementById("match-results");

  if (!candidates.length) {
    container.innerHTML = `<div class="empty-state">No matching candidates found.</div>`;
    return;
  }

  container.innerHTML = candidates.map((c, i) => {
    const matchCls = c.match_score >= 60 ? "score-high" : c.match_score >= 40 ? "score-mid" : "score-low";
    const rankEmoji = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `#${i+1}`;

    let skillsArr = Array.isArray(c.skills) ? c.skills : [];
    const skills = skillsArr.slice(0, 5).join(", ");

    return `
      <div class="resume-card" onclick="viewResume(${c.resume_id})">
        <div class="resume-left">
          <div class="rank-badge">${rankEmoji}</div>
          <div class="resume-avatar">${(c.candidate_name || "?")[0].toUpperCase()}</div>
          <div class="resume-info">
            <div class="resume-name">${c.candidate_name || "Unknown"}</div>
            <div class="resume-email">📧 ${c.email || "No email"}</div>
            <div class="resume-skills">🛠 ${skills || "No skills"}</div>
          </div>
        </div>
        <div class="match-scores">
          <div class="score-item">
            <div class="ats-badge ${matchCls}">${c.match_score}%</div>
            <div class="ats-label">Match</div>
          </div>
          <div class="score-item">
            <div class="ats-badge ${c.ats_score >= 70 ? 'score-high' : c.ats_score >= 50 ? 'score-mid' : 'score-low'}">${c.ats_score}%</div>
            <div class="ats-label">ATS</div>
          </div>
        </div>
      </div>`;
  }).join("");
}

// ══════════ DAY 4: REPORTS ══════════

async function populateReportJobSelect() {
  try {
    const res = await fetch(`${API}/jobs/`, { headers });
    const jobs = await res.json();
    const select = document.getElementById("report-job-select");
    select.innerHTML = `<option value="">Select a job description...</option>` +
      jobs.map(j => `<option value="${j.id}">${j.title}</option>`).join("");
  } catch (err) { console.error(err); }
}

async function downloadReport() {
  const jobId = document.getElementById("report-job-select").value;
  const topK  = document.getElementById("report-top-k").value;
  const msgEl = document.getElementById("report-msg");

  if (!jobId) {
    msgEl.textContent = "Please select a job first!";
    msgEl.className = "msg error";
    return;
  }

  msgEl.textContent = "⏳ Generating PDF report...";
  msgEl.className = "msg success";

  try {
    const res = await fetch(`${API}/reports/${jobId}/pdf?top_k=${topK}`, { headers });

    if (!res.ok) {
      const err = await res.json();
      msgEl.textContent = `❌ ${err.detail || "Report generation failed"}`;
      msgEl.className = "msg error";
      return;
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `TalentAI_Report_Job_${jobId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    msgEl.textContent = "✅ Report downloaded successfully!";
    msgEl.className = "msg success";

  } catch (err) {
    msgEl.textContent = `❌ Error: ${err.message}`;
    msgEl.className = "msg error";
  }
}

// ══════════ CONTACT DIRECTORY EXPORT ══════════

async function downloadContactsPDF() {
  const msgEl = document.getElementById("contacts-msg");
  msgEl.textContent = "⏳ Generating contact directory...";
  msgEl.className = "msg success";

  try {
    const res = await fetch(`${API}/reports/contacts/pdf`, { headers });

    if (!res.ok) {
      const err = await res.json();
      msgEl.textContent = `❌ ${err.detail || "Export failed"}`;
      msgEl.className = "msg error";
      return;
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "TalentAI_Contact_Directory.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    msgEl.textContent = "✅ Contact directory downloaded!";
    msgEl.className = "msg success";

  } catch (err) {
    msgEl.textContent = `❌ Error: ${err.message}`;
    msgEl.className = "msg error";
  }
}

// ══════════ PHASE 2: CONSISTENCY AUDIT ══════════

let currentAuditResumeId = null;  // set this in your openResumeModal function

async function runAudit() {
  const container = document.getElementById("audit-result");
  const id = currentAuditResumeId || window.currentResumeId;
  if (!id) { container.innerHTML = "No resume selected"; return; }

  container.innerHTML = "⏳ Auditing...";

  try {
    const res = await fetch(`${API}/resumes/${id}/audit`, {
      method: "POST", headers
    });
    if (!res.ok) {
      const err = await res.json();
      container.innerHTML = `❌ ${err.detail}`;
      return;
    }
    const data = await res.json();

    const sevColor = { "info": "#60a5fa", "warning": "#fbbf24", "red-flag": "#f87171" };
    const scoreColor = data.consistency_score >= 80 ? "#34d399" :
                       data.consistency_score >= 50 ? "#fbbf24" : "#f87171";

    let html = `<div style="font-size:18px;font-weight:bold;color:${scoreColor}">
                  Consistency Score: ${data.consistency_score}/100</div>
                <div style="font-size:12px;color:#94a3b8;margin-bottom:10px">
                  ${data.date_ranges_found} date ranges analyzed · ${data.total_flags} flags
                  ${data.llm_audit_included ? "· AI audit included" : "· rules-only (AI audit pending)"}</div>`;

    if (data.flags.length === 0) {
      html += `<div style="color:#34d399">✅ No consistency issues detected</div>`;
    } else {
      data.flags.forEach(f => {
        html += `<div style="border-left:3px solid ${sevColor[f.severity] || '#94a3b8'};
                   padding:6px 10px;margin:6px 0;background:rgba(0,0,0,0.25);
                   border-radius:6px;font-size:13px">
                   <b style="color:${sevColor[f.severity]}">${f.severity.toUpperCase()}</b>
                   — ${f.detail}</div>`;
      });
    }
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `❌ ${err.message}`;
  }
}