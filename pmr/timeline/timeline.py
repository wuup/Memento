import pygame
from pmr.timeline.frame_getter import FrameGetter
from pmr.timeline.time_bar import TimeBar
from pmr.timeline.search_bar import SearchBar
from pmr.timeline.region_selector import RegionSelector
import pmr.utils as utils
import pyperclip
from pmr.timeline.ui import PopUpManager
import time


class Timeline:
    def __init__(self):
        self.window_size = utils.RESOLUTION

        # Faster than pygame.init()
        pygame.display.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode(self.window_size, flags=pygame.SRCALPHA)
        # +pygame.HIDDEN
        pygame.key.set_repeat(500, 50)
        self.clock = pygame.time.Clock()

        self.ctrl_pressed = False

        self.update()

        self.t = 0
        self.dt = 0

    def update(self):
        start = time.time()
        self.frame_getter = FrameGetter(self.window_size)
        self.time_bar = TimeBar(self.frame_getter)
        self.search_bar = SearchBar(self.frame_getter)
        self.region_selector = RegionSelector()
        self.popup_manager = PopUpManager()

    def draw_current_frame(self):
        frame = self.frame_getter.get_frame(self.time_bar.current_frame_i)
        surf = pygame.surfarray.make_surface(frame).convert()
        self.screen.blit(surf, (0, 0))

    def handle_inputs(self):
        found = False
        mouse_wheel = 0
        for event in pygame.event.get():
            found = self.search_bar.event(event)
            if event.type == pygame.MOUSEWHEEL:
                mouse_wheel = event.x - event.y
                if not self.ctrl_pressed:
                    self.time_bar.move_cursor((mouse_wheel))
                    self.region_selector.reset()
                    self.frame_getter.clear_annotations()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if self.time_bar.hover(event.pos):
                        self.time_bar.set_current_frame_i(
                            self.time_bar.get_frame_i(event.pos)
                        )
                        self.region_selector.reset()
                    else:
                        self.search_bar.deactivate()
                        self.region_selector.start(event.pos)
                        self.time_bar.hide()
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if self.time_bar.hover(event.pos):
                        continue
                    self.time_bar.show()
                    if self.search_bar.active:
                        continue
                    self.region_selector.end(event.pos)
                    frame = self.frame_getter.get_frame(
                        self.time_bar.current_frame_i
                    ).swapaxes(0, 1)
                    res = self.region_selector.region_ocr(frame)
                    if res is None:
                        continue
                    self.frame_getter.clear_annotations()
                    self.frame_getter.add_annotation(self.time_bar.current_frame_i, res)
                    if not self.time_bar.hover(event.pos):
                        self.popup_manager.add_popup(
                            "Ctrl + C to copy text",
                            (50, 70),
                            2,
                        )
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.time_bar.move_cursor(-1)
                if event.key == pygame.K_RIGHT:
                    self.time_bar.move_cursor(1)
                if event.key == pygame.K_ESCAPE:
                    self.region_selector.reset()
                    self.frame_getter.clear_annotations()
                if event.key == pygame.K_RETURN:
                    pass
                if event.key == pygame.K_u:
                    if self.search_bar.active:
                        continue
                    self.update()
                    self.popup_manager.add_popup(
                        "Updating ...",
                        (50, 70),
                        2,
                    )
                if event.key == pygame.K_d:
                    if self.search_bar.active:
                        continue
                    self.frame_getter.toggle_debug_mode()
                    self.popup_manager.add_popup(
                        "DEBUG MODE ON"
                        if self.frame_getter.debug_mode
                        else "DEBUG MODE OFF",
                        (50, 70),
                        2,
                    )
                if event.mod & pygame.KMOD_CTRL:
                    self.ctrl_pressed = True
                    if event.key == pygame.K_c:
                        text = self.frame_getter.get_annotations_text()
                        pyperclip.copy(text)
                        self.popup_manager.add_popup(
                            "Text copied to clipboard",
                            (50, 70),
                            2,
                        )
            if event.type == pygame.KEYUP:
                self.ctrl_pressed = False

        if self.ctrl_pressed:
            if mouse_wheel != 0:
                self.time_bar.zoom(mouse_wheel)
                self.popup_manager.add_popup(
                    "Zoom : " + str(self.time_bar.tws) + "s",
                    (50, 70),
                    2,
                )

        if found:
            self.time_bar.set_current_frame_i(
                self.frame_getter.get_next_annotated_frame_i()
            )

    def run(self):
        while True:
            self.screen.fill((255, 255, 255))
            self.draw_current_frame()
            self.time_bar.draw(self.screen, pygame.mouse.get_pos())
            self.search_bar.draw(self.screen)
            self.handle_inputs()
            self.popup_manager.tick(self.screen)

            if self.search_bar.active:
                self.region_selector.reset()

            self.region_selector.draw(self.screen, pygame.mouse.get_pos())
            pygame.display.update()
            self.dt = self.clock.tick() / 1000.0
            self.t += self.dt
