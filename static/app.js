(() => {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  let cityId = null, sessionId = null, health = {};

  // ---------- meta
  fetch("/api/health").then((r) => r.json()).then((h) => {
    health = h;
    $("#disc-long").textContent = h.disclaimer_long;
    $("#disc-priv").textContent = h.privacy;
    $("#llmprivacy").textContent = h.llm ? "Η συνομιλία στέλνεται στην υπηρεσία γλωσσικού μοντέλου που έχει ρυθμίσει ο διαχειριστής." : "";
  }).catch(() => {});

  // ---------- city autocomplete
  const city = $("#city"), list = $("#citylist");
  let timer, items = [], active = -1;
  const hideList = () => { list.hidden = true; city.setAttribute("aria-expanded", "false"); active = -1; };
  const choose = (c) => { cityId = c.id; city.value = c.label; hideList(); $("#lat").value = ""; $("#lon").value = ""; $("#tz").value = ""; tzPreview(); };
  city.addEventListener("input", () => {
    cityId = null; $("#tzinfo").textContent = "";
    clearTimeout(timer);
    const q = city.value.trim();
    if (q.length < 2) return hideList();
    timer = setTimeout(async () => {
      try {
        items = await (await fetch("/api/cities?q=" + encodeURIComponent(q))).json();
      } catch { return; }
      list.innerHTML = items.length ? items.map((c, i) => `<li role="option" data-i="${i}">${esc(c.label)}<small>${esc(c.tz)}</small></li>`).join("")
        : `<li class="none">Δεν βρέθηκε. Δοκίμασε λατινικά ή χρησιμοποίησε συντεταγμένες παρακάτω.</li>`;
      list.hidden = false; city.setAttribute("aria-expanded", "true"); active = -1;
    }, 200);
  });
  list.addEventListener("mousedown", (e) => { const li = e.target.closest("li[data-i]"); if (li) choose(items[+li.dataset.i]); });
  city.addEventListener("keydown", (e) => {
    const lis = [...list.querySelectorAll("li[data-i]")];
    if (!lis.length || list.hidden) return;
    if (e.key === "ArrowDown") { active = (active + 1) % lis.length; e.preventDefault(); }
    else if (e.key === "ArrowUp") { active = (active - 1 + lis.length) % lis.length; e.preventDefault(); }
    else if (e.key === "Enter" && active >= 0) { choose(items[active]); e.preventDefault(); return; }
    else if (e.key === "Escape") return hideList();
    else return;
    lis.forEach((l, i) => l.classList.toggle("on", i === active));
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".citybox")) hideList(); });

  // ---------- timezone preview (historical DST)
  async function tzPreview() {
    const el = $("#tzinfo");
    const d = $("#date").value, t = $("#tunk").checked ? "12:00" : ($("#time").value || "12:00");
    if (!cityId || !d) { el.textContent = ""; return; }
    try {
      const r = await fetch(`/api/tz?city_id=${cityId}&date=${d}&time=${t}`);
      if (!r.ok) return;
      const j = await r.json();
      el.innerHTML = `🕰 Ζώνη ώρας: <b>${esc(j.tz)}</b> · τότε: <b>${esc(j.utc_offset)}</b>${j.dst ? " (θερινή ώρα)" : ""} · σε UTC: ${esc(j.utc)}` +
        (j.warnings.length ? ` <span class="warn">⚠ ${j.warnings.includes("gap") ? "Η ώρα αυτή δεν υπήρξε (αλλαγή ώρας)." : j.warnings.includes("ambiguous") ? "Η ώρα αυτή υπήρξε δύο φορές (αλλαγή ώρας)." : "Δες τις σημειώσεις παρακάτω."}</span>` : "");
    } catch {}
  }
  ["#date", "#time", "#tunk"].forEach((s) => $(s).addEventListener("change", tzPreview));
  $("#tunk").addEventListener("change", () => { $("#time").disabled = $("#tunk").checked; });

  $("#sample").addEventListener("click", async () => {
    // fictional sample person (not a real individual)
    $("#name").value = "Ioanna Example"; $("#date").value = "1990-03-14"; $("#time").value = "14:30"; $("#tunk").checked = false; $("#time").disabled = false;
    const cs = await (await fetch("/api/cities?q=Athens")).json();
    const c = cs.find((x) => x.tz === "Europe/Athens") || cs[0]; choose(c);
  });

  // ---------- submit
  $("#form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = $("#err"); err.hidden = true;
    const body = { name: $("#name").value.trim() || null, date: $("#date").value, time: $("#tunk").checked ? null : ($("#time").value || null), time_unknown: $("#tunk").checked || !$("#time").value };
    const lat = $("#lat").value.trim().replace(",", "."), lon = $("#lon").value.trim().replace(",", ".");
    if (cityId) body.city_id = cityId;
    else if (lat && lon) { body.lat = parseFloat(lat); body.lon = parseFloat(lon); body.tz = $("#tz").value.trim() || null; }
    else { err.textContent = "Διάλεξε πόλη από τη λίστα ή δώσε συντεταγμένες."; err.hidden = false; return; }
    const btn = $("#go"); btn.disabled = true; btn.textContent = "Υπολογίζω τον ουρανό…";
    try {
      const r = await fetch("/api/chart", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const j = await r.json();
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "Έλεγξε τα στοιχεία που έδωσες.");
      render(j);
    } catch (ex) { err.textContent = ex.message; err.hidden = false; }
    finally { btn.disabled = false; btn.textContent = "Δείξε τον χάρτη μου"; }
  });

  // ---------- render
  function render(j) {
    sessionId = j.session_id;
    const rd = j.reading;
    $("#results").hidden = false;
    $("#intro").textContent = rd.intro;
    $("#wheel").innerHTML = j.svg;
    $("#big3").innerHTML = rd.big_three.map((t) => `<li>${esc(t)}</li>`).join("");
    const tz = j.timezone;
    $("#meta").innerHTML = `<p><b>Τόπος:</b> ${esc(j.input.place)} · <b>${esc(j.input.date)}</b>${j.input.time ? " " + esc(j.input.time) : " (άγνωστη ώρα)"}<br>
      <b>Ζώνη:</b> ${esc(tz.tz)}, ${esc(tz.utc_offset)}${tz.dst ? " (θερινή ώρα)" : ""} → UTC ${esc(tz.utc)}<br>
      <b>Οίκοι:</b> ${j.time_known ? esc(j.chart.house_system) : "— (χωρίς ώρα)"}</p>`;
    const rows = [];
    const sg = {}; rd.cards.forEach((c) => (sg[c.key] = c));
    rd.cards.forEach((c) => rows.push(`<tr><td><span class="gl">${esc(c.glyph)}</span> ${esc(c.name)}${c.retrograde ? " ℞" : ""}</td><td>${esc(c.position)}</td><td>${c.house ?? "—"}</td></tr>`));
    $("#ptable tbody").innerHTML = rows.join("");
    $("#notes").innerHTML = rd.notes.concat(tz.warnings).map((n) => `<p>ℹ️ ${esc(n)}</p>`).join("");

    $("#cards").innerHTML = rd.cards.map((c, i) => `
      <details class="pcard" ${i < 3 ? "open" : ""}>
        <summary><span class="gl">${esc(c.glyph)}</span> <b>${esc(c.name)}</b> ${esc(c.sign_glyph)} ${esc(c.position)}${c.house ? " · οίκος " + c.house : ""}${c.retrograde ? " · ανάδρομος" : ""}</summary>
        <ol class="steps">
          <li><span class="k">Τι είναι</span>${esc(c.steps.what)}</li>
          <li><span class="k">Πώς δουλεύει στο ζώδιο</span>${esc(c.steps.sign)}</li>
          ${c.steps.house ? `<li><span class="k">Πού στη ζωή</span>${esc(c.steps.house)}</li>` : ""}
          <li class="sum"><span class="k">Με μια φράση</span>${esc(c.steps.summary.replace(/^Με μια φράση:\s*/, ""))}</li>
        </ol>
      </details>`).join("");

    $("#aspects").innerHTML = rd.aspects.length ? rd.aspects.map((a) => `
      <div class="asp"><b>${esc(a.a)} ${esc(a.glyph)} ${esc(a.b)}</b> <span class="muted">${esc(a.type)} · ${a.orb}°${a.applying ? " · " + esc(a.applying) : ""}</span><p>${esc(a.text)}</p></div>`).join("") : "<p>Δεν υπάρχουν στενές όψεις κάτω από 3°.</p>";
    const bars = (obj, raw) => Object.entries(obj).map(([k, v]) => `<div class="bar"><span>${esc(k)}</span><i style="width:${v * 9}%"></i><em>${v}</em></div>`).join("");
    const b = rd.balance;
    $("#balance").innerHTML = `<div class="bars two"><div>${bars(b.elements)}</div><div>${bars(b.modalities)}</div></div>` + b.text.map((t) => `<p>${esc(t)}</p>`).join("");
    $("#moonphase").innerHTML = `<b>${esc(rd.moon_phase.name)}</b> (${rd.moon_phase.illumination}% φωτισμένη)<br>${esc(rd.moon_phase.text)}`;

    const cn = rd.chinese;
    $("#cn-title").textContent = `${cn.animal_cn} · ${cn.title}`;
    const pil = cn.pillars.map((p) => `<div class="pil"><small>${esc(p.label)}</small><big>${esc(p.text)}</big><span>${esc(p.pinyin)}</span><em>${esc(p.stem_element)} · ${esc(p.animal)}</em></div>`);
    if (cn.hour_alt) pil.push(`<div class="pil alt"><small>${esc(cn.hour_alt.label)}</small><big>${esc(cn.hour_alt.text)}</big><span>~${esc(cn.hour_alt.solar_time)}</span><em>${cn.hour_alt.differs ? "διαφέρει από το ρολόι" : "ίδια με το ρολόι"}</em></div>`);
    $("#pillars").innerHTML = pil.join("");
    $("#cn-text").innerHTML = cn.text.map((t) => `<p>${esc(t)}</p>`).join("") +
      `<p>${esc(cn.day_master)}</p>` +
      `<p class="muted">Στοιχεία στους πυλώνες: ${Object.entries(cn.element_count).map(([k, v]) => esc(k) + " " + v).join(" · ")}</p><p>${esc(cn.balance_text)}</p>`;
    $("#cn-notes").innerHTML = cn.notes.map((n) => `<p>ℹ️ ${esc(n)}</p>`).join("");

    const nu = rd.numerology;
    $("#num").innerHTML = `<div class="nums">` + nu.items.map((it) => `
      <div class="numcard${it.master ? " master" : ""}"><div class="n">${it.value}</div><div><b>${esc(it.role)}</b><small>${esc(it.intro)}</small>
      <p>${esc(it.text)}</p><p class="muted">Δύναμη: ${esc(it.strength)}.<br>Πρόκληση: ${esc(it.challenge)}.</p><p><i>${esc(it.tip)}</i></p></div></div>`).join("") + `</div>` +
      `<div class="numcard"><div class="n">${nu.personal_year.value}</div><div><b>Προσωπικό έτος ${nu.personal_year.year}</b><p>${esc(nu.personal_year.text)}</p></div></div>` +
      nu.notes.map((n) => `<p class="note-s">ℹ️ ${esc(n)}</p>`).join("");

    let phase = "", h = "";
    rd.ninety_days.forEach((x) => { if (x.phase !== phase) { if (h) h += "</ul>"; phase = x.phase; h += `<h3>${esc(phase)}</h3><ul class="todo">`; } h += `<li>${esc(x.text)}</li>`; });
    $("#d90").innerHTML = h + "</ul>";

    renderHealth(rd.health);

    // chat
    $("#log").innerHTML = "";
    addMsg("bot", "Γεια σου. Έχω μπροστά μου τον χάρτη σου. Ρώτα με κάτι καθημερινό: μια απόφαση, ένα συναίσθημα, τη μέρα σου. Δίνω μόνο συμβολική καθοδήγηση.");
    $("#chatmode").innerHTML = j.chat.llm ? `🟢 Συνδεδεμένο γλωσσικό μοντέλο (${esc((health.llm || {}).provider || "LLM")})`
      : `🟡 Τοπική λειτουργία: δεν έχει ρυθμιστεί κλειδί LLM· οι απαντήσεις προέρχονται από τη βιβλιοθήκη κειμένων του χάρτη σου (πιο απλές, χωρίς ελεύθερη συζήτηση).`;
    $("#chips").innerHTML = ["Τι να προσέξω σήμερα;", "Πώς πάω στις σχέσεις;", "Τι με βοηθά στη δουλειά;", "Νιώθω άγχος· τι κάνω;", "Ποιο είναι το έτος μου;"].map((t) => `<button type="button" class="chip">${esc(t)}</button>`).join("");
    $("#results").scrollIntoView({ behavior: "smooth" });
  }

  // ---------- health (symbolic)
  function renderHealth(h) {
    $("#h-intro").textContent = h.intro;
    $("#h-top").innerHTML = `<strong>${esc(h.disclaimer_top.split(":")[0])}:</strong>${esc(h.disclaimer_top.slice(h.disclaimer_top.indexOf(":") + 1))}`;
    $("#h-sci").textContent = h.science_note;
    $("#h-checkup").innerHTML = `${esc(h.checkup)} <i>${esc(h.stoic)}</i>`;
    $("#h-bottom").innerHTML = `<strong>${esc(h.disclaimer_bottom.split(":")[0])}:</strong>${esc(h.disclaimer_bottom.slice(h.disclaimer_bottom.indexOf(":") + 1))}`;
    document.querySelectorAll("#h-tabs [role=tab]").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === "body" ? "true" : "false"));
    ["body", "watch", "time", "east"].forEach((k) => { $("#h-" + k).hidden = k !== "body"; });

    // 1. body map
    const bm = h.bodymap, hl = bm.signs.filter((s) => s.marks.length);
    $("#h-body").innerHTML = `
      <p class="sub">Κάθε ζώδιο «κυβερνά» συμβολικά μια περιοχή του σώματος. Οι χρυσές περιοχές είναι τα ζώδια όπου βρίσκονται σημεία του χάρτη σου. Πάτησε μια περιοχή για να δεις περισσότερα.</p>
      <div class="bmwrap">
        <div class="bmsvg" id="h-svg">${bm.svg}</div>
        <div class="bmlist">
          ${hl.length ? `<p class="legend"><span class="dot"></span> Τονισμένα στο χάρτη σου: ${hl.map((s) => `<b>${esc(s.glyph)} ${esc(s.name)}</b> (${esc(s.marks.join(", "))})`).join(" · ")}</p>` : ""}
          ${bm.signs.map((s) => `
            <details class="hsign${s.marks.length ? " on" : ""}" id="hs-${esc(s.key)}" ${s.marks.length ? "open" : ""}>
              <summary><span class="gl">${esc(s.glyph)}</span> <b>${esc(s.name)}</b> <span class="muted">${esc(s.areas.slice(0, 3).join(", "))}</span>${s.marks.length ? ` <span class="tagm">${esc(s.marks.join(" · "))}</span>` : ""}</summary>
              <p><b>Περιοχές:</b> ${esc(s.areas.join(", "))}.</p>
              <p>${esc(s.tendency)}</p>
              <p class="care"><b>Μικρό βήμα:</b> ${esc(s.care)}</p>
            </details>`).join("")}
        </div>
      </div>
      <h3>Ανά πλανήτη</h3>
      <p class="sub">Κάθε πλανήτης αντιστοιχεί συμβολικά σε ένα σύστημα του σώματος. Δες πού βρίσκεται ο καθένας στο χάρτη σου.</p>
      <div class="hplanets">${bm.planets.map((p) => `
        <details class="hplanet"><summary><span class="gl">${esc(p.glyph)}</span> <b>${esc(p.name)}</b> <span class="muted">${esc(p.areas.slice(0, 3).join(", "))}</span></summary>
          <p class="muted">Στο χάρτη σου: ${esc(p.sign_in)}${p.house ? ", " + p.house + "ος οίκος" : ""}.</p>
          <p>${esc(p.theme)}</p><p>${esc(p.tendency)}</p><p class="care"><b>Μικρό βήμα:</b> ${esc(p.tip)}</p>
        </details>`).join("")}</div>`;

    // 2. watch points
    let wh = "", grp = "";
    h.watch.forEach((w) => {
      if (w.group_name !== grp) { grp = w.group_name; wh += `<h3>${esc(grp)}</h3>`; }
      wh += `<article class="wp"><h4>${esc(w.title)}${w.tightness ? ` <span class="chipt">${esc(w.tightness)}</span>` : ""}</h4>
        <p class="muted">Περιοχή: ${esc(w.area)}</p><p>${esc(w.tendency)}</p><p class="care"><b>Μικρό βήμα:</b> ${esc(w.tip)}</p></article>`;
    });
    const notes = h.notes.concat(h.watch_skipped.length ? ["Δεν εμφανίζονται: " + h.watch_skipped.join(" ")] : []);
    $("#h-watch").innerHTML = `<p class="sub">Υπολογίζονται από τον δικό σου χάρτη. Είναι συμβολικές «τάσεις» και «ευαίσθητα σημεία», όχι διαγνώσεις. Κάθε σημείο έχει ένα μικρό, ήπιο βήμα φροντίδας.</p>` + wh +
      notes.map((n) => `<p class="note-s">ℹ️ ${esc(n)}</p>`).join("");

    // 3. timeline
    const tl = h.timeline;
    const rowsHtml = (rows) => `<div class="tablewrap tlwrap"><table class="tl"><thead><tr><th>Ηλικία</th><th>Έτη</th><th>Θέμα</th><th>Περιοχές</th><th>Τι να προσέξεις</th></tr></thead><tbody>` +
      rows.map((r) => `<tr class="k-${esc(r.kind)}"><td data-l="Ηλικία">${esc(r.age_text)}</td><td data-l="Έτη">${esc(r.years)}<small>${esc(r.dates)}</small></td>
        <td data-l="Θέμα"><b>${r.kind === "milestone" ? "★ " : r.kind === "cycle" ? "◦ " : ""}${esc(r.title)}</b>${r.exact ? `<small>ακριβής: ${esc(r.exact)}</small>` : ""}</td>
        <td data-l="Περιοχές">${esc(r.areas)}</td><td data-l="Τι να προσέξεις">${esc(r.watch)}<small>Βοηθά: ${esc(r.tip)}.</small></td></tr>`).join("") + `</tbody></table></div>`;
    const n10 = tl.next10;
    $("#h-time").innerHTML = `
      <p class="sub">${esc(tl.intro)}</p>
      ${tl.notes.map((n) => `<p class="note-s">ℹ️ ${esc(n)}</p>`).join("")}
      <p class="note-s">🌙 ${esc(tl.lunar)}</p>
      <h3>Οι επόμενοι 10 χρόνοι (${esc(n10.from.slice(0, 4))}–${esc(n10.to.slice(0, 4))})</h3>
      <div class="years">${n10.by_year.map((y) => `<div class="yr"><b>${y.year}</b><small>ηλικία ~${y.age}</small>${y.items.length ? `<ul>${y.items.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` : `<span class="muted">ήρεμη χρονιά</span>`}</div>`).join("")}</div>
      ${n10.rows.length ? rowsHtml(n10.rows) : "<p>Δεν υπάρχουν σημαντικές περίοδοι στο διάστημα αυτό.</p>"}
      <h3>Όλη η ζωή ανά ηλικιακή ομάδα</h3>
      <p class="note-s">★ σταθμός ζωής (επιστροφές και βασικοί κύκλοι) · ◦ κύκλος ρυθμού</p>
      ${tl.bands.map((b) => `<details class="band"><summary><b>${esc(b.label)}</b> ετών · ${esc(b.name)} <span class="muted">(${b.rows.length}${b.total > b.rows.length ? " από " + b.total : ""} περίοδοι)</span></summary>${b.rows.length ? rowsHtml(b.rows) : "<p>Καμία σημαντική περίοδος.</p>"}</details>`).join("")}
      <p class="note-s">ℹ️ ${esc(tl.method)}</p>`;

    // 4. Chinese + numbers
    const c = h.chinese, nu = h.numbers;
    $("#h-east").innerHTML = `
      <h3>${esc(c.title)}</h3><p class="sub">${esc(c.intro)}</p>
      <div class="tablewrap"><table class="tl cn"><thead><tr><th>Στοιχείο</th><th>Όργανα (παραδοσιακά)</th><th>Πυλώνες</th><th>Εικόνα</th></tr></thead><tbody>` +
      c.rows.map((r) => `<tr class="st-${esc(r.status)}"><td data-l="Στοιχείο"><b>${esc(r.cn)} ${esc(r.name)}</b></td><td data-l="Όργανα">${esc(r.organs)}<small>${esc(r.emotion)} · ${esc(r.tissue)}</small></td>
        <td data-l="Πυλώνες">${r.count} από ${c.n} <span class="chipt">${esc(r.status_label)}</span></td><td data-l="Εικόνα">${esc(r.text) || "—"}</td></tr>`).join("") + `</tbody></table></div>
      ${c.balanced ? `<p>${esc(c.balanced)}</p>` : ""}
      <p>${esc(c.day_master)}</p>
      ${c.tips.length ? `<ul class="todo">${c.tips.map((t) => `<li><b>${esc(t.element)}:</b> ${esc(t.tip)}</li>`).join("")}</ul>` : ""}
      <p class="note-s">ℹ️ ${esc(c.note)}</p>
      <h3>${esc(nu.title)}</h3><p class="sub">${esc(nu.note)}</p>
      <div class="nums">${nu.items.map((it) => `<div class="numcard"><div class="n">${it.value}</div><div><b>${esc(it.role)}</b><p>${esc(it.theme)}</p><p class="care"><b>Μικρό βήμα:</b> ${esc(it.tip)}</p></div></div>`).join("")}</div>`;
  }
  $("#h-tabs").addEventListener("click", (e) => {
    const b = e.target.closest("[role=tab]"); if (!b) return;
    document.querySelectorAll("#h-tabs [role=tab]").forEach((x) => x.setAttribute("aria-selected", x === b ? "true" : "false"));
    ["body", "watch", "time", "east"].forEach((k) => { $("#h-" + k).hidden = k !== b.dataset.tab; });
  });
  $("#h-body").addEventListener("click", (e) => {
    const g = e.target.closest(".zone"); if (!g) return;
    const d = document.getElementById("hs-" + g.dataset.sign);
    if (d) { d.open = true; d.scrollIntoView({ block: "nearest", behavior: "smooth" }); }
  });

  // ---------- chat
  function addMsg(who, text, cls = "") {
    const d = document.createElement("div");
    d.className = "m " + who + " " + cls;
    d.textContent = text;
    $("#log").appendChild(d); $("#log").scrollTop = $("#log").scrollHeight;
    return d;
  }
  async function send(text) {
    text = text.trim(); if (!text || !sessionId) return;
    addMsg("me", text); $("#msg").value = "";
    const wait = addMsg("bot", "…", "wait"); $("#send").disabled = true;
    try {
      const r = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId, message: text }) });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || "Σφάλμα");
      wait.classList.remove("wait"); wait.textContent = j.reply;
      if (j.mode === "safety") wait.classList.add("safety");
      if (j.note) addMsg("sys", j.note);
    } catch (ex) { wait.classList.remove("wait"); wait.textContent = ex.message; wait.classList.add("safety"); }
    finally { $("#send").disabled = false; }
  }
  $("#chatform").addEventListener("submit", (e) => { e.preventDefault(); send($("#msg").value); });
  $("#msg").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send($("#msg").value); } });
  $("#chips").addEventListener("click", (e) => { const b = e.target.closest(".chip"); if (b) send(b.textContent); });
})();
