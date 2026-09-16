"""The wizard's main window.

Owns the left and right panelsand handles start animation. 
Business logic itself (detection, install dispatch) lives 
in ``app.core`` -- here are signals connecting ui and core.
"""
from __future__ import annotations

from collections.abc import Callable

import sys

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QParallelAnimationGroup, QRect, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QMainWindow, QStackedLayout, QVBoxLayout, QWidget

from app.constants import (
    BACK_BUTTON_MARGIN,
    NETWORK_POLLING_DELAY_MS,
    USB_POLLING_DELAY_MS,
    INTRO_DELAY_MS,
    LEFT_PANEL_RATIO,
    LOGO_MOVE_DURATION_MS,
    LOGO_SIZE_CENTERED,
    LOGO_SIZE_DOCKED,
    PANEL_FADE_DURATION_MS,
    SCREEN_FADE_IN_MS,
    SCREEN_FADE_OUT_MS,
    WINDOW_SIZE,
)
from app.core.installer import InstallerLauncher
from app.core.robot_detector import RobotDetector
from app.core.server_detector import ServerDetector
from app.i18n import Translator
from app.widgets.connect_screen import ConnectScreen
from app.widgets.logo import LogoWidget
from app.widgets.welcome_screen import WelcomeScreen
from app.widgets.back_button import BackButton
from app.widgets.find_vaacula_server import FindVaaculaServer
from app.widgets.wifi_screen import WifiScreen

from app.core.session import SessionData
import usb.core # type: ignore[reportMissingTypeStubs]


def _clear_graphics_effect(widget: QWidget) -> None:
    # Pyside has annoying stub, this gets rid of errors shown by linter
    # QT documents None as proper way to clear effect: https://doc.qt.io/qt-6/qgraphicsitem.html#setGraphicsEffect
    widget.setGraphicsEffect(None)  # type: ignore[arg-type]

