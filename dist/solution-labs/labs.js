(function () {
  const project = document.body.dataset.project;
  const e = (value) =>
    String(value).replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const $ = (selector) => document.querySelector(selector);
  let current = null,
    mode = "local",
    component = project === "master" ? "matching" : "metrics",
    busy = false;
  const role = () => $("#identity").value;
  async function api(path, body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`/api/labs/${project}/${path}`, {
        method: body ? "POST" : "GET",
        headers: {
          "Content-Type": "application/json",
          "X-Demo-Identity": role(),
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
        signal: controller.signal,
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Check the selected values.",
        );
      return data;
    } finally {
      clearTimeout(timeout);
    }
  }
  function notice(message, error = false) {
    $("#notice").innerHTML = message
      ? `<div class="notice${error ? " error" : ""}">${e(message)}</div>`
      : "";
  }
  function tab(id, focus = false) {
    document.querySelectorAll("[data-view]").forEach((button) => {
      const selected = button.dataset.view === id;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
      if (selected && focus) button.focus();
    });
    document
      .querySelectorAll("[role=tabpanel]")
      .forEach((panel) => (panel.hidden = panel.id !== id));
  }
  function trace(data) {
    if (!data) return;
    $("#trace").innerHTML =
      `<span class="eyebrow">MEASURED LOCAL EXECUTION · ${e(data.total_ms)} ms</span><div class="trace">${data.stages.map((stage) => `<button data-trace-component="${e(stage.component)}">${e(stage.label)}<small>${e(stage.duration_ms)} ms · inspect component ↗</small></button>`).join("")}</div><details><summary>Execution JSON</summary><pre>${e(JSON.stringify(data, null, 2))}</pre></details>`;
  }
  function pairEvidence(data, pair) {
    const sources = [pair.left, pair.right].map((key) =>
      data.records.find((row) => row.source_key === key),
    );
    return `<details><summary>Compare source attributes</summary><div class="pair-evidence">${sources.map((row) => `<span><b>${e(row.source_key)}</b>${e(row.description)}<br>Part: ${e(row.part_number || "Unknown")}<br>${e(row.size)} · ${e(row.load_index)}${e(row.speed)}<br>${e(row.season)}</span>`).join("")}</div></details>`;
  }
  function master(data) {
    const counts = (status) =>
      data.pairs.filter((p) => p.status === status).length;
    $("#stats").innerHTML = [
      [data.records.length, "valid regional records"],
      [data.groups.length, "draft identity groups"],
      [counts("review"), "pairs needing review"],
      [data.publish_version, "published version"],
    ]
      .map(
        ([value, label]) =>
          `<div class="stat"><strong>${e(value)}</strong><span>${label}</span></div>`,
      )
      .join("");
    const pairs = data.pairs.filter((p) =>
      ["review", "blocked", "rejected"].includes(p.status),
    );
    $("#results").innerHTML =
      `<div class="split"><div class="panel"><span class="eyebrow">HUMAN DECISIONS + HARD GUARDRAILS</span><h2>Steward queue</h2><p class="small">${data.candidate_pairs} candidate pairs instead of ${data.all_pairs} all-pairs comparisons. Specifications alone never establish identity.</p>${
        pairs.length
          ? pairs
              .slice(0, 15)
              .map(
                (p) =>
                  `<div class="row"><div><span class="badge ${e(p.status)}">${e(p.status)}</span><h3>${e(p.left)} ↔ ${e(p.right)}</h3><small>${e(p.reason)} · text similarity ${e(p.score)}</small>${pairEvidence(data, p)}</div>${p.status === "review" && role() === "steward" ? `<div class="actions"><button data-action="approve" data-pair="${e(p.pair_id)}">Approve identity</button><button class="secondary" data-action="reject" data-pair="${e(p.pair_id)}">Keep distinct</button></div>` : ""}</div>`,
              )
              .join("")
          : "<p>No ambiguous or blocked pairs in this scenario.</p>"
      }<details><summary>All pair evidence (${data.pairs.length})</summary><pre>${e(JSON.stringify(data.pairs, null, 2))}</pre></details></div><div><div class="panel"><span class="eyebrow">CONSISTENT SNAPSHOT</span><h2>Publish with confidence.</h2><p>${data.publication ? `${data.publication.products.length} canonical products and ${data.publication.crosswalk.length} source mappings share version ${data.publish_version}.` : "Publish only after resolving ambiguity and source conflicts. The clean scenario demonstrates a valid publication."}</p><button data-action="publish" ${role() !== "steward" ? "disabled" : ""}>Validate & publish →</button> <button class="secondary" data-action="replay">Replay decisions</button>${data.publication ? `<details><summary>Master and crosswalk snapshot</summary><pre>${e(JSON.stringify(data.publication, null, 2))}</pre></details>` : ""}</div><div class="panel"><span class="eyebrow">DATA QUALITY</span><h3>${data.quarantine.length} quarantined source row(s)</h3>${data.quarantine.map((q) => `<p class="small">${e(q.source_key)} · ${e(q.reason)}</p>`).join("")}<details><summary>Audit / ${data.audit.length} actions</summary><pre>${e(JSON.stringify(data.audit, null, 2))}</pre></details></div></div></div><details class="panel"><summary>Normalized input records / source lineage</summary><pre>${e(JSON.stringify(data.records, null, 2))}</pre></details>`;
    trace(data.trace);
  }
  function beauty(data) {
    $("#stats").innerHTML = [
      [data.counts.invoice_lines, "synthetic sales lines"],
      [data.counts.invoices, "reconciled invoices"],
      [data.bronze_batches, "received batch hashes"],
      [data.publish_version, "valid product version"],
    ]
      .map(
        ([value, label]) =>
          `<div class="stat"><strong>${e(value)}</strong><span>${label}</span></div>`,
      )
      .join("");
    $("#results").innerHTML =
      `<div class="flow"><span>01 · SAP-shaped source</span><b>→</b><span>02 · Bronze ledger</span><b>→</b><span>03 · Silver + quality gate</span><b>→</b><span>04 · Cashflow / RGM</span><b>→</b><span>05 · Shared metrics + agents</span></div>${data.quality.length ? `<div class="notice error"><strong>Publication blocked. Last valid version ${data.publish_version} retained.</strong><br>${data.quality.map(e).join(" · ")}</div>` : `<p class="small">Quality gate passed · ${e(data.markets.join(" / "))} scope · USD only · as of ${e(data.as_of)}. Invoice revenue and receipt cash remain separate.</p>`}<div class="metric-grid">${data.metrics.map((m) => `<article class="metric-card"><span class="eyebrow">${e(m.metric.replaceAll("_", " "))}</span><strong>${m.value === null ? "N/A" : `${m.unit === "USD" ? "$" : ""}${Number(m.value).toLocaleString(undefined, { maximumFractionDigits: 2 })}${m.unit === "%" ? "%" : ""}`}</strong><p>${e(m.definition)}</p><details><summary>Definition and query</summary><pre>${e(JSON.stringify(m, null, 2))}</pre></details></article>`).join("")}</div><div class="panel"><span class="eyebrow">SHARED DEFINITIONS / SCOPED TOOLS</span><h2>Ask the data. Inspect the evidence.</h2><form id="ask" class="ask"><label>Business question<input id="question" value="What is the net revenue and explain promotion policy?" required maxlength="300"></label><label>Metric tool<select id="metric"><option value="">Infer one tool / policy</option>${data.metrics.map((m) => `<option value="${e(m.metric)}">${e(m.metric.replaceAll("_", " "))}</option>`).join("")}</select></label><label>Market<select id="market"><option value="all">Allowed markets</option>${data.markets.map((m) => `<option>${e(m)}</option>`).join("")}</select></label><button>Ask →</button></form><p class="small">Local deterministic routing + SQL + lexical cosine retrieval. Cloud Databricks metric views, AI Search and model serving are reference bindings.</p><div id="answer"></div></div>`;
    trace(data.trace);
  }
  function render(data) {
    current = data;
    if (project === "master") master(data);
    else beauty(data);
    $("#run-meta").textContent =
      `Workspace ${data.run_id.slice(0, 8)} · revision ${data.revision} · synthetic data`;
  }
  async function perform(functionToRun) {
    if (busy) return;
    busy = true;
    $("#run").disabled = true;
    $("#identity").disabled = true;
    $("#scenario").disabled = true;
    try {
      notice("Running the independent demo…");
      await functionToRun();
    } catch (error) {
      notice(
        error.name === "AbortError"
          ? "Request timed out. Retry the local service."
          : error.message,
        true,
      );
    } finally {
      busy = false;
      $("#run").disabled = false;
      $("#identity").disabled = false;
      $("#scenario").disabled = false;
    }
  }
  function map() {
    const model = window.solutionArchitecture.model(project, mode),
      graph = window.diagramGraph;
    $("#map-key").innerHTML = graph.key();
    $("#map").innerHTML =
      `<svg viewBox="0 0 ${model.width} ${model.height}" data-connection-map="" role="group" aria-label="${e(model.label)}"><defs>${graph.markers("lab-arrow", "#73886a", 7)}</defs>${model.paths.map((p) => `<path class="wire ${p[1]}" d="${graph.route(model, p)}" data-from="${p[2]}" data-to="${p[3]}" data-marker="lab-arrow" marker-end="url(#lab-arrow)"><title>${e(p[4])}</title></path>`).join("")}${model.nodes.map((n) => `<g class="arch-node${n.reference ? " reference" : ""}" data-component="${n.id}" data-node="${n.id}" role="button" tabindex="0" aria-label="${e(n.title)}"><rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="6"/><text class="platform" x="${n.x + 13}" y="${n.y + 25}">${e(n.platform)}</text><text class="title" x="${n.x + 13}" y="${n.y + 58}">${e(n.title)}</text><text class="subtitle" x="${n.x + 13}" y="${n.y + 92}">${e(n.sub)}</text></g>`).join("")}</svg>`;
    $("#component-select").innerHTML = model.nodes
      .map((n) => `<option value="${n.id}">${e(n.title)}</option>`)
      .join("");
    $("#map-download").href = `artifacts/${mode}-architecture.svg`;
    select(component);
  }
  function select(id, focused = true) {
    const model = window.solutionArchitecture.model(project, mode),
      node = model.nodes.find((n) => n.id === id);
    if (!node) return;
    component = id;
    document.querySelectorAll(".arch-node").forEach((n) => {
      n.classList.toggle("selected", n.dataset.node === id);
      n.setAttribute("aria-pressed", String(n.dataset.node === id));
    });
    $("#component-select").value = id;
    window.diagramGraph.apply($("#architecture"), model, id, focused);
    $("#inspector").innerHTML =
      `<span class="eyebrow">${e(node.platform)}</span><h3>${e(node.title)}</h3><p>${e(node.detail)}</p>${window.diagramGraph.html(model, id, "data-connect")}`;
  }
  document.addEventListener("click", (event) => {
    const button = event.target.closest("button,[data-node]");
    if (!button) return;
    if (button.dataset.view) tab(button.dataset.view);
    if (button.dataset.node || button.dataset.connect)
      select(button.dataset.node || button.dataset.connect);
    if (button.dataset.traceComponent) {
      tab("architecture");
      select(button.dataset.traceComponent);
    }
    if (button.id === "reset-map") select(component, false);
    if (button.dataset.action && current)
      perform(async () => {
        render(
          await api(`runs/${current.run_id}/actions`, {
            revision: current.revision,
            action: button.dataset.action,
            pair_id: button.dataset.pair || "",
          }),
        );
        notice(
          "Action applied. Inspect the new revision and publication state.",
        );
      });
  });
  document.addEventListener("keydown", (event) => {
    if (
      event.target.matches("[data-view]") &&
      ["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)
    ) {
      event.preventDefault();
      const buttons = [...document.querySelectorAll("[data-view]")],
        index = buttons.indexOf(event.target);
      const next =
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? buttons.length - 1
            : (index + (event.key === "ArrowRight" ? 1 : -1) + buttons.length) %
              buttons.length;
      tab(buttons[next].dataset.view, true);
    }
    const node = event.target.closest("[data-node]");
    if (node && ["Enter", " "].includes(event.key)) {
      event.preventDefault();
      select(node.dataset.node);
    }
  });
  $("#component-select").addEventListener("change", (event) =>
    select(event.target.value),
  );
  $("#map-mode").addEventListener("change", (event) => {
    mode = event.target.value;
    map();
  });
  $("#start").addEventListener("submit", (event) => {
    event.preventDefault();
    perform(async () => {
      render(await api("runs", { scenario: $("#scenario").value }));
      notice(
        "Independent workspace ready. Original client outcomes are not measured here.",
      );
    });
  });
  $("#identity").addEventListener("change", () => {
    current = null;
    $("#results").innerHTML = "";
    $("#stats").innerHTML = "";
    $("#trace").innerHTML = "";
    notice("Identity changed. Start a new isolated workspace.");
  });
  document.addEventListener("submit", (event) => {
    if (event.target.id !== "ask") return;
    event.preventDefault();
    perform(async () => {
      const data = await api(`runs/${current.run_id}/questions`, {
        question: $("#question").value,
        metric: $("#metric").value || null,
        market: $("#market").value,
      });
      $("#answer").innerHTML =
        `<div class="answer">${e(data.answer || data.clarification)}</div>${data.evidence ? `<details><summary>SQL metric evidence</summary><pre>${e(JSON.stringify(data.evidence, null, 2))}</pre></details>` : ""}${data.citations.map((c) => `<div class="citation"><strong>${e(c.document_id)} / ${e(c.title)}</strong><small> · lexical cosine ${e(c.similarity)}</small><p>${e(c.text)}</p></div>`).join("")}`;
      trace(data.trace);
      notice("");
    });
  });
  tab("workspace");
  map();
  perform(async () => {
    render(await api("runs", { scenario: $("#scenario").value }));
    notice("");
  });
})();
