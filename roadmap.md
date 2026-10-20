# Roadmap do combate (rcs_battlelab)

## 1. Visão geral: as camadas

O combate é dividido em camadas, em que cada uma só conversa com a de baixo:

```
DADOS        mockup.py              → INITIAL_UNITS (hero e monster)
GEOMETRIA    battle_geometry.py     → matemática do tabuleiro isométrico
ESTADO       battle_state.py        → turnos, rounds, timer, vencedor
REGRAS       battle_actions.py      → pode mover? pode atacar? aplica dano
IA           battle_ai.py           → o que o monstro faz no turno dele
LOG          battle_log.py          → histórico de eventos
UI           battle_page.py + components/*  → desenha e captura cliques
```

A regra de ouro do código: **a UI nunca altera o estado direto**. Ela chama `perform_move` ou `perform_attack`, que validam e só então alteram o estado.

---

## 2. Os dados: de onde vêm as unidades

Em `mockup.py`, cada unidade é um **dicionário** com:

| Grupo | Campos |
|---|---|
| Identidade | `name`, `job`, `team` ("player" ou "enemy") |
| Posição | `col`, `row` (coordenada de tile, não de pixel) |
| Status | `hp/max_hp`, `ap/max_ap` (AP = Pontos de Ação, exibido como "PA") |
| Combate | `skills` (lista de nomes), `ai` (só o monstro) |
| Visual | `sprite`, `width`, `height`, `offset_x/y`, `placeholder_color`, `avatar` |
| Controle | `is_draggable` (só o herói) |

Hoje existem duas unidades: o **herói** (50 HP, 5 AP, posição 0,4) e o **Poring** (50 HP, 2 AP, posição 9,4, IA `approach_and_attack`).

---

## 3. Geometria: como tile vira pixel

Em `battle_geometry.py`, o tabuleiro é 10x10, com losangos 2:1 (96x48 px).

```
x = origin_x + (col - row) * tile_width / 2
y = origin_y + (col + row) * tile_height / 2
```

- `tile_to_pixel(col, row)` calcula o centro do tile na tela.
- `pixel_to_tile(x, y)` é a inversa. O `round()` faz o "snap" para o tile mais próximo.
- `get_depth(unit)` é `col + row`. Quanto maior, mais perto do jogador, e a unidade é desenhada por cima.
- `get_sprite_bounds` posiciona o sprite pelos **pés**, ancorado no centro do tile, e serve também para *hit-test* (saber se o clique acertou o sprite).

---

## 4. O estado: `BattleState`

É o objeto central. Ele guarda:

- `units`: **cópia profunda** das unidades iniciais, para não alterar o mockup.
- `turn_order`: `["hero", "monster"]`, e `turn_index` indica de quem é a vez.
- `round`, `time_left` (30s por turno), `winner` (None, "victory" ou "defeat"), `log`.
- Flags de UI: `input_locked` (True durante o turno inimigo), `closed` (encerra o loop) e `version` (força re-render).

Métodos principais:

- **`end_turn()`**: avança o índice, pulando unidades mortas. Se o índice estoura a lista, volta a 0 e incrementa o `round`. Reseta o timer e **recarrega o AP da unidade que vai jogar**.
- **`tick()`**: chamado 1x por segundo; diminui `time_left`. Se chegar a 0, chama `end_turn()` e retorna True.
- **`check_battle_end()`**: vê se algum lado ficou sem unidades vivas, define `winner` e registra no log.
- **`unit_at(col, row)`**: devolve a unidade **viva** naquele tile.

---

## 5. As regras: `battle_actions.py`

### Skills

Por enquanto há uma só: `Basic Attack` (custo 1 AP, dano 10, alcance 1).

### Ataque

`can_attack` valida em ordem:

1. A batalha já acabou?
2. É a vez dessa unidade?
3. A unidade conhece a skill?
4. O alvo existe e está vivo?
5. O alvo é inimigo (sem fogo amigo)?
6. Há AP suficiente?
7. Está no alcance? (`in_range`: só vale **mesma coluna ou mesma linha**, distância entre 1 e `range`; diagonal não vale)

`perform_attack` chama `can_attack`. Se passou, desconta o AP, reduz o HP (com mínimo 0) e registra no log. Se o alvo morreu, registra a derrota dele e chama `check_battle_end()`.

