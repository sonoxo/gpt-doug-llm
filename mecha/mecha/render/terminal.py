"""Deterministic, bounded, zero-ANSI projection of a synthetic 3D wireframe."""
from __future__ import annotations
import math
from typing import Any, Mapping

_ALLOWED_KEYS={'x','y','z','time','memory','compute'}


def _frame_args(frame: int, width: int) -> None:
    if (type(frame) is not int or not 0<=frame<=1000 or
        type(width) is not int or not 40<=width<=160):
        raise ValueError('frame 0..1000 and width 40..160 required')


def _validated_channels(snapshot: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(snapshot,dict) or snapshot.get('type')!='MechaSnapshot':
        raise ValueError('read-only view accepts validated MechaSnapshot only')
    if snapshot.get('source_kind')!='SYNTHETIC' or snapshot.get('authority')!='RESEARCH_ONLY':
        raise ValueError('view accepts only synthetic research data')
    if snapshot.get('real_world_actuation') is not False or snapshot.get('external_calls')!=0:
        raise ValueError('cannot render operational state')
    c=snapshot.get('channels')
    if not isinstance(c,dict) or set(c)!=_ALLOWED_KEYS:
        raise ValueError('six typed channels required')
    for key in ('x','y','z'):
        if type(c[key]) not in (int,float) or not math.isfinite(c[key]) or not -100<=c[key]<=100:
            raise ValueError('invalid projected coordinate')
    if c['memory']!='SOURCE_LABELS_ONLY' or c['compute']!='ABSTRACT_SIMULATION_OPERATIONS':
        raise ValueError('untrusted model label')
    time=c['time']
    if (not isinstance(time,dict) or set(time)!={'simulated_step'} or
        type(time['simulated_step']) is not int or not 0<=time['simulated_step']<=20):
        raise ValueError('invalid simulated time')
    return c


def render_frame(snapshot: Mapping[str,Any] | None, *, frame: int=0,
                 width: int=80, color: bool=False) -> str:
    _frame_args(frame,width)
    if snapshot is None:
        return 'MECHA | NO SIGNAL | RESEARCH_ONLY\nNo real robotics connected'
    c=_validated_channels(snapshot)
    # Width is never increased and colors/ANSI are not emitted for untrusted data.
    height=15
    board=[[' ']*width for _ in range(height)]
    vertices=[(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
              (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
    angle=frame*0.37+0.3
    cosa,sina=math.cos(angle),math.sin(angle)
    ca,sa=math.cos(angle*0.64),math.sin(angle*0.64)
    projected=[]
    for x,y,z in vertices:
        rx=x*cosa+z*sina
        rz=z*cosa-x*sina
        ry=y*ca-rz*sa
        projected.append((int(width/2+rx*width/7+ry*width/12),
                          int(height/2+ry*height/4)))
    edges=((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),
           (0,4),(1,5),(2,6),(3,7))
    for first,last in edges:
        ax,ay=projected[first]; bx,by=projected[last]
        steps=max(abs(ax-bx),abs(ay-by),1)
        for index in range(steps+1):
            px=round(ax+(bx-ax)*index/steps)
            py=round(ay+(by-ay)*index/steps)
            if 0<=py<height and 0<=px<width:
                board[py][px]='.'
    for px,py in projected:
        if 0<=py<height and 0<=px<width:
            board[py][px]='+'
    lines=['GPT-DOUG MECHA | SYNTHETIC | RESEARCH_ONLY | No real robotics connected']
    lines.extend(''.join(row).rstrip() for row in board)
    lines += [
        'X: {:.2f}  Y: {:.2f}  Z: {:.2f}'.format(c['x'],c['y'],c['z']),
        'D4 TIME: simulated step {}'.format(c['time']['simulated_step']),
        'D5 MEMORY: SOURCE_LABELS_ONLY',
        'D6 COMPUTE: ABSTRACT_SIMULATION_OPERATIONS',
        'CLASSICAL SIMULATION | No quantum hardware or biological device connected',
    ]
    return '\n'.join(lines)


def render_frames(snapshot: Mapping[str,Any] | None, *, frames: int=3,
                  width: int=80, color: bool=False) -> list[str]:
    if type(frames) is not int or not 1<=frames<=1000:
        raise ValueError('frames must be integer 1..1000')
    return [render_frame(snapshot,frame=i,width=width,color=color) for i in range(frames)]
