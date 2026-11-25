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
