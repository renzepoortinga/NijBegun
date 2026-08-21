/* Ventilatieplan-tekening (taak 020): sleepbare markers op de plattegrond, vanilla JS, geen framework.
   Bootstrap-data komt uit de pagina zelf (window.VP_TAG / VP_MARKER_TYPES / VP_VERDIEPINGEN, zie de
   VENTILATIEPLAN_TMPL in dashboard/app.py). Elke wijziging (slepen/draaien/waarde/toevoegen/verwijderen)
   stuurt de VOLLEDIGE markerlijst van die ene verdieping naar de server (POST .../markers) — de server
   is de waarheid, dit script tekent alleen en houdt de UI in de tussentijd bij.
   Ruimtepolygonen komen uitsluitend uit expliciete dossiergeometrie. Zonder die geometrie wordt slepen
   geblokkeerd; het script verzint nooit ruimtevormen. */
(function () {
  "use strict";
  var KLEUR = { toevoer: "var(--blue)", afvoer: "var(--orange)", overstroom: "var(--green)" };
  var SLEEP_DREMPEL_PX = 4;   // minder beweging dan dit = klik (draaien), niet slepen

  function svgEl(tag, attrs) {
    var e = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }

  function markerVorm(type) {
    if (type === "afvoer") return svgEl("ellipse", { cx: 0, cy: 0, rx: 34, ry: 26, fill: KLEUR.afvoer });
    // toevoer + overstroom: pijl-driehoek, overstroom iets kleiner
    var s = type === "overstroom" ? 26 : 34;
    return svgEl("path", { d: "M0 " + (-s) + " L" + s + " " + s + " L" + (-s) + " " + s + " Z", fill: KLEUR[type] });
  }

  function teken(verdieping) {
    var svg = document.querySelector('.vp-canvas[data-verdieping="' + cssEsc(verdieping.naam) + '"]');
    if (!svg) return;
    var laag = svg.querySelector(".vp-markers");
    while (laag.firstChild) laag.removeChild(laag.firstChild);
    verdieping.markers.forEach(function (m) {
      var g = svgEl("g", {
        "class": "vp-marker", "data-id": m.id, "data-type": m.type,
        tabindex: "0", role: "button", "aria-label": m.type + " " + m.waarde_ls.toFixed(1)
          + " liter per seconde, ruimte " + m.ruimte_id,
        transform: "translate(" + (m.x * 1000) + " " + (m.y * 750) + ") rotate(" + (m.rotatie || 0) + ")"
      });
      g.appendChild(markerVorm(m.type));
      var t = svgEl("text", { x: 0, y: 9 });
      t.textContent = (Math.round(m.waarde_ls * 10) / 10).toFixed(1);
      g.appendChild(t);
      if (m.bron === "auto") g.setAttribute("opacity", "0.75");
      laag.appendChild(g);
      bindMarker(g, verdieping);
    });
  }

  function cssEsc(s) { return (window.CSS && CSS.escape) ? CSS.escape(s) : s.replace(/["\\]/g, "\\$&"); }

  function vindMarker(verdieping, id) {
    for (var i = 0; i < verdieping.markers.length; i++) if (verdieping.markers[i].id === id) return verdieping.markers[i];
    return null;
  }

  function puntInPolygoon(x, y, punten) {
    var binnen = false;
    for (var i = 0, j = punten.length - 1; i < punten.length; j = i++) {
      var xi = punten[i][0], yi = punten[i][1], xj = punten[j][0], yj = punten[j][1];
      if (((yi > y) !== (yj > y)) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) binnen = !binnen;
    }
    return binnen;
  }

  function ruimteOpPunt(verdieping, x, y) {
    for (var i = 0; i < verdieping.ruimtes.length; i++) {
      var r = verdieping.ruimtes[i];
      if (r.contour && r.contour.length >= 3 && puntInPolygoon(x, y, r.contour)) return r;
    }
    return null;
  }

  function sleepIndicatie(svg, ruimte, x, y) {
    [].slice.call(svg.querySelectorAll(".vp-ruimte,.vp-ruimtelabel")).forEach(function (n) {
      n.classList.toggle("vp-actief", !!ruimte && n.dataset.ruimteId === ruimte.naam);
    });
    var lijn = svg.querySelector(".vp-koppellijn");
    if (!lijn) return;
    if (!ruimte) { lijn.classList.remove("vp-zichtbaar"); return; }
    lijn.setAttribute("x1", x * 1000); lijn.setAttribute("y1", y * 750);
    lijn.setAttribute("x2", ruimte.label[0] * 1000); lijn.setAttribute("y2", ruimte.label[1] * 750);
    lijn.classList.add("vp-zichtbaar");
  }

  function opslaan(verdieping) {
    return fetch("/project/" + encodeURIComponent(window.VP_TAG) + "/ventilatieplan/"
        + encodeURIComponent(verdieping.naam) + "/markers", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markers: verdieping.markers })
    }).then(function (r) { return r.json().then(function (d) { return { status: r.status, data: d }; }); })
      .then(function (res) {
        if (!res.data.ok) {
          alert(res.data.fout || "Opslaan mislukt.");
          return false;
        }
        toonBalans(res.data.balans);
        return true;
      }).catch(function () { alert("Opslaan mislukt (geen verbinding)."); return false; });
  }

  function herbereken() {
    var toevoer = 0, afvoer = 0;
    window.VP_VERDIEPINGEN.forEach(function (v) {
      v.markers.forEach(function (m) {
        if (m.type === "toevoer") toevoer += m.waarde_ls;
        else if (m.type === "afvoer") afvoer += m.waarde_ls;
      });
    });
    toonBalans({ toevoer: Math.round(toevoer * 10) / 10, afvoer: Math.round(afvoer * 10) / 10,
                sluitend: Math.abs(toevoer - afvoer) < 0.05 });
  }

  function toonBalans(balans) {
    var pil = document.getElementById("vp-balans");
    if (!pil) return;
    pil.className = "pill " + (balans.sluitend ? "green" : "amber");
    pil.textContent = "Balans: toevoer " + balans.toevoer.toFixed(1) + " l/s "
        + (balans.sluitend ? "=" : "\u2260") + " afvoer " + balans.afvoer.toFixed(1) + " l/s";
  }

  function bindMarker(g, verdieping) {
    var slepend = false, start = null, verplaatst = false, svg = g.ownerSVGElement, vorige = null;
    g.addEventListener("pointerdown", function (ev) {
      ev.preventDefault();
      slepend = true; verplaatst = false;
      start = { px: ev.clientX, py: ev.clientY };
      var huidig = vindMarker(verdieping, g.dataset.id);
      vorige = { x: huidig.x, y: huidig.y, ruimte_id: huidig.ruimte_id, bron: huidig.bron };
      g.setPointerCapture(ev.pointerId);
      g.classList.add("vp-dragging");
    });
    g.addEventListener("pointermove", function (ev) {
      if (!slepend) return;
      var dx = ev.clientX - start.px, dy = ev.clientY - start.py;
      if (Math.abs(dx) > SLEEP_DREMPEL_PX || Math.abs(dy) > SLEEP_DREMPEL_PX) verplaatst = true;
      if (!verplaatst) return;
      if (!verdieping.heeft_ruimtegeometrie) return;
      var rect = svg.getBoundingClientRect();
      var x = Math.min(1, Math.max(0, (ev.clientX - rect.left) / rect.width));
      var y = Math.min(1, Math.max(0, (ev.clientY - rect.top) / rect.height));
      var m = vindMarker(verdieping, g.dataset.id);
      m.x = Math.round(x * 10000) / 10000; m.y = Math.round(y * 10000) / 10000; m.bron = "handmatig";
      var ruimte = ruimteOpPunt(verdieping, m.x, m.y);
      if (ruimte) m.ruimte_id = ruimte.naam;
      sleepIndicatie(svg, ruimte, m.x, m.y);
      g.setAttribute("transform", "translate(" + (m.x * 1000) + " " + (m.y * 750) + ") rotate(" + (m.rotatie || 0) + ")");
    });
    g.addEventListener("pointerup", function (ev) {
      if (!slepend) return;
      slepend = false; g.classList.remove("vp-dragging");
      try { g.releasePointerCapture(ev.pointerId); } catch (e) {}
      var m = vindMarker(verdieping, g.dataset.id);
      if (verplaatst) {
        if (!verdieping.heeft_ruimtegeometrie) {
          alert("Slepen kan pas nadat gemeten ruimtecontouren beschikbaar zijn.");
          return;
        }
        var ruimte = ruimteOpPunt(verdieping, m.x, m.y);
        sleepIndicatie(svg, null, 0, 0);
        if (!ruimte) {
          m.x = vorige.x; m.y = vorige.y; m.ruimte_id = vorige.ruimte_id; m.bron = vorige.bron;
          teken(verdieping);
          alert("Laat de marker binnen een gemeten ruimte los.");
          return;
        }
        m.ruimte_id = ruimte.naam;
        opslaan(verdieping).then(function (ok) { if (!ok) { Object.assign(m, vorige); teken(verdieping); } });
      } else {
        // geen beweging = klik -> 90 graden draaien
        m.rotatie = ((m.rotatie || 0) + 90) % 360; m.bron = "handmatig";
        g.setAttribute("transform", "translate(" + (m.x * 1000) + " " + (m.y * 750) + ") rotate(" + m.rotatie + ")");
        opslaan(verdieping);
      }
    });
    function bewerkMarker() {
      var m = vindMarker(verdieping, g.dataset.id);
      var antwoord = window.prompt("Nieuwe waarde in l/s. Splits met + (bijvoorbeeld 10+11); leeg verwijdert:", m.waarde_ls.toFixed(1));
      if (antwoord === null) return;                 // geannuleerd
      antwoord = antwoord.trim().replace(",", ".");
      if (antwoord === "") {
        verdieping.markers = verdieping.markers.filter(function (x) { return x.id !== m.id; });
        teken(verdieping); opslaan(verdieping);
        return;
      }
      var delen = antwoord.split("+").map(function (deel) { return parseFloat(deel.trim()); });
      if (delen.length > 2 || delen.some(function (waarde) { return isNaN(waarde) || waarde < 0; })) {
        alert("Gebruik één waarde of twee waarden gescheiden door +."); return;
      }
      m.waarde_ls = Math.round(delen[0] * 10) / 10; m.bron = "handmatig";
      if (delen.length === 2) {
        verdieping.markers.push({ id: "s" + Date.now().toString(36), type: m.type,
          ruimte_id: m.ruimte_id, waarde_ls: Math.round(delen[1] * 10) / 10,
          x: m.x, y: m.y, rotatie: m.rotatie,
          bron: "handmatig" });
      }
      teken(verdieping); opslaan(verdieping);
    }
    g.addEventListener("dblclick", function (ev) {
      ev.preventDefault(); bewerkMarker();
    });
    g.addEventListener("keydown", function (ev) {
      var m = vindMarker(verdieping, g.dataset.id);
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); bewerkMarker(); return; }
      if (ev.key === "Delete" || ev.key === "Backspace") {
        ev.preventDefault();
        if (window.confirm("Marker " + m.type + " uit " + m.ruimte_id + " verwijderen?")) {
          verdieping.markers = verdieping.markers.filter(function (x) { return x.id !== m.id; });
          teken(verdieping); opslaan(verdieping);
        }
        return;
      }
      var stap = ev.shiftKey ? 0.02 : 0.005, dx = 0, dy = 0;
      if (ev.key === "ArrowLeft") dx = -stap; else if (ev.key === "ArrowRight") dx = stap;
      else if (ev.key === "ArrowUp") dy = -stap; else if (ev.key === "ArrowDown") dy = stap; else return;
      ev.preventDefault();
      if (!verdieping.heeft_ruimtegeometrie) { alert("Toetsenbordverplaatsing vereist gemeten ruimtecontouren."); return; }
      var nx = Math.max(0, Math.min(1, m.x + dx)), ny = Math.max(0, Math.min(1, m.y + dy));
      var ruimte = ruimteOpPunt(verdieping, nx, ny);
      if (!ruimte) return;
      m.x = Math.round(nx * 10000) / 10000; m.y = Math.round(ny * 10000) / 10000;
      m.ruimte_id = ruimte.naam; m.bron = "handmatig";
      teken(verdieping); opslaan(verdieping);
    });
  }

  function initKalibratie(verdieping) {
    var svg = document.querySelector('.vp-canvas[data-verdieping="' + cssEsc(verdieping.naam) + '"]');
    var punten = {}, actief = null;
    verdieping.ruimtes.forEach(function (r) { if (r.contour) punten[r.naam] = r.contour.slice(); });
    function status(tekst) {
      var n = document.querySelector('.vp-kalibratie-status[data-verdieping="' + cssEsc(verdieping.naam) + '"]');
      if (n) n.textContent = tekst;
    }
    var start = document.querySelector('.vp-kalibratie-start[data-verdieping="' + cssEsc(verdieping.naam) + '"]');
    if (!start || !svg) return;
    start.addEventListener("click", function () {
      var select = document.querySelector('.vp-kalibratie-ruimte[data-verdieping="' + cssEsc(verdieping.naam) + '"]');
      actief = select.value; punten[actief] = []; status("Klik minimaal drie hoekpunten voor " + actief + ".");
    });
    svg.addEventListener("click", function (ev) {
      if (!actief || ev.target.closest(".vp-marker")) return;
      var rect = svg.getBoundingClientRect();
      punten[actief].push([Math.round((ev.clientX - rect.left) / rect.width * 10000) / 10000,
                           Math.round((ev.clientY - rect.top) / rect.height * 10000) / 10000]);
      var preview = svg.querySelector(".vp-kalibratie-preview") || svg.appendChild(svgEl("polyline", {"class":"vp-kalibratie-preview"}));
      preview.setAttribute("points", punten[actief].map(function (p) { return (p[0]*1000)+","+(p[1]*750); }).join(" "));
      status(punten[actief].length + " punten voor " + actief + ".");
    });
    document.querySelector('.vp-kalibratie-wis[data-verdieping="' + cssEsc(verdieping.naam) + '"]').addEventListener("click", function () {
      if (actief) punten[actief] = []; var p = svg.querySelector(".vp-kalibratie-preview"); if (p) p.remove(); status("Punten gewist.");
    });
    document.querySelector('.vp-kalibratie-save[data-verdieping="' + cssEsc(verdieping.naam) + '"]').addEventListener("click", function () {
      if (Object.keys(punten).some(function (naam) { return punten[naam].length < 3; })) { status("Elke getekende ruimte heeft minimaal drie punten nodig."); return; }
      fetch("/project/" + encodeURIComponent(window.VP_TAG) + "/ventilatieplan/" + encodeURIComponent(verdieping.naam) + "/ruimtepolygonen",
        {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({polygonen:punten})})
        .then(function(r){return r.json();}).then(function(data){ if(!data.ok){status(data.fout);return;} window.location.reload(); })
        .catch(function(){status("Opslaan mislukt (geen verbinding).");});
    });
  }

  function nieuweMarker(verdieping, type, ruimteNaam) {
    var ruimte = null;
    for (var i = 0; i < verdieping.ruimtes.length; i++) if (verdieping.ruimtes[i].naam === ruimteNaam) ruimte = verdieping.ruimtes[i];
    if (!ruimte) { alert("Kies eerst een ruimte."); return; }
    var waarde = type === "toevoer" ? (ruimte.toevoer || 7.0) : (type === "afvoer" ? (ruimte.afvoer || 7.0) : 0.0);
    var id = "n" + Date.now().toString(36) + Math.floor(Math.random() * 1000);
    verdieping.markers.push({ id: id, type: type, ruimte_id: ruimte.naam, waarde_ls: waarde,
                              x: ruimte.label[0], y: ruimte.label[1], rotatie: 0, bron: "handmatig" });
    teken(verdieping); opslaan(verdieping);
  }

  function verdiepingBijNaam(naam) {
    for (var i = 0; i < window.VP_VERDIEPINGEN.length; i++) if (window.VP_VERDIEPINGEN[i].naam === naam) return window.VP_VERDIEPINGEN[i];
    return null;
  }

  window.ventilatieplanInit = function () {
    window.VP_VERDIEPINGEN.forEach(teken);
    window.VP_VERDIEPINGEN.forEach(initKalibratie);

    [].slice.call(document.querySelectorAll(".vp-add")).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var verdieping = verdiepingBijNaam(btn.dataset.verdieping);
        var kiezer = document.querySelector('.vp-ruimte-kiezer[data-verdieping="' + cssEsc(btn.dataset.verdieping) + '"]');
        if (!verdieping || !kiezer || !kiezer.value) { alert("Kies eerst een ruimte."); return; }
        nieuweMarker(verdieping, btn.dataset.type, kiezer.value);
      });
    });

    [].slice.call(document.querySelectorAll(".vp-herstel")).forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (!window.confirm("Automatische plaatsing terugzetten voor deze verdieping? Handmatige wijzigingen op déze verdieping gaan verloren.")) return;
        fetch("/project/" + encodeURIComponent(window.VP_TAG) + "/ventilatieplan/"
            + encodeURIComponent(btn.dataset.verdieping) + "/herstel", { method: "POST" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (!data.ok) { alert(data.fout || "Herstellen mislukt."); return; }
            var verdieping = verdiepingBijNaam(btn.dataset.verdieping);
            verdieping.markers = data.markers;
            teken(verdieping);
            toonBalans(data.balans);
          }).catch(function () { alert("Herstellen mislukt (geen verbinding)."); });
      });
    });

    var herbeerknop = document.getElementById("vp-herbereken");
    if (herbeerknop) herbeerknop.addEventListener("click", herbereken);
    [].slice.call(document.querySelectorAll(".vp-topologie-save")).forEach(function(btn){
      btn.addEventListener("click", function(){
        var naam=btn.dataset.verdieping, bron=document.querySelector('.vp-topologie-bron[data-verdieping="'+cssEsc(naam)+'"]').value;
        var doel=document.querySelector('.vp-topologie-doel[data-verdieping="'+cssEsc(naam)+'"]').value;
        fetch("/project/"+encodeURIComponent(window.VP_TAG)+"/ventilatieplan/"+encodeURIComponent(naam)+"/topologie",
          {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({bron:bron,doel:doel})})
          .then(function(r){return r.json();}).then(function(data){if(!data.ok){alert(data.fout);return;} var v=verdiepingBijNaam(naam);v.markers=data.markers;teken(v);toonBalans(data.balans);})
          .catch(function(){alert("Verbinding opslaan mislukt.");});
      });
    });
  };
})();
