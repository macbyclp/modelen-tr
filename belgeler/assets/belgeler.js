/* Modelen dokümantasyonu: kod kopyalama, istemci tarafı arama, içindekiler vurgusu. Bağımlılık yok. */
(function () {
  var govde = document.body, dil = govde.dataset.dil || "tr";

  // --- kod bloklarına "Kopyala" düğmesi
  document.querySelectorAll(".kod").forEach(function (k) {
    var b = document.createElement("button");
    b.type = "button"; b.textContent = govde.dataset.kopyala || "Copy";
    b.addEventListener("click", function () {
      var m = k.querySelector("code").innerText;
      var bitti = function () { b.textContent = govde.dataset.kopyalandi || "Copied"; setTimeout(function () { b.textContent = govde.dataset.kopyala || "Copy"; }, 1400); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(m).then(bitti, function () {});
      else { var t = document.createElement("textarea"); t.value = m; document.body.appendChild(t); t.select(); try { document.execCommand("copy"); bitti(); } catch (e) {} document.body.removeChild(t); }
    });
    k.appendChild(b);
  });

  // --- arama
  var kutu = document.getElementById("ara"), sonuc = document.getElementById("sonuc"), veri = null, yukleniyor = false;
  function kac(s) { return s.replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function yukle(cb) {
    if (veri) return cb();
    if (yukleniyor) return;
    yukleniyor = true;
    fetch("/assets/arama-" + dil + ".json").then(function (r) { return r.json(); }).then(function (d) { veri = d; yukleniyor = false; cb(); }).catch(function () { yukleniyor = false; });
  }
  function ara() {
    var q = kutu.value.trim().toLowerCase();
    if (q.length < 2) { sonuc.hidden = true; return; }
    var kelimeler = q.split(/\s+/);
    var puanli = veri.map(function (s) {
      var b = s.b.toLowerCase(), t = s.t.toLowerCase(), p = 0;
      kelimeler.forEach(function (k) {
        if (b.indexOf(k) >= 0) p += 10;
        var i = t.indexOf(k); if (i >= 0) p += 2 + (t.split(k).length - 1 > 3 ? 1 : 0);
        else if (b.indexOf(k) < 0) p -= 100;
      });
      return { s: s, p: p };
    }).filter(function (x) { return x.p > 0; }).sort(function (a, b) { return b.p - a.p; }).slice(0, 8);
    if (!puanli.length) { sonuc.innerHTML = '<div class="yok">' + kac(govde.dataset.yok || "No results.") + "</div>"; sonuc.hidden = false; return; }
    sonuc.innerHTML = puanli.map(function (x) {
      var t = x.s.t, i = Math.max(0, t.toLowerCase().indexOf(kelimeler[0]) - 40), parca = kac(t.substr(i, 130));
      kelimeler.forEach(function (k) { parca = parca.replace(new RegExp("(" + k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig"), "<mark>$1</mark>"); });
      return '<a href="' + x.s.u + '"><b>' + kac(x.s.b) + "</b><small>" + (i > 0 ? "… " : "") + parca + " …</small></a>";
    }).join("");
    sonuc.hidden = false;
  }
  if (kutu) {
    kutu.addEventListener("input", function () { yukle(ara); });
    kutu.addEventListener("focus", function () { yukle(function () {}); });
    kutu.addEventListener("keydown", function (e) { if (e.key === "Escape") { sonuc.hidden = true; kutu.blur(); } if (e.key === "ArrowDown") { var a = sonuc.querySelector("a"); if (a) { a.focus(); e.preventDefault(); } } });
    sonuc.addEventListener("keydown", function (e) {
      var a = document.activeElement;
      if (e.key === "ArrowDown" && a.nextElementSibling) { a.nextElementSibling.focus(); e.preventDefault(); }
      if (e.key === "ArrowUp") { (a.previousElementSibling || kutu).focus(); e.preventDefault(); }
      if (e.key === "Escape") { sonuc.hidden = true; kutu.focus(); }
    });
    document.addEventListener("click", function (e) { if (!e.target.closest(".arama")) sonuc.hidden = true; });
    document.addEventListener("keydown", function (e) { if (e.key === "/" && !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) { e.preventDefault(); kutu.focus(); } });
  }

  // --- içindekiler: görünen başlığı vurgula
  var baglar = document.querySelectorAll(".toc a"), basliklar = [];
  baglar.forEach(function (a) { var h = document.getElementById(a.getAttribute("href").slice(1)); if (h) basliklar.push([h, a]); });
  if (basliklar.length && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (kayitlar) {
      kayitlar.forEach(function (k) { if (k.isIntersecting) { baglar.forEach(function (a) { a.classList.remove("aktif"); }); basliklar.forEach(function (x) { if (x[0] === k.target) x[1].classList.add("aktif"); }); } });
    }, { rootMargin: "-70px 0px -70% 0px" });
    basliklar.forEach(function (x) { io.observe(x[0]); });
  }
})();