### Movimento

`can_move` valida: batalha em andamento, vez da unidade, tile diferente do atual, dentro do tabuleiro, não bloqueado, não ocupado. **Custo = distância Manhattan** (1 AP por tile) e precisa caber no AP atual. `perform_move` atualiza `col/row`, desconta o AP e loga.

---

## 6. O loop de turnos (o coração do fluxo)

Fica em `battle_page.py`, dentro da função `turn_loop`, que roda como tarefa assíncrona iniciada no `on_mount`:

```
enquanto a tela estiver aberta e ninguém tiver vencido:

  ┌─ Se é turno INIMIGO ───────────────────────────────┐
  │  input_locked = True  → refresh                    │
  │  espera 0.7s                                       │
  │  para cada ação que a IA gerar (yield):            │
  │       refresh → espera 0.7s                        │
  │  end_turn() → input_locked = False → refresh       │
  └────────────────────────────────────────────────────┘

  ┌─ Se é turno do JOGADOR ────────────────────────────┐
  │  dorme 0.25s e acumula `elapsed`                   │
  │  a cada 1s completo → state.tick()                 │
  │     (se o tempo acabou, o turno passa sozinho)     │
  └────────────────────────────────────────────────────┘
```

O jogador age **durante esses intervalos**, pelos handlers da UI. O loop só cuida do relógio e do turno do monstro.

---

## 7. Turno do jogador, passo a passo

### 7.1 Mover (arrastar o herói)

Em `battle_board.py`, via `GestureDetector`:

1. **`on_pan_start`** (`handle_drag_start`): só prossegue se for a vez do jogador, se a unidade da vez for arrastável e se o ponteiro estiver **dentro do sprite**. Guarda no `_drag_state` o offset do clique, para o sprite não "pular" para o cursor.
2. **`on_pan_update`**: atualiza a posição virtual do token e força re-render. O sprite segue o mouse, e o tile de destino fica **dourado** (válido) ou **vermelho** (inválido), calculado com `can_move`.
3. **`on_pan_end`**: converte o pixel final em tile, chama `perform_move`. Se `ok`, chama `on_change()`. Se não, o sprite volta ao lugar, pois a posição real nunca mudou.

### 7.2 Atacar

1. Clicar no botão da skill (`skills_panel`) chama `handle_select_skill`, que guarda `selected_skill` (clicar de novo desmarca).
   - O botão **sempre tem `on_click` registrado**. A propriedade `enabled` (AP suficiente e vez do jogador) controla apenas a **aparência** (opacidade 1 ou 0.4).
   - A validação real acontece **dentro do handler**: `skills_panel` só repassa a chamada se `enabled` for verdadeiro, e `handle_select_skill` confere de novo `player_can_act()` e se `ap >= ap_cost`.
2. Com skill selecionada, o tabuleiro pinta os tiles de alcance (`get_attack_tiles`) em vermelho translúcido.
3. Clicar no tabuleiro dispara `handle_tap` (`on_tap_down`), que percorre os inimigos vivos **do mais próximo ao mais distante** (hit-test) e, se acertou um sprite, chama `perform_attack`. Se deu certo, a skill é desmarcada.

### 7.3 Encerrar turno

O botão "Turn End" chama `state.end_turn()`. Também fica desabilitado fora da vez do jogador.

---

## 8. Turno do monstro: a IA

Em `battle_ai.py`, cada comportamento é um **gerador Python**: cada `yield` significa "fiz uma ação, pode redesenhar e esperar". É assim que o monstro age de forma visível, uma ação por vez.

`approach_and_attack` (usado pelo Poring):

1. Acha o inimigo vivo mais próximo (`_nearest_enemy_id`, por distância Manhattan).
2. Se já pode atacar, vai direto ao passo 4.
3. Senão, `_best_approach_tile` testa **todos os tiles do tabuleiro** com `can_move` e escolhe o melhor pela chave `(consegue atacar de lá?, distância ao alvo, custo)`. Se nenhum tile melhora a situação, fica parado. Depois do `perform_move`, dá `yield`.
4. `attack_every_turn`: ataca repetidamente até `perform_attack` falhar (acabou o AP), com `yield` a cada golpe.

