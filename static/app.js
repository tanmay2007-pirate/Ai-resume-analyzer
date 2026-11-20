(() => {
  const $ = (id) => document.getElementById(id);
  const form = $("form"), fileInput = $("resume"), drop = $("drop"), jd = $("jd");
  const submit = $("submit"), submitLabel = $("submit-label"), errorBox = $("error");
  const results = $("results");
  let previousScore = null;

  const SAMPLE_JD = `Software Engineer Intern - Full Stack (AI)

We are looking for an intern to build web features with React and FastAPI, design REST APIs, and work with PostgreSQL and Docker. Experience with Python, JavaScript, TypeScript and Git is required. Familiarity with machine learning, NLP and AWS is a plus. Strong communication, problem solving and teamwork skills are expected. You will write unit tests, use CI/CD pipelines and follow Agile practices.`;

  // ---------- helpers ----------
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  };
  const clear = (n) => { while (n.firstChild) n.removeChild(n.firstChild); };
  const tone = (v) => (v >= 75 ? "good" : v >= 50 ? "warn" : "bad");
  const showError = (msg) => { errorBox.textContent = msg; errorBox.hidden = !msg; };

  function setFile(file) {
    if (!file) return;
    const ok = /\.(pdf|docx)$/i.test(file.name);
    if (!ok) { showError("Please choose a PDF or DOCX file."); return; }
    showError("");
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    drop.classList.add("has-file");
    $("drop-title").textContent = file.name;
    $("drop-hint").textContent = `${(file.size / 1024).toFixed(0)} KB. Click to replace.`;
  }

  // ---------- init ----------
  fetch("/api/health").then((r) => r.json()).then((h) => {
    if (h.ai_feedback_available) $("ai-toggle-wrap").hidden = false;
  }).catch(() => {});

  fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("drag"); }));
  drop.addEventListener("drop", (e) => setFile(e.dataTransfer.files[0]));
  $("sample-jd").addEventListener("click", () => { jd.value = SAMPLE_JD; jd.focus(); });
  $("print").addEventListener("click", () => window.print());
  $("recheck").addEventListener("click", () => {
    $("tool").scrollIntoView({ behavior: "smooth" });
    drop.classList.remove("has-file");
    fileInput.value = "";
    $("drop-title").textContent = "Drop your updated resume here or browse";
    $("drop-hint").textContent = "PDF or DOCX, up to 5 MB";
  });

  // ---------- submit ----------
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError("");
    if (!fileInput.files[0]) return showError("Choose your resume first (PDF or DOCX).");
    if (jd.value.trim().length < 40) return showError("Paste the job description. A few sentences is enough.");

    const body = new FormData();
    body.append("resume", fileInput.files[0]);
    body.append("job_description", jd.value);
    body.append("use_ai", $("use-ai").checked ? "true" : "false");

    submit.disabled = true; submit.classList.add("loading"); submitLabel.textContent = "Analyzing resume";
    try {
      const res = await fetch("/api/analyze", { method: "POST", body });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Something went wrong. Please try again.");
      render(data);
    } catch (err) {
      showError(err.message || "Could not reach the server. Check your connection and try again.");
    } finally {
      submit.disabled = false; submit.classList.remove("loading"); submitLabel.textContent = "Analyze resume";
    }
  });

  // ---------- render ----------
  function chips(container, items, cls, emptyText) {
    clear(container);
    if (!items.length) { container.appendChild(el("p", "empty", emptyText)); return; }
    items.forEach((t) => container.appendChild(el("span", `chip ${cls}`, t)));
  }

  function render(d) {
    results.hidden = false;

    // Score ring
    const ring = $("ring-fg");
    ring.style.stroke = d.score >= 75 ? "#22c58b" : d.score >= 50 ? "#5b5cf6" : "#f0556a";
    requestAnimationFrame(() => { ring.style.strokeDashoffset = 326.7 * (1 - d.score / 100); });
    animateNumber($("score"), d.score);
    $("verdict").textContent = d.verdict;
    $("verdict-sub").textContent =
      `You match ${d.skills.matched.length} of ${d.skills.jd_total} skills in this job post. ` +
      (d.suggestions.length ? `We found ${d.suggestions.length} ${d.suggestions.length === 1 ? "thing" : "things"} to improve.` : "Nothing urgent to fix.");

    const delta = $("delta");
    if (previousScore !== null) {
      const diff = d.score - previousScore;
      delta.hidden = false;
      delta.className = "delta " + (diff > 0 ? "up" : diff < 0 ? "down" : "");
      delta.textContent = diff === 0 ? `Same as your last check (${previousScore}).`
        : `${diff > 0 ? "Up" : "Down"} ${Math.abs(diff)} points from your last check (${previousScore}).`;
    } else { delta.hidden = true; }
    previousScore = d.score;

    // Breakdown
    const bd = $("breakdown"); clear(bd);
    d.breakdown.forEach((b) => {
      const row = el("div", "bar-row");
      const label = el("div", "bar-label", b.label);
      label.appendChild(el("small", "", `${b.weight}% of total score`));
      const bar = el("div", "bar"); const fill = el("i", tone(b.score)); bar.appendChild(fill);
      row.append(label, bar, el("div", "bar-val", `${b.score}%`));
      bd.appendChild(row);
      requestAnimationFrame(() => requestAnimationFrame(() => { fill.style.width = b.score + "%"; }));
    });

    // Skills
    chips($("matched"), d.skills.matched, "hit", "No skills from the job post were found in your resume yet.");
    chips($("missing"), d.skills.missing, "miss", "You cover every skill in the job post.");
    $("matched-count").textContent = d.skills.matched.length;
    $("missing-count").textContent = d.skills.missing.length;

    // Keywords
    const kwAll = [...d.keywords.missing.map((k) => ["miss", k]), ...d.keywords.present.map((k) => ["hit", k])];
    const kw = $("kw"); clear(kw);
    if (!d.keywords.missing.length) { $("kw-card").hidden = true; }
    else { $("kw-card").hidden = false; kwAll.forEach(([c, k]) => kw.appendChild(el("span", `chip ${c}`, k))); }

    // Tips
    const tips = $("tips"); clear(tips);
    if (!d.suggestions.length) tips.appendChild(el("li", "", "Your resume looks solid for this role. Re-check after any edits."));
    d.suggestions.forEach((s) => {
      const li = el("li");
      li.appendChild(el("span", `dot ${s.severity}`));
      const box = el("div"); box.appendChild(el("strong", "", s.title)); box.appendChild(el("span", "", s.detail));
      li.appendChild(box); tips.appendChild(li);
    });

    // AI tips
    $("ai-card").hidden = !(d.ai_feedback || d.ai_error);
    $("ai-text").textContent = d.ai_feedback || d.ai_error || "";

    // Profile
    const p = d.profile, prof = $("profile"); clear(prof);
    const add = (k, v) => {
      prof.appendChild(el("dt", "", k));
      const dd = el("dd");
      if (Array.isArray(v)) {
        if (!v.length) dd.textContent = "Not found";
        else { const ul = el("ul"); v.forEach((x) => ul.appendChild(el("li", "", x))); dd.appendChild(ul); }
      } else dd.textContent = v || "Not found";
      prof.appendChild(dd);
    };
    add("Name", p.name); add("Email", p.email); add("Phone", p.phone);
    add("LinkedIn", p.linkedin); add("GitHub", p.github);
    add("Education", p.education); add("Experience", p.experience);
    add("Certifications", p.certifications);
    add("Sections found", d.sections.found.map((s) => s[0].toUpperCase() + s.slice(1)).join(", "));
    add("Length", `${d.stats.words} words, ${d.stats.pages} page(s), ${d.stats.file_type.toUpperCase()}`);

    results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function animateNumber(node, to) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { node.textContent = to; return; }
    const start = performance.now(), dur = 900;
    const tick = (t) => {
      const k = Math.min(1, (t - start) / dur);
      node.textContent = Math.round(to * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
})();
