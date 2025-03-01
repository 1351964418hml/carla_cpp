#!/usr/bin/env python
#
# Copyright (c) 2020 Intel Corporation
#

import glob
import os
import sys

# 尝试将Carla相关的模块路径添加到系统路径中，以便能够正确导入Carla相关的库。
# 这里根据不同的操作系统（Windows或Linux）以及Python版本信息来构建正确的模块路径格式。
try:
    sys.path.append(glob.glob(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + '/carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

from enum import Enum
import math
import numpy as np
import pygame
import weakref
import carla
from carla import ad


# RssStateVisualizer类用于可视化RSS状态信息，接收显示尺寸、字体、Carla世界对象等参数进行初始化，并提供更新可视化内容的方法
class RssStateVisualizer(object):

    def __init__(self, display_dimensions, font, world):
        # 初始化用于绘制的Surface对象为None，后续会根据实际情况创建和更新
        self._surface = None
        # 保存传入的显示尺寸信息（如屏幕宽高），用于确定绘制区域大小等
        self._display_dimensions = display_dimensions
        # 保存传入的字体对象，用于后续渲染文字
        self._font = font
        # 保存传入的Carla世界对象，方便获取场景中的相关Actor等信息
        self._world = world

    def tick(self, individual_rss_states):
        # 创建一个用于绘制RSS状态信息的Surface，设置背景色为透明（以黑色为透明色）
        state_surface = pygame.Surface((220, self._display_dimensions[1]))
        state_surface.set_colorkey(pygame.Color('black'))
        v_offset = 0

        # 如果存在RSS状态信息则进行绘制相关操作
        if individual_rss_states:
            # 使用传入的字体渲染"RSS States:"文字，颜色为白色，准备绘制到Surface上
            surface = self._font.render('RSS States:', True, (255, 255, 255))
            state_surface.blit(surface, (8, v_offset))
            v_offset += 26
        # 遍历每个RSS状态信息进行详细绘制
        for state in individual_rss_states:
            object_name = "Obj"
            # 根据对象ID判断是否是特定边界对象，并设置相应名称
            if state.rss_state.objectId == 18446744073709551614:
                object_name = "Border Left"
            elif state.rss_state.objectId == 18446744073709551615:
                object_name = "Border Right"
            else:
                # 获取对应Actor对象（如果存在），并尝试从其类型ID提取出合适的名称用于展示
                other_actor = state.get_actor(self._world)
                if other_actor:
                    li = list(other_actor.type_id.split("."))
                    if li:
                        li.pop(0)
                    li = [element.capitalize() for element in li]

                    object_name = " ".join(li).strip()[:15]

            mode = "?"
            # 根据计算模式设置对应的显示字符
            if state.actor_calculation_mode == ad.rss.map.RssMode.Structured:
                mode = "S"
            elif state.actor_calculation_mode == ad.rss.map.RssMode.Unstructured:
                mode = "U"
            elif state.actor_calculation_mode == ad.rss.map.RssMode.NotRelevant:
                mode = "-"
            # 格式化要显示的信息字符串，包含计算模式、距离、对象名称
            item = '%4s % 2dm %8s' % (mode, state.distance, object_name)

            # 使用字体渲染要显示的信息字符串，颜色为白色，准备绘制到Surface上
            surface = self._font.render(item, True, (255, 255, 255))
            state_surface.blit(surface, (5, v_offset))
            color = (128, 128, 128)
            # 根据计算模式和是否危险来设置显示颜色（危险为红色，非危险且相关为绿色，不相关为灰色）
            if state.actor_calculation_mode != ad.rss.map.RssMode.NotRelevant:
                if state.is_dangerous:
                    color = (255, 0, 0)
                else:
                    color = (0, 255, 0)
            # 在Surface上绘制一个表示状态的圆形，位置和颜色根据上述条件确定，半径为5
            pygame.draw.circle(state_surface, color, (12, v_offset + 7), 5)
            xpos = 184
            # 如果是结构化计算模式，根据不同的纵向、横向安全状态等条件绘制相应多边形图形来进一步展示状态细节
            if state.actor_calculation_mode == ad.rss.map.RssMode.Structured:
                if not state.rss_state.longitudinalState.isSafe and ((state.rss_state.longitudinalState.rssStateInformation.evaluator == "LongitudinalDistanceSameDirectionOtherInFront") or (state.rss_state.longitudinalState.rssStateInformation.evaluator == "LongitudinalDistanceSameDirectionEgoFront")):
                    pygame.draw.polygon(
                        state_surface, (
                            255, 255, 255), ((xpos + 1, v_offset + 1 + 4), (xpos + 6, v_offset + 1 + 0), (xpos + 11, v_offset + 1 + 4),
                                             (xpos + 7, v_offset + 1 + 4), (xpos + 7, v_offset + 1 + 12), (xpos + 5, v_offset + 1 + 12), (xpos + 5, v_offset + 1 + 4)))
                    xpos += 14

                # 如果纵向状态不安全（即 isSafe 为 False），并且纵向状态信息的评估器是 "LongitudinalDistanceOppositeDirectionEgoCorrectLane"
                # 或者 "LongitudinalDistanceOppositeDirection"，则执行以下绘制多边形操作
                if not state.rss_state.longitudinalState.isSafe and ((state.rss_state.longitudinalState.rssStateInformation.evaluator == "LongitudinalDistanceOppositeDirectionEgoCorrectLane") or (state.rss_state.longitudinalState.rssStateInformation.evaluator == "LongitudinalDistanceOppositeDirection")):
                   # 在 state_surface 表面上使用白色（RGB 值为 (255, 255, 255)）绘制一个多边形
                   # 多边形的顶点坐标通过一系列 (x, y) 坐标对表示，这里的坐标值是基于给定的 xpos 和 v_offset 变量以及一些固定偏移量计算得出的
                    pygame.draw.polygon(
                        state_surface, (
                            255, 255, 255), ((xpos + 2, v_offset + 1 + 8), (xpos + 6, v_offset + 1 + 12), (xpos + 10, v_offset + 1 + 8),
                                             (xpos + 7, v_offset + 1 + 8), (xpos + 7, v_offset + 1 + 0), (xpos + 5, v_offset + 1 + 0), (xpos + 5, v_offset + 1 + 8)))
                   # 在水平方向上增加偏移量，为下一次可能的绘制操作预留位置，偏移量值为 14
                    xpos += 14

                # 如果右侧横向状态不安全（isSafe 为 False），并且右侧横向状态信息的评估器不是 "None"，则执行以下绘制多边形操作
                if not state.rss_state.lateralStateRight.isSafe and not (state.rss_state.lateralStateRight.rssStateInformation.evaluator == "None"):
                    pygame.draw.polygon(
                        state_surface, (
                            255, 255, 255), ((xpos + 0, v_offset + 1 + 4), (xpos + 8, v_offset + 1 + 4), (xpos + 8, v_offset + 1 + 1),
                                             (xpos + 12, v_offset + 1 + 6), (xpos + 8, v_offset + 1 + 10), (xpos + 8, v_offset + 1 + 8), (xpos + 0, v_offset + 1 + 8)))
                    xpos += 14
                # 如果左侧横向状态不安全（isSafe 为 False），并且左侧横向状态信息的评估器不是 "None"，则执行以下绘制多边形操作
                if not state.rss_state.lateralStateLeft.isSafe and not (state.rss_state.lateralStateLeft.rssStateInformation.evaluator == "None"):
                    pygame.draw.polygon(
                        state_surface, (
                            255, 255, 255), ((xpos + 0, v_offset + 1 + 6), (xpos + 4, v_offset + 1 + 1), (xpos + 4, v_offset + 1 + 4),
                                             (xpos + 12, v_offset + 1 + 4), (xpos + 12, v_offset + 1 + 8), (xpos + 4, v_offset + 1 + 8), (xpos + 4, v_offset + 1 + 10)))
                    xpos += 14
            # 如果 actor_calculation_mode 处于非结构化模式（Unstructured），则执行以下逻辑
            elif state.actor_calculation_mode == ad.rss.map.RssMode.Unstructured:
                text = ""
                # 根据非结构化场景状态的响应类型设置要显示的文本内容
                if state.rss_state.unstructuredSceneState.response == ad.rss.state.UnstructuredSceneResponse.DriveAway:
                    text = "  D"
                elif state.rss_state.unstructuredSceneState.response == ad.rss.state.UnstructuredSceneResponse.ContinueForward:
                    text = "  C"
                elif state.rss_state.unstructuredSceneState.response == ad.rss.state.UnstructuredSceneResponse.Brake:
                    text = "  B"
                # 使用指定字体（self._font）渲染文本内容，设置文本颜色为白色（RGB 值为 (255, 255, 255)）
                surface = self._font.render(text, True, (255, 255, 255))
                # 将渲染好的文本表面绘制到 state_surface 的指定位置（xpos, v_offset）上
                state_surface.blit(surface, (xpos, v_offset))

            # 在垂直方向上增加偏移量，为下一轮绘制相关内容预留空间，偏移量值为 14
            v_offset += 14
            # 将更新后的 state_surface 赋值给实例的 _surface 属性，以便后续使用
            self._surface = state_surface

    def render(self, display, v_offset):
        if self._surface:
            # 用于将自身维护的表面（_surface）绘制到给定的显示表面（display）上的方法，绘制位置基于传入的垂直偏移量（v_offset）
            display.blit(self._surface, (0, v_offset))


def get_matrix(transform):
    """
    Creates matrix from carla transform.
    """

    rotation = transform.rotation
    location = transform.location
    # 计算偏航角（yaw）的余弦值
    c_y = np.cos(np.radians(rotation.yaw))
    # 计算偏航角（yaw）的正弦值
    s_y = np.sin(np.radians(rotation.yaw))
    # 计算翻滚角（roll）的余弦值
    c_r = np.cos(np.radians(rotation.roll))
    # 计算翻滚角（roll）的正弦值
    s_r = np.sin(np.radians(rotation.roll))
    # 计算俯仰角（pitch）的余弦值
    c_p = np.cos(np.radians(rotation.pitch))
    # 计算俯仰角（pitch）的正弦值
    s_p = np.sin(np.radians(rotation.pitch))
    matrix = np.matrix(np.identity(4))
    # 设置变换矩阵中的位置信息，将位置的 x 坐标赋值给矩阵的对应元素
    matrix[0, 3] = location.x
    # 设置变换矩阵中的位置信息，将位置的 y 坐标赋值给矩阵的对应元素
    matrix[1, 3] = location.y
    # 设置变换矩阵中的位置信息，将位置的 z 坐标赋值给矩阵的对应元素
    matrix[2, 3] = location.z
    # 根据旋转角度的三角函数值设置变换矩阵中表示旋转的部分元素，用于在 x 轴方向上的旋转相关计算
    matrix[0, 0] = c_p * c_y
    matrix[0, 1] = c_y * s_p * s_r - s_y * c_r
    matrix[0, 2] = -c_y * s_p * c_r - s_y * s_r
    # 根据旋转角度的三角函数值设置变换矩阵中表示旋转的部分元素，用于在 y 轴方向上的旋转相关计算
    matrix[1, 0] = s_y * c_p
    matrix[1, 1] = s_y * s_p * s_r + c_y * c_r
    matrix[1, 2] = -s_y * s_p * c_r + c_y * s_r
    # 根据旋转角度的三角函数值设置变换矩阵中表示旋转的部分元素，用于在 z 轴方向上的旋转相关计算
    matrix[2, 0] = s_p
    matrix[2, 1] = -c_p * s_r
    matrix[2, 2] = c_p * c_r
    return matrix

# ==============================================================================
# -- RssUnstructuredSceneVisualizer ------------------------------------------------
# ==============================================================================


# 定义一个枚举类，用于表示 RSS 非结构化场景可视化器的不同模式
class RssUnstructuredSceneVisualizerMode(Enum):
    disabled = 1
    window = 2
    fullscreen = 3


# RSS 非结构化场景可视化器类，用于处理相关场景的可视化展示等功能
class RssUnstructuredSceneVisualizer(object):

    def __init__(self, parent_actor, world, display_dimensions):
        # 记录上一次渲染的帧编号，初始值为 -1，表示尚未进行过渲染
        self._last_rendered_frame = -1
        # 用于存储整体的可视化表面对象，初始为 None
        self._surface = None
        # 用于存储当前 RSS 相关的可视化表面对象及对应的帧编号，初始为 None
        self._current_rss_surface = None
        # 存储当前相机获取的表面对象及对应的帧编号，初始值为 (0, None)，表示帧编号为 0，表面对象为 None
        self.current_camera_surface = (0, None)
        # 保存传入的 Carla 世界对象，用于后续与世界中的元素（如相机、演员等）进行交互
        self._world = world
        # 保存传入的父级演员对象，可能用于关联可视化器与特定的场景元素等，具体取决于使用场景
        self._parent_actor = parent_actor
        # 存储显示尺寸信息（可能是宽度和高度），用于后续设置相机、表面尺寸等相关操作
        self._display_dimensions = display_dimensions
        # 相机对象，用于获取场景图像等信息，初始为 None
        self._camera = None
         # 可视化器的当前模式，初始设置为 disabled（禁用状态）
        self._mode = RssUnstructuredSceneVisualizerMode.disabled

         # 调用 restart 方法，根据默认或传入的模式进行初始化相关设置
        self.restart(RssUnstructuredSceneVisualizerMode.window)

    # 用于销毁相机对象及相关资源的方法
    def destroy(self):
        # 停止相机的数据获取（如果正在运行）
        if self._camera:
            # 销毁相机对象，释放相关资源
            self._camera.stop()
             # 将相机对象设置为 None，表示已销毁
            self._camera.destroy()
            self._camera = None

    # 根据指定的模式重新启动可视化器，进行相应的初始化和资源设置
    def restart(self, mode):
        # 先调用 destroy 方法，清理之前可能存在的相机等相关资源
       
        self.destroy()
        self._mode = mode

        spawn_sensor = False
        # 如果模式设置为窗口模式（window）
        if mode == RssUnstructuredSceneVisualizerMode.window:
            # 设置可视化表面的尺寸，这里将传入的显示尺寸分别除以 3 和 2，得到相对较小的尺寸（可能用于在窗口中合适显示）
            self._dim = (self._display_dimensions[0] / 3, self._display_dimensions[1] / 2)
            # 设置需要生成相机传感器（即开启相机数据获取相关操作）
            spawn_sensor = True
        elif mode == RssUnstructuredSceneVisualizerMode.fullscreen:
            self._dim = (self._display_dimensions[0], self._display_dimensions[1])
            spawn_sensor = True
        # 如果模式是禁用状态（disabled），则直接将可视化表面设置为 None，不进行相机相关操作
        else:
            self._surface = None

         # 如果需要生成相机传感器（即处于窗口或全屏模式）
        if spawn_sensor:
            # 创建一个 3x3 的单位矩阵，用于相机的校准，后续会修改其中元素来完成实际校准设置
            self._calibration = np.identity(3)
            # 设置校准矩阵中对应图像宽度方向上的中心坐标，使得后续计算的坐标能正确对应图像中的位置（将图像宽度的一半赋值给对应元素）
            self._calibration[0, 2] = self._dim[0] / 2.0
            # 设置校准矩阵中对应图像高度方向上的中心坐标，使得后续计算的坐标能正确对应图像中的位置（将图像高度的一半赋值给对应元素
            self._calibration[1, 2] = self._dim[1] / 2.0
            # 根据默认的视野角度（90 度）计算图像宽度和高度方向上的缩放因子，以确保相机获取的图像在显示等操作中的坐标正确对应实际像素位置
            self._calibration[0, 0] = self._calibration[1, 1] = self._dim[0] / \
            (2.0 * np.tan(90.0 * np.pi / 360.0))  # fov default: 90.0

            # 从世界的蓝图库中获取蓝图对象
            bp_library = self._world.get_blueprint_library()
            # 查找名为'sensor.camera.rgb'的相机蓝图，用于创建相机实例
            bp = bp_library.find('sensor.camera.rgb')
            # 设置相机图像的宽度属性，使用之前计算得到的 _dim[0] 值（即根据模式确定的宽度尺寸）
            bp.set_attribute('image_size_x', str(self._dim[0]))
             # 设置相机图像的高度属性，使用之前计算得到的 _dim[1] 值（即根据模式确定的高度尺寸）
            bp.set_attribute('image_size_y', str(self._dim[1]))

            # 在世界中生成相机演员实例，设置其位置（x 坐标为 7.5，z 坐标为 10）和姿态（俯仰角为 -90 度），并将其绑定到传入的父级演员（self._parent_actor）上
            self._camera = self._world.spawn_actor(
            self._camera = self._world.spawn_actor(
                bp,
                carla.Transform(carla.Location(x=7.5, z=10), carla.Rotation(pitch=-90)),
                attach_to=self._parent_actor)
            # 我们需要对lamda进行传递以避免循环
            # 创建一个对当前实例（self）的弱引用，避免循环引用导致内存泄漏等问题，便于在相机的回调函数中访问当前实例的属性和方法
            weak_self = weakref.ref(self)
            weak_self = weakref.ref(self)
             # 为相机注册一个监听函数（回调函数），当相机获取到新的图像数据时会触发该函数，将图像数据传递给 _parse_image 方法进行处理
            self._camera.listen(lambda image: self._parse_image(weak_self, image))

    # 根据相机帧和 RSS 帧的信息更新可视化表面，判断是否需要进行渲染以及进行相关绘制操作
    def update_surface(self, cam_frame, rss_frame):
        if self._mode == RssUnstructuredSceneVisualizerMode.disabled:
            return
        render = False

        # 如果相机帧存在，并且当前 RSS 表面及其帧编号与相机帧匹配，则设置需要进行渲染
        if cam_frame and self._current_rss_surface and self._current_rss_surface[0] == cam_frame:
            render = True

        # 如果 RSS 帧存在，并且当前相机表面及其帧编号与 RSS 帧匹配，则设置需要进行渲染
        if rss_frame and self.current_camera_surface and self.current_camera_surface[0] == rss_frame:
            render = True

        if render:
            surface = self.current_camera_surface[1]
            surface.blit(self._current_rss_surface[1], (0, 0))
            rect = pygame.Rect((0, 0), (2, surface.get_height()))
            pygame.draw.rect(surface, (0, 0, 0), rect, 0)
            rect = pygame.Rect((0, 0), (surface.get_width(), 2))
            pygame.draw.rect(surface, (0, 0, 0), rect, 0)
            rect = pygame.Rect((0, surface.get_height() - 2), (surface.get_width(), surface.get_height()))
            pygame.draw.rect(surface, (0, 0, 0), rect, 0)
            rect = pygame.Rect((surface.get_width() - 2, 0), (surface.get_width(), surface.get_width()))
            pygame.draw.rect(surface, (0, 0, 0), rect, 0)
            self._surface = surface

    # 用于切换可视化器模式的方法，例如从窗口模式切换到全屏模式，或从全屏模式切换到禁用模式等
    def toggle_camera(self):
        print("Toggle RssUnstructuredSceneVisualizer")
        if self._mode == RssUnstructuredSceneVisualizerMode.window:
            self.restart(RssUnstructuredSceneVisualizerMode.fullscreen)
        elif self._mode == RssUnstructuredSceneVisualizerMode.fullscreen:
            self.restart(RssUnstructuredSceneVisualizerMode.disabled)
        elif self._mode == RssUnstructuredSceneVisualizerMode.disabled:
            self.restart(RssUnstructuredSceneVisualizerMode.window)

    @staticmethod
    def _parse_image(weak_self, image):
        self = weak_self()
        if not self:
            return
        image.convert(carla.ColorConverter.Raw)
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))
        self.current_camera_surface = (image.frame, surface)
        self.update_surface(image.frame, None)

    @staticmethod
    def rotate_around_point(xy, radians, origin):
        """Rotate a point around a given point.
        """
        x, y = xy
        offset_x, offset_y = origin
        adjusted_x = (x - offset_x)
        adjusted_y = (y - offset_y)
        cos_rad = math.cos(radians)
        sin_rad = math.sin(radians)
        qx = offset_x + cos_rad * adjusted_x - sin_rad * adjusted_y
        qy = offset_y + sin_rad * adjusted_x + cos_rad * adjusted_y

        return qx, qy

    def tick(self, frame, rss_response, allowed_heading_ranges):
        if not self._camera:
            return
        surface = pygame.Surface(self._dim)
        surface.set_colorkey(pygame.Color('black'))
        surface.set_alpha(180)
        try:
            lines = RssUnstructuredSceneVisualizer.get_trajectory_sets(
                rss_response.rss_state_snapshot, self._camera.get_transform(), self._calibration)

            polygons = []
            for heading_range in allowed_heading_ranges:
                polygons.append((RssUnstructuredSceneVisualizer.transform_points(
                    RssUnstructuredSceneVisualizer._get_points_from_pairs(
                        RssUnstructuredSceneVisualizer.draw_heading_range(
                            heading_range, rss_response.ego_dynamics_on_route)),
                    self._camera.get_transform(), self._calibration), (0, 0, 255)))

            RssUnstructuredSceneVisualizer.draw_lines(surface, lines)
            RssUnstructuredSceneVisualizer.draw_polygons(surface, polygons)

        except RuntimeError as e:
            print("ERROR {}".format(e))
        self._current_rss_surface = (frame, surface)
        self.update_surface(None, frame)

    def render(self, display):
        if self._surface:
            display.blit(self._surface, (display.get_width() - self._dim[0], 0))

    @staticmethod
    def draw_heading_range(heading_range, ego_dynamics_on_route):
        line = [(float(ego_dynamics_on_route.ego_center.x), float(ego_dynamics_on_route.ego_center.y))]
        length = 3.0
        current_angle = float(heading_range.begin)
        max_angle = float(heading_range.end)
        if heading_range.end < heading_range.begin:
            max_angle += 2.0 * np.pi

        while current_angle < max_angle:
            line.append((float(ego_dynamics_on_route.ego_center.x) + length * np.cos(current_angle),
                         float(ego_dynamics_on_route.ego_center.y) + length * np.sin(current_angle)))
            current_angle += 0.2

        if current_angle != max_angle:
            line.append((float(ego_dynamics_on_route.ego_center.x) + length * np.cos(max_angle),
                         float(ego_dynamics_on_route.ego_center.y) + length * np.sin(max_angle)))

        line.append((float(ego_dynamics_on_route.ego_center.x), float(ego_dynamics_on_route.ego_center.y)))
        return line

    @staticmethod
    def get_trajectory_sets(rss_state_snapshot, camera_transform, calibration):
        """
        Creates 3D bounding boxes based on carla vehicle list and camera.
        """
        trajectory_sets = []

        # ego
        trajectory_sets.append((RssUnstructuredSceneVisualizer.transform_points(RssUnstructuredSceneVisualizer._get_trajectory_set_points(
            rss_state_snapshot.unstructuredSceneEgoInformation.brakeTrajectorySet), camera_transform, calibration), (255, 0, 0)))
        trajectory_sets.append((RssUnstructuredSceneVisualizer.transform_points(RssUnstructuredSceneVisualizer._get_trajectory_set_points(
            rss_state_snapshot.unstructuredSceneEgoInformation.continueForwardTrajectorySet), camera_transform, calibration), (0, 255, 0)))

        # others
        for state in rss_state_snapshot.individualResponses:
            if state.unstructuredSceneState.rssStateInformation.brakeTrajectorySet:
                trajectory_sets.append((RssUnstructuredSceneVisualizer.transform_points(RssUnstructuredSceneVisualizer._get_trajectory_set_points(
                    state.unstructuredSceneState.rssStateInformation.brakeTrajectorySet), camera_transform, calibration), (255, 0, 0)))
            if state.unstructuredSceneState.rssStateInformation.continueForwardTrajectorySet:
                trajectory_sets.append((RssUnstructuredSceneVisualizer.transform_points(RssUnstructuredSceneVisualizer._get_trajectory_set_points(
                    state.unstructuredSceneState.rssStateInformation.continueForwardTrajectorySet), camera_transform, calibration), (0, 255, 0)))

        return trajectory_sets

    @staticmethod
    def draw_lines(surface, lines):
        """
        Draws lines on pygame display.
        """
        for line, color in lines:
            if len(line) > 1:
                pygame.draw.lines(surface, color, True, line, 2)

    @staticmethod
    def draw_polygons(surface, polygons):
        """
        Draws polygons on pygame display.
        """
        for polygon, color in polygons:
            if len(polygon) > 1:
                pygame.draw.polygon(surface, color, polygon)

    @staticmethod
    def transform_points(world_cords, camera_transform, calibration):
        """
        Returns trajectory set projected to camera view
        """
        world_cords = np.transpose(world_cords)
        cords_x_y_z = RssUnstructuredSceneVisualizer._world_to_sensor(world_cords, camera_transform)[:3, :]
        cords_y_minus_z_x = np.concatenate([cords_x_y_z[1, :], -cords_x_y_z[2, :], cords_x_y_z[0, :]])
        ts = np.transpose(np.dot(calibration, cords_y_minus_z_x))
        camera_ts = np.concatenate([ts[:, 0] / ts[:, 2], ts[:, 1] / ts[:, 2], ts[:, 2]], axis=1)
        line_to_draw = []
        for point in camera_ts:
            line_to_draw.append((int(point[0, 0]), int(point[0, 1])))
        return line_to_draw

    @staticmethod
    def _get_trajectory_set_points(trajectory_set):
        """
        """
        cords = np.zeros((len(trajectory_set), 4))
        i = 0
        for pt in trajectory_set:
            cords[i, :] = np.array([pt.x, -pt.y, 0, 1])
            i += 1
        return cords

    @staticmethod
    def _get_points_from_pairs(trajectory_set):
        """
        """
        cords = np.zeros((len(trajectory_set), 4))
        i = 0
        for pt in trajectory_set:
            cords[i, :] = np.array([pt[0], -pt[1], 0, 1])
            i += 1
        return cords

    @staticmethod
    def _world_to_sensor(cords, camera_transform):
        """
        Transforms world coordinates to sensor.
        """
        sensor_world_matrix = get_matrix(camera_transform)
        world_sensor_matrix = np.linalg.inv(sensor_world_matrix)
        sensor_cords = np.dot(world_sensor_matrix, cords)
        return sensor_cords

# ==============================================================================
# -- RssBoundingBoxVisualizer ------------------------------------------------------
# ==============================================================================


class RssBoundingBoxVisualizer(object):

    def __init__(self, display_dimensions, world, camera):
        self._last_camera_frame = 0
        self._surface_for_frame = []
        self._world = world
        self._dim = display_dimensions
        self._calibration = np.identity(3)
        self._calibration[0, 2] = self._dim[0] / 2.0
        self._calibration[1, 2] = self._dim[1] / 2.0
        self._calibration[0, 0] = self._calibration[1, 1] = self._dim[0] / \
            (2.0 * np.tan(90.0 * np.pi / 360.0))  # fov default: 90.0
        self._camera = camera

    def tick(self, frame, individual_rss_states):
        if len(self._surface_for_frame) > 0:
            try:
                while self._surface_for_frame[0][0] < self._last_camera_frame:
                    self._surface_for_frame.pop(0)
            except IndexError:
                return

        # only render on new frame
        if len(self._surface_for_frame) > 0:
            if self._surface_for_frame[0][0] == frame:
                return

        surface = pygame.Surface(self._dim)
        surface.set_colorkey(pygame.Color('black'))
        surface.set_alpha(80)
        try:
            bounding_boxes = RssBoundingBoxVisualizer.get_bounding_boxes(
                individual_rss_states, self._camera.get_transform(), self._calibration, self._world)
            RssBoundingBoxVisualizer.draw_bounding_boxes(surface, bounding_boxes)
            self._surface_for_frame.append((frame, surface, len(bounding_boxes)))
        except RuntimeError:
            pass

    def render(self, display, current_camera_frame):
        rendered = False
        boxes_to_render = 0
        for frame, surface, box_count in self._surface_for_frame:
            if frame == current_camera_frame:
                display.blit(surface, (0, 0))
                boxes_to_render = box_count
                rendered = True
                break
        if not rendered and boxes_to_render > 0:
            print("Warning: {} bounding boxes were not drawn.".format(boxes_to_render))
        self._last_camera_frame = current_camera_frame

    @staticmethod
    def get_bounding_boxes(individual_rss_states, camera_transform, calibration, world):
        """
        Creates 3D bounding boxes based on carla vehicle list and camera.
        """
        bounding_boxes = []
        for state in individual_rss_states:
            if state.actor_calculation_mode != ad.rss.map.RssMode.NotRelevant and state.is_dangerous:
                other_actor = state.get_actor(world)
                if other_actor:
                    bounding_boxes.append(RssBoundingBoxVisualizer.get_bounding_box(
                        other_actor, camera_transform, calibration))
        # filter objects behind camera
        bounding_boxes = [bb for bb in bounding_boxes if all(bb[:, 2] > 0)]
        return bounding_boxes

    @staticmethod
    def draw_bounding_boxes(surface, bounding_boxes, color=pygame.Color('red')):
        """
        Draws bounding boxes on pygame display.
        """
        for bbox in bounding_boxes:
            points = [(int(bbox[i, 0]), int(bbox[i, 1])) for i in range(8)]
            # draw lines
            # base
            polygon = [points[0], points[1], points[2], points[3]]
            pygame.draw.polygon(surface, color, polygon)
            # top
            polygon = [points[4], points[5], points[6], points[7]]
            pygame.draw.polygon(surface, color, polygon)
            # base-top
            polygon = [points[0], points[1], points[5], points[4]]
            pygame.draw.polygon(surface, color, polygon)
            polygon = [points[1], points[2], points[6], points[5]]
            pygame.draw.polygon(surface, color, polygon)
            polygon = [points[2], points[6], points[7], points[3]]
            pygame.draw.polygon(surface, color, polygon)
            polygon = [points[0], points[4], points[7], points[3]]
            pygame.draw.polygon(surface, color, polygon)

    @staticmethod
    def get_bounding_box(vehicle, camera_transform, calibration):
        """
        Returns 3D bounding box for a vehicle based on camera view.
        """

        bb_cords = RssBoundingBoxVisualizer._create_bb_points(vehicle)
        cords_x_y_z = RssBoundingBoxVisualizer._vehicle_to_sensor(bb_cords, vehicle, camera_transform)[:3, :]
        cords_y_minus_z_x = np.concatenate([cords_x_y_z[1, :], -cords_x_y_z[2, :], cords_x_y_z[0, :]])
        bbox = np.transpose(np.dot(calibration, cords_y_minus_z_x))
        camera_bbox = np.concatenate([bbox[:, 0] / bbox[:, 2], bbox[:, 1] / bbox[:, 2], bbox[:, 2]], axis=1)
        return camera_bbox

    @staticmethod
    def _create_bb_points(vehicle):
        """
        Returns 3D bounding box for a vehicle.
        """

        cords = np.zeros((8, 4))
        extent = vehicle.bounding_box.extent
        cords[0, :] = np.array([extent.x, extent.y, -extent.z, 1])
        cords[1, :] = np.array([-extent.x, extent.y, -extent.z, 1])
        cords[2, :] = np.array([-extent.x, -extent.y, -extent.z, 1])
        cords[3, :] = np.array([extent.x, -extent.y, -extent.z, 1])
        cords[4, :] = np.array([extent.x, extent.y, extent.z, 1])
        cords[5, :] = np.array([-extent.x, extent.y, extent.z, 1])
        cords[6, :] = np.array([-extent.x, -extent.y, extent.z, 1])
        cords[7, :] = np.array([extent.x, -extent.y, extent.z, 1])
        return cords

    @staticmethod
    def _vehicle_to_sensor(cords, vehicle, camera_transform):
        """
        Transforms coordinates of a vehicle bounding box to sensor.
        """

        world_cord = RssBoundingBoxVisualizer._vehicle_to_world(cords, vehicle)
        sensor_cord = RssBoundingBoxVisualizer._world_to_sensor(world_cord, camera_transform)
        return sensor_cord

    @staticmethod
    def _vehicle_to_world(cords, vehicle):
        """
        Transforms coordinates of a vehicle bounding box to world.
        """

        bb_transform = carla.Transform(vehicle.bounding_box.location)
        bb_vehicle_matrix = get_matrix(bb_transform)
        vehicle_world_matrix = get_matrix(vehicle.get_transform())
        bb_world_matrix = np.dot(vehicle_world_matrix, bb_vehicle_matrix)
        world_cords = np.dot(bb_world_matrix, np.transpose(cords))
        return world_cords

    @staticmethod
    def _world_to_sensor(cords, camera_transform):
        """
        Transforms world coordinates to sensor.
        """

        sensor_world_matrix = get_matrix(camera_transform)
        world_sensor_matrix = np.linalg.inv(sensor_world_matrix)
        sensor_cords = np.dot(world_sensor_matrix, cords)
        return sensor_cords

# ==============================================================================
# -- RssDebugVisualizer ------------------------------------------------------------
# ==============================================================================


class RssDebugVisualizationMode(Enum):
    Off = 1
    RouteOnly = 2
    VehicleStateOnly = 3
    VehicleStateAndRoute = 4
    All = 5


class RssDebugVisualizer(object):

    def __init__(self, player, world):
        self._world = world
        self._player = player
        self._visualization_mode = RssDebugVisualizationMode.Off

    def toggleMode(self):
        if self._visualization_mode == RssDebugVisualizationMode.All:
            self._visualization_mode = RssDebugVisualizationMode.Off
        elif self._visualization_mode == RssDebugVisualizationMode.Off:
            self._visualization_mode = RssDebugVisualizationMode.RouteOnly
        elif self._visualization_mode == RssDebugVisualizationMode.RouteOnly:
            self._visualization_mode = RssDebugVisualizationMode.VehicleStateOnly
        elif self._visualization_mode == RssDebugVisualizationMode.VehicleStateOnly:
            self._visualization_mode = RssDebugVisualizationMode.VehicleStateAndRoute
        elif self._visualization_mode == RssDebugVisualizationMode.VehicleStateAndRoute:
            self._visualization_mode = RssDebugVisualizationMode.All
        print("New Debug Visualizer Mode {}".format(self._visualization_mode))

    def tick(self, route, dangerous, individual_rss_states, ego_dynamics_on_route):
        if self._visualization_mode == RssDebugVisualizationMode.RouteOnly or \
                self._visualization_mode == RssDebugVisualizationMode.VehicleStateAndRoute or \
                self._visualization_mode == RssDebugVisualizationMode.All:
            self.visualize_route(dangerous, route)

        if self._visualization_mode == RssDebugVisualizationMode.VehicleStateOnly or \
                self._visualization_mode == RssDebugVisualizationMode.VehicleStateAndRoute or \
                self._visualization_mode == RssDebugVisualizationMode.All:
            self.visualize_rss_results(individual_rss_states)

        if self._visualization_mode == RssDebugVisualizationMode.All:
            self.visualize_ego_dynamics(ego_dynamics_on_route)

    def visualize_route(self, dangerous, route):
        if not route:
            return
        right_lane_edges = dict()
        left_lane_edges = dict()

        for road_segment in route.roadSegments:
            right_most_lane = road_segment.drivableLaneSegments[0]
            if right_most_lane.laneInterval.laneId not in right_lane_edges:
                edge = ad.map.route.getRightProjectedENUEdge(right_most_lane.laneInterval)
                right_lane_edges[right_most_lane.laneInterval.laneId] = edge
                intersection_lane = ad.map.intersection.Intersection.isLanePartOfAnIntersection(right_most_lane.laneInterval.laneId)

                color = carla.Color(r=(128 if dangerous else 255))
                if intersection_lane:
                    color.b = 128 if dangerous else 255
                color = carla.Color(r=255, g=0, b=255)
                self.visualize_enu_edge(edge, color, self._player.get_location().z)

            left_most_lane = road_segment.drivableLaneSegments[-1]
            if left_most_lane.laneInterval.laneId not in left_lane_edges:
                edge = ad.map.route.getLeftProjectedENUEdge(left_most_lane.laneInterval)
                left_lane_edges[left_most_lane.laneInterval.laneId] = edge
                intersection_lane = ad.map.intersection.Intersection.isLanePartOfAnIntersection(left_most_lane.laneInterval.laneId)
                color = carla.Color(g=(128 if dangerous else 255))
                if intersection_lane:
                    color.b = 128 if dangerous else 255

                self.visualize_enu_edge(edge, color, self._player.get_location().z)

    def visualize_enu_edge(self, edge, color, z_offset):
        for point in edge:
            carla_point = carla.Location(x=float(point.x), y=-1. * float(point.y), z=float(point.z) + z_offset)
            self._world.debug.draw_point(carla_point, 0.1, color, 0.1, False)

    def visualize_rss_results(self, state_snapshot):
        for state in state_snapshot:
            other_actor = state.get_actor(self._world)
            if not other_actor:
                # print("Actor not found. Skip visualizing state {}".format(state))
                continue
            ego_point = self._player.get_location()
            ego_point.z += 0.05
            yaw = self._player.get_transform().rotation.yaw
            cosine = math.cos(math.radians(yaw))
            sine = math.sin(math.radians(yaw))
            line_offset = carla.Location(-sine * 0.1, cosine * 0.1, 0.0)

            point = other_actor.get_location()
            point.z += 0.05
            indicator_color = carla.Color(0, 255, 0)
            dangerous = ad.rss.state.isDangerous(state.rss_state)
            if dangerous:
                indicator_color = carla.Color(255, 0, 0)
            elif state.rss_state.situationType == ad.rss.situation.SituationType.NotRelevant:
                indicator_color = carla.Color(150, 150, 150)

            if self._visualization_mode == RssDebugVisualizationMode.All:
                # the connection lines are only visualized if All is requested
                lon_color = indicator_color
                lat_l_color = indicator_color
                lat_r_color = indicator_color
                if not state.rss_state.longitudinalState.isSafe:
                    lon_color.r = 255
                    lon_color.g = 0 if dangerous else 255
                if not state.rss_state.lateralStateLeft.isSafe:
                    lat_l_color.r = 255
                    lat_l_color.g = 0 if dangerous else 255
                if not state.rss_state.lateralStateRight.isSafe:
                    lat_r_color.r = 255
                    lat_r_color.g = 0 if dangerous else 255
                self._world.debug.draw_line(ego_point, point, 0.1, lon_color, 0.02, False)
                self._world.debug.draw_line(ego_point - line_offset, point -
                                            line_offset, 0.1, lat_l_color, 0.02, False)
                self._world.debug.draw_line(ego_point + line_offset, point +
                                            line_offset, 0.1, lat_r_color, 0.02, False)
            point.z += 3.
            self._world.debug.draw_point(point, 0.2, indicator_color, 0.02, False)

    def visualize_ego_dynamics(self, ego_dynamics_on_route):
        color = carla.Color(0, 0, 255)

        sin_heading = math.sin(float(ego_dynamics_on_route.route_heading))
        cos_heading = math.cos(float(ego_dynamics_on_route.route_heading))

        heading_location_start = self._player.get_location()
        heading_location_start.x -= cos_heading * 10.
        heading_location_start.y += sin_heading * 10.
        heading_location_start.z += 0.5
        heading_location_end = self._player.get_location()
        heading_location_end.x += cos_heading * 10.
        heading_location_end.y -= sin_heading * 10.
        heading_location_end.z += 0.5

        self._world.debug.draw_arrow(heading_location_start, heading_location_end, 0.1, 0.1, color, 0.02, False)

        sin_center = math.sin(float(ego_dynamics_on_route.route_heading) + math.pi / 2.)
        cos_center = math.cos(float(ego_dynamics_on_route.route_heading) + math.pi / 2.)
        center_location_start = self._player.get_location()
        center_location_start.x -= cos_center * 2.
        center_location_start.y += sin_center * 2.
        center_location_start.z += 0.5
        center_location_end = self._player.get_location()
        center_location_end.x += cos_center * 2.
        center_location_end.y -= sin_center * 2.
        center_location_end.z += 0.5

        self._world.debug.draw_line(center_location_start, center_location_end, 0.1, color, 0.02, False)
