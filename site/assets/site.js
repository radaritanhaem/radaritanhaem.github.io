// Botão "Copiar link" e "Mostrar mais" nas listas.
document.querySelectorAll("[data-copiar]").forEach(b => b.addEventListener("click", async () => {
  try { await navigator.clipboard.writeText(b.dataset.copiar); b.textContent = "Link copiado"; }
  catch { prompt("Copie o link:", b.dataset.copiar); }
}));
document.querySelectorAll("[data-paginar]").forEach(g => {
  const passo = Number(g.dataset.paginar) || 12, itens = [...g.children];
  if (itens.length <= passo) return;
  let n = passo;
  const btn = document.createElement("button");
  btn.type = "button"; btn.className = "btn-mais";
  const mostrar = () => {
    itens.forEach((el, i) => { el.hidden = i >= n; });
    btn.hidden = n >= itens.length;
    btn.textContent = `Mostrar mais (${itens.length - n} restantes)`;
  };
  btn.addEventListener("click", () => { n += passo; mostrar(); });
  g.after(btn); mostrar();
});

// Compras da Prefeitura: busca, filtro por modalidade e "mostrar mais"
(() => {
  const lista = document.getElementById("lista-compras");
  if (!lista) return;
  const cards = [...lista.children], q = document.getElementById("q-compra"), info = document.getElementById("n-compra"), mais = document.getElementById("mais-compras");
  const norm = s => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  let mod = "", passo = 18, n = passo;
  const desenhar = () => {
    const termos = norm(q.value).split(/\s+/).filter(t => t.length > 1);
    const ok = cards.filter(c => (!mod || c.dataset.mod === mod) && termos.every(t => c.dataset.texto.includes(t)));
    cards.forEach(c => c.hidden = true);
    ok.slice(0, n).forEach(c => c.hidden = false);
    info.textContent = `${ok.length} ${ok.length === 1 ? "compra" : "compras"}, da mais recente para a mais antiga.`;
    mais.hidden = ok.length <= n; mais.textContent = `Mostrar mais (${ok.length - n} restantes)`;
  };
  let t; q.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => { n = passo; desenhar(); }, 200); });
  document.querySelectorAll("[data-fmod]").forEach(b => b.addEventListener("click", () => {
    mod = b.dataset.fmod; n = passo;
    document.querySelectorAll("[data-fmod]").forEach(x => x.setAttribute("aria-pressed", String(x === b))); desenhar(); }));
  mais.addEventListener("click", () => { n += passo; desenhar(); });
  if (location.hash.startsWith("#c-")) { const alvo = document.querySelector(location.hash); if (alvo) { n = cards.length; desenhar(); alvo.scrollIntoView(); } }
  window.addEventListener("hashchange", () => { const alvo = document.querySelector(location.hash); if (alvo && alvo.hidden) { q.value = ""; mod = ""; n = cards.length; desenhar(); alvo.scrollIntoView(); } });
  desenhar();
})();