Com 2 AP, o Poring anda até 2 tiles. Só ataca no mesmo turno se, depois de andar, sobrar 1 AP. Os outros comportamentos são `passive` (não faz nada) e `attack_every_turn` (não anda).

---

## 9. Como a tela se atualiza

O `state` é um objeto **mutável** guardado em `use_state`. O Flet não percebe mudanças dentro dele, então o projeto usa um truque:

- `refresh()` faz `state.version += 1` e `set_tick(state.version)`. O contador muda, e a página re-renderiza.
- A `version` é passada como parâmetro para `battle_board`, para forçar o re-render dele também.
- O `battle_board` tem um `_drag_state` global de módulo e um contador próprio (`force_rerender`) para o arraste, que acontece várias vezes por segundo sem passar pela página.

Desenho do tabuleiro, em camadas dentro de um `Stack`:

1. **Fundo**: imagem, ou cor placeholder se o arquivo não existir (`asset_file_exists`).
2. **Grid**: `Canvas` com losangos estáticos (criados uma vez na importação) mais os destaques dinâmicos.
3. **Sprites**: só unidades vivas, ordenadas por profundidade. A unidade arrastada vai por último, para ficar por cima.

Painéis ao redor: `units_panel` (cards com HP/PA, borda dourada na unidade da vez), `skills_panel`, `battle_log_panel` e `turn_panel` (round, tempo ou "Enemy turn...", botões).

> **Regra dos handlers:** não alterne `on_click` entre `None` e função entre renders. O Flet pode não registrar de novo o handler, e o controle fica visualmente habilitado, mas sem reação ao clique (foi o bug de "não consigo selecionar a skill depois do round 1"). Mantenha o `on_click` sempre definido e valide dentro dele. Para `ft.Button`, usar `disabled=` é seguro.

---

## 10. Fim da batalha

Quando o HP de um alvo chega a 0, `perform_attack` chama `check_battle_end()`:

- Sem inimigos vivos: `winner = "victory"`.
- Sem jogadores vivos: `winner = "defeat"`.

Com `winner` definido, o `turn_loop` sai do `while`, `end_turn`, `tick` e as ações de ataque e movimento passam a recusar tudo, e o `turn_panel` mostra "Victory!" ou "Defeat...". O botão "Leave" só marca `state.closed = True` por enquanto (há um TODO para navegar de volta ao mapa).

---

## 11. Resumo: ciclo de vida de uma rodada

```
Início (round 1, vez do herói, 30s)
 │
 ├─ Jogador: move (arrasta) → perform_move → AP diminui
 ├─ Jogador: seleciona skill → clica no inimigo → perform_attack → HP diminui
 ├─ Jogador: "Turn End" (ou o tempo zera) → end_turn → vez do monstro, AP recarregado
 │
 ├─ Monstro: input bloqueado → IA gera ações → cada yield redesenha
 ├─ end_turn → índice volta a 0 → round += 1 → AP do herói recarregado
 │
 └─ Repete até alguém ficar com 0 HP → check_battle_end → Victory/Defeat
```

---

## 12. Pontos de atenção

Não são necessariamente bugs, mas vale saber:

1. **Movimento sem pathfinding**: o custo é a distância Manhattan direta, então a unidade "teleporta" e pode atravessar outras unidades. O arraste só valida o tile final.
2. **`skills_panel` fixo em `state.units["hero"]`**: o arraste só funciona para a unidade da vez, o que é coerente hoje, mas o painel de skills assume o herói fixo. Vira problema com mais de um personagem do jogador ou classes diferentes.
3. **`_drag_state` é global de módulo**: funciona com uma tela só, mas ficaria compartilhado entre batalhas simultâneas.
4. **Dados duplicados**: `SKILLS` está em `battle_actions.py` (TODO para o backend) e as unidades vêm do mockup, então ao integrar será preciso trocar essas duas fontes.
5. **Mensagem de log do ataque**: termina em `:` ("X uses Y in Z:") porque o dano é concatenado depois em `damage_text`. É intencional, só estranho quando lido isolado.
6. **Falhas silenciosas**: `[attack]` e `[move]` ainda só vão para o `print`. O jogador não vê por que uma ação foi recusada. Vale registrar o motivo no Battle Log ou em um texto temporário na tela.