(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const set = (id, value) => { const e = $(id); if (e) e.textContent = value == null ? "â€”" : String(value); };
  const num = value => Number(value || 0).toLocaleString();
  const pct = value => value == null ? "â€”" : (Number(value) * 100).toFixed(1) + "%";

  async function get(url) {
    const r = await fetch(url, { cache: "no-store", credentials: "same-origin" });
    if (!r.ok) throw new Error(url + " HTTP " + r.status);
    return r.json();
  }
  async function post(url, body) {
    const r = await fetch(url, {
      method: "POST", cache: "no-store", credentials: "same-origin",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    });
    if (!r.ok) throw new Error(url + " HTTP " + r.status);
    return r.json();
  }

  function bars(id, values) {
    const e = $(id);
    if (!e) return;
    e.innerHTML = Object.entries(values || {}).map(([key, value]) => {
      const n = Number(value) || 0;
      return '<div class="k-row"><span>Top ' + key +
        '</span><div class="k-track"><div class="k-fill" style="width:' +
        Math.max(2, Math.min(100, n * 100)) + '%"></div></div><strong class="k-value">' +
        (n * 100).toFixed(1) + '%</strong></div>';
    }).join("");
  }

  function renderMetrics(model) {
    const e = $("digit-metrics");
    const names = ["jodi_first", "jodi_second", "close_first", "close_second", "close_third"];
    if (!e) return;
    e.innerHTML = names.map(name => {
      const m = (model.metrics || {})[name] || {};
      return "<tr><td>" + (name.startsWith("jodi") ? "Jodi" : "Close") +
        "</td><td>" + name + "</td><td>" + pct(m.top_1_accuracy) +
        "</td><td>" + pct(m.top_5_accuracy) + "</td><td>" + pct(m.top_7_accuracy) +
        "</td><td>" + pct(m.top_10_accuracy) + "</td><td>" + num(m.train_rows) +
        "</td><td>" + num(m.validation_rows) + "</td></tr>";
    }).join("");
  }

  function renderRecords(data) {
    const rows = data.records || [];
    const e = $("records-table");
    if (e) {
      e.innerHTML = rows.map((r, i) =>
        "<tr><td>" + (r.id || i + 1) + "</td><td>" + (r.date || "â€”") +
        "</td><td>" + (r.market || "â€”") + "</td><td><b>" + (r.open || "â€”") +
        "</b></td><td>" + (r.jodi || "â€”") + "</td><td>" + (r.close || "â€”") +
        "</td><td>" + (r.columns || []).join(" ") + "</td><td>STORED</td></tr>"
      ).join("");
    }
    set("database-count", num(rows.length) + " / " + num(data.count || rows.length) + " records");
    return rows;
  }

  function renderFamilies(rows, prediction) {
    const openDigits = Array(10).fill(0);
    const closeDigits = Array(10).fill(0);
    const jodi = {}, panels = {};
    rows.forEach(row => {
      String(row.open || "").padStart(3, "0").split("").forEach(d => { if (/\d/.test(d)) openDigits[+d]++; });
      String(row.close || "").padStart(3, "0").split("").forEach(d => { if (/\d/.test(d)) closeDigits[+d]++; });
      if (row.jodi) jodi[String(row.jodi).padStart(2, "0")] = (jodi[String(row.jodi).padStart(2, "0")] || 0) + 1;
      if (row.open) panels[String(row.open).padStart(3, "0")] = (panels[String(row.open).padStart(3, "0")] || 0) + 1;
    });

    const esc = value => String(value ?? "").replace(/[&<>"]/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]));
    const chip = (label, meta) =>
      '<span class="family-chip"><b>' + esc(label) + '</b>' +
      (meta ? '<small>' + esc(meta) + '</small>' : '') + '</span>';

    const tier = (name, values, total, formatter) => {
      const items = values.map(x => {
        const meta = formatter ? formatter(x, total) : "";
        return chip(x[0], meta);
      }).join("");
      return '<div class="family-tier readable-tier"><div class="family-tier-head"><b>' +
        name + '</b><span>' + values.length + ' items</span></div>' +
        '<div class="family-members">' + (items || '<span class="family-empty">No data</span>') + '</div></div>';
    };

    const setCard = (id, tiers) => {
      const e = $(id);
      if (e) e.innerHTML = tiers.join("");
    };

    const digitTiers = (id, counts, predicted) => {
      const e = $(id); if (!e) return;
      const order = counts.map((v, i) => [String(i), v]).sort((a,b) => b[1] - a[1]);
      const total = counts.reduce((a,b) => a + b, 0) || 1;
      const groups = [order.slice(0,1), order.slice(1,3), order.slice(3,5), order.slice(5,7), order.slice(7,10)];
      const tiers = groups.map((g,i) => tier(["TOP 1","TOP 30%","TOP 50%","TOP 70%","TOP 100%"][i], g, total,
        x => predicted ? (Number(x[1]) * 100).toFixed(2) + "%" : x[1] + " obs · " + (x[1] / total * 100).toFixed(1) + "%"));
      setCard(id, tiers);
    };

    const mapTiers = (id, map, probabilityMode) => {
      const e = $(id); if (!e) return;
      const order = Object.entries(map).sort((a,b) => Number(b[1]) - Number(a[1]));
      const total = order.reduce((a,x) => a + Number(x[1]), 0) || 1;
      const sizes = [1,2,2,2,order.length];
      let offset = 0;
      const names = ["TOP 1","TOP 30%","TOP 50%","TOP 70%","TOP 100%"];
      const tiers = names.map((name,i) => {
        const group = i < 4 ? order.slice(offset, offset + sizes[i]) : order.slice(offset);
        offset += group.length;
        return tier(name, group, total, x => probabilityMode
          ? (Number(x[1]) * 100).toFixed(2) + "%"
          : x[1] + " obs · " + (Number(x[1]) / total * 100).toFixed(1) + "%");
      });
      setCard(id, tiers);
    };

    digitTiers("open-digit-family", openDigits, false);
    mapTiers("open-jodi-family", jodi, false);
    mapTiers("open-panel-family", panels, false);

    let closeDigitValues = closeDigits;
    if (Array.isArray(prediction?.close_digit_candidates?.first) && prediction.close_digit_candidates.first.length) {
      closeDigitValues = Array(10).fill(0);
      prediction.close_digit_candidates.first.forEach(x => {
        const d = Number(x.digit);
        if (Number.isInteger(d) && d >= 0 && d <= 9) closeDigitValues[d] = Number(x.probability || 0);
      });
    }
    digitTiers("close-digit-family", closeDigitValues, Boolean(prediction?.close_digit_candidates?.first?.length));

    mapTiers("close-jodi-family", jodi, false);
    const closePanels = {};
    (Array.isArray(prediction?.panel_candidates) ? prediction.panel_candidates : []).forEach(x => {
      const key = x.panel || x.candidate;
      if (key != null) closePanels[String(key).padStart(3, "0")] = Number(x.probability || 0);
    });
    mapTiers("close-panel-family", Object.keys(closePanels).length ? closePanels : panels, Object.keys(closePanels).length > 0);

    const openBest = openDigits.indexOf(Math.max(...openDigits));
    const jBest = Object.entries(jodi).sort((a,b) => b[1]-a[1])[0];
    const pBest = Object.entries(panels).sort((a,b) => b[1]-a[1])[0];
    set("open-digit-best", openBest);
    set("open-jodi-best-family", jBest ? jBest[0] : "—");
    set("open-panel-best-family", pBest ? pBest[0] : "—");
    set("close-jodi-best-family", jBest ? jBest[0] : "—");
    set("close-panel-best-family", pBest ? pBest[0] : "—");
  }

  function copyFamilyContent(targetId, button) {
    const source = $(targetId);
    if (!source) return;
    const lines = [];
    source.querySelectorAll(".family-tier").forEach(tierEl => {
      const title = tierEl.querySelector(".family-tier-head b")?.textContent?.trim() || "";
      const chips = [...tierEl.querySelectorAll(".family-chip")].map(ch => {
        const label = ch.querySelector("b")?.textContent?.trim() || ch.textContent.trim();
        const meta = ch.querySelector("small")?.textContent?.trim() || "";
        return meta ? label + " — " + meta : label;
      });
      lines.push(title + " (" + chips.length + " items)");
      lines.push(...chips.map(x => "  " + x));
      lines.push("");
    });
    navigator.clipboard.writeText(lines.join("\n").trim()).then(() => {
      if (button) {
        const old = button.textContent;
        button.textContent = "Copied";
        setTimeout(() => button.textContent = old, 1400);
      }
    }).catch(() => {
      const ta = document.createElement("textarea");
      ta.value = lines.join("\n").trim();
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      if (button) button.textContent = "Copied";
    });
  }

  function bindFamilyCopyButtons() {
    document.querySelectorAll(".copy-family-btn").forEach(button => {
      button.addEventListener("click", () => copyFamilyContent(button.dataset.copyTarget, button));
    });
  }

  function renderWeightLadders(rows) {
    const esc = value => String(value ?? "").replace(/[&<>"]/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]));
    const build = (map, formatValue, totalObservations) => {
      const entries = Object.entries(map).map(([value, count]) => ({ value, count: Number(count) || 0 }))
        .sort((a,b) => b.count - a.count || String(a.value).localeCompare(String(b.value)));
      const total = entries.reduce((sum, x) => sum + x.count, 0) || totalObservations || 1;
      let cumulative = 0;
      return entries.map((x, index) => {
        const weight = (x.count / total) * 100;
        cumulative += weight;
        const percentile = Math.max(1, Math.ceil(((index + 1) / entries.length) * 100));
        return {
          rank: index + 1,
          percentile,
          value: formatValue(x.value),
          count: x.count,
          weight,
          cumulative,
          maxCount: entries[0]?.count || 1
        };
      });
    };

    const digitMap = {};
    const jodiMap = {};
    const panelMap = {};
    rows.forEach(row => {
      String(row.open || "").padStart(3, "0").split("").forEach(d => {
        if (/\d/.test(d)) digitMap[d] = (digitMap[d] || 0) + 1;
      });
      if (row.jodi != null && row.jodi !== "") {
        const j = String(row.jodi).padStart(2, "0");
        jodiMap[j] = (jodiMap[j] || 0) + 1;
      }
      if (row.open != null && row.open !== "") {
        const p = String(row.open).padStart(3, "0");
        panelMap[p] = (panelMap[p] || 0) + 1;
      }
    });

    const formatDigit = v => v;
    const formatJodi = v => String(v).padStart(2, "0");
    const formatPanel = v => String(v).padStart(3, "0");

    const render = (targetId, data, countId, uniqueId) => {
      const target = $(targetId);
      if (!target) return;
      set(countId, num(data.reduce((s,x) => s + x.count, 0)));
      set(uniqueId, num(data.length) + " values");
      const max = data[0]?.count || 1;
      target.innerHTML = data.map(x =>
        '<div class="weight-row" title="Top ' + x.percentile + '% · rank ' + x.rank +
        ' · ' + x.count + ' observations">' +
        '<span class="rank">#' + x.rank + ' · ' + x.percentile + '%</span>' +
        '<span class="value">' + esc(x.value) + '</span>' +
        '<span class="weight-bar"><i style="width:' + Math.max(2, (x.count / max) * 100) + '%"></i></span>' +
        '<span class="weight">' + x.weight.toFixed(2) + '%</span>' +
        '<span class="cum">' + x.cumulative.toFixed(2) + '%</span></div>'
      ).join("");
    };

    render("digit-weight-ladder", build(digitMap, formatDigit, rows.length * 3), "digit-weight-count", "digit-weight-unique");
    render("jodi-weight-ladder", build(jodiMap, formatJodi, rows.length), "jodi-weight-count", "jodi-weight-unique");
    render("panel-weight-ladder", build(panelMap, formatPanel, rows.length), "panel-weight-count", "panel-weight-unique");
    set("weight-source", num(rows.length) + " historical rows");
  }

  function copyWeightLadder(type, button) {
    const ids = { digit: "digit-weight-ladder", jodi: "jodi-weight-ladder", panel: "panel-weight-ladder" };
    const source = $(ids[type]);
    if (!source) return;
    const lines = [];
    source.querySelectorAll(".weight-row:not(.header)").forEach(row => {
      const cells = row.querySelectorAll("span");
      lines.push(
        cells[0]?.textContent.trim() + " | " +
        cells[1]?.textContent.trim() + " | Weight " +
        cells[3]?.textContent.trim() + " | Cumulative " +
        cells[4]?.textContent.trim()
      );
    });
    const text = lines.join("\n");
    const done = () => {
      if (button) {
        const old = button.textContent;
        button.textContent = "Copied";
        setTimeout(() => button.textContent = old, 1400);
      }
    };
    navigator.clipboard?.writeText(text).then(done).catch(() => {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      done();
    });
  }

  function bindWeightCopyButtons() {
    document.querySelectorAll(".weight-copy").forEach(button => {
      button.addEventListener("click", () => copyWeightLadder(button.dataset.weightCopy, button));
    });
  }

  function renderMovement(rows) {
    const e = $("movement-chart"); if (!e) return;
    const values = rows.slice(0, 60).reverse().map(r => {
      const nums = String(r.open || "").split("").map(Number).filter(Number.isFinite);
      return nums.length ? nums.reduce((a,b)=>a+b,0)/nums.length : 0;
    });
    if (!values.length) { e.textContent = "No historical movement data"; return; }
    const max = Math.max(...values), min = Math.min(...values);
    e.innerHTML = '<div class="movement-summary">Latest ' + values[values.length-1].toFixed(2) +
      ' Â· Range ' + min.toFixed(2) + 'â€“' + max.toFixed(2) + '</div>' +
      '<div class="movement-bars">' + values.map(v =>
        '<span title="' + v.toFixed(2) + '" style="height:' +
        Math.max(4, ((v-min)/Math.max(.01,max-min))*100) + '%"></span>').join("") + '</div>';
    set("trend-range", rows.length + " stored rows");
    set("trend-label", "LIVE Â· 60-row view");
  }

  function renderRanking(data, type) {
    bars(type === "jodi" ? "jodi-k-bars" : "panel-k-bars", data.top_k || {});
    const latest = (data.observations_detail || [])[0];
    const candidates = latest && latest.top_candidates ? latest.top_candidates : [];
    set(type === "jodi" ? "jodi-meta" : "panel-meta",
      num(data.observations) + " held-out observations");
    const best = candidates[0] || {};
    set(type === "jodi" ? "jodi-best" : "panel-best", best.jodi || best.panel || "â€”");
    const e = $(type === "jodi" ? "jodi-candidates" : "panel-candidates");
    if (e) {
      e.innerHTML = candidates.slice(0, 10).map(c =>
        '<div class="candidate"><span class="rank">#' + (c.rank || "") +
        '</span><strong>' + (c.jodi || c.panel || "â€”") +
        '</strong><small>' + pct(c.probability) + '</small></div>'
      ).join("");
    }
  }

  function renderPrediction(prediction) {
    const jodi = prediction.jodi_second_candidates || [];
    const close = prediction.close_digit_candidates || {};
    set("preview-jodi", jodi.slice(0, 5).map(x => x.digit).join(", "));
    set("preview-c1", (close.first || []).slice(0, 5).map(x => x.digit).join(", "));
    set("preview-c2", (close.second || []).slice(0, 5).map(x => x.digit).join(", "));
    set("preview-c3", (close.third || []).slice(0, 5).map(x => x.digit).join(", "));
    set("close-digit-first", close.first && close.first[0] ? close.first[0].digit : "â€”");
    set("close-digit-second", close.second && close.second[0] ? close.second[0].digit : "â€”");
    set("close-digit-third", close.third && close.third[0] ? close.third[0].digit : "â€”");
  }

  function renderAudit(data) {
    if (!data || data.status !== "AVAILABLE") {
      set("audit-live-state", data && data.status ? data.status : "UNAVAILABLE");
      return;
    }
    set("audit-live-state", "AVAILABLE");
    set("audit-progress", num(data.predicted_rows) + " / " + num(data.record_count));
    set("audit-latest", "Latest " + (data.latest_date || "â€”"));
    set("audit-cycles", num(data.training_cycles));
    set("audit-matches", num(data.matches));
    set("audit-misses", num(data.misses));
    set("audit-top5", num((data.top_k_hits || {})["5"]));
    set("audit-row-count", num((data.rows || []).length) + " rows");
    const body = $("audit-table-body");
    if (!body) return;
    body.innerHTML = (data.rows || []).map(row => {
      const details = Object.entries(row.targets || {}).map(([name, value]) =>
        name + ": " + value.prediction + " -> " + value.actual +
        (value.matched ? " OK" : " MISS")
      ).join(" | ");
      return "<tr><td>" + row.row_number + "</td><td>" + row.date +
        "</td><td>" + row.open + "</td><td>" + row.jodi + "</td><td>" +
        row.jodi_family + "</td><td>" + row.close + "</td><td>" +
        row.training_state + "</td><td>" + row.status + "</td><td>" +
        details + "</td></tr>";
    }).join("");
  }

  async function loadAudit() {
    try { renderAudit(await get("/v1/model/training-audit")); }
    catch (error) { set("audit-live-state", "ERROR"); }
  }

  async function loadDashboard() {
    try {
      const urls = [
        "/v1/live/status",
        "/v1/historical/summary",
        "/v1/model/sequential/status",
        "/v1/ranking/summary",
        "/v1/analytics/summary",
        "/v1/historical/records?limit=2000",
        "/v1/model-health/summary",
        "/v1/ranking/jodi",
        "/v1/ranking/panel",
        "/v1/historical/frequency"
      ];
      const results = await Promise.all(urls.map(url => get(url).catch(() => ({}))));
      const live = results[0], history = results[1], model = results[2];
      const recordsData = results[5], health = results[6], jodi = results[7];
      const panel = results[8], frequency = results[9];

      const rows = renderRecords(recordsData);
      const latest = rows[0] || {};

      set("service-status", "LIVE");
      set("live-state", "LIVE");
      set("model-state", "Model " + (model.version || "â€”"));
      set("kpi-records", num(history.record_count));
      set("kpi-date", "Latest date " + (history.end_date || "â€”"));
      set("kpi-train", num(model.train_rows));
      set("kpi-validation", num(model.validation_rows));
      set("kpi-version", model.version || "â€”");
      set("kpi-ranking", num(jodi.observations));
      set("pipeline-state", "AVAILABLE");

      set("flow-data", latest.open || "â€”");
      set("flow-data-detail", latest.date || "Latest stored record");
      set("flow-training", model.status || "VALID");
      set("flow-training-detail", num(model.training_samples) + " training samples");

      renderMetrics(model);
      renderMovement(rows);
      renderRanking(jodi, "jodi");
      renderRanking(panel, "panel");

      const digitValues = {};
      (frequency.digits || []).forEach(item => {
        digitValues[item.digit] = Number(item.percentage || 0) / 100;
      });
      bars("digit-bars", digitValues);

      const panelCounts = {};
      rows.forEach(row => {
        if (row.open) panelCounts[row.open] = (panelCounts[row.open] || 0) + 1;
      });
      const counts = Object.values(panelCounts).sort((a, b) => b - a);
      const total = rows.length || 1;
      const coverage = {};
      [1, 3, 5, 7, 10].forEach(k => {
        coverage[k] = counts.slice(0, k).reduce((a, b) => a + b, 0) / total;
      });
      bars("open-panel-k", coverage);
      bars("close-panel-k", panel.top_k || {});

      set("health-card",
        health.status || health.health_report && health.health_report.status ||
        model.status || "AVAILABLE");
      set("training-card",
        (model.status || "AVAILABLE") + " Â· " +
        num(model.training_samples) + " training samples Â· " +
        num(model.validation_rows) + " validation rows");
      set("safety-card",
        model.strict_temporal_boundary ? "TEMPORAL SAFE" : "CHECK");

      renderFamilies(rows, null);
      renderWeightLadders(rows);
      if (latest.open && latest.jodi) {
        try {
          const prediction = await post("/v1/model/sequential/predict", {
            open: latest.open,
            jodi_first: String(latest.jodi)[0],
            market_id: latest.market_id || 1,
            top_k: 10
          });
          renderPrediction(prediction);
          renderFamilies(rows, prediction);
        } catch (error) {
          renderFamilies(rows, null);
          set("close-digit-first", "â€”");
          set("close-digit-second", "â€”");
          set("close-digit-third", "â€”");
        }
      }

      set("last-update", new Date().toLocaleTimeString());
    } catch (error) {
      set("service-status", "ERROR");
    }
  }

  async function initEntry() {
    const market = $("data-entry-market");
    if (market) {
      try {
        const data = await get("/v1/historical/markets");
        market.innerHTML = (data.markets || []).map(m =>
          '<option value="' + m.name + '">' + m.name + "</option>").join("");
      } catch (error) {
        market.innerHTML = '<option value="">Market unavailable</option>';
      }
    }
    const date = $("data-entry-date");
    if (date && !date.value) date.value = new Date().toISOString().slice(0, 10);
    const stage1 = $("stage1-save");
    const stage2 = $("stage2-save");
    const status = $("entry-status");
    const raw = $("entry-raw");
    const values = () => ({
      date: $("data-entry-date")?.value || "",
      market_name: $("data-entry-market")?.value || "",
      open: $("data-entry-open")?.value || "",
      jodi_first: $("data-entry-jodi-first")?.value || "",
      jodi_second: $("data-entry-jodi-second")?.value || "",
      close: $("data-entry-close")?.value || ""
    });
    if (stage1) stage1.addEventListener("click", async () => {
      try {
        const v = values();
        status.textContent = "Saving Stage 1...";
        const result = await post("/v1/historical/stage1", v);
        status.textContent = "Stage 1 saved Â· prediction ready";
        if (raw) raw.textContent = JSON.stringify(result, null, 2);
        const p = result.prediction || {};
        renderPrediction(p);
        set("flow-data", v.open);
        set("flow-data-detail", v.date);
        set("flow-prediction", "Stage 2 candidates");
        set("flow-prediction-detail", "Live sequential prediction");
        set("entry-raw", JSON.stringify(result, null, 2));
        stage2.disabled = false;
      } catch (error) {
        status.textContent = "Stage 1 failed";
        if (raw) raw.textContent = String(error);
      }
    });
    if (stage2) stage2.addEventListener("click", async () => {
      try {
        const v = values();
        status.textContent = "Saving Stage 2...";
        const result = await post("/v1/historical/stage2", v);
        status.textContent = "Record completed Â· model workflow updated";
        if (raw) raw.textContent = JSON.stringify(result, null, 2);
        set("flow-actual", v.close);
        set("flow-actual-detail", v.date);
        await loadDashboard();
        await loadAudit();
      } catch (error) {
        status.textContent = "Stage 2 failed";
        if (raw) raw.textContent = String(error);
      }
    });
    $("entry-clear")?.addEventListener("click", () => {
      ["data-entry-open","data-entry-jodi-first","data-entry-jodi-second","data-entry-close"].forEach(id => { const e=$(id); if(e)e.value=""; });
      if (raw) raw.textContent = "Waiting for Stage 1.";
      if (status) status.textContent = "Ready";
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadDashboard();
    loadAudit();
    setInterval(loadDashboard, 5000);
    $("refresh-all")?.addEventListener("click", () => {
      loadDashboard();
      loadAudit();
    });
    $("audit-refresh")?.addEventListener("click", loadAudit);
    bindFamilyCopyButtons();
    bindWeightCopyButtons();
    initEntry();
  });
})();