class MainWindow(QMainWindow):
    def __init__(self, translator: Translator) -> None:
        super().__init__()
        self._translator = translator
        self._session = SessionData()

        # Keep references to in-flight animations: QPropertyAnimation
        # doesn't guarantee its C++ side survives being garbage
        # collected mid-animation otherwise.
        self._active_animations: list[QPropertyAnimation | QParallelAnimationGroup] = []

        self.setFixedSize(*WINDOW_SIZE)
        self._translator.languageChanged.connect(self._retranslate)

        central = QWidget(self)
        central.setObjectName("central")
        self.setCentralWidget(central)

        self._left_panel = QWidget(central)
        self._left_panel.setObjectName("leftPanel")
        self._left_panel.setGeometry(self._left_panel_rect())

        self._back_action: Callable[[], None] | None = None
        self._back_button = BackButton(self._left_panel)
        self._back_button.move(BACK_BUTTON_MARGIN, BACK_BUTTON_MARGIN)
        self._back_button.clicked.connect(self._go_back)

        self._right_panel = QWidget(central)
        self._right_panel.setObjectName("rightPanel")
        self._right_panel.setGeometry(self._right_panel_rect())
        self._right_panel_opacity = QGraphicsOpacityEffect(self._right_panel)
        self._right_panel_opacity.setOpacity(0.0)
        self._right_panel.setGraphicsEffect(self._right_panel_opacity)

        right_layout = QVBoxLayout(self._right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._screen_stack = QStackedLayout()
        right_layout.addLayout(self._screen_stack)

        self._welcome_screen = WelcomeScreen(self._translator, self._right_panel)
        self._connect_screen = ConnectScreen(self._translator, self._right_panel)
        self._screen_stack.addWidget(self._welcome_screen)
        self._screen_stack.addWidget(self._connect_screen)

        self._server_search_screen = FindVaaculaServer(self._translator, self._right_panel)
        self._screen_stack.addWidget(self._server_search_screen)

        self._connect_to_wifi_screen = WifiScreen(self._translator, self._right_panel)
        self._screen_stack.addWidget(self._connect_to_wifi_screen)

        # Logo starts centered on the whole window, on top of everything,
        # then animates into its resting spot in the left panel.
        self._logo = LogoWidget(central)
        self._logo.setGeometry(self._logo_centered_rect())
        self._logo.raise_()

        self._robot_detector = RobotDetector(self)
        self._installer = InstallerLauncher(self)
        self._server_detector = ServerDetector(self)

        self._connect_signals()
        self._retranslate()

        QTimer.singleShot(INTRO_DELAY_MS, self._play_intro_animation)

    # -- geometry helpers -----------------------------------------------------

    @staticmethod
    def _left_panel_rect() -> QRect:
        width, height = WINDOW_SIZE
        return QRect(0, 0, int(width * LEFT_PANEL_RATIO), height)

    @staticmethod
    def _right_panel_rect() -> QRect:
        width, height = WINDOW_SIZE
        left_width = int(width * LEFT_PANEL_RATIO)
        return QRect(left_width, 0, width - left_width, height)

    @staticmethod
    def _logo_centered_rect() -> QRect:
        width, height = WINDOW_SIZE
        size = LOGO_SIZE_CENTERED
        return QRect((width - size) // 2, (height - size) // 2, size, size)

    def _logo_docked_rect(self) -> QRect:
        left_rect = self._left_panel_rect()
        size = LOGO_SIZE_DOCKED
        x = left_rect.x() + (left_rect.width() - size) // 2
        y = left_rect.y() + (left_rect.height() - size) // 2
        return QRect(x, y, size, size)

    # -- intro animation -------------------------------------------------------

    def _play_intro_animation(self) -> None:
        animation = QPropertyAnimation(self._logo, b"geometry", self)
        animation.setDuration(LOGO_MOVE_DURATION_MS)
        animation.setStartValue(self._logo.geometry())
        animation.setEndValue(self._logo_docked_rect())
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.finished.connect(self._reveal_right_panel)
        self._run(animation)

    def _reveal_right_panel(self) -> None:
        animation = QPropertyAnimation(self._right_panel_opacity, b"opacity", self)
        animation.setDuration(PANEL_FADE_DURATION_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        # A QGraphicsOpacityEffect left attached keeps compositing every
        # repaint so remove when finished
        animation.finished.connect(lambda: _clear_graphics_effect(self._right_panel))
        self._run(animation)

    # -- screen transitions -----------------------------------------------------

    def _crossfade_to(self, target: QWidget) -> None:
        """Fade the current right-panel screen out, then the target in."""
        current = self._screen_stack.currentWidget()
        if current is None or current is target:
            return

        fade_out_effect = QGraphicsOpacityEffect(current)
        current.setGraphicsEffect(fade_out_effect)
        fade_out = QPropertyAnimation(fade_out_effect, b"opacity", self)
        fade_out.setDuration(SCREEN_FADE_OUT_MS)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.finished.connect(lambda: self._switch_and_fade_in(current, target))
        self._run(fade_out)

    def _switch_and_fade_in(self, previous: QWidget, target: QWidget) -> None:
        _clear_graphics_effect(previous)

        self._screen_stack.setCurrentWidget(target)

        fade_in_effect = QGraphicsOpacityEffect(target)
        target.setGraphicsEffect(fade_in_effect)
        fade_in = QPropertyAnimation(fade_in_effect, b"opacity", self)
        fade_in.setDuration(SCREEN_FADE_IN_MS)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.finished.connect(lambda: _clear_graphics_effect(target))
        self._run(fade_in)

    def _run(self, animation: QPropertyAnimation) -> None:
        """Start an animation and keep it alive until it finishes."""
        self._active_animations.append(animation)
        animation.finished.connect(lambda: self._active_animations.remove(animation))
        animation.start()

    # -- back navigation ---------------------------------------------------------

    def _set_back_action(self, action: Callable[[], None] | None) -> None:
        """Set what clicking "back" does right now (or hide the button)."""
        self._back_action = action
        self._back_button.setVisible(action is not None)

    def _go_back(self) -> None:
        if self._back_action is not None:
            self._back_action()

    # -- signal wiring & handlers ------------------------------------------------
    # TODO rename from handle_event to go_to_page, let signal be descriptor what event happened and function what is to happen
    def _connect_signals(self) -> None:
        # TODO: conditionally skip pages if session is already populated? Or recheck?
        self._welcome_screen.continueRequested.connect(self._select_dev_or_server_screen)

        self._server_detector.serverDetected.connect(self._goto_connect_robot_screen)

        self._robot_detector.robotDetected.connect(self._goto_connect_robot_screen_firmware)
        self._robot_detector.multipleRobotsDetected.connect(self._handle_multiple_robots)
        # TODO robot disconnected, just pass to handler inside connect_robot_screen

        self._connect_screen.startInstallRequested.connect(self._goto_wifi_screen) # TODO wrong name signal and order
        self._connect_to_wifi_screen.wifiAdded.connect(self._goto_install_screen)


    def _select_dev_or_server_screen(self)->None:
        if not getattr(sys, "frozen", False):
            self._goto_dev_only_screen() # Not implemented yet
            #self._goto_server_search_screen() # Temporary
        else:
            self._goto_server_search_screen()

    def _goto_dev_only_screen(self)->None:
        print("Not implemented yet") #TODO
        self._crossfade_to(self._connect_screen)
        self._connect_screen.reset_searching()
        #self._connect_to_wifi_screen.set_gen23_page()
        #self._connect_to_wifi_screen.set_gen23_wifi_options(["Antons hemliga wifi ", "  tillåtet wifi  "])

    def _goto_server_search_screen(self) -> None:
        self._crossfade_to(self._server_search_screen)
        self._server_detector.start(NETWORK_POLLING_DELAY_MS)
        self._set_back_action(self._back_to_welcome)

    def _goto_connect_robot_screen(self, ip: str, cert: str) -> None:
        anim = self._server_search_screen.show_server_detected(ip)
        self._active_animations.append(anim)
        self._session.server_ip = ip
        self._session.server_certificate = cert
        # Dont @ me
        anim.finished.connect(lambda: QTimer.singleShot(2000, lambda : {self._crossfade_to(self._connect_screen) , self._robot_detector.start(USB_POLLING_DELAY_MS)}))
        anim.finished.connect(lambda: self._active_animations.remove(anim))
        anim.start()
        self._connect_screen.reset_searching()
        self._set_back_action(self._back_to_welcome)

    def _goto_connect_robot_screen_firmware(self, display_name: str, device: usb.core.Device) -> None:
        self._session.robot_model_display_name = display_name
        self._session.robot_usb_device = device
        self._connect_screen.show_robot_detected(display_name)
        self._robot_detector.stop() #maybe keep running for disconnect notices? TODO

    def _handle_multiple_robots(self) -> None:
        # TODO: Inform user about one at a time limit
        return None # Tmp python bsittery
    
    def _handle_robot_disconnected(self) -> None:
        # TODO: For detecting reboot or unintentional disconnections
        return None


    def _goto_wifi_screen(self)->None:
        match self._session.robot_model_display_name:
            case "Neato D10" | "Neato D9" | "Neato D8":
                self._crossfade_to(self._connect_to_wifi_screen)
            case "Neato Botvac D7"|"Neato Botvac D6"|"Neato Botvac D5"|"Neato Botvac D4"|"Neato Botvac D3"|"Neato Botvac Connected":
                self._crossfade_to(self._connect_to_wifi_screen)
                self._connect_to_wifi_screen.set_gen23_page()
            case "Neato D800":
                print("I don't think this one is supported") # temp TODO
            case _:
                print("How the hell did you get here?")

    def _goto_install_screen(self, ssid: str, password: str) -> None:
        self._session.wifi_ssid = ssid
        self._session.wifi_pass = password
        self._robot_detector.start(USB_POLLING_DELAY_MS)# Temp placeholder
        self._crossfade_to(self._connect_screen)
        self._set_back_action(self._back_to_wifi)


    def _back_to_welcome(self) -> None:
        self._robot_detector.stop()
        self._server_detector.stop()
        self._server_search_screen.reset_searching()
        self._connect_screen.reset_searching()
        self._crossfade_to(self._welcome_screen)
        self._set_back_action(None)

    def _back_to_wifi(self) -> None:
        self._robot_detector.stop() # Temp placeholder
        self._crossfade_to(self._connect_to_wifi_screen)
        self._set_back_action(self._back_to_welcome)
        self._connect_to_wifi_screen.wifi_revalidate_input()


    def _retranslate(self) -> None:
        self.setWindowTitle(self._translator.tr("app.window_title"))
