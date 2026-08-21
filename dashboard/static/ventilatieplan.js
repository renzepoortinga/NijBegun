/* Ventilatieplan-tekening (taak 020): sleepbare markers op de plattegrond, vanilla JS, geen framework.
   Bootstrap-data komt uit de pagina zelf (window.VP_TAG / VP_MARKER_TYPES / VP_VERDIEPINGEN, zie de
   VENTILATIEPLAN_TMPL in dashboard/app.py). Elke wijziging (slepen/draaien/waarde/toevoegen/verwijderen)
   stuurt de VOLLEDIGE markerlijst van die ene verdieping naar de server (POST .../markers) — de server
   is de waarheid, dit script tekent alleen en houdt de UI in de tussentijd bij.
   'Splitsen' (één marker in twee opsplitsen) zit NIET in deze versie — dubbelklik met een lege waarde
   verwijdert de marker, dat dekt de acceptatiecriteria van taak 020 (wijzigen + verwijderen). */
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
    var slepend = false, start = null, verplaatst = false, svg = g.ownerSVGElement;
    g.addEventListener("pointerdown", function (ev) {
      ev.preventDefault();
      slepend = true; verplaatst = false;
      start = { px: ev.clientX, py: ev.clientY };
      g.setPointerCapture(ev.pointerId);
      g.classList.add("vp-dragging");
    });
    g.addEventListener("pointermove", function (ev) {
      if (!slepend) return;
      var dx = ev.clientX - start.px, dy = ev.clientY - start.py;
      if (Math.abs(dx) > SLEEP_DREMPEL_PX || Math.abs(dy) > SLEEP_DREMPEL_PX) verplaatst = true;
      if (!verplaatst) return;
      var rect = svg.getBoundingClientRect();
      var x = Math.min(1, Math.max(0, (ev.clientX - rect.left) / rect.width));
      var y = Math.min(1, Math.max(0, (ev.clientY - rect.top) / rect.height));
      var m = vindMarker(verdieping, g.dataset.id);
      m.x = Math.round(x * 10000) / 10000; m.y = Math.round(y * 10000) / 10000; m.bron = "handmatig";
      g.setAttribute("transform", "translate(" + (m.x * 1000) + " " + (m.y * 750) + ") rotate(" + (m.rotatie || 0) + ")");
    });
    g.addEventListener("pointerup", function (ev) {
      if (!slepend) return;
      slepend = false; g.classList.remove("vp-dragging");
      try { g.releasePointerCapture(ev.pointerId); } catch (e) {}
      var m = vindMarker(verdieping, g.dataset.id);
      if (verplaatst) {
        opslaan(verdieping);
      } else {
        // geen beweging = klik -> 90 graden draaien
        m.rotatie = ((m.rotatie || 0) + 90) % 360; m.bron = "handmatig";
        g.setAttribute("transform", "translate(" + (m.x * 1000) + " " + (m.y * 750) + ") rotate(" + m.rotatie + ")");
        opslaan(verdieping);
      }
    });
    g.addEventListener("dblclick", function (ev) {
      ev.preventDefault();
      var m = vindMarker(verdieping, g.dataset.id);
      var antwoord = window.prompt("Nieuwe waarde in l/s (leeg = marker verwijderen):", m.waarde_ls.toFixed(1));
      if (antwoord === null) return;                 // geannuleerd
      antwoord = antwoord.trim().replace(",", ".");
      if (antwoord === "") {
        verdieping.markers = verdieping.markers.filter(function (x) { return x.id !== m.id; });
        teken(verdieping); opslaan(verdieping);
        return;
      }
      var waarde = parseFloat(antwoord);
      if (isNaN(waarde) || waarde < 0) { alert("Geen geldig getal."); return; }
      m.waarde_ls = Math.round(waarde * 10) / 10; m.bron = "handmatig";
      teken(verdieping); opslaan(verdieping);
    });
  }

  function nieuweMarker(verdieping, type, ruimteNaam) {
    var ruimte = null;
    for (var i = 0; i < verdieping.ruimtes.length; i++) if (verdieping.ruimtes[i].naam === ruimteNaam) ruimte = verdieping.ruimtes[i];
    if (!ruimte) { alert("Kies eerst een ruimte."); return; }
    var waarde = type === "toevoer" ? (ruimte.toevoer || 7.0) : (type === "afvoer" ? (ruimte.afvoer || 7.0) : 0.0);
    var id = "n" + Date.now().toString(36) + Math.floor(Math.random() * 1000);
    verdieping.markers.push({ id: id, type: type, ruimte_id: ruimte.naam, waarde_ls: waarde,
                              x: 0.5, y: 0.5, rotatie: 0, bron: "handmatig" });
    teken(verdieping); opslaan(verdieping);
  }

  function verdiepingBijNaam(naam) {
    for (var i = 0; i < window.VP_VERDIEPINGEN.length; i++) if (window.VP_VERDIEPINGEN[i].naam === naam) return window.VP_VERDIEPINGEN[i];
    return null;
  }

  window.ventilatieplanInit = function () {
    window.VP_VERDIEPINGEN.forEach(teken);

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
  };
})();
