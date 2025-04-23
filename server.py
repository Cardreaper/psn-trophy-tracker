from flask import Flask, jsonify, request
from flask_cors import CORS
from psnawp_api import PSNAWP
import os
import json
import logging

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://Cardreaper.github.io/psn-trophy-tracker"}})

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Obter NPSSO da variável de ambiente
npsso = os.getenv('NPSSO')
if not npsso:
    logger.error("NPSSO não configurado nas variáveis de ambiente")
    raise ValueError("NPSSO não configurado")

# Inicializar PSNAWP
try:
    psnawp = PSNAWP(npsso)
    user = psnawp.user(online_id="Cardreaper")  # Substitua pelo teu online_id
except Exception as e:
    logger.error(f"Erro ao inicializar PSNAWP: {str(e)}")
    raise

# Caminho para interested_games.json
INTERESTED_GAMES_FILE = "interested_games.json"

# Criar interested_games.json se não existir
if not os.path.exists(INTERESTED_GAMES_FILE):
    logger.info("Criando interested_games.json")
    with open(INTERESTED_GAMES_FILE, 'w') as f:
        json.dump([], f)

# Lista de jogos PS Plus (ajuste para a tua região)
ps_plus_games = [
    {"title": "Bloodborne", "genre": "Action RPG", "platform": "PS4"},
    {"title": "Hogwarts Legacy", "genre": "Action RPG", "platform": "PS5"},
    {"title": "The Last of Us Part II", "genre": "Action-Adventure", "platform": "PS4"},
    {"title": "Spider-Man: Miles Morales", "genre": "Action-Adventure", "platform": "PS5"},
    {"title": "God of War", "genre": "Action-Adventure", "platform": "PS4"},
]

@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        # Obter troféus
        trophies = user.trophies_summary()
        totals = {
            "platinum": trophies.platinum,
            "gold": trophies.gold,
            "silver": trophies.silver,
            "bronze": trophies.bronze
        }

        # Obter jogos em progresso (exemplo simplificado)
        progress = [
            {"title": "Elden Ring", "progress": "75%", "last_played": "2023-10-01"},
            {"title": "Horizon Forbidden West", "progress": "50%", "last_played": "2023-09-15"}
        ]

        # Obter jogos com platina
        platinum_games = [
            {"title": "Astro's Playroom", "earned_date": "2022-11-12"},
            {"title": "Ghost of Tsushima", "earned_date": "2021-08-20"}
        ]

        # Carregar jogos favoritos
        try:
            with open(INTERESTED_GAMES_FILE, 'r') as f:
                interested_games = json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar interested_games.json: {str(e)}. Criando novo arquivo.")
            interested_games = []
            with open(INTERESTED_GAMES_FILE, 'w') as f:
                json.dump(interested_games, f)

        # Gerar sugestões
        suggestions = ps_plus_games
        if interested_games:
            genres = [game.get('genre', '') for game in interested_games if 'genre' in game]
            suggestions = [
                game for game in ps_plus_games
                if game['genre'] in genres or not genres
            ]

        logger.info("Dados retornados com sucesso para /api/data")
        return jsonify({
            "totals": totals,
            "progress": progress,
            "platinum_games": platinum_games,
            "suggestions": suggestions,
            "interested_games": interested_games
        })
    except Exception as e:
        logger.error(f"Erro em /api/data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/interested', methods=['POST'])
def add_interested():
    try:
        data = request.get_json()
        title = data.get('title')
        if not title:
            logger.warning("Título não fornecido em /api/interested")
            return jsonify({"error": "Título não fornecido"}), 400

        try:
            with open(INTERESTED_GAMES_FILE, 'r') as f:
                interested_games = json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar interested_games.json: {str(e)}. Criando novo arquivo.")
            interested_games = []
            with open(INTERESTED_GAMES_FILE, 'w') as f:
                json.dump(interested_games, f)

        if title not in [game['title'] for game in interested_games]:
            game_info = next((game for game in ps_plus_games if game['title'] == title), {"title": title})
            interested_games.append(game_info)
            with open(INTERESTED_GAMES_FILE, 'w') as f:
                json.dump(interested_games, f)
            logger.info(f"Jogo '{title}' adicionado aos favoritos")
        else:
            logger.info(f"Jogo '{title}' já está na lista de favoritos")

        return jsonify({"message": f"Jogo '{title}' adicionado aos favoritos"})
    except Exception as e:
        logger.error(f"Erro em /api/interested: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
