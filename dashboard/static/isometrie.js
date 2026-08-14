(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg", COS30 = Math.sqrt(3) / 2, SIN30 = 0.5;

  function n(value) {
    var parsed = parseFloat(String(value || "").replace(",", "."));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function project(point) {
    return {x: (point.x - point.z) * COS30, y: (point.x + point.z) * SIN30 - point.y};
  }

  function el(name, attrs, text) {
    var node = document.createElementNS(NS, name);
    Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); });
    if (text) node.textContent = text;
    return node;
  }

  function polygon(points, kind) {
    var node = el("polygon", {"data-face": kind || "vlak"});
    node._points3d = points;
    return node;
  }

  function block(width, depth, height) {
    var a = {x: 0, y: 0, z: 0}, b = {x: width, y: 0, z: 0};
    var c = {x: width, y: 0, z: depth}, d = {x: 0, y: 0, z: depth};
    var at = {x: 0, y: height, z: 0}, bt = {x: width, y: height, z: 0};
    var ct = {x: width, y: height, z: depth}, dt = {x: 0, y: height, z: depth};
    return [polygon([a, b, bt, at], "voor"), polygon([b, c, ct, bt], "zij"),
      polygon([at, bt, ct, dt], "boven")];
  }

  function slope(points, kind) { return polygon(points, kind || "hellend"); }

  // Zelfde 'zon' en shading-formule als dashboard/gebouw_svg.py:_shade — puur een CSS
  // brightness()-filter bovenop de bestaande kleurtokens (geen hex), zodat de wizard-previews
  // en het definitieve gebouwoverzicht dezelfde visuele diepte krijgen. Vlakken zijn hier steeds
  // 'onder-links, onder-rechts, boven-rechts, boven-links' (of een driehoek) opgebouwd; cross van
  // de tweede rand op de eerste geeft de naar-buiten-wijzende normaal.
  var ZON = {x: -0.25, y: 0.85, z: -0.45};
  function shade(points3d) {
    if (points3d.length < 3) return 1;
    var p0 = points3d[0], p1 = points3d[1], p2 = points3d[2];
    var ax = p1.x - p0.x, ay = p1.y - p0.y, az = p1.z - p0.z;
    var bx = p2.x - p0.x, by = p2.y - p0.y, bz = p2.z - p0.z;
    var nx = by * az - bz * ay, ny = bz * ax - bx * az, nz = bx * ay - by * ax;
    var lengte = Math.sqrt(nx * nx + ny * ny + nz * nz);
    if (lengte < 1e-9) return 1;
    var dot = (nx * ZON.x + ny * ZON.y + nz * ZON.z) / lengte;
    return Math.max(0.6, Math.min(1.15, 0.90 + 0.20 * dot));
  }

  function draw(svg, faces, label) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    var projected = [];
    faces.forEach(function (face) {
      face._points3d.forEach(function (point) { projected.push(project(point)); });
    });
    var xs = projected.map(function (p) { return p.x; }), ys = projected.map(function (p) { return p.y; });
    var minX = Math.min.apply(null, xs), maxX = Math.max.apply(null, xs);
    var minY = Math.min.apply(null, ys), maxY = Math.max.apply(null, ys);
    var scale = Math.min(260 / Math.max(1, maxX - minX), 150 / Math.max(1, maxY - minY));
    function screen(point) {
      var p = project(point);
      return ((p.x - (minX + maxX) / 2) * scale + 160).toFixed(1) + "," +
        ((p.y - (minY + maxY) / 2) * scale + 100).toFixed(1);
    }
    faces.forEach(function (face) {
      face.setAttribute("points", face._points3d.map(screen).join(" "));
      face.setAttribute("fill", face.getAttribute("data-face") === "boven" ? "var(--info-bg)" : "var(--tint2)");
      face.setAttribute("stroke", face.getAttribute("data-face").indexOf("actief") >= 0 ? "var(--orange)" : "var(--blue)");
      face.setAttribute("stroke-width", "2");
      face.setAttribute("stroke-linejoin", "round");
      face.setAttribute("filter", "brightness(" + shade(face._points3d).toFixed(3) + ")");
      svg.appendChild(face);
    });
    svg.appendChild(el("text", {x: "160", y: "207", "text-anchor": "middle",
      fill: "var(--ink)", "font-size": "var(--svg-fs-3)"}, label));
  }

  function empty(svg, text, color) {
    if (!svg) return;
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.appendChild(el("text", {x: "160", y: "110", "text-anchor": "middle",
      fill: color || "var(--sub)", "font-size": "var(--svg-fs-3)"}, text));
  }

  window.platDakPrev = function (form) {
    var width = n(form.breedte.value), depth = n(form.diepte.value), svg = document.getElementById("platSvg");
    if (!(width > 0 && depth > 0)) return empty(svg, "Vul breedte en diepte in");
    draw(svg, block(width, depth, Math.max(width, depth) * 0.06),
      width.toFixed(2) + " × " + depth.toFixed(2) + " m · " + (width * depth).toFixed(2) + " m²");
  };

  window.dakPrev = function (form) {
    var depth = n(form.lange_zijde.value), width = n(form.breedte.value), angle = n(form.helling1.value);
    var angle2 = n(form.helling2.value) || angle, svg = document.getElementById("zadelSvg");
    var info = document.getElementById("dakprev");
    if (!(depth > 0 && width > 0 && angle > 0 && angle < 90 && angle2 > 0 && angle2 < 90)) {
      if (info) info.textContent = "Vul lange zijde, breedte en hellingshoek in voor een voorbeeld.";
      return empty(svg, "Vul de dakmaten in");
    }
    var tan1 = Math.tan(angle * Math.PI / 180), tan2 = Math.tan(angle2 * Math.PI / 180);
    var ridge = depth / (1 / tan1 + 1 / tan2), run1 = ridge / tan1;
    var a = {x: 0, y: 0, z: 0}, b = {x: width, y: 0, z: 0};
    var c = {x: width, y: 0, z: depth}, d = {x: 0, y: 0, z: depth};
    var r1 = {x: 0, y: ridge, z: run1}, r2 = {x: width, y: ridge, z: run1};
    var faces = [slope([a, b, r2, r1], "hellend-actief"), slope([r1, r2, c, d], "hellend"),
      slope([a, r1, d], "kop"), slope([b, c, r2], "kop")];
    var slopeLength = run1 / Math.cos(angle * Math.PI / 180), area = slopeLength * width;
    if (info) info.innerHTML = "Voorbeeld: eerste hellende vlak <b>" + area.toFixed(2) +
      " m²</b>; de tekening volgt beide hellingshoeken en alle ingevoerde maten.";
    draw(svg, faces, width.toFixed(2) + " × " + depth.toFixed(2) + " m · " + angle.toFixed(0) + "° / " + angle2.toFixed(0) + "°");
  };

  window.kapelPrev = function (form) {
    var width = n(form.breedte.value), height = n(form.hoogte.value), depth = n(form.diepte.value);
    var svg = document.getElementById("kapelSvg"), info = document.getElementById("kapelprev");
    if (!(width > 0 && height > 0 && depth > 0)) {
      if (info) info.textContent = "Vul breedte, hoogte en diepte in.";
      return empty(svg, "Vul breedte, hoogte en diepte in");
    }
    var selected = form.moederdak_i && form.moederdak_i.options[form.moederdak_i.selectedIndex];
    var angle = selected ? n(selected.getAttribute("data-helling")) : 45;
    if (!(angle > 0 && angle < 90)) angle = 45;
    var roofWidth = width * 2.2, roofDepth = depth * 3.2, tangent = Math.tan(angle * Math.PI / 180);
    var climb = depth * tangent;
    if (climb >= height) {
      var error = "Niet haalbaar: hoogte moet groter zijn dan " + climb.toFixed(2) + " m bij " + angle.toFixed(0) + "°.";
      if (info) info.textContent = error;
      return empty(svg, error, "var(--err-fg)");
    }
    if (info) info.textContent = "De onderranden volgen het moederdak; het dakje blijft horizontaal.";
    var rise = roofDepth * tangent;
    var roof = slope([{x: 0, y: 0, z: 0}, {x: roofWidth, y: 0, z: 0},
      {x: roofWidth, y: rise, z: roofDepth}, {x: 0, y: rise, z: roofDepth}], "moederdak");
    var x0 = (roofWidth - width) / 2, z0 = roofDepth * 0.3, z1 = z0 + depth;
    var floorFront = z0 * tangent, floorBack = z1 * tangent, top = floorFront + height;
    var lf = {x: x0, y: floorFront, z: z0}, rf = {x: x0 + width, y: floorFront, z: z0};
    var lb = {x: x0, y: floorBack, z: z1}, rb = {x: x0 + width, y: floorBack, z: z1};
    var lft = {x: x0, y: top, z: z0}, rft = {x: x0 + width, y: top, z: z0};
    var lbt = {x: x0, y: top, z: z1}, rbt = {x: x0 + width, y: top, z: z1};
    var dormer = [slope([lf, rf, rft, lft], "voor-actief"),
      slope([rf, rb, rbt, rft], "wang-actief"), slope([lft, rft, rbt, lbt], "boven-actief")];
    draw(svg, [roof].concat(dormer), width.toFixed(2) + " × " + depth.toFixed(2) + " × " + height.toFixed(2) + " m · moederdak " + angle.toFixed(0) + "°");
  };

  window.Isometrie = {project: project, polygon: polygon, block: block, slope: slope};
  document.addEventListener("DOMContentLoaded", function () {
    empty(document.getElementById("platSvg"), "Vul breedte en diepte in");
    empty(document.getElementById("zadelSvg"), "Vul de dakmaten in");
    empty(document.getElementById("kapelSvg"), "Vul breedte, hoogte en diepte in");
  });
}());
