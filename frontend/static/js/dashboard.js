const API = "http://127.0.0.1:8000";
const token = localStorage.getItem("token");
if (!token) window.location.href = "/";
const headers = { "Authorization": `Bearer ${token}` };
let currentAuditResumeId = null;

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
    const totalJobsEl = document.getElementById("total-jobs");
    if (totalJobsEl) totalJobsEl.textContent = jobs.length;
    renderJobList(jobs);

  } catch (err) {
    console.error("loadJobs error:", err);
    document.getElementById("job-list").innerHTML =
      `<div class="empty-state">Error loading jobs. Is server running?</div>`;
  }
}

function renderJobList(jobs) {
  const container = document.getElementById("job-list");
  if (!jobs.length) {
    container.innerHTML = `<div class="empty-state">No job descriptions yet!</div>`;
    return;
  }
  container.innerHTML = jobs.map(j => `
    <div class="resume-card">
      <div class="resume-left">
        <div class="resume-avatar">${(j.title || "?")[0].toUpperCase()}</div>
        <div class="resume-info">
          <div class="resume-name">${j.title}</div>
          <div class="resume-skills">${(j.description || "").slice(0, 90)}...</div>
        </div>
      </div>
      <div class="resume-right">
        <button class="delete-btn" onclick="deleteJob(${j.id})">🗑</button>
      </div>
    </div>`).join("");
}

