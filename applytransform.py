#!/usr/bin/env python3
#
# License: GPL2
# Copyright Mark "Klowner" Riedesel
# https://github.com/Klowner/inkscape-applytransforms
#
import sys
sys.path.append('/usr/share/inkscape/extensions')

import inkex
import math
from inkex.paths import CubicSuperPath, Path
from inkex.transforms import Transform
from inkex.styles import Style

NULL_TRANSFORM = Transform([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

class ApplyTransform(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self) 

    def effect(self):
        self.svg.get_selected()

        if self.svg.selected:
            for id, shape in self.svg.selected.items():
                self.recursiveFuseTransform(shape)
        else:
            self.recursiveFuseTransform(self.document.getroot())

    @staticmethod
    def objectToPath(node):
        if node.tag == inkex.addNS('g', 'svg'):
            return node

        if node.tag == inkex.addNS('path', 'svg') or node.tag == 'path':
            for attName in node.attrib.keys():
                if ("sodipodi" in attName) or ("inkscape" in attName):
                    del node.attrib[attName]
            return node

        return node

    def scalePxAttribute(self, node, transf, attr):
        if 'style' in node.attrib:
            style = node.attrib.get('style')
            style = dict(Style.parse_str(style))
            update = False

            if attr in style:
                try:
                    stroke_width = float(style.get(attr).strip().replace("px", ""))
                    stroke_width *= math.sqrt(abs(transf.a * transf.d))
                    style[attr] = str(max(stroke_width, 0.1)) + "px"
                    update = True
                except AttributeError:
                    pass

            if update:
                node.attrib['style'] = Style(style).to_str()

    def recursiveFuseTransform(self, node, transf=NULL_TRANSFORM):

        transf = Transform(transf) * Transform(node.get("transform", None))

        if 'transform' in node.attrib:
            del node.attrib['transform']

        node = ApplyTransform.objectToPath(node)

        if transf == NULL_TRANSFORM:
            # Don't do anything if there is effectively no transform applied
            # reduces alerts for unsupported nodes
            pass
        elif 'd' in node.attrib:
            d = node.get('d')
            p = CubicSuperPath(d)
            p = Path(p).to_absolute().transform(transf, True)
            node.set('d', Path(CubicSuperPath(p).to_path()))

            self.scalePxAttribute(node, transf, 'stroke-width')

        elif node.tag in [inkex.addNS('polygon', 'svg'),
                          inkex.addNS('polyline', 'svg')]:
            points = node.get('points')
            points = points.strip().split(' ')
            for k, p in enumerate(points):
                if ',' in p:
                    p = p.split(',')
                    p = [float(p[0]), float(p[1])]
                    p = transf.apply_to_point(p)
                    p = [str(p[0]), str(p[1])]
                    p = ','.join(p)
                    points[k] = p
            points = ' '.join(points)
            node.set('points', points)

            self.scalePxAttribute(node, transf, 'stroke-width')

        elif node.tag in [inkex.addNS("ellipse", "svg"), inkex.addNS("circle", "svg")]:

            def isequal(a, b):
                return abs(a - b) <= transf.absolute_tolerance

            if node.TAG == "ellipse":
                rx = float(node.get("rx"))
                ry = float(node.get("ry"))
            else:
                rx = float(node.get("r"))
                ry = rx

            cx = float(node.get("cx"))
            cy = float(node.get("cy"))
            sqxy1 = (cx - rx, cy - ry)
            sqxy2 = (cx + rx, cy - ry)
            sqxy3 = (cx + rx, cy + ry)
            newxy1 = transf.apply_to_point(sqxy1)
            newxy2 = transf.apply_to_point(sqxy2)
            newxy3 = transf.apply_to_point(sqxy3)

            node.set("cx", (newxy1[0] + newxy3[0]) / 2)
            node.set("cy", (newxy1[1] + newxy3[1]) / 2)
            edgex = math.sqrt(
                abs(newxy1[0] - newxy2[0]) ** 2 + abs(newxy1[1] - newxy2[1]) ** 2
            )
            edgey = math.sqrt(
                abs(newxy2[0] - newxy3[0]) ** 2 + abs(newxy2[1] - newxy3[1]) ** 2
            )

            if not isequal(edgex, edgey) and (
                node.TAG == "circle"
                or not isequal(newxy2[0], newxy3[0])
                or not isequal(newxy1[1] != newxy2[1])
            ):
                inkex.utils.errormsg(
                    "Warning: Shape %s (%s) is approximate only, try Object to path first for better results"
                    % (node.TAG, node.get("id"))
                )

            if node.TAG == "ellipse":
                node.set("rx", edgex / 2)
                node.set("ry", edgey / 2)
            else:
                node.set("r", edgex / 2)

        elif node.tag in [inkex.addNS('text', 'svg'), inkex.addNS('tspan', 'svg')]:
            
            x = float(node.get("x"))
            y = float(node.get("y"))

            xy = (x, y)

            newxy = transf.apply_to_point(xy)

            node.set("x", newxy[0])
            node.set("y", newxy[1])

            self.scalePxAttribute(node, transf, 'stroke-width')

            # only scale font size by Y value of scale transform
            self.scalePxAttribute(node, [[1.0, 0.0, 0.0], [0.0, transf.d, 0.0]], 'font-size')

            inkex.utils.errormsg(
                    "Warning: Only scale and translate transforms will be applied to shape %s (%s)"
                    % (node.TAG, node.get("id"))
                )

        elif node.tag in [inkex.addNS('rect', 'svg'),
                          inkex.addNS('image', 'svg'),
                          inkex.addNS('use', 'svg')]:
            inkex.utils.errormsg(
                "Shape %s (%s) not yet supported, try Object to path first"
                % (node.TAG, node.get("id"))
            )

        else:
            # e.g. <g style="...">
            self.scalePxAttribute(node, transf, 'stroke-width')

        for child in node.getchildren():
            self.recursiveFuseTransform(child, transf)


if __name__ == '__main__':
    e = ApplyTransform()
    e.run()
