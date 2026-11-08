#!/usr/bin/env python3
"""GPT-DOUG // CL1 FULL BODY -- interactive, offline 3D binary terminal.

Self-contained, pure Python 3.10+ 3D mesh sampler + z-buffer.  The figure is an
ANATOMY-INSPIRED PROCEDURAL MODEL, not a medical reference or an actual CL1
hardware connection. Neural pulses are software simulations. No external
assets, web calls or third-party packages are required.
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import select
import shutil
import sys
import time
from dataclasses import dataclass

BONE, TISSUE, NEURAL, BIOCHIP = 1, 2, 3, 4
COLORS = {
    'CYAN': (70, 236, 231), 'BONE': (232, 221, 195),
    'AMBER': (255, 167, 65), 'GREEN': (125, 252, 154),
}


# -----------------------------------------------------------------------------
# CL1 mechanical ontology: a constrained *illustrative* kinematic model.
# These are not bone density measurements, medical reference values, actuator
# specifications, or observations from living CL1 hardware.
# -----------------------------------------------------------------------------
MECH_WORLD_SCALE_M = 0.315  # model coordinate -> nominal metre (artistic scale)
SKELETAL_MASS_SHARE = 0.15  # configurable proxy, NOT a measured body composition


@dataclass(frozen=True)
class MechanicalNode:
    key: str
    parent: str | None
    joint: str
    anchor: tuple[float, float, float]
    length_units: float
    mass_share: float
    axes: tuple[tuple[str, float, float], ...] = ()
    stiffness_nm_rad: float = 0.0
    damping_nms_rad: float = 0.0


MECHANICAL_NODES = (
    MechanicalNode('pelvis', None, 'fixed', (0, -.10, -.10), .65, .132),
    MechanicalNode('lumbar_spine', 'pelvis', 'ball_socket', (0, .20, -.12), .45, .060,
                   (('flexion', -25, 25), ('lateral', -18, 18), ('twist', -20, 20)), 18, 1.2),
    MechanicalNode('thoracic_cage', 'lumbar_spine', 'fixed', (0, 1.15, .0), .85, .170),
    MechanicalNode('cervical_spine', 'thoracic_cage', 'ball_socket', (0, 1.82, -.03), .27, .040,
                   (('flexion', -40, 40), ('lateral', -30, 30), ('twist', -50, 50)), 7, .45),
    MechanicalNode('cranium', 'cervical_spine', 'fixed', (0, 2.47, .02), .75, .110),
    MechanicalNode('left_clavicle', 'thoracic_cage', 'fixed', (-.48, 1.73, .13), .64, .025),
    MechanicalNode('right_clavicle', 'thoracic_cage', 'fixed', (.48, 1.73, .13), .64, .025),
    MechanicalNode('left_humerus', 'left_clavicle', 'ball_socket', (-.72, 1.59, .02), 1.10, .035,
                   (('flexion', -110, 110), ('abduction', -80, 100), ('rotation', -65, 65)), 9, .60),
    MechanicalNode('right_humerus', 'right_clavicle', 'ball_socket', (.72, 1.59, .02), 1.10, .035,
                   (('flexion', -110, 110), ('abduction', -80, 100), ('rotation', -65, 65)), 9, .60),
    MechanicalNode('left_forearm', 'left_humerus', 'hinge', (-.91, .52, .02), .82, .022,
                   (('elbow_flexion', 0, 140),), 5, .25),
    MechanicalNode('right_forearm', 'right_humerus', 'hinge', (.91, .52, .02), .82, .022,
                   (('elbow_flexion', 0, 140),), 5, .25),
    MechanicalNode('left_hand', 'left_forearm', 'universal', (-1.06, -.29, .13), .40, .012,
                   (('wrist_flexion', -70, 70), ('deviation', -25, 25)), 2, .12),
    MechanicalNode('right_hand', 'right_forearm', 'universal', (1.06, -.29, .13), .40, .012,
                   (('wrist_flexion', -70, 70), ('deviation', -25, 25)), 2, .12),
    MechanicalNode('left_femur', 'pelvis', 'ball_socket', (-.42, -.36, .04), 1.07, .070,
                   (('hip_flexion', -35, 120), ('abduction', -35, 45), ('rotation', -35, 35)), 22, 1.4),
    MechanicalNode('right_femur', 'pelvis', 'ball_socket', (.42, -.36, .04), 1.07, .070,
                   (('hip_flexion', -35, 120), ('abduction', -35, 45), ('rotation', -35, 35)), 22, 1.4),
    MechanicalNode('left_lower_leg', 'left_femur', 'hinge', (-.42, -1.43, .13), 1.12, .055,
                   (('knee_flexion', 0, 135),), 17, 1.1),
    MechanicalNode('right_lower_leg', 'right_femur', 'hinge', (.42, -1.43, .13), 1.12, .055,
                   (('knee_flexion', 0, 135),), 17, 1.1),
    MechanicalNode('left_foot', 'left_lower_leg', 'universal', (-.44, -2.54, .05), .50, .025,
                   (('ankle_flexion', -35, 45), ('inversion', -20, 20)), 5, .35),
    MechanicalNode('right_foot', 'right_lower_leg', 'universal', (.44, -2.54, .05), .50, .025,
                   (('ankle_flexion', -35, 45), ('inversion', -20, 20)), 5, .35),
)

NODE_BY_KEY = {node.key: node for node in MECHANICAL_NODES}


def validate_mechanical_graph():
    """Reject orphan joints, invalid constraints and mechanical graph cycles."""
    if len(NODE_BY_KEY) != len(MECHANICAL_NODES):
        raise ValueError('Duplicate mechanical entity ID')
    if not math.isclose(sum(n.mass_share for n in MECHANICAL_NODES), 1.0, abs_tol=1e-9):
        raise ValueError('Bone proxy mass fractions must sum to 1')
    for node in MECHANICAL_NODES:
        if node.parent is not None and node.parent not in NODE_BY_KEY:
            raise ValueError('Orphan joint: ' + node.key)
        if node.parent == node.key or node.mass_share <= 0 or node.length_units <= 0:
            raise ValueError('Invalid rigid segment: ' + node.key)
        if node.joint == 'fixed' and node.axes:
            raise ValueError('Fixed joint has degrees of freedom')
        if node.joint != 'fixed' and not node.axes:
            raise ValueError('Moving joint without limits')
        if any(lo >= hi or not all(map(math.isfinite, (lo, hi))) for _, lo, hi in node.axes):
            raise ValueError('Invalid angular limits')
        seen = set()
        cur = node.key
        while cur is not None:
            if cur in seen:
                raise ValueError('Cycle in rigid-link ontology')
            seen.add(cur)
            cur = NODE_BY_KEY[cur].parent
    return True


def _body_mass(body_mass_kg):
    if isinstance(body_mass_kg, bool) or not isinstance(body_mass_kg, (int, float)):
        raise ValueError('Body mass must be numeric')
    if not math.isfinite(body_mass_kg) or not 20 <= body_mass_kg <= 300:
        raise ValueError('Illustrative body mass must be 20..300 kg')
    return float(body_mass_kg)


def mechanical_properties(key, body_mass_kg=70.0):
    """Estimate proxy link mass/inertia, not clinical biomechanics."""
    body_mass_kg = _body_mass(body_mass_kg)
    if key not in NODE_BY_KEY:
        raise ValueError('Unknown mechanical entity: ' + str(key))
    n = NODE_BY_KEY[key]
    mass = body_mass_kg * SKELETAL_MASS_SHARE * n.mass_share
    length = n.length_units * MECH_WORLD_SCALE_M
    return {
        'id': 'cl1:segment/' + n.key,
        'label': n.key.replace('_', ' ').title(),
        'class': 'cl1:SkeletalRigidLink',
        'parent_id': 'cl1:segment/' + n.parent if n.parent else None,
        'joint_type': n.joint,
        'degrees_of_freedom': len(n.axes),
        'axes_limits_deg': [{'axis': axis, 'min': lo, 'max': hi} for axis, lo, hi in n.axes],
        'anchor_model_xyz': list(n.anchor),
        'nominal_length_m': round(length, 5),
        'estimated_bone_proxy_mass_kg': round(mass, 5),
        'mass_fraction_of_skeleton': n.mass_share,
        'rod_axis_inertia_kg_m2': round(mass * length * length / 12.0, 8),
        'joint_stiffness_nm_per_rad': n.stiffness_nm_rad,
        'joint_damping_nms_per_rad': n.damping_nms_rad,
        'collision_proxy': 'ellipsoid' if n.key in ('pelvis', 'cranium', 'thoracic_cage') else 'capsule',
        'material': 'idealized rigid bone proxy',
        'provenance': 'illustrative procedural simulation, NOT measured',
    }


def mech_ontology(body_mass_kg=70.0):
    """Locally serializable graph for downstream GPT-DOUG/XUNIA ontology APIs."""
    body_mass_kg = _body_mass(body_mass_kg)
    validate_mechanical_graph()
    components = [mechanical_properties(n.key, body_mass_kg) for n in MECHANICAL_NODES]
    return {
        '@context': {
            'cl1': 'urn:gpt-doug:cl1:mechanics:',
            'schema': 'https://schema.org/',
        },
        'schema_version': 'cl1-mechanics/v1',
        'entity_count': len(components),
        'ontology_type': 'ArticulatedSkeletalKinematicGraph',
        'simulation_only': True,
        'hardware_connected': False,
        'reference_body_mass_kg': body_mass_kg,
        'bone_system_mass_fraction_assumed': SKELETAL_MASS_SHARE,
        'reference_metre_per_model_unit': MECH_WORLD_SCALE_M,
        'inertia_model': 'uniform slender rod I = m * L^2 / 12 (illustrative)',
        'source': 'procedural full-body CL1 terminal model; no anatomical scan',
        'components': components,
        'relations': [
            {'source': c['parent_id'], 'type': 'HAS_CHILD_SEGMENT', 'target': c['id']}
            for c in components if c['parent_id'] is not None
        ],
    }


def evaluate_joint(key, angle_deg, speed_deg_s=0.0, body_mass_kg=70.0):
    """Evaluate a 1-axis *virtual spring-damper*; no actuation or motor control."""
    p = mechanical_properties(key, body_mass_kg)
    if not p['axes_limits_deg']:
        raise ValueError('Fixed link cannot be flexed: ' + key)
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
               for v in (angle_deg, speed_deg_s)):
        raise ValueError('Angle and speed must be finite numbers')
    if abs(angle_deg) > 360 or abs(speed_deg_s) > 720:
        raise ValueError('Simulation angle/speed are outside bounded inputs')
    axis = p['axes_limits_deg'][0]
    allowed = axis['min'] <= angle_deg <= axis['max']
    if not allowed:
        torque = None  # unsafe state; never fabricate an admissible actuator command
    else:
        torque = -(p['joint_stiffness_nm_per_rad'] * math.radians(angle_deg) +
                   p['joint_damping_nms_per_rad'] * math.radians(speed_deg_s))
    return {
        'entity_id': p['id'],
        'axis': axis['axis'],
        'input_angle_deg': angle_deg,
        'input_speed_deg_s': speed_deg_s,
        'limit_min_deg': axis['min'],
        'limit_max_deg': axis['max'],
        'within_limits': allowed,
        'virtual_restoring_torque_nm': round(torque, 5) if torque is not None else None,
        'simulation_only': True,
        'hardware_command_sent': False,
    }

def _add_ellipsoid(points, x, y, z, rx, ry, rz, kind=BONE, lat=19, lon=48,
                   mask=None):
    """Surface samples, not a 2D picture."""
    for i in range(1, lat):
        theta = math.pi * i / lat
        sy = math.cos(theta)
        ss = math.sin(theta)
        for j in range(lon):
            phi = 2 * math.pi * j / lon
            xx, yy, zz = rx * ss * math.cos(phi), ry * sy, rz * ss * math.sin(phi)
            p = (x + xx, y + yy, z + zz)
            if mask is None or mask(p):
                points.append((*p, kind))


def _tube(points, knots, radius, kind=BONE, rings=12, segments=5, radius_end=None):
    """Cylinder samples along piecewise 3D curve, including thickness/turning."""
    for n in range(len(knots)-1):
        p, q = knots[n], knots[n+1]
        axis = [q[j]-p[j] for j in range(3)]
        length = math.sqrt(sum(a*a for a in axis))
        if length < 1e-8:
            continue
        axis = [a/length for a in axis]
        reference = (0., 0., 1.) if abs(axis[2]) < .89 else (1., 0., 0.)
        ux = axis[1]*reference[2]-axis[2]*reference[1]
        uy = axis[2]*reference[0]-axis[0]*reference[2]
        uz = axis[0]*reference[1]-axis[1]*reference[0]
        magnitude = math.sqrt(ux*ux+uy*uy+uz*uz)
        u = [ux/magnitude, uy/magnitude, uz/magnitude]
        v = [axis[1]*u[2]-axis[2]*u[1], axis[2]*u[0]-axis[0]*u[2], axis[0]*u[1]-axis[1]*u[0]]
        for i in range(segments+1):
            t = i/segments
            center = [p[j] + (q[j]-p[j])*t for j in range(3)]
            r = radius if radius_end is None else radius + (radius_end-radius)*t
            for j in range(rings):
                a = 2*math.pi*j/rings
                ca, sa = math.cos(a), math.sin(a)
                points.append((*(center[k] + r*(u[k]*ca+v[k]*sa) for k in range(3)), kind))


def _curve(points, fn, radius, kind, steps=44, rings=8):
    knots = [fn(i/steps) for i in range(steps+1)]
    _tube(points, knots, radius, kind, rings=rings, segments=1)


def _bone_skeleton(points):
    # Normalized artistic human, standing 5.55 units high, head to toes.
    # Torso: 24 individual vertebral bodies and visible processes.
    for i in range(25):
        y = 1.78 - 0.075*i
        z = -0.09 - 0.08*math.sin(math.pi*i/24)
        _add_ellipsoid(points, 0, y, z, .071, .044, .056,
                       BONE, lat=9, lon=18)
        if i % 2 == 0:
            _tube(points, [(-.10, y, z-.015), (.10, y, z-.015)], .022,
                  BONE, rings=8, segments=2)
    # Sternum and clavicles.
    _tube(points, [(0, 1.64, .34), (0, 1.16, .36), (0, .91, .33)], .048,
          BONE, rings=13, segments=8)
    for side in (-1, 1):
        _curve(points, lambda t, s=side:
               (s*(.075+.62*t), 1.75-.13*math.sin(math.pi*t), .25-.12*t),
               .040, BONE)
    # 11 paired ribs: each wraps posterior to lateral and forward to sternum.
    for rib in range(11):
        y = 1.55-rib*.074
        span = .60*(1-.050*max(0, rib-5))
        depth = .30*(1-.035*max(0, rib-5))
        for side in (-1, 1):
            _curve(points, lambda t, s=side, y0=y, a=span, d=depth: (
                s*(.08+a*math.sin(math.pi*t)),
                y0 - .04*math.sin(math.pi*t) + .07*t,
                -.13 + d*(1-math.cos(math.pi*t))
            ), .022 if rib<6 else .017, BONE, steps=35)
    # Floating ribs are visibly shorter and separate from the sternum.
    for side in (-1, 1):
        _curve(points, lambda t, s=side:
               (s*(.09+.43*math.sin(math.pi*t*.78)), .67-.12*t,
                -.14 + .24*t), .023, BONE, steps=35)
    # Pelvic ring, sacrum, iliac wings and acetabulum.
    _add_ellipsoid(points, 0, -.12, -.10, .13, .23, .09, BONE, lat=14, lon=27)
    for side in (-1, 1):
        _curve(points, lambda t,s=side: (s*(.15+.37*math.sin(math.pi*t)),
                 .11+.07*math.sin(math.pi*t)-.42*t,
                 -.08+.32*t), .056, BONE, steps=44, rings=12)
        _curve(points, lambda t,s=side: (s*(.46-.34*t), -.32-.14*math.sin(math.pi*t),
                 .17+.08*math.sin(math.pi*t)), .047, BONE, steps=28)
        _add_ellipsoid(points, side*.40, -.38, .04, .13, .12, .11,
                       BONE, lat=12, lon=26)
    # Upper arms, radius/ulna, carpals, metacarpals, and five digits.
    for side in (-1, 1):
        shoulder=(side*.72,1.60,.00)
        elbow=(side*.91,.52,.02)
        wrist=(side*1.06,-.29,.13)
        _add_ellipsoid(points,*shoulder,.115,.12,.12,BONE,lat=12,lon=26)
        _tube(points,[shoulder,(side*.84,1.17,.00),elbow],.068,BONE,segments=9)
        _add_ellipsoid(points,*elbow,.085,.08,.08,BONE,lat=12,lon=24)
        for dx in (-.046,.050):
            _tube(points,[(elbow[0]+side*dx,elbow[1],elbow[2]),
                    (side*(.99+dx*.65),.04,.10),
                    (wrist[0]+side*dx*.3,wrist[1],wrist[2])],
                  .031,BONE,rings=10,segments=7)
        _add_ellipsoid(points,*wrist,.078,.045,.07,BONE,lat=10,lon=18)
        palm=(side*1.08,-.43,.14)
        _tube(points,[wrist,palm],.080,BONE,segments=6)
        for finger in range(5):
            offset=(finger-2)*.038
            base=(side*(1.08+offset),-.45,.15)
            tip=(side*(1.095+offset*1.75),-.68+(abs(finger-2)*.045),.17)
            _tube(points,[base,tip],.015,BONE,rings=7,segments=7)
    # Femurs, kneecaps, tibia, fibula, ankle and metatarsal feet.
    for side in (-1,1):
        hip=(side*.42,-.36,.04)
        knee=(side*.42,-1.43,.13)
        ankle=(side*.44,-2.54,.05)
        _add_ellipsoid(points,*hip,.13,.14,.12,BONE,lat=13,lon=28)
        _tube(points,[hip,(side*.49,-.87,.06),knee],.10,BONE,segments=10)
        _add_ellipsoid(points,*knee,.11,.1,.13,BONE,lat=12,lon=29)
        _tube(points,[knee,(side*.45,-1.99,.04),ankle],.074,BONE,segments=10)
        _tube(points,[(knee[0]+side*.075,knee[1],knee[2]-.03),
                       (side*.54,-2.02,-.03),(side*.51,-2.53,-.01)],
              .027,BONE,rings=9,segments=6)
        _add_ellipsoid(points,*ankle,.08,.09,.08,BONE,lat=12,lon=20)
        heel=(side*.43,-2.63,-.09)
        toe=(side*.43,-2.72,.34)
        _tube(points,[heel,(side*.44,-2.68,.16),toe],.075,BONE,segments=8)
        for j in range(5):
            off=(j-2)*.043
            _tube(points,[(side*(.43+off),-2.70,.29),
                          (side*(.43+off*1.5),-2.73,.46-.012*abs(j-2))],
                  .014,BONE,rings=7,segments=5)


def _head(points):
    # Sculptural cranial shell with actual voids for the orbits and nose.
    # Eye sockets cut out from the frontal bone, not black painted circles.
    def mask(p):
        x,y,z=p
        if z>0.185:
            left=((x+.16)/.115)**2+((y-2.29)/.123)**2
            right=((x-.16)/.115)**2+((y-2.29)/.123)**2
            if min(left,right)<1.05:
                return False
            if abs(x)<.065 and 2.02<y<2.28:
                return False
        return True
    _add_ellipsoid(points,0,2.45,.015,.365,.435,.335,BONE,lat=56,lon=118,mask=mask)
    _add_ellipsoid(points,0,2.045,.10,.27,.16,.26,BONE,lat=19,lon=55,mask=mask)
    # Brow ridges and zygomatic arches.
    for side in (-1,1):
        _curve(points,lambda t,s=side:
               (s*(.075+.205*t),2.42-.045*math.sin(math.pi*t),.296),
               .035,BONE,steps=25)
        _curve(points,lambda t,s=side:
               (s*(.21+.13*math.sin(math.pi*t)),2.15+.02*math.sin(math.pi*t),
                .24-.20*t), .034,BONE,steps=28)
    # Mandible / jaw U-arc.
    _curve(points,lambda t: (.29*math.cos(math.pi*t),1.97-.16*math.sin(math.pi*t),
               .11+.19*math.sin(math.pi*t)),.038,BONE,steps=54,rings=11)
    for row in (0,1):
        for side in (-1,1):
            for j in range(7):
                angle=(j+.5)/7*math.pi/2
                x=side*.235*math.sin(angle)
                z=.28-.10*math.sin(angle)
                y=2.00-(row*.10)
                _add_ellipsoid(points,x,y,z,.019,.029,.028,BONE,lat=7,lon=12)
    _tube(points,[(0,1.91,.0),(0,1.80,-.02)],.086,BONE,segments=5)


def _body_shell(points):
    # Surface under-sampling deliberately leaves bones and neurons visible.
    _add_ellipsoid(points,0,1.17,0,.67,.79,.38,TISSUE,lat=45,lon=85)
    _add_ellipsoid(points,0,-.10,.005,.58,.43,.37,TISSUE,lat=23,lon=57)
    _add_ellipsoid(points,0,2.46,.01,.375,.46,.35,TISSUE,lat=38,lon=74)
    for side in (-1,1):
        for endpoints,radius in [
            ([(side*.71,1.59,0),(side*.92,.52,.03)],.145),
            ([(side*.92,.50,.03),(side*1.06,-.31,.13)],.105),
            ([(side*.42,-.40,.06),(side*.42,-1.45,.12)],.22),
            ([(side*.42,-1.45,.11),(side*.45,-2.56,.05)],.15),
        ]:
            _tube(points,endpoints,radius,TISSUE,rings=27,segments=45)


def _neural_circuitry(points):
    # Simulation of neuroprosthetic routing, not CL1 cell measurements.
    _add_ellipsoid(points,0,2.51,0,.295,.322,.263,NEURAL,lat=35,lon=72)
    # Neural bundles pass from a synthetic cranial implant into a torso hub.
    for side in (-1,1):
        _curve(points,lambda t,s=side:
               (s*(.07+.09*math.sin(math.pi*t)),2.02-.89*t,
                .30-.08*math.sin(math.pi*t)), .018,NEURAL,steps=55)
        _curve(points,lambda t,s=side:
               (s*(.06+.30*t),1.15-.81*t,.23-.13*t),
               .014,NEURAL,steps=50)
        _curve(points,lambda t,s=side:
               (s*(.38+.60*t),.35-.78*t,.02+.13*t),
               .012,NEURAL,steps=60)
        _curve(points,lambda t,s=side:
               (s*(.30+.18*t),-.27-2.21*t,.12-.06*t),
               .013,NEURAL,steps=77)
    # Heart-like hub and abdominal computational core.
    _add_ellipsoid(points,-.13,1.15,.30,.16,.18,.13,NEURAL,lat=22,lon=40)
    _add_ellipsoid(points,0,.26,.35,.25,.16,.10,BIOCHIP,lat=22,lon=40)
    for ring in range(7):
        y=.29-ring*.065
        _curve(points,lambda t, r=ring,y=y:
               (.24*math.sin(math.pi*2*t),y,
                .36+.055*math.cos(math.pi*2*t)), .012,BIOCHIP,steps=52)
    # Paired subdermal electric paths.
    for s in (-1,1):
        for channel in range(3):
            _curve(points,lambda t,s=s,ch=channel:
                   (s*(.19+.07*ch+.15*math.sin(math.pi*t)),
                    1.48-.76*t,.35-.045*ch),
                   .008,NEURAL,steps=50,rings=5)


@functools.lru_cache(maxsize=2)
def geometry(detail='normal'):
    if detail not in ('normal','light'):
        raise ValueError('detail must be normal or light')
    points=[]
    _bone_skeleton(points)
    _head(points)
    _body_shell(points)
    _neural_circuitry(points)
    if detail=='light':
        points=points[::3]
    return tuple(points)


class BodyCanvas:
    def __init__(self, points, width=108, height=47, mode='SKELETON'):
        self.points=points
        self.width,self.height=width,height
        self.mode=mode.upper()
        self.yaw=0.07
        self.pitch=0.03
        self.zoom=1.0
        self.spin=True
        self.binary=True
        self.tint='BONE'
        self.frame=0
        self.view='FULL'
        self.ontology_enabled=True
        self.ontology_selection=0
        self.simulated_body_mass_kg=70.0

    def render(self, color=False):
        w,h=self.width,self.height
        zbuf=[-999.0]*(w*h)
        intens=[0]*(w*h)
        layers=[0]*(w*h)
        cy,sy=math.cos(self.yaw),math.sin(self.yaw)
        cp,sp=math.cos(self.pitch),math.sin(self.pitch)
        if self.view=='HEAD':
            focus=2.28
            zoomscale=self.zoom*2.7
        elif self.view=='TORSO':
            focus=.90
            zoomscale=self.zoom*1.67
        else:
            focus=.14
            zoomscale=self.zoom
        camera=6.4
        # Character cells are typically ~twice as high as wide. Compensation
        # protects full-body skeletal proportions on the terminal.
        focal=min((w-4)*camera/9.0,(h-3)*camera/5.55)*zoomscale
        for idx,(x0,y0,z0,kind) in enumerate(self.points):
            if self.mode=='SKELETON' and kind not in (BONE,BIOCHIP):
                continue
            if self.mode=='BODY' and kind not in (TISSUE,BIOCHIP):
                continue
            if self.mode=='NEURAL' and kind not in (NEURAL,BIOCHIP,BONE):
                continue
            if self.mode=='FUSION' and kind==TISSUE and idx%6:
                continue
            x=cy*x0+sy*z0
            z=-sy*x0+cy*z0
            yc=y0-focus
            y=cp*yc-sp*z
            z=sp*yc+cp*z
            # In CL1 NEURAL mode, channels float just over bone; they do not
            # claim to be real neuronal sensing.
            if kind in (NEURAL,BIOCHIP) and self.mode in ('NEURAL','FUSION'):
                z+=.09
            depth=camera-z
            if depth<=.8:
                continue
            col=int(w*.5+x/depth*focal*2.0)
            row=int(h*.5-y/depth*focal*.92)
            if not(0<=col<w and 0<=row<h):
                continue
            at=row*w+col
            if z<=zbuf[at]:
                continue
            zbuf[at]=z
            layers[at]=kind
            intensity=.43+.19*(z+1)+.11*(x+.6)-.08*abs(y)
            intens[at]=max(1,min(6,int(intensity*5.5)))
        # Project the currently selected ontology joint locator onto the same
        # 3D scene (not a separate flat ASCII skull). The locator is a simulated
        # reference marker, not a calibrated skeletal measurement.
        locator_pixels=set()
        locator_center=None
        if self.ontology_enabled:
            selected = MECHANICAL_NODES[self.ontology_selection]
            x0, y0, z0 = selected.anchor
            px = cy*x0 + sy*z0
            pz = -sy*x0 + cy*z0
            py = cp*(y0-focus)-sp*pz
            pz = sp*(y0-focus)+cp*pz
            d = camera-pz
            if d > .8:
                col = int(w*.5 + px/d*focal*2.0)
                row = int(h*.5 - py/d*focal*.92)
                locator_center=row*w+col
                for dr, dc in ((0,0),(-1,0),(1,0),(0,-1),(0,1)):
                    rr, cc = row+dr, col+dc
                    if 0<=rr<h and 0<=cc<w:
                        at=rr*w+cc
                        locator_pixels.add(at)
                        intens[at] = 6
                        layers[at] = BONE
        lines=[]
        rgb=COLORS[self.tint]
        for row in range(h):
            cells=[]
            last=None
            for col in range(w):
                i=row*w+col
                level=intens[i]
                kind=layers[i]
                if not level:
                    char=' '
                elif self.binary:
                    if i in locator_pixels:
                        char='1' if i==locator_center else '0'
                    else:
                        char='1' if ((row*3+col*5+self.frame//4)%7)<4 else '0'
                else:
                    ramp=' .:+*#@'
                    char=ramp[level]
                if color:
                    new=(kind,level,i in locator_pixels)
                    if new!=last:
                        last=new
                        if not level:
                            cells.append('\x1b[0m')
                        else:
                            if i in locator_pixels:
                                base=(255,204,128)
                            elif kind in (BIOCHIP,NEURAL):
                                base=(105,255,181) if self.tint!='AMBER' else (255,240,150)
                            elif kind==TISSUE:
                                base=tuple(int(v*.53) for v in rgb)
                            else:
                                base=rgb
                            brightness=min(1.0,.32+.14*level)
                            cells.append('\x1b[38;2;%d;%d;%dm'%tuple(int(v*brightness) for v in base))
                cells.append(char)
            lines.append(''.join(cells)+('\x1b[0m' if color else ''))
        return '\n'.join(lines)

    def dashboard(self, color=False):
        w=self.width
        hdr='BIOCHIP-CL1 // GPT-DOUG FULL BODY // 3D BINARY ANATOMY'
        stats='MODEL: %s | %s | %s | %s | %d VERTICES | YAW %03d'%(
            self.view,self.mode,'01' if self.binary else 'SHADE',self.tint,
            len(self.points),int(math.degrees(self.yaw))%360)
        footer='A/D ORBIT W/S TILT +/- ZOOM 1-4 MODE [/] SELECT O ONTOLOGY H/T/F VIEW B/C RENDER P PAUSE Q EXIT'
        notice='CL1 NEURAL/BIOCHIP LAYER IS SIMULATED. NO LIVING NEURONS OR HARDWARE CONNECTED.'
        head=('\x1b[1;36m' if color else '')+hdr[:w].ljust(w)+('\x1b[0m' if color else '')
        if self.ontology_enabled:
            part=mechanical_properties(
                MECHANICAL_NODES[self.ontology_selection].key,
                self.simulated_body_mass_kg,
            )
            joint=part['axes_limits_deg']
            limits=(' | '.join('%s[%g,%g]' % (a['axis'],a['min'],a['max'])
                     for a in joint) if joint else 'LOCKED')
            info1='ONTOLOGY %02d/%02d  %s -> %s  %s / DOF %d' % (
                self.ontology_selection+1,len(MECHANICAL_NODES),part['label'].upper(),
                (part['parent_id'] or 'ROOT').rsplit('/',1)[-1].upper(),
                part['joint_type'].upper(),part['degrees_of_freedom'])
            info2='MECH SIM  MASS %.2f kg  L %.2f m  I %.4f kg.m2  K %g  D %g  %s' % (
                part['estimated_bone_proxy_mass_kg'],part['nominal_length_m'],
                part['rod_axis_inertia_kg_m2'],part['joint_stiffness_nm_per_rad'],
                part['joint_damping_nms_per_rad'],limits)
        else:
            info1='ONTOLOGY HIDDEN - PRESS O TO INSPECT MECHANICAL PROPERTIES'
            info2='MECHANICAL PARAMETERS: ILLUSTRATIVE SIMULATION; NOT MEASURED.'
        return '\n'.join((head,stats[:w].ljust(w),'='*w,self.render(color),
                          '='*w,info1[:w].ljust(w),info2[:w].ljust(w),
                          footer[:w].ljust(w),notice[:w].ljust(w)))


def run(argv=None):
    p=argparse.ArgumentParser(description='Full-body 3D anatomical-inspired CL1 binary terminal. Offline; no dependencies.')
    p.add_argument('--once',action='store_true',help='render a single frame')
    p.add_argument('--frames',type=int,default=0)
    p.add_argument('--width',type=int,default=0,help='40..180 characters')
    p.add_argument('--height',type=int,default=0,help='24..90 text rows')
    p.add_argument('--fps',type=int,default=9)
    p.add_argument('--mode',choices=('fusion','body','skeleton','neural'),default='skeleton')
    p.add_argument('--color',choices=('bone','cyan','amber','green'),default='bone')
    p.add_argument('--ontology-json',action='store_true',help='export local skeletal mechanical ontology JSON')
    p.add_argument('--inspect',choices=tuple(NODE_BY_KEY),help='print properties of a single entity')
    p.add_argument('--joint-angle',type=float,help='evaluate virtual spring/limits at this angle in degrees')
    p.add_argument('--joint-speed',type=float,default=0.0,help='simulated angular speed in degrees/s')
    p.add_argument('--body-mass',type=float,default=70.0,help='nominal simulated mass 20..300 kg')
    p.add_argument('--detail',choices=('normal','light'),default='normal')
    p.add_argument('--no-color',action='store_true')
    p.add_argument('--no-spin',action='store_true')
    args=p.parse_args(argv)
    if args.width and not 40<=args.width<=180:
        p.error('width must be 40..180')
    if args.height and not 24<=args.height<=90:
        p.error('height must be 24..90')
    if not 1<=args.fps<=20 or not 0<=args.frames<=3600:
        p.error('FPS 1..20, frame count 0..3600')
    try:
        _body_mass(args.body_mass)
        if args.ontology_json:
            if args.inspect or args.joint_angle is not None:
                p.error('--ontology-json cannot be combined with --inspect/--joint-angle')
            print(json.dumps(mech_ontology(args.body_mass),indent=2))
            return 0
        if args.joint_angle is not None and not args.inspect:
            p.error('--joint-angle requires --inspect')
        if args.joint_speed and args.joint_angle is None:
            p.error('--joint-speed requires --joint-angle and --inspect')
        if args.inspect:
            payload=mechanical_properties(args.inspect,args.body_mass)
            if args.joint_angle is not None:
                payload['joint_evaluation']=evaluate_joint(args.inspect,args.joint_angle,
                                                          args.joint_speed,args.body_mass)
            print(json.dumps(payload,indent=2))
            return 0
    except ValueError as exc:
        p.error(str(exc))
    points=geometry(args.detail)
    terminal=shutil.get_terminal_size((116,54))
    cols=args.width or max(60,min(140,terminal.columns-2))
    rows=args.height or max(24,min(74,terminal.lines-8))
    canvas=BodyCanvas(points,width=cols,height=rows,mode=args.mode)
    canvas.tint=args.color.upper()
    canvas.simulated_body_mass_kg=args.body_mass
    canvas.spin=not args.no_spin
    interactive=sys.stdout.isatty() and sys.stdin.isatty() and args.frames==0 and not args.once
    maximum=1 if (args.once or (not interactive and args.frames==0)) else args.frames
    original=None
    try:
        if interactive:
            import termios
            import tty
            fd=sys.stdin.fileno()
            original=termios.tcgetattr(fd)
            tty.setcbreak(fd)
            sys.stdout.write('\x1b[?25l\x1b[2J')
        frame=0
        while True:
            started=time.monotonic()
            if interactive:
                size=shutil.get_terminal_size((cols,rows+8))
                canvas.width=args.width or max(60,min(140,size.columns-2))
                canvas.height=args.height or max(24,min(74,size.lines-8))
                sys.stdout.write('\x1b[H\x1b[J')
            sys.stdout.write(canvas.dashboard(color=not args.no_color and sys.stdout.isatty())+'\n')
            sys.stdout.flush()
            frame+=1
            canvas.frame=frame
            if maximum and frame>=maximum:
                break
            if canvas.spin:
                canvas.yaw+=.032
            wait=max(0,1/args.fps-(time.monotonic()-started))
            if interactive:
                ready,_,_=select.select([sys.stdin],[],[],wait)
                if ready:
                    key=sys.stdin.read(1).lower()
                    if key in ('q','\x03'):
                        break
                    if key=='a':
                        canvas.yaw-=.16
                    if key=='d':
                        canvas.yaw+=.16
                    if key=='w':
                        canvas.pitch=max(-1.1,canvas.pitch-.11)
                    if key=='s':
                        canvas.pitch=min(1.1,canvas.pitch+.11)
                    if key in ('+','='):
                        canvas.zoom=min(2.4,canvas.zoom+.14)
                    if key in ('-','_'):
                        canvas.zoom=max(.5,canvas.zoom-.14)
                    if key=='1':
                        canvas.mode='FUSION'
                    if key=='2':
                        canvas.mode='SKELETON'
                    if key=='3':
                        canvas.mode='NEURAL'
                    if key=='4':
                        canvas.mode='BODY'
                    if key=='h':
                        canvas.view='HEAD'
                    if key=='t':
                        canvas.view='TORSO'
                    if key=='f':
                        canvas.view='FULL'
                    if key=='o':
                        canvas.ontology_enabled=not canvas.ontology_enabled
                    if key==']':
                        canvas.ontology_selection=(canvas.ontology_selection+1)%len(MECHANICAL_NODES)
                    if key=='[':
                        canvas.ontology_selection=(canvas.ontology_selection-1)%len(MECHANICAL_NODES)
                    if key=='p':
                        canvas.spin=not canvas.spin
                    if key=='b':
                        canvas.binary=not canvas.binary
                    if key=='c':
                        options=list(COLORS)
                        canvas.tint=options[(options.index(canvas.tint)+1)%len(options)]
            else:
                time.sleep(wait)
    except KeyboardInterrupt:
        return 130
    finally:
        if original is not None:
            import termios
            termios.tcsetattr(fd,termios.TCSADRAIN,original)
            sys.stdout.write('\x1b[0m\x1b[?25h\n')
    return 0

if __name__=='__main__':
    raise SystemExit(run())
