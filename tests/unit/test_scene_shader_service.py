"""O que o servidor guarda de um shader — e o que ele deliberadamente não julga.

Houve aqui uma revisão de GLSL: laço sem teto recusado, nome reservado, ``main``
obrigatório. Ela existia por um motivo real — garantir que o efeito ficasse dentro
do alcance —, mas garantir isso lendo texto obriga a *mexer* no texto, até o GLSL
deixar de ser de quem escreveu.

A contenção passou a ser geométrica: o cliente pinta cada shader num quadro do
tamanho do alcance, recortado por máscara, e o que for desenhado fora não tem onde
existir. Com a garantia fora do texto, o texto não precisa de regra.

O que sobrou aqui é sobre o CAMPO, não sobre o código.
"""
from app.engine.scenes.scene_shader_service import DEFAULT_SOURCE, MAX_SOURCE, review


def test_the_shader_we_ship_is_accepted():
    # Nascer com tela em branco faz o recurso parecer quebrado antes da primeira
    # linha; nascer com um exemplo que o próprio servidor recusa seria pior.
    assert review(DEFAULT_SOURCE) is None


def test_the_field_still_has_bounds():
    assert review("   ") == "lighting.errors.shader_empty", "vazio não é shader"
    # Sem teto, um texto colado sem querer enche banco e rede — isto é limite de
    # armazenamento, não de código.
    assert review("void main(){}" + "\n// " + "a" * MAX_SOURCE) == "lighting.errors.shader_long"


def test_the_server_does_not_judge_the_code():
    """Nada disto é recusado, e é o ponto da mudança.

    Se compila, se é bonito ou se é lento, quem responde é a GPU de quem está
    olhando — e a resposta dela volta como frase no editor, não como palpite de
    uma lista de palavras proibidas aqui.
    """
    escrito_livremente = (
        "void main(){ while(true) { } }",              # laço sem saída
        "void main(){ for(int i=0;i<9999;i++){} }",    # laço enorme
        "uniform float uTime;\nvoid main(){}",         # redeclara um uniform nosso
        "vec2 gwWorld(vec2 uv){ return uv; }\nvoid main(){}",
        "#include <coisa>\nvoid main(){}",
        "float x = 1.0;",                              # nem main tem
    )
    for source in escrito_livremente:
        assert review(source) is None, source


def test_the_example_paints_with_alpha_instead_of_washing_the_map():
    """Um efeito de cena tem de deixar o mapa aparecer por baixo.

    Enquanto o shader era um filtro sobre o mundo, o exemplo misturava a própria
    cor com a do terreno (``mix(cena.rgb, ...)``) e o resultado era uma lavagem
    por cima do mapa. Agora ele pinta num quadro próprio, então o que compõe é o
    alfa — com a cor já multiplicada por ele, que é o que a GPU espera.
    """
    assert "finalColor = vec4(cor * a, a);" in DEFAULT_SOURCE
    assert "texture(uTexture" not in DEFAULT_SOURCE, "o quadro é dele, não a cena"
    # E o desenho é feito em espaço de mundo — e na escala do alcance, senão zoom e
    # arrasto deslizam o efeito, e um círculo pequeno vira mancha chapada.
    assert "gwPattern(vTextureCoord)" in DEFAULT_SOURCE
    assert "gwLight(vTextureCoord)" in DEFAULT_SOURCE
    assert "gwLight(uv)" not in DEFAULT_SOURCE
