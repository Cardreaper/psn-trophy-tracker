import json
from psnawp_api import PSNAWP
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import logging

app = Flask(__name__)
CORS(app)

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configuração inicial
CONFIG_FILE = "config.json"
INTERESTED_FILE = "interested_games.json"
INSTRUCTIONS_FILE = "npsso_instructions.txt"
NPSSO_EXPIRY_DAYS = 50
GENRES = ["Soulslike", "Ação", "Anime", "RPG", "Luta"]

# Lista estática de jogos do PS Plus Game Catalog (Extra/Premium) e Essential mensal
PS_PLUS_GAMES = [
    {"title": "Ghost of Tsushima", "genre": "Ação"},
    {"title": "Hogwarts Legacy", "genre": "RPG"},
    {"title": "Star Wars Jedi: Survivor", "genre": "Ação"},
    {"title": "The Witcher 3: Wild Hunt", "genre": "RPG"},
    {"title": "Bloodborne", "genre": "Soulslike"},
    {"title": "Uncharted: Legacy of Thieves", "genre": "Ação"},
    {"title": "Slay the Spire", "genre": "Indie"},
    {"title": "Celeste", "genre": "Indie"},
    {"title": "Hollow Knight", "genre": "Indie"},
    {"title": "Final Fantasy XV", "genre": "RPG"},
    {"title": "RoboCop: Rogue City", "genre": "Ação"},  # Essential abril 2025
    {"title": "The Texas Chain Saw Massacre", "genre": "Horror"},  # Essential abril 2025
    {"title": "Digimon Story: Cyber Sleuth - Hacker's Memory", "genre": "RPG"},  # Essential abril 2025
    {"title": "Demon's Souls", "genre": "Soulslike"},
    {"title": "Sly Cooper Collection", "genre": "Ação"}
]

# Lista estática de sugestões gerais (para simular busca na web)
GAME_SUGGESTIONS = [
    {"title": "Elden Ring", "genre": "Soulslike"},
    {"title": "Dark Souls III", "genre": "Soulslike"},
    {"title": "Bloodborne", "genre": "Soulslike"},
    {"title": "God of War Ragnarök", "genre": "Ação"},
    {"title": "Horizon Forbidden West", "genre": "Ação"},
    {"title": "Spider-Man 2", "genre": "Ação"},
    {"title": "Persona 5 Royal", "genre": "RPG"},
    {"title": "Final Fantasy XVI", "genre": "RPG"},
    {"title": "Dragon Quest XI", "genre": "RPG"},
    {"title": "Demon Slayer: Kimetsu no Yaiba", "genre": "Anime"},
    {"title": "Naruto Ultimate Ninja Storm 4", "genre": "Anime"},
    {"title": "Tekken 8", "genre": "Luta"},
    {"title": "Street Fighter 6", "genre": "Luta"},
    {"title": "Hogwarts Legacy", "genre": "RPG"},
    {"title": "Star Wars Jedi: Survivor", "genre": "Ação"},
    {"title": "The Witcher 3: Wild Hunt", "genre": "RPG"},
    {"title": "Uncharted: Legacy of Thieves", "genre": "Ação"},
    {"title": "Slay the Spire", "genre": "Indie"},
    {"title": "Celeste", "genre": "Indie"},
    {"title": "Hollow Knight", "genre": "Indie"}
]

# Gerar instruções do NPSSO
def generate_npsso_instructions():
    instructions = """Como obter o NPSSO para o programa:
1. Abra um navegador (ex.: Chrome, Firefox), de preferência em uma aba anônima.
2. Acesse https://www.playstation.com/ e clique em "Sign In".
3. Faça login com seu e-mail e senha da PSN.
4. Se tiver autenticação de dois fatores (2FA), insira o código enviado por SMS ou app.
5. Após logar, abra uma nova aba no MESMO navegador.
6. Acesse https://ca.account.sony.com/api/v1/ssocookie
7. Você verá um texto como: {"npsso":"abcdefghijklmnopqrstuvwxyz1234567890..."}
8. Copie apenas o valor do campo "npsso" (a string longa, sem aspas).
9. Cole no programa quando solicitado ou adicione ao arquivo config.json.
10. Repita este processo a cada ~60 dias, quando o NPSSO expirar.
AVISO: Nunca compartilhe seu NPSSO publicamente. Ele é como uma senha.
"""
    with open(INSTRUCTIONS_FILE, "w") as f:
        f.write(instructions)
    return instructions

