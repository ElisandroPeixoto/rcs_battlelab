import asyncio
import flet as ft
import themes as t
from mockup import INITIAL_UNITS
from services.battle_state import BattleState
from services.battle_ai import iter_ai_turn
from components.battle_board import battle_board
from components.unit_card import units_panel
from components.skills_panel import skills_panel
from components.battle_log_panel import battle_log_panel
from components.turn_panel import turn_panel
from services.battle_geometry import BoardConfig
from services.battle_actions import SKILLS

board_config = BoardConfig()


BOARD_WIDTH, BOARD_HEIGHT = 1100, 700
LEFT_WIDTH = 330
RIGHT_PANEL_WIDTH = 300
BOTTOM_HEIGHT = 200
GAP = 16
CONTENT_WIDTH = LEFT_WIDTH + GAP + BOARD_WIDTH

ENEMY_ACTION_DELAY = 0.7      # segundos entre as ações do monstro (para dar para acompanhar)
TICK_INTERVAL = 0.25          # o loop acorda 4x por segundo; o relógio do turno conta 1x por segundo

@ft.component
def battle_page():
    state, _ = ft.use_state(BattleState(INITIAL_UNITS, board_config))
    _, set_tick = ft.use_state(0)
    selected_skill, set_selected_skill = ft.use_state(None)

    def refresh(clear_skill: bool = False):
        """Chamado depois de QUALQUER mudança no estado: re-renderiza a página."""
        if clear_skill:
            set_selected_skill(None)
        state.version += 1
        set_tick(state.version)

    # ---------- PASSO 11: loop de turnos (timer + turno do monstro) ----------
    def on_mount():
        async def turn_loop():
            elapsed = 0.0
            while not state.closed and state.winner is None:
                if state.current_unit()["team"] == "enemy":
                    state.input_locked = True
                    refresh(clear_skill=True)
                    await asyncio.sleep(ENEMY_ACTION_DELAY)
                    for _ in iter_ai_turn(state, state.current_unit_id):
                        refresh()
                        await asyncio.sleep(ENEMY_ACTION_DELAY)
                    if state.closed:
                        break
                    state.end_turn()
                    state.input_locked = False
                    elapsed = 0.0
                    refresh()
                else:
                    await asyncio.sleep(TICK_INTERVAL)
                    elapsed += TICK_INTERVAL
                    if elapsed >= 1.0 and not state.closed:
                        elapsed = 0.0
                        if state.tick():                  # o tempo acabou: turno passou sozinho
                            refresh(clear_skill=True)
                        else:
                            refresh()

        ft.context.page.run_task(turn_loop)

    def on_unmount():
        state.closed = True       # para o loop quando a tela sair

    ft.use_effect(on_mount, [], cleanup=on_unmount)

    # ---------- handlers ----------
    def player_can_act() -> bool:
        return (state.winner is None and not state.input_locked
                and state.current_unit()["team"] == "player")

    def handle_select_skill(name: str):
        if not player_can_act():
            return
        if state.current_unit()["ap"] < SKILLS[name]["ap_cost"]:
            return
        set_selected_skill(None if selected_skill == name else name)

    def handle_end_turn(e):
        if not player_can_act():
            return
        state.end_turn()
        refresh(clear_skill=True)

    def handle_leave(e):
        state.closed = True
        # TODO: no jogo principal, navegar de volta ao mapa: navigate_to_map(character["current_map_id"])
        print("Leave: no laboratório só encerra o loop de turnos.")
        refresh(clear_skill=True)

    # ---------- layout ----------
    log_width = CONTENT_WIDTH - LEFT_WIDTH - RIGHT_PANEL_WIDTH - 2 * GAP

    top_row = ft.Row(
        spacing=GAP,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            units_panel(state, LEFT_WIDTH, BOARD_HEIGHT),
            battle_board(state, state.version, selected_skill, refresh),
        ],
    )

    bottom_row = ft.Row(
        spacing=GAP,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            skills_panel(state, selected_skill, handle_select_skill, LEFT_WIDTH, BOTTOM_HEIGHT),
            battle_log_panel(state.log.entries, log_width, BOTTOM_HEIGHT),
            turn_panel(state, handle_end_turn, handle_leave, RIGHT_PANEL_WIDTH, BOTTOM_HEIGHT),
        ],
    )

    return ft.Container(
        expand=True,
        bgcolor=t.PAGE_BACKGROUND_COLOR,
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=CONTENT_WIDTH,
                    padding=ft.Padding.symmetric(vertical=16),
                    content=ft.Column(spacing=GAP, controls=[top_row, bottom_row]),
                ),
            ],
        ),
    )
