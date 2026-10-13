const fs = require("node:fs"),
  path = require("node:path"),
  vm = require("node:vm");
const root = path.resolve(__dirname, ".."),
  context = vm.createContext({ window: {} });
for (const file of [
  "dist/technical-graph.js",
  "dist/solution-labs/architecture.js",
])
  vm.runInContext(fs.readFileSync(path.join(root, file), "utf8"), context);
const graph = context.window.diagramGraph,
  architecture = context.window.solutionArchitecture;
const e = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&apos;",
      })[c],
  );
function wrapper(title, width, height, body) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><title>${e(title)}</title><rect width="100%" height="100%" fill="#f6f5ef"/><style>text{fill:#192d26;font-family:Arial,sans-serif}.wire{fill:none;stroke:#73886a;stroke-width:2}.request{stroke-dasharray:7 4}.context{stroke-dasharray:3 4}.platform{font-size:9px;fill:#69716a}.title{font-size:18px;font-family:Georgia,serif}.subtitle{font-size:11px;fill:#69716a}</style>${body}</svg>\n`;
}
function map(project, mode) {
  const model = architecture.model(project, mode);
  graph.validate(model);
  return wrapper(
    model.label,
    model.width,
    model.height,
    `<defs>${graph.markers("arrow", "#73886a", 7)}</defs>${model.paths.map((p) => `<path class="wire ${p[1]}" d="${graph.route(model, p)}" marker-end="url(#arrow)"><title>${e(p[4])}</title></path>`).join("")}${model.nodes.map((n) => `<g><rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="6" fill="#fcfbf7" stroke="#adc0a1" ${mode === "cloud" ? 'stroke-dasharray="5 3"' : ""}/><text class="platform" x="${n.x + 13}" y="${n.y + 25}">${e(n.platform)}</text><text class="title" x="${n.x + 13}" y="${n.y + 58}">${e(n.title)}</text><text class="subtitle" x="${n.x + 13}" y="${n.y + 92}">${e(n.sub)}</text></g>`).join("")}`,
  );
}
function flow(title, steps) {
  return wrapper(
    title,
    1200,
    350,
    `<defs>${graph.markers("flow", "#73886a", 6)}</defs><text x="35" y="45" font-size="25" font-family="Georgia">${e(title)}</text><text x="35" y="76" font-size="12">Independent synthetic implementation / source and cloud bindings are separate.</text>${steps
      .map((step, i) => {
        const x = 35 + i * 232;
        return `<rect x="${x}" y="120" width="210" height="135" rx="7" fill="#e9eddf" stroke="#adc0a1"/><text x="${x + 15}" y="151" class="platform">0${i + 1}</text><text x="${x + 15}" y="184" font-size="17">${e(step[0])}</text><text x="${x + 15}" y="215" font-size="11">${e(step[1])}</text>${i < steps.length - 1 ? `<path class="wire" d="M${x + 210} 187L${x + 229} 187" marker-end="url(#flow)"/>` : ""}`;
      })
      .join("")}`,
  );
}
function entity(project) {
  const master = project === "master";
  const specifications = master
    ? [
        [
          "source",
          "Regional source",
          [
            "PK: source_key (globally unique)",
            "manufacturer part + hard specs",
            "Original representation / lineage",
          ],
        ],
        [
          "pair",
          "Candidate pair",
          [
            "PK: pair_id",
            "FK: left_source + right_source",
            "score evidence / rule version",
          ],
        ],
        [
          "decision",
          "Steward decision",
          [
            "FK: pair_id",
            "actor / approve or reject",
            "expected revision / audit history",
          ],
        ],
        [
          "canonical",
          "Canonical product",
          [
            "PK: global_id + publish_version",
            "Member source keys",
            "Stable identity / explicit migrations",
          ],
        ],
        [
          "crosswalk",
          "Regional crosswalk",
          [
            "FK: source_key / global_id",
            "Same publish_version",
            "One mapping per source/version",
          ],
        ],
        [
          "publication",
          "Publication pointer",
          [
            "active publish_version",
            "Input/decision snapshot digest",
            "Atomic master + crosswalk snapshot",
          ],
        ],
      ]
    : [
        [
          "invoice",
          "Invoice header",
          [
            "PK: invoice_id",
            "market / USD / amount_cents",
            "due_date / source provenance",
          ],
        ],
        [
          "line",
          "Sales line",
          [
            "PK: line_id / FK: invoice_id",
            "units / returns / net_cents",
            "Line grain; reconcile to header",
          ],
        ],
        [
          "receipt",
          "Receipt application",
          [
            "PK: receipt_id / FK: invoice_id",
            "amount_cents / received_date",
            "Aggregate before joining invoices",
          ],
        ],
        [
          "rgm",
          "Gold RGM fact",
          [
            "PK: line_id (derived)",
            "gross / discount / net / profit",
            "Same validated publication version",
          ],
        ],
        [
          "cash",
          "Gold cashflow fact",
          [
            "PK: invoice_id (derived)",
            "paid / outstanding / overdue",
            "Actual receipts; one invoice grain",
          ],
        ],
        [
          "docs",
          "Document / chunk corpus",
          [
            "document_id / chunk_id",
            "paragraph / server ACL / vector",
            "Independent of finance table joins",
          ],
        ],
      ];
  const relationships = master
    ? [
        ["source", "pair", "1:N left/right source references"],
        ["pair", "decision", "1:N versioned steward decisions"],
        ["source", "crosswalk", "1:1 accepted mapping per version"],
        ["canonical", "crosswalk", "1:N regional source mappings"],
        ["publication", "canonical", "one consistent published version"],
        ["publication", "crosswalk", "same publication marker"],
      ]
    : [
        ["invoice", "line", "1:N invoice lines"],
        ["invoice", "receipt", "1:N receipt applications"],
        ["line", "rgm", "1:1 derived line fact"],
        ["invoice", "cash", "1:1 derived invoice fact"],
        ["receipt", "cash", "N:1 aggregate receipts before join"],
      ];
  const model = {
    label: `${project} logical data model`,
    nodes: specifications.map(([id, title, fields], i) => ({
      id,
      title,
      fields,
      x: 35 + (i % 3) * 415,
      y: 135 + Math.floor(i / 3) * 225,
      w: 330,
      h: 155,
    })),
    paths: relationships.map(([from, to, label]) => [
      null,
      "data",
      from,
      to,
      label,
    ]),
  };
  return wrapper(
    model.label,
    1250,
    730,
    `<defs>${graph.markers("entity", "#73886a", 6)}</defs><text x="35" y="45" font-size="27">${master ? "Product identity / lineage contracts" : "Financial grain / independent document corpus"}</text><text x="35" y="78" font-size="12">${master ? "Logical relationships within the versioned JSON snapshot; canonical attribute survivorship is a production extension." : "Header, line and receipt grains remain separate. The corpus joins only as answer evidence, never as financial rows."}</text>${model.paths.map((p) => `<path class="wire" d="${graph.route(model, p)}" marker-end="url(#entity)"><title>${e(p[4])}</title></path>`).join("")}${model.nodes.map((n) => `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="7" fill="#fcfbf7" stroke="#adc0a1"/><text x="${n.x + 17}" y="${n.y + 33}" font-size="19">${e(n.title)}</text>${n.fields.map((field, i) => `<text x="${n.x + 17}" y="${n.y + 66 + i * 27}" font-size="12">${e(field)}</text>`).join("")}`).join("")}<text x="35" y="575" class="platform">RELATIONSHIPS / INVARIANTS</text>${relationships.map(([from, to, label], i) => `<text x="${35 + (i % 2) * 600}" y="${603 + Math.floor(i / 2) * 26}" font-size="12">${e(`${from} → ${to} : ${label}`)}</text>`).join("")}`,
  );
}
function sequence(project) {
  const master = project === "master",
    participants = master
      ? [
          "Steward browser",
          "API / identity boundary",
          "Resolution / state",
          "Published snapshot",
        ]
      : [
          "Business user",
          "API / scoped tools",
          "SQL metric layer",
          "Document corpus",
        ];
  const calls = master
    ? [
        [0, 1, "Action + expected workspace revision"],
        [1, 2, "Load owner / inputs / persistent decisions"],
        [2, 2, "Normalize, block and check whole clusters"],
        [2, 1, "Validated groups or ambiguity/conflict"],
        [1, 3, "If publish: atomic CAS snapshot"],
        [3, 1, "Same-version master / crosswalk / pointer"],
        [1, 0, "Decision evidence / audit / version"],
      ]
    : [
        [0, 1, "Question + role + typed market"],
        [1, 1, "Authorize / clarify unsupported requests"],
        [1, 2, "If numeric: allowlisted scoped query"],
        [2, 1, "Calculated measure + definition + version"],
        [1, 3, "If context: filter ACLs, then score vectors"],
        [3, 1, "Authorized chunks + source IDs"],
        [1, 1, "Compose factual evidence / bounded fallback"],
        [1, 0, "Answer + SQL evidence + citations"],
      ];
  const xs = [140, 460, 780, 1100];
  return wrapper(
    `${project} runtime sequence`,
    1250,
    740,
    `<defs>${graph.markers("sequence", "#577568", 6)}</defs><text x="35" y="45" font-size="27">${master ? "Steward decision / publication sequence" : "Scoped business-question sequence"}</text><text x="35" y="77" font-size="12">Logical local calls; conditional paths run only when needed. Cloud endpoints are separate reference bindings.</text>${participants.map((label, i) => `<rect x="${xs[i] - 115}" y="103" width="230" height="45" rx="5" fill="#e9eddf"/><text x="${xs[i]}" y="130" text-anchor="middle" font-size="13">${e(label)}</text><path d="M${xs[i]} 148L${xs[i]} 680" stroke="#b7c4ae" stroke-dasharray="5 4"/>`).join("")}${calls
      .map(([from, to, label], i) => {
        const y = 187 + i * 60;
        return from === to
          ? `<path class="wire" d="M${xs[from]} ${y}H${xs[from] + 60}V${y + 23}H${xs[from]}" marker-end="url(#sequence)"/><text x="${xs[from] + 70}" y="${y + 15}" font-size="11">${e(label)}</text>`
          : `<path class="wire${from > to ? " request" : ""}" d="M${xs[from]} ${y}L${xs[to]} ${y}" marker-end="url(#sequence)"/><text x="${Math.min(xs[from], xs[to]) + 13}" y="${y - 9}" font-size="12">${e(label)}</text>`;
      })
      .join(
        "",
      )}<text x="35" y="713" class="subtitle">Independent synthetic implementation · requests and results follow declared actor direction.</text>`,
  );
}
const descriptions = {
  master: {
    "runtime-sequence.svg": [
      "Steward decision → versioned master",
      [
        ["Inspect pair", "Source + score evidence"],
        ["Authorize action", "Owner + expected revision"],
        ["Apply constraints", "Reject transitive conflicts"],
        ["Commit publication", "Master / crosswalk / pointer"],
        ["Serve one version", "Lineage + audit revision"],
      ],
    ],
    "ingestion-flow.svg": [
      "Regional ingestion and replay",
      [
        ["Regional input", "Stable source keys"],
        ["Normalize", "Schema + taxonomy"],
        ["Block & match", "Hard specs + identity"],
        ["Review / quarantine", "Ambiguity / source conflicts"],
        ["Publish / retain", "Complete valid snapshot"],
      ],
    ],
    "data-model.svg": [
      "Product identity contracts",
      [
        ["Source record", "region + source_key"],
        ["Candidate pair", "two source keys + evidence"],
        ["Decision", "actor + revision + rule"],
        ["Canonical product", "stable global_id + version"],
        ["Crosswalk", "source → global + version"],
      ],
    ],
  },
  beauty: {
    "runtime-sequence.svg": [
      "Business question → authorized evidence",
      [
        ["Question + identity", "Typed metric / market"],
        ["Authorize tool", "Finance / market policy"],
        ["Execute SQL", "Allowlisted metric definition"],
        ["Retrieve context", "ACL before vector scoring"],
        ["Render answer", "Calculated value + citations"],
      ],
    ],
    "ingestion-flow.svg": [
      "Medallion quality-gated publication",
      [
        ["SAP-shaped source", "Lines / invoices / receipts"],
        ["Bronze ledger", "Payload + content hash"],
        ["Silver reconcile", "Keys / USD / header totals"],
        ["Gold products", "RGM + receipt cashflow"],
        ["Semantic serving", "Last valid publish version"],
      ],
    ],
    "data-model.svg": [
      "Financial grain and retrieval contracts",
      [
        ["Invoice header", "1 row / invoice_id"],
        ["Sales line", "1 row / line_id"],
        ["Receipt application", "1 row / receipt_id"],
        ["Metric result", "scope + unit + version"],
        ["Document chunk", "source_id + ACL + vector"],
      ],
    ],
  },
};
for (const project of ["master"]) {
  const dest = path.join(root, `dist/${project}-demo/artifacts`);
  fs.mkdirSync(dest, { recursive: true });
  const files = {
    "local-architecture.svg": map(project, "local"),
    "cloud-architecture.svg": map(project, "cloud"),
    ...Object.fromEntries(
      Object.entries(descriptions[project]).map(([file, [title, steps]]) => [
        file,
        file === "data-model.svg"
          ? entity(project)
          : file === "runtime-sequence.svg"
            ? sequence(project)
            : flow(title, steps),
      ]),
    ),
  };
  for (const [file, content] of Object.entries(files)) {
    const target = path.join(dest, file);
    if (process.argv.includes("--check")) {
      if (fs.readFileSync(target, "utf8") !== content)
        throw new Error(`Diagram drift: ${project}/${file}`);
    } else fs.writeFileSync(target, content);
  }
}
console.log("Validated two logical graphs and five native SVG artifacts.");
