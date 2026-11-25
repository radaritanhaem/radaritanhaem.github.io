"""Servidor só para ver o site no próprio computador, igual ao GitHub Pages
(abre /noticia/nome procurando /noticia/nome.html).  Uso: python servidor_local.py [porta]"""
import http.server, os, sys

PASTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site")

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=PASTA, **k)
    def translate_path(self, path):
        p = super().translate_path(path)  # Windows: caminhos longos precisam do prefixo \\?\
        return "\\\\?\\" + os.path.abspath(p) if os.name == "nt" and not p.startswith("\\\\?\\") else p
    def send_head(self):
        caminho = self.translate_path(self.path)
        if not os.path.exists(caminho) and os.path.exists(caminho + ".html"):
            self.path = self.path.split("?")[0] + ".html"
        elif not os.path.exists(caminho):
            self.path = "/404.html"
        return super().send_head()

http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8765), H).serve_forever()
