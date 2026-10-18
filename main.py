import asyncio
import json
import threading
import requests
import websockets
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, RoundedRectangle

# ============================================================
SERVER_IP = "192.168.1.113"
API_URL = f"http://{SERVER_IP}:8000"
WS_URL = f"ws://{SERVER_IP}:8000/ws"
# ============================================================

THEMES = {
    "dark": {
        "bg": (0.08, 0.08, 0.12, 1),
        "surface": (0.15, 0.15, 0.22, 1),
        "text": (0.92, 0.92, 1, 1),
        "text_secondary": (0.55, 0.55, 0.65, 1),
        "accent": (0.48, 0.64, 0.97, 1),
        "bubble_own": (0.25, 0.35, 0.6, 1),
        "bubble_other": (0.2, 0.2, 0.28, 1),
        "error": (0.9, 0.3, 0.3, 1),
        "success": (0.35, 0.8, 0.45, 1),
    },
    "light": {
        "bg": (0.96, 0.96, 0.98, 1),
        "surface": (1, 1, 1, 1),
        "text": (0.1, 0.1, 0.15, 1),
        "text_secondary": (0.4, 0.4, 0.5, 1),
        "accent": (0.2, 0.4, 0.8, 1),
        "bubble_own": (0.7, 0.82, 1, 1),
        "bubble_other": (0.88, 0.88, 0.92, 1),
        "error": (0.8, 0.2, 0.2, 1),
        "success": (0.15, 0.6, 0.25, 1),
    },
}


def theme():
    return THEMES[App.get_running_app().theme]


class ThemedScreen(Screen):
    """Базовый экран с цветным фоном."""
    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._color = Color(*theme()["bg"])
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def refresh(self):
        t = theme()
        self._color.rgba = t["bg"]
        self.canvas.clear()
        self.clear_widgets()
        with self.canvas.before:
            Color(*t["bg"])
            Rectangle(pos=self.pos, size=self.size)
        self.build()


class AuthScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build()

    def build(self):
        t = theme()
        root = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(12))

        title = Label(text="Zed Messenger", font_size=dp(30),
                      bold=True, color=t["text"],
                      size_hint_y=None, height=dp(100))
        root.add_widget(title)

        self.user_input = TextInput(
            hint_text="Никнейм", multiline=False,
            size_hint_y=None, height=dp(52),
            background_color=t["surface"], foreground_color=t["text"],
            cursor_color=t["accent"], padding=[dp(14), dp(14)],
        )
        self.pass_input = TextInput(
            hint_text="Пароль", password=True, multiline=False,
            size_hint_y=None, height=dp(52),
            background_color=t["surface"], foreground_color=t["text"],
            cursor_color=t["accent"], padding=[dp(14), dp(14)],
        )
        root.add_widget(self.user_input)
        root.add_widget(self.pass_input)

        btn_login = Button(text="Войти", bold=True,
                           size_hint_y=None, height=dp(52),
                           background_color=t["accent"], color=(1, 1, 1, 1))
        btn_login.bind(on_press=self.do_login)

        btn_reg = Button(text="Регистрация",
                         size_hint_y=None, height=dp(52),
                         background_color=t["surface"], color=t["text"])
        btn_reg.bind(on_press=self.do_register)

        root.add_widget(btn_login)
        root.add_widget(btn_reg)

        self.status = Label(text="", color=t["text_secondary"],
                            size_hint_y=None, height=dp(40))
        root.add_widget(self.status)
        root.add_widget(Widget())
        self.add_widget(root)

    def _status(self, text, color_key):
        self.status.text = text
        self.status.color = theme()[color_key]

    def do_login(self, *a):
        u, p = self.user_input.text.strip(), self.pass_input.text
        if not u or not p:
            self._status("Заполните поля", "error")
            return
        self._status("Вход...", "text_secondary")

        def _run():
            try:
                r = requests.post(f"{API_URL}/login",
                                  json={"username": u, "password": p}, timeout=10)
                if r.status_code == 200:
                    app = App.get_running_app()
                    app.username = u
                    Clock.schedule_once(lambda dt: self._success())
                else:
                    msg = r.json().get("detail", "Ошибка")
                    Clock.schedule_once(lambda dt: self._status(msg, "error"))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._status(f"Сеть: {e}", "error"))

        threading.Thread(target=_run, daemon=True).start()

    def _success(self):
        self._status("Успех!", "success")
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "chatlist"

    def do_register(self, *a):
        u, p = self.user_input.text.strip(), self.pass_input.text
        if not u or not p:
            self._status("Заполните поля", "error")
            return
        self._status("Регистрация...", "text_secondary")

        def _run():
            try:
                r = requests.post(f"{API_URL}/register",
                                  json={"username": u, "password": p}, timeout=10)
                if r.status_code == 200:
                    Clock.schedule_once(lambda dt: self._status("Аккаунт создан", "success"))
                else:
                    msg = r.json().get("detail", "Ошибка")
                    Clock.schedule_once(lambda dt: self._status(msg, "error"))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._status(f"Сеть: {e}", "error"))

        threading.Thread(target=_run, daemon=True).start()


class ChatListScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build()

    def build(self):
        t = theme()
        root = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))

        # Заголовок с балансом и кнопкой темы
        header = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        app = App.get_running_app()
        header.add_widget(Label(text=f"Вы: {app.username}", color=t["text"],
                                 bold=True, halign="left"))
        self.balance_lbl = Label(text="💰 ...", color=t["accent"], bold=True,
                                   size_hint_x=0.4)
        header.add_widget(self.balance_lbl)
        btn_theme = Button(text="🌓", size_hint_x=0.15,
                           background_color=t["surface"], color=t["text"])
        btn_theme.bind(on_press=self.toggle_theme)
        header.add_widget(btn_theme)
        root.add_widget(header)

        # Кнопка "обновить"
        btn_refresh = Button(text="Обновить контакты",
                             size_hint_y=None, height=dp(45),
                             background_color=t["accent"], color=(1, 1, 1, 1))
        btn_refresh.bind(on_press=lambda *a: self.load_users())
        root.add_widget(btn_refresh)

        # Прокручиваемый список
        scroll = ScrollView()
        self.list_layout = GridLayout(cols=1, spacing=dp(6),
                                       size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        scroll.add_widget(self.list_layout)
        root.add_widget(scroll)

        self.add_widget(root)
        Clock.schedule_once(lambda dt: self.load_users(), 0.2)

    def toggle_theme(self, *a):
        app = App.get_running_app()
        app.theme = "light" if app.theme == "dark" else "dark"
        # Простое пересоздание экранов
        Clock.schedule_once(lambda dt: app.rebuild_screens(), 0.1)

    def load_users(self):
        def _run():
            try:
                r = requests.get(f"{API_URL}/users", timeout=10)
                users = r.json() if r.status_code == 200 else []
                Clock.schedule_once(lambda dt: self.populate(users))
            except Exception as e:
                print("Load users error:", e)
        threading.Thread(target=_run, daemon=True).start()

    def populate(self, users):
        self.list_layout.clear_widgets()
        t = theme()
        app = App.get_running_app()
        for u in users:
            if u["username"] == app.username:
                # Свой баланс
                self.balance_lbl.text = f"💰 {u['balance']}"
                continue
            btn = Button(text=f"{u['username']}  ·  💰 {u['balance']}",
                         size_hint_y=None, height=dp(60),
                         background_color=t["surface"], color=t["text"],
                         halign="left")
            btn.bind(on_press=lambda inst, name=u["username"]: self.open_chat(name))
            self.list_layout.add_widget(btn)

    def open_chat(self, contact):
        chat = self.manager.get_screen("chat")
        chat.contact = contact
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "chat"


class ChatScreen(ThemedScreen):
    contact = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.contact = ""
        self._ws = None
        self._loop = None
        self.build()

    def build(self):
        t = theme()
        root = BoxLayout(orientation='vertical')

        # Заголовок с кнопкой "назад"
        header = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(8),
                            padding=[dp(8), dp(8)])
        back = Button(text="←", size_hint_x=0.15,
                      background_color=t["surface"], color=t["text"])
        back.bind(on_press=self.go_back)
        header.add_widget(back)
        self.title_lbl = Label(text=self.contact, color=t["text"], bold=True)
        header.add_widget(self.title_lbl)
        # Кнопка "подарок"
        gift = Button(text="🎁", size_hint_x=0.15,
                      background_color=t["surface"], color=t["text"])
        gift.bind(on_press=self.show_gift_dialog)
        header.add_widget(gift)
        root.add_widget(header)

        # Область сообщений
        self.scroll = ScrollView()
        self.messages = GridLayout(cols=1, spacing=dp(6),
                                     size_hint_y=None, padding=[dp(8), dp(8)])
        self.messages.bind(minimum_height=self.messages.setter("height"))
        self.scroll.add_widget(self.messages)
        root.add_widget(self.scroll)

        # Поле ввода
        input_row = BoxLayout(size_hint_y=None, height=dp(55),
                                spacing=dp(6), padding=[dp(6), dp(6)])
        self.input = TextInput(hint_text="Сообщение...", multiline=False,
                                background_color=t["surface"],
                                foreground_color=t["text"],
                                cursor_color=t["accent"],
                                padding=[dp(12), dp(12)])
        send = Button(text="→", size_hint_x=0.2, bold=True,
                      background_color=t["accent"], color=(1, 1, 1, 1))
        send.bind(on_press=self.send)
        input_row.add_widget(self.input)
        input_row.add_widget(send)
        root.add_widget(input_row)

        self.add_widget(root)

    def on_enter(self):
        self.title_lbl.text = self.contact
        # Загрузка истории
        self.load_history()
        # Запуск WS
        threading.Thread(target=self._ws_thread, daemon=True).start()

    def load_history(self):
        app = App.get_running_app()
        def _run():
            try:
                r = requests.get(f"{API_URL}/history/{app.username}/{self.contact}",
                                  timeout=10)
                if r.status_code == 200:
                    Clock.schedule_once(lambda dt: self.render_history(r.json()))
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    def render_history(self, history):
        self.messages.clear_widgets()
        app = App.get_running_app()
        for m in history:
            self._add_bubble(m["sender"], m["text"],
                              m["sender"] == app.username)

    def _ws_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._ws_loop())
        except Exception as e:
            print("WS error:", e)

    async def _ws_loop(self):
        app = App.get_running_app()
        async with websockets.connect(f"{WS_URL}/{app.username}") as ws:
            self._ws = ws
            async for msg in ws:
                Clock.schedule_once(lambda dt, m=msg: self._on_message(m))

    def _on_message(self, msg_json):
        try:
            data = json.loads(msg_json)
            sender = data.get("sender", "?")
            text = data.get("text", "")
            # Показываем только сообщения от/для текущего контакта
            app = App.get_running_app()
            if (sender == self.contact) or (sender == app.username):
                self._add_bubble(sender, text, sender == app.username)
        except Exception:
            pass

    def _add_bubble(self, sender, text, is_own):
        t = theme()
        bubble = Label(
            text=text,
            color=t["text"],
            size_hint_x=0.78,
            size_hint_y=None,
            text_size=(Window.width * 0.7, None),
            halign="left", valign="top",
            padding=[dp(12), dp(10)],
        )
        bubble.bind(texture_size=lambda i, v: setattr(i, "height", v[1] + dp(18)))

        with bubble.canvas.before:
            bubble._color = Color(*(t["bubble_own"] if is_own else t["bubble_other"]))
            bubble._rect = RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=[dp(14)])
        bubble.bind(pos=lambda *a: setattr(bubble._rect, "pos", bubble.pos))
        bubble.bind(size=lambda *a: setattr(bubble._rect, "size", bubble.size))

        row = BoxLayout(size_hint_y=None, spacing=dp(4))
        row.bind(minimum_height=row.setter("height"))
        if is_own:
            row.add_widget(Widget(size_hint_x=0.22))
            row.add_widget(bubble)
        else:
            row.add_widget(bubble)
            row.add_widget(Widget(size_hint_x=0.22))

        self.messages.add_widget(row)
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.05)

    def send(self, *a):
        text = self.input.text.strip()
        if not text or not self._ws or not self._loop:
            return
        payload = json.dumps({"receiver": self.contact, "text": text})
        try:
            asyncio.run_coroutine_threadsafe(self._ws.send(payload), self._loop)
            self.input.text = ""
        except Exception as e:
            print("Send error:", e)

    def go_back(self, *a):
        # Закрыть WS
        if self._ws and self._loop:
            try:
                asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)
            except Exception:
                pass
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "chatlist"

    def show_gift_dialog(self, *a):
        # Простое модальное окно через Popup
        from kivy.uix.popup import Popup
        t = theme()
        content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        amount = TextInput(text="10", multiline=False, input_filter="int",
                           background_color=t["surface"], foreground_color=t["text"])
        content.add_widget(Label(text=f"Подарить {self.contact}:", color=t["text"]))
        content.add_widget(amount)

        def do_gift(*args):
            app = App.get_running_app()
            try:
                r = requests.post(f"{API_URL}/gift", json={
                    "from_user": app.username,
                    "to_user": self.contact,
                    "amount": int(amount.text or 0)
                }, timeout=10)
                if r.status_code == 200:
                    print("Gift sent!")
            except Exception as e:
                print("Gift error:", e)
            popup.dismiss()

        btn = Button(text="Отправить", size_hint_y=None, height=dp(45),
                     background_color=t["accent"], color=(1, 1, 1, 1))
        btn.bind(on_press=do_gift)
        content.add_widget(btn)

        popup = Popup(title="🎁 Подарок", content=content,
                       size_hint=(0.85, 0.4))
        popup.open()


class MessengerApp(App):
    username = StringProperty("")
    theme = StringProperty("dark")

    def build(self):
        self.sm = ScreenManager()
        self._add_screens()
        return self.sm

    def _add_screens(self):
        self.sm.clear_widgets()
        self.sm.add_widget(AuthScreen(name="auth"))
        self.sm.add_widget(ChatListScreen(name="chatlist"))
        self.sm.add_widget(ChatScreen(name="chat"))
        self.sm.current = "auth"

    def rebuild_screens(self):
        current = self.sm.current
        self._add_screens()
        self.sm.current = current


if __name__ == "__main__":
    MessengerApp().run()
