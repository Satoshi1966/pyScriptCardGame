"""PyScript 神経衰弱ゲーム：カードを2枚ずつめくって同じ絵柄を探します。"""
import asyncio
import random
from js import document, localStorage
from pyodide.ffi import create_proxy

# ===== 改造ポイント（まずはここを変更してみよう） =====
SYMBOLS = ["🍎", "🍋", "🍇", "🍓", "🍒", "🍉"]
WAIT_SECONDS = 1.0  # 不一致のカードを見せる秒数
BEST_KEY = "memory_game_best_v1"

# ===== ゲームの状態 =====
cards = []            # シャッフルされた12枚の絵柄
opened = []           # 現在めくっているカードの番号（最大2つ）
matched = set()       # 見つけたカードの番号
turns = 0             # 2枚めくると1回
busy = False          # 不一致のカードを表示している間はTrue
game_id = 0           # リセット前の待機処理を無効にするための番号
card_buttons = []
event_proxies = []    # イベント関数を保持してGCを防ぐ


def element(element_id):
    return document.getElementById(element_id)


def say(text):
    element("message").textContent = text


def update_score():
    element("turns").textContent = str(turns)
    element("pairs").textContent = f"{len(matched) // 2} / {len(SYMBOLS)}"
    best = localStorage.getItem(BEST_KEY)
    element("best").textContent = f"{best}回" if best is not None else "—"


def draw_card(index):
    """1枚のカードの見た目を更新します。"""
    button = card_buttons[index]
    is_open = index in opened
    is_matched = index in matched
    button.textContent = cards[index] if (is_open or is_matched) else "?"
    button.className = "card"
    if is_matched:
        button.classList.add("matched")
    elif is_open:
        button.classList.add("open")
    button.disabled = is_matched or is_open or busy
    button.setAttribute("aria-label", "カード" + str(index + 1) + (" " + cards[index] if (is_open or is_matched) else " 裏向き"))


def draw_all():
    for index in range(len(cards)):
        draw_card(index)
    update_score()


async def close_unmatched(current_game):
    """一致しなかったカードを少し待ってから裏返します。"""
    global busy
    await asyncio.sleep(WAIT_SECONDS)
    if current_game != game_id:  # 待機中にリセットされた場合
        return
    opened.clear()
    busy = False
    say("もう一度、2枚選んでください。")
    draw_all()


def select_card(index):
    """カードが押されたときの処理です。"""
    global turns, busy
    if busy or index in matched or index in opened:
        return

    opened.append(index)
    draw_all()
    if len(opened) < 2:
        say("もう1枚選んでください。")
        return

    turns += 1
    first, second = opened
    if cards[first] == cards[second]:
        matched.update(opened)
        opened.clear()
        say("正解！ 同じ絵柄です 🎉")
        if len(matched) == len(cards):
            best_raw = localStorage.getItem(BEST_KEY)
            if best_raw is None or turns < int(best_raw):
                localStorage.setItem(BEST_KEY, str(turns))
            say(f"クリア！ {turns}回ですべてそろえました！ 🏆")
    else:
        busy = True
        say("残念！ 1秒後に裏返します。")
        asyncio.ensure_future(close_unmatched(game_id))
    draw_all()


def new_game(event=None):
    """カードを並べ直し、ゲームを最初から始めます。"""
    global cards, opened, matched, turns, busy, game_id
    game_id += 1
    cards = SYMBOLS * 2
    random.shuffle(cards)
    opened = []
    matched = set()
    turns = 0
    busy = False

    board = element("board")
    board.innerHTML = ""
    card_buttons.clear()
    for index in range(len(cards)):
        button = document.createElement("button")
        button.type = "button"
        button.className = "card"
        # デフォルト引数に番号を保存し、どのカードかを区別する
        callback = create_proxy(lambda event, i=index: select_card(i))
        event_proxies.append(callback)
        button.addEventListener("click", callback)
        board.appendChild(button)
        card_buttons.append(button)
    say("カードを2枚選んでください。")
    draw_all()


# ===== 起動：関数を定義した後にイベントを登録 =====
restart_callback = create_proxy(new_game)
event_proxies.append(restart_callback)
element("restart").addEventListener("click", restart_callback)
new_game()
