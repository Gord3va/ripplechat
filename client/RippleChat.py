from typing import cast
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDFloatingActionButton
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.metrics import dp
from kivy.clock import Clock
import requests
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton



API_BASE_URL = "http://213.171.24.188:8000"  #  http://127.0.0.1:8000


class LoginScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(16))

        top_bar = MDTopAppBar(
            title="RippleChat · Вход",
            elevation=4,
            md_bg_color=(0.0, 0.48, 0.99, 1),
            specific_text_color=(1, 1, 1, 1),
        )
        root.add_widget(top_bar)

        form = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=(0, dp(24), 0, 0),
        )

        self.username_field = MDTextField(
            hint_text="Логин (ira, mama, seva)",
            mode="rectangle",
        )
        self.password_field = MDTextField(
            hint_text="Пароль",
            mode="rectangle",
            password=True,
        )

        login_btn = MDFloatingActionButton(
            icon="login",
            md_bg_color=(0.0, 0.48, 0.99, 1),
            icon_color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(dp(46), dp(46)),
            on_release=self.do_login,
        )

        form.add_widget(self.username_field)
        form.add_widget(self.password_field)
        form.add_widget(login_btn)

        root.add_widget(form)
        self.add_widget(root)

    def do_login(self, *args):
        username = self.username_field.text.strip()
        password = self.password_field.text.strip()
        if not username or not password:
            print("Пустой логин или пароль")
            return

        try:
            resp = requests.post(
                f"{API_BASE_URL}/login",
                data={"username": username, "password": password},
                timeout=5,
            )
            print("LOGIN status:", resp.status_code)
            print("LOGIN text:", resp.text)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print("Ошибка логина:", e)
            return

        app = MDApp.get_running_app()
        if app is None:
            print("Приложение MDApp ещё не запущено")
            return
        
        app = cast(RippleChatApp, app)

        app.api_token = data["access_token"]
        app.current_user_id = data["user_id"]
        app.current_username = username

        print("TOKEN SET:", app.api_token, "USER_ID:", app.current_user_id)

        app.chat_list_screen.load_chats()
        app.sm.current = "chat_list"


class ChatListScreen(MDScreen):

    def _do_logout(self, *args):
        app = MDApp.get_running_app()
        if app is None:
            return
        app = cast(RippleChatApp, app)
        app.logout()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = MDBoxLayout(orientation="vertical")

        top_bar = MDTopAppBar(
            title="RippleChat · Чаты",
            elevation=4,
            md_bg_color=(0.0, 0.48, 0.99, 1),
            specific_text_color=(1, 1, 1, 1),
        )
        top_bar.right_action_items = [
            ["logout", self._do_logout],
            ["plus", lambda x: self.create_chat_dialog()],
        ]
        root.add_widget(top_bar)

        self.current_user_label = MDLabel(
            text="Вы: ?",
            halign="left",
            size_hint_y=None,
            height=dp(24),
        )
        root.add_widget(self.current_user_label)

        scroll = MDScrollView()
        self.chat_list = MDList()
        scroll.add_widget(self.chat_list)
        root.add_widget(scroll)

        self.add_widget(root)

    def load_chats(self):
        app = MDApp.get_running_app()
        if app is None:
            print("Нет запущенного приложения MDApp")
            return

        if not app.api_token or not app.current_user_id:
            print("Нет токена или user_id")
            return
        if not app.api_token or not app.current_user_id:
            print("Нет токена или user_id")
            return

        headers = {"Authorization": f"Bearer {app.api_token}"}
        user_id = app.current_user_id

        self.current_user_label.text = f"Вы: {app.current_username}"
        self.chat_list.clear_widgets()

        try:
            resp = requests.get(
                f"{API_BASE_URL}/users/{user_id}/chats",
                headers=headers,
                timeout=5,
            )
            print("Chats status:", resp.status_code)
            print("Chats text:", resp.text)
            resp.raise_for_status()
            data = resp.json()
            print("Chats parsed json:", data, type(data))
        except Exception as e:
            print("Ошибка загрузки чатов:", e)
            return

        if not isinstance(data, list):
            print("Ожидал список чатов, а пришло что-то другое")
            return

        for chat in data:
            chat_id = chat["id"]
            title = chat["title"]
            item = OneLineListItem(
                text=title,
                on_release=lambda inst, cid=chat_id, ct=title: app.open_chat(cid, ct),
            )
            self.chat_list.add_widget(item)


    def create_chat_dialog(self):
        self.dialog = MDDialog(
            title="Новый чат",
            type="custom",
            content_cls=MDTextField(
                hint_text="Название чата",
            ),
            buttons=[
                MDFlatButton(
                    text="Отмена",
                    on_release=lambda x: self.dialog.dismiss(),
                ),
                MDFlatButton(
                    text="Создать",
                    on_release=lambda x: self._create_chat_from_dialog(),
                ),
            ],
        )
        self.dialog.open()

    def _create_chat_from_dialog(self):
        text_field = self.dialog.content_cls
        title = text_field.text.strip()
        if not title:
            return
        self.dialog.dismiss()

        app = MDApp.get_running_app()

        if app is None:
            print("Нет запущенного приложения MDApp")
            return
        app = cast(RippleChatApp, app)

        if not app.api_token or app.current_user_id is None:
            print("Нет токена или user_id при создании чата")
            return

        headers = {"Authorization": f"Bearer {app.api_token}"}
        user_id = app.current_user_id

        try:
            resp = requests.post(
                f"{API_BASE_URL}/chats",
                json={"title": title, "creator_id": user_id},
                headers=headers,
                timeout=5,
            )
            resp.raise_for_status()
        except Exception as e:
            print("Ошибка создания чата:", e)
            return

        self.load_chats()