async function deleteJob(id) {
  if (!confirm("Delete this job?")) return;
  await fetch(`${API}/jobs/${id}`, { method: "DELETE", headers });
  loadJobs();
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
  if (!results) return;
  container.innerHTML = `<div class="results-title">Upload Results:</div>` +
    results.map(r => {
      if (r.error) return `<div class="result-item result-error">❌ ${r.filename} — ${r.error}</div>`;
      if (r.status === "skipped") return `<div class="result-item result-error">⏭️ ${r.filename} — ${r.detail}</div>`;
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

    const tok = localStorage.getItem("token");
    if (!tok) { window.location.href = "/"; return; }

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

    const res = await fetch(url, { headers });

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

// ── Debounced search ──
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
async function viewResume(id) {
  currentAuditResumeId = id;
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
      </div>

      <div style="margin-top:16px">
        <button class="upload-btn match-btn" onclick="runAudit()">🔍 Run Consistency Audit</button>
        <div id="audit-result" style="margin-top:12px"></div>
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
  } else {
    if (avgEl)  avgEl.textContent  = "0%";
    if (highEl) highEl.textContent = "0";
  }
}

// ══════════ TAB SWITCHING ══════════
function showTab(tab) {
  document.getElementById("section-resumes").style.display = tab === "resumes" ? "block" : "none";
  document.getElementById("section-jobs").style.display    = tab === "jobs"    ? "block" : "none";
  document.getElementById("section-matches").style.display = tab === "matches" ? "block" : "none";
  document.getElementById("section-reports").style.display = tab === "reports" ? "block" : "none";
  document.getElementById("tab-resumes")?.classList.toggle("active", tab === "resumes");
  document.getElementById("tab-jobs")?.classList.toggle("active",    tab === "jobs");
  document.getElementById("tab-matches")?.classList.toggle("active", tab === "matches");
  document.getElementById("tab-reports")?.classList.toggle("active", tab === "reports");
  document.getElementById("section-simulator").style.display = tab === "simulator" ? "block" : "none";
  document.getElementById("tab-simulator")?.classList.toggle("active", tab === "simulator");

  if (tab === "matches") populateJobSelect();
  if (tab === "reports") populateReportJobSelect();
  if (tab === "simulator") populateSimJobSelect();
}

// ══════════ DAY 3: MATCHING ══════════
async function populateJobSelect() {
  try {
    const res = await fetch(`${API}/jobs/`, { headers });
    const jobs = await res.json();
    const select = document.getElementById("match-job-select");
    select.innerHTML = `<option value="">Select a job description...</option>` +
      jobs.map(j => `<option value="${j.id}">${j.title}</option>`).join("");
  } catch (err) { console.error(err); }
}

async function runMatch() {
  const jobId = document.getElementById("match-job-select").value;
  const topK  = document.getElementById("match-top-k").value;

  if (!jobId) { alert("Please select a job first!"); return; }
  window.currentMatchJobId = jobId;

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
      <div class="resume-card">
        <div class="resume-left" onclick="viewResume(${c.resume_id})" style="cursor:pointer">
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
          <button class="delete-btn" style="margin-top:8px;white-space:nowrap"
            onclick="runDebate(${c.resume_id}, window.currentMatchJobId)">⚖️ Debate</button>
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
async function runAudit() {
  const container = document.getElementById("audit-result");
  const id = currentAuditResumeId;
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

// ══════════ PHASE 2: AI DEBATE ══════════
async function runDebate(resumeId, jobId) {
  const modal = document.getElementById("debate-modal");
  const body = document.getElementById("debate-body");
  modal.style.display = "flex";
  body.innerHTML = "⏳ Running Advocate vs. Skeptic vs. Judge debate...";

  try {
    const res = await fetch(`${API}/debate/${resumeId}/${jobId}`, {
      method: "POST", headers
    });
    if (!res.ok) {
      const err = await res.json();
      body.innerHTML = `❌ ${err.detail}`;
      return;
    }
    const d = await res.json();

    const recColor = { "shortlist": "#34d399", "reject": "#f87171", "borderline": "#fbbf24" };
    const mockTag = d.is_mock
      ? `<span style="background:#7c3aed;padding:2px 8px;border-radius:6px;font-size:11px">MOCK MODE — real AI debate activates with API credits</span>`
      : "";

    body.innerHTML = `
      <h3 style="margin-bottom:4px">${d.candidate_name} — ${d.job_title} ${mockTag}</h3>

      <div style="border-left:3px solid #34d399;padding:8px 12px;margin:10px 0;background:rgba(0,0,0,0.25);border-radius:6px">
        <b style="color:#34d399">🟢 ADVOCATE</b><br>${d.advocate_case}
      </div>

      <div style="border-left:3px solid #f87171;padding:8px 12px;margin:10px 0;background:rgba(0,0,0,0.25);border-radius:6px">
        <b style="color:#f87171">🔴 SKEPTIC</b><br>${d.skeptic_case}
      </div>

      <div style="border-left:3px solid #60a5fa;padding:8px 12px;margin:10px 0;background:rgba(0,0,0,0.25);border-radius:6px">
        <b style="color:#60a5fa">🟢 ADVOCATE REBUTTAL</b><br>${d.rebuttal}
      </div>

      <div style="border:2px solid ${recColor[d.verdict.recommendation] || '#94a3b8'};padding:12px;margin:14px 0;border-radius:10px">
        <b style="font-size:16px;color:${recColor[d.verdict.recommendation]}">
          ⚖️ VERDICT: ${d.verdict.recommendation.toUpperCase()}</b>
        <span style="float:right">Confidence: ${d.verdict.confidence}%</span>
        <ul style="margin-top:8px;font-size:13px">
          ${d.verdict.key_reasons.map(r => `<li>${r}</li>`).join("")}
        </ul>
      </div>`;
  } catch (err) {
    body.innerHTML = `❌ ${err.message}`;
  }
}

function closeDebateModal() {
  document.getElementById("debate-modal").style.display = "none";
}


// ══════════ PHASE 2: WHAT-IF SIMULATOR ══════════
let simRequirements = [];

async function populateSimJobSelect() {
  try {
    const res = await fetch(`${API}/jobs/`, { headers });
    const jobs = await res.json();
    const sel = document.getElementById("sim-job-select");
    sel.innerHTML = `<option value="">Select a job description...</option>` +
      jobs.map(j => `<option value="${j.id}">${j.title}</option>`).join("");
  } catch (err) { console.error(err); }
}

async function loadRequirements() {
  const jobId = document.getElementById("sim-job-select").value;
  const chips = document.getElementById("sim-chips");
  document.getElementById("sim-result").innerHTML = "";
  if (!jobId) { chips.innerHTML = ""; return; }

  chips.innerHTML = "⏳ Extracting requirements...";
  try {
    const res = await fetch(`${API}/jobs/${jobId}/requirements`, { headers });
    const data = await res.json();
    simRequirements = data.requirements.map(r => ({ text: r, active: true }));
    renderChips();
  } catch (err) {
    chips.innerHTML = `❌ ${err.message}`;
  }
}

function renderChips() {
  const chips = document.getElementById("sim-chips");
  if (!simRequirements.length) {
    chips.innerHTML = `<span style="color:#94a3b8">No requirements detected in this JD</span>`;
    return;
  }
  chips.innerHTML = simRequirements.map((r, i) => `
    <span onclick="toggleChip(${i})"
      style="cursor:pointer;padding:6px 14px;border-radius:20px;font-size:13px;
      border:1px solid ${r.active ? '#4F46E5' : 'rgba(255,255,255,0.2)'};
      background:${r.active ? 'rgba(79,70,229,0.25)' : 'rgba(0,0,0,0.3)'};
      color:${r.active ? '#c7d2fe' : '#64748b'};
      text-decoration:${r.active ? 'none' : 'line-through'}">
      ${r.active ? '✓' : '✕'} ${r.text}</span>`).join("");
}

function toggleChip(i) {
  simRequirements[i].active = !simRequirements[i].active;
  renderChips();
}

async function runSimulation() {
  const jobId = document.getElementById("sim-job-select").value;
  const resultEl = document.getElementById("sim-result");
  if (!jobId) { resultEl.innerHTML = "Select a job first"; return; }

  const removed = simRequirements.filter(r => !r.active).map(r => r.text);
  resultEl.innerHTML = "⏳ Re-ranking candidate pool...";

  try {
    const res = await fetch(`${API}/jobs/${jobId}/simulate`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ removed_requirements: removed, added_requirements: [] })
    });
    const d = await res.json();

    const poolColor = d.deltas.pool_size_change >= 0 ? "#34d399" : "#f87171";
    const sign = d.deltas.pool_size_change >= 0 ? "+" : "";

    let html = `
      <div style="border:2px solid ${poolColor};border-radius:10px;padding:14px;margin-bottom:14px">
        <b style="color:${poolColor};font-size:15px">
          ${removed.length ? `Removing ${removed.length} requirement(s):` : 'No changes —'}
          pool ${sign}${d.deltas.pool_size_change} candidates (${sign}${d.deltas.pool_size_pct}%),
          avg score ${d.deltas.avg_score_change >= 0 ? '+' : ''}${d.deltas.avg_score_change}%
        </b>
      </div>
      <div style="display:flex;gap:16px;flex-wrap:wrap">
        <div style="flex:1;min-width:260px">
          <h4>Original (${d.original.pool_size} qualified, avg ${d.original.avg_score}%)</h4>
          ${d.original.ranked.slice(0,5).map((c,i) =>
            `<div style="padding:4px 0;font-size:13px">${i+1}. ${c.candidate_name} — ${c.match_score}%</div>`).join("")}
        </div>
        <div style="flex:1;min-width:260px">
          <h4>Simulated (${d.simulated.pool_size} qualified, avg ${d.simulated.avg_score}%)</h4>
          ${d.simulated.ranked.slice(0,5).map((c,i) =>
            `<div style="padding:4px 0;font-size:13px">${i+1}. ${c.candidate_name} — ${c.match_score}%</div>`).join("")}
        </div>
      </div>`;

    if (d.top_movers.length) {
      html += `<h4 style="margin-top:14px">Biggest Movers</h4>` +
        d.top_movers.map(m =>
          `<div style="font-size:13px;color:${m.movement>0?'#34d399':'#f87171'}">
            ${m.movement>0?'▲':'▼'} ${m.candidate_name} moved ${Math.abs(m.movement)} places (now ${m.new_score}%)</div>`).join("");
    }

    resultEl.innerHTML = html;
  } catch (err) {
    resultEl.innerHTML = `❌ ${err.message}`;
  }
}