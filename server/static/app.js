(function () {
  "use strict";

  // ── Enum labels (mirrors dsn_extractor/enums.py) ─────────
  var RETIREMENT_LABELS = {
    "01": "Cadre",
    "02": "Extension cadre",
    "04": "Non-cadre",
    "98": "Autre (pas de distinction cadre/non-cadre)",
    "99": "Pas de retraite compl\u00e9mentaire",
  };

  var CONTRACT_LABELS = {
    "01": "CDI",
    "02": "CDD",
    "03": "CTT (int\u00e9rim)",
    "07": "CDI intermittent",
    "08": "CDD d\u2019usage",
    "09": "CDD senior",
    "10": "CDD \u00e0 objet d\u00e9fini",
    "29": "Convention de stage",
    "32": "CDD remplacement",
    "50": "CDI de chantier",
    "60": "CDI op\u00e9rationnel",
    "70": "CDI int\u00e9rimaire",
    "80": "Mandat social",
    "81": "Mandat \u00e9lectif",
    "82": "Contrat d\u2019appui",
    "89": "Volontariat de service civique",
    "90": "Autre contrat",
    "91": "Contrat engagement \u00e9ducatif",
    "92": "CDD tremplin",
    "93": "Dispositif acad\u00e9mie des leaders",
  };

  var EXIT_REASON_LABELS = {
    "011": "Licenciement (liquidation judiciaire)",
    "012": "Licenciement (redressement judiciaire)",
    "014": "Licenciement \u00e9conomique",
    "015": "Licenciement inaptitude (non pro.)",
    "017": "Licenciement inaptitude (pro.)",
    "020": "Licenciement faute grave",
    "025": "Licenciement faute lourde",
    "026": "Licenciement cause r\u00e9elle et s\u00e9rieuse",
    "031": "Fin de CDD",
    "032": "Fin de mission (int\u00e9rim)",
    "034": "Fin de contrat d\u2019apprentissage",
    "035": "Fin de p\u00e9riode d\u2019essai (salari\u00e9)",
    "036": "Fin de mandat",
    "038": "Mise \u00e0 la retraite",
    "039": "D\u00e9part retraite (salari\u00e9)",
    "043": "Rupture conventionnelle",
    "058": "Prise d\u2019acte de rupture",
    "059": "D\u00e9mission",
    "065": "D\u00e9c\u00e8s",
    "066": "D\u00e9part volontaire (PSE)",
    "099": "Fin de relation (transfert)",
  };

  var ABSENCE_MOTIF_LABELS = {
    "01": "Maladie",
    "02": "Maladie professionnelle",
    "03": "Accident du travail",
    "04": "Accident de trajet",
    "05": "Maternit\u00e9",
    "06": "Paternit\u00e9",
    "07": "Adoption",
    "10": "Activit\u00e9 partielle",
    "13": "Cong\u00e9 sans solde",
    "14": "Cong\u00e9 sabbatique",
    "15": "Cong\u00e9 parental",
    "17": "\u00c9v\u00e9nement familial",
    "19": "Gr\u00e8ve",
    "20": "Temps partiel th\u00e9rapeutique",
    "501": "Cong\u00e9 divers non r\u00e9mun\u00e9r\u00e9",
    "637": "Cong\u00e9 pour \u00e9v\u00e9nement familial",
  };

  var COMPLEXITY_WEIGHTS = {
    "bulletins": 1,
    "entries": 3,
    "exits": 3,
    "absence_events": 2,
    "dsn_anomalies": 5,
  };

  var COMPLEXITY_LABELS = {
    "bulletins": "Bulletins",
    "entries": "Entr\u00e9es",
    "exits": "Sorties",
    "absence_events": "Absences",
    "dsn_anomalies": "Anomalies DSN",
  };

  var MONTH_NAMES = [
    "Janvier", "F\u00e9vrier", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Ao\u00fbt", "Septembre", "Octobre", "Novembre", "D\u00e9cembre",
  ];

  var CONTRIBUTION_FAMILIES = ["urssaf", "pas", "prevoyance", "mutuelle", "retraite"];

  var CONTRIBUTION_FAMILY_LABELS = {
    "urssaf": "URSSAF",
    "pas": "PAS",
    "prevoyance": "Pr\u00e9voyance",
    "mutuelle": "Mutuelle",
    "retraite": "Retraite",
  };

  // ── State ────────────────────────────────────────────────
  var PAGES = ["analyse", "tracking", "controle"];

  var state = {
    phase: "empty",
    data: null,
    error: null,
    scope: "global",
    activeEstIdx: 0,
    activeContributionFamily: "urssaf",
    activePage: "controle",
    contribFilterEcartsOnly: false,
  };

  // ── DOM refs (cached once) ───────────────────────────────
  var $body = document.body;
  var $dropzone = document.getElementById("dropzone");
  var $fileInput = document.getElementById("file-input");
  var $browseBtn = document.getElementById("browse-btn");
  var $dropzoneLabel = document.getElementById("dropzone-label");
  var $dropzoneSublabel = document.getElementById("dropzone-sublabel");
  var $dropzoneError = document.getElementById("dropzone-error");
  var $spinner = document.getElementById("spinner");
  var $spinnerLabel = document.getElementById("spinner-label");

  var $errorDetail = document.getElementById("error-detail");
  var $errorWarnings = document.getElementById("error-warnings");

  var $headerCompany = document.getElementById("header-company");
  var $headerSiret = document.getElementById("header-siret");
  var $headerPeriod = document.getElementById("header-period");

  var $establishmentTabs = document.getElementById("establishment-tabs");
  var $establishmentDetail = document.getElementById("establishment-detail");

  var $warningsBanner = document.getElementById("warnings-banner");
  var $warningsList = document.getElementById("warnings-list");

  var $cardEmployees = document.getElementById("card-employees");
  var $cardHires = document.getElementById("card-hires");
  var $cardExits = document.getElementById("card-exits");
  var $cardStagiaires = document.getElementById("card-stagiaires");

  var $tableRetirement = document.getElementById("table-retirement");
  var $tableContract = document.getElementById("table-contract");

  var $amtTickets = document.getElementById("amt-tickets");
  var $amtTransportPublic = document.getElementById("amt-transport-public");
  var $amtTransportPersonal = document.getElementById("amt-transport-personal");

  var $extNetFiscal = document.getElementById("ext-net-fiscal");
  var $extNetPaid = document.getElementById("ext-net-paid");
  var $extPas = document.getElementById("ext-pas");
  var $extGross = document.getElementById("ext-gross");

  // Social analysis
  var $saEffectif = document.getElementById("sa-effectif");
  var $saEntrees = document.getElementById("sa-entrees");
  var $saSorties = document.getElementById("sa-sorties");
  var $saStagiaires = document.getElementById("sa-stagiaires");
  var $saCadre = document.getElementById("sa-cadre");
  var $saNonCadre = document.getElementById("sa-non-cadre");
  var $saTableContracts = document.getElementById("sa-table-contracts");
  var $saTableExitReasons = document.getElementById("sa-table-exit-reasons");
  var $saAbsEmployees = document.getElementById("sa-abs-employees");
  var $saAbsEvents = document.getElementById("sa-abs-events");
  var $saTableAbsences = document.getElementById("sa-table-absences");
  var $saNetVerse = document.getElementById("sa-net-verse");
  var $saNetFiscal = document.getElementById("sa-net-fiscal");
  var $saPas = document.getElementById("sa-pas");
  var $saAlertsSection = document.getElementById("sa-alerts-section");
  var $saAlertsCount = document.getElementById("sa-alerts-count");
  var $saAlertsList = document.getElementById("sa-alerts-list");

  // Payroll tracking
  var $ptBulletins = document.getElementById("pt-bulletins");
  var $ptEntries = document.getElementById("pt-entries");
  var $ptExits = document.getElementById("pt-exits");
  var $ptAbsences = document.getElementById("pt-absences");
  var $ptExceptional = document.getElementById("pt-exceptional");
  var $ptAnomalies = document.getElementById("pt-anomalies");
  var $ptScoreValue = document.getElementById("pt-score-value");
  var $ptScoreInputs = document.getElementById("pt-score-inputs");
  var $ptEntriesNames = document.getElementById("pt-entries-names");
  var $ptExitsNames = document.getElementById("pt-exits-names");
  var $ptAbsencesNames = document.getElementById("pt-absences-names");

  // Contribution comparisons
  var $ccOkCount = document.getElementById("cc-ok-count");
  var $ccMismatchCount = document.getElementById("cc-mismatch-count");
  var $ccWarningCount = document.getElementById("cc-warning-count");
  var $contribFamilyTabs = document.getElementById("contrib-family-tabs");
  var $contribFamilyPanels = document.getElementById("contrib-family-panels");

  // ── Formatting helpers ───────────────────────────────────

  function formatAmount(v) {
    if (v == null) return "\u2014";
    var n = parseFloat(v);
    if (isNaN(n)) return "\u2014";
    return n.toLocaleString("fr-FR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) + " \u20ac";
  }

  function formatRate(v) {
    if (v == null) return "\u2014";
    var n = parseFloat(v);
    if (isNaN(n)) return "\u2014";
    return n.toLocaleString("fr-FR", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 4,
    }) + " %";
  }

  function formatSiret(v) {
    if (!v) return "\u2014";
    var s = v.replace(/\s/g, "");
    if (s.length !== 14) return v;
    return s.slice(0, 3) + " " + s.slice(3, 6) + " " + s.slice(6, 9) + " " + s.slice(9);
  }

  function formatMonth(v) {
    if (!v) return "\u2014";
    var parts = v.split("-");
    if (parts.length !== 2) return v;
    var monthIdx = parseInt(parts[1], 10) - 1;
    if (monthIdx < 0 || monthIdx > 11) return v;
    return MONTH_NAMES[monthIdx] + " " + parts[0];
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function formatStatusLabel(status) {
    if (!status) return "\u2014";
    if (status === "ok") return "OK";
    if (status === "ecart") return "\u00c9cart";
    if (status === "declared_only") return "D\u00e9clar\u00e9 seul";
    if (status === "computed_only") return "Recalcul\u00e9 seul";
    if (status.indexOf("manquant") === 0) return status.replace(/_/g, " ");
    if (status === "non_rattache") return "Non rattach\u00e9";
    if (status === "non_calculable") return "Non calculable";
    return status.replace(/_/g, " ");
  }

  function formatDetailStatusLabel(detail) {
    if (detail.status !== "ecart") return formatStatusLabel(detail.status);
    var rm = !!detail.rate_mismatch;
    var am = !!detail.amount_mismatch;
    if (rm && am) return "\u00c9cart taux + montant";
    if (rm) return "\u00c9cart taux";
    if (am) return "\u00c9cart montant";
    return "\u00c9cart";
  }

  function formatFamilyLabel(family) {
    return CONTRIBUTION_FAMILY_LABELS[family] || family || "\u2014";
  }

  function getStatusBadgeClass(status) {
    return "status-badge status-badge--" + (status || "non_calculable");
  }

  function collectComparisonWarnings(item) {
    var warnings = [];
    if (item && Array.isArray(item.warnings)) {
      warnings = warnings.concat(item.warnings);
    }
    if (item && Array.isArray(item.details)) {
      item.details.forEach(function (detail) {
        if (detail && Array.isArray(detail.warnings) && detail.warnings.length > 0) {
          warnings = warnings.concat(detail.warnings);
        }
      });
    }
    return warnings;
  }

  function countComparisonWarnings(items) {
    var seen = {};
    var count = 0;
    (items || []).forEach(function (item) {
      collectComparisonWarnings(item).forEach(function (warning) {
        var key = String(warning);
        if (!seen[key]) {
          seen[key] = true;
          count += 1;
        }
      });
    });
    return count;
  }

  // ── State management ─────────────────────────────────────

  function setState(patch) {
    for (var k in patch) {
      if (patch.hasOwnProperty(k)) state[k] = patch[k];
    }
    render();
  }

  // ── Render ───────────────────────────────────────────────

  function render() {
    $body.dataset.state = state.phase;

    if (state.phase === "uploading") {
      $dropzoneLabel.textContent = "Traitement en cours...";
      $dropzoneSublabel.textContent = "";
      $browseBtn.hidden = true;
      $spinner.hidden = false;
      $spinnerLabel.hidden = false;
      $dropzoneError.textContent = "";
    } else if (state.phase === "empty") {
      $dropzoneLabel.textContent = "D\u00e9posez un fichier .dsn ou .txt ici";
      $dropzoneSublabel.textContent = "ou cliquez pour parcourir";
      $browseBtn.hidden = false;
      $spinner.hidden = true;
      $spinnerLabel.hidden = true;
    }

    if (state.phase === "error" && state.error) {
      renderError();
    }

    if (state.phase === "results" && state.data) {
      renderResults();
    }
  }

  // ── Error rendering ──────────────────────────────────────

  function renderError() {
    var err = state.error;
    $errorDetail.textContent = err.detail || "Une erreur inconnue s\u2019est produite.";
    $errorWarnings.innerHTML = "";
    if (err.warnings && err.warnings.length > 0) {
      err.warnings.forEach(function (w) {
        var li = document.createElement("li");
        li.textContent = w;
        $errorWarnings.appendChild(li);
      });
    }
  }

  // ── Results rendering ────────────────────────────────────

  function renderPageNav() {
    var btns = document.querySelectorAll(".page-nav__btn");
    btns.forEach(function (btn) {
      if (btn.dataset.page === state.activePage) {
        btn.classList.add("page-nav__btn--active");
      } else {
        btn.classList.remove("page-nav__btn--active");
      }
    });

    PAGES.forEach(function (page) {
      var el = document.getElementById("page-" + page);
      if (el) el.hidden = page !== state.activePage;
    });
  }

  function renderResults() {
    var d = state.data;

    renderHeader(d);
    renderPageNav();
    renderScopeToggle();
    renderEstablishmentTabs(d);

    var counts, amounts, extras, quality;

    if (state.scope === "global") {
      counts = d.global_counts;
      amounts = d.global_amounts;
      extras = d.global_extras;
      quality = d.global_quality;
      $establishmentDetail.hidden = true;
    } else {
      var est = d.establishments[state.activeEstIdx];
      counts = est.counts;
      amounts = est.amounts;
      extras = est.extras;
      quality = est.quality;
      renderEstablishmentDetail(est.identity);
    }

    renderSummaryCards(counts);
    renderRetirementTable(counts);
    renderContractTable(counts);
    renderAmounts(amounts);
    renderExtras(extras);
    renderWarnings(quality);

    var sa, pt;
    if (state.scope === "global") {
      sa = d.global_social_analysis;
      pt = d.global_payroll_tracking;
    } else {
      var activeEst = d.establishments[state.activeEstIdx];
      sa = activeEst.social_analysis;
      pt = activeEst.payroll_tracking;
    }
    renderSocialAnalysis(sa);
    renderPayrollTracking(pt);
    renderContributionComparisons();
  }

  function renderHeader(d) {
    var company = d.company || {};
    $headerCompany.textContent = company.name || company.siren || "\u2014";
    $headerSiret.textContent = formatSiret(company.siret);
    $headerPeriod.textContent = formatMonth(d.declaration ? d.declaration.month : null);
  }

  function renderScopeToggle() {
    var btns = document.querySelectorAll(".scope-toggle__btn");
    btns.forEach(function (btn) {
      if (btn.dataset.scope === state.scope) {
        btn.classList.add("scope-toggle__btn--active");
      } else {
        btn.classList.remove("scope-toggle__btn--active");
      }
    });

    // Disable per-establishment if no establishments
    var estBtn = document.querySelector('[data-scope="establishment"]');
    if (state.data && state.data.establishments.length === 0) {
      estBtn.disabled = true;
      estBtn.style.opacity = "0.4";
      estBtn.style.cursor = "default";
    } else {
      estBtn.disabled = false;
      estBtn.style.opacity = "";
      estBtn.style.cursor = "";
    }
  }

  function renderEstablishmentTabs(d) {
    var show = state.scope === "establishment" && d.establishments.length > 1;
    $establishmentTabs.hidden = !show;
    if (!show) return;

    $establishmentTabs.innerHTML = "";
    d.establishments.forEach(function (est, i) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tab-bar__btn";
      if (i === state.activeEstIdx) btn.classList.add("tab-bar__btn--active");
      btn.dataset.index = i;
      var id = est.identity || {};
      btn.textContent = id.name || id.siret || ("\u00c9tablissement " + (i + 1));
      $establishmentTabs.appendChild(btn);
    });
  }

  function renderEstablishmentDetail(identity) {
    if (!identity) {
      $establishmentDetail.hidden = true;
      return;
    }

    var items = [];
    if (identity.siret) items.push({ label: "SIRET", value: formatSiret(identity.siret) });
    if (identity.naf_code) items.push({ label: "NAF", value: identity.naf_code });
    if (identity.ccn_code) items.push({ label: "CCN", value: identity.ccn_code });
    if (identity.city) items.push({ label: "Ville", value: identity.city });

    if (items.length === 0) {
      $establishmentDetail.hidden = true;
      return;
    }

    $establishmentDetail.hidden = false;
    $establishmentDetail.innerHTML = items.map(function (item) {
      return '<span class="establishment-detail__item">'
        + '<span class="establishment-detail__label">' + escapeHtml(item.label) + ':</span> '
        + '<span class="establishment-detail__value">' + escapeHtml(item.value) + '</span>'
        + '</span>';
    }).join("");
  }

  function renderSummaryCards(counts) {
    $cardEmployees.textContent = counts.employee_blocks_count;
    $cardHires.textContent = counts.new_employees_in_month;
    $cardExits.textContent = counts.exiting_employees_in_month;
    $cardStagiaires.textContent = counts.stagiaires;
  }

  function renderRetirementTable(counts) {
    var data = counts.employees_by_retirement_category_code || {};
    var codes = Object.keys(data);

    if (codes.length === 0) {
      $tableRetirement.innerHTML = '<tr><td colspan="3" class="data-table__empty">Aucune donn\u00e9e</td></tr>';
      return;
    }

    codes.sort();
    $tableRetirement.innerHTML = codes.map(function (code) {
      var label = RETIREMENT_LABELS[code] || code;
      return '<tr>'
        + '<td class="mono">' + escapeHtml(code) + '</td>'
        + '<td>' + escapeHtml(label) + '</td>'
        + '<td class="mono">' + data[code] + '</td>'
        + '</tr>';
    }).join("");
  }

  function renderContractTable(counts) {
    var data = counts.employees_by_contract_nature_code || {};
    var codes = Object.keys(data);

    if (codes.length === 0) {
      $tableContract.innerHTML = '<tr><td colspan="3" class="data-table__empty">Aucune donn\u00e9e</td></tr>';
      return;
    }

    codes.sort();
    $tableContract.innerHTML = codes.map(function (code) {
      var label = CONTRACT_LABELS[code] || code;
      return '<tr>'
        + '<td class="mono">' + escapeHtml(code) + '</td>'
        + '<td>' + escapeHtml(label) + '</td>'
        + '<td class="mono">' + data[code] + '</td>'
        + '</tr>';
    }).join("");
  }

  function renderAmounts(amounts) {
    $amtTickets.textContent = formatAmount(amounts.tickets_restaurant_employer_contribution_total);
    $amtTransportPublic.textContent = formatAmount(amounts.transport_public_total);
    $amtTransportPersonal.textContent = formatAmount(amounts.transport_personal_total);
  }

  function renderExtras(extras) {
    $extNetFiscal.textContent = formatAmount(extras.net_fiscal_sum);
    $extNetPaid.textContent = formatAmount(extras.net_paid_sum);
    $extPas.textContent = formatAmount(extras.pas_sum);
    $extGross.textContent = formatAmount(extras.gross_sum_from_salary_bases);
  }

  function renderWarnings(quality) {
    var warnings = quality.warnings || [];
    if (warnings.length === 0) {
      $warningsBanner.hidden = true;
      return;
    }
    $warningsBanner.hidden = false;
    $warningsList.innerHTML = "";
    warnings.forEach(function (w) {
      var li = document.createElement("li");
      li.textContent = w;
      $warningsList.appendChild(li);
    });
  }

  // ── Social analysis rendering ──────────────────────────────

  function renderSocialAnalysis(sa) {
    if (!sa) return;

    $saEffectif.textContent = sa.effectif;
    $saEntrees.textContent = sa.entrees;
    $saSorties.textContent = sa.sorties;
    $saStagiaires.textContent = sa.stagiaires;
    $saCadre.textContent = sa.cadre_count;
    $saNonCadre.textContent = sa.non_cadre_count;

    // Contracts table
    renderCodeTable($saTableContracts, sa.contracts_by_code, CONTRACT_LABELS);

    // Exit reasons table
    renderCodeTable($saTableExitReasons, sa.exit_reasons_by_code, EXIT_REASON_LABELS);

    // Absences
    $saAbsEmployees.textContent = sa.absences_employees_count;
    $saAbsEvents.textContent = sa.absences_events_count;
    renderCodeCountTable($saTableAbsences, sa.absences_by_code, ABSENCE_MOTIF_LABELS);

    // Remuneration
    $saNetVerse.textContent = formatAmount(sa.net_verse_total);
    $saNetFiscal.textContent = formatAmount(sa.net_fiscal_total);
    $saPas.textContent = formatAmount(sa.pas_total);

    // Quality alerts
    var alerts = sa.quality_alerts || [];
    if (alerts.length === 0) {
      $saAlertsSection.hidden = true;
    } else {
      $saAlertsSection.hidden = false;
      $saAlertsCount.textContent = sa.quality_alerts_count;
      $saAlertsList.innerHTML = "";
      alerts.forEach(function (a) {
        var li = document.createElement("li");
        li.textContent = a;
        $saAlertsList.appendChild(li);
      });
    }
  }

  function renderCodeTable(tbody, codeData, labelMap) {
    var codes = Object.keys(codeData || {});
    if (codes.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" class="data-table__empty">Aucune donn\u00e9e</td></tr>';
      return;
    }
    codes.sort();
    tbody.innerHTML = codes.map(function (code) {
      var label = labelMap[code] || code;
      return '<tr>'
        + '<td class="mono">' + escapeHtml(code) + '</td>'
        + '<td>' + escapeHtml(label) + '</td>'
        + '<td class="mono">' + codeData[code] + '</td>'
        + '</tr>';
    }).join("");
  }

  function renderCodeCountTable(tbody, codeData, labelMap) {
    var codes = Object.keys(codeData || {});
    if (codes.length === 0) {
      tbody.innerHTML = '<tr><td colspan="2" class="data-table__empty">Aucune donn\u00e9e</td></tr>';
      return;
    }
    codes.sort();
    tbody.innerHTML = codes.map(function (code) {
      var label = labelMap[code] || code;
      return '<tr>'
        + '<td>' + escapeHtml(label) + ' <span class="mono">(' + escapeHtml(code) + ')</span></td>'
        + '<td class="mono">' + codeData[code] + '</td>'
        + '</tr>';
    }).join("");
  }

  function renderNameList(el, names) {
    if (!names || names.length === 0) { el.innerHTML = ""; return; }
    el.innerHTML = names.map(function (n) {
      return '<span class="name-tag">' + escapeHtml(n) + '</span>';
    }).join("");
  }

  function renderAbsenceDetails(el, details) {
    if (!details || details.length === 0) { el.innerHTML = ""; return; }
    el.innerHTML = details.map(function (d) {
      var motif = ABSENCE_MOTIF_LABELS[d.motif_code] || d.motif_label || d.motif_code;
      return '<span class="name-tag">'
        + escapeHtml(d.employee_name)
        + ' <span class="name-tag__motif">\u2014 ' + escapeHtml(motif) + '</span>'
        + '</span>';
    }).join("");
  }

  // ── Payroll tracking rendering ─────────────────────────────

  function renderPayrollTracking(pt) {
    if (!pt) return;

    $ptBulletins.textContent = pt.bulletins;
    $ptEntries.textContent = pt.billable_entries;
    $ptExits.textContent = pt.billable_exits;
    $ptAbsences.textContent = pt.billable_absence_events;
    $ptAnomalies.textContent = pt.dsn_anomalies_count;

    renderNameList($ptEntriesNames, pt.billable_entry_names);
    renderNameList($ptExitsNames, pt.billable_exit_names);
    renderAbsenceDetails($ptAbsencesNames, pt.billable_absence_details);

    $ptScoreValue.textContent = pt.complexity_score;

    var inputs = pt.complexity_inputs || {};
    var keys = ["bulletins", "entries", "exits", "absence_events", "dsn_anomalies"];
    $ptScoreInputs.innerHTML = keys.map(function (key) {
      var val = inputs[key] || 0;
      var weight = COMPLEXITY_WEIGHTS[key] || 0;
      var label = COMPLEXITY_LABELS[key] || key;
      return '<tr>'
        + '<td>' + escapeHtml(label) + '</td>'
        + '<td class="mono">' + val + '</td>'
        + '<td class="mono">\u00d7' + weight + '</td>'
        + '<td class="mono">' + (val * weight) + '</td>'
        + '</tr>';
    }).join("");
  }

  // ── Contribution comparisons rendering ───────────────────

  function getActiveContributionPayload() {
    if (!state.data) return null;
    if (state.scope === "global") return state.data.global_contribution_comparisons || null;
    var est = state.data.establishments[state.activeEstIdx];
    return est ? (est.contribution_comparisons || null) : null;
  }

  function renderContributionComparisons() {
    var payload = getActiveContributionPayload() || {};
    var items = Array.isArray(payload.items) ? payload.items : [];

    $ccOkCount.textContent = payload.ok_count != null
      ? payload.ok_count
      : items.filter(function (item) { return item.status === "ok"; }).length;
    $ccMismatchCount.textContent = payload.mismatch_count != null
      ? payload.mismatch_count
      : items.filter(function (item) { return item.status === "ecart"; }).length;
    $ccWarningCount.textContent = payload.warning_count != null
      ? payload.warning_count
      : countComparisonWarnings(items);

    renderContributionFamilyTabs(items);
    renderContributionFamilyPanels(items);
  }

  function renderContributionFamilyTabs(items) {
    var countsByFamily = {};
    (items || []).forEach(function (item) {
      var family = item && item.family ? item.family : "";
      countsByFamily[family] = (countsByFamily[family] || 0) + 1;
    });

    $contribFamilyTabs.innerHTML = CONTRIBUTION_FAMILIES.map(function (family) {
      var active = family === state.activeContributionFamily;
      var count = countsByFamily[family] || 0;
      return '<button type="button" class="tab-bar__btn'
        + (active ? ' tab-bar__btn--active' : '')
        + '" data-family="' + escapeHtml(family) + '">'
        + escapeHtml(formatFamilyLabel(family))
        + ' <span class="mono">(' + count + ')</span>'
        + '</button>';
    }).join("");
  }

  function renderContributionFamilyPanels(items) {
    var byFamily = {};
    CONTRIBUTION_FAMILIES.forEach(function (family) {
      byFamily[family] = [];
    });

    (items || []).forEach(function (item) {
      var family = item && item.family ? item.family : "";
      if (!byFamily[family]) byFamily[family] = [];
      byFamily[family].push(item);
    });

    var html = CONTRIBUTION_FAMILIES.map(function (family) {
      var familyItems = byFamily[family] || [];
      var hidden = family !== state.activeContributionFamily;
      return '<section class="contrib-panel"' + (hidden ? ' hidden' : '') + '>'
        + renderContributionFamilyPanelContent(family, familyItems)
        + '</section>';
    }).join("");

    // Render unclassified items (family not in CONTRIBUTION_FAMILIES)
    var unclassifiedItems = [];
    (items || []).forEach(function (item) {
      if (item && item.family && CONTRIBUTION_FAMILIES.indexOf(item.family) === -1) {
        unclassifiedItems.push(item);
      }
    });
    if (unclassifiedItems.length > 0) {
      html += '<section class="contrib-panel">'
        + '<h3 class="data-section__title">Organismes non classifi\u00e9s (' + unclassifiedItems.length + ')</h3>'
        + '<div class="contrib-stack">' + unclassifiedItems.map(renderContributionItem).join("") + '</div>'
        + '</section>';
    }

    $contribFamilyPanels.innerHTML = html;
  }

  function renderContributionFamilyPanelContent(family, items) {
    if (!items || items.length === 0) {
      return '<div class="contrib-empty">'
        + '<strong>' + escapeHtml(formatFamilyLabel(family)) + '</strong>'
        + 'Aucune donn\u00e9e disponible pour cette famille dans le r\u00e9sultat courant.'
        + '</div>';
    }

    return '<div class="contrib-stack">' + items.map(renderContributionItem).join("") + '</div>';
  }

  function renderContributionItem(item) {
    var title = item.organism_label || item.organism_id || formatFamilyLabel(item.family);
    var meta = [];
    if (item.organism_id) meta.push("Organisme : " + item.organism_id);
    if (item.contract_ref) meta.push("Contrat : " + item.contract_ref);
    if (item.adhesion_id) meta.push("Adh\u00e9sion : " + item.adhesion_id);

    var warningList = collectComparisonWarnings(item);

    return '<article class="contrib-item">'
      + '<div class="contrib-item__header">'
      + '<div>'
      + '<div class="contrib-item__title">' + escapeHtml(title) + '</div>'
      + (meta.length > 0
        ? '<div class="contrib-item__meta">' + escapeHtml(meta.join(' · ')) + '</div>'
        : '')
      + '</div>'
      + '<span class="' + getStatusBadgeClass(item.status) + '">'
      + escapeHtml(formatStatusLabel(item.status))
      + '</span>'
      + '</div>'
      + renderContributionMetrics(item)
      + (warningList.length > 0 ? renderContributionWarnings(warningList) : '')
      + renderContributionDetailsTable(item)
      + '</article>';
  }

  function renderContributionMetrics(item) {
    var rows = [
      { label: "Agr\u00e9g\u00e9", value: formatAmount(item.aggregate_amount) },
      { label: "Bordereau", value: formatAmount(item.bordereau_amount) },
      { label: "Composant", value: formatAmount(item.component_amount) },
      { label: "Individuel", value: formatAmount(item.individual_amount) },
      { label: "\u0394 agr\u00e9g\u00e9 / bordereau", value: formatAmount(item.aggregate_vs_bordereau_delta) },
      { label: "\u0394 bordereau / composant", value: formatAmount(item.bordereau_vs_component_delta) },
      { label: "\u0394 agr\u00e9g\u00e9 / composant", value: formatAmount(item.aggregate_vs_component_delta) },
      { label: "\u0394 agr\u00e9g\u00e9 / individuel", value: formatAmount(item.aggregate_vs_individual_delta) },
    ];

    return '<div class="kv-grid">' + rows
      .filter(function (row) { return row.value !== "\u2014"; })
      .map(function (row) {
        return '<div class="kv-row">'
          + '<span class="kv-row__label">' + escapeHtml(row.label) + '</span>'
          + '<span class="kv-row__value">' + escapeHtml(row.value) + '</span>'
          + '</div>';
      }).join("") + '</div>';
  }

  function renderContributionWarnings(warnings) {
    return '<div class="contrib-warning">'
      + '<span class="contrib-warning__title">Vigilance</span>'
      + '<ul class="contrib-warning__list">'
      + warnings.map(function (warning) {
        return '<li>' + escapeHtml(String(warning)) + '</li>';
      }).join("")
      + '</ul>'
      + '</div>';
  }

  function renderUrssafDetailsTable(item) {
    var details = Array.isArray(item.details) ? item.details : [];
    var totalRows = details.length;
    var ecartRows = details.filter(function (d) {
      return !!d.rate_mismatch || !!d.amount_mismatch;
    }).length;
    var filterActive = state.contribFilterEcartsOnly;

    var visibleDetails = filterActive
      ? details.filter(function (d) { return !!d.rate_mismatch || !!d.amount_mismatch; })
      : details;

    var toolbar = '<div class="contrib-filter-toolbar">'
      + '<label class="contrib-filter-toggle">'
      + '<input type="checkbox" class="contrib-filter-toggle__input"'
      + ' data-action="toggle-ecarts-filter"'
      + (filterActive ? ' checked' : '') + '>'
      + '<span class="contrib-filter-toggle__label">Afficher uniquement les \u00e9carts</span>'
      + '</label>'
      + '<span class="contrib-filter-count">' + ecartRows + ' \u00e9cart(s) / ' + totalRows + ' lignes</span>'
      + '</div>';

    var body = visibleDetails.length === 0
      ? '<tr><td colspan="9" class="data-table__empty">Aucun d\u00e9tail disponible</td></tr>'
      : visibleDetails.map(function (detail) {
          var rmCls = detail.rate_mismatch ? ' cell-mismatch' : '';
          var amCls = detail.amount_mismatch ? ' cell-mismatch' : '';
          return '<tr>'
            + '<td class="mono">' + escapeHtml(detail.mapped_code || detail.ctp_code || "\u2014") + '</td>'
            + '<td>' + escapeHtml(detail.label || "\u2014") + '</td>'
            + '<td>' + escapeHtml(detail.assiette_label || detail.assiette_qualifier || "\u2014") + '</td>'
            + '<td class="mono">' + escapeHtml(formatAmount(detail.base_amount)) + '</td>'
            + '<td class="mono' + rmCls + '">' + escapeHtml(formatRate(detail.rate)) + '</td>'
            + '<td class="mono' + rmCls + '">' + escapeHtml(formatRate(detail.expected_rate)) + '</td>'
            + '<td class="mono' + amCls + '">' + escapeHtml(formatAmount(detail.declared_amount)) + '</td>'
            + '<td class="mono' + amCls + '">' + escapeHtml(formatAmount(detail.computed_amount)) + '</td>'
            + '<td><span class="' + getStatusBadgeClass(detail.status) + '">'
            + escapeHtml(formatDetailStatusLabel(detail))
            + '</span></td>'
            + '</tr>';
        }).join("");

    return toolbar
      + '<div class="contrib-details-wrap">'
      + '<table class="data-table contrib-details-table" style="margin-top: var(--sp-4);">'
      + '<thead><tr><th>Code DUCS</th><th>Libell\u00e9</th><th>Type d\u2019assiette</th><th>Assiette</th><th>Taux DSN</th><th>Taux ref</th><th>Montant DSN</th><th>Montant recalcul\u00e9</th><th>Statut</th></tr></thead>'
      + '<tbody>' + body + '</tbody>'
      + '</table>'
      + '</div>';
  }

  function renderContributionDetailsTable(item) {
    if (item && item.family === "urssaf") {
      return renderUrssafDetailsTable(item);
    }

    var details = Array.isArray(item.details) ? item.details : [];
    var body = details.length === 0
      ? '<tr><td colspan="5" class="data-table__empty">Aucun d\u00e9tail disponible</td></tr>'
      : details.map(function (detail) {
          return '<tr>'
            + '<td class="mono">' + escapeHtml(detail.key || "\u2014") + '</td>'
            + '<td>' + escapeHtml(detail.label || "\u2014") + '</td>'
            + '<td class="mono">' + escapeHtml(formatAmount(detail.declared_amount)) + '</td>'
            + '<td class="mono">' + escapeHtml(formatAmount(detail.computed_amount)) + '</td>'
            + '<td><span class="' + getStatusBadgeClass(detail.status) + '">'
            + escapeHtml(formatStatusLabel(detail.status))
            + '</span></td>'
            + '</tr>';
        }).join("");

    return '<div class="contrib-details-wrap">'
      + '<table class="data-table contrib-details-table" style="margin-top: var(--sp-4);">'
      + '<thead><tr><th>Cl\u00e9</th><th>Libell\u00e9</th><th>D\u00e9clar\u00e9</th><th>Calcul\u00e9</th><th>Statut</th></tr></thead>'
      + '<tbody>' + body + '</tbody>'
      + '</table>'
      + '</div>';
  }

  // ── Client-side file validation ──────────────────────────

  function isDsnFile(file) {
    var name = file && file.name ? file.name.toLowerCase() : "";
    return name.endsWith(".dsn") || name.endsWith(".txt");
  }

  var errorTimer = null;

  function showDropzoneError(msg) {
    $dropzoneError.textContent = msg;
    if (errorTimer) clearTimeout(errorTimer);
    errorTimer = setTimeout(function () {
      $dropzoneError.textContent = "";
      errorTimer = null;
    }, 3000);
  }

  function clearDropzoneError() {
    if (errorTimer) {
      clearTimeout(errorTimer);
      errorTimer = null;
    }
    $dropzoneError.textContent = "";
  }

  // ── Upload ───────────────────────────────────────────────

  function handleFile(file) {
    if (!isDsnFile(file)) {
      showDropzoneError("Seuls les fichiers .dsn ou .txt sont accept\u00e9s");
      return;
    }
    clearDropzoneError();
    upload(file);
  }

  async function upload(file) {
    setState({ phase: "uploading" });

    var form = new FormData();
    form.append("file", file);

    try {
      var res = await fetch("/api/extract", { method: "POST", body: form });
      var json = await res.json();

      if (!res.ok) {
        setState({
          phase: "error",
          error: { detail: json.detail || "\u00c9chec du chargement", warnings: json.warnings || [] },
        });
        return;
      }

      setState({ phase: "results", data: json, scope: "global", activeEstIdx: 0 });
    } catch (err) {
      setState({
        phase: "error",
        error: { detail: "Erreur r\u00e9seau\u00a0: " + err.message, warnings: [] },
      });
    }
  }

  // ── Reset ────────────────────────────────────────────────

  function reset() {
    $fileInput.value = "";
    clearDropzoneError();
    setState({
      phase: "empty",
      data: null,
      error: null,
      scope: "global",
      activeEstIdx: 0,
      activeContributionFamily: "urssaf",
      activePage: "controle",
      contribFilterEcartsOnly: false,
    });
  }

  // ── Event listeners ──────────────────────────────────────

  // Drag and drop
  var dragCounter = 0;

  $dropzone.addEventListener("dragenter", function (e) {
    e.preventDefault();
    dragCounter++;
    $dropzone.classList.add("dropzone--active");
  });

  $dropzone.addEventListener("dragover", function (e) {
    e.preventDefault();
  });

  $dropzone.addEventListener("dragleave", function (e) {
    e.preventDefault();
    dragCounter--;
    if (dragCounter <= 0) {
      dragCounter = 0;
      $dropzone.classList.remove("dropzone--active");
    }
  });

  $dropzone.addEventListener("drop", function (e) {
    e.preventDefault();
    dragCounter = 0;
    $dropzone.classList.remove("dropzone--active");
    var files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
  });

  // Browse button
  $browseBtn.addEventListener("click", function () {
    $fileInput.click();
  });

  // File input
  $fileInput.addEventListener("change", function () {
    if ($fileInput.files.length > 0) handleFile($fileInput.files[0]);
  });

  // Page navigation
  document.querySelectorAll(".page-nav__btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var page = btn.dataset.page;
      if (page && page !== state.activePage) {
        setState({ activePage: page });
      }
    });
  });

  // Scope toggle
  document.querySelectorAll(".scope-toggle__btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var newScope = btn.dataset.scope;
      if (newScope === state.scope) return;
      if (newScope === "establishment" && state.data && state.data.establishments.length === 0) return;
      setState({ scope: newScope, activeEstIdx: 0 });
    });
  });

  // Establishment tabs (event delegation)
  $establishmentTabs.addEventListener("click", function (e) {
    var btn = e.target.closest(".tab-bar__btn");
    if (!btn) return;
    var idx = parseInt(btn.dataset.index, 10);
    if (idx !== state.activeEstIdx) {
      setState({ activeEstIdx: idx });
    }
  });

  $contribFamilyTabs.addEventListener("click", function (e) {
    var btn = e.target.closest(".tab-bar__btn");
    if (!btn) return;
    var family = btn.dataset.family;
    if (!family || family === state.activeContributionFamily) return;
    setState({ activeContributionFamily: family });
  });

  $contribFamilyPanels.addEventListener("change", function (e) {
    if (e.target && e.target.dataset && e.target.dataset.action === "toggle-ecarts-filter") {
      setState({ contribFilterEcartsOnly: e.target.checked });
    }
  });

  // Reset buttons
  document.querySelectorAll('[data-action="reset"]').forEach(function (btn) {
    btn.addEventListener("click", reset);
  });

  // Also allow clicking the whole dropzone to trigger file picker
  $dropzone.addEventListener("click", function (e) {
    if (e.target === $browseBtn || e.target === $fileInput) return;
    if (state.phase === "empty") $fileInput.click();
  });

  // ── Theme toggle ────────────────────────────────────────

  var $themeToggle = document.getElementById("theme-toggle");
  $themeToggle.addEventListener("click", function () {
    var isLight = document.documentElement.getAttribute("data-theme") === "light";
    if (isLight) {
      document.documentElement.removeAttribute("data-theme");
      localStorage.removeItem("dsn-theme");
    } else {
      document.documentElement.setAttribute("data-theme", "light");
      localStorage.setItem("dsn-theme", "light");
    }
  });

  // Initial render
  render();

})();