class RippleChatScreen(MDScreen):
    def __init__(self, chat_id=None, chat_title="Чат", **kwargs):
        super().__init__(**kwargs)

        self.chat_id = chat_id
        self.chat_title = chat_title
        self.messages = []

        root = MDBoxLayout(orientation="vertical")

        self.top_bar = MDTopAppBar(
            title=f"RippleChat · {self.chat_title}",
            elevation=4,
            md_bg_color=(0.0, 0.48, 0.99, 1),
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self.go_back()]],
        )
        root.add_widget(self.top_bar)

        self.scroll = MDScrollView()
        self.chat_list = MDList()
        self.scroll.add_widget(self.chat_list)
        root.add_widget(self.scroll)

        bottom = MDBoxLayout(
            orientation="horizontal",
            padding=(dp(8), dp(4)),
            spacing=dp(8),
            size_hint_y=None,
            height=dp(60),
        )

        self.text_input = MDTextField(
            hint_text="Сообщение",
            mode="rectangle",
            multiline=False,
            text_color_normal=(0, 0, 0, 1),
            text_color_focus=(0, 0, 0, 1),
            hint_text_color_normal=(0.3, 0.3, 0.3, 1),
        )

        send_btn = MDFloatingActionButton(
            icon="send",
            md_bg_color=(0.0, 0.48, 0.99, 1),
            icon_color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(dp(46), dp(46)),
            on_release=self.send_message,
        )

        bottom.add_widget(self.text_input)
        bottom.add_widget(send_btn)
        root.add_widget(bottom)

        self.add_widget(root)

        Clock.schedule_interval(lambda dt: self.load_messages(), 3)

    def set_chat(self, chat_id, chat_title):
        self.chat_id = chat_id
        self.chat_title = chat_title
        self.top_bar.title = f"RippleChat · {self.chat_title}"
        self.load_messages()

    def go_back(self):
        app = MDApp.get_running_app()
        if app is None:
            return
        app = cast(RippleChatApp, app)
        app.sm.current = "chat_list"


    def load_messages(self, *args):
        if self.chat_id is None:
            return

        app = MDApp.get_running_app()
        if app is None:
            print("Нет запущенного приложения MDApp")
            return
        app = cast(RippleChatApp, app)

        if not app.api_token:
            print("Нет токена при загрузке сообщений")
            return

        headers = {"Authorization": f"Bearer {app.api_token}"}
        print("HEADERS FOR MESSAGES:", headers)

        try:
            resp = requests.get(
                f"{API_BASE_URL}/chats/{self.chat_id}/messages",
                headers=headers,
                timeout=5,
            )
            print("MSG status:", resp.status_code)
            print("MSG text:", resp.text)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print("Ошибка загрузки сообщений:", e)
            return

        self.messages = []
        for item in data:
            user_name = item.get("user_name", f"User {item['user_id']}")
            incoming = user_name != app.current_username

            self.messages.append(
                {
                    "text": item["text"],
                    "user": user_name,
                    "incoming": incoming,
                }
            )

        self.update_chat()

    def send_message(self, *args):
        text = self.text_input.text.strip()
        if not text or self.chat_id is None:
            return

        app = MDApp.get_running_app()

        if app is None:
                print("Нет запущенного приложения MDApp")
                return
        app = cast(RippleChatApp, app)

        headers = {"Authorization": f"Bearer {app.api_token}"}
        payload = {
            "user_id": app.current_user_id,
            "text": text,
        }

        try:
            resp = requests.post(
                f"{API_BASE_URL}/chats/{self.chat_id}/messages",
                json=payload,
                headers=headers,
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print("Ошибка отправки сообщения:", e)
            return

        self.messages.append(
            {
                "text": data["text"],
                "user": app.current_username,
                "incoming": False,
            }
        )
        self.text_input.text = ""
        self.update_chat()

    def update_chat(self):
        self.chat_list.clear_widgets()

        for msg in self.messages:
            text = msg["text"]
            user = msg["user"]
            incoming = msg.get("incoming", True)

            row = MDBoxLayout(
                orientation="horizontal",
                padding=(dp(8), dp(4)),
                size_hint_y=None,
            )
            row.bind(minimum_height=row.setter("height"))

            bubble = MDBoxLayout(
                orientation="vertical",
                padding=(dp(10), dp(6)),
                size_hint_x=0.8,
                md_bg_color=(1, 1, 1, 1) if incoming else (0.882, 0.996, 0.776, 1),
                radius=[dp(16), dp(16), dp(16), dp(16)],
                size_hint_y=None,
            )
            bubble.bind(minimum_height=bubble.setter("height"))

            label = MDLabel(
                text=f"{user}: {text}",
                theme_text_color="Custom",
                text_color=(0, 0, 0, 1),
                halign="left",
                valign="middle",
                size_hint_y=None,
            )
            label.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
            label.bind(
                texture_size=lambda inst, val: setattr(inst, "height", val[1])
            )

            bubble.add_widget(label)

            if incoming:
                row.add_widget(bubble)
                row.add_widget(MDBoxLayout(size_hint_x=0.2))
            else:
                row.add_widget(MDBoxLayout(size_hint_x=0.2))
                row.add_widget(bubble)

            self.chat_list.add_widget(row)


class RippleChatApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sm = ScreenManager(transition=NoTransition())
        self.api_token: str | None = None
        self.current_user_id: int | None = None
        self.current_username: str | None = None
        self.chat_list_screen: ChatListScreen

    def build(self):
        self.title = "RippleChat"
        self.theme_cls.theme_style = "Light"

        self.login_screen = LoginScreen(name="login")
        self.chat_list_screen = ChatListScreen(name="chat_list")
        self.chat_screen = RippleChatScreen(name="chat", chat_id=1, chat_title="Семейный чат")

        self.sm.add_widget(self.login_screen)
        self.sm.add_widget(self.chat_list_screen)
        self.sm.add_widget(self.chat_screen)

        self.sm.current = "login"
        return self.sm

    def open_chat(self, chat_id, chat_title):
        self.chat_screen.set_chat(chat_id, chat_title)
        self.sm.current = "chat"

    def logout(self):
        print("== logout")
        self.api_token = None
        self.current_user_id = None
        self.current_username = None
        self.chat_list_screen.chat_list.clear_widgets()
        self.chat_list_screen.current_user_label.text = "Вы: ?"
        self.sm.current = "login"


if __name__ == "__main__":
    RippleChatApp().run()