# Carregar NPSSO
def load_config():
    if not os.path.exists(CONFIG_FILE):
        instructions = generate_npsso_instructions()
        logger.info("NPSSO não encontrado. Solicitando novo NPSSO.")
        print("\n=== NPSSO não encontrado ===")
        print(instructions)
        npsso = input("Digite seu NPSSO: ")
        save_config(npsso)
        return npsso
    
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
        npsso = config.get("npsso")
        last_updated = config.get("last_updated")
    
    if last_updated:
        last_updated_date = datetime.strptime(last_updated, "%Y-%m-%d")
        days_since_update = (datetime.now() - last_updated_date).days
        if days_since_update > NPSSO_EXPIRY_DAYS:
            logger.warning(f"NPSSO pode estar próximo de expirar. Última atualização: {last_updated} ({days_since_update} dias atrás)")
            print(f"\n=== Aviso: NPSSO pode estar próximo de expirar ===")
            print(f"Última atualização: {last_updated} ({days_since_update} dias atrás)")
            print("Considere renovar seu NPSSO seguindo as instruções em npsso_instructions.txt")
    
    return npsso

# Salvar NPSSO
def save_config(npsso):
    config = {
        "npsso": npsso,
        "last_updated": datetime.now().strftime("%Y-%m-%d")
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
    logger.info(f"NPSSO salvo em {CONFIG_FILE}")
    print(f"NPSSO salvo em {CONFIG_FILE}")

# Carregar jogos com "Like"
def load_interested_games():
    if os.path.exists(INTERESTED_FILE):
        with open(INTERESTED_FILE, "r") as f:
            return json.load(f)
    return []

# Salvar jogos com "Like"
def save_interested_games(interested_games):
    with open(INTERESTED_FILE, "w") as f:
        json.dump(interested_games, f, indent=4)
    logger.info(f"Jogos com Like salvos em {INTERESTED_FILE}")

# Autenticar na PSN
def authenticate_psn(npsso):
    try:
        psnawp = PSNAWP(npsso)
        logger.info("Autenticação PSN bem-sucedida")
        return psnawp
    except Exception as e:
        logger.error(f"Erro ao autenticar na PSN: {e}")
        print(f"\n=== Erro ao autenticar: {e} ===")
        return None

# Obter troféus
def get_trophies(psnawp):
    try:
        user = psnawp.user(online_id=psnawp.me().online_id)
        totals = {"platinum": 0, "gold": 0, "silver": 0, "bronze": 0}
        progress = []
        platinum_games = []
        
        for trophy_title in user.trophy_titles():
            earned = trophy_title.earned_trophies
            total = trophy_title.defined_trophies
            progress_percent = trophy_title.progress
            
            totals["platinum"] += earned.platinum
            totals["gold"] += earned.gold
            totals["silver"] += earned.silver
            totals["bronze"] += earned.bronze
            
            if earned.platinum > 0:
                platinum_games.append(trophy_title.title_name)
            
            if 0 < progress_percent < 100:
                progress.append({
                    "title": trophy_title.title_name,
                    "progress": progress_percent,
                    "earned_trophies": f"{earned.platinum}/{total.platinum}P, "
                                     f"{earned.gold}/{total.gold}G, "
                                     f"{earned.silver}/{total.silver}S, "
                                     f"{earned.bronze}/{total.bronze}B"
                })
        
        logger.info(f"Troféus obtidos: {totals}, Platinas: {len(platinum_games)} jogos")
        return totals, progress, platinum_games
    except Exception as e:
        logger.error(f"Erro ao obter troféus: {e}")
        return {"platinum": 0, "gold": 0, "silver": 0, "bronze": 0}, [], []

# Obter sugestões de platinas
def get_platinum_suggestions(platinum_games, progress, interested_games):
    try:
        # Inferir gêneros preferidos com base nos jogos platinados, em progresso e com Like
        preferred_genres = set()
        for game in platinum_games + [p["title"] for p in progress] + interested_games:
            for genre in GENRES:
                if genre.lower() in game.lower() or any(g["genre"] == genre for g in PS_PLUS_GAMES if g["title"] == game):
                    preferred_genres.add(genre)
        
        if not preferred_genres:
            preferred_genres = GENRES  # Usar todos os gêneros se não houver preferências claras
        
        # Filtrar sugestões com base nos gêneros preferidos e disponibilidade no PS Plus
        suggestions = [
            game for game in GAME_SUGGESTIONS
            if game["genre"] in preferred_genres
            and game["title"] not in platinum_games
            and game["title"] not in [p["title"] for p in progress]
            and any(ps_game["title"] == game["title"] for ps_game in PS_PLUS_GAMES)
        ]
        
        # Priorizar sugestões com base em jogos com Like
        if interested_games:
            prioritized_suggestions = []
            for game in suggestions:
                score = sum(1 for ig in interested_games if any(g["genre"] == game["genre"] for g in PS_PLUS_GAMES if g["title"] == ig))
                prioritized_suggestions.append((game, score))
            prioritized_suggestions.sort(key=lambda x: x[1], reverse=True)
            suggestions = [game for game, _ in prioritized_suggestions]
        
        # Limitar a 5 sugestões
        suggestions = suggestions[:5]
        
        logger.info(f"Sugestões geradas: {len(suggestions)} jogos")
        return suggestions
    except Exception as e:
        logger.error(f"Erro ao gerar sugestões: {e}")
        return []

# Rota padrão
@app.route('/')
def home():
    logger.info("Acessada a rota padrão")
    return jsonify({"message": "Bem-vindo à API PSN Trophy Tracker. Use /api/data para obter dados."})

# Endpoint da API
@app.route('/api/data', methods=['GET'])
def get_data():
    logger.info("Requisição recebida para /api/data")
    try:
        npsso = load_config()
        psnawp = authenticate_psn(npsso)
        
        if not psnawp:
            logger.error("Falha na autenticação PSN")
            return jsonify({"error": "Falha na autenticação PSN"}), 401
        
        totals, progress, platinum_games = get_trophies(psnawp)
        interested_games = load_interested_games()
        suggestions = get_platinum_suggestions(platinum_games, progress, interested_games)
        
        logger.info("Dados enviados com sucesso")
        return jsonify({
            "totals": totals,
            "progress": progress,
            "platinum_games": platinum_games,
            "suggestions": suggestions
        })
    except Exception as e:
        logger.error(f"Erro no endpoint /api/data: {e}")
        return jsonify({"error": str(e)}), 500

# Endpoint para salvar jogos com Like
@app.route('/api/interested', methods=['POST'])
def save_interested():
    logger.info("Requisição recebida para /api/interested")
    try:
        data = request.get_json()
        game_title = data.get("title")
        if not game_title:
            return jsonify({"error": "Título do jogo não fornecido"}), 400
        
        interested_games = load_interested_games()
        if game_title not in interested_games:
            interested_games.append(game_title)
            save_interested_games(interested_games)
        
        logger.info(f"Jogo '{game_title}' marcado como Interessado")
        return jsonify({"message": f"Jogo '{game_title}' adicionado aos favoritos"})
    except Exception as e:
        logger.error(f"Erro no endpoint /api/interested: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)