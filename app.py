import os
import re
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string
import redis

app = Flask(__name__)

cache = redis.Redis(host='banco-redis', port=6379, decode_responses=True)

LOG_DIR = '/var/log/app'
LOG_FILE = os.path.join(LOG_DIR, 'acessos.log')

CATALOGO_PADRAO = {
    "1": {"titulo": "Elden Ring", "categoria": "Soulslike / RPG", "preco": 249, "estoque": 5},
    "2": {"titulo": "Baldur's Gate 3", "categoria": "CRPG Tático", "preco": 199, "estoque": 4},
    "3": {"titulo": "Dark Souls III", "categoria": "Action RPG", "preco": 159, "estoque": 3},
    "4": {"titulo": "Lies of P", "categoria": "Soulslike", "preco": 199, "estoque": 6},
    "5": {"titulo": "Clean Architecture (Livro)", "categoria": "Biblioteca DevOps", "preco": 89, "estoque": 8},
}

def registrar_log(evento):
    os.makedirs(LOG_DIR, exist_ok=True)
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{agora}] {evento}\n")

def inicializar_catalogo():
    if not cache.exists("catalogo_inicializado"):
        for item_id, dados in CATALOGO_PADRAO.items():
            cache.hset(f"item:{item_id}", mapping=dados)
        cache.set("catalogo_inicializado", "1")
        cache.set("receita_total", 0)
        registrar_log("SISTEMA: Catálogo inicializado no Redis com sucesso.")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>DevOps Store & Hub</title>
    <style>
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 980px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 20px; }
        .badges { display: flex; gap: 12px; }
        .badge { background: #0ea5e9; color: #fff; padding: 8px 14px; border-radius: 6px; font-weight: bold; font-size: 0.9rem; }
        .badge.revenue { background: #10b981; }
        .grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        .card { background: #1e293b; padding: 18px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 12px 8px; border-bottom: 1px solid #334155; }
        th { color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; }
        .btn { padding: 6px 12px; border: none; border-radius: 5px; cursor: pointer; font-weight: 600; color: white; transition: 0.15s; }
        .btn-buy { background: #6366f1; }
        .btn-buy:hover { background: #4f46e5; }
        .btn-buy:disabled { background: #475569; cursor: not-allowed; }
        .btn-restock { background: #334155; font-size: 0.8rem; }
        .btn-restock:hover { background: #475569; }
        .btn-remove-tx { background: #ef4444; color: white; border: none; border-radius: 4px; padding: 3px 8px; cursor: pointer; font-size: 0.75rem; font-weight: bold; }
        .btn-remove-tx:hover { background: #dc2626; }
        .form-group { display: flex; gap: 8px; margin-top: 10px; }
        input { background: #0f172a; border: 1px solid #334155; color: white; padding: 8px; border-radius: 5px; width: 100%; }
        .history-list { list-style: none; padding: 0; margin: 0; font-size: 0.9rem; }
        .history-list li { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid #334155; color: #cbd5e1; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1 style="margin: 0; font-size: 1.5rem;">🎮 DevOps Store & Biblioteca</h1>
            <p style="margin: 5px 0 0; color: #94a3b8; font-size: 0.9rem;">Orquestração com Flask + Redis Cache + Persistência de Logs em Volume</p>
        </div>
        <div class="badges">
            <div class="badge">👁️ Visitas (F5): {{ visitas }}</div>
            <div class="badge revenue">💰 Total no Redis: R$ {{ receita }}</div>
        </div>
    </div>

    <div class="grid">
        <div>
            <div class="card">
                <h3 style="margin-top: 0;">📦 Catálogo em Cache (Redis Hashes)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Título</th>
                            <th>Categoria</th>
                            <th>Preço</th>
                            <th>Estoque</th>
                            <th>Ação</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for id, item in itens.items() %}
                        <tr>
                            <td><strong>{{ item.titulo }}</strong></td>
                            <td>{{ item.categoria }}</td>
                            <td>R$ {{ item.preco }}</td>
                            <td>{{ item.estoque }} un.</td>
                            <td style="display: flex; gap: 6px;">
                                <form action="/comprar/{{ id }}" method="post" style="margin:0;">
                                    <button class="btn btn-buy" type="submit" {% if item.estoque|int <= 0 %}disabled{% endif %}>
                                        {% if item.estoque|int > 0 %}Comprar{% else %}Esgotado{% endif %}
                                    </button>
                                </form>
                                <form action="/repor/{{ id }}" method="post" style="margin:0;">
                                    <button class="btn btn-restock" type="submit" title="Repor +1">+1</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            <div class="card">
                <h4 style="margin-top: 0;">➕ Cadastrar Novo Item no Redis</h4>
                <form action="/adicionar" method="post" class="form-group">
                    <input type="text" name="titulo" placeholder="Nome do Jogo ou Livro" required>
                    <input type="text" name="categoria" placeholder="Categoria" required>
                    <input type="number" name="preco" placeholder="Preço (R$)" required style="max-width: 110px;">
                    <input type="number" name="estoque" placeholder="Qtd" required style="max-width: 80px;">
                    <button class="btn btn-buy" type="submit">Salvar</button>
                </form>
            </div>
        </div>

        <div>
            <div class="card">
                <h3 style="margin-top: 0;">🧾 Últimas Transações (Redis List)</h3>
                <ul class="history-list">
                    {% for transacao in historico %}
                        <li>
                            <span>{{ transacao }}</span>
                            <form action="/remover-transacao" method="post" style="margin:0;">
                                <input type="hidden" name="transacao" value="{{ transacao }}">
                                <button class="btn-remove-tx" type="submit" title="Remover transação e estornar">✕</button>
                            </form>
                        </li>
                    {% else %}
                        <li style="color: #64748b;">Nenhuma compra realizada ainda.</li>
                    {% endfor %}
                </ul>
            </div>
            <div class="card" style="font-size: 0.85rem; color: #94a3b8;">
                <strong>📁 Auditoria de Volume:</strong><br>
                Cada visita (F5), compra, estorno de transação, reposição ou cadastro grava uma linha detalhada em <code>/var/log/app/acessos.log</code> (espelhado na pasta local <code>logs/</code>).
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""

@app.route('/')
def home():
    try:
        inicializar_catalogo()
        visitas = cache.incr('contador_visitas')
        receita = cache.get('receita_total') or 0

        chaves = sorted(cache.keys("item:*"), key=lambda k: int(k.split(":")[1]))
        itens = {k.split(":")[1]: cache.hgetall(k) for k in chaves}

        historico = cache.lrange("historico_vendas", 0, 7)

        registrar_log(f"ACESSO: Página principal carregada. Visita nº {visitas} (IP: {request.remote_addr})")
        return render_template_string(HTML_TEMPLATE, visitas=visitas, receita=receita, itens=itens, historico=historico)
    except redis.exceptions.ConnectionError:
        return "Erro: Não foi possível conectar ao container 'banco-redis' na rede 'rede-app'.", 500

@app.route('/comprar/<item_id>', methods=['POST'])
def comprar(item_id):
    chave = f"item:{item_id}"
    if cache.exists(chave):
        item = cache.hgetall(chave)
        estoque_atual = int(item.get("estoque", 0))
        preco = int(item.get("preco", 0))
        titulo = item.get("titulo", "Item")

        if estoque_atual > 0:
            novo_estoque = cache.hincrby(chave, "estoque", -1)
            nova_receita = cache.incrby("receita_total", preco)
            hora = datetime.now().strftime('%H:%M:%S')
            cache.lpush("historico_vendas", f"[{hora}] Compra: {titulo} (R$ {preco})")
            registrar_log(f"VENDA: '{titulo}' vendido por R$ {preco} | Estoque restante: {novo_estoque} | Receita acumulada: R$ {nova_receita}")
    return redirect(url_for('home'))

@app.route('/remover-transacao', methods=['POST'])
def remover_transacao():
    transacao = request.form.get("transacao")
    if transacao:
        removidos = cache.lrem("historico_vendas", 1, transacao)
        if removidos > 0:
            match = re.search(r"Compra:\s+(.+)\s+\(R\$\s+(\d+)\)$", transacao)
            if match:
                titulo_item = match.group(1)
                preco_item = int(match.group(2))
                
                receita_atual = int(cache.get("receita_total") or 0)
                nova_receita = max(0, receita_atual - preco_item)
                cache.set("receita_total", nova_receita)

                for chave in cache.keys("item:*"):
                    if cache.hget(chave, "titulo") == titulo_item:
                        cache.hincrby(chave, "estoque", 1)
                        break

                registrar_log(f"ESTORNO: Transação '{transacao}' removida da lista | +1 devolvido ao estoque de '{titulo_item}' | Receita ajustada: R$ {nova_receita}")
            else:
                registrar_log(f"TRANSAÇÃO REMOVIDA: '{transacao}' excluída da lista de histórico.")
    return redirect(url_for('home'))

@app.route('/repor/<item_id>', methods=['POST'])
def repor(item_id):
    chave = f"item:{item_id}"
    if cache.exists(chave):
        titulo = cache.hget(chave, "titulo")
        novo_estoque = cache.hincrby(chave, "estoque", 1)
        registrar_log(f"ESTOQUE: +1 unidade adicionada ao item '{titulo}'. Total em estoque: {novo_estoque}")
    return redirect(url_for('home'))

@app.route('/adicionar', methods=['POST'])
def adicionar():
    chaves = cache.keys("item:*")
    maior_id = max([int(k.split(":")[1]) for k in chaves], default=0)
    novo_id = str(maior_id + 1)

    titulo = request.form.get("titulo")
    categoria = request.form.get("categoria")
    preco = int(request.form.get("preco", 0))
    estoque = int(request.form.get("estoque", 1))

    cache.hset(f"item:{novo_id}", mapping={
        "titulo": titulo,
        "categoria": categoria,
        "preco": preco,
        "estoque": estoque
    })
    registrar_log(f"CADASTRO: Novo item '{titulo}' ({categoria}) adicionado por R$ {preco} com {estoque} un.")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)