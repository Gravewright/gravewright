"""Rebuild the private Savage Pathfinder item compendium from the owned rulebook.

Descriptions are intentionally concise paraphrases. Mechanical fields already curated in the
existing packs are preserved; missing catalogue entries receive their category and book reference.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data/packages/content/savage-pathfinder-private"
CONTENT = PACKAGE / "content"


def slug(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def read_pack(name: str) -> dict:
    return json.loads((CONTENT / name).read_text(encoding="utf-8"))


def write_pack(name: str, data: dict) -> None:
    (CONTENT / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def add_catalogue(pack: dict, names: list[str], *, prefix: str, item_type: str,
                  folder: str, page: str, category: str | None = None) -> None:
    existing = {entry["name"].casefold() for entry in pack["entries"]}
    for name in names:
        if name.casefold() in existing:
            continue
        data = {
            "importFolder": folder,
            "summary": f"{category or folder}. Referência condensada do Livro de Regras, p. {page}.",
            "source": f"Livro de Regras, p. {page}",
        }
        if category:
            data["category"] = category
        pack["entries"].append({
            "id": f"{prefix}-{slug(name)}",
            "type": item_type,
            "name": name,
            "data": data,
        })
        existing.add(name.casefold())


# Repair the corrupted first block and restore every Background Edge from the summary table.
advantages = read_pack("vantagens.gwpack.json")
advantages["entries"] = [
    entry for entry in advantages["entries"]
    if entry.get("data", {}).get("category", "").casefold() != "vantagens de antecedente"
]
background = [
    ("Ambidestro", "N, Agi d8", "Ignora a penalidade por usar a mão inábil."),
    ("Antecedente Arcano (Magia ou Milagres)", "N", "Concede acesso a magia ou milagres."),
    ("Aristocrata", "N", "Conhecimento e contatos entre a elite."),
    ("Atraente", "N, Vig d6", "Favorece Performance e Persuadir."),
    ("Muito Atraente", "N, Atraente", "Amplia os benefícios sociais de Atraente."),
    ("Brutamontes", "N, For d6, Vig d6", "Vincula Atletismo à Força e melhora arremessos."),
    ("Carismático", "N, Esp d8", "Permite uma nova tentativa gratuita de Persuadir."),
    ("Corajoso", "N, Esp d6", "Melhora testes e consequências de Medo."),
    ("Cura Rápida", "N, Vig d8", "Favorece e acelera a cura natural."),
    ("Famoso", "N", "Reconhecimento público concede benefícios sociais e financeiros."),
    ("Muito Famoso", "E, Famoso", "Amplia os benefícios concedidos pela fama."),
    ("Impulso", "N, Esp d8", "Melhora rerrolagens de Característica pagas com Bene."),
    ("Ligeiro", "N, Agi d6", "Aumenta Movimentação e o dado de corrida."),
    ("Linguista", "N, Ast d6", "Concede familiaridade com vários idiomas."),
    ("Musculoso", "N, For d6, Vig d6", "Aumenta Tamanho e capacidade efetiva de carga."),
    ("Prontidão", "N", "Concede bônus em Perceber."),
    ("Rápido", "N, Agi d8", "Permite substituir Cartas de Ação baixas."),
    ("Resistência Arcana", "N, Esp d8", "Dificulta poderes hostis e reduz dano mágico."),
    ("Resistência Arcana Aprimorada", "N, Resistência Arcana", "Amplia a resistência contra magia."),
    ("Sorte", "N", "Concede um Bene adicional por sessão."),
    ("Sorte Grande", "N, Sorte", "Concede dois Benes adicionais por sessão."),
]
for name, requirements, summary in reversed(background):
    advantages["entries"].insert(0, {
        "id": f"vantagem-{slug(name)}", "type": "edge", "name": name,
        "data": {"rank": "seasoned" if requirements.startswith("E,") else "novice",
                 "requirements": requirements, "category": "Vantagens de Antecedente",
                 "importFolder": "Antecedente", "summary": summary,
                 "source": "Livro de Regras, p. 97"},
    })
add_catalogue(advantages, ["Ás"], prefix="vantagem", item_type="edge",
              folder="Profissionais", page="104", category="Vantagens Profissionais")
for entry in advantages["entries"]:
    entry["data"].setdefault("importFolder", entry["data"].get("category", "Outras"))
# The old table extraction repeated this prestige progression once.
seen_advantage_ids: set[str] = set()
seen_advantage_names: set[str] = set()
advantages["entries"] = [
    entry for entry in advantages["entries"]
    if not (
        entry["id"] in seen_advantage_ids
        or entry["name"].casefold() in seen_advantage_names
        or seen_advantage_ids.add(entry["id"])
        or seen_advantage_names.add(entry["name"].casefold())
    )
]
write_pack("vantagens.gwpack.json", advantages)


# Divinities/domains and sorcerous bloodlines are selectable character items too.
domains = {"id": "sp-dominios", "type": "item_pack", "entries": []}
add_catalogue(domains, [
    "Civilização", "Conhecimento", "Destruição", "Elemental", "Enganação", "Força",
    "Glória", "Guerra", "Magia", "Morte", "Natureza", "Proteção", "Sorte", "Viagem",
], prefix="dominio", item_type="edge", folder="Domínios", page="50–54", category="Domínio divino")
write_pack("dominios.gwpack.json", domains)

bloodlines = {"id": "sp-linhagens", "type": "item_pack", "entries": []}
add_catalogue(bloodlines, [
    "Aberrante", "Arcana", "Celestial", "Demoníaca", "Destinado", "Diabólica",
    "Dracônica", "Elemental", "Feérica", "Morto-vivo",
], prefix="linhagem", item_type="edge", folder="Linhagens", page="58–61", category="Linhagem de feiticeiro")
write_pack("linhagens.gwpack.json", bloodlines)


equipment = read_pack("equipamento.gwpack.json")
for entry in equipment["entries"]:
    folders = {"weapon": "Armas", "armor": "Armaduras", "shield": "Escudos", "gear": "Equipamento de aventura"}
    entry["data"].setdefault("importFolder", folders.get(entry["type"], "Outros"))

add_catalogue(equipment, [
    "Agulha", "Algemas", "Ampulheta", "Anzol", "Apito de cerâmica", "Arpéu", "Bolsa de cinto",
    "Caneca/Copo de cerâmica", "Caneta-tinteiro", "Cera de vedação", "Cesto pequeno", "Cobertor",
    "Corda de seda (20 m)", "Corrente", "Espelho pequeno de aço", "Espigão (pitão)",
    "Estojo de mapa ou pergaminho", "Estrepes", "Frasco ou jarro de cerâmica", "Frasco pequeno",
    "Garrafa de vidro", "Giz", "Lamparina pequena", "Lanterna coberta", "Lanterna olho de boi",
    "Lenha", "Odre", "Óleo para lamparina", "Pá", "Panela de ferro", "Papel", "Pé de cabra",
    "Pederneira e aço", "Pedra de amolar", "Pergaminho", "Polia e corda", "Rede de pesca", "Sabão",
    "Saco", "Saco de dormir", "Tela", "Tenda de lona", "Vara (3,5 m)", "Vela",
], prefix="equip", item_type="gear", folder="Equipamento de aventura", page="110–112")
add_catalogue(equipment, [
    "Traje de artesão", "Traje de frio", "Traje de mercador", "Traje de nobre", "Traje de viajante", "Traje real",
], prefix="roupa", item_type="gear", folder="Roupas", page="111")
add_catalogue(equipment, [
    "Ale (caneca)", "Ale (galão)", "Banquete", "Frutas secas", "Pão", "Queijo", "Ração animal",
    "Refeição boa", "Refeição comum", "Refeição pobre", "Vinho (caneca)", "Vinho (galão)",
], prefix="comida", item_type="gear", folder="Comida e bebida", page="111")
add_catalogue(equipment, [
    "Bolsa de componentes mágicos", "Ferramentas de artesão", "Instrumento musical", "Luneta", "Lupa",
    "Marreta", "Martelo", "Picareta de mineiro", "Régua de mercador", "Símbolo sagrado de madeira",
    "Símbolo sagrado de prata",
], prefix="ferramenta", item_type="gear", folder="Ferramentas e kits", page="111–112")
add_catalogue(equipment, [
    "Alforjes", "Burro ou mula", "Cão de guarda", "Cavalo leve", "Cavalo pesado", "Freio e arreio",
    "Pônei leve", "Pônei pesado", "Sela de cavalgar", "Sela de guerra",
], prefix="animal", item_type="gear", folder="Animais e arreios", page="111")
add_catalogue(equipment, [
    "Estalagem pobre", "Estalagem comum", "Estalagem boa", "Estábulo",
], prefix="servico", item_type="gear", folder="Alojamento e serviços", page="111")
add_catalogue(equipment, [
    "Adamante", "Madeira negra", "Couro de dragão", "Ferro frio", "Mithral", "Prata alquímica", "Obra-prima",
], prefix="material", item_type="gear", folder="Materiais especiais", page="109–110")
add_catalogue(equipment, [
    "Elmo pesado fechado", "Armadura de espinhos", "Manopla fechada", "Barda de couro",
    "Barda de malha", "Barda de placas",
], prefix="armadura", item_type="armor", folder="Armaduras", page="113")
add_catalogue(equipment, ["Escudo com espinhos"], prefix="escudo", item_type="shield", folder="Escudos", page="114")
add_catalogue(equipment, [
    "Besta de mão", "Besta de mão de repetição", "Besta leve de repetição", "Besta pesada de repetição",
    "Boleadeira", "Faca estrela", "Funda", "Lança leve/dardo", "Machado de mão", "Rede balanceada",
    "Shuriken", "Tridente", "Zarabatana", "Alfange", "Chicote", "Clava leve", "Clava pesada",
    "Corrente com cravos", "Espada bastarda", "Foice", "Glaive", "Guisarme", "Katana", "Lança curta",
    "Lança de cavalaria", "Maça pesada", "Maça-estrela", "Malho", "Mangual", "Mangual pesado", "Pique",
    "Ranseur", "Sai", "Segadeira",
], prefix="arma", item_type="weapon", folder="Armas", page="115–117")
add_catalogue(equipment, [
    "Dardos de zarabatana", "Flechas", "Pedras de funda", "Setas de besta",
], prefix="municao", item_type="gear", folder="Munições", page="116")
add_catalogue(equipment, [
    "Canhão (balas sólidas)", "Aríete", "Balista", "Catapulta", "Torre de cerco", "Trabuco",
], prefix="cerco", item_type="weapon", folder="Armas especiais e de cerco", page="117–118")
add_catalogue(equipment, [
    "Ácido", "Água benta", "Antitoxina", "Bastão de fumaça", "Bastão solar", "Bolsa enredapé",
    "Fogo alquímico", "Fósforos", "Pedra-trovão", "Tocha da chama eterna",
], prefix="alquimico", item_type="gear", folder="Itens alquímicos", page="119")
add_catalogue(equipment, [
    "Carroça", "Carroção leve", "Carroção pesado", "Carruagem", "Trenó", "Aeronave (dirigível)",
    "Dragão alquímico", "Planador", "Barcaça", "Barco a remo", "Corveta", "Galé", "Navio",
    "Navio de guerra (galeão)", "Veleiro",
], prefix="veiculo", item_type="gear", folder="Veículos", page="120–121")
write_pack("equipamento.gwpack.json", equipment)


magic = {"id": "sp-itens-magicos", "type": "item_pack", "entries": []}
magic_groups = {
    "Encantamentos de armaduras e escudos": ["Animado", "Deflexão de flechas", "Defletir", "Égide", "Eterialidade", "Fortificação", "Resistência a energia", "Refletir", "Resistência mágica", "Transformação"],
    "Encantamentos de armas": ["Afiada", "Arremessável", "Brutal", "Corte poderoso", "Dançante", "Dano", "Distância", "Elemental", "Iluminar", "Matadora", "Perversa", "Precisão", "Retornável", "Velocidade", "Vorpal"],
    "Armaduras, escudos e armas nomeados": ["Armadura celestial", "Cota de talhas da sorte", "Couro de rinoceronte", "Elmo do teleporte", "Elmo dos idiomas compreendidos", "Escudo do leão", "Adaga do assassino", "Arco do juramento", "Azagaia dos relâmpagos", "Espada dos planos", "Flecha do sono", "Lâmina da sorte", "Língua flamejante", "Vingadora sagrada"],
    "Anéis": ["Anel da evasão", "Anel da habilidade", "Anel da invisibilidade", "Anel da queda suave", "Anel de armazenamento de magias", "Anel de caminhar na água", "Anel de contramágicas", "Anel de proteção", "Anel de regeneração", "Anel de resistência energética", "Anel de telecinese", "Anel de três desejos", "Anel do aríete", "Anel do sustento"],
    "Bastões": ["Bastão da absorção", "Bastão da metamágica", "Bastão da negação", "Bastão da serpente", "Bastão das maravilhas", "Bastão do governo", "Bastão imóvel"],
    "Cajados": ["Cajado da abjuração", "Cajado da cura", "Cajado da defesa", "Cajado da evocação", "Cajado da necromancia", "Cajado da vida", "Cajado do encanto", "Cajado do poder"],
    "Consumíveis arcanos": ["Poção", "Pergaminho", "Varinha"],
    "Itens maravilhosos": ["Algemas dimensionais", "Aljava eficiente", "Amuleto da armadura natural", "Amuleto dos planos", "Asas do voo", "Bandana da superioridade mental", "Bandana do primor mental", "Bolsa de truques", "Botas aladas", "Botas da levitação", "Botas da travessia e do salto", "Botas da velocidade", "Botas élficas", "Braçadeiras da armadura", "Bracelete dos amigos", "Buraco portátil", "Capa do saltimbanco", "Carrilhão da abertura", "Chapéu do disfarce", "Cinto da força física", "Cinto da perfeição física", "Cinto dos anões", "Cola tudo", "Colar de bolas de fogo", "Colher da sustentação", "Corda de constrição", "Corda de escalada", "Elixir do sopro de fogo", "Escaravelho contra golens", "Escaravelho da proteção", "Estatuetas de incrível poder", "Ferraduras da velocidade", "Garrafa da água infinita", "Garrafa de ar", "Harpa do encantamento", "Lanterna da revelação", "Luvas de armazenamento", "Luvas de natação e escalada", "Manopla da ferrugem", "Manto da forma etérea", "Manto do deslocamento", "Manto élfico", "Manual do aumento de atributo", "Mão da glória", "Mão do mago", "Mochila de carga", "Óculos noturnos", "Olhos de águia", "Pedra da boa sorte", "Pedra iônica", "Pérola das sirenes", "Pérola do poder", "Periapto da proteção contra veneno", "Periapto da saúde", "Pó do aparecimento", "Pó do desaparecimento", "Robe da camuflagem", "Robe das cores cintilantes", "Robe dos itens úteis", "Robe dos ossos", "Sacola prestativa", "Sandálias de patas de aranha", "Solvente universal", "Talismã de penas", "Tapete voador", "Vela da verdade"],
}
for folder, names in magic_groups.items():
    add_catalogue(magic, names, prefix="magico", item_type="gear", folder=folder, page="220–239", category="Item mágico")
write_pack("itens-magicos.gwpack.json", magic)


manifest_path = PACKAGE / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"] = "0.3.0"
packs = manifest["provides"]["contentPacks"]
additions = [
    {"id": "sp-dominios", "type": "item_pack", "label": "Divindades e Domínios", "path": "content/dominios.gwpack.json"},
    {"id": "sp-linhagens", "type": "item_pack", "label": "Linhagens", "path": "content/linhagens.gwpack.json"},
    {"id": "sp-itens-magicos", "type": "item_pack", "label": "Itens Mágicos", "path": "content/itens-magicos.gwpack.json"},
]
known = {pack["id"] for pack in packs}
packs.extend(pack for pack in additions if pack["id"] not in known)
for pack in packs:
    if pack["id"] == "sp-equipamento":
        pack["label"] = "Equipamento"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("Compêndio de itens reconstruído.")
